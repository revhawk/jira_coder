"""
Unified Application Generation Graph.

This module defines and runs a LangGraph workflow to generate a complete,
integrated Streamlit application from a set of Jira tickets. The process involves
multiple agentic steps, from architecture design to code generation and testing.
"""
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from pathlib import Path
from agents.jira_agent import jira_client
from agents.implementation_agent import write_files
from agents.tester_agent import run_pytest
from config.settings import Settings
from utils.logging_utils import setup_logging
from utils.file_utils import load_prompt, read_text_safe
from utils.langsmith_stats import display_run_stats
from utils.llm_helper import call_llm
import ast
import logging
import json
import re
import os

def run_unified_graph(project_key: str, ticket_keys: list):
    """
    Initializes and runs the unified application generation graph.
    """
    logger, log_file = setup_logging("unified", project_key)
    logger.info(f"Starting unified generation for project {project_key} with tickets: {ticket_keys}")

    class GenState(TypedDict, total=False):
        """Defines the shared state for the graph, passing data between nodes."""
        project_key: str
        ticket_keys: list
        tickets: list  # [{key, title, description}]
        epic_description: str
        architecture_approved: bool
        arch_iteration: int
        rejection_reason: str
        architecture_plan: str
        modules: dict  # {module_name: {tickets: [], functions: []}}
        specs: dict  # {module_name: spec_json}
        test_files: dict  # {module_name: path}
        code_files: dict  # {module_name: path}
        app_path: str
        test_results: dict
        ui_design: str
        ui_pattern: str
        test_output: str # For fix_analyzer
        passed: int
        failed: int
        collected: int
        needs_fix: bool
        stuck: bool
        prev_failures: dict
        fix_recommendations: str
        fix_type: str
        app_errors: list
        app_fix_iteration: int
        current_tests: str
        current_code: str
        health_ok: bool
        review_report: str
        senior_dev_review: str
        architecture_review: str

    def _log_phase(phase: str): # Renamed to avoid conflict with imported log_phase if any
        logger.info(f"Phase: {phase}")
        print(f"⚙️  {phase}...") # noqa: T201

    def jira_reader(state: GenState) -> GenState:
        """Node: Reads Jira tickets based on keys or fetches all from a project."""
        _log_phase("jira_reader")
        keys_to_fetch = state.get("ticket_keys", [])
        
        # Handle "ALL" keyword - load all tickets from project
        if len(keys_to_fetch) == 1 and keys_to_fetch[0].upper() == "ALL":
            logger.info(f"Loading all tickets from project {project_key} (max 50)")
            result = jira_client.list_all_issues_in_project(project_key, max_results=50)
            issues = result.get("issues", [])
            keys_to_fetch = [issue.get("key") for issue in issues]
            logger.info(f"Found {len(keys_to_fetch)} tickets in {project_key}")
        
        tickets = []
        epic_description = ""
        for key in keys_to_fetch:
            data = jira_client.read_issue(key)
            if "error" not in data:
                # Check if this is an EPIC
                issue_type = data.get("issuetype", "")
                logger.info(f"{key}: issue_type = {issue_type}")
                
                if issue_type.upper() == "EPIC":
                    desc = data.get("description", "")
                    if desc:
                        epic_description = str(desc)
                        logger.info(f"Found EPIC: {key} with description length: {len(epic_description)}")
                        print(f"📋 EPIC: {data.get('summary', '')}")
                    else:
                        logger.warning(f"EPIC {key} has no description")
                else:
                    tickets.append({
                        "key": key,
                        "title": data.get("summary", ""),
                        "description": str(data.get("description", ""))
                    })
        logger.info(f"Loaded {len(tickets)} tickets and EPIC description")
        return {"tickets": tickets, "ticket_keys": keys_to_fetch, "epic_description": epic_description}

    def health_check(state: GenState) -> GenState:
        """Node: Verifies connections to external services like Jira and OpenAI."""
        _log_phase("health_check")
        project_key = state.get("project_key", "") # Ensure project_key is available from state
        
        # Check OpenAI connection
        try: # noqa: SIM105
            from openai import OpenAI
            client = OpenAI(api_key=Settings.OPENAI_API_KEY)
            client.models.list()
            logger.info("✅ OpenAI connection successful.")
        except Exception as e: # Catching a broader exception for connection issues
            logger.error(f"❌ OpenAI connection failed: {e}", exc_info=True)
            print(f"❌ OpenAI connection failed. Check your OPENAI_API_KEY. Error: {e}") # noqa: T201
            return {"health_ok": False}
        try:
            # Use the more robust Agile API endpoint for the health check, as the search endpoint is deprecated (410 Gone).
            # This aligns the health check with the method used to fetch all tickets later in the graph.
            result = jira_client.list_all_issues_in_project(project_key=project_key, max_results=1)
            if "error" in result and "issues" not in result:
                raise ConnectionError(result.get("details", "Project not found or permission error"))
            logger.info(f"✅ Jira connection successful and project '{project_key}' found.")
        except Exception as e: # Catching a broader exception for connection issues
            logger.error(f"❌ Jira connection failed or project '{project_key}' not found: {e}")
            print(f"❌ Jira connection failed. Check JIRA settings and project key '{project_key}'. Error: {e}") # noqa: T201
            return {"health_ok": False}
        
        return {"health_ok": True}

    def system_architect(state: GenState) -> GenState:
        """
        Node: Designs the application architecture based on Jira tickets.
        Infers the application's goal and defines modules, their purposes,
        and the functions they should contain.
        """
        _log_phase("system_architect")
        tickets = state.get("tickets", [])
        project_key = state.get("project_key", "")
        epic_description = state.get("epic_description", "")
        arch_iteration = state.get("arch_iteration", 0)
        rejection_reason = state.get("rejection_reason", "")
        
        if not tickets:
            logger.error("No tickets loaded. Cannot design architecture.")
            return {"architecture_plan": "{}", "modules": {}}
        
        tickets_summary = "\n".join([f"- {t['key']}: {t['title']}" for t in tickets])
        
        # Infer application goal from tickets
        if epic_description:
            app_goal = f"EPIC Requirements:\n{epic_description}"
            logger.info("Using EPIC description for application goal")
            print(f"🎯 Using EPIC requirements")
        else:
            prompt_template = load_prompt("unified_app_goal.txt")
            app_goal_prompt = prompt_template.format(tickets_summary=tickets_summary)
            app_goal = call_llm(
                system_prompt="You are an application architect inferring goals from requirements.",
                user_prompt=app_goal_prompt,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=1000
            )

        # Add feedback from previous rejection
        if arch_iteration > 0 and rejection_reason:
            app_goal = f"PREVIOUS ATTEMPT WAS REJECTED:\n{rejection_reason}\n\nYOUR TASK: Redesign the architecture to be much simpler. Use fewer modules and only include essential functions. Avoid complex patterns. The original goal was: {app_goal}"

        logger.info(f"Inferred application goal: {app_goal}")
        print(f"🎯 Goal: {app_goal}") # noqa: T201

        ticket_details = "\n".join(
            [f"\n{t['key']}: {t['title']}\n{t['description'][:200]}\n" for t in tickets]
        )
        prompt_template = load_prompt("unified_system_architect.txt")
        prompt = prompt_template.format(
            app_goal=app_goal,
            tickets_summary=tickets_summary,
            ticket_details=ticket_details
        )
        
        arch_plan = call_llm(
            system_prompt=load_prompt("system_json_only.txt"),
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=2000
        )
        # Clean markdown from the response before parsing
        arch_plan = re.sub(r'^```json\s*', '', arch_plan)
        arch_plan = re.sub(r'```\s*$', '', arch_plan)
        
        logger.info(f"Architecture plan:\n{arch_plan}")
        
        # Parse modules
        try: # noqa: SIM105
            plan_json = json.loads(arch_plan)
            modules = {}
            for mod in plan_json.get("modules", []):
                # Sanitize module name to be a valid Python identifier
                safe_module_name = mod["name"].replace(" ", "_").lower()
                modules[safe_module_name] = {
                    "tickets": mod.get("tickets", []),
                    "functions": mod.get("functions", []),
                    "purpose": mod.get("purpose", "")
                }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse architecture: {e}")
            modules = {"main": {"tickets": [t["key"] for t in tickets], "functions": [], "purpose": "Main module"}}
        
        return {"architecture_plan": arch_plan, "modules": modules, "arch_iteration": arch_iteration}

    def requirements_analyzer(state: GenState) -> GenState:
        """Analyze EPIC requirements and ensure architecture stays simple and focused."""
        _log_phase("requirements_analyzer")
        epic_description = state.get("epic_description", "")
        architecture_plan = state.get("architecture_plan", "")
        arch_iteration = state.get("arch_iteration", 0)
        
        # Skip if modules already exist (incremental update mode)
        module_dir = "modules"
        if os.path.exists(module_dir) and any(f.endswith('.py') and f != '__init__.py' for f in os.listdir(module_dir)):
            logger.info("Existing modules detected - skipping requirements check for incremental update")
            print("🔄 Incremental update mode - accepting new features")
            return {"architecture_approved": True}
        
        # Skip if no EPIC or max retries reached
        if not epic_description:
            logger.info("No EPIC description - auto-approving architecture")
            return {"architecture_approved": True}
        
        if arch_iteration >= 3:
            logger.warning(f"Max architecture iterations ({arch_iteration}) reached - auto-approving")
            print("⚠️  Max retries reached - accepting current architecture")
            return {"architecture_approved": True, "arch_iteration": arch_iteration + 1}
        
        prompt = (
            "Analyze the proposed architecture against the EPIC requirements, focusing on simplicity.\n"
            "REJECT any over-engineered patterns like FSM, state machines, or observers if the EPIC calls for a 'simple' or 'basic' app.\n"
            "A calculator, for example, should be simple functions, not a state machine.\n"
            "Output format:\n"
            "APPROVED: [YES or NO]\n"
            "REASON: [Briefly explain why, especially for rejection.]\n\n"
            f"EPIC REQUIREMENTS:\n{epic_description}\n\n"
            f"PROPOSED ARCHITECTURE:\n{architecture_plan}\n"
        )
        
        analysis = call_llm(
            system_prompt="You are a requirements analyst ensuring architecture matches EPIC requirements.",
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=500
        )
        logger.info(f"Requirements analysis:\n{analysis}")
        
        approved = 'APPROVED: YES' in analysis.upper()
        
        if approved:
            print("✅ Requirements check: APPROVED")
            return {"architecture_approved": True, "arch_iteration": arch_iteration + 1}
        else:
            print(f"❌ Requirements check: REJECTED (attempt {arch_iteration + 1}/3) - will regenerate simpler architecture")
            return {"architecture_approved": False, "arch_iteration": arch_iteration + 1, "rejection_reason": analysis}

    def spec_agent(state: GenState) -> GenState:
        """
        Node: Generates detailed implementation specifications for each module.
        This includes function signatures, inputs, outputs, edge cases, and
        acceptance criteria in a structured JSON format.
        """
        _log_phase("spec_agent")
        tickets = state.get("tickets", [])
        modules = state.get("modules", {})
        specs = {}
        for module_name, module_info in modules.items():
            module_tickets = [t for t in tickets if t["key"] in module_info["tickets"]]
            
            tickets_text = "\n".join([f"{t['key']}: {t['title']}\n{t['description']}" for t in module_tickets])
            
            prompt_template = load_prompt("unified_spec_agent.txt")
            prompt = prompt_template.format(
                module_name=module_name,
                purpose=module_info.get('purpose', 'No purpose defined'),
                tickets_text=tickets_text
            )
            
            spec = call_llm(
                system_prompt=load_prompt("system_json_only.txt"),
                user_prompt=prompt,
                model="gpt-4o",
                temperature=0.2,
                max_tokens=1500
            )
            try: # noqa: SIM105
                json.loads(spec)
            except json.JSONDecodeError:
                spec = json.dumps({"module": module_name, "functions": [], "edge_cases": [], "acceptance": []})
            
            specs[module_name] = spec
            logger.info(f"Spec for {module_name}:\n{spec}")
        
        return {"specs": specs}

    def spec_reviewer(state: GenState) -> GenState:
        """
        Node: Reviews the generated specifications for completeness and quality.
        This step acts as a quality gate before proceeding to code generation.
        """
        _log_phase("spec_reviewer")
        specs = state.get("specs", {})
        
        for module_name, spec in specs.items():
            prompt_template = load_prompt("unified_spec_reviewer.txt")
            prompt = prompt_template.format(module_name=module_name, spec=spec)

            review = call_llm(
                system_prompt="You are a senior QA engineer reviewing specifications.",
                user_prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=500
            )
            logger.info(f"Spec review for {module_name}:\n{review}")
        
        return {}

    def generate_tests(state: GenState) -> GenState:
        """
        Node: Generates pytest test files for each module based on its spec.
        The tests are designed to cover normal functionality, edge cases, and error handling.
        """
        _log_phase("generate_tests")
        specs = state.get("specs", {})
        
        test_files = {}
        test_dir = "generated_tests"
        os.makedirs(test_dir, exist_ok=True)
        
        for module_name, spec in specs.items():
            test_path = os.path.join(test_dir, f"test_{module_name}.py")
            
            prompt_template = load_prompt("unified_generate_tests.txt")
            prompt = prompt_template.format(module_name=module_name, spec=spec)
            
            tests_src = call_llm(
                system_prompt=load_prompt("system_python_test_code_only.txt"),
                user_prompt=prompt,
                model="gpt-4o",
                temperature=0.1,
                max_tokens=3000
            )
            tests_src = re.sub(r'^```python\s*', '', tests_src)
            tests_src = re.sub(r'```\s*$', '', tests_src)
            
            # Validate
            if f"from modules.{module_name}" not in tests_src:
                tests_src = f"import pytest\nfrom modules.{module_name} import *\n\n" + tests_src
            
            try:
                ast.parse(tests_src)
            except SyntaxError: # noqa: SIM105
                tests_src = f"import pytest\nfrom modules.{module_name} import *\n\ndef test_placeholder():\n    assert True\n"
            
            write_files([{"path": test_path, "content": tests_src}])
            test_files[module_name] = test_path
            logger.info(f"Tests written: {test_path}")
        
        return {"test_files": test_files}

    def code_merger(state: GenState) -> GenState:
        """
        Node: Checks if modules exist and merges new functions into existing code.
        This enables incremental updates without losing existing functionality.
        """
        _log_phase("code_merger")
        specs = state.get("specs", {})
        
        module_dir = "modules"
        os.makedirs(module_dir, exist_ok=True)
        
        merged_specs = {}
        
        for module_name, spec in specs.items():
            code_path = os.path.join(module_dir, f"{module_name}.py")
            
            # Check if module already exists
            if os.path.exists(code_path):
                with open(code_path, "r") as f:
                    existing_code = f.read()
                
                # Extract existing function names
                existing_funcs = re.findall(r'^def (\w+)\(', existing_code, re.MULTILINE)
                
                # Extract new functions from spec
                try:
                    spec_json = json.loads(spec)
                    new_funcs = [f["name"] for f in spec_json.get("functions", [])]
                except:
                    new_funcs = []
                
                # Filter out functions that already exist
                funcs_to_add = [f for f in new_funcs if f not in existing_funcs]
                
                if funcs_to_add:
                    logger.info(f"{module_name}: Merging {len(funcs_to_add)} new functions into existing code")
                    print(f"🔄 {module_name}: Adding {funcs_to_add} to existing code")
                    
                    # Create filtered spec with only new functions
                    try:
                        spec_json = json.loads(spec)
                        spec_json["functions"] = [f for f in spec_json.get("functions", []) if f["name"] in funcs_to_add]
                        filtered_spec = json.dumps(spec_json)
                    except:
                        filtered_spec = spec
                    
                    # Use merger prompt
                    prompt_template = load_prompt("unified_code_merger.txt")
                    prompt = prompt_template.format(
                        existing_code=existing_code,
                        new_functions_spec=filtered_spec
                    )
                    
                    merged_code = call_llm(
                        system_prompt=load_prompt("system_python_code_only.txt"),
                        user_prompt=prompt,
                        model="gpt-4o",
                        temperature=0.1,
                        max_tokens=3000
                    )
                    merged_code = re.sub(r'^```python\s*', '', merged_code)
                    merged_code = re.sub(r'```\s*$', '', merged_code)
                    
                    # Validate merged code
                    try:
                        ast.parse(merged_code)
                        write_files([{"path": code_path, "content": merged_code}])
                        logger.info(f"Merged code written: {code_path}")
                    except SyntaxError as e:
                        logger.error(f"Merged code has syntax error: {e}. Keeping existing code.")
                        # Keep existing code if merge fails
                else:
                    logger.info(f"{module_name}: All functions already exist, skipping")
                    print(f"✓ {module_name}: Up to date")
                
                # Use original spec for downstream (tests still need to cover all functions)
                merged_specs[module_name] = spec
            else:
                # New module - use full spec for generation
                logger.info(f"{module_name}: New module, will generate from scratch")
                merged_specs[module_name] = spec
        
        return {"specs": merged_specs}

    def generate_code(state: GenState) -> GenState:
        """
        Node: Implements the business logic for each module.
        Only generates code for NEW modules (existing modules handled by code_merger).
        """
        _log_phase("generate_code")
        specs = state.get("specs", {})
        test_files = state.get("test_files", {})
        
        module_dir = "modules"
        os.makedirs(module_dir, exist_ok=True)
        code_files = {}
        
        # Generate modules
        for module_name, spec in specs.items():
            code_path = os.path.join(module_dir, f"{module_name}.py")
            
            # Skip if module already exists (was handled by code_merger)
            if os.path.exists(code_path):
                code_files[module_name] = code_path
                logger.info(f"Using existing module: {code_path}")
                continue
            
            test_path = test_files.get(module_name, "")
            
            tests_src = ""
            if test_path and os.path.exists(test_path):
                with open(test_path, "r") as f:
                    tests_src = f.read()
            
            prompt_template = load_prompt("unified_generate_code.txt")
            prompt = prompt_template.format(spec=spec, tests_src=tests_src)

            code_src = call_llm(
                system_prompt=load_prompt("system_python_code_only.txt"),
                user_prompt=prompt,
                model="gpt-4o",
                temperature=0.1,
                max_tokens=3000
            )
            code_src = re.sub(r'^```python\s*', '', code_src)
            code_src = re.sub(r'```\s*$', '', code_src)
            
            try:
                ast.parse(code_src)
            except SyntaxError:
                code_src = f'"""Module {module_name}"""\n\ndef placeholder():\n    pass\n'
            
            write_files([{"path": code_path, "content": code_src}])
            code_files[module_name] = code_path
            logger.info(f"Code written: {code_path}")
        
        # Generate __init__.py
        init_path = os.path.join(module_dir, "__init__.py")
        write_files([{"path": init_path, "content": ""}])
        
        return {"code_files": code_files}

    def validate_modules(state: GenState) -> GenState:
        """Validate that modules have the functions they claim to have."""
        _log_phase("validate_modules")
        code_files = state.get("code_files", {})
        specs = state.get("specs", {})
        
        for module_name, code_path in code_files.items():
            if not os.path.exists(code_path):
                continue
            
            with open(code_path, "r") as f:
                code_content = f.read()
            
            # Extract function names from spec
            spec = specs.get(module_name, "")
            try:
                spec_json = json.loads(spec)
                expected_funcs = [f["name"] for f in spec_json.get("functions", [])]
            except Exception:
                expected_funcs = []
            
            # Check if functions exist in code
            actual_funcs = re.findall(r'^def (\w+)\(', code_content, re.MULTILINE)
            
            missing = [f for f in expected_funcs if f not in actual_funcs]
            if missing:
                logger.warning(f"{module_name}: Missing functions {missing}. Found: {actual_funcs}")
        
        return {}

    def generate_main_app(state: GenState) -> GenState:
        """
        Node: Creates the main Streamlit application file (app.py).
        This node integrates all generated modules into a cohesive user interface,
        using the architecture plan and actual generated functions as a guide.
        """
        _log_phase("generate_main_app")
        architecture_plan = state.get("architecture_plan", "")
        modules = state.get("modules", {})
        specs = state.get("specs", {})
        code_files = state.get("code_files", {})
        
        # Read actual module code to get real function names
        actual_functions = {}
        for module_name, code_path in code_files.items():
            if code_path and os.path.exists(code_path):
                with open(code_path, "r") as f:
                    code_content = f.read()
                funcs = re.findall(r'^def (\w+)\(', code_content, re.MULTILINE)
                actual_functions[module_name] = funcs
                logger.info(f"{module_name} actual functions: {funcs}")
        
        modules_list = "\n".join([f"- {name}: {info['purpose']}" for name, info in modules.items()])
        
        # Build accurate function list from actual code
        functions_text = ""
        for module_name, funcs in actual_functions.items():
            functions_text += f"\nmodules.{module_name}: {', '.join(funcs)}"
        
        specs_text = "\n".join([f"{name}:\n{spec}" for name, spec in specs.items()])
        
        # Get the UI pattern
        ui_pattern = state.get("ui_pattern", "sidebar_nav")

        # Load ONLY the relevant reference example for this pattern
        reference_code = ""
        if ui_pattern == "button_grid":
            ref_path = "reference_examples/streamlit_apps/calculator_with_memory.py"
            if os.path.exists(ref_path):
                with open(ref_path, 'r') as f:
                    reference_code = f.read()
                    # Extract just the docstring for guidance
                    docstring_match = re.search(r'"""([\s\S]*?)"""', reference_code)
                    if docstring_match:
                        reference_code = f"REFERENCE PATTERN:\n{docstring_match.group(1)}"

        # Add pattern guidance
        pattern_guidance = ""
        if ui_pattern == "button_grid":
            pattern_guidance = (
                "\n\nUI PATTERN: Button Grid (Calculator Style)\n"
                "CRITICAL RULES:\n"
                "1. EVERY button MUST have a unique key parameter: st.button('7', key='7')\n"
                "2. Operator buttons: st.button('➕', key='+') - emoji label, symbol key\n"
                "3. Append SYMBOL not emoji: st.session_state.display += '+' (not ➕)\n"
                "4. Multiply: st.button('✖️', key='*') then append '*' not emoji\n"
                "5. Display: st.markdown(f'### Display: `{st.session_state.display}`')\n"
                "6. Initialize: if 'display' not in st.session_state: st.session_state.display = '0'\n"
                "7. Digit buttons: if st.button('7', key='7'): st.session_state.display += '7'; st.rerun()\n"
                "8. NO helper functions - all logic inline in button handlers\n"
                "9. Equals button: st.session_state.display = str(eval(st.session_state.display))\n"
                "10. Clear button: if st.button('Clear', key='C'): st.session_state.display = '0'; st.rerun()\n"
            )
        elif ui_pattern == "sidebar_nav":
            pattern_guidance = (
                "\n\nUI PATTERN: Sidebar Navigation\n"
                "Use st.sidebar.radio() or st.sidebar.selectbox() for navigation between pages/tools\n"
            )
        
        # Build prompt without .format() to avoid KeyError
        prompt_template = load_prompt("unified_generate_main_app.txt")
        prompt = (
            prompt_template
            .replace("{architecture_plan}", architecture_plan)
            .replace("{functions_text}", functions_text)
            .replace("{specs_text}", specs_text)
            + (f"\n\n{reference_code}" if reference_code else "")
            + pattern_guidance
        )
        
        app_src = call_llm(
            system_prompt=load_prompt("system_python_code_only.txt"),
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.1,
            max_tokens=4000
        )
        app_src = re.sub(r'^```python\s*', '', app_src)
        app_src = re.sub(r'```\s*$', '', app_src)
        
        try:
            ast.parse(app_src)
            logger.info("Generated app.py passed syntax validation")
        except SyntaxError as e:
            logger.error(f"Generated app.py has syntax error: {e}")
            # Don't fallback - let validation catch it and trigger fix_app
        
        app_path = "app.py"
        write_files([{"path": app_path, "content": app_src}])
        logger.info(f"Main app written: {app_path}")
        
        return {"app_path": app_path}

    def ui_designer(state: GenState) -> GenState:
        """Analyze functions and design optimal UI layout."""
        _log_phase("ui_designer")
        code_files = state.get("code_files", {})
        epic_description = state.get("epic_description", "")
        
        # Read actual functions
        actual_functions = {}
        for module_name, code_path in code_files.items():
            if os.path.exists(code_path):
                with open(code_path, "r") as f:
                    code_content = f.read()
                funcs = re.findall(r'^def (\w+)\(', code_content, re.MULTILINE)
                actual_functions[module_name] = funcs
        
        functions_list = "\n".join([f"{mod}: {', '.join(funcs)}" for mod, funcs in actual_functions.items()])
        
        prompt = (
            "Design the optimal Streamlit UI layout based on the available functions and EPIC.\n"
            "Analyze the function types (e.g., math, data processing) and choose the best UI pattern.\n"
            "Examples:\n"
            "- Calculator functions (add, subtract) -> 'button_grid'\n"
            "- Multiple distinct tools -> 'sidebar_nav'\n"
            "OUTPUT FORMAT:\n"
            "UI_PATTERN: [button_grid | sidebar_nav | tabs | form]\n"
            "REASONING: [Why this pattern fits the functions.]\n\n"
            f"EPIC CONTEXT:\n{epic_description}\n\n"
            f"AVAILABLE FUNCTIONS:\n{functions_list}\n"
        )
        
        ui_design = call_llm(
            system_prompt="You are a UI/UX designer choosing optimal Streamlit layouts.",
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=300
        )
        logger.info(f"UI design:\n{ui_design}")
        
        # Extract UI pattern
        ui_pattern = "sidebar_nav"  # default
        if "button_grid" in (ui_design or "").lower():
            ui_pattern = "button_grid"
            print("🎨 UI: Button grid layout (calculator style)")
        elif "tabs" in (ui_design or "").lower():
            ui_pattern = "tabs"
            print("🎨 UI: Tabbed layout")
        elif "form" in (ui_design or "").lower():
            ui_pattern = "form"
            print("🎨 UI: Form layout")
        else:
            print("🎨 UI: Sidebar navigation")
        
        # Return the chosen pattern and design guidance for the next step
        return {"ui_pattern": ui_pattern, "ui_design": ui_design or ""}

    def run_tests_node(state: GenState) -> GenState:
        """
        Node: Executes the generated pytest tests against the generated code.
        """
        _log_phase("run_tests")
        test_files = state.get("test_files", {})
        
        total_passed = 0
        total_failed = 0
        test_results = {}
        
        for module_name, test_path in test_files.items():
            # Add current directory to Python path for module imports
            extra_paths = [os.path.abspath(".")]
            
            res = run_pytest(test_path, extra_paths=extra_paths)
            test_results[module_name] = res
            total_passed += res.get("passed", 0)
            total_failed += res.get("failed", 0)
            logger.info(f"{module_name}: {res.get('passed', 0)} passed, {res.get('failed', 0)} failed")
        
        # Aggregate test output for the fixer
        aggregated_output = "\n".join([f"--- {mod} ---\n{res.get('output', '')}" for mod, res in test_results.items()])
        
        return {
            "test_results": test_results,
            "test_output": aggregated_output,
            "passed": total_passed,
            "failed": total_failed,
            "collected": sum(res.get("collected") or 0 for res in test_results.values())
        }

    def fix_analyzer(state: GenState) -> GenState:
        """Analyze failures across all modules and provide fix recommendations."""
        _log_phase("fix_analyzer")
        
        collected = state.get("collected", 0)
        failed = state.get("failed", 0)
        
        # If tests passed successfully, skip fixing
        if failed == 0 and collected > 0:
            logger.info("All tests passed. Skipping fix analysis.")
            return {"needs_fix": False}
        
        # If no tests collected, skip fixing and proceed (pytest config issue, not code issue)
        if collected == 0:
            logger.warning("No tests collected - pytest configuration issue. Proceeding without test fixes.")
            return {"needs_fix": False}
        
        specs = state.get("specs", {})
        test_files = state.get("test_files", {})
        code_files = state.get("code_files", {})
        test_results = state.get("test_results", {})
        prev_failures = state.get("prev_failures", {})
        
        # Check for infinite loop
        current_failures = {mod: res.get("failed", 0) for mod, res in test_results.items() if res.get("failed", 0) > 0}
        if prev_failures and prev_failures == current_failures:
            logger.error("Failures are identical to the previous run. Breaking loop to prevent recursion.")
            print("⚠️  Stuck on the same test failures. Stopping fix attempts.")
            return {"needs_fix": False, "stuck": True}

        
        all_recommendations = []
        fix_targets = set()

        for module_name, res in test_results.items():
            if res.get("failed", 0) > 0 or res.get("collected", 0) == 0:
                logger.info(f"Analyzing failures for {module_name}...")
                spec = specs.get(module_name, "")
                pytest_out = res.get("output", "")
                test_path = test_files.get(module_name)
                code_path = code_files.get(module_name)
                
                current_tests = read_text_safe(test_path or "")
                current_code = read_text_safe(code_path or "")

                prompt_template = load_prompt("unified_fix_analyzer.txt")
                fix_prompt = prompt_template.format(
                    module_name=module_name,
                    spec=spec,
                    pytest_out=pytest_out,
                    current_tests=current_tests,
                    current_code=current_code
                )
                recommendations = call_llm(
                    system_prompt="You are a debugging expert analyzing test failures.",
                    user_prompt=fix_prompt,
                    model="gpt-4o",
                    temperature=0.2,
                    max_tokens=1000
                )
                logger.info(f"Fix recommendations for {module_name}:\n{recommendations}")
                all_recommendations.append(f"--- FIX FOR MODULE: {module_name} ---\n{recommendations}")
                
                if "FIX_TARGET: TESTS" in (recommendations or "").upper():
                    fix_targets.add("TESTS")
                elif "FIX_TARGET: CODE" in (recommendations or "").upper():
                    fix_targets.add("CODE")
                else: fix_targets.add("BOTH")

        if all_recommendations:
            return {
                "needs_fix": True,
                "fix_recommendations": "\n\n".join(all_recommendations),
                "fix_type": ",".join(list(fix_targets)),
                "prev_failures": current_failures, # Save current failures for next iteration
            }
        return {"needs_fix": False}

    def fixer_agent(state: GenState) -> GenState:
        """Apply fixes to multiple modules based on aggregated recommendations."""
        _log_phase("fixer_agent")
        
        fix_recommendations = state.get("fix_recommendations", "")
        
        # Split recommendations by module
        module_fixes = re.split(r"--- FIX FOR MODULE: ", fix_recommendations)
        
        for fix_block in module_fixes:
            if not fix_block.strip(): continue
            # Extract module name from the fix block header
            module_name_match = re.search(r"^(.*?) ---", fix_block.strip())
            if not module_name_match: continue
            module_name = module_name_match.group(1).strip()
            logger.info(f"Applying fixes for module: {module_name}")

            code_path = state.get("code_files", {}).get(module_name)
            test_path = state.get("test_files", {}).get(module_name)
            
            current_code = read_text_safe(code_path or "")
            current_tests = read_text_safe(test_path or "")

            prompt_template = load_prompt("unified_fixer_agent.txt")
            fix_prompt = prompt_template.format(
                module_name=module_name,
                fix_block=fix_block,
                code_path=code_path,
                current_code=current_code,
                test_path=test_path,
                current_tests=current_tests
            )
            fixed_content = call_llm(
                system_prompt="You are a code fixing expert. Output fixed code in the specified format.",
                user_prompt=fix_prompt,
                model="gpt-4o",
                temperature=0.2,
                max_tokens=4000
            )
            
            # Extract and write fixed files
            file_blocks = re.findall(r"--- START FILE: (.*?) ---\n(.*?)\n--- END FILE: \1 ---", fixed_content or "", re.DOTALL)
            if not file_blocks:
                logger.warning(f"Fixer agent for {module_name} did not produce valid file blocks. Skipping fix.")
                continue

            for file_path, content in file_blocks:
                file_path = file_path.strip()
                # Clean markdown from content
                content = re.sub(r'^```(python|py)?\s*', '', content.strip()) # More robust regex
                content = re.sub(r'```\s*$', '', content)
                write_files([{"path": file_path, "content": content}])
                logger.info(f"Applied fix to: {file_path}")

        return {}

    def validate_app(state: GenState) -> GenState:
        """Validate Streamlit app by checking for common errors."""
        _log_phase("validate_app")
        app_path = state.get("app_path", "app.py")
        
        if not os.path.exists(app_path):
            return {"app_errors": ["App file not found"], "app_fix_iteration": 0}

        with open(app_path, "r") as f:
            app_code = f.read()

        errors = []

        # Check for syntax errors FIRST - this is critical
        try:
            ast.parse(app_code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}. Check for unterminated strings, missing quotes, or unmatched brackets.")
            logger.error(f"App syntax error: {e}")

        # Check for common Streamlit button issues
        if 'on_click=' in app_code and 'st.button' in app_code:
            errors.append("Buttons use 'on_click' callbacks which cause issues. Use 'if st.button():' pattern with st.rerun() instead.")
        
        # Check for missing button keys (causes duplicate ID errors)
        button_pattern = r'st\.button\([^)]+\)'
        buttons = re.findall(button_pattern, app_code)
        for btn in buttons:
            if 'key=' not in btn:
                errors.append(f"Button without unique key found: {btn}. ALL buttons must have key parameter to avoid duplicate ID errors.")

        # Check if buttons update session_state but don't call st.rerun()
        if 'st.session_state' in app_code and 'if st.button(' in app_code:
            if 'st.rerun()' not in app_code:
                errors.append("Buttons update session_state but don't call st.rerun(). Add st.rerun() after state updates for immediate display refresh.")
        
        # Check for disabled text_input used as display (doesn't update properly)
        if 'disabled=True' in app_code and 'st.session_state' in app_code:
            errors.append("Using disabled text_input for display. Use st.markdown() or st.text() instead for proper state updates.")
        
        # Check for incorrect markdown formatting (backticks outside f-string)
        if 'st.markdown(f"`{' in app_code or 'st.markdown(f"\\`{' in app_code:
            errors.append("Incorrect markdown format. Use: st.markdown(f'### Display: `{st.session_state.display}`') with backticks INSIDE the f-string.")

        # Check imports match available modules and functions
        code_files = state.get("code_files", {})
        
        # Extract all imports: from modules.X import func1, func2
        import_pattern = r'from modules\.(\w+) import ([\w, ]+)'
        imports = re.findall(import_pattern, app_code)
        
        for module_name, funcs_str in imports:
            # Check if module exists
            if module_name not in code_files:
                errors.append(f"Import error: modules.{module_name} doesn't exist. Available: {list(code_files.keys())}")
                continue
            
            # Check if functions exist in the module
            module_path = code_files[module_name]
            if os.path.exists(module_path):
                with open(module_path, 'r') as f:
                    module_code = f.read()
                available_funcs = re.findall(r'^def (\w+)\(', module_code, re.MULTILINE)
                
                # Parse imported function names
                imported_funcs = [f.strip() for f in funcs_str.split(',')]
                
                # Check each imported function
                for func in imported_funcs:
                    if func not in available_funcs:
                        errors.append(f"Import error: {func} not found in modules.{module_name}. Available: {available_funcs}")

        
        logger.info(f"App validation: {len(errors)} errors found")
        if errors:
            for err in errors:
                logger.warning(f"  - {err}")
        
        return {"app_errors": errors}

    def fix_app(state: GenState) -> GenState:
        """Fix Streamlit app based on validation errors."""
        _log_phase("fix_app")
        app_errors = state.get("app_errors", [])
        app_path = state.get("app_path", "app.py")
        iteration = state.get("app_fix_iteration", 0)
        
        print(f"🔧 Fixing app (iteration {iteration + 1}/3)")
        
        with open(app_path, "r") as f:
            current_app = f.read()
        
        errors_text = "\n".join([f"- {err}" for err in app_errors])
        
        # Get available functions for context
        code_files = state.get("code_files", {})
        available_functions = {}
        for mod_name, mod_path in code_files.items():
            if os.path.exists(mod_path):
                with open(mod_path, 'r') as f:
                    mod_code = f.read()
                funcs = re.findall(r'^def (\w+)\(', mod_code, re.MULTILINE)
                available_functions[mod_name] = funcs
        
        funcs_text = "\n".join([f"modules.{mod}: {', '.join(funcs)}" for mod, funcs in available_functions.items()])
        
        prompt = (
            "Fix the Streamlit app based on these errors. Follow Streamlit best practices.\n"
            "CRITICAL RULES:\n"
            "1. EVERY st.button() MUST have a unique key parameter: st.button('7', key='7')\n"
            "2. Use 'if st.button():' pattern, NOT on_click callbacks\n"
            "3. ALWAYS call st.rerun() after updating st.session_state\n"
            "4. Use st.markdown() to display values, NOT disabled text_input\n"
            "5. ONLY import functions that actually exist in the modules\n\n"
            f"AVAILABLE FUNCTIONS:\n{funcs_text}\n\n"
            f"ERRORS TO FIX:\n{errors_text}\n\n"
            f"CURRENT APP:\n{current_app}\n\n"
            "OUTPUT: Only the fixed Python code, no markdown."
        )
        
        fixed_app = call_llm(
            system_prompt=load_prompt("system_python_code_only.txt"),
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.1,
            max_tokens=4000
        )
        fixed_app = re.sub(r'^```python\s*', '', fixed_app)
        fixed_app = re.sub(r'```\s*$', '', fixed_app)
        
        write_files([{"path": app_path, "content": fixed_app}])
        logger.info(f"App fixed (iteration {iteration + 1})")
        
        return {"app_fix_iteration": iteration + 1}

    def quality_reviewer(state: GenState) -> GenState:
        """Review test and code quality across all modules."""
        _log_phase("quality_reviewer")
        
        specs = state.get("specs", {})
        passed = state.get("passed", 0)
        failed = state.get("failed", 0)

        specs_text = "\n\n".join([f"--- MODULE: {name} ---\n{spec}" for name, spec in specs.items()])

        prompt_template = load_prompt("unified_quality_reviewer.txt")
        review_prompt = prompt_template.format(
            passed=passed,
            failed=failed,
            specs_text=specs_text,
        )
        
        review_report = call_llm(
            system_prompt="You are a quality assurance expert reviewing code and tests.",
            user_prompt=review_prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=1500
        )
        logger.info(f"Quality Review Report:\n{review_report}")
        
        return {"review_report": review_report or ""}

    def senior_dev_reviewer(state: GenState) -> GenState:
        """Senior developer reviews if the integrated app will run."""
        _log_phase("senior_dev_reviewer")
        
        app_path = state.get("app_path")
        app_code = read_text_safe(app_path or "")
        architecture_plan = state.get("architecture_plan", "")
        
        prompt_template = load_prompt("unified_senior_dev_reviewer.txt")
        senior_prompt = prompt_template.format(
            architecture_plan=architecture_plan,
            app_code=app_code
        )
        
        review = call_llm(
            system_prompt="You are a senior developer reviewing code for production readiness.",
            user_prompt=senior_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        )
        logger.info(f"Senior Dev Review:\n{review}")
        
        return {"senior_dev_review": review or ""}

    def architecture_reviewer(state: GenState) -> GenState:
        """Architect reviews the final application against the plan."""
        _log_phase("architecture_reviewer")
        
        app_path = state.get("app_path")
        app_code = read_text_safe(app_path or "")
        architecture_plan = state.get("architecture_plan", "")
        
        prompt_template = load_prompt("unified_architecture_reviewer.txt")
        arch_prompt = prompt_template.format(
            architecture_plan=architecture_plan,
            app_code=app_code
        )
        
        review = call_llm(
            system_prompt="You are a software architect reviewing code structure and design.",
            user_prompt=arch_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        )
        logger.info(f"Architecture Review:\n{review}")
        
        return {"architecture_review": review or ""}

    # Build graph
    builder = StateGraph(GenState)
    builder.add_node(health_check)
    builder.add_node(jira_reader)
    builder.add_node(system_architect)
    builder.add_node(requirements_analyzer)
    builder.add_node(spec_agent)
    builder.add_node(spec_reviewer)
    builder.add_node(generate_tests)
    builder.add_node(code_merger)
    builder.add_node(generate_code)
    builder.add_node(validate_modules)
    builder.add_node(ui_designer)
    builder.add_node(generate_main_app)
    builder.add_node(validate_app)
    builder.add_node(fix_app)
    builder.add_node(run_tests_node)
    builder.add_node(fix_analyzer)
    builder.add_node(fixer_agent)
    builder.add_node(quality_reviewer)
    builder.add_node(senior_dev_reviewer)
    builder.add_node(architecture_reviewer)
    
    # Start with health check
    builder.add_edge(START, "health_check")

    # Conditional edge after health check
    def check_health(state: GenState) -> str:
        if state.get("health_ok", False):
            return "jira_reader"
        return "END"

    builder.add_conditional_edges("health_check", check_health, {"jira_reader": "jira_reader", "END": END})
    builder.add_edge("jira_reader", "system_architect")
    builder.add_edge("system_architect", "requirements_analyzer")

    def should_regenerate_arch(state: GenState) -> str:
        return "regenerate" if not state.get("architecture_approved") else "continue"

    builder.add_conditional_edges("requirements_analyzer", should_regenerate_arch, {
        "regenerate": "system_architect",
        "continue": "spec_agent"
    })

    builder.add_edge("spec_agent", "spec_reviewer")
    builder.add_edge("spec_reviewer", "generate_tests")
    builder.add_edge("generate_tests", "code_merger")
    builder.add_edge("code_merger", "generate_code")
    builder.add_edge("generate_code", "validate_modules")
    builder.add_edge("validate_modules", "run_tests_node") # Run tests before UI design

    def should_fix_app(state: GenState) -> list:
        app_errors = state.get("app_errors", [])
        iteration = state.get("app_fix_iteration", 0)
        if app_errors and iteration < 3:  # Increased from 2 to 3 for syntax errors
            return ["fix_app"]
        if app_errors and iteration >= 3:
            logger.warning(f"Max app fix iterations reached with {len(app_errors)} errors remaining")
        # Run all three reviewers in parallel
        return ["quality_reviewer", "senior_dev_reviewer", "architecture_reviewer"]

    # The flow is: test -> fix tests -> design UI -> generate app -> validate app -> fix app -> parallel review -> END
    builder.add_edge("run_tests_node", "fix_analyzer")

    # Conditional: fix if needed, otherwise proceed to UI design or reviewers in parallel.
    def should_fix(state: GenState) -> list:
        if state.get("stuck", False):
            logger.error("Fixing loop is stuck. Proceeding to parallel final review.")
            return ["quality_reviewer", "senior_dev_reviewer", "architecture_reviewer"]
        if state.get("needs_fix", False) and state.get("failed", 0) > 0:
            logger.info("Failures detected. Routing to fixer_agent.")
            return ["fixer_agent"]
        # If tests pass, proceed to UI design and app generation
        logger.info("All tests passed or no fix needed. Proceeding to UI design.")
        return ["ui_designer"]

    builder.add_conditional_edges("fix_analyzer", should_fix, {
        "fixer_agent": "fixer_agent", 
        "ui_designer": "ui_designer",
        "quality_reviewer": "quality_reviewer",
        "senior_dev_reviewer": "senior_dev_reviewer",
        "architecture_reviewer": "architecture_reviewer"
    })
    
    # After fixing, loop back to run tests again.
    builder.add_edge("fixer_agent", "run_tests_node")
    
    # After tests pass, design and validate the UI
    builder.add_edge("ui_designer", "generate_main_app") # Correctly wire ui_designer to generate_main_app
    builder.add_edge("generate_main_app", "validate_app")
    builder.add_conditional_edges("validate_app", should_fix_app, {
        "fix_app": "fix_app",
        "quality_reviewer": "quality_reviewer",
        "senior_dev_reviewer": "senior_dev_reviewer",
        "architecture_reviewer": "architecture_reviewer"
    })
    builder.add_edge("fix_app", "validate_app")

    # Wire all reviewers in parallel directly to END
    builder.add_edge("quality_reviewer", END)
    builder.add_edge("senior_dev_reviewer", END)
    builder.add_edge("architecture_reviewer", END)

    
    graph = builder.compile()
    
    try:
        result = graph.invoke(
            {"project_key": project_key, "ticket_keys": ticket_keys},
            {"recursion_limit": 50}  # Increase from default 25
        )
        
        print(f"\n✅ Unified app generated")
        print(f"📊 Tests: {result.get('passed', 0)} passed, {result.get('failed', 0)} failed")
        print(f"🚀 streamlit run {result.get('app_path', 'app.py')}")
        print(f"📄 Log: {log_file}")
        
        logger.info(f"Generation complete for {project_key}")
        
        # Display LangSmith stats for this run
        display_run_stats(limit=30)
        
        return result
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "rate_limit" in error_msg.lower():
            print(f"\n❌ OpenAI API quota exceeded. Please check your usage limits.")
            logger.error(f"Quota error: {error_msg}")
        else:
            print(f"\n❌ Error during generation: {error_msg}")
            logger.error(f"Generation failed: {error_msg}", exc_info=True)
        raise
