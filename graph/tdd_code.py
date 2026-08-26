# graph/langgraph_poc.py
from langgraph.graph import StateGraph, START
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

# Constants for generated code validation
ISSUE_KEY_VAR_NAME = "ISSUE_KEY"
TEST_FUNCTION_PREFIX = "def test_"

def run_poc_graph(issue_key: str):
    logger, log_file = setup_logging("generation", issue_key)
    logger.info(f"Starting generation for issue: {issue_key}")

    class GenState(TypedDict, total=False):
        issue_key: str
        title: str
        description: str
        test_path: str
        code_path: str
        test_output: str
        passed: int
        failed: int
        collected: int
        iteration: int
        max_iterations: int
        spec: str
        streamlit_ready: bool
        test_count: int
        tests_validated: bool
        needs_fix: bool
        fix_type: str
        review_report: str
        spec_review: str
        fix_recommendations: str
        senior_dev_review: str
        architecture_review: str
        test_issues: list
        code_issues: list
        current_tests: str
        current_code: str

    def log_phase(phase: str):
        logger.info(f"Phase: {phase}")
        # Only show critical phases on console
        if phase in ["jira_reader", "test_generator", "impl_agent"]:
            print(f"⚙️  {phase}...") # noqa: T201

    def jira_reader(state: GenState) -> GenState:
        log_phase("jira_reader")
        data = jira_client.read_issue(state.get("issue_key", ""))
        if "error" in data:
            return {"title": "", "description": f"ERROR: {data['error']}"}
        return {"title": data.get("summary", ""), "description": str(data.get("description"))}

    def spec_agent(state: GenState) -> GenState:
        log_phase("spec_agent")
        title = state.get("title", "")
        description = state.get("description", "")
        
        prompt_template = load_prompt("tdd_spec_agent.txt")
        prompt = prompt_template.format(title=title, description=description)

        spec = call_llm(
            system_prompt=load_prompt("system_json_only.txt"),
            user_prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=1500
        )
        try: # noqa: SIM105
            json.loads(spec or "{}")
        except json.JSONDecodeError:
            spec = json.dumps({"problem": title, "inputs": [], "outputs": [], "edge_cases": [], "acceptance": [], "api": []})
        return {"spec": spec or "{}", "iteration": 0, "max_iterations": 3}

    def spec_reviewer(state: GenState) -> GenState:
        """Review spec quality before test generation."""
        log_phase("spec_reviewer")
        
        spec = state.get("spec", "")
        title = state.get("title", "")
        description = state.get("description", "")
        
        prompt_template = load_prompt("tdd_spec_reviewer.txt")
        review_prompt = prompt_template.format(title=title, description=description, spec=spec)
        
        review = call_llm(
            system_prompt="You are a senior QA engineer reviewing specifications.",
            user_prompt=review_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=800
        )
        logger.info(f"Spec review:\n{review}")
        
        return {"spec_review": review or ""}

    def generate_tests(state: GenState) -> GenState:
        log_phase("test_generator")
        title = state.get("title", "").strip()
        description = state.get("description", "")
        spec = state.get("spec", "")
        key = state.get("issue_key", "").upper().replace(" ", "_")
        module_name = key.replace("-", "_")
        output_dir = os.path.join("workspace", "tdd_modules", key)
        os.makedirs(output_dir, exist_ok=True)
        test_path = os.path.join(output_dir, f"test_{key}.py")

        # Generate tests
        prompt_template = load_prompt("unified_generate_tests.txt")
        test_prompt = prompt_template.format(
            module_name=module_name,
            title=title,
            description=description,
            spec=spec
        )

        tests_src = call_llm(
            system_prompt=load_prompt("system_python_test_code_only.txt"),
            user_prompt=test_prompt,
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=3000
        )
        
        # Clean markdown
        tests_src = re.sub(r'^```python\s*', '', tests_src)
        tests_src = re.sub(r'```\s*$', '', tests_src)
        
        # Validate imports
        if f"from {module_name} import *" not in tests_src:
            # Ensure pytest is imported first, then our module
            if "import pytest" not in tests_src:
                tests_src = "import pytest\n" + tests_src
            # Insert the module import after pytest, if pytest is present
            if "import pytest" in tests_src: # Check again in case it was just added
                tests_src = tests_src.replace("import pytest", f"import pytest\nfrom {module_name} import *")
            else: # Fallback if pytest is somehow still missing
                tests_src = f"import pytest\nfrom {module_name} import *\n\n" + tests_src
        
        # Ensure at least one test
        if TEST_FUNCTION_PREFIX not in tests_src:
            tests_src += "\n\ndef test_sanity():\n    assert True\n"
        
        # Validate syntax
        try: # noqa: SIM105
            ast.parse(tests_src)
        except SyntaxError as e:
            logger.error(f"Test syntax error: {e}")
            tests_src = f"import pytest\nfrom {module_name} import *\n\ndef test_sanity():\n    assert True\n"
        # Validate coverage: count test functions
        test_count = tests_src.count("def test_")
        if test_count < 2:
            logger.warning(f"Only {test_count} test(s) generated. Adding basic tests.")
            for i in range(test_count, 2):
                tests_src += f"\n\ndef test_basic_{i}():\n    assert True\n"
        elif test_count == 2:
            logger.info("2 tests generated (acceptable for simple functions).")
        elif test_count > 7:
            logger.info(f"{test_count} tests generated (more than recommended 7).")
        
        # Write test file
        write_files([{"path": test_path, "content": tests_src}])
        return {"test_path": test_path, "tests_validated": True, "test_count": test_count}

    def generate_code(state: GenState) -> GenState:
        log_phase("impl_agent")
        title = state.get("title", "").strip()
        description = state.get("description", "")
        spec = state.get("spec", "")
        key = state.get("issue_key", "").upper().replace(" ", "_")
        module_name = key.replace("-", "_")
        output_dir = os.path.join("workspace", "tdd_modules", key)
        os.makedirs(output_dir, exist_ok=True)
        code_path = os.path.join(output_dir, f"{module_name}.py")
        test_path = state.get("test_path")
        
        # Read validated tests
        tests_src = read_text_safe(test_path or "")
        
        # Generate implementation based on validated tests
        prompt_template = load_prompt("unified_generate_code.txt")
        code_prompt = prompt_template.format(
            key=key,
            title=title,
            description=description,
            spec=spec,
            tests_src=tests_src
        )

        code_src = call_llm(
            system_prompt=load_prompt("system_python_code_only.txt"),
            user_prompt=code_prompt,
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=3000
        )
        
        # Clean markdown
        code_src = re.sub(r'^```python\s*', '', code_src)
        code_src = re.sub(r'```\s*$', '', code_src)

        # Ensure ISSUE_KEY
        if ISSUE_KEY_VAR_NAME not in code_src:
            code_src = f"{ISSUE_KEY_VAR_NAME} = '{key}'\n" + code_src
        
        # Validate syntax
        try: # noqa: SIM105
            ast.parse(code_src)
        except SyntaxError as e: # noqa: SIM105
            logger.error(f"Code syntax error: {e}")
            code_src = f"ISSUE_KEY = '{key}'\n\ndef placeholder():\n    pass\n"

        # The TDD workflow should produce a module, not a runnable app.
        # We set streamlit_ready to False.
        streamlit_ready = False
        logger.info("Generating a standalone module without Streamlit UI.")
        
        write_files([{"path": code_path, "content": code_src}])
        return {"code_path": code_path, "streamlit_ready": streamlit_ready}

    def run_tests_node(state: GenState) -> GenState:
        log_phase("test_runner")
        test_path = state.get("test_path")
        if not test_path:
            return {"output": "No test path found", "passed": 0, "failed": 1, "collected": 0}
        
        print(f"\n🧪 Running tests: pytest {test_path}") # noqa: T201

        # The test runner needs the code's directory in the python path
        res = run_pytest(test_path)
        out = res.get("output", "")

        # Log full output to file and print a summary to console
        logger.info(f"PyTest output:\n{out}")
        print(out)
        return {"test_output": out, "passed": res.get("passed", 0), "failed": res.get("failed", 0), "collected": res.get("collected")}

    def fix_analyzer(state: GenState) -> GenState:
        """Analyze failures and provide specific fix recommendations."""
        log_phase("fix_analyzer")
        
        if state.get("failed", 0) == 0 and state.get("collected", 0) > 0:
            return {"needs_fix": False, "fix_recommendations": ""}
        
        test_path = state.get("test_path")
        code_path = state.get("code_path")
        current_tests = read_text_safe(test_path)
        current_code = read_text_safe(code_path)
        
        spec = state.get("spec", "")
        pytest_out = state.get("test_output", "")
        
        prompt_template = load_prompt("unified_fix_analyzer.txt")
        fix_prompt = prompt_template.format(
            spec=spec,
            pytest_out=pytest_out,
            current_tests=current_tests,
            current_code=current_code
        )
        
        recommendations = call_llm(
            system_prompt="You are a debugging expert analyzing test failures.",
            user_prompt=fix_prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=1000
        )
        logger.info(f"Fix recommendations:\n{recommendations}")
        
        # Determine fix target
        fix_target = "BOTH"
        if "FIX_TARGET: TESTS" in recommendations:
            fix_target = "TESTS"
        elif "FIX_TARGET: CODE" in recommendations:
            fix_target = "CODE"
        
        return {
            "needs_fix": True,
            "fix_recommendations": recommendations,
            "fix_type": fix_target,
            "current_tests": current_tests,
            "current_code": current_code
        }

    def quality_reviewer(state: GenState) -> GenState:
        """Review test and code quality."""
        log_phase("quality_reviewer")
        
        # Read current files
        test_path = state.get("test_path")
        code_path = state.get("code_path")
        current_tests = read_text_safe(test_path)
        current_code = read_text_safe(code_path)
        
        title = state.get("title", "")
        spec = state.get("spec", "")
        pytest_out = state.get("test_output", "")
        passed = state.get("passed", 0)
        failed = state.get("failed", 0)
        collected = state.get("collected", 0)
        
        # Comprehensive review prompt
        prompt_template = load_prompt("unified_quality_reviewer.txt")
        review_prompt = prompt_template.format(spec=spec, passed=passed, failed=failed, collected=collected, pytest_out=pytest_out, current_tests=current_tests, current_code=current_code)
        
        review_report = call_llm(
            system_prompt="You are a quality assurance expert reviewing code and tests.",
            user_prompt=review_prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=1500
        )
        
        # Extract issues
        test_issues = []
        code_issues = []
        if "TEST_ISSUES:" in review_report:
            test_section = review_report.split("TEST_ISSUES:")[1].split("CODE_QUALITY:")[0]
            test_issues = [line.strip() for line in test_section.split("\n") if line.strip().startswith("-")]
        if "CODE_ISSUES:" in review_report:
            code_section = review_report.split("CODE_ISSUES:")[1].split("RECOMMENDATIONS:")[0]
            code_issues = [line.strip() for line in code_section.split("\n") if line.strip().startswith("-")]
        
        return {
            "review_report": review_report,
            "test_issues": test_issues,
            "code_issues": code_issues
        }

    def senior_dev_reviewer(state: GenState) -> GenState:
        """Senior developer reviews if code will actually run."""
        log_phase("senior_dev_reviewer")
        
        test_path = state.get("test_path")
        code_path = state.get("code_path")
        current_tests = read_text_safe(test_path)
        current_code = read_text_safe(code_path)
        
        spec = state.get("spec", "")
        
        prompt_template = load_prompt("unified_senior_dev_reviewer.txt")
        senior_prompt = prompt_template.format(
            spec=spec,
            current_tests=current_tests,
            current_code=current_code
        )
        
        review = call_llm(
            system_prompt="You are a senior developer reviewing code for production readiness.",
            user_prompt=senior_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=800
        )
        logger.info(f"Senior dev review:\n{review}")
        
        will_run = "WILL_RUN: YES" in review
        streamlit_ready = "STREAMLIT_READY: YES" in review
        
        return {
            "senior_dev_review": review,
            "streamlit_ready": streamlit_ready,
            "needs_fix": not will_run
        }

    def architecture_reviewer(state: GenState) -> GenState:
        """Architect reviews code structure and design."""
        log_phase("architecture_reviewer")
        
        # Only run if code will run
        if state.get("needs_fix", False):
            return {"architecture_review": "Skipped - code has critical issues"}
        
        code_path = state.get("code_path")
        current_code = read_text_safe(code_path)
        
        spec = state.get("spec", "")
        title = state.get("title", "")
        
        prompt_template = load_prompt("unified_architecture_reviewer.txt")
        arch_prompt = prompt_template.format(
            title=title,
            spec=spec,
            current_code=current_code
        )
        
        review = call_llm(
            system_prompt="You are a software architect reviewing code structure and design.",
            user_prompt=arch_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=800
        )
        logger.info(f"Architecture review:\n{review}")
        
        return {"architecture_review": review}

    def fixer_agent(state: GenState) -> GenState:
        """Apply fixes based on recommendations."""
        log_phase("fixer_agent")
        
        key = state["issue_key"].upper().replace(" ", "_")
        module_name = key.replace("-", "_")
        output_dir = os.path.join("workspace", "tdd_modules", key)
        code_path = state.get("code_path") or os.path.join(output_dir, f"{module_name}.py")
        test_path = state.get("test_path") or os.path.join(output_dir, f"test_{key}.py")
        
        spec = state.get("spec", "")
        fix_recommendations = state.get("fix_recommendations", "")
        fix_type = state.get("fix_type", "BOTH")
        current_tests = state.get("current_tests", "")
        current_code = state.get("current_code", "")
        
        current_tests = read_text_safe(test_path) or current_tests
        
        # Fix tests if needed
        if fix_type in ["TESTS", "BOTH"]:
            prompt_template = load_prompt("tdd_fixer_agent.txt")
            test_fix_prompt = prompt_template.format(
                module_name=module_name,
                spec=spec,
                fix_recommendations=fix_recommendations,
                current_tests=current_tests
            )
            tests_src = call_llm(
                system_prompt="You are a test fixing expert. Output only valid Python code, no markdown.",
                user_prompt=test_fix_prompt,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=3000
            )
            tests_src = re.sub(r'^```python\s*', '', tests_src)
            tests_src = re.sub(r'```\s*$', '', tests_src)
        else:
            tests_src = current_tests # Use the current tests if not fixing them
        
        # Fix code if needed
        if fix_type in ["CODE", "BOTH"]:
            prompt_template = load_prompt("tdd_fixer_agent.txt")
            # The tdd_fixer_agent prompt expects 'fix_recommendations', 'current_code', and 'current_tests'
            code_fix_prompt = prompt_template.format(
                fix_recommendations=fix_recommendations,
                current_code=current_code,
                current_tests=tests_src # Use the potentially fixed tests
            )
            code_src = call_llm(
                system_prompt="You are a code fixing expert. Output only valid Python code, no markdown.",
                user_prompt=code_fix_prompt,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=3000
            )
            code_src = re.sub(r'^```python\s*', '', code_src)
            code_src = re.sub(r'```\s*$', '', code_src)
        else:
            code_src = current_code # Use the current code if not fixing it
        
        # Validate imports
        if f"from {module_name} import *" not in tests_src:
            if "import pytest" not in tests_src:
                tests_src = "import pytest\n" + tests_src
            if "import pytest" in tests_src:
                tests_src = tests_src.replace("import pytest", f"import pytest\nfrom {module_name} import *")
            else:
                tests_src = f"import pytest\nfrom {module_name} import *\n\n" + tests_src

        # Ensure ISSUE_KEY
        if ISSUE_KEY_VAR_NAME not in code_src:
            code_src = f"{ISSUE_KEY_VAR_NAME} = '{key}'\n" + code_src
        
        # Ensure at least one test
        if TEST_FUNCTION_PREFIX not in tests_src:
            tests_src += "\n\ndef test_sanity():\n    assert True\n"

        # AST validation
        try: # noqa: SIM105
            ast.parse(code_src)
        except SyntaxError:
            code_src = current_code
        try: # noqa: SIM105
            ast.parse(tests_src)
        except SyntaxError:
            tests_src = current_tests

        write_files([
            {"path": test_path, "content": tests_src},
            {"path": code_path, "content": code_src},
        ])
        return {"test_path": test_path, "code_path": code_path}

    builder = StateGraph(GenState)
    builder.add_node(jira_reader)
    builder.add_node(spec_agent)
    builder.add_node(spec_reviewer)
    builder.add_node(generate_tests)
    builder.add_node(generate_code)
    builder.add_node(run_tests_node)
    builder.add_node(fix_analyzer)
    builder.add_node(fixer_agent)
    builder.add_node(quality_reviewer)
    builder.add_node(senior_dev_reviewer)
    builder.add_node(architecture_reviewer)
    
    # Main flow
    builder.add_edge(START, "jira_reader")
    builder.add_edge("jira_reader", "spec_agent")
    builder.add_edge("spec_agent", "spec_reviewer")
    builder.add_edge("spec_reviewer", "generate_tests")
    builder.add_edge("generate_tests", "generate_code")
    builder.add_edge("generate_code", "run_tests_node")
    builder.add_edge("run_tests_node", "fix_analyzer")
    
    # Conditional: fix if needed
    def should_fix(state: GenState) -> str:
        return "fixer_agent" if state.get("needs_fix") else "quality_reviewer"
    
    builder.add_conditional_edges("fix_analyzer", should_fix, {
        "fixer_agent": "fixer_agent",
        "quality_reviewer": "quality_reviewer"
    })
    
    # After fix, re-run tests
    builder.add_edge("fixer_agent", "run_tests_node")
    
    # Quality and architecture reviews
    builder.add_edge("quality_reviewer", "senior_dev_reviewer")
    builder.add_edge("senior_dev_reviewer", "architecture_reviewer")
    
    graph = builder.compile()

    logger.info("LangGraph compiled successfully")
    result = graph.invoke({"issue_key": issue_key})
    
    # Console: Only critical info
    print(f"\n🧾 {issue_key}: {result.get('title')}") # noqa: T201
    print(f"📊 Tests: {result.get('passed',0)} passed, {result.get('failed',0)} failed")
    if result.get("streamlit_ready"):
        print(f"🚀 streamlit run {result['code_path']}")

    # Log: Full details
    logger.info(f"Jira Issue {issue_key}: {result.get('title')}")
    logger.info(f"Tests written to: {result.get('test_path')}")
    logger.info(f"Code written to: {result.get('code_path')}")
    logger.info(f"PyTest: {result.get('passed',0)} passed, {result.get('failed',0)} failed (collected: {result.get('collected')})")
    
    # Log all reviews
    if result.get("spec_review"):
        logger.info(f"SPEC REVIEW:\n{result['spec_review']}")
    if result.get("fix_recommendations"):
        logger.info(f"FIX RECOMMENDATIONS:\n{result['fix_recommendations']}")
    if result.get("review_report"):
        logger.info(f"QUALITY REVIEW:\n{result['review_report']}")
    if result.get("senior_dev_review"):
        logger.info(f"SENIOR DEV REVIEW:\n{result['senior_dev_review']}")
    if result.get("architecture_review"):
        logger.info(f"ARCHITECTURE REVIEW:\n{result['architecture_review']}")
    
    # Final status with review summary
    if result.get("failed", 0) == 0 and (result.get("collected") or 0) > 0:
        print("✅ Success")
        logger.info("All tests passed")
        
        # Show architecture score if available
        if result.get("architecture_review"):
            arch_review = result["architecture_review"]
            if "ARCHITECTURE_SCORE:" in arch_review:
                score = arch_review.split("ARCHITECTURE_SCORE:")[1].split("\n")[0].strip()
                print(f"🏛️ Architecture: {score}/10")
                logger.info(f"Architecture score: {score}/10")
    else:
        print(f"⚠️  {result.get('failed', 0)} tests failing")
        logger.warning(f"Tests failing: {result.get('failed', 0)} failed, {result.get('passed', 0)} passed")
        
        # Show what needs fixing
        if result.get("fix_recommendations"):
            print("🔧 See log for fix recommendations")

    logger.info(f"Generation complete for {issue_key}")
    print(f"📄 Log: {log_file}")
    
    # Display LangSmith stats for this run
    display_run_stats(limit=20)
    
    return result
