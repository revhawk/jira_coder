"""
Streamlit application synthesis, UI design, validation, and auto-fix nodes.
"""
import os
import re
import ast
import logging
from utils.file_utils import load_prompt
from utils.llm_helper import call_llm

logger = logging.getLogger("unified")

def _log_phase(phase: str):
    logger.info(f"Phase: {phase}")
    print(f"⚙️  {phase}...")

def ui_designer(state: dict) -> dict:
    """
    Node: Designs user interface structure for the main Streamlit application.
    """
    _log_phase("ui_designer")
    valid_modules = state.get("valid_modules", {})
    epic_description = state.get("epic_description", "")
    
    modules_info = []
    for mod_name, info in valid_modules.items():
        functions = info.get("functions", [])
        modules_info.append(f"Module: {mod_name}\nFunctions: {', '.join(functions)}")
        
    modules_text = "\n\n".join(modules_info)
    
    prompt = (
        f"You are a UI/UX designer creating a layout for a Streamlit application.\n\n"
        f"AVAILABLE MODULES & FUNCTIONS:\n{modules_text}\n\n"
        f"APPLICATION GOAL / EPIC:\n{epic_description}\n\n"
        f"DESIGN INSTRUCTIONS:\n"
        f"1. Choose a clean layout (Sidebar navigation, tabs, or unified dashboard)\n"
        f"2. Keep layout interactive and intuitive\n"
        f"3. Return layout instructions\n"
    )
    
    ui_layout = call_llm(
        system_prompt="You are a UI designer specializing in Streamlit applications.",
        user_prompt=prompt,
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=1000
    )
    
    logger.info(f"UI Layout:\n{ui_layout}")
    return {"ui_layout": ui_layout}

def generate_main_app(state: dict) -> dict:
    """
    Node: Generates main `app.py` connecting all modules into a cohesive UI.
    """
    _log_phase("generate_main_app")
    valid_modules = state.get("valid_modules", {})
    ui_layout = state.get("ui_layout", "")
    epic_description = state.get("epic_description", "")
    tickets = state.get("tickets", [])
    
    modules_detail = []
    for mod_name, info in valid_modules.items():
        code_path = info.get("path", "")
        if os.path.exists(code_path):
            with open(code_path, "r") as f:
                code = f.read()
            modules_detail.append(f"# Module: modules/{mod_name}.py\n{code}")
            
    modules_code = "\n\n".join(modules_detail)
    
    prompt_template = load_prompt("unified_generate_main_app.txt")
    prompt = prompt_template.format(
        modules_code=modules_code,
        ui_layout=ui_layout,
        epic_description=epic_description,
        tickets_summary="\n".join([f"- {t['key']}: {t['title']}" for t in tickets])
    )

    app_code = call_llm(
        system_prompt=load_prompt("system_python_code_only.txt"),
        user_prompt=prompt,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=4000
    )
    app_code = re.sub(r'^```python\s*', '', app_code)
    app_code = re.sub(r'```\s*$', '', app_code)
    
    app_path = "app.py"
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app_code)
    logger.info(f"Main app written: {app_path}")
    
    return {"app_file": app_path}

def validate_app(state: dict) -> dict:
    """
    Node: Validates generated `app.py` syntax and import references.
    """
    _log_phase("validate_app")
    app_file = state.get("app_file", "app.py")
    
    if not os.path.exists(app_file):
        return {"app_valid": False, "app_error": "app.py file not found"}
        
    with open(app_file, "r") as f:
        app_code = f.read()
        
    try:
        ast.parse(app_code)
        logger.info("app.py syntax is valid")
        return {"app_valid": True, "app_error": ""}
    except SyntaxError as e:
        logger.error(f"app.py syntax error: {e}")
        return {"app_valid": False, "app_error": f"Syntax error: {e}"}

def fix_app(state: dict) -> dict:
    """
    Node: Fixes syntax errors or broken imports in `app.py`.
    """
    _log_phase("fix_app")
    app_file = state.get("app_file", "app.py")
    app_error = state.get("app_error", "")
    iteration = state.get("app_fix_iteration", 0)
    
    if not os.path.exists(app_file):
        return {"app_fix_iteration": iteration + 1}
        
    with open(app_file, "r") as f:
        broken_code = f.read()
        
    prompt = (
        f"Fix the following Streamlit application code.\n\n"
        f"BROKEN CODE:\n{broken_code}\n\n"
        f"ERROR DETAILS:\n{app_error}\n\n"
        f"Return ONLY valid Python code fixing the issue."
    )
    
    fixed_code = call_llm(
        system_prompt=load_prompt("system_python_code_only.txt"),
        user_prompt=prompt,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=4000
    )
    fixed_code = re.sub(r'^```python\s*', '', fixed_code)
    fixed_code = re.sub(r'```\s*$', '', fixed_code)
    
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(fixed_code)
    logger.info(f"Fixed app.py written (Iteration {iteration + 1})")
    
    return {"app_fix_iteration": iteration + 1}

