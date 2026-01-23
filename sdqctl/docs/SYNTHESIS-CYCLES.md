# Synthesis Cycles: Iterative AI-Driven Workflows

A **synthesis cycle** uses sdqctl to improve a codebase iteratively, where each cycle's output becomes input for the next. The workflow analyzes, implements, documents, and queues the next priorities — creating a self-sustaining improvement loop.

> **Note**: This pattern was previously called "quine-like workflows". See [GLOSSARY.md](GLOSSARY.md#quine-like-deprecated) for why we changed the terminology.

---

## Quick Reference: Pitfalls to Avoid

| ⚠️ Issue | ❌ Bad | ✅ Good | Why |
|----------|--------|---------|-----|
| **Naming** | `tracker.conv` | `fix-bugs.conv` | Filename affects agent role ([Q-001](QUIRKS.md#q-001-workflow-filename-influences-agent-behavior)) |
| **Context** | Inject 50KB file | Let agent read on demand | Saves tokens, fresher data |
| **Scope** | "Fix all 15 issues" | "Select ONE item" | Focus prevents partial work |
| **Exit** | MAX-CYCLES 100 | MAX-CYCLES 3-5 | Bounded iteration |
| **Turns** | Separate RUN + PROMPT | Use `ELIDE` to merge | Fewer agent turns, less token waste |

---

## What Makes a Synthesis Cycle?

Traditional workflows are linear: input → process → output.

Synthesis cycles are circular:
1. **Analyze** current state and select work
2. **Implement** the selected improvement
3. **Document** progress and lessons
4. **Queue** next priorities for the next cycle

The key insight: **the output of cycle N becomes the context for cycle N+1** (this is the [State Relay Pattern](GLOSSARY.md#state-relay-pattern)).

---

## The Core Pattern

```
┌─────────────────────────────────────────────┐
│  Cycle 1: Triage                            │
│  - Read backlog/findings                    │
│  - Select highest-impact item               │
│  - Plan the implementation                  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Cycle 2: Implement                         │
│  - Make the changes                         │
│  - Run tests to verify                      │
│  - Commit if successful                     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Cycle 3: Document                          │
│  - Summarize completed work                 │
│  - Record barriers and lessons              │
│  - Update backlog with next 3 priorities   │
│  - Output next session command              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
           (next session)
```

---

## Example: progress-tracker.conv

The `examples/workflows/progress-tracker.conv` demonstrates this pattern:

```dockerfile
MODEL gpt-4
ADAPTER copilot
MODE implement
MAX-CYCLES 3

# Minimal context injection - just session info
PROLOGUE ---
PROLOGUE ## Session Context
PROLOGUE Branch: {{GIT_BRANCH}} ({{GIT_COMMIT}})
PROLOGUE Date: {{DATETIME}}
PROLOGUE ---

# Remind agent of output expectations
EPILOGUE ---
EPILOGUE Remember:
EPILOGUE - Make minimal, surgical changes
EPILOGUE - Test changes before marking complete
EPILOGUE - Document any blockers encountered

# Cycle 1: Triage
PROMPT ## Task Selection

Select the SINGLE most impactful item to work on.
Review the backlog in reports/improvements-tracker.md.

Selection criteria:
1. P0 items that block other work
2. P1 items affecting multiple components
3. Items where the fix is well-understood

# Cycle 2: Implement
PROMPT ## Implementation

Implement the selected fix now.
Edit the files, run tests, commit if successful.
If blocked, document the barrier and move on.

# Cycle 3: Document
PROMPT ## Progress Documentation

Summarize:
1. What was completed
2. Barriers encountered
3. Next 3 priorities
4. Command for next session
```

### Running It

```bash
# Hint at the backlog file in the prompt, don't inject it
sdqctl cycle examples/workflows/progress-tracker.conv \
  --adapter copilot \
  -n 3
```

The agent will read `reports/improvements-tracker.md` when it needs context, rather than having it force-loaded.

---

## Designing Effective Prompts

### Hint, Don't Inject

❌ **Over-priming** (wastes context):
```bash
sdqctl cycle workflow.conv --prologue @reports/full-analysis.md
```

✅ **Hinting** (agent reads on demand):
```dockerfile
PROMPT Review the backlog in reports/improvements-tracker.md.
  Select the highest-impact item to work on.
```

### Why Hinting Works Better

1. **Agent autonomy**: The AI decides what context it needs
2. **Context efficiency**: Only reads files when relevant
3. **Exploration**: Agent can discover related files
4. **Flexibility**: Same workflow works with different backlogs

### When to Use Prologue/Epilogue

Use PROLOGUE for:
- Session metadata (`{{DATE}}`, `{{GIT_BRANCH}}`)
- Short reminders (1-3 lines)
- Consistent framing across all prompts

Use `--prologue @file` sparingly:
- Only for small, critical context files
- When the agent absolutely must see something upfront

---

## Managing State Across Cycles

### Option 1: File-Based State (Recommended)

The agent updates files that persist between sessions:

```dockerfile
PROMPT Update reports/improvements-tracker.md:
  - Mark completed items with ✅
  - Add lessons learned
  - Reorder remaining items by priority
```

### Option 2: Checkpoints

Use `CHECKPOINT` for resumable workflows:

```dockerfile
PROMPT Complete phase 1 analysis.
CHECKPOINT phase-1-complete

PROMPT Continue with phase 2.
```

Resume later:
```bash
sdqctl resume ~/.sdqctl/sessions/<id>/checkpoint.json
```

### Option 3: Output as Next Input

End each session with a "next command":

```dockerfile
PROMPT Output the exact command for the next session:
  ```bash
  sdqctl cycle examples/workflows/progress-tracker.conv \
    --adapter copilot -n 3
  ```
```

---

## Context Budget Strategies

### Cycle Session Modes

```bash
# Fresh: Each cycle starts clean, re-reads files (for file editing)
sdqctl cycle workflow.conv -n 5 --session-mode fresh

# Accumulate: Context grows until limit, then compacts
sdqctl cycle workflow.conv -n 5 --session-mode accumulate

# Compact: Summarize after each cycle
sdqctl cycle workflow.conv -n 10 --session-mode compact
```

### When to Use Each Mode

| Mode | Use Case |
|------|----------|
| `fresh` | Agent edits files; each cycle needs to see changes |
| `accumulate` | Building on previous analysis; want full history |
| `compact` | Long workflows; need to manage token usage |

---

## Real Example: sdqctl Improving Itself

### Step 1: Generate a Test Discovery Report

```bash
sdqctl run examples/workflows/test-discovery.conv --adapter copilot
# Outputs: reports/test-discovery-2026-01-22.md
```

### Step 2: Run Improvement Cycles

```bash
sdqctl cycle examples/workflows/progress-tracker.conv \
  --adapter copilot -n 3
```

The workflow:
1. Reads the test discovery report
2. Selects highest-priority item
3. Implements the fix
4. Documents progress and next steps

### Step 3: Continue Next Session

The final output includes the command for the next session:
```bash
sdqctl cycle examples/workflows/progress-tracker.conv \
  --adapter copilot -n 3
```

---

## Anti-Patterns: What Causes Problems

### 1. Over-Priming with Context

❌ Injecting large files upfront:
```bash
--prologue @reports/50kb-analysis.md
```

✅ Let agent read on demand:
```dockerfile
PROMPT The analysis is in reports/analysis.md. Review it and select a task.
```

### 2. Vague Cycle Boundaries

❌ Unclear what each cycle should accomplish:
```dockerfile
PROMPT Work on improvements.
PROMPT Keep working.
PROMPT Finish up.
```

✅ Clear, distinct phases:
```dockerfile
PROMPT ## Triage: Select ONE item to implement.
PROMPT ## Implement: Make the changes and test.
PROMPT ## Document: Summarize and queue next work.
```

### 3. No Exit Condition

❌ Workflow runs forever:
```dockerfile
MAX-CYCLES 100
PROMPT Keep improving until perfect.
```

✅ Bounded with clear completion:
```dockerfile
MAX-CYCLES 3
PROMPT If all P0 items are done, output "COMPLETE" and stop.
```

### 4. Too Many Items Per Cycle

❌ Trying to do everything at once:
```dockerfile
PROMPT Fix all 15 issues in the backlog.
```

✅ Single-item focus:
```dockerfile
PROMPT Select the SINGLE most impactful item.
  Complete it fully before moving on.
```

### 5. Filename Semantics Influence Agent Behavior

❌ Naming a workflow after its output type:
```bash
progress-tracker.conv   # Agent interprets role as "tracking"
documentation-sync.conv # Agent focuses on docs, not implementation
```

✅ Name workflows by their action:
```bash
implement-improvements.conv  # Agent understands it should edit files
edit-and-verify.conv         # Clear implementation intent
```

**See [QUIRKS.md](QUIRKS.md#q-001-workflow-filename-influences-agent-behavior)** for full details on this surprising behavior.

---

## Efficiency Tips

### Use ELIDE to Reduce Agent Turns

The `ELIDE` directive merges adjacent elements into a single prompt, eliminating unnecessary agent turns. This is particularly useful in synthesis cycles where you run tests and then ask the agent to fix failures:

❌ **Without ELIDE** — 3 agent turns (wasteful):
```dockerfile
PROMPT Run the tests and analyze results.
RUN pytest -v
PROMPT Fix any failing tests.
```

✅ **With ELIDE** — 1 agent turn (efficient):
```dockerfile
PROMPT Run the tests and analyze results.
RUN pytest -v
ELIDE
PROMPT Fix any failing tests.
```

The agent receives a single merged prompt containing the test output and fix instructions together, reducing token waste from intermediate "I see the output" responses.

### Chain ELIDEs for Multi-Step Verification

```dockerfile
PROMPT Review the build and test output below.
ELIDE
RUN npm run build
ELIDE
RUN npm test
ELIDE
PROMPT Fix any errors found in the build or tests.
# All merged into a single prompt
```

---

## Template: Topic Focus Document

When focusing cycles on a specific area, create a topic document:

```markdown
# [Topic] Improvements - Focus Document

## Scope
- **In Scope**: lib/auth/, tests/auth/
- **Out of Scope**: Other modules (defer to later)

## Work Items

### 1. [ID]: [Title] ⏳
**File**: path/to/file.py:123
**Issue**: Description
**Tasks**:
- [ ] Task 1
- [ ] Task 2

### 2. [ID]: [Title] ⏳
...

## Completed This Session
(Updated by the agent)

## Lessons Learned
(Barriers, workarounds, insights)
```

Reference it in prompts:
```dockerfile
PROMPT Review the focus document at reports/auth-improvements.md.
  Select and implement the next item.
```

---

## Next Steps

- **[Glossary](GLOSSARY.md)** — Terminology definitions
- **[Context Management](CONTEXT-MANAGEMENT.md)** — Optimal context window strategies
- **[Traceability Workflows](TRACEABILITY-WORKFLOW.md)** — Requirements → specs → tests → code
- **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Code → documentation
- **[Getting Started](GETTING-STARTED.md)** — Basics of sdqctl

See `examples/workflows/progress-tracker.conv` for a complete working example.
