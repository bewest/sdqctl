# Conversation Lifecycle

> **Status**: Living Document  
> **Last Updated**: 2026-01-26  
> **Related**: [ITERATE-CONSOLIDATION.md](../proposals/ITERATE-CONSOLIDATION.md), [PHILOSOPHY.md](PHILOSOPHY.md)

---

## Overview

This document describes how `sdqctl iterate` processes workflows from file parsing through execution. Understanding the lifecycle helps predict behavior, especially around:

- When prologues/epilogues are injected
- How elision merges adjacent items into single turns
- **Mixed mode**: Combining inline prompts with `.conv` files
- Session management across cycles

---

## Lifecycle Phases

```
┌─────────┐    ┌──────────┐    ┌────────┐    ┌─────────┐    ┌─────────┐
│  Parse  │ → │ Validate │ → │ Render │ → │ Execute │ → │ Compact │
└─────────┘    └──────────┘    └────────┘    └─────────┘    └─────────┘
```

### 1. Parse

Read input and build the `ConversationFile` structure.

**Inputs:**
- `.conv` file path(s)
- Inline prompt strings
- CLI options (`--prologue`, `--epilogue`, etc.)

**Actions:**
1. Parse directives from `.conv` file into `ConversationFile`
2. Resolve `INCLUDE` directives (recursive parsing)
3. Merge CLI options with file-level settings (CLI overrides file)
4. Build step list from `PROMPT`, `RUN`, `VERIFY`, `COMPACT`, etc.

**Output:** Parsed `ConversationFile` with merged configuration

### 2. Validate

Check references and requirements before execution.

**Checks performed:**
- `CONTEXT @patterns` resolve to existing files
- `REFCAT @file#lines` references are valid
- `REQUIRE @file` and `REQUIRE cmd:name` pass
- `MODEL-REQUIRES` can be resolved
- `ELIDE` chains don't contain branching (ON-FAILURE/ON-SUCCESS)

**Modes:**
- `VALIDATION-MODE strict` - Fail on any missing reference
- `VALIDATION-MODE lenient` - Warn on optional/missing, continue

### 3. Render

Prepare prompts for execution by substituting variables and building context.

**Actions:**
1. Substitute template variables (`{{DATETIME}}`, `{{WORKFLOW_NAME}}`, etc.)
2. Resolve `REFCAT` references to file excerpts
3. Build context string from `CONTEXT` patterns
4. Apply `HELP` topic injection into prologues
5. Prepare steps with resolved content

**Template Variables:**
| Variable | Source | Example |
|----------|--------|---------|
| `{{DATETIME}}` | Current timestamp | `2026-01-25T22:00:00` |
| `{{DATE}}` | Current date | `2026-01-25` |
| `{{WORKFLOW_NAME}}` | Source file name | `security-audit` |
| `{{CWD}}` | Working directory | `/home/user/project` |

### 4. Execute

Run the workflow by processing steps and sending prompts to the AI adapter.

**Step Processing Order:**
1. Initialize adapter session
2. Process each step in sequence:
   - `PROMPT` → Build with injection, send to AI
   - `RUN` → Execute command, capture output
   - `VERIFY` → Run verifier, inject output
   - `COMPACT` → Summarize conversation history
   - `CONSULT` → Pause for human input
3. Handle `ELIDE` chains (merge into single turn)
4. Handle branching (`ON-FAILURE`/`ON-SUCCESS`)

**Turn Structure:**
Each agent "turn" is a user message + assistant response. Multiple items can be elided into a single turn.

### 5. Compact (Optional)

Triggered by `COMPACT` directive, `ON-CONTEXT-LIMIT compact`, or SDK compaction threshold.

**Actions:**
1. Summarize conversation history
2. Apply `COMPACT-PRESERVE` patterns to keep specific content
3. Inject `COMPACT-PROLOGUE` and `COMPACT-EPILOGUE` around summary (only if explicitly configured)
4. Replace history with compacted version

> **Note**: By default, the compacted summary is injected without wrapper content.
> Use `COMPACT-PROLOGUE` and `COMPACT-EPILOGUE` only when you need custom context framing.

---

## Turn Structure

### Single Turn Anatomy

```
┌────────────────────────────────────────────────────────────────┐
│ USER MESSAGE                                                    │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ [Prologues] (if first prompt of cycle)                   │   │
│ │ [Context] (if first prompt)                              │   │
│ │ [Main Prompt Content]                                    │   │
│ │ [RUN output] (if elided)                                 │   │
│ │ [VERIFY output] (if elided)                              │   │
│ │ [Epilogues] (if last prompt of cycle)                    │   │
│ └──────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│ ASSISTANT RESPONSE                                              │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ AI-generated response                                    │   │
│ └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

### Elision: Merging Adjacent Items

The `ELIDE` directive (in `.conv` files) or default behavior (in mixed CLI mode) merges adjacent items into a single turn.

**Without Elision (3 turns):**
```
Turn 1: RUN echo "test output"        → AI responds
Turn 2: PROMPT "Analyze the output"   → AI responds  
Turn 3: PROMPT "Suggest fixes"        → AI responds
```

**With Elision (1 turn):**
```
Turn 1: [RUN output] + [Analyze prompt] + [Suggest prompt] → AI responds once
```

**Benefits:**
- Fewer agent round-trips
- More context in single response
- Token-efficient

---

## Prologue/Epilogue Injection

### Injection Points

```
Cycle Start
    ↓
┌─────────────────────────────────────────────────────────┐
│ First Prompt                                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 1. CLI --prologue (before all)                      │ │
│ │ 2. HELP topic content                               │ │
│ │ 3. PROLOGUE directives (file-level)                 │ │
│ │ 4. Context (CONTEXT patterns)                       │ │
│ │ 5. Main prompt content                              │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
    ↓
[ Middle prompts - no injection ]
    ↓
┌─────────────────────────────────────────────────────────┐
│ Last Prompt                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 1. Main prompt content                              │ │
│ │ 2. EPILOGUE directives (file-level)                 │ │
│ │ 3. CLI --epilogue (after all)                       │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
    ↓
Cycle End
```

### Key Points

1. **Prologues** only inject on the **first prompt** of a cycle
2. **Epilogues** only inject on the **last prompt** of a cycle
3. **CLI options** wrap around file-level directives:
   - `--prologue` → before file prologues
   - `--epilogue` → after file epilogues

### Multi-Cycle Behavior

In multi-cycle execution (`-n 3`), prologues and epilogues apply per-cycle:

```
Cycle 1: [prologues] + prompts + [epilogues]
Cycle 2: [prologues] + prompts + [epilogues]  
Cycle 3: [prologues] + prompts + [epilogues]
```

---

## Mixed Prompt Mode

> **Feature**: ITERATE-CONSOLIDATION.md Phase 6  
> **Status**: Planned

### Overview

Mix inline prompts with `.conv` files in a single command:

```bash
sdqctl iterate --prologue "A" "promptB" work.conv "promptC" --epilogue "D"
```

### Default Behavior: Document-Based Elision

Adjacent items merge into single turns at boundaries:

```
Turn 1: [A] + [work.conv prologues] + [promptB] + [first work.conv prompt]
Turn 2..N-1: remaining work.conv prompts
Turn N: [last work.conv prompt] + [work.conv epilogues] + [promptC] + [D]
```

### Separator Syntax: `---`

Force turn boundaries with `---` (use `--` before targets containing `---`):

```bash
sdqctl iterate --prologue "A" -- "promptB" --- work.conv --- "promptC"
```

```
Turn 1: [A + promptB]
Turn 2+: work.conv prompts
Turn N: [promptC]
```

### Constraints

- Maximum ONE `.conv` file per invocation
- `---` is reserved (cannot be prompt content)
- Use `--` before targets when using `---` separators (Click parsing requirement)
- At least one target required

---

## Session Modes

Control how context accumulates across cycles with `--session-mode`:

### `accumulate` (default)

Keep all conversation history. Context grows with each cycle.

```
Cycle 1: [context] + prompts → responses added to history
Cycle 2: [history from 1] + prompts → responses added
Cycle 3: [history from 1+2] + prompts → responses added
```

**Use when:** Iterative refinement where each cycle builds on previous

### `compact`

Periodically compress history when context limit approached.

```
Cycle 1: prompts → responses
Cycle 2: prompts → responses
[Context at 80%] → COMPACT triggered
Cycle 3: [compacted summary] + prompts → responses
```

**Use when:** Long-running workflows that might hit context limits

### `fresh`

Start each cycle with clean context (re-read files).

```
Cycle 1: [context from files] + prompts → responses (discarded)
Cycle 2: [fresh context from files] + prompts → responses (discarded)
Cycle 3: [fresh context from files] + prompts → responses
```

**Use when:** 
- Each cycle should see current file state
- Workflow makes file changes that next cycle should see

---

## Examples

### Simple Workflow

```
# workflow.conv
MODEL gpt-4
ADAPTER copilot

PROLOGUE You are a code reviewer.

PROMPT Review the authentication module.
PROMPT Suggest security improvements.
```

**Lifecycle:**
1. Parse: 2 prompts, 1 prologue
2. Validate: No context patterns to check
3. Render: No variables to substitute
4. Execute:
   - Turn 1: `[prologue] + Review auth...` → response
   - Turn 2: `Suggest security...` → response

### Elided RUN + PROMPT

```
# verify-fix.conv
RUN npm test
ELIDE
PROMPT If tests failed, fix the issues.
```

**Lifecycle:**
1. Parse: 1 RUN step, 1 ELIDE, 1 PROMPT
2. Execute:
   - Turn 1: `[test output] + If tests failed...` → response (single turn)

### Multi-Cycle with Compaction

```
# iterative-fix.conv
MAX-CYCLES 5
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

PROMPT Analyze and improve the code.
COMPACT-PRESERVE error messages
```

**Lifecycle per cycle:**
1. Check context usage
2. If >80%, trigger COMPACT with preserved error messages
3. Execute prompt with (possibly compacted) history

---

## Debugging Tips

### See What's Being Sent

```bash
sdqctl iterate workflow.conv --dry-run    # Preview without executing
sdqctl iterate workflow.conv --render-only # Show rendered prompts
sdqctl -P iterate workflow.conv           # Show prompts on stderr
```

### Trace Execution

```bash
sdqctl -vvv iterate workflow.conv         # TRACE level logging
sdqctl iterate workflow.conv --event-log events.jsonl  # SDK events
```

### Validate Before Running

```bash
sdqctl validate workflow.conv             # Check syntax and references
sdqctl validate workflow.conv --check-model  # Also check model resolution
```

---

## See Also

- [DIRECTIVE-REFERENCE.md](DIRECTIVE-REFERENCE.md) - Complete directive catalog
- [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md) - Context patterns and limits
- [ITERATE-CONSOLIDATION.md](../proposals/ITERATE-CONSOLIDATION.md) - Command design
- [PHILOSOPHY.md](PHILOSOPHY.md) - Design principles
