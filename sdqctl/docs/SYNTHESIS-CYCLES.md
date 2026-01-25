# Synthesis Cycles: Iterative AI-Driven Workflows

A **synthesis cycle** uses sdqctl to improve a codebase iteratively, where each cycle's output becomes input for the next. The workflow analyzes, implements, documents, and queues the next priorities — creating a self-sustaining improvement loop.

> **Note**: This pattern was previously called "quine-like workflows". See [GLOSSARY.md](GLOSSARY.md#quine-like-deprecated) for why we changed the terminology.

---

## Quick Reference: Pitfalls to Avoid

| ⚠️ Issue | ❌ Bad | ✅ Good | Why |
|----------|--------|---------|-----|
| **Context** | Inject 50KB file | Let agent read on demand | Saves tokens, fresher data |
| **Scope** | "Fix all 15 issues" | "Select ONE item" | Focus prevents partial work |
| **Exit** | MAX-CYCLES 100 | MAX-CYCLES 3-5 | Bounded iteration |
| **Turns** | Separate RUN + PROMPT | Use `ELIDE` to merge | Fewer agent turns, less token waste |
| **Git commits** | `RUN git commit -m "..."` | PROMPT "commit with descriptive message" | Agent writes meaningful messages |

---

## Best Practice: Git Operations

**Use PROMPT for commits, RUN for verification.**

The agent writes better commit messages when it describes its actual work, rather than using hardcoded messages in RUN directives.

### ❌ Avoid: Hardcoded commit messages

```dockerfile
RUN git add -A && git commit -m "feat: implement feature"
```

Problems:
- Message doesn't reflect actual changes
- Commits even if work is incomplete
- No agent judgment on what to stage

### ✅ Prefer: Agent-driven commits

```dockerfile
# Show what changed (RUN - deterministic)
RUN git --no-pager diff --stat

# Let agent review and commit (PROMPT - flexible)
PROMPT |
  Review the changes above. If implementation is complete:
  1. Stage relevant files with git add
  2. Commit with a descriptive message summarizing what you built
  3. Show the commit with git log -1 --oneline
```

Benefits:
- Agent writes meaningful commit messages
- Agent decides what's ready to commit
- Agent can skip commit if work is incomplete
- Matches how human developers work

### Exception: WIP Checkpoints

For preserving intermediate state (not final commits), `RUN git commit` is acceptable:

```dockerfile
# Save work-in-progress before risky operation
RUN git add -A && git commit -m "wip: checkpoint before refactor" || true
```

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

## Example: implement-improvements.conv

The `examples/workflows/implement-improvements.conv` demonstrates this pattern:

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
sdqctl cycle examples/workflows/implement-improvements.conv \
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
  sdqctl cycle examples/workflows/implement-improvements.conv \
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
sdqctl cycle examples/workflows/implement-improvements.conv \
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
sdqctl cycle examples/workflows/implement-improvements.conv \
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

- **[Philosophy](PHILOSOPHY.md)** — Core workflow design principles
- **[Workflow Design](WORKFLOW-DESIGN.md)** — Core principle: specs in docs, orchestration in .conv
- **[Glossary](GLOSSARY.md)** — Terminology definitions
- **[Context Management](CONTEXT-MANAGEMENT.md)** — Optimal context window strategies
- **[Traceability Workflows](TRACEABILITY-WORKFLOW.md)** — Requirements → specs → tests → code
- **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Code → documentation
- **[Getting Started](GETTING-STARTED.md)** — Basics of sdqctl

See `examples/workflows/implement-improvements.conv` for a complete working example.

---

## Lessons Learned

Documented insights from real sdqctl usage sessions.

### Lesson #28: Sequential Workflows Combine Well

Running multiple focused workflows in sequence often completes faster than a single large workflow:

```bash
# Three focused workflows: 20 min total (faster than predicted 30-40 min)
sdqctl run 01-design.conv --adapter copilot && \
sdqctl run 02-implement.conv --adapter copilot && \
sdqctl run 03-verify.conv --adapter copilot
```

**Why it works**:
- Context fully resets between workflows
- No degradation from accumulated context
- Each workflow optimized for one deliverable type

**When to use**: Deliverables are independent and don't need shared context.

**When NOT to use**: Later phases depend on earlier phase analysis (use single workflow with COMPACT instead).

### Lesson #29: ELIDE + RUN Synergy Pattern

The most efficient pattern for running tests and analyzing results:

```dockerfile
# Phase 2: Implement
PROMPT Implement the feature.
RUN pytest tests/ -v --tb=short
COMPACT

# Phase 3: Analyze (merged with test output)
ELIDE
PROMPT The test results are shown above. Fix any failures.
```

**What happens**:
1. RUN executes tests, output captured
2. COMPACT frees context (keeps errors/tool-results via COMPACT-PRESERVE)
3. ELIDE merges test output with Phase 3 prompt
4. Agent sees failures in context without full code

### Lesson #30: Over-Delivery is Common

Structured workflows with clear specifications tend to produce **more output than predicted**:

| Predicted | Actual | Factor |
|-----------|--------|--------|
| ~300 lines | 2,229 lines | 7x |
| ~100 line help.py | 946 lines | 9x |

**Why it happens**:
- Agent has full spec from @-referenced proposal files
- No human interruption to say "that's enough"
- MODE implement encourages completeness
- PROLOGUE "edit files directly" prevents analysis paralysis

**If you want minimal output**: Scope prompts explicitly ("implement only the core function, no extras") or use MODE audit for analysis-only tasks.

### Lesson #31: CHECKPOINT Requires `cycle`

The CHECKPOINT directive is **only processed by `sdqctl cycle`**, not `sdqctl run`.

```dockerfile
PROMPT Do some work.
CHECKPOINT phase-1    # ← Ignored by 'run', saved by 'cycle'
PROMPT Continue work.
```

If your workflow needs resumability, use `cycle`:
```bash
sdqctl cycle workflow.conv --adapter copilot  # ✅ Checkpoints work
sdqctl run workflow.conv --adapter copilot    # ❌ Checkpoints ignored
```

See [GETTING-STARTED.md](GETTING-STARTED.md#run-vs-cycle-vs-apply) for full comparison.

### Lesson #32: Multi-Prologue Requires Cross-Document Instruction

When injecting multiple `--prologue` files, the model exhibits **first-prologue bias** — disproportionately selecting items from the first document even when higher-priority items exist in subsequent files.

**Evidence** (from 78-minute session):
- BACKLOG.md: 80% of items selected
- ARTIFACT-TAXONOMY.md: 13%
- REFCAT-DESIGN.md: 7%

**Fix**: Add explicit cross-document review instruction:

```dockerfile
PROLOGUE Review ALL the following roadmaps to select a high-value taskable area.
PROLOGUE Prioritize by: P0 > P1 > P2 across ALL documents, not just the first.
```

### Lesson #33: "EVALUATE ALL" Prefix Enables Cohesiveness Review

Adding an evaluation prefix to multi-prologue workflows improves cross-document awareness:

```bash
sdqctl cycle workflow.conv \
  --prologue "EVALUATE ALL following documents for cohesiveness." \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md
```

**Observed behavior**:
- Agent explicitly creates cohesiveness evaluation TODOs before work selection
- Catches inconsistencies between documents (e.g., directive count mismatches)
- Adds ~10 minutes to session but improves quality

### Lesson #34: Fresh Session Mode Requires Prologue Continuity

With `--session-mode=fresh`, context resets each cycle. Continuity depends on:

1. **Prologue injection** - Key context re-injected each cycle
2. **File-based state** - Progress tracked in files agent reads
3. **Git history** - Previous commits provide context via `git log`

**Trade-off**: No cross-cycle memory, but prevents context accumulation issues.

### Lesson #35: ~90 Minutes Sustainable with COMPACT Discipline

Extended sessions (88+ minutes, 10 cycles) are sustainable with:
- `COMPACT` after phases 2, 3, 4
- `--session-mode=fresh` to reset per cycle
- 4-phase structure (select → execute → verify → commit)
- Per-cycle commits for recovery

**Context progression**: ~46% at cycle end, stable across cycles.

### Lesson #36: Documentation and Backlog Hygiene Phases

Long-running backlog processors benefit from dedicated phases for:
1. **Documentation integration** - Ensure recent changes are reflected in docs
2. **Backlog hygiene** - Archive completed items, chunk complex ones

Without these, backlogs grow with completed work and docs drift from implementation.
