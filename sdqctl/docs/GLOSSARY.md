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

### Prompt, Phase, and Iteration

These terms describe different levels of workflow structure:

| Term | Definition | Example |
|------|------------|---------|
| **Prompt** | A single `PROMPT` directive; one agent turn | `PROMPT Analyze the code.` |
| **Phase** | A logical grouping of prompts within one iteration | "Phase 1: Select", "Phase 2: Execute" |
| **Iteration** | One complete pass through ALL prompts in a workflow | Running all 4 phases once |
| **Cycle** | Synonym for iteration (used in `sdqctl iterate` command) | `sdqctl iterate -n 3` = 3 iterations |

**Key insight**: Phases are NOT selectable steps. The agent processes all prompts sequentially during each iteration. Phases are organizational labels, not menu options.

**See also**: [Philosophy](PHILOSOPHY.md) — Workflow design principles

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

### "Escape Hatch" (deprecated)

Earlier terminology for blocker handling. The term suggested an emergency exit mechanism, but the actual concept is more deliberate:

**Actual intent**: Systematic handling of back-pressure through:
1. **Scope partitioning** — Dividing work into manageable chunks per iteration
2. **Categorical chunking** — Separating items by type (open questions vs actionable)
3. **Blocker surfacing** — Routing blocked items to appropriate queues (OPEN-QUESTIONS.md, proposals/)

**Prefer**: Use "scope partitioning", "blocker surfacing", or "categorical chunking" depending on which aspect you mean.

---

## Workflow Concepts

### Scope Partitioning

The practice of handling back-pressure by dividing work into appropriate categories:

| Category | Destination | When to Use |
|----------|-------------|-------------|
| **Actionable** | BACKLOG.md Ready Queue | Clear scope, unblocked, can complete now |
| **Open Questions** | OPEN-QUESTIONS.md | Needs human input or design decision |
| **Design Decisions** | proposals/*.md | Architectural impact, needs proposal |
| **Deferred** | Future/Backlog | Low priority, not ready yet |

This prevents context window exhaustion by routing items appropriately rather than accumulating everything in one iteration.

### Categorical Chunking

Synonym for scope partitioning, emphasizing the division of work by kind rather than just priority. Helps agents evaluate and select batches of related work that can complete together efficiently.

### Work Package

A pre-grouped set of related backlog items that can complete together in 1-2 iterations. Work packages:
- Share files or modules (reduces re-reading)
- Have explicit dependencies
- Include time/effort estimates
- Are tracked with `WP-###` identifiers

Example: `WP-001: SDK Economy Optimization` groups domain queues, metrics tracking, and workflow optimization.

See: [BACKLOG.md Work Packages section](../proposals/BACKLOG.md#work-packages)

---

## Disambiguation

### run (command) vs RUN (directive)

These share a name but are **completely unrelated**:

**`sdqctl run`** — CLI command that executes a workflow with an AI agent.
- Sends prompts to the configured adapter (copilot, openai, etc.)
- "Yields control" to the agent for the conversation duration
- Example: `sdqctl run workflow.conv --adapter copilot`

**`RUN`** — Directive in `.conv` files that executes shell commands locally.
- Runs before/after prompts, captures output for context
- No AI involved; pure subprocess execution
- Example: `RUN pytest tests/ -v`

```dockerfile
# This workflow uses BOTH:
PROMPT Analyze the test output.
RUN pytest tests/ -v          # ← RUN directive: executes shell command
ELIDE
PROMPT Fix any failures.

# Execute with:
# sdqctl run my-workflow.conv  # ← run command: sends to AI
```

### run vs cycle (commands)

Both commands execute workflows, but with different iteration counts:

**`sdqctl run`** — Executes workflow **once** (1 iteration).
- Good for: Testing, priming, single-spike work
- Example: `sdqctl run workflow.conv --adapter copilot`

**`sdqctl iterate`** — Executes workflow **N times** (N iterations).
- Good for: Iterative refinement, backlog processing
- Example: `sdqctl iterate workflow.conv -n 3 --adapter copilot`

**Note**: The name `iterate` can be confusing—it sounds singular but means "iterate N times." See [Philosophy](PHILOSOPHY.md#command-roles) for details and [CLI-ERGONOMICS.md](../proposals/CLI-ERGONOMICS.md) for potential rename options.

---

## See Also

- [Philosophy](PHILOSOPHY.md) — Workflow design principles
- [Synthesis Cycles](SYNTHESIS-CYCLES.md) — Iterative AI-driven workflows
- [Traceability Workflows](TRACEABILITY-WORKFLOW.md) — REQ → SPEC → TEST → CODE
- [Context Management](CONTEXT-MANAGEMENT.md) — Managing context window
- [Getting Started](GETTING-STARTED.md) — sdqctl basics
