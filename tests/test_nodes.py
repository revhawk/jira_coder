"""
Unit tests for individual graph nodes in graph.nodes package.
"""
import os
import pytest
from graph.nodes.app_nodes import validate_app
from graph.nodes.architect_nodes import requirements_analyzer

def test_validate_app_valid(tmp_path):
    app_file = tmp_path / "app.py"
    app_file.write_text("import streamlit as st\nst.write('Hello')")
    
    state = {"app_file": str(app_file)}
    res = validate_app(state)
    assert res.get("app_valid") is True

def test_validate_app_syntax_error(tmp_path):
    app_file = tmp_path / "app.py"
    app_file.write_text("def broken_func(:")
    
    state = {"app_file": str(app_file)}
    res = validate_app(state)
    assert res.get("app_valid") is False
    assert "Syntax error" in res.get("app_error", "")

def test_requirements_analyzer_no_epic():
    state = {"epic_description": ""}
    res = requirements_analyzer(state)
    assert res.get("architecture_approved") is True
