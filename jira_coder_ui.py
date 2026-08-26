#!/usr/bin/env python3
"""
Jira Coder - Streamlit Web UI
AI-powered code generation from Jira tickets & Interactive Code Set Launcher
"""
import streamlit as st
import subprocess
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Page config
st.set_page_config(
    page_title="Jira Coder",
    page_icon="🔧",
    layout="wide"
)

# Initialize session state
if 'generation_running' not in st.session_state:
    st.session_state.generation_running = False
if 'log_output' not in st.session_state:
    st.session_state.log_output = []
if 'active_code_set_label' not in st.session_state:
    st.session_state.active_code_set_label = "Current Generated App"

# Header
st.title("🔧 Jira Coder")
st.markdown("AI-powered code generation & Interactive App Viewer")

def get_env_or_secret(key_name: str, default: str = "") -> str:
    """Helper to check os.getenv (.env) and st.secrets (Streamlit Cloud)."""
    val = os.getenv(key_name, "")
    if val and not str(val).startswith("your_"):
        return str(val)
    try:
        if hasattr(st, "secrets") and key_name in st.secrets:
            sec_val = st.secrets[key_name]
            if sec_val and not str(sec_val).startswith("your_"):
                os.environ[key_name] = str(sec_val)
                return str(sec_val)
    except Exception:
        pass
    return default

# Detect whether owner credentials exist in environment or Streamlit Secrets
current_key = get_env_or_secret("OPENAI_API_KEY")
current_jira_base = get_env_or_secret("JIRA_BASE", "https://reg-hawkins.atlassian.net")
current_jira_email = get_env_or_secret("JIRA_EMAIL")
current_jira_token = get_env_or_secret("JIRA_API_TOKEN")
current_jira_proj = get_env_or_secret("JIRA_PROJECT_KEY", "KAN")

has_valid_creds = bool(current_key and not current_key.startswith("your_"))

# Sidebar - Credentials Manager
with st.sidebar.expander("🔑 API Credentials & Settings", expanded=not has_valid_creds):
    if has_valid_creds:
        st.success("✅ Owner credentials loaded from environment / secrets")
    else:
        st.warning("⚠️ No OpenAI API key detected. Please enter your key below to generate code.")
        
    st.caption("Provide your own API keys for this session:")
    user_openai_key = st.text_input("OpenAI API Key", value=current_key, type="password")
    user_jira_base = st.text_input("Jira Base URL", value=current_jira_base)
    user_jira_email = st.text_input("Jira Email", value=current_jira_email)
    user_jira_token = st.text_input("Jira API Token", value=current_jira_token, type="password")
    user_jira_proj = st.text_input("Default Jira Project", value=current_jira_proj)

    
    if st.button("💾 Apply Session Credentials"):
        if user_openai_key:
            os.environ["OPENAI_API_KEY"] = user_openai_key
        if user_jira_base:
            os.environ["JIRA_BASE"] = user_jira_base
        if user_jira_email:
            os.environ["JIRA_EMAIL"] = user_jira_email
        if user_jira_token:
            os.environ["JIRA_API_TOKEN"] = user_jira_token
        if user_jira_proj:
            os.environ["JIRA_PROJECT_KEY"] = user_jira_proj
        st.session_state.custom_credentials_applied = True
        st.success("✅ Credentials updated for session!")
        st.rerun()

st.sidebar.markdown("---")


# Sidebar - Code Set Launcher
st.sidebar.header("🚀 Code Set Launcher")

# Build code set options mapping: label -> dir_or_script
code_set_options = {}

if os.path.exists("app.py"):
    code_set_options["Current Generated App (app.py)"] = {"app": "app.py", "dir": "."}

if os.path.exists("archive"):
    archives = sorted([d for d in os.listdir("archive") if os.path.isdir(os.path.join("archive", d))], reverse=True)
    for arch in archives:
        arch_dir = os.path.join("archive", arch)
        arch_app = os.path.join(arch_dir, "app.py")
        if os.path.exists(arch_app):
            code_set_options[f"Archive: {arch}"] = {"app": arch_app, "dir": arch_dir}

code_set_options["Demo: Basic Calculator"] = {"app": "demos/basic_calculator.py", "dir": "demos"}
code_set_options["Demo: Calculator with Memory"] = {"app": "demos/calculator_with_memory.py", "dir": "demos"}
code_set_options["Demo: Calculator with Binary"] = {"app": "demos/calculator_with_binary.py", "dir": "demos"}

selected_label = st.sidebar.selectbox("Select Code Set to Load:", list(code_set_options.keys()))
target_info = code_set_options[selected_label]

if st.sidebar.button("▶️ Load & Activate Selected Code Set", type="primary"):
    target_app = target_info["app"]
    target_dir = target_info["dir"]
    
    # Copy app.py
    if os.path.exists(target_app):
        shutil.copy2(target_app, "app.py")
    
    # Copy associated modules if loading from archive
    arch_modules = os.path.join(target_dir, "modules")
    if os.path.exists(arch_modules):
        if os.path.exists("modules"):
            shutil.rmtree("modules")
        shutil.copytree(arch_modules, "modules")
        
    arch_tests = os.path.join(target_dir, "generated_tests")
    if os.path.exists(arch_tests):
        if os.path.exists("generated_tests"):
            shutil.rmtree("generated_tests")
        shutil.copytree(arch_tests, "generated_tests")

    st.session_state.active_code_set_label = selected_label
    st.sidebar.success(f"✅ Active code set: {selected_label}")
    st.rerun()

st.sidebar.info(f"Active: **{st.session_state.active_code_set_label}**")
st.sidebar.markdown("---")

# Navigation Tabs in Main View
tab1, tab2 = st.tabs(["📱 Interactive App View (Live Application)", "⚙️ Generator Dashboard & Jira Config"])

with tab1:
    st.header(f"Live Application — {st.session_state.active_code_set_label}")
    st.caption("Interact with your loaded Streamlit application directly below:")
    st.markdown("---")
    
    # Execute current app.py in an isolated namespace for direct interactive rendering
    if os.path.exists("app.py"):
        try:
            # Ensure current directory is in sys.path
            if "." not in sys.path:
                sys.path.insert(0, ".")
            
            with open("app.py", "r", encoding="utf-8") as f:
                app_code = f.read()
            
            # Execute app script
            exec(compile(app_code, "app.py", "exec"), {"__name__": "__main__"})
        except Exception as e:
            st.error(f"❌ Error rendering app.py: {e}")
            st.exception(e)
    else:
        st.warning("No app.py found. Please select a code set from the sidebar and click 'Load & Activate'.")

with tab2:
    st.header("Generator Dashboard & Settings")
    
    if not has_valid_creds:
        st.warning("⚠️ **API Credentials Required**: No OpenAI or Jira API key detected for this session. Please open **'🔑 API Credentials & Settings'** in the sidebar to enter your own API key to generate code.")

    
    # Sidebar - Mode Selection inside Tab 2 context
    st.sidebar.header("Mode Selection")
    mode = st.sidebar.radio(
        "Choose Mode:",
        [
            "1. TDD Workflow",
            "2. Full Generation",
            "3. Incremental Update",
            "4. Compare Archives",
            "10. Demo: Basic Calculator",
            "11. Demo: Calculator with Memory",
            "12. Demo: Calculator with Binary",
        ]
    )
    
    mode_num = mode.split(".")[0]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Configuration")
        
        if mode_num in ["1", "2", "3"]:
            if mode_num == "1":
                st.subheader("TDD Workflow - Single Ticket")
                ticket_key = st.text_input("Jira Ticket Key", placeholder="KAN-1")
                
                if st.button("Generate Module", type="primary"):
                    if ticket_key:
                        st.session_state.generation_running = True
                        with st.spinner(f"Generating module for {ticket_key}..."):
                            try:
                                result = subprocess.run(
                                    ["python3", "main.py"],
                                    input=f"1\n{ticket_key}\n",
                                    capture_output=True,
                                    text=True,
                                    timeout=300
                                )
                                st.success("✅ Generation complete!")
                                st.code(result.stdout, language="text")
                                if result.stderr:
                                    st.error(result.stderr)
                            except subprocess.TimeoutExpired:
                                st.error("⏱️ Generation timed out (5 min limit)")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                            finally:
                                st.session_state.generation_running = False
                    else:
                        st.warning("Please enter a ticket key")
            
            elif mode_num == "2":
                st.subheader("Full Generation - Multiple Tickets")
                
                if os.path.exists("app.py") or (os.path.exists("modules") and any(f.endswith('.py') for f in os.listdir("modules"))):
                    st.warning("⚠️ Existing code detected!")
                    backup_option = st.radio(
                        "Choose action:",
                        ["Backup and regenerate", "Cancel", "Overwrite (DANGEROUS)"]
                    )
                else:
                    backup_option = None
                
                from config.settings import Settings
                default_proj = os.getenv("JIRA_PROJECT_KEY", Settings.JIRA_PROJECT_KEY or "CAL")
                project_key = st.text_input("Project Key", value=default_proj)
                ticket_input = st.text_input("Ticket Keys (comma-separated, or leave empty for ALL)", placeholder=f"{default_proj}-1,{default_proj}-2,{default_proj}-3")
                
                if st.button("Generate Application", type="primary"):
                    if backup_option == "Cancel":
                        st.info("ℹ️ Cancelled. Use Mode 3 for incremental updates.")
                    elif backup_option == "Overwrite (DANGEROUS)":
                        confirm = st.text_input("Type 'DELETE' to confirm:")
                        if confirm != "DELETE":
                            st.error("Confirmation required")
                            st.stop()
                    
                    if project_key:
                        st.session_state.generation_running = True
                        with st.spinner(f"Generating application for {project_key}..."):
                            try:
                                input_text = f"2\n{project_key}\n{ticket_input}\n"
                                if backup_option == "Backup and regenerate":
                                    input_text = f"2\n1\n{project_key}\n{ticket_input}\n"
                                
                                result = subprocess.run(
                                    ["python3", "main.py"],
                                    input=input_text,
                                    capture_output=True,
                                    text=True,
                                    timeout=600
                                )
                                st.success("✅ Generation complete!")
                                st.code(result.stdout, language="text")
                                if result.stderr:
                                    st.error(result.stderr)
                            except subprocess.TimeoutExpired:
                                st.error("⏱️ Generation timed out (10 min limit)")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                            finally:
                                st.session_state.generation_running = False
                    else:
                        st.warning("Please enter a project key")
            
            elif mode_num == "3":
                st.subheader("Incremental Update - Add Features")
                ticket_keys = st.text_input("Ticket Keys to Add", placeholder="KAN-1,KAN-2")
                
                if st.button("Add Features", type="primary"):
                    if ticket_keys:
                        st.session_state.generation_running = True
                        with st.spinner(f"Adding features from {ticket_keys}..."):
                            try:
                                result = subprocess.run(
                                    ["python3", "main.py"],
                                    input=f"3\n{ticket_keys}\n",
                                    capture_output=True,
                                    text=True,
                                    timeout=300
                                )
                                st.success("✅ Features added!")
                                st.code(result.stdout, language="text")
                                if result.stderr:
                                    st.error(result.stderr)
                            except subprocess.TimeoutExpired:
                                st.error("⏱️ Update timed out (5 min limit)")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                            finally:
                                st.session_state.generation_running = False
                    else:
                        st.warning("Please enter ticket keys")
        
        elif mode_num == "4":
            st.subheader("Compare Archived Apps")
            archive_dir = "archive"
            if os.path.exists(archive_dir):
                archives = [d for d in os.listdir(archive_dir) if os.path.isdir(os.path.join(archive_dir, d))]
                archives.sort(reverse=True)
                
                if archives:
                    archive_options = {f"{20+i}. {arch}": arch for i, arch in enumerate(archives[:10])}
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        archive1 = st.selectbox("First Archive", options=list(archive_options.keys()))
                    with col_b:
                        archive2 = st.selectbox("Second Archive", options=list(archive_options.keys()))
                    
                    if st.button("Compare", type="primary"):
                        mode1 = int(archive1.split(".")[0])
                        mode2 = int(archive2.split(".")[0])
                        
                        with st.spinner("Comparing archives..."):
                            try:
                                result = subprocess.run(
                                    ["python3", "compare_archives.py", str(mode1), str(mode2)],
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )
                                st.code(result.stdout, language="diff")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                else:
                    st.info("No archives found.")
            else:
                st.info("No archive directory found.")

    with col2:
        st.header("Status")
        if os.path.exists("app.py"):
            st.success("✅ app.py exists")
            if st.button("View app.py"):
                with open("app.py", "r") as f:
                    st.code(f.read(), language="python")
        
        if os.path.exists("modules"):
            modules = [f for f in os.listdir("modules") if f.endswith('.py') and f != '__init__.py']
            if modules:
                st.success(f"✅ {len(modules)} modules")
                selected_module = st.selectbox("View module:", modules)
                if selected_module:
                    with open(f"modules/{selected_module}", "r") as f:
                        st.code(f.read(), language="python")

# Quick Actions Footer in Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Actions")
if st.sidebar.button("🐙 Create GitHub Pull Request"):
    from agents.github_pr_agent import create_pull_request_for_tickets
    from config.settings import Settings
    current_project = os.getenv("JIRA_PROJECT_KEY", Settings.JIRA_PROJECT_KEY or "PROJ")
    with st.sidebar.spinner("Creating GitHub PR..."):
        pr_link = create_pull_request_for_tickets(current_project, [f"{current_project}-1", f"{current_project}-2"])
        if pr_link:
            st.sidebar.success(f"✅ PR Created: [View PR →]({pr_link})")
        else:
            st.sidebar.info("PR creation checked (see log details)")


if st.sidebar.button("🗂️ Open Archive Folder"):
    st.sidebar.code("archive/", language="text")
if st.sidebar.button("📊 View Test Results"):
    if os.path.exists("generated_tests/.report.json"):
        import json
        with open("generated_tests/.report.json", "r") as f:
            report = json.load(f)
            st.sidebar.json(report)
    else:
        st.sidebar.info("No test results yet")

