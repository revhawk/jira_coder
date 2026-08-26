"""
Unit tests for LangGraph topology and node routing logic in create_streamlit_app.py
"""
import pytest
from graph.create_streamlit_app import (
    should_continue,
    should_retry_architecture,
    should_fix,
    should_fix_app,
    reviewers_fanout
)

def test_should_continue():
    assert should_continue({"health_ok": True}) == "jira_reader"
    assert should_continue({"health_ok": False}) == "end"

def test_should_retry_architecture():
    assert should_retry_architecture({"architecture_approved": True}) == "spec_agent"
    assert should_retry_architecture({"architecture_approved": False}) == "system_architect"

def test_should_fix():
    assert should_fix({"test_success": True}) == "ui_designer"
    assert should_fix({"test_success": False, "fix_iteration": 3}) == "ui_designer"
    assert should_fix({"test_success": False, "fix_iteration": 1}) == "fix_analyzer"

def test_should_fix_app():
    assert should_fix_app({"app_valid": True}) == "reviewers_fanout"
    assert should_fix_app({"app_valid": False, "app_fix_iteration": 3}) == "reviewers_fanout"
    assert should_fix_app({"app_valid": False, "app_fix_iteration": 0}) == "fix_app"

def test_reviewers_fanout():
    fanout = reviewers_fanout({})
    assert "quality_reviewer" in fanout
    assert "senior_dev_reviewer" in fanout
    assert "architecture_reviewer" in fanout
