# Jira Coder - Agent Architecture

## Overview

Jira Coder uses a **multi-agent architecture** orchestrated by LangGraph. Each agent is a specialized AI component that performs a specific task in the code generation pipeline.

---

## Agent Structure

### Core Agents (14 Total)

```mermaid
flowchart TD
    HC["1. health_check\n(Verifies APIs)"] --> JR["2. jira_reader\n(Fetches tickets + EPIC)"]
    JR --> SA["3. system_architect\n(Designs modules & functions)"]
    SA --> RA["4. requirements_analyzer\n(Validates EPIC constraints)"]
    
    RA -->|"APPROVED"| SA_SPEC["5. spec_agent\n(Generates detailed specs)"]
    RA -->|"REJECTED"| SA
    
    SA_SPEC --> SR["6. spec_reviewer\n(Reviews spec completeness)"]
    SR --> GT["7. generate_tests\n(Creates pytest files)"]
    GT --> CM["8. code_merger\n(Merges functions safely)"]
    CM --> GC["9. generate_code\n(Implements business logic)"]
    GC --> VM["10. validate_modules\n(Verifies function existence)"]
    VM --> RT["11. run_tests\n(Executes pytest suite)"]
    
    RT -->|"FAIL"| FA["12. fix_analyzer & fixer_agent\n(Auto-fixes failing tests)"]
    FA -->|"Retry Loop"| GC
    
    RT -->|"PASS"| UI_D["13. ui_designer & generate_main_app\n(Creates Streamlit UI)"]
    UI_D --> VA["14. validate_app & fix_app\n(UI Validation Loop)"]
    
    VA -->|"Parallel Fan-Out"| QR["quality_reviewer"]
    VA -->|"Parallel Fan-Out"| SR_REV["senior_dev_reviewer"]
    VA -->|"Parallel Fan-Out"| AR_REV["architecture_reviewer"]
    
    QR --> END_NODE(("END"))
    SR_REV --> END_NODE
    AR_REV --> END_NODE
```

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT WORKFLOW                      │
│                  (LangGraph Orchestration)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  1. health_check                        │
        │  Verifies Jira & OpenAI connections     │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  2. jira_reader                         │
        │  Fetches tickets + EPIC from Jira       │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  3. system_architect                    │
        │  Designs modules & functions            │
        │  Model: gpt-4o (complex reasoning)      │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  4. requirements_analyzer               │
        │  Validates against EPIC constraints     │
        │  Rejects FSM if "simple" required       │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
            APPROVED            REJECTED
                │                   │
                │                   └──→ Regenerate (max 3x)
                │
                ▼
        ┌─────────────────────────────────────────┐
        │  5. spec_agent                          │
        │  Generates detailed specifications      │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  6. spec_reviewer                       │
        │  Reviews specs for completeness         │
        │  Model: gpt-4o-mini                     │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  7. generate_tests                      │
        │  Creates pytest test files              │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  8. code_merger ⭐ NEW                   │
        │  Merges new functions into existing     │
        │  Preserves all existing code            │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  9. generate_code                       │
        │  Implements business logic              │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  10. validate_modules                   │
        │  Checks function existence              │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  11. run_tests                          │
        │  Executes pytest                        │
        └─────────────────┬───────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
              PASS                FAIL
                │                   │
                │                   ▼
                │         ┌─────────────────────┐
                │         │  12. fix_analyzer   │
                │         │  Analyzes failures  │
                │         └──────────┬──────────┘
                │                    │
                │                    ▼
                │         ┌─────────────────────┐
                │         │  13. fixer_agent    │
                │         │  Fixes code/tests   │
                │         └──────────┬──────────┘
                │                    │
                │                    └──→ Loop back to run_tests
                │
                ▼
        ┌─────────────────────────────────────────┐
        │  14. ui_designer                        │
        │  Chooses UI pattern (button_grid/etc)   │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  15. generate_main_app                  │
        │  Creates Streamlit UI (app.py)          │
        │  Model: gpt-4o                          │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  16. validate_app                       │
        │  Checks for common Streamlit errors     │
        └─────────────────┬───────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
               OK                ERRORS
                │                   │
                │                   ▼
                │         ┌─────────────────────┐
                │         │  17. fix_app        │
                │         │  Fixes UI errors    │
                │         └──────────┬──────────┘
                │                    │
                │                    └──→ Loop back (max 3x)
                │
                ▼
        ┌─────────────────────────────────────────┐
        │  18. quality_reviewer                   │
        │  Reviews test/code quality              │
        │  Model: gpt-4o-mini                     │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  19. senior_dev_reviewer                │
        │  Checks if app will run                 │
        │  Model: gpt-4o-mini                     │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  20. architecture_reviewer              │
        │  Scores architecture (0-10)             │
        │  Model: gpt-4o-mini                     │
        └─────────────────┬───────────────────────┘
                          │
                          ▼
                        DONE
```

---

## Agent Details

### 1. health_check
**Purpose:** Verify external service connections  
**Checks:** OpenAI API, Jira API, project access  
**Output:** `health_ok: bool`  
**Model:** None (API calls only)

### 2. jira_reader
**Purpose:** Fetch Jira tickets and EPIC  
**Input:** Project key, ticket keys  
**Output:** List of tickets with descriptions, EPIC requirements  
**Model:** None (Jira API)  
**File:** `agents/jira_agent.py`

### 3. system_architect
**Purpose:** Design application architecture  
**Input:** Tickets, EPIC description  
**Output:** JSON with modules, functions, purposes  
**Model:** gpt-4o (complex reasoning)  
**Temperature:** 0.2  
**Prompt:** `prompts/unified_system_architect.txt`  
**Key Feature:** Context-aware (simple apps → simple architecture)

### 4. requirements_analyzer
**Purpose:** Validate architecture against EPIC  
**Input:** Architecture plan, EPIC requirements  
**Output:** APPROVED/REJECTED with reason  
**Model:** gpt-4o  
**Max Retries:** 3  
**Key Feature:** Rejects FSM/classes if EPIC says "simple"

### 5. spec_agent
**Purpose:** Generate detailed implementation specs  
**Input:** Module info, related tickets  
**Output:** JSON with function signatures, edge cases, acceptance criteria  
**Model:** gpt-4o  
**Temperature:** 0.2  
**Prompt:** `prompts/unified_spec_agent.txt`

### 6. spec_reviewer
**Purpose:** Review specs for completeness  
**Input:** Module spec  
**Output:** Review feedback  
**Model:** gpt-4o-mini (cost optimization)  
**Prompt:** `prompts/unified_spec_reviewer.txt`

### 7. generate_tests
**Purpose:** Create pytest test files  
**Input:** Module spec  
**Output:** Test file with normal cases, edge cases, error handling  
**Model:** gpt-4o  
**Temperature:** 0.1 (deterministic)  
**Prompt:** `prompts/unified_generate_tests.txt`  
**File:** `generated_tests/test_[module].py`

### 8. code_merger ⭐ NEW
**Purpose:** Merge new functions into existing modules  
**Input:** Existing code, new function specs  
**Output:** Merged code with all functions  
**Model:** gpt-4o  
**Temperature:** 0.1  
**Prompt:** `prompts/unified_code_merger.txt`  
**Key Feature:** Preserves ALL existing code, adds only new functions  
**Safety:** Creates `.backup` file before modifying

### 9. generate_code
**Purpose:** Implement business logic  
**Input:** Spec, tests  
**Output:** Python module with functions  
**Model:** gpt-4o  
**Temperature:** 0.1  
**Prompt:** `prompts/unified_generate_code.txt`  
**File:** `modules/[module].py`

### 10. validate_modules
**Purpose:** Verify functions exist  
**Input:** Code files, specs  
**Output:** Validation report  
**Method:** AST parsing + regex  
**Model:** None (code analysis)

### 11. run_tests
**Purpose:** Execute pytest  
**Input:** Test files  
**Output:** Pass/fail counts, error messages  
**Tool:** pytest via subprocess  
**File:** `agents/tester_agent.py`

### 12. fix_analyzer
**Purpose:** Analyze test failures  
**Input:** Test output, specs, code  
**Output:** Fix recommendations, target (CODE/TESTS/BOTH)  
**Model:** gpt-4o  
**Temperature:** 0.2  
**Loop Detection:** Compares failures to previous run

### 13. fixer_agent
**Purpose:** Fix failing tests or code  
**Input:** Fix recommendations, current code/tests  
**Output:** Fixed files  
**Model:** gpt-4o  
**Temperature:** 0.2  
**Prompt:** `prompts/unified_fixer_agent.txt`  
**Max Iterations:** Unlimited (until stuck or pass)

### 14. ui_designer
**Purpose:** Choose optimal UI pattern  
**Input:** Available functions, EPIC context  
**Output:** UI pattern (button_grid/sidebar_nav/tabs/form)  
**Model:** gpt-4o  
**Decision Logic:**
- Calculator functions → button_grid
- Multiple tools → sidebar_nav
- Categories → tabs
- Data entry → form

### 15. generate_main_app
**Purpose:** Create Streamlit UI  
**Input:** Architecture, functions, UI pattern  
**Output:** app.py with complete UI  
**Model:** gpt-4o  
**Temperature:** 0.1  
**Prompt:** `prompts/unified_generate_main_app.txt`  
**Reference:** Loads pattern-specific example from `reference_examples/`

### 16. validate_app
**Purpose:** Check for Streamlit errors  
**Checks:**
- Syntax errors (AST parsing)
- Missing button keys
- Incorrect imports
- on_click callbacks (should use if/rerun pattern)
- Disabled text_input (should use markdown)
**Model:** None (code analysis)

### 17. fix_app
**Purpose:** Fix Streamlit UI errors  
**Input:** Validation errors, current app  
**Output:** Fixed app.py  
**Model:** gpt-4o  
**Temperature:** 0.2  
**Max Iterations:** 3

### 18. quality_reviewer
**Purpose:** Review overall quality  
**Input:** Specs, test results  
**Output:** Quality report  
**Model:** gpt-4o-mini  
**Prompt:** `prompts/unified_quality_reviewer.txt`

### 19. senior_dev_reviewer
**Purpose:** Check if app will run  
**Input:** Architecture plan, app code  
**Output:** Runability assessment  
**Model:** gpt-4o-mini  
**Prompt:** `prompts/unified_senior_dev_reviewer.txt`

### 20. architecture_reviewer
**Purpose:** Score architecture alignment  
**Input:** Architecture plan, final app  
**Output:** Score (0-10) with feedback  
**Model:** gpt-4o-mini  
**Prompt:** `prompts/unified_architecture_reviewer.txt`  
**Scoring:** 40% functionality, 30% code quality, 30% architecture

---

## Agent Files

### Core Agent Implementations
- `agents/jira_agent.py` - Jira API client
- `agents/implementation_agent.py` - Code generation utilities
- `agents/tester_agent.py` - Pytest execution
- `agents/reviewer_agent.py` - Code review logic
- `agents/integration_agent.py` - Module integration
- `agents/github_agent.py` - GitHub operations (optional)

### Workflow Orchestration
- `graph/create_streamlit_app.py` - Main unified workflow (20 agents)
- `graph/tdd_code.py` - TDD workflow (simpler, 5 agents)

### Prompts (Agent Instructions)
- `prompts/unified_system_architect.txt`
- `prompts/unified_spec_agent.txt`
- `prompts/unified_generate_tests.txt`
- `prompts/unified_generate_code.txt`
- `prompts/unified_code_merger.txt` ⭐ NEW
- `prompts/unified_generate_main_app.txt`
- `prompts/unified_fixer_agent.txt`
- `prompts/unified_quality_reviewer.txt`
- `prompts/unified_senior_dev_reviewer.txt`
- `prompts/unified_architecture_reviewer.txt`

---

## Model Selection Strategy

### Expensive Models (gpt-4o: $15/$60 per 1M tokens)
Used for complex reasoning:
- system_architect
- requirements_analyzer
- spec_agent
- generate_tests
- code_merger
- generate_code
- ui_designer
- generate_main_app
- fix_analyzer
- fixer_agent
- fix_app

### Cheap Models (gpt-4o-mini: $0.15/$0.60 per 1M tokens)
Used for reviews and validation:
- spec_reviewer
- quality_reviewer
- senior_dev_reviewer
- architecture_reviewer

### No Model (Code Analysis)
- health_check
- jira_reader
- validate_modules
- run_tests
- validate_app

**Cost per App:** ~$0.85 (down from $1.05 in v1.0)

---

## Temperature Settings

- **0.1** - Deterministic (code generation, tests, fixes)
- **0.2** - Slightly creative (architecture, specs, analysis)
- **0.3** - More creative (reviews, feedback)

Lower temperature = fewer fix iterations = lower cost

---

## Loop Detection & Safety

### Fix Loop Protection
- Compares current failures to previous run
- If identical → STUCK → stops fixing
- Prevents infinite loops

### Max Iterations
- Test fixes: Unlimited (until stuck or pass)
- App fixes: 3 iterations max
- Architecture regeneration: 3 attempts max

### Recursion Limit
- LangGraph recursion limit: 50 steps
- Prevents runaway workflows

---

## State Management

### Shared State (GenState)
All agents share state via TypedDict:
- `tickets` - Jira ticket data
- `architecture_plan` - JSON architecture
- `specs` - Module specifications
- `test_files` - Test file paths
- `code_files` - Module file paths
- `app_path` - Main app path
- `passed/failed` - Test counts
- `needs_fix` - Fix flag
- `stuck` - Loop detection flag

### State Flow
```
Input → Agent 1 → State Update → Agent 2 → State Update → ... → Output
```

Each agent:
1. Reads from state
2. Performs task
3. Updates state
4. Returns updated state

---

## Incremental Update Agent (Mode 3)

### Standalone Agent
File: `incremental_update.py`

**Purpose:** Add features without regenerating UI

**Steps:**
1. Read Jira tickets
2. Analyze what functions needed (LLM)
3. Load existing module
4. Extract existing functions (regex)
5. Filter new functions (set difference)
6. Merge with LLM (code_merger logic)
7. Validate syntax (AST)
8. Create backup
9. Write merged code

**Model:** gpt-4o  
**Safety:** Creates `.backup` before modifying  
**Speed:** ~10-30 seconds per ticket

---

## Comparison Tool (Mode 4)

### Standalone Tool
File: `compare_archives.py`

**Purpose:** Show differences between archived apps

**Features:**
- Unified diff view
- File-by-file comparison
- Module count changes
- Added/removed modules

**Method:** Python difflib  
**No LLM:** Pure code analysis

---

## Agent Communication

### LangGraph Edges
```python
# Sequential
builder.add_edge("agent1", "agent2")

# Conditional
builder.add_conditional_edges("agent", decision_func, {
    "path1": "next_agent1",
    "path2": "next_agent2"
})
```

### Decision Points
1. **health_check** → jira_reader or END
2. **requirements_analyzer** → regenerate or continue
3. **fix_analyzer** → fixer_agent or ui_designer
4. **validate_app** → fix_app or quality_reviewer

---

## Performance Metrics

### Agent Execution Times
- jira_reader: ~2-5 seconds
- system_architect: ~10-15 seconds
- spec_agent: ~5-10 seconds per module
- generate_tests: ~10-15 seconds per module
- generate_code: ~10-15 seconds per module
- generate_main_app: ~15-20 seconds
- run_tests: ~5-10 seconds
- fixer_agent: ~10-15 seconds per iteration

**Total (30 tickets):** ~5-10 minutes

### Token Usage
- Architecture: ~2,000 tokens
- Specs: ~1,500 tokens per module
- Tests: ~2,000 tokens per module
- Code: ~2,000 tokens per module
- UI: ~3,000 tokens
- Fixes: ~1,500 tokens per iteration

**Total (30 tickets, 0 fixes):** ~50,000 tokens (~$0.85)

---

## Future Enhancements

### Planned Agents
- **dependency_analyzer** - Detect module dependencies
- **security_scanner** - Check for vulnerabilities
- **performance_optimizer** - Optimize generated code
- **documentation_generator** - Auto-generate docs
- **deployment_agent** - Deploy to cloud

### Planned Features
- Multi-model support (Claude, Gemini)
- Parallel agent execution
- Agent result caching
- Custom agent plugins

---

## Summary

**Total Agents:** 20 (unified workflow) + 2 (standalone tools)

**Key Innovation:** Multi-agent orchestration with LangGraph enables:
- Specialized expertise per task
- Iterative refinement (fix loops)
- Quality gates (reviewers)
- Cost optimization (model selection)
- Safety (validation, backups)

**Result:** High-quality code generation with minimal human intervention
