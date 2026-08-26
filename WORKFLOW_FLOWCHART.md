# Jira Code Generator - Workflow Flowchart

## Access Methods

### Web UI (Recommended)
```bash
streamlit run jira_coder_ui.py
```
Open http://localhost:8501

### Command Line
```bash
python3 main.py
```

## Main Menu Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    🔧 JIRA CODER                            │
│          streamlit run jira_coder_ui.py (Web UI)            │
│                  python3 main.py (CLI)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │  Choose Mode (1-3 for generation, 10+ demo) │
        └─────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────────────────┐
        │                     │                                  │
        ▼                     ▼                                  ▼
   ┌─────────┐         ┌──────────┐                      ┌──────────┐
   │ Mode 1  │         │ Mode 2   │                      │ Mode 3   │
   │  TDD    │         │ Unified  │                      │Increment │
   └─────────┘         └──────────┘                      └──────────┘
        │                     │                                  │
        │                     │                                  │
        ▼                     ▼                                  ▼
   ┌─────────┐         ┌──────────┐                      ┌──────────┐
   │ Mode 10 │         │ Mode 11  │                      │ Mode 12  │
   │ Basic   │         │ Memory   │                      │ Binary   │
   │  Demo   │         │  Demo    │                      │  Demo    │
   └─────────┘         └──────────┘                      └──────────┘
```

---

## Mode 1: TDD Workflow (Single Ticket)

```
┌──────────────┐
│ Enter Ticket │
│   (CAL-1)    │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Read Jira       │
│  Ticket Details  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Generate Spec   │
│  (function sig)  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Generate Tests   │
│  (pytest file)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Generate Code    │
│ (implementation) │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   Run Tests      │
└──────┬───────────┘
       │
       ├─── PASS ──→ ✅ Done
       │
       └─── FAIL ──→ Fix Loop (max 10x) ──→ Run Tests
```

---

## Mode 2: Unified App Generation (Multiple Tickets)

```
┌────────────────────┐
│ Enter Project Key  │
│   & Ticket Keys    │
│  (CAL, or ALL)     │
└─────────┬──────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT WORKFLOW                      │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────┐
│  1. jira_reader  │  Fetch all tickets + EPIC
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ 2. system_architect  │  Design modules & functions
└────────┬─────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. requirements_analyzer│  Check EPIC constraints
└────────┬────────────────┘  (reject FSM if "simple")
         │
         ├─── REJECTED ──→ Regenerate Architecture (max 3x)
         │
         └─── APPROVED
                │
                ▼
┌──────────────────┐
│  4. spec_agent   │  Generate detailed specs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. spec_reviewer │  Review specs for quality
└────────┬─────────┘
         │
         ▼
┌───────────────────┐
│ 6. generate_tests │  Create pytest files
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 7. generate_code  │  Implement functions
└────────┬──────────┘
         │
         ▼
┌──────────────────┐
│ 8. run_tests     │  Execute pytest
└────────┬─────────┘
         │
         ├─── FAIL ──→ fix_analyzer → fixer_agent → run_tests
         │                                              │
         └─── PASS ────────────────────────────────────┘
                │
                ▼
┌──────────────────┐
│ 9. ui_designer   │  Choose UI pattern (button_grid/sidebar/tabs)
└────────┬─────────┘
         │
         ▼
┌─────────────────────┐
│ 10. generate_main_app│  Create app.py with Streamlit UI
└────────┬────────────┘
         │
         ▼
┌──────────────────┐
│ 11. validate_app │  Check for common errors
└────────┬─────────┘
         │
         ├─── ERRORS ──→ fix_app (max 3x) → validate_app
         │
         └─── OK
                │
                ▼
┌──────────────────────┐
│ 12. quality_reviewer │  Review test/code quality
└────────┬─────────────┘
         │
         ▼
┌─────────────────────────┐
│ 13. senior_dev_reviewer │  Check if app will run
└────────┬────────────────┘
         │
         ▼
┌───────────────────────────┐
│ 14. architecture_reviewer │  Score architecture (0-10)
└────────┬──────────────────┘
         │
         ▼
    ✅ DONE
    app.py + modules/ + tests/
```

---

## Mode 3: Incremental Update (Add Features)

```
┌──────────────────┐
│ Enter Ticket Keys│
│  (CAL-31,CAL-32) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Read Tickets    │
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│  Analyze Functions   │  What new functions needed?
│  (LLM extracts spec) │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Load Existing Module │  Read modules/calculator.py
└────────┬─────────────┘
         │
         ▼
┌──────────────────────────┐
│ Extract Existing Funcs   │  ['add', 'subtract', 'multiply']
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Filter New Functions     │  Only add what's missing
│ (avoid duplicates)       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Merge with LLM           │  Add new functions to end
│ (preserve existing code) │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Validate Syntax          │  ast.parse() check
└────────┬─────────────────┘
         │
         ├─── FAIL ──→ Keep existing code
         │
         └─── PASS
                │
                ▼
┌──────────────────────────┐
│ Create Backup            │  calculator.py.backup
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Write Merged Code        │  calculator.py updated
└────────┬─────────────────┘
         │
         ▼
    ✅ DONE
    ⚠️  app.py NOT modified
    (manually add UI or run Mode 2)
```

---

## Demo Modes (10-12)

```
┌──────────────┐
│  Mode 10     │  streamlit run demos/basic_calculator.py
│ Basic Demo   │  → Shows: Digits, operators, equals, clear
└──────────────┘

┌──────────────┐
│  Mode 11     │  streamlit run demos/calculator_with_memory.py
│ Memory Demo  │  → Shows: Basic + M+, MR, MC buttons
└──────────────┘

┌──────────────┐
│  Mode 12     │  streamlit run app.py
│ Binary Demo  │  → Shows: Memory + DEC/BIN toggle, binary arithmetic
└──────────────┘
```

---

## Key Decision Points

### Mode 2: requirements_analyzer

```
┌─────────────────────────┐
│ Check EPIC constraints  │
└───────────┬─────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
SIMPLE APP      COMPLEX APP
(< 10 tickets)  (> 15 tickets)
EPIC: "simple"  EPIC: "state mgmt"
    │                │
    ▼                ▼
Pure Functions   Classes/FSM OK
1-2 modules      Multiple modules
    │                │
    └────────┬───────┘
             │
             ▼
    Architecture Plan
```

### Mode 2: fix_analyzer

```
┌──────────────┐
│  Run Tests   │
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
 PASS     FAIL
   │        │
   │        ▼
   │   ┌────────────────┐
   │   │ Compare with   │
   │   │ prev failures  │
   │   └────┬───────────┘
   │        │
   │    ┌───┴────┐
   │    │        │
   │    ▼        ▼
   │  SAME    DIFFERENT
   │    │        │
   │    ▼        ▼
   │  STUCK   Fix Code/Tests
   │    │        │
   │    └────┬───┘
   │         │
   └─────────┼──→ Continue
             │
             ▼
        Run Tests
```

---

## Cost Optimization Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    MODEL SELECTION                       │
└─────────────────────────────────────────────────────────┘

Expensive (gpt-4o: $15/$60 per 1M tokens)
    │
    ├─→ system_architect      (complex reasoning)
    ├─→ spec_agent            (detailed specs)
    └─→ requirements_analyzer (validation)

Cheap (gpt-4o-mini: $0.15/$0.60 per 1M tokens)
    │
    ├─→ generate_code         (pattern-based)
    ├─→ generate_tests        (template-based)
    ├─→ generate_main_app     (UI generation)
    ├─→ fixer_agent           (iterative fixes)
    └─→ reviewers             (quality checks)

Temperature: 0.1 (deterministic, fewer retries)

Result: ~$0.85 per app (down from $1.05)
```

---

## Comparison: Mode 2 vs Mode 3

```
┌─────────────────────────────────────────────────────────────┐
│                    MODE 2 (Full Generation)                  │
└─────────────────────────────────────────────────────────────┘

Jira Tickets → Generate Everything → ❌ LOSE custom changes

✅ Good for: Initial app creation
❌ Bad for: Adding features to existing app


┌─────────────────────────────────────────────────────────────┐
│                  MODE 3 (Incremental Update)                 │
└─────────────────────────────────────────────────────────────┘

Jira Tickets → Analyze → Merge New Functions → ✅ KEEP existing code

✅ Good for: Adding features without losing work
❌ Bad for: UI updates (need manual changes)


WORKFLOW RECOMMENDATION:
1. Use Mode 2 to create initial app
2. Use Mode 3 to add backend functions
3. Manually update UI in app.py
4. Use Mode 2 again if you want full UI regeneration
```

---

## Summary Table

| Mode | Purpose | Input | Output | Preserves Existing Code |
|------|---------|-------|--------|------------------------|
| 1 | TDD single module | 1 ticket | module.py + tests | N/A (new file) |
| 2 | Full app generation | Multiple tickets | app.py + modules/ + tests/ | ❌ No (regenerates) |
| 3 | Incremental update | Ticket keys | Updated modules/ | ✅ Yes (merges) |
| 10 | Basic demo | None | Runs demo | N/A (read-only) |
| 11 | Memory demo | None | Runs demo | N/A (read-only) |
| 12 | Binary demo | None | Runs demo | N/A (read-only) |

