# sdqctl Glossary

This glossary defines the core concepts and terminology used in sdqctl.

---

## Conceptual Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        sdqctl Workflow Patterns                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │ Synthesis Cycle  │    │ Traceability     │    │  Convergence  │ │
│  │                  │    │ Pipeline         │    │               │ │
│  │  AI generates    │    │  REQ→SPEC→TEST   │    │  Repeat until │ │
│  │  artifacts:      │    │  →CODE→VERIFY    │    │  goal reached │ │
│  │  code, tests,    │    │                  │    │  or MAX-CYCLES│ │
│  │  specs, docs     │    │  Bidirectional   │    │               │ │
│  │                  │    │  linking         │    │  Fixed-point  │ │
│  └────────┬─────────┘    └────────┬─────────┘    └───────┬───────┘ │
│           │                       │                      │         │
│           └───────────────────────┼──────────────────────┘         │
│                                   │                                 │
│                    ┌──────────────▼──────────────┐                 │
│                    │     State Relay Pattern     │                 │
│                    │  Output of cycle N becomes  │                 │
│                    │  input for cycle N+1        │                 │
│                    └─────────────────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

These patterns are ORTHOGONAL — combine them as needed:
• Synthesis + Convergence: "Keep fixing until tests pass"
• Synthesis + Traceability: "Generate tests linked to specs"
• All three: "Iteratively build traced artifacts until complete"
```

---

## Core Concepts

### Conversation Script

A `.conv` file that declaratively specifies a workflow. Contains directives (MODEL, ADAPTER, PROMPT, RUN, etc.) that define what the AI agent should do.

**Example**: `fix-bugs.conv`, `test-discovery.conv`

### Synthesis Cycle

A multi-pass workflow where AI generates or modifies artifacts (code, tests, specs, docs), with state persisted between passes. Each cycle builds on the output of previous cycles.

**Types of synthesis**:
- **Code synthesis** — generating or modifying source code
- **Test synthesis** — generating test cases and fixtures
- **Spec synthesis** — generating specifications or requirements
- **Doc synthesis** — generating documentation
- **Trace synthesis** — generating traceability links (UCA → REQ → TEST)

**See also**: [Synthesis Cycles](SYNTHESIS-CYCLES.md)

### State Relay Pattern

The pattern where output from cycle N becomes input context for cycle N+1. State is persisted in files (progress reports, trackers, etc.) that the AI reads and updates.

**Example**: A progress tracker file updated after each cycle, informing the next cycle what work remains.

### Convergence

The process of repeating cycles until a goal state is reached or `MAX-CYCLES` is hit. The workflow converges toward completion (all tests pass, all items fixed, etc.).

---

## Workflow Patterns

### Traceability Pipeline

The chain linking: **Requirements → Specifications → Tests → Code → Verification**

Each phase produces artifacts that reference the previous phase. Verification confirms all links are valid.

**See also**: [Traceability Workflows](TRACEABILITY-WORKFLOW.md)

### Bifurcation

When one synthesis cycle spawns multiple downstream workflows. For example, a discovery workflow might produce separate fix workflows for different components.

### Cross-Pollination

Insights from one project informing another. For example, STPA analysis findings in Loop being applied to AAPS.

---

## Directives

### ELIDE

Merges adjacent workflow elements into a single agent turn. Reduces token waste from intermediate responses.

```dockerfile
RUN pytest -v
ELIDE
PROMPT Fix any failing tests.
# Agent sees test output and fix request in one turn
```

### PROLOGUE / EPILOGUE

Content prepended/appended to every prompt in a workflow. Used for session context, reminders, or consistent framing.

### CHECKPOINT

Saves workflow state at a specific point. Enables resuming interrupted workflows.

### COMPACT

Triggers session compaction, summarizing conversation history to free context space.

---

## Execution Modes

### Session Mode

Controls how context accumulates across cycles:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `fresh` | Each cycle starts clean | File editing (agent re-reads modified files) |
| `accumulate` | Context grows until limit | Building on previous analysis |
| `compact` | Summarize after each cycle | Long workflows, token management |

---

## Historical Terms

### "Quine-like" (deprecated)

Earlier terminology for synthesis cycles. A true quine is a program that outputs its own source code—sdqctl workflows don't do this. The term was used informally to describe the self-referential nature of workflows that improve the codebase, but conflated several distinct concepts:

1. State relay (output → input)
2. Convergence (iterate until done)
3. Synthesis (AI generates artifacts)
4. Traceability (linking artifacts)

**Prefer**: Use the specific term for what you mean (synthesis cycle, state relay, convergence, traceability pipeline).

---

## See Also

- [Synthesis Cycles](SYNTHESIS-CYCLES.md) — Iterative AI-driven workflows
- [Traceability Workflows](TRACEABILITY-WORKFLOW.md) — REQ → SPEC → TEST → CODE
- [Context Management](CONTEXT-MANAGEMENT.md) — Managing context window
- [Getting Started](GETTING-STARTED.md) — sdqctl basics
