"""
Architecture planning and requirement analysis nodes for Jira Coder graph workflow.
"""
import re
import json
import logging
from utils.file_utils import load_prompt
from utils.llm_helper import call_llm

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def system_architect(state: dict) -> dict:
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
        print("🎯 Using EPIC requirements")
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
    print(f"🎯 Goal: {app_goal}")

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
    # Clean markdown from response
    arch_plan = re.sub(r'^```json\s*', '', arch_plan)
    arch_plan = re.sub(r'```\s*$', '', arch_plan)
    
    logger.info(f"Architecture plan:\n{arch_plan}")
    
    # Parse modules
    try:
        plan_json = json.loads(arch_plan)
        modules = {}
        for mod in plan_json.get("modules", []):
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

def requirements_analyzer(state: dict) -> dict:
    """Analyze EPIC requirements and ensure architecture stays simple and focused."""
    _log_phase("requirements_analyzer")
    epic_description = state.get("epic_description", "")
    architecture_plan = state.get("architecture_plan", "")
    arch_iteration = state.get("arch_iteration", 0)
    
    import os
    module_dir = "modules"
    if os.path.exists(module_dir) and any(f.endswith('.py') and f != '__init__.py' for f in os.listdir(module_dir)):
        logger.info("Existing modules detected - skipping requirements check for incremental update")
        print("🔄 Incremental update mode - accepting new features")
        return {"architecture_approved": True}
    
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
        "A calculator, for example, should be simple functions, not a state machine.\n\n"
        f"EPIC Requirements:\n{epic_description}\n\n"
        f"Proposed Architecture:\n{architecture_plan}\n\n"
        "Respond with JSON:\n"
        "{\n"
        '  "approved": boolean,\n'
        '  "reason": "explanation if rejected, or approved message"\n'
        "}"
    )
    
    response = call_llm(
        system_prompt=load_prompt("system_json_only.txt"),
        user_prompt=prompt,
        model="gpt-4o-mini",
        temperature=0.1,
        max_tokens=500
    )
    
    response = re.sub(r'^```json\s*', '', response)
    response = re.sub(r'```\s*$', '', response)
    
    try:
        result = json.loads(response)
        approved = result.get("approved", True)
        reason = result.get("reason", "")
        
        if approved:
            logger.info("Architecture approved by requirements analyzer")
            print("✅ Architecture approved (simple & focused)")
            return {"architecture_approved": True}
        else:
            logger.warning(f"Architecture REJECTED: {reason}")
            print(f"❌ Architecture rejected: {reason}")
            print("🔄 Requesting simpler architecture...")
            return {
                "architecture_approved": False,
                "rejection_reason": reason,
                "arch_iteration": arch_iteration + 1
            }
    except Exception as e:
        logger.error(f"Failed to parse requirements analyzer response: {e}")
        return {"architecture_approved": True}
