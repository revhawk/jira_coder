"""
PyTest execution and test-driven code auto-fixing nodes.
"""
import os
import re
import ast
import json
import logging
from agents.tester_agent import run_pytest
from utils.file_utils import load_prompt
from utils.llm_helper import call_llm

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def run_tests_node(state: dict) -> dict:
    """
    Node: Runs pytest suite against generated modules.
    """
    _log_phase("run_tests_node")
    test_files = state.get("test_files", {})
    iteration = state.get("fix_iteration", 0)
    
    if not test_files:
        logger.info("No test files to run.")
        return {"test_success": True, "test_results": {}}
        
    test_dir = "generated_tests"
    
    result = run_pytest(test_dir, extra_paths=["modules"])
    logger.info(f"Test run result (Iteration {iteration}): {result}")
    
    all_passed = (result.get("failed", 0) == 0) and (result.get("passed", 0) > 0)
    return {
        "test_success": all_passed,
        "test_results": result,
        "fix_iteration": iteration
    }


def fix_analyzer(state: dict) -> dict:
    """
    Node: Analyzes failing pytest runs and creates fix plans.
    """
    _log_phase("fix_analyzer")
    test_results = state.get("test_results", {})
    code_files = state.get("code_files", {})
    
    failures = test_results.get("failures", [])
    if not failures:
        return {"fix_plans": {}}
        
    fix_plans = {}
    for fail in failures:
        test_name = fail.get("nodeid", "")
        error_msg = fail.get("message", "")
        
        prompt = (
            f"Analyze the following pytest failure and describe required code fix:\n\n"
            f"Test: {test_name}\n"
            f"Error: {error_msg}\n"
        )
        
        plan = call_llm(
            system_prompt="You are a debugging expert creating targeted fix plans.",
            user_prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=500
        )
        fix_plans[test_name] = plan
        
    return {"fix_plans": fix_plans}

def fixer_agent(state: dict) -> dict:
    """
    Node: Applies code fixes to module files based on fix plans.
    """
    _log_phase("fixer_agent")
    fix_plans = state.get("fix_plans", {})
    code_files = state.get("code_files", {})
    iteration = state.get("fix_iteration", 0)
    
    for test_name, plan in fix_plans.items():
        module_name = test_name.split("::")[0].replace("test_", "").replace(".py", "")
        module_name = os.path.basename(module_name)
        
        code_path = code_files.get(module_name, f"modules/{module_name}.py")
        if not os.path.exists(code_path):
            continue
            
        with open(code_path, "r") as f:
            broken_code = f.read()
            
        prompt = (
            f"Fix the following Python code based on the fix plan.\n\n"
            f"CURRENT CODE:\n{broken_code}\n\n"
            f"FIX PLAN:\n{plan}\n\n"
            f"Return ONLY fixed Python code."
        )
        
        fixed_code = call_llm(
            system_prompt=load_prompt("system_python_code_only.txt"),
            user_prompt=prompt,
            model="gpt-4o",
            temperature=0.1,
            max_tokens=3000
        )
        fixed_code = re.sub(r'^```python\s*', '', fixed_code)
        fixed_code = re.sub(r'```\s*$', '', fixed_code)
        
        try:
            ast.parse(fixed_code)
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)
            logger.info(f"Applied fix to {code_path}")
        except SyntaxError:
            pass

            
    return {"fix_iteration": iteration + 1}
