# config/settings.py
"""
Central configuration for the Jira–GitHub LangGraph PoC.
Loads environment variables safely using python-dotenv.
"""

from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

class Settings:
    # === Core API Keys ===
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

    # === Jira Settings ===
    JIRA_BASE = os.getenv("JIRA_BASE")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "CAL")
    JIRA_BOARD_ID = os.getenv("JIRA_BOARD_ID", "34")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "CAL")
    JIRA_BOARD_ID = os.getenv("JIRA_BOARD_ID", "34")

    # === GitHub Defaults ===
    GITHUB_REPO = os.getenv("GITHUB_REPO", "org/repo-name")
    GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

    # === Runtime Options ===
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    @classmethod
    def check(cls):
        """Validate required environment variables are loaded."""
        required = ["OPENAI_API_KEY", "GITHUB_TOKEN", "JIRA_API_TOKEN"]
        missing = [k for k in required if not getattr(cls, k, None)]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {missing}")

    @classmethod
    def info(cls):
        """Print safe summary (without revealing secrets)."""
        print("\n🔧 Configuration Summary:")
        print(f"  Environment: {cls.ENV}")
        print(f"  Debug Mode: {cls.DEBUG}")
        print(f"  Jira Base: {cls.JIRA_BASE}")
        print(f"  GitHub Repo: {cls.GITHUB_REPO} ({cls.GITHUB_BRANCH})")
        print("  API Keys: [Loaded ✅]" if cls.OPENAI_API_KEY else "  API Keys: [Missing ⚠️]")
        print("")

# Run a quick test when executed directly
if __name__ == "__main__":
    try:
        Settings.check()
        Settings.info()
        print("✅ All environment variables loaded successfully.")
    except EnvironmentError as e:
        print(f"❌ {e}")