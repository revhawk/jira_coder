"""
Initialization nodes for Jira Coder graph workflow.
"""
import logging
from config.settings import Settings
from agents.jira_agent import jira_client
from utils.logging_utils import setup_logging

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def health_check(state: dict) -> dict:
    """Node: Verifies connections to external services like Jira and OpenAI."""
    _log_phase("health_check")
    project_key = state.get("project_key", "")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        client.models.list()
        logger.info("✅ OpenAI connection successful.")
    except Exception as e:
        logger.error(f"❌ OpenAI connection failed: {e}", exc_info=True)
        print(f"❌ OpenAI connection failed. Error: {e}")
        return {"health_ok": False}
        
    try:
        result = jira_client.list_all_issues_in_project(project_key=project_key, max_results=1)
        if "error" in result and "issues" not in result:
            raise ConnectionError(result.get("details", "Project not found or permission error"))
        logger.info(f"✅ Jira connection successful and project '{project_key}' found.")
    except Exception as e:
        logger.error(f"❌ Jira connection failed or project '{project_key}' not found: {e}")
        print(f"❌ Jira connection failed. Error: {e}")
        return {"health_ok": False}
        
    return {"health_ok": True}

def jira_reader(state: dict) -> dict:
    """Node: Reads Jira tickets based on keys or fetches all from a project."""
    _log_phase("jira_reader")
    project_key = state.get("project_key", "")
    keys_to_fetch = state.get("ticket_keys", [])
    
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
            issue_type = data.get("issuetype", "")
            if issue_type.upper() == "EPIC":
                desc = data.get("description", "")
                if desc:
                    epic_description = str(desc)
                    logger.info(f"Found EPIC: {key} with description length: {len(epic_description)}")
                    print(f"📋 EPIC: {data.get('summary', '')}")
            else:
                tickets.append({
                    "key": key,
                    "title": data.get("summary", ""),
                    "description": str(data.get("description", ""))
                })
    logger.info(f"Loaded {len(tickets)} tickets and EPIC description")
    return {"tickets": tickets, "ticket_keys": keys_to_fetch, "epic_description": epic_description}
