#!/usr/bin/env python3
"""
Refactored LangGraph workflow builder for Streamlit code generation.
Wires graph nodes imported from graph.nodes package.
"""
import logging
from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator

from langgraph.graph import StateGraph, END
from utils.logging_utils import setup_logging
from save_app import save_app
from graph.nodes import (
    health_check,
    jira_reader,
    system_architect,
    requirements_analyzer,
    spec_agent,
    spec_reviewer,
    generate_tests,
    code_merger,
    generate_code,
    validate_modules,
    ui_designer,
    generate_main_app,
    validate_app,
    fix_app,
    run_tests_node,
    fix_analyzer,
    fixer_agent,
    quality_reviewer,
    senior_dev_reviewer,
    architecture_reviewer
)

logger = logging.getLogger("unified")

class GenState(TypedDict, total=False):
    project_key: str
    ticket_keys: List[str]
    tickets: List[Dict[str, Any]]
    epic_description: str
    architecture_plan: str
    modules: Dict[str, Any]
    specs: Dict[str, Any]
    test_files: Dict[str, str]
    code_files: Dict[str, str]
    valid_modules: Dict[str, Any]
    ui_layout: str
    app_file: str
    health_ok: bool
    architecture_approved: bool
    rejection_reason: str
    arch_iteration: int
    test_success: bool
    test_results: Dict[str, Any]
    fix_plans: Dict[str, Any]
    fix_iteration: int
    app_valid: bool
    app_error: str
    app_fix_iteration: int
    quality_review: str
    senior_dev_review: str
    architecture_review: str

def should_continue(state: GenState) -> str:
    if not state.get("health_ok", True):
        return "end"
    return "jira_reader"

def should_retry_architecture(state: GenState) -> str:
    if state.get("architecture_approved", False):
        return "spec_agent"
    return "system_architect"

def should_fix(state: GenState) -> str:
    if state.get("test_success", False):
        return "ui_designer"
    if state.get("fix_iteration", 0) >= 3:
        return "ui_designer"
    return "fix_analyzer"

def should_fix_app(state: GenState) -> str:
    if state.get("app_valid", False):
        return "reviewers_fanout"
    if state.get("app_fix_iteration", 0) >= 3:
        return "reviewers_fanout"
    return "fix_app"

def reviewers_fanout(state: GenState) -> List[str]:
    return ["quality_reviewer", "senior_dev_reviewer", "architecture_reviewer"]

def run_unified_graph(project_key: str, ticket_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    setup_logging(log_file="logs/unified_graph.log")
    logger.info("Initializing refactored LangGraph Unified Workflow")
    print("🚀 Initializing Refactored LangGraph Workflow...")

    builder = StateGraph(GenState)

    # Register graph nodes
    builder.add_node("health_check", health_check)
    builder.add_node("jira_reader", jira_reader)
    builder.add_node("system_architect", system_architect)
    builder.add_node("requirements_analyzer", requirements_analyzer)
    builder.add_node("spec_agent", spec_agent)
    builder.add_node("spec_reviewer", spec_reviewer)
    builder.add_node("generate_tests", generate_tests)
    builder.add_node("code_merger", code_merger)
    builder.add_node("generate_code", generate_code)
    builder.add_node("validate_modules", validate_modules)
    builder.add_node("ui_designer", ui_designer)
    builder.add_node("generate_main_app", generate_main_app)
    builder.add_node("validate_app", validate_app)
    builder.add_node("fix_app", fix_app)
    builder.add_node("run_tests_node", run_tests_node)
    builder.add_node("fix_analyzer", fix_analyzer)
    builder.add_node("fixer_agent", fixer_agent)
    builder.add_node("quality_reviewer", quality_reviewer)
    builder.add_node("senior_dev_reviewer", senior_dev_reviewer)
    builder.add_node("architecture_reviewer", architecture_reviewer)

    # Set entry point
    builder.set_entry_point("health_check")

    # Wire graph edges
    builder.add_conditional_edges("health_check", should_continue, {"end": END, "jira_reader": "jira_reader"})
    builder.add_edge("jira_reader", "system_architect")
    builder.add_edge("system_architect", "requirements_analyzer")
    builder.add_conditional_edges("requirements_analyzer", should_retry_architecture, {
        "spec_agent": "spec_agent",
        "system_architect": "system_architect"
    })
    builder.add_edge("spec_agent", "spec_reviewer")
    builder.add_edge("spec_reviewer", "generate_tests")
    builder.add_edge("generate_tests", "code_merger")
    builder.add_edge("code_merger", "generate_code")
    builder.add_edge("generate_code", "validate_modules")
    builder.add_edge("validate_modules", "run_tests_node")
    
    builder.add_conditional_edges("run_tests_node", should_fix, {
        "ui_designer": "ui_designer",
        "fix_analyzer": "fix_analyzer"
    })
    builder.add_edge("fix_analyzer", "fixer_agent")
    builder.add_edge("fixer_agent", "run_tests_node")

    builder.add_edge("ui_designer", "generate_main_app")
    builder.add_edge("generate_main_app", "validate_app")
    
    builder.add_conditional_edges("validate_app", should_fix_app, {
        "reviewers_fanout": "quality_reviewer", # Also triggers senior_dev_reviewer and architecture_reviewer concurrently
        "fix_app": "fix_app"
    })
    builder.add_edge("fix_app", "validate_app")

    builder.add_edge("quality_reviewer", END)
    builder.add_edge("senior_dev_reviewer", END)
    builder.add_edge("architecture_reviewer", END)

    app_graph = builder.compile()

    initial_state: GenState = {
        "project_key": project_key,
        "ticket_keys": ticket_keys if ticket_keys else ["ALL"],
        "arch_iteration": 0,
        "fix_iteration": 0,
        "app_fix_iteration": 0
    }

    print("⚡ Executing Unified Graph...")
    final_state = app_graph.invoke(initial_state)

    if final_state.get("health_ok", True):
        save_app(project_key=project_key)
        print("🎉 Unified Application Generation Complete!")

    else:
        print("❌ Execution aborted due to health check failure.")

    return final_state

if __name__ == "__main__":
    import sys
    from config.settings import Settings
    proj = sys.argv[1] if len(sys.argv) > 1 else Settings.JIRA_PROJECT_KEY
    run_unified_graph(project_key=proj, ticket_keys=["KAN-1", "KAN-2", "KAN-3"])
