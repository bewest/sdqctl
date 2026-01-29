# sdqctl Philosophy

Principles for effective AI-assisted workflow design.

---

## Core Concepts

### The Fundamental Unit: One Iteration

An **iteration** (or **cycle**) is one complete pass through all prompts in a conversation file. Each iteration:

1. Reads the current state (files, backlog, progress)
2. Selects work based on priorities
3. Makes progress on that work
4. Records outcomes and updates state
5. Surfaces blockers or queues next work

```
┌─────────────────────────────────────────────────────────────────────┐
│                      One Iteration / Cycle                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PROMPT 1        PROMPT 2        PROMPT 3        PROMPT 4          │
│  (Phase 1)       (Phase 2)       (Phase 3)       (Phase 4)         │
│     ↓               ↓               ↓               ↓              │
│  Select Work  →  Execute   →   Verify    →   Document/Triage      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Command Roles

| Command | What It Does | When to Use |
|---------|--------------|-------------|
| `run` | Executes workflow **once** (1 iteration) | Testing, priming, single-spike work |
| `cycle -n N` | Executes workflow **N times** (N iterations) | Iterative refinement, backlog processing |
| `apply` | Executes workflow once **per component** | Batch processing across files |

**Note on naming**: The command names can be confusing. `run` performs one iteration, while `iterate` performs multiple. The name `iterate` suggests singularity but means "iterate N times." See [CLI-ERGONOMICS.md](../proposals/CLI-ERGONOMICS.md) for potential rename options (`do`/`invoke`).

---

## Terminology

| Term | Definition |
|------|------------|
| **Prompt** | A single `PROMPT` directive; one agent turn |
| **Phase** | A logical grouping of prompts (e.g., "Phase 1: Select") |
| **Iteration/Cycle** | One complete pass through ALL prompts |
| **`run` command** | Execute workflow once (1 iteration) |
| **`iterate` command** | Execute workflow N times (N iterations) |

**Key distinction**: Phases are *logical* groupings within the conversation file. They are NOT selectable steps—the agent processes all prompts in sequence during each iteration.

---

## Anatomy of an Effective Conversation File

A well-designed workflow contains these elements:

### 1. Scope Confirmation
Ensure the agent understands what work is ready and in-scope.

```dockerfile
PROMPT ## Phase 1: Scope and Readiness

Review the backlog at reports/improvements-tracker.md.
Select ONE item that is:
- Clearly defined (not research-needed)
- Unblocked (no external dependencies)
- High impact relative to effort
```

### 2. Progress Instructions
Direct the agent to make tangible progress, not just analyze.

```dockerfile
PROMPT ## Phase 2: Execute

Implement the selected item now.
- Edit files directly (do not describe changes)
- Run tests to verify: `pytest tests/ -v`
- If blocked, document the blocker and stop
```

### 3. Scope Partitioning for Blockers
Provide a way to surface problems and partition work without derailing the workflow. This "categorical chunking" separates actionable items from open questions that need human input.

```dockerfile
# In Phase 2:
If you encounter a blocker:
1. Document what's blocking in the progress file
2. Mark the item as "blocked" with reason
3. Do NOT attempt workarounds—stop and document
```

### 4. Verification with Tools
Use `RUN` and `VERIFY` to confirm work was done correctly.

```dockerfile
RUN python -m pytest tests/ -v --tb=short
ELIDE
PROMPT ## Phase 3: Analyze Results

The test results are shown above.
- If all tests pass, proceed to documentation
- If tests fail, fix the issues or document blockers
```

### 5. Summarization and Recording
Capture what was accomplished for future reference.

```dockerfile
PROMPT ## Phase 4: Document

Update reports/progress-{{DATE}}.md with:
1. What was completed this iteration
2. Barriers encountered and workarounds
3. Lessons learned for future work
```

### 6. Backlog Management
Limit the growth of future work; prioritize ruthlessly.

```dockerfile
PROMPT ## Phase 5: Triage

Review remaining work and surface:
- Next 3 highest-priority items (no more)
- Items that need human input before proceeding
- Items that should be deferred or dropped

Output the command for the next session.
```

---

## The Double Diamond Pattern

Effective workflows often follow the **double diamond** design pattern:

```
                    DIVERGE                    CONVERGE
                       ↓                          ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │     ◇                                        ◇              │
    │    ◇ ◇        First Diamond              ◇ ◇               │
    │   ◇   ◇       (Discover)                ◇   ◇              │
    │  ◇     ◇                               ◇     ◇             │
    │ ◇       ◇                             ◇       ◇            │
    │◇─────────◇ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ◇─────────◇           │
    │           ◇                         ◇                       │
    │            ◇       Second          ◇                        │
    │             ◇      Diamond        ◇                         │
    │              ◇     (Deliver)     ◇                          │
    │               ◇                 ◇                           │
    │                ◇───────────────◇                            │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
    
    Explore          Define        Develop         Deliver
    problem          problem       solutions       solution
    space           statement                      
```

### First Diamond: Discovery
- **Diverge**: Explore the codebase, gather context, identify issues
- **Converge**: Focus on what matters, define the problem clearly

### Second Diamond: Delivery
- **Diverge**: Explore solution options, prototype approaches
- **Converge**: Implement the chosen solution, verify it works

### In Practice

This pattern appears at multiple levels:

1. **Within a single iteration**: Explore → Select → Implement → Verify
2. **Across multiple iterations**: Discovery workflows → Implementation workflows
3. **Across workflow types**: `test-discovery.conv` (diverge) → `implement-improvements.conv` (converge)

---

## When to Use Multiple `run` vs One Consolidated Workflow

### Signal: Multiple sequential `run` commands

If you find yourself running:
```bash
sdqctl iterate step1.conv
sdqctl iterate step2.conv  
sdqctl iterate step3.conv
```

This is a signal that these workflows should be consolidated with proper context management.

### When Consolidation Works

✅ **Consolidate when**:
- Steps share context (later steps need earlier analysis)
- Total context fits in one session (with COMPACT)
- Steps are always run together

```dockerfile
# consolidated-workflow.conv
PROMPT ## Phase 1: Analysis (was step1.conv)
...

COMPACT

PROMPT ## Phase 2: Planning (was step2.conv)
...

COMPACT

PROMPT ## Phase 3: Execution (was step3.conv)
...
```

### When Separation Works

✅ **Keep separate when**:
- Steps are independently useful
- Steps have different audiences or triggers
- Full context reset is desirable between steps

```bash
# Discovery → Implementation is a natural break
sdqctl iterate test-discovery.conv --adapter copilot
# Human reviews findings, then:
sdqctl iterate implement-improvements.conv -n 3 --adapter copilot
```

---

## Backlog-Driven Workflow Design

The most effective sdqctl workflows are **backlog-driven**:

1. **Backlog file** (`reports/improvements-tracker.md`) holds prioritized work items
2. **Workflow** reads backlog, selects ONE item, works on it
3. **Workflow** updates backlog with completion status, new findings
4. **Next iteration** picks up the next item

### Benefits

- **Focus**: Each iteration completes one thing well
- **Resumability**: Backlog persists; workflow can stop/restart
- **Traceability**: Progress is documented in markdown files
- **Human oversight**: Human can reprioritize backlog between runs

### Example: Self-Improvement Workflow

sdqctl improving itself (demonstrates state relay + convergence):

```bash
# 1. Discover issues → creates backlog
sdqctl iterate test-discovery.conv --adapter copilot

# 2. Iterate through backlog items
sdqctl iterate implement-improvements.conv -n 3 --adapter copilot

# 3. Review progress, adjust priorities, continue
sdqctl iterate implement-improvements.conv -n 3 --adapter copilot
```

---

## Direction: Forward and Backward

Workflows can move in two directions through the software lifecycle:

### Forward: Toward Traceability
Requirements → Specifications → Tests → Code → Verification

```dockerfile
# Forward workflow: implementing from requirements
PROMPT Review REQ-001 through REQ-010.
PROMPT Generate test cases that verify each requirement.
PROMPT Implement code to pass the tests.
PROMPT Verify all requirements are traced to tests and code.
```

### Backward: Through Discovery
Code → Documentation → Requirements → Gaps

```dockerfile
# Backward workflow: reverse-engineering
PROMPT Analyze the existing codebase.
PROMPT Extract implicit requirements from code behavior.
PROMPT Document gaps between code and requirements.
PROMPT Prioritize gaps for remediation.
```

Both directions are valid. The key is knowing which direction you're moving and why.

---

## Anti-Patterns

### ❌ Describing Changes Instead of Making Them

```dockerfile
# BAD
PROMPT Describe what changes would improve this code.

# GOOD  
PROMPT Implement the improvements now. Edit files directly.
```

### ❌ Trying to Do Everything in One Iteration

```dockerfile
# BAD
PROMPT Fix all 15 issues in the backlog.

# GOOD
PROMPT Select the SINGLE most impactful issue. Complete it fully.
```

### ❌ No Exit Condition

```dockerfile
# BAD
MAX-CYCLES 100
PROMPT Keep improving until perfect.

# GOOD
MAX-CYCLES 3
PROMPT If all P0 items are done, output "COMPLETE" and stop.
```

### ❌ Over-Priming with Context

```dockerfile
# BAD - exhausts context before work begins
CONTEXT @reports/50kb-analysis.md
CONTEXT @lib/**/*.py

# GOOD - let agent read on demand
PROMPT The analysis is in reports/analysis.md.
  Review it and select a task.
```

### ❌ Conflating Iteration with Selection

```dockerfile
# BAD - implies prompts are selectable
PROMPT Select which phase to work on:
  1. Analysis
  2. Implementation
  3. Testing

# GOOD - phases are sequential
PROMPT ## Phase 1: Analysis
...
PROMPT ## Phase 2: Implementation
...
```

---

## Reference Examples

Well-designed workflows that demonstrate these principles:

| Workflow | Pattern | Why It's Effective |
|----------|---------|-------------------|
| [`backlog-processor.conv`](../examples/workflows/backlog-processor.conv) | **Universal** | Reusable across domains via `--prologue` injection |
| [`fix-quirks.conv`](../examples/workflows/fix-quirks.conv) | Synthesis cycle | Clear terminology docs, scope partitioning, backlog-driven |
| [`implement-improvements.conv`](../examples/workflows/implement-improvements.conv) | Synthesis cycle | Triage→Implement→Document with COMPACT between phases |
| [`proposal-development.conv`](../examples/workflows/proposal-development.conv) | State relay | Assess→Work→Commit with backlog persistence |
| [`sdk-debug-integration.conv`](../examples/workflows/sdk-debug-integration.conv) | Backlog-driven | Single item selection, blocker acknowledgment |
| [`test-discovery.conv`](../examples/workflows/test-discovery.conv) | Discovery | Clear MODE audit, feeds into implementation workflows |
| [`deep-analysis.conv`](../examples/workflows/deep-analysis.conv) | Multi-phase | CHECKPOINT and COMPACT for context management |

### The Backlog Processor Pattern

The most reusable workflow pattern uses `--prologue` to inject context while keeping the conversation file domain-agnostic:

```bash
# Same workflow, different backlogs:
sdqctl iterate examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --adapter copilot -n 10

sdqctl iterate examples/workflows/backlog-processor.conv \
  --prologue docs/QUIRKS.md \
  --adapter copilot -n 5

# Multiple backlogs in priority order:
sdqctl iterate examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md \
  --prologue proposals/ARTIFACT-TAXONOMY.md \
  --adapter copilot -n 10
```

**Key design principles:**
1. **No hardcoded paths** — Prompts say "the injected backlog" not specific files
2. **Generic selection** — P0 > P1 > P2, unblocked > blocked
3. **COMPACT after each phase** — Essential for `-n 10+` runs
4. **Git commit per change** — State persists across cycles
5. **Built-in scope partitioning** — Surface blockers, route to appropriate queues, stop cleanly

**Anti-pattern note**: Single-pass audit workflows (`MAX-CYCLES 1`, `MODE audit`) are valid for analysis tasks but should not be confused with synthesis cycles. They produce reports; they don't iterate on improvements.

---

## Extended Workflow Pattern (v2)

The backlog-processor-v2 workflow introduces a **9-phase structure** with role shifts:

### Implementation Stream (Phases 1-6)
The agent acts as an **Implementer**:
1. **Select** — Pick ONE item from Ready Queue
2. **Execute** — Make the changes
3. **Verify** — Run tests, check results
4. **Document** — Update relevant docs
5. **Hygiene** — Light backlog cleanup
6. **Commit** — Git commit with conventional message

### Management Stream (Phases 7-8)
The agent shifts to **Project Manager**:
7. **Candidate Discovery** — Scan proposals/, QUIRKS, code for 5 new candidates
8. **Queue Routing** — Route candidates to appropriate queues:
   - Actionable → BACKLOG.md Ready Queue (target: 3 items)
   - Questions → OPEN-QUESTIONS.md (for human input)
   - Design needs → proposals/*.md
   - Bugs → QUIRKS.md

### Maintenance Stream (Phase 9)
The agent shifts to **Librarian**:
9. **Archive & Integrate** — Keep files under size limits, archive completed work

### Context Efficiency

The v2 pattern achieves dramatically better context efficiency:

| Metric | v1 (6 phases) | v2 (9 phases) |
|--------|---------------|---------------|
| Context peak | 55-58% | **20%** |
| Cycles completed | 5.5/10 | **10/10** |
| Tool success | 99.4% | **100%** |

**Key insight**: COMPACT after Phase 6 clears implementation details before PM/Librarian work, keeping context lean across 10+ cycles.

### Bidirectional Flow

The v2 workflow enables bidirectional flow:

```
FORWARD (synthesis)              BACKWARD (analysis)
humans → decisions → code        code → discoveries → humans
        ↓                                ↓
        └── BACKLOG.md ←──────── OPEN-QUESTIONS.md ──┘
```

- **Backward**: Implementation reveals questions → routed to OPEN-QUESTIONS.md
- **Forward**: Human answers questions → routed to BACKLOG.md for implementation

---

## See Also

- [GLOSSARY.md](GLOSSARY.md) — Terminology definitions
- [SYNTHESIS-CYCLES.md](SYNTHESIS-CYCLES.md) — Multi-iteration patterns
- [WORKFLOW-DESIGN.md](WORKFLOW-DESIGN.md) — Conversation file structure
- [GETTING-STARTED.md](GETTING-STARTED.md) — Basic usage
- [proposals/CLI-ERGONOMICS.md](../proposals/CLI-ERGONOMICS.md) — Command naming analysis
