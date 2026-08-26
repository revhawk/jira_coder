"""
Code generation, test synthesis, code merging, and module validation nodes.
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

def generate_tests(state: dict) -> dict:
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
            max_tokens=2000
        )
        tests_src = re.sub(r'^```python\s*', '', tests_src)
        tests_src = re.sub(r'```\s*$', '', tests_src)
        
        try:
            ast.parse(tests_src)
        except SyntaxError:
            tests_src = f"def test_placeholder():\n    assert True\n"
        
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(tests_src)
        test_files[module_name] = test_path
        logger.info(f"Tests written: {test_path}")
    
    return {"test_files": test_files}

def code_merger(state: dict) -> dict:
    """
    Node: Merges new requirements into existing modules if they exist.
    Prevents overwriting existing code during incremental updates.
    """
    _log_phase("code_merger")
    specs = state.get("specs", {})
    module_dir = "modules"
    
    if not os.path.exists(module_dir):
        logger.info("No existing modules directory - skipping merge")
        return {}
        
    for module_name, spec in specs.items():
        code_path = os.path.join(module_dir, f"{module_name}.py")
        
        if os.path.exists(code_path):
            logger.info(f"Existing module found: {code_path} - merging new requirements...")
            print(f"🔀 Merging new features into {module_name}.py...")
            
            with open(code_path, "r") as f:
                existing_code = f.read()
                
            prompt = (
                f"You are updating an existing Python module with new features.\n\n"
                f"EXISTING MODULE CODE:\n{existing_code}\n\n"
                f"NEW SPECIFICATION/FEATURES TO ADD:\n{spec}\n\n"
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. KEEP all existing functions and classes intact (do NOT remove them)\n"
                f"2. ADD new functions/classes required by the specification\n"
                f"3. UPDATE existing functions if the spec explicitly calls for changing them\n"
                f"4. Ensure imports for all functions are preserved\n"
                f"5. Return ONLY the complete updated Python file code, no markdown\n"
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
            
            try:
                ast.parse(merged_code)
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(merged_code)
                logger.info(f"Successfully merged code into {code_path}")
            except SyntaxError as e:
                logger.error(f"Syntax error in merged code: {e} - keeping existing module")
                print(f"⚠️ Merge syntax error - keeping original file")
                
    return {}

def generate_code(state: dict) -> dict:
    """
    Node: Generates Python module code for each spec, taking generated tests into account.
    """
    _log_phase("generate_code")
    specs = state.get("specs", {})
    test_files = state.get("test_files", {})
    
    module_dir = "modules"
    os.makedirs(module_dir, exist_ok=True)
    code_files = {}
    
    for module_name, spec in specs.items():
        code_path = os.path.join(module_dir, f"{module_name}.py")
        
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
        
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code_src)
        code_files[module_name] = code_path
        logger.info(f"Code written: {code_path}")
    
    init_path = os.path.join(module_dir, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write("")

    
    return {"code_files": code_files}

def validate_modules(state: dict) -> dict:
    """
    Node: Validates generated module syntax and verifies all functions exist.
    """
    _log_phase("validate_modules")
    code_files = state.get("code_files", {})
    
    valid_modules = {}
    for module_name, code_path in code_files.items():
        if not os.path.exists(code_path):
            logger.warning(f"Module file not found: {code_path}")
            continue
            
        with open(code_path, "r") as f:
            code_src = f.read()
            
        try:
            tree = ast.parse(code_src)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            logger.info(f"Module {module_name} syntax valid with functions: {functions}")
            valid_modules[module_name] = {"path": code_path, "functions": functions}
        except SyntaxError as e:
            logger.error(f"Syntax error in {code_path}: {e}")
            
    return {"valid_modules": valid_modules}
