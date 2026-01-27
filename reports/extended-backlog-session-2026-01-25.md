# Extended Backlog Session Experience Report

> **Date**: 2026-01-25  
> **Duration**: 88m 44s (real), 6m 38s (user), 0m 31s (sys)  
> **Cycles**: 10  
> **Session Mode**: fresh  
> **Final Context**: 46% (59,314/128,000 tokens)  
> **Total Tokens**: 7,059,473 in / 25,839 out  
> **Tool Calls**: 137  
> **Goal**: Evaluate cohesiveness of proposals with "EVALUATE ALL" prefix

---

## Executive Summary

This session extended the previous backlog processing run (78m40s) to 88m44s by adding an "EVALUATE ALL following task lists, proposals and backlogs for cohesiveness" prefix to the prologue. The instruction successfully encouraged broader cross-document review, though the session revealed **tool name logging issues** (1,695 "unknown" tool entries) that warrant investigation.

**Key Finding**: The "EVALUATE ALL" prefix improved cross-document awareness compared to the previous session, with the agent explicitly performing cohesiveness evaluation in early cycles before work selection.

**Issue Discovered**: Tool completion logs show "unknown" instead of tool names in 1,695 instances, indicating a gap in the `tool.execution_complete` event handling where tool_name is not being extracted properly.

---

## Comparison: Previous vs Current Session

| Metric | Previous (2026-01-24 AM) | Current (2026-01-24 PM) | Delta |
|--------|--------------------------|-------------------------|-------|
| Duration | 78m 40s | 88m 44s | +10m (+13%) |
| Cycles | 10 | 10 | — |
| Session Mode | fresh | fresh | — |
| Final Context | 46% | 46% | — |
| Messages | 80 | 80 | — |
| "EVALUATE ALL" prefix | ❌ No | ✅ Yes | New |
| Tool calls with "unknown" | Not measured | 1,695 | Issue |

### Timing Breakdown by Cycle

| Cycle | Previous | Current | Notes |
|-------|----------|---------|-------|
| 1 | ~10m 30s | 8m 28s | Faster - less exploration |
| 2 | ~2m 40s | 6m 57s | Slower - cohesiveness work |
| 3 | ~8m | 17m 24s | Much longer - deep implementation |
| 4 | ~3m 15s | 12m 26s | ON-FAILURE/ON-SUCCESS blocks |
| 5 | ~4m | 4m 36s | Similar |
| 6 | ~9m | 6m 56s | Faster |
| 7 | ~6m | 8m 18s | Longer |
| 8 | ~13m 30s | 9m 15s | Faster |
| 9 | ~9m 30s | 8m 44s | Similar |
| 10 | ~5m 15s | 5m 55s | Similar |

**Observation**: The "EVALUATE ALL" prefix caused cycles 2-4 to take significantly longer as the agent performed more thorough cross-document analysis before selecting work items.

---

## Effect of "EVALUATE ALL" Prefix

### Command Comparison

**Previous**:
```bash
sdqctl -vvv cycle --session-mode=fresh \
  examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md \
  --prologue proposals/ARTIFACT-TAXONOMY.md \
  --adapter copilot -n 10
```

**Current**:
```bash
sdqctl -vvv cycle --session-mode=fresh \
  examples/workflows/backlog-processor.conv \
  --prologue "EVALUATE ALL following task lists, proposals and backlogs for cohesiveness." \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md \
  --prologue proposals/ARTIFACT-TAXONOMY.md \
  --adapter copilot -n 10
```

### Observed Behavior Changes

1. **Cross-document awareness**: Agent explicitly created TODO items for cohesiveness evaluation:
   ```
   ## Cohesiveness Evaluation & Work Selection
   
   ### Phase 1: Document Review
   - [x] Read BACKLOG.md (main backlog - executive summary, proposals status)
   - [x] Read REFCAT-DESIGN.md (Status: Implemented ✅)
   - [x] Read ARTIFACT-TAXONOMY.md (Status: PROPOSAL, Phase 0-0.5 complete)
   
   ### Phase 2: Cohesiveness Evaluation
   - [x] Cross-reference documents for gaps/inconsistencies
   - [x] Documents are well-aligned and cohesive
   - [x] Identify remaining work items
   ```

2. **Directive count update**: Agent noticed and fixed directive count discrepancy (50 → 66 directives)

3. **Links verifier bug fix**: Found and fixed code block exclusion issue in links verifier

---

## The "unknown" Tool Name Issue

### Symptoms

1,695 log entries show `unknown` instead of the actual tool name:

```
15:43:02 [INFO] sdqctl.adapters.copilot: [backlog-processor:10/10:P4/4]   ✓ unknown (0.3s) → 906 chars
15:43:10 [INFO] sdqctl.adapters.copilot: [backlog-processor:10/10:P4/4]   ✓ unknown (0.3s) → 109 chars
15:43:14 [INFO] sdqctl.adapters.copilot: [backlog-processor:10/10:P4/4]   ✓ unknown (0.8s) → 150 chars
```

### Root Cause Analysis

The `tool.execution_complete` event handler extracts tool name but may be falling back to "unknown":

```python
# From copilot.py - potential issue
elif event_type == "tool.execution_complete":
    tool_call_id = _get_field(data, "tool_call_id", None)
    success = _get_field(data, "success", False)
    
    if tool_call_id in stats.active_tools:
        tool_info = stats.active_tools.pop(tool_call_id)
        # ... uses tool_info["name"]
    else:
        # Falls through to "unknown" when tool_call_id not found
```

### Possible Causes

1. **tool_call_id mismatch**: The ID from `execution_start` differs from `execution_complete`
2. **Event ordering**: Complete events arriving before start events in some cases
3. **SDK field naming**: The field might be named differently than expected

### Recommendation

Add debug logging to capture the raw event data when tool name extraction fails:

```python
if tool_call_id not in stats.active_tools:
    logger.warning(f"Tool complete without matching start: id={tool_call_id}, data={data}")
```

---

## Work Accomplished

### Commits Made (from log)

1. `feat(verify): add --strict flag to refs, links, and all commands`
2. `feat(adapters): add metadata APIs (get_cli_status, get_auth_status, list_models)`
3. `feat(status): Add SDK metadata APIs to status command (Phase 2)`
4. `feat(cli): add --json-errors flag for structured error output`
5. `feat: Add REQUIRE directive for pre-flight checks`
6. `docs: Add REQUIRE directive to README and help topic`
7. `docs(BACKLOG): add session notes for cohesiveness fixes`

### Features Implemented

| Feature | Proposal | Status |
|---------|----------|--------|
| `--strict` flag for verifiers | ERROR-HANDLING Phase 1 | ✅ Complete |
| SDK metadata APIs in adapters | SDK-METADATA-APIS Phase 1 | ✅ Complete |
| Enhanced `sdqctl status` | SDK-METADATA-APIS Phase 2 | ✅ Complete |
| `--json-errors` flag | ERROR-HANDLING Phase 3 | ✅ Complete |
| `REQUIRE` directive | New feature | ✅ Complete |
| Links verifier code block fix | Bug fix | ✅ Complete |
| Directive count update | BACKLOG accuracy | ✅ Complete |

---

## Context Window Progression

| Cycle | End Context | Messages |
|-------|-------------|----------|
| 1 | 0% | Fresh |
| 2 | 1% | Fresh |
| 3 | 2% | Fresh |
| 4 | 3% | Fresh |
| 5 | 4% | Fresh |
| 6 | 4% | Fresh |
| 7 | 5% | Fresh |
| 8 | 6% | Fresh |
| 9 | 6% | Fresh |
| 10 | 7% (46% at end) | 141 |

**Note**: With `--session-mode=fresh`, each cycle starts with a new session. The context percentage shown is the starting point. The final cycle reached 46% (59,314/128,000 tokens) with 141 messages before session end.

---

## Lessons Learned

### 1. "EVALUATE ALL" Prefix Works

Adding explicit cross-document evaluation instructions to the prologue successfully counters the first-prologue bias identified in the previous session. The agent spent more time in early cycles doing cohesiveness evaluation before diving into implementation.

**Recommendation**: Add this pattern to the backlog-processor.conv workflow template.

### 2. Tool Name Logging Needs Investigation

The 1,695 "unknown" tool entries indicate a logging gap that should be fixed for better observability. The tool *executes* correctly (based on output sizes and timing), but the name is not being captured in completion logs.

**Action Item**: Add Q-013 to QUIRKS.md for tool name extraction issue.

### 3. Fresh Session Mode is Effective

Context reset between cycles prevented accumulation, allowing each cycle to work with minimal context overhead. The trade-off is losing cross-cycle context, but the prologue injection provides necessary continuity.

### 4. Longer Sessions Produce More Work

At 88m44s, this is the longest automated session. The extra 10 minutes over the previous run (from cohesiveness evaluation) resulted in additional bug fixes and documentation improvements.

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Total duration | 88m 44s |
| Average cycle time | 8m 52s |
| Longest cycle | Cycle 3 (17m 24s) |
| Shortest cycle | Cycle 5 (4m 36s) |
| Total input tokens | 7,059,473 |
| Total output tokens | 25,839 |
| Tool calls | 137 |
| "unknown" tool logs | 1,695 (issue) |
| Commits | 7+ |
| Features completed | 5+ |

---

## Follow-up Items

- [ ] Investigate "unknown" tool name issue (Q-013)
- [ ] Add "EVALUATE ALL" pattern to workflow template
- [ ] Consider adding cohesiveness evaluation as a dedicated Phase 0
- [ ] Monitor tool call ID matching between start/complete events

---

## References

- Previous session: [backlog-long-session-2026-01-24.md](backlog-long-session-2026-01-24.md)
- Log file: `../longer-workflow.log` (14,158 lines)
- Workflow: `examples/workflows/backlog-processor.conv`
