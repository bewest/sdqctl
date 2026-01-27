# Accumulate Mode Critical Findings Report

> **Date**: 2026-01-25  
> **Duration**: 30m 47.9s (real), 3m 11.8s (user), 0m 14.1s (sys)  
> **Cycles**: 4.5 (stopped by agent via STOPAUTOMATION)  
> **Session Mode**: accumulate  
> **Severity**: 🔴 Critical - multiple bugs discovered  
> **Log**: `../longer-workflow-again.log` (33,632 lines, 3.6MB)

---

## Executive Summary

This session revealed **critical bugs** in `--session-mode=accumulate` that cause exponential resource consumption and data corruption. Despite completing only 4.5 cycles (vs 10 in previous sessions), it consumed **40x more input tokens** than a comparable fresh-mode session.

| Finding | Severity | Quirk ID |
|---------|----------|----------|
| Event handler multiplexing | 🔴 Critical | Q-014 |
| Duplicate tool calls at termination | 🔴 Critical | Q-015 |
| Unknown tool names regression | 🟡 Medium | Q-013 (reopened) |
| Log line duplication (25x) | 🟡 Medium | Symptom of Q-014 |

**Root cause**: Event handlers appear to accumulate across cycles without cleanup, causing N handlers to fire for each event where N ≈ prompt count.

**Recommendation**: Use `--session-mode=fresh` for multi-cycle runs until Q-014 is resolved.

---

## Session Comparison

| Metric | This Run (Accumulate) | Extended (Fresh) | Long (Fresh) |
|--------|----------------------|------------------|--------------|
| Date | 2026-01-25 | 2026-01-24 PM | 2026-01-24 AM |
| Duration | 30m 48s | 88m 44s | 78m 40s |
| Cycles | 4.5 (stopped) | 10 | 10 |
| Session Mode | **accumulate** | fresh | fresh |
| Turns logged | **3,667** | ~1,400 | ~1,200 |
| Tool calls | **3,878** | 137 | ~1,400 |
| Input tokens | **276,504,117** | 7,059,473 | ~107,000,000 |
| Output tokens | 864,903 | 25,839 | ~405,000 |
| "unknown" tools | **3,535 (91%)** | 1,695 | Not measured |
| Failed tools | 28 | 0 | 2 |
| Commits | 4 | 7+ | 14 |

### Token Explosion Analysis

| Session | Tokens/Cycle | Tokens/Minute |
|---------|--------------|---------------|
| This run (accumulate) | 61.4M | 8.97M |
| Extended (fresh) | 706K | 79.6K |
| **Ratio** | **87x** | **113x** |

The accumulate session consumed 87x more tokens per cycle than the fresh session.

---

## Bug #1: Event Handler Multiplexing (Q-014)

### Evidence

Multiple turns "starting" at the same millisecond:

```
21:51:47 [INFO] Turn 132 started
21:51:47 [INFO] Turn 133 started  
21:51:47 [INFO] Turn 134 started
21:51:47 [DEBUG] Context: 69,669/128,000 tokens (54%), 103 messages
21:51:47 [DEBUG] Context: 69,669/128,000 tokens (54%), 103 messages
```

By session end, each log line repeated 25x:

```
20:01:04 [INFO] Turn 3667 ended  # x25
20:01:04 [DEBUG] Context: 37,823/128,000 tokens (29%), 178 messages  # x25
20:01:09 [INFO] Tokens: 51987 in / 240 out  # x25
```

### Progression Analysis

| Cycle | Approx Handler Count | Evidence |
|-------|---------------------|----------|
| 1 | 6 | 6-phase workflow |
| 2 | 12 | 6 + 6 from new cycle |
| 3 | 18 | Accumulating |
| 4 | 24 | Near 25x seen at end |
| 5 | ~25 | 25x duplication observed |

### Impact

- **3,667 turns logged** for what should be ~150 turns
- **276M input tokens** instead of ~10M expected
- Tool tracking corrupted (Q-013 regression)

### Hypothesis

```python
# Suspected issue in cycle command
for cycle in range(max_cycles):
    for prompt in prompts:
        session.on_event("turn.started", handler)  # Accumulates!
        # Handler never removed, fires on all subsequent events
```

---

## Bug #2: Duplicate Tool Calls (Q-015)

### Evidence

At session termination, the same STOPAUTOMATION command executed 15+ times:

```
20:01:02 [INFO] 🔧 Tool: bash  # Same command
20:01:02 [INFO] 🔧 Tool: bash
20:01:02 [INFO] 🔧 Tool: bash
... (15 total)
20:01:04 [INFO] ✓ bash (1.3s) → Created STOPAUTOMATION file
20:01:04 [INFO] ✓ unknown → Created STOPAUTOMATION file
... (24 more "unknown" completions)
```

### Impact

- 15+ bash processes spawned for one logical tool call
- File created successfully (first write wins)
- Resource waste
- Corrupts tool_call_id tracking

---

## Bug #3: Unknown Tool Names Regression (Q-013)

### Statistics

| Metric | Value |
|--------|-------|
| Total tool calls | 3,878 |
| "unknown" completions | 3,535 |
| Percentage unknown | **91%** |

This is a regression from the Q-013 fix applied 2026-01-24. The fix used stored tool name from start event, but with multiplexed handlers:
- Multiple "start" events register different tool_call_ids
- "Complete" events can't match to correct start
- Falls back to "unknown"

### SDK 2 Hypothesis

The regression may also be related to SDK 2 changes:
- Different event field structure for `tool.execution_complete`
- `report_intent` tool affecting event ordering
- Changed `tool_requests` object format

---

## Timing Analysis

### Phase Timing by Cycle

| Cycle | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Total |
|-------|---------|---------|---------|---------|---------|---------|-------|
| 1 | 49s | 228s | 68s | 80s | 32s | 22s | 479s |
| 2 | 26s | 241s | 37s | 58s | 37s | 22s | 421s |
| 3 | 45s | 294s | 39s | 58s | 62s | 25s | 523s |
| 4 | 27s | 258s | 25s | 37s | 16s | 21s | 384s |
| 5 | 37s | - | - | - | - | - | (stopped) |

**Average cycle time**: 7m 27s (excluding partial cycle 5)

### Phase 2 (Execute) Dominates

Phase 2 (Execute) consistently takes 4-5 minutes, representing 55-70% of cycle time. This is expected as implementation work happens here.

---

## Work Accomplished

Despite the bugs, the session produced real value:

### Commits (4)

1. `feat(directives): implement CONSULT directive Phase 1`
   - CONSULT directive type, dataclass, execution handling
   - Block support in ON-FAILURE/ON-SUCCESS
   - Help documentation, test coverage

2. `feat(sessions): CONSULT directive Phase 2-3 - prompt injection on resume`
   - Save session status in checkpoint JSON
   - Detect 'consulting' status on resume
   - Inject CONSULTATION_PROMPT with topic

3. `feat(models): MODEL-REQUIREMENTS Phase 1 - abstract model selection`
   - MODEL-REQUIRES, MODEL-PREFERS, MODEL-POLICY directives
   - Capability-based model selection
   - New `sdqctl/core/models.py`

4. `feat(validate): MODEL-REQUIREMENTS Phase 2 - CLI integration`
   - `sdqctl validate --models` for model requirements checking

### Agent Self-Termination

Agent correctly used STOPAUTOMATION mechanism when it determined Phase 4 of CONSULT-DIRECTIVE wasn't worth implementing:

```json
{
  "reason": "CONSULT-DIRECTIVE Phase 4 contains only optional refinements...",
  "needs_review": true,
  "options": [
    "A: Implement Phase 4 refinements (Low value)",
    "B: Mark CONSULT as complete, defer Phase 4",
    "C: Select MODEL-REQUIREMENTS Phase 3 (Higher value)"
  ],
  "recommendation": "Option B or C"
}
```

---

## Session Mode Comparison

### accumulate vs fresh

| Aspect | accumulate | fresh |
|--------|------------|-------|
| Context per cycle | Carries over | Resets |
| Event handlers | **Accumulate (bug)** | Reset each cycle |
| Token efficiency | Poor (276M/5 cycles) | Good (7M/10 cycles) |
| Tool tracking | Corrupted | Works |
| Stability | 🔴 Unstable | ✅ Stable |

### When to Use

| Mode | Use Case | Status |
|------|----------|--------|
| `fresh` | Multi-cycle automation | ✅ Recommended |
| `accumulate` | Single-cycle with continuation | ⚠️ Use with caution |
| `accumulate` | Multi-cycle runs | 🔴 Do not use (Q-014) |

---

## Recommendations

### Immediate (Workaround)

1. **Use `--session-mode=fresh`** for all multi-cycle runs
2. **Monitor turn counts** - if turns >> expected, abort session
3. **Check for log duplication** - repeated lines indicate handler leak

### Investigation (Q-014)

1. Audit `_subscribe_events()` in copilot adapter
2. Check if handlers are removed between prompts
3. Add handler count logging at DEBUG level
4. Test: Does accumulate mode work with 1 prompt per cycle?

### Investigation (Q-013 / SDK 2)

1. Log raw event data when tool name extraction fails
2. Compare event structure between SDK 1 and SDK 2
3. Check if `report_intent` affects event ordering

---

## Action Items

- [ ] **Q-014**: Audit event subscription lifecycle in copilot adapter
- [ ] **Q-014**: Add handler count diagnostic logging
- [ ] **Q-013**: Log raw event data on extraction failure
- [ ] **R-001**: Compare SDK 1 vs SDK 2 event structures
- [ ] **R-002**: Create minimal repro for accumulate mode issue
- [ ] Update workflow templates to recommend `--session-mode=fresh`

---

## References

- [Archived Quirks - Q-014](../archive/quirks/2026-01-resolved-quirks.md#q-014-event-handler-multiplexing-in-accumulate-mode)
- [Archived Quirks - Q-015](../archive/quirks/2026-01-resolved-quirks.md#q-015-duplicate-tool-calls-at-session-termination)
- [Archived Quirks - Q-013](../archive/quirks/2026-01-resolved-quirks.md#q-013-tool-name-shows-unknown-in-completion-logs)
- [BACKLOG.md - Research Items](../proposals/BACKLOG.md#research-items-2026-01-25)
- Previous session: [extended-backlog-session-2026-01-25.md](extended-backlog-session-2026-01-25.md)
- Log file: `../longer-workflow-again.log`
