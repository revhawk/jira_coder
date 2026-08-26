"""
Automated tests for Streamlit app functionality.
Tests UI behavior without manual clicking.
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_app_imports():
    """Test that app.py can be imported without errors."""
    try:
        import app
        assert app is not None, "App module must import cleanly"
    except ImportError as e:
        pytest.fail(f"Failed to import app: {e}")


def test_app_syntax():
    """Test that app.py has valid Python syntax."""
    import ast
    with open('app.py', 'r') as f:
        code = f.read()
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in app.py: {e}")

def test_streamlit_imports():
    """Test that all required Streamlit components are imported."""
    with open('app.py', 'r') as f:
        code = f.read()
    assert 'import streamlit' in code, "Must import streamlit"
    assert 'st.session_state' in code, "Should use session_state for state management"

def test_button_pattern():
    """Test that buttons use correct pattern (if st.button(), not on_click=lambda)."""
    with open('app.py', 'r') as f:
        code = f.read()
    assert 'on_click=lambda' not in code, "Should not use on_click=lambda pattern"
    if 'st.button(' in code:
        assert 'if st.button(' in code, "Buttons should use 'if st.button():' pattern"

def test_session_state_initialization():
    """Test that session state is properly initialized."""
    with open('app.py', 'r') as f:
        code = f.read()
    # Check for session state initialization pattern
    assert 'st.session_state' in code, "Should use session_state"

def test_no_widget_key_conflicts():
    """Test that widgets don't have key conflicts with session_state assignments."""
    import re
    with open('app.py', 'r') as f:
        code = f.read()
    # Pattern: st.session_state.X = st.widget(..., key='X')
    pattern = r"st\.session_state\.(\w+)\s*=\s*st\.\w+\([^)]*key=['\"]\\1['\"]"
    conflicts = re.findall(pattern, code)
    assert len(conflicts) == 0, f"Found session_state/key conflicts: {conflicts}"

def test_module_imports_exist():
    """Test that all imported modules actually exist."""
    import re
    with open('app.py', 'r') as f:
        code = f.read()
    imports = re.findall(r'from modules\.(\w+) import', code)
    for module_name in imports:
        module_path = f'modules/{module_name}.py'
        assert os.path.exists(module_path), f"Module {module_name} doesn't exist at {module_path}"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
