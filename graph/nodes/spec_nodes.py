"""
Specification extraction and review nodes for Jira Coder graph workflow.
"""
import logging
from utils.file_utils import load_prompt
from utils.llm_helper import call_llm

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def spec_agent(state: dict) -> dict:
    """
    Node: Generates detailed specifications for each module defined in the architecture plan.
    It links requirements from Jira tickets to module functions and implementation details.
    """
    _log_phase("spec_agent")
    modules = state.get("modules", {})
    tickets = state.get("tickets", [])
    
    ticket_dict = {t["key"]: t for t in tickets}
    specs = {}
    
    for module_name, mod_info in modules.items():
        module_tickets = mod_info.get("tickets", [])
        related_tickets = [ticket_dict[k] for k in module_tickets if k in ticket_dict]
        
        tickets_text = "\n\n".join(
            [f"Ticket: {t['key']}\nTitle: {t['title']}\nDescription: {t['description']}" for t in related_tickets]
        )
        
        prompt_template = load_prompt("unified_spec_agent.txt")
        prompt = prompt_template.format(
            module_name=module_name,
            purpose=mod_info.get("purpose", ""),
            functions=", ".join(mod_info.get("functions", [])),
            tickets_text=tickets_text
        )

        spec = call_llm(
            system_prompt="You are a lead developer writing technical specifications.",
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=1500
        )
        specs[module_name] = spec
        logger.info(f"Spec for {module_name}:\n{spec}")
    
    return {"specs": specs}

def spec_reviewer(state: dict) -> dict:
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
