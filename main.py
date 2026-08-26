#!/usr/bin/env python3
"""
Jira Coder: AI-powered code generation from Jira tickets.

This is the main entry point for the application. It allows users to choose between different code generation modes.
"""
import subprocess
import sys
from config.settings import Settings
from graph.tdd_code import run_poc_graph
from graph.create_streamlit_app import run_unified_graph
from agents.jira_agent import jira_client
import json
import os

# Constants for mode selection and paths
MODE_TDD = "1"
MODE_UNIFIED = "2"
MODE_INCREMENTAL = "3"
MODE_COMPARE = "4"
MODE_LANGSMITH = "5"
MODE_DEMO_BASIC = "10"
MODE_DEMO_MEMORY = "11"
MODE_DEMO_BINARY = "12"
ARCHIVE_START = 20  # Archive apps start at mode 20
MAX_JIRA_RESULTS = 50
DEMO_BASIC_PATH = "demos/basic_calculator.py"
DEMO_MEMORY_PATH = "demos/calculator_with_memory.py"
DEMO_BINARY_PATH = "demos/calculator_with_binary.py"

def main():
    """
    Main function to run the Jira Coder application.

    Presents the user with a choice of modes:
    1. Generate Standalone Module: Creates a tested module from one or more tickets using a TDD workflow.
    2. Build Integrated Application: Creates a single, unified Streamlit application from multiple tickets.
    3. Run Calculator Demo: Launches a pre-built demo application.
    """
    # Ensure all env vars are present
    Settings.check()

    # Ask user for mode
    print("\n🔧 Jira Coder")
    print("\n📝 Generation Modes:")
    print("1. Generate Standalone code and tests (TDD workflow)")
    print("2. Build Integrated Application (full generation from tickets)")
    print("3. Incremental Update (add features AND regenerate UI)")
    print("4. Compare Archived Apps (show differences)")
    print("5. View LangSmith Stats (monitoring & costs)")
    print("\n🎬 Demo Apps:")
    print("10. Run Basic Calculator Demo")
    print("11. Run Calculator with Memory Demo")
    print("12. Run Calculator with Binary Mode Demo")
    
    # List archived apps starting at mode 20
    archive_dir = "archive"
    archive_modes = {}
    if os.path.exists(archive_dir):
        archives = [d for d in os.listdir(archive_dir) if os.path.isdir(os.path.join(archive_dir, d))]
        archives.sort(reverse=True)  # Newest first
        
        if archives:
            print("\n📦 Archived Apps:")
            for i, archive in enumerate(archives[:10]):  # Max 10 archives (modes 20-29)
                mode_num = ARCHIVE_START + i
                archive_path = os.path.join(archive_dir, archive)
                app_exists = os.path.exists(os.path.join(archive_path, "app.py"))
                status = "✅" if app_exists else "⚠️"
                
                # Try to get app name from README
                readme_path = os.path.join(archive_path, "README.md")
                app_name = None
                if os.path.exists(readme_path):
                    try:
                        with open(readme_path, 'r') as f:
                            first_line = f.readline().strip()
                            if first_line.startswith('#'):
                                app_name = first_line.lstrip('#').strip()
                    except:
                        pass
                
                # Extract timestamp from folder name
                parts = archive.split('_')
                timestamp = parts[-2] + '_' + parts[-1] if len(parts) >= 2 else archive
                
                if app_name:
                    display = f"{app_name} ({timestamp})"
                else:
                    display = archive[:60] + "..." if len(archive) > 60 else archive
                
                print(f"{mode_num}. {status} {display}")
                archive_modes[str(mode_num)] = archive
            
            print("\n💡 Tip: Use Mode 4 to compare archives")
    
    try:
        mode = input("\nChoose mode: ").strip() or MODE_UNIFIED
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Goodbye!")
        sys.exit(0)

    if mode == MODE_UNIFIED:
        # Mode 2: Build Integrated Application
        
        # Check if existing code exists
        existing_app = os.path.exists("app.py")
        existing_modules = os.path.exists("modules") and any(f.endswith('.py') and f != '__init__.py' for f in os.listdir("modules"))
        
        if existing_app or existing_modules:
            print("\n⚠️  Existing code detected!")
            if existing_app:
                print("   - app.py exists")
            if existing_modules:
                module_files = [f for f in os.listdir("modules") if f.endswith('.py') and f != '__init__.py']
                print(f"   - modules/ contains: {', '.join(module_files)}")
            
            print("\n🛡️  Options:")
            print("1. Backup and regenerate (saves to archive/)")
            print("2. Cancel and use Mode 3 (Incremental Update)")
            print("3. Overwrite without backup (DANGEROUS)")
            
            try:
                choice = input("\nChoose option (1-3): ").strip()
            except EOFError:
                choice = "2"
            
            if choice == "2":
                print("\nℹ️  Cancelled. Use Mode 3 for incremental updates.")
                return
            elif choice == "1":
                # Auto-backup
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_before_regen_{timestamp}"
                print(f"\n💾 Backing up to archive/{backup_name}/...")
                try:
                    subprocess.run(["python", "save_app.py", backup_name], check=True)
                    print("✅ Backup complete!")
                except Exception as e:
                    print(f"⚠️  Backup failed: {e}")
                    confirm = input("Continue anyway? (yes/no): ").strip().lower()
                    if confirm != "yes":
                        return
            elif choice == "3":
                confirm = input("\n⚠️  Are you SURE? This will delete existing code. Type 'DELETE' to confirm: ").strip()
                if confirm != "DELETE":
                    print("Cancelled.")
                    return
            else:
                print("Invalid choice. Exiting.")
                return
        
        try:
            project_key = input("\nEnter Jira project key (e.g., CAL): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Cancelled.")
            sys.exit(0)
        if not project_key:
            print("⚠️ No project key provided. Exiting.")
            return
        
        try:
            ticket_input = input("Enter ticket keys (comma-separated, or press Enter for ALL): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Cancelled.")
            sys.exit(0)
        
        if not ticket_input:
            # Load all tickets from project
            print(f"\n📦 Fetching all tickets from {project_key}...")
            result = jira_client.list_all_issues_in_project(project_key, max_results=MAX_JIRA_RESULTS)
            issues = result.get("issues", [])
            if not issues:
                print(f"⚠️ No tickets found in {project_key}. Details: {result.get('details')}")
                return
            ticket_keys = [issue.get("key") for issue in issues]
            print(f"Found {len(ticket_keys)} tickets: {', '.join(ticket_keys[:5])}{'...' if len(ticket_keys) > 5 else ''}")
        else:
            ticket_keys = [k.strip() for k in ticket_input.split(",") if k.strip()]
        
        print(f"\n🏗️ Building integrated application for {len(ticket_keys)} tickets...")
        run_unified_graph(project_key, ticket_keys)

    elif mode == MODE_COMPARE:
        # Mode 4: Compare Archives
        from compare_archives import get_archive_list, compare_archives
        
        archives = get_archive_list()
        if not archives:
            print("\n⚠️  No archives found.")
            return
        
        print("\n📦 Available Archives:")
        for i, archive in enumerate(archives[:10]):
            mode_num = ARCHIVE_START + i
            print(f"{mode_num}. {archive}")
        
        try:
            mode1 = input("\nFirst archive mode: ").strip()
            mode2 = input("Second archive mode: ").strip()
            compare_archives(int(mode1), int(mode2))
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled.")
            sys.exit(0)
        except (ValueError, EOFError):
            print("Invalid input.")
    
    elif mode == MODE_LANGSMITH:
        # Mode 5: View LangSmith Stats
        try:
            subprocess.run(["python3", "view_langsmith_stats.py"])
        except KeyboardInterrupt:
            print("\n")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\n💡 Make sure langsmith is installed: pip install langsmith")
    
    elif mode == MODE_INCREMENTAL:
        # Mode 3: Incremental Update
        from incremental_update import incremental_update
        
        try:
            ticket_input = input("Enter ticket keys to add (comma-separated, e.g., CAL-31,CAL-32): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Cancelled.")
            sys.exit(0)
        
        if not ticket_input:
            print("⚠️ No ticket keys provided. Exiting.")
            return
        
        ticket_keys = [k.strip().upper() for k in ticket_input.split(",") if k.strip()]
        print(f"\n🔄 Incremental update for {len(ticket_keys)} tickets...")
        incremental_update(ticket_keys)
    
    elif mode == MODE_DEMO_BASIC:
        # Mode 10: Run basic calculator demo
        print(f"\n🚀 Launching Basic Calculator Demo...")
        if os.path.exists(DEMO_BASIC_PATH):
            try:
                subprocess.run(["streamlit", "run", DEMO_BASIC_PATH])
            except KeyboardInterrupt:
                print("\n\n👋 Demo stopped.")
                sys.exit(0)
        else:
            print(f"⚠️  Demo not found at '{DEMO_BASIC_PATH}'.")
            print("   Run Mode 2 to generate a basic calculator first.")
    
    elif mode == MODE_DEMO_MEMORY:
        # Mode 11: Run calculator with memory demo
        print(f"\n🚀 Launching Calculator with Memory Demo...")
        if os.path.exists(DEMO_MEMORY_PATH):
            try:
                subprocess.run(["streamlit", "run", DEMO_MEMORY_PATH])
            except KeyboardInterrupt:
                print("\n\n👋 Demo stopped.")
                sys.exit(0)
        else:
            print(f"⚠️  Demo not found at '{DEMO_MEMORY_PATH}'.")
            print("   This demo shows memory functions (M+, MR, MC).")
    
    elif mode == MODE_DEMO_BINARY:
        # Mode 12: Run binary calculator demo
        print(f"\n🚀 Launching Calculator with Binary Mode Demo...")
        if os.path.exists(DEMO_BINARY_PATH):
            try:
                subprocess.run(["streamlit", "run", DEMO_BINARY_PATH])
            except KeyboardInterrupt:
                print("\n\n👋 Demo stopped.")
                sys.exit(0)
        else:
            print(f"⚠️  Demo not found at '{DEMO_BINARY_PATH}'.")
            print("   This demo shows binary mode with DEC/BIN toggle.")
    
    elif mode in archive_modes:
        # Modes 20+: Run archived app
        selected = archive_modes[mode]
        app_path = os.path.join(archive_dir, selected, "app.py")
        
        if os.path.exists(app_path):
            print(f"\n🚀 Launching {selected}...")
            try:
                subprocess.run(["streamlit", "run", app_path])
            except KeyboardInterrupt:
                print("\n\n👋 Demo stopped.")
                sys.exit(0)
        else:
            print(f"\n⚠️  app.py not found in {selected}")
    
    else: # mode == MODE_TDD or default to 1
        # Mode 1: Generate Standalone Module (can be single or bulk)
        # For Mode 1, we only need the ticket key.
        ticket_key = input("Enter a single Jira ticket key (e.g., CAL-1): ").strip().upper()
        if not ticket_key:
            print("⚠️ No ticket key provided. Exiting.")
            return
        
        print(f"\n--- Processing {ticket_key} with TDD workflow ---")
        status = "✅ success"
        try:
            run_poc_graph(ticket_key)
        except Exception as e:
            print(f"⚠️ Error processing {ticket_key}: {e}")
            status = f"❌ error: {e}"
        
        # For a single ticket, just print the result directly
        print("\n" + "="*60)
        print(f"📊 TDD Generation Result for {ticket_key}")
        print("="*60)
        print(f"{ticket_key}: {status}")
        print("="*60)
        
        # No manifest for single ticket, as it's not a bulk run

if __name__ == "__main__":
    main()
