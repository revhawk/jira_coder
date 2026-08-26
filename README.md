# Jira Code Generator

AI-powered code generation from Jira tickets using LangGraph, featuring multiple specialized agents for TDD and full-stack application generation.

## 🌐 Web UI Available!

```bash
streamlit run jira_coder_ui.py
```

Visual interface with real-time feedback, code viewing, and archive management. See [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) for details.

## Features

- **Unified App Generation**: Multiple Jira tickets → One cohesive Streamlit application
- **TDD Workflow**: Generates standalone, tested modules from single tickets.
- **Multi-Agent Workflow**: Architecture design, spec extraction, code generation, testing, and validation
- **Automatic Fixing**: Auto-fixes failing tests and Streamlit app errors
- **Cost Optimized**: Uses `gpt-4o-mini` for a balance of performance and cost.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file with your Jira and OpenAI credentials:

```bash
# Jira Configuration
JIRA_BASE=https://reg-hawkins.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=KAN
JIRA_BOARD_ID=1

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# GitHub Configuration
GITHUB_TOKEN=your_github_token
GITHUB_REPO=revhawk/jira_coder

# LangSmith Tracing (Optional - for monitoring and debugging)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=jira-code-generator
```

### 3. Run Jira Coder

**Option A: Web UI Dashboard (Recommended)**
```bash
PYTHONPATH=.deps:. streamlit run jira_coder_ui.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser. Features live app interactive view and an archive launcher.

**Option B: Podman / Docker Container**
```bash
podman-compose up --build
# OR
docker-compose up --build
```

**Option C: Command Line**
```bash
PYTHONPATH=.deps:. python3 main.py
```

### 4. Deploy Live to Streamlit Cloud

1. Push latest code to GitHub: `PYTHONPATH=.deps:. python3 push_to_github.py`
2. Open [https://share.streamlit.io/deploy](https://share.streamlit.io/deploy)
3. Set **Repository**: `revhawk/jira_coder`, **Branch**: `main`, **Main file path**: `jira_coder_ui.py` (or `app.py`).
4. Click **Deploy!**


Choose mode:
1. **TDD Workflow** - Standalone module from single ticket
2. **Full Generation** - Complete app from multiple tickets
3. **Incremental Update** - Add features without regenerating
4. **Compare Archives** - View differences between versions
5. **LangSmith Stats** - View monitoring and costs
10-12. **Demos** - Run example calculators
20+. **Archives** - Run previously generated apps

## System Architecture

```mermaid
flowchart TD
    subgraph Inputs ["Inputs & User Interfaces"]
        UI["Streamlit Web UI (jira_coder_ui.py)"]
        CLI["CLI Launcher (main.py)"]
        JIRA[("Jira API\n(Tickets & EPICs)")]
    end

    subgraph Core ["LangGraph Multi-Agent Engine"]
        HC["1. health_check"] --> JR["2. jira_reader"]
        JR --> SA["3. system_architect"]
        SA --> RA["4. requirements_analyzer"]
        
        RA -->|"Approved"| SA_SPEC["5. spec_agent"]
        RA -->|"Rejected / Retry"| SA
        
        SA_SPEC --> SR["6. spec_reviewer"]
        SR --> GT["7. generate_tests"]
        GT --> CM["8. code_merger"]
        CM --> GC["9. generate_code"]
        GC --> VM["10. validate_modules"]
        VM --> RT["11. run_tests"]
        
        RT -->|"Tests Fail"| FA["12. fix_analyzer & fixer_agent"]
        FA -->|"Retry Loop"| GC
        
        RT -->|"Tests Pass"| UI_D["13. ui_designer & generate_main_app"]
        UI_D --> QR["14. quality & architecture reviewers"]
    end

    subgraph Outputs ["Generated Outputs & Artifacts"]
        MODS["Python Modules\n(modules/)"]
        TESTS["PyTest Test Files\n(generated_tests/)"]
        APP["Main Streamlit App\n(app.py)"]
        SMITH[("LangSmith Tracing &\nCost Tracking")]
    end

    UI --> Core
    CLI --> Core
    JIRA <--> JR
    
    Core --> MODS
    Core --> TESTS
    Core --> APP
    Core -.-> SMITH
```

## Workflow Architecture

**20 Specialized AI Agents** orchestrated by LangGraph. See [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) for complete details.

### Key Agents
1.  **jira_reader**: Fetches tickets and EPIC from Jira
2.  **system_architect**: Designs modules and functions (context-aware)
3.  **requirements_analyzer**: Validates against EPIC constraints
4.  **spec_agent**: Generates detailed specifications
5.  **generate_tests**: Creates pytest test files
6.  **code_merger** ⭐: Merges new functions without deleting existing code
7.  **generate_code**: Implements business logic
8.  **ui_designer**: Chooses optimal UI pattern
9.  **generate_main_app**: Creates Streamlit UI
10. **fix_analyzer** + **fixer_agent**: Auto-fixes failing tests
11. **quality_reviewer** + **senior_dev_reviewer** + **architecture_reviewer**: Final reviews


## Generated Structure

```
modules/
  calculator.py          # Business logic modules
  validator.py
  __init__.py
generated_tests/
  test_calculator.py     # Pytest tests
  test_validator.py
app.py                   # Main Streamlit application
```

## Running Generated Apps

**From Web UI:**
- Generated apps appear in the Status panel
- Click "View app.py" to see the code
- Run demos directly from the UI

**From Command Line:**
```bash
streamlit run app.py
```

## Testing

### Run Connection Tests

```bash
python -m tests.test_connections
```

### Run Generated Module Tests

```bash
python -m pytest generated_tests/ -v
```

### View Test Results in Web UI

1. Launch web UI: `streamlit run jira_coder_ui.py`
2. Click "📊 View Test Results" in sidebar
3. See pass/fail counts and details

## Documentation

- [README.md](README.md) - This file (quick start)
- [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) - Streamlit UI guide
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - Agent structure and details
- [WORKFLOW_FLOWCHART.md](WORKFLOW_FLOWCHART.md) - Complete workflow diagrams
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Reference Examples

Add proven working patterns to `reference_examples/streamlit_apps/`:

- `calculator_button_grid.py` - Button grid layout with st.rerun()
- `sidebar_navigation.py` - Multi-page sidebar navigation

The workflow automatically loads and uses these examples.

## Jira Configuration

### Board ID Setup

For CAL project, board ID is 34. Configure in `.env`:

```bash
JIRA_PROJECT_KEY=CAL
JIRA_BOARD_ID=34
```

The system uses Jira Agile API directly (skips GET/POST that return 410).

### EPIC Requirements

Create an EPIC ticket with description containing:
- Application requirements
- Constraints (e.g., "simple", "no complex state management")
- Architecture preferences

Link all feature tickets to the EPIC.

## LangSmith Monitoring

LangSmith provides real-time tracing and monitoring of all agent executions.

### Setup

1. Create account at https://smith.langchain.com/
2. Get API key from Settings → API Keys
3. Add to `.env`:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=jira-code-generator
```

### View Stats

- **Dashboard**: https://smith.langchain.com/
- **Traces**: Full execution logs for each agent
- **Token Usage**: Real-time cost tracking
- **Latency**: Response times per agent
- **Errors**: Detailed failure analysis

## Cost Optimization

- **o1 model** ($15/$60 per 1M tokens): Architecture, specs, requirements
- **gpt-4o-mini** ($0.15/$0.60 per 1M tokens): Code generation, tests, UI, fixes
- **Estimated cost**: ~$0.50-$2 per unified app generation

## Troubleshooting

### Module Import Errors

Run from project root with `-m` flag:
```bash
python -m tests.test_connections
```

### Streamlit App Not Updating

- Restart Streamlit server: `Ctrl+C` then `streamlit run app.py`
- Hard refresh browser: `Ctrl+Shift+R`
- Check logs in `logs/unified_*.log`
- View logs in Web UI: Click "View Latest Log" in Status panel

### Test Failures

Check `logs/unified_*.log` for detailed error messages. The workflow auto-fixes tests up to loop detection limit.

### Web UI Issues

- Ensure port 8501 is available
- Check `.env` file has all required keys
- View status panel for file existence checks

## Examples

### Demo Apps (Modes 10-12)
- **Mode 10**: Basic calculator (digits + operators)
- **Mode 11**: Calculator with memory (M+, MR, MC)
- **Mode 12**: Calculator with binary mode (DEC/BIN toggle)

### Archived Apps (Modes 20+)
Previously generated apps are auto-discovered and listed.
Use Mode 4 to compare any two archives.

### Full Example
See `simple_calculator/` for a complete working example generated from 30 Jira tickets.

## Contributing

To add new reference examples:
1. Create working Streamlit app
2. Add to `reference_examples/streamlit_apps/`
3. Include docstring with pattern name and use case
4. Update `ui_designer` to detect the pattern

## License

MIT
