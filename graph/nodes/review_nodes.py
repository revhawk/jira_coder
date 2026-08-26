"""
Parallel code review nodes for Jira Coder graph workflow.
"""
import os
import logging
from utils.file_utils import load_prompt
from utils.llm_helper import call_llm

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def quality_reviewer(state: dict) -> dict:
    """Node: Reviews code quality, readability, and error handling."""
    _log_phase("quality_reviewer")
    app_file = state.get("app_file", "app.py")
    if not os.path.exists(app_file):
        return {}
    with open(app_file, "r") as f:
        code = f.read()
        
    prompt_template = load_prompt("unified_quality_reviewer.txt")
    prompt = prompt_template.format(app_code=code)
    review = call_llm(
        system_prompt="You are a senior QA engineer reviewing code quality.",
        user_prompt=prompt,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=1000
    )
    logger.info(f"Quality Review:\n{review}")
    return {"quality_review": review}

def senior_dev_reviewer(state: dict) -> dict:
    """Node: Reviews code functionality, performance, and best practices."""
    _log_phase("senior_dev_reviewer")
    app_file = state.get("app_file", "app.py")
    if not os.path.exists(app_file):
        return {}
    with open(app_file, "r") as f:
        code = f.read()
        
    prompt_template = load_prompt("unified_senior_dev_reviewer.txt")
    prompt = prompt_template.format(app_code=code)
    review = call_llm(
        system_prompt="You are a principal developer performing code review.",
        user_prompt=prompt,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=1000
    )
    logger.info(f"Senior Dev Review:\n{review}")
    return {"senior_dev_review": review}

def architecture_reviewer(state: dict) -> dict:
    """Node: Reviews structural cohesion and modularity."""
    _log_phase("architecture_reviewer")
    app_file = state.get("app_file", "app.py")
    if not os.path.exists(app_file):
        return {}
    with open(app_file, "r") as f:
        code = f.read()
        
    prompt_template = load_prompt("unified_architecture_reviewer.txt")
    prompt = prompt_template.format(app_code=code)
    review = call_llm(
        system_prompt="You are an enterprise software architect reviewing application structure.",
        user_prompt=prompt,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=1000
    )
    logger.info(f"Architecture Review:\n{review}")
    return {"architecture_review": review}
