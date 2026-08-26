"""
Unit tests for Smart Credential Detection (Owner Mode vs. Guest Mode) logic.
"""
import os
import pytest

def is_owner_credentials_valid(api_key: str) -> bool:
    """Helper function reflecting UI credential detection logic."""
    return bool(api_key and not api_key.startswith("your_"))

def test_owner_credentials_detected(monkeypatch):
    """Test that valid API keys are detected as Owner Mode."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-validtoken123456789")
    key = os.getenv("OPENAI_API_KEY", "")
    assert is_owner_credentials_valid(key) is True

def test_placeholder_credentials_detected_as_guest_mode(monkeypatch):
    """Test that placeholder 'your_...' keys are detected as Guest Mode."""
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key")
    key = os.getenv("OPENAI_API_KEY", "")
    assert is_owner_credentials_valid(key) is False

def test_missing_credentials_detected_as_guest_mode(monkeypatch):
    """Test that empty/missing keys trigger Guest Mode warning."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    key = os.getenv("OPENAI_API_KEY", "")
    assert is_owner_credentials_valid(key) is False
