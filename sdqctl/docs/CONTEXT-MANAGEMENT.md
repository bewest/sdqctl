# Context Window Management

Guidance for optimally managing context window capacity across sdqctl workflows.

---

## Quick Reference

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **Hint, don't inject** | Large codebases, exploratory tasks | `PROMPT Check lib/auth/ for issues` |
| **Pre-load (CONTEXT)** | Small critical files (<100 lines) | `CONTEXT @config.yaml` |
| **COMPACT** | After tool-heavy phases | `COMPACT` after investigation |
| **Fresh sessions** | Independent tasks | `--session-mode fresh` |
| **Accumulate** | Building on analysis | `--session-mode accumulate` |

---

## Context Window Fundamentals

### What Fills the Context

When using sdqctl with an AI agent, the context window accumulates:

1. **Your prompts** - PROMPT, PROLOGUE, EPILOGUE, HEADER content
2. **Injected files** - Files from CONTEXT directives (expanded at render time)
3. **Agent responses** - All assistant messages and reasoning
4. **Tool calls** - Every tool invocation and its output (file reads, command results)
5. **Session history** - Previous turns in accumulate mode

### How Context Grows

```
Turn 1: Your prompt (100 tokens) + Agent response (500 tokens) = 600 tokens
Turn 2: + Your prompt (100) + File read tool (2000) + Response (800) = 3500 tokens
Turn 3: + Your prompt (100) + Multiple tools (5000) + Response (1000) = 9600 tokens
...
```

Tool-heavy investigation phases consume context rapidly. A single `view` of a 500-line file adds ~2000+ tokens.

### Empirical Measurements

From real sdqctl usage with Claude models:

| Context Usage | Approximate Size | Notes |
|---------------|------------------|-------|
| 98% full | ~10,000 lines | Includes code, prompts, all outputs |
| 60-80% | Typical completion | Opus 4.5 completing full cycles |
| 50% | Good synthesis headroom | Leaves room for substantial output |

---

## The 50% Synthesis Hypothesis

### The Claim

> "Compact or start fresh before synthesizing new results if the window is more than 40-50% full, since in theory half the context should be dedicated to the result."

### Analysis

This guidance reflects an important intuition but requires nuance:

**Why it makes sense:**
- Large synthesis tasks (reports, refactoring plans) need output space
- Quality may degrade when the model is "squeezed" near limits
- Compaction preserves essential context while freeing tokens

**Why it's not absolute:**
- Modern models generate incrementally (streaming), not all-at-once
- Observed: Claude Opus 4.5 produces good results at 60-80% context
- Some tasks need more input context than output space

**Practical guidance:**

| Task Type | Safe Context Threshold | Rationale |
|-----------|----------------------|-----------|
| Analysis/audit | 70-80% | Output is relatively compact |
| Report generation | 50-60% | Need room for structured output |
| Code refactoring | 40-50% | Output may be larger than input |
| Implementation | 60-70% | Depends on scope of changes |

### When to COMPACT

1. **After investigation, before synthesis** - You've gathered data, now need to write
2. **Before major phase transitions** - Triage → Implement → Document
3. **When context exceeds threshold** - Use `CONTEXT-LIMIT` directive
4. **When responses become terse** - May indicate context pressure

---

## Pre-loading Strategy

### When to Use CONTEXT

✅ **Do inject** small, critical files:
```dockerfile
CONTEXT @pyproject.toml          # Config the agent must see
CONTEXT @lib/types.py            # Type definitions (usually small)
CONTEXT @.env.example            # Environment template
```

❌ **Don't inject** large or exploratory content:
```dockerfile
# BAD: Wastes tokens, may not all be needed
CONTEXT @lib/**/*.py
CONTEXT @docs/*.md
```

### When to Hint Instead

Let the agent read files on demand:

```dockerfile
# GOOD: Agent fetches only what it needs
PROMPT Analyze the authentication module in lib/auth/.
  Start with auth_handler.py and trace the token flow.
  
# GOOD: Reference without injecting
PROMPT Previous findings are documented in reports/audit.md.
  Review them before proceeding.
```

### The Cost of Over-Context

From workflow analysis:

| Workflow | Rendered Size | Strategy |
|----------|---------------|----------|
| `test-discovery.conv` | **4,096 lines** | Heavy CONTEXT injection |
| `fix-quirks.conv` | 103 lines | Hint-based (agent reads on demand) |
| `progress-tracker.conv` | 95 lines | Minimal prologue, hints in prompts |
| `security-audit.conv` | 85 lines | Role prologue only |

The `test-discovery.conv` workflow pre-loads 6 files via CONTEXT, consuming context before the agent even starts. The hint-based workflows reserve that capacity for tool results.

---

## Session Modes

### Fresh Mode

```bash
sdqctl cycle workflow.conv -n 5 --session-mode fresh
```

Each cycle starts with a clean context. Use when:
- Agent edits files and needs to see fresh versions
- Tasks are independent across cycles
- You want predictable context usage per cycle

### Accumulate Mode (Default)

```bash
sdqctl cycle workflow.conv -n 5 --session-mode accumulate
```

Context grows across cycles. Use when:
- Building on previous analysis
- Need conversation continuity
- Tasks reference prior cycle outputs

**Caveat:** Monitor context percentage; may need manual COMPACT.

### Compact Mode

```bash
sdqctl cycle workflow.conv -n 10 --session-mode compact
```

Automatically summarize between cycles. Use when:
- Running many cycles (5+)
- Need some continuity but context would overflow
- Acceptable to lose exact details for summaries

---

## COMPACT Directive Usage

### Basic Usage

```dockerfile
PROMPT ## Phase 1: Investigation
  Analyze the codebase for security issues.

COMPACT

PROMPT ## Phase 2: Report
  Generate a findings report based on your analysis.
```

### Preserving Specific Content

```dockerfile
COMPACT-PRESERVE findings, security_issues
COMPACT

# Agent retains only: prompts, findings, security_issues
# Discards: file contents, intermediate reasoning
```

### Automatic Compaction

```dockerfile
CONTEXT-LIMIT 70%
ON-CONTEXT-LIMIT compact
COMPACT-PRESERVE errors, tool-results
```

Triggers compaction when context exceeds 70%.

---

## Per-Workflow Recommendations

### Light Workflows (50-100 rendered lines)

Examples: `security-audit.conv`, `human-review.conv`, `deep-analysis.conv`

These workflows use the hint pattern effectively:
- Role clarification in PROLOGUE (3-5 lines)
- Minimal session metadata
- Agent reads files on demand

**Status:** ✅ Well-contexted

### Medium Workflows (100-200 rendered lines)

Examples: `progress-tracker.conv`, `fix-quirks.conv`, `sdk-debug-integration.conv`

Include more PROLOGUE/EPILOGUE guidance:
- Session context (date, branch, commit)
- Implementation reminders
- Multiple COMPACT directives for phase transitions

**Status:** ✅ Appropriate for multi-phase work

### Heavy Workflows (1000+ rendered lines)

Examples: `test-discovery.conv` (4,096 lines rendered)

Uses CONTEXT directives to inject files upfront:
```dockerfile
CONTEXT @sdqctl/core/conversation.py
CONTEXT @sdqctl/commands/run.py
CONTEXT @INTEGRATION-PROPOSAL.md
CONTEXT @README.md
CONTEXT @TEST-PLAN.md
CONTEXT @examples/workflows/verify-with-run.conv
```

**Status:** ⚠️ Consider refactoring to hint pattern

**Optimization opportunity:**
```dockerfile
# Instead of:
CONTEXT @sdqctl/core/conversation.py
CONTEXT @sdqctl/commands/run.py

# Use:
PROMPT Analyze the conversation parser in sdqctl/core/conversation.py
  and the run command in sdqctl/commands/run.py.
```

---

## Decision Tree

```
Should I use CONTEXT to inject a file?
│
├─ Is the file < 100 lines AND critical (config, types)?
│  └─ YES → Use CONTEXT
│
├─ Is it a large source file (> 200 lines)?
│  └─ NO → Hint at location, let agent read
│
├─ Will I need the ENTIRE file or just parts?
│  └─ PARTS → Hint, agent will read specific sections
│
├─ Am I exploring/auditing (unknown scope)?
│  └─ YES → Hint, let agent navigate
│
└─ Am I analyzing a specific known file in detail?
   └─ YES → Consider CONTEXT if small, else hint
```

---

## Monitoring Context Usage

### During Execution

Use verbose mode to see context percentage:

```bash
sdqctl -v cycle workflow.conv -n 3
# Shows: (ctx: 45%) after each turn
```

### With Prompt Display

```bash
sdqctl -vv -P cycle workflow.conv -n 3
# Shows prompts and context percentage
```

### Pre-flight Check

```bash
sdqctl render run workflow.conv | wc -l
# Shows rendered prompt line count before execution
```

---

## Anti-Patterns

### 1. Glob CONTEXT Injection

```dockerfile
# BAD: Could inject thousands of lines
CONTEXT @lib/**/*.py
CONTEXT @docs/**/*.md
```

### 2. Injecting Reports as PROLOGUE

```dockerfile
# BAD: Wastes tokens on old analysis
--prologue @reports/full-analysis-50kb.md
```

### 3. No Compaction in Long Cycles

```dockerfile
MAX-CYCLES 10
# No COMPACT anywhere
# Context will overflow
```

### 4. Ignoring Context Warnings

When responses become terse or the agent says "I'm running low on context," heed it.

---

## Model-Specific Notes

| Model | Context Window | Notes |
|-------|----------------|-------|
| GPT-4 | 8K-128K | Varies by version |
| Claude Sonnet | 200K | Handles large context well |
| Claude Opus | 200K | Best quality at high context |
| Claude Haiku | 200K | Fast, good for exploration |

Larger context windows don't mean you should fill them. Quality can degrade even with space remaining.

---

## See Also

- [Getting Started](GETTING-STARTED.md) - Basic context guidance
- [Synthesis Cycles](SYNTHESIS-CYCLES.md) - "Hint, Don't Inject" pattern
- [Quirks](QUIRKS.md) - Q-002 discusses context-related behaviors
- [Loop Stress Test](LOOP-STRESS-TEST.md) - Testing context limits

---

## Summary

1. **Default to hinting** - Let agents read files on demand
2. **Pre-load only small critical files** - Config, types, interfaces
3. **COMPACT after investigation** - Before synthesis phases
4. **Monitor with -v** - Watch context percentage grow
5. **Use CONTEXT-LIMIT** - Automatic compaction trigger
6. **Match session mode to task** - Fresh for edits, accumulate for analysis
