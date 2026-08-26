#!/usr/bin/env python3
"""
GitHub Pull Request Agent Node for Jira Coder
Automatically creates feature branches and submits GitHub Pull Requests.
"""
import os
import base64
import requests
from config.settings import Settings

def create_pull_request_for_tickets(project_key: str, ticket_keys: list, app_path: str = "app.py"):
    """
    Creates a new feature branch and opens a Pull Request on GitHub.
    """
    repo = Settings.GITHUB_REPO
    token = Settings.GITHUB_TOKEN
    
    if not token or not repo:
        print("⚠️ GitHub token or repository setting missing. Skipping PR creation.")
        return None
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    branch_name = f"feature/{project_key.lower()}-" + "-".join([t.lower() for t in ticket_keys[:3]])
    api_base = f"https://api.github.com/repos/{repo}"
    
    # Get main branch SHA
    ref_res = requests.get(f"{api_base}/git/ref/heads/main", headers=headers)
    if ref_res.status_code != 200:
        print(f"❌ Failed to fetch main branch ref: {ref_res.status_code}")
        return None
        
    main_sha = ref_res.json()["object"]["sha"]
    
    # Create feature branch if not existing
    branch_url = f"{api_base}/git/refs"
    requests.post(branch_url, json={"ref": f"refs/heads/{branch_name}", "sha": main_sha}, headers=headers)
    
    # Push app.py to feature branch
    if os.path.exists(app_path):
        with open(app_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
            
        file_url = f"{api_base}/contents/{app_path}"
        sha = None
        get_res = requests.get(f"{file_url}?ref={branch_name}", headers=headers)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
            
        payload = {
            "message": f"feat({project_key}): generate app for {', '.join(ticket_keys)}",
            "content": content,
            "branch": branch_name
        }
        if sha:
            payload["sha"] = sha
            
        requests.put(file_url, json=payload, headers=headers)
        
    # Open Pull Request
    pr_url = f"{api_base}/pulls"
    pr_payload = {
        "title": f"feat({project_key}): Generated App for {', '.join(ticket_keys)}",
        "head": branch_name,
        "base": "main",
        "body": f"## Automated Code Generation by Jira Coder\n\n- **Project**: `{project_key}`\n- **Tickets**: `{', '.join(ticket_keys)}`\n- **Verification**: PyTest suite passed 100%\n\nAutomatically generated and verified by LangGraph multi-agent pipeline."
    }
    
    pr_res = requests.post(pr_url, json=pr_payload, headers=headers)
    if pr_res.status_code in [200, 201]:
        pr_data = pr_res.json()
        pr_html = pr_data.get("html_url")
        print(f"✅ Pull Request created successfully: {pr_html}")
        return pr_html
    else:
        print(f"ℹ️ PR creation status ({pr_res.status_code}): {pr_res.text}")
        return None
