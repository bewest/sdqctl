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
| `implement-improvements.conv` | 95 lines | Minimal prologue, hints in prompts |
| `security-audit.conv` | 85 lines | Role prologue only |

The `test-discovery.conv` workflow pre-loads 6 files via CONTEXT, consuming context before the agent even starts. The hint-based workflows reserve that capacity for tool results.

### Precise Extraction with REFCAT

When you need specific sections rather than entire files, use `sdqctl refcat`:

```bash
# Extract only the function you need (lines 182-194)
sdqctl refcat @sdqctl/core/context.py#L182-L194

# Find and extract by pattern
sdqctl refcat @lib/auth.py#/def authenticate/
```

Output includes metadata for agent disambiguation:

```markdown
## From: sdqctl/core/context.py:182-194 (relative to /home/user/project)
```python
182 |     def get_context_content(self) -> str:
183 |         """Get formatted context content..."""
...
```
```

This is more token-efficient than CONTEXT for large files where you only need specific sections.

---

## SDK Infinite Sessions (v2)

The Copilot SDK v2 introduces **Infinite Sessions** with native background compaction. When enabled, the SDK automatically manages context window limits without requiring manual `COMPACT` directives.

### How It Works

```
Context grows during workflow execution
        │
        ▼
At 80% context usage (background_compaction_threshold)
  → SDK starts background compaction asynchronously
  → Workflow continues uninterrupted
        │
        ▼
At 95% context usage (buffer_exhaustion_threshold)
  → SDK blocks until compaction completes
  → Prevents context overflow
        │
        ▼
After compaction
  → Context reduced, workflow continues
  → session.compaction_complete event emitted
```

### Configuration

```python
# SDK configuration (via adapter)
session = await client.create_session({
    "model": "gpt-5",
    "infinite_sessions": {
        "enabled": True,
        "background_compaction_threshold": 0.80,  # Start at 80%
        "buffer_exhaustion_threshold": 0.95,      # Block at 95%
    },
})
```

### sdqctl Integration ✅

Infinite sessions CLI options are now active in `iterate` mode:

```bash
# Default: infinite sessions enabled
sdqctl iterate workflow.conv -n 10

# Disable infinite sessions (use client-side compaction)
sdqctl iterate workflow.conv -n 10 --no-infinite-sessions

# Client-side compaction with session reset (destroy old, create new with summary)
sdqctl iterate workflow.conv -n 10 --no-infinite-sessions --reset-on-compact

# Custom thresholds
sdqctl iterate workflow.conv -n 10 \
    --compaction-min 25 \
    --compaction-threshold 75 \
    --compaction-max 90
```

### Threshold Behavior

| CLI Option | Directive | Default | Behavior |
|------------|-----------|---------|----------|
| `--compaction-min` | `COMPACTION-MIN` | 30% | Skip compaction if context below this |
| `--compaction-threshold` | `COMPACTION-THRESHOLD` | 80% | Start background compaction |
| `--compaction-max` | `COMPACTION-MAX` | 95% | Block until compaction complete |
| `--reset-on-compact` | N/A | off | Destroy session and create new with compacted summary |

> **Note**: `--min-compaction-density` and `--buffer-threshold` are deprecated aliases.

### Session Reset on Compaction

When `--reset-on-compact` is enabled, client-side compaction will:

1. Send `/compact` to get a summary of the conversation
2. Destroy the old session
3. Create a new session
4. Inject the compacted summary into the new session

This ensures a truly clean context window. Use when:
- SDK infinite sessions are disabled (`--no-infinite-sessions`)
- You need guaranteed context reduction (not just in-place compaction)
- Testing or debugging compaction behavior

### When to Use Manual COMPACT

Even with infinite sessions enabled, you may still want explicit `COMPACT` directives:

1. **Phase transitions** - Compact before switching from investigation to synthesis
2. **Context freshness** - Force compaction to get clean slate for new phase
3. **Preserving specific content** - Use `COMPACT-PRESERVE` for important items

### Implementation Status

All phases complete (Phase 1-4). Configuration available via CLI options and directives:

```dockerfile
# Enable/disable SDK infinite sessions
INFINITE-SESSIONS enabled    # or: disabled

# Minimum context density to trigger compaction (default: 30%)
COMPACTION-MIN 30           # or: 30%

# SDK background compaction threshold (default: 80%)
COMPACTION-THRESHOLD 80     # or: 80%
```

**Priority**: CLI flags override directive values, which override defaults.

See [SDK-INFINITE-SESSIONS proposal](../proposals/SDK-INFINITE-SESSIONS.md) for implementation details.

---

## Session Modes

| Mode | Context Behavior | Token Usage | Best For |
|------|------------------|-------------|----------|
| **accumulate** (default) | Grows across cycles; compacts only at limit | Medium-High | Iterative refinement |
| **compact** | Summarizes after each cycle | Low | Long workflows (10+ cycles) |
| **fresh** | New session each cycle | High (no reuse) | Autonomous file editing |

### Fresh Mode

```bash
sdqctl iterate workflow.conv -n 5 --session-mode fresh
```

Each cycle starts with a clean context. Use when:
- Agent edits files and needs to see fresh versions
- Tasks are independent across cycles
- You want predictable context usage per cycle

### Accumulate Mode (Default)

```bash
sdqctl iterate workflow.conv -n 5 --session-mode accumulate
```

Context grows across cycles. Use when:
- Building on previous analysis
- Need conversation continuity
- Tasks reference prior cycle outputs

**Caveat:** Monitor context percentage; may need manual COMPACT.

**With Infinite Sessions:** When SDK infinite sessions are enabled, accumulate mode benefits from automatic background compaction—no manual intervention needed for long-running workflows.

### Compact Mode

```bash
sdqctl iterate workflow.conv -n 10 --session-mode compact
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

Examples: `implement-improvements.conv`, `fix-quirks.conv`, `sdk-debug-integration.conv`

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
sdqctl -v iterate workflow.conv -n 3
# Shows: (ctx: 45%) after each turn
```

### With Prompt Display

```bash
sdqctl -vv -P iterate workflow.conv -n 3
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

---

## Throughput Expectations

When using well-structured workflows with strategic COMPACTs:

| Metric | Typical Range | Notes |
|--------|---------------|-------|
| Lines per workflow | 500-2,000 | Implementation workflows produce more |
| Throughput | 50-150 lines/min | Depends on task complexity |
| Duration per phase | 3-5 min | 4-phase workflows ~15-20 min total |

### Factors Affecting Throughput

**Faster**:
- Clear specifications in PROLOGUE/EPILOGUE
- Strategic COMPACTs between phases
- Focused single-deliverable workflows
- Pattern files via `@` context (agent follows existing style)

**Slower**:
- Large context file injection
- Exploratory/research tasks
- Complex multi-file implementations
- Frequent tool use (many file reads)

### Real-World Example

From the CLI ergonomics session (2026-01-23):
- **Predicted**: 300 lines in 30-40 min
- **Actual**: 2,229 lines in 20 min (~110 lines/min)
- **Key factors**: 4-phase structure, COMPACT at phase boundaries, clear proposal spec

See: [reports/cli-ergonomics-experience-2026-01-23.md](../reports/cli-ergonomics-experience-2026-01-23.md)
