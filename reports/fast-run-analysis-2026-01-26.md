# Fast Run Analysis: 27-Minute Success

> **Date**: 2026-01-26T22:19 UTC  
> **Workflow**: `examples/workflows/backlog-processor-v2.conv`  
> **Duration**: 27m 12s (real), 2m 8s (user), 11s (sys)  
> **Model**: claude-sonnet-4-20250514  
> **Adapter**: Copilot SDK

---

## Executive Summary

This was the **fastest 5-cycle run recorded** for the backlog-processor-v2 workflow, completing in just 27 minutes - nearly 25% faster than the previous best (35m 36s baseline) and 74% faster than the slowest run (103m 32s).

### Run Metrics

| Metric | This Run | Baseline | Fastest Prior | Slowest Prior |
|--------|----------|----------|---------------|---------------|
| **Wall Clock** | **27m 12s** ✨ | 35m 36s | 35m 36s | 103m 32s |
| **Cycles** | 5/5 ✅ | 5/5 | 5/5 | 5/5 |
| **Prompts** | 45 | 45 | 45 | 45 |
| **Commits** | 8 | 6 | 5 | 11 |
| **Compactions** | 0 explicit | 1 | 1 | 2 |
| **Final Context** | 9% | 44% | 56% | 13% |
| **Tokens In** | 21.3M | 23.1M | 22.6M | 30.2M |
| **Tokens Out** | 57K | 92K | 103K | 115K |

### Key Finding: **Smaller Work Items = Faster Execution**

This run focused on **documentation and marker tasks** (P3 items) rather than major refactoring (P2). The lightweight work items resulted in:
- Faster Phase 1 selection (fewer decisions)
- Lighter Phase 2 execution (no major code changes)
- No compaction needed until final turn

---

## Timing Analysis

### Per-Cycle Duration

| Cycle | Duration | Context Start→End | Primary Work |
|-------|----------|-------------------|--------------|
| 1 | 4m 22s | 0% → 32% | Q-021 separator docs (resolved) |
| 2 | 8m 39s | 53% → 56% | Q-019A timestamps (resolved) |
| 3 | 3m 39s | 56% → 65% | Integration test markers |
| 4 | 3m 19s | 65% → 73% | @pytest.mark.slow marker |
| 5 | 3m 02s | 74% → 81% → 9% | README docs batch |
| **Total** | **27m 12s** | 0% → 9% | 8 commits |

**Observation**: Cycles 3-5 averaged just 3m 20s each - the fastest sustained execution observed.

### Per-Phase Timing (Averaged)

| Phase | Avg Duration | Range | vs Baseline |
|-------|--------------|-------|-------------|
| P1: Selection | **159.9s** | 75-396s | +258% ⚠️ |
| P2: Execute | **14.9s** | 13-17s | -93% ✅ |
| P3: Verify | **22.9s** | 21-26s | +9% |
| P4: Docs | **19.2s** | 9-33s | -39% |
| P5: Hygiene | **10.5s** | 10-11s | -36% |
| P6: Commit | **12.0s** | 9-13s | -15% |
| P7: Discovery | **11.6s** | 10-14s | -17% |
| P8: Routing | **11.9s** | 11-13s | +19% |
| P9: Archive | **16.6s** | 13-19s | -28% |

**Key Pattern**: Phase 2 (Execute) was 93% faster than baseline because work was completed during Phase 1 (Selection). This is the "work-during-selection" pattern previously observed in slower runs, but here it worked efficiently due to simpler tasks.

### Phase 1 Anomaly Analysis

Cycle 2 had an unusually long P1 (396s / 6.6 minutes). Investigation shows:
- Multiple document scans (BACKLOG.md, QUIRKS.md, COMMANDS.md)
- Discovered Q-019A needed timestamp fix
- Implemented the fix within P1 before P2 was reached
- This front-loading is acceptable when work is well-defined

---

## Context Window Evolution

```
Cycle 1: 0% ────────────────────────────> 32%
Cycle 2: 53% ──────────────────────────> 56%
Cycle 3: 56% ──────────────────────────> 65%
Cycle 4: 65% ──────────────────────────> 73%
Cycle 5: 74% ─────────────> 81% ──> 🗜️ → 9%
```

### Compaction Efficiency

| Event | Trigger | Before | After | Method |
|-------|---------|--------|-------|--------|
| Cycle 5, P9 | End of session | 81% | 9% | Server-side |

**Notable**: Only one compaction occurred, and it was at session end. The run stayed under 80% for 44 of 45 prompts, demonstrating excellent context economy.

### Token Statistics

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Input tokens | 21,303,104 | -8% |
| Output tokens | 56,819 | -38% |
| Total turns | 243 | -24% |
| Tool calls | 246 | -31% |
| Failed tools | 1 | Same |

**Efficiency**: This run used 38% fewer output tokens while producing 33% more commits.

---

## Work Accomplished

### Commits (8 total)

| # | Commit | Type | Description |
|---|--------|------|-------------|
| 1 | af36722 | docs | Q-021 separator documentation in iterate.py help |
| 2 | e179838 | docs | CONVERSATION-LIFECYCLE.md update for Q-021 |
| 3 | f590a40 | chore | Backlog hygiene - update Ready Queue |
| 4 | dea24e1 | feat | Progress timestamps when verbose (Q-019A) |
| 5 | a89e593 | docs | Timestamps in -v option description |
| 6 | 0d43879 | feat | Integration test markers (conftest.py) |
| 7 | d88868c | feat | @pytest.mark.slow for timeout test |
| 8 | 8f15e6d | docs | Test markers and refcat patterns in README |

### Quirks Resolved

- **Q-021**: `---` separator documentation (P2) ✅ → RESOLVED
- **Q-019A**: Progress timestamps when verbose (P3) ✅ → RESOLVED

### Test Improvements

- Added `tests/integration/conftest.py` with auto-marker
- All integration tests now selectable with `-m integration`
- Timeout test marked with `@pytest.mark.slow`
- Test count: 1296 → 1300 (+4 new tests)

---

## Comparison to Predictions

### Original Predictions (from run-prediction-2026-01-26.md)

| Metric | Predicted | Actual | Accuracy |
|--------|-----------|--------|----------|
| Duration | 55-75m (medium) | **27m** | ✨ Beat low estimate by 51% |
| Commits | 4-9 | 8 | ✅ Within range |
| Compactions | 1-2 | 1 | ✅ Correct |
| copilot.py tackled | 85% likely | ❌ No | P3 work instead |

**Why faster than predicted?**
1. **Work selection**: P3 documentation tasks instead of P2 refactoring
2. **Pre-resolved blockers**: Q-021 was already documented, just needed propagation
3. **Clean codebase**: Prior runs had reduced technical debt
4. **Session freshness**: No rate limit proximity effects

---

## Historical Comparison

### All 5-Cycle Runs

| Date | Duration | Commits | Tokens | Type |
|------|----------|---------|--------|------|
| **2026-01-26 PM** | **27m 12s** ✨ | 8 | 21.3M | Light (P3) |
| 2026-01-26 AM (B) | 35m 36s | 6 | 23.1M | Mixed (P2/P3) |
| 2026-01-26 AM (1) | 45m 02s | 5 | 22.6M | Heavy (P2) |
| 2026-01-26 AM (2) | 103m 32s | 11 | 30.2M | Heavy (P2) |

### Correlation: Duration vs Work Complexity

```
Duration    Work Type           Tokens/Commit
────────────────────────────────────────────
27m         Documentation       2.7M
36m         Mixed refactor      3.9M  
45m         Heavy refactor      4.5M
104m        Multi-feature       2.7M (more commits)
```

**Insight**: Documentation/marker work achieves ~2.7M tokens per commit, while refactoring work costs ~4M+ tokens per commit. The 27m run and 104m run have similar per-commit token costs - the difference is total commits attempted.

---

## Run Patterns Identified

### Pattern 1: Work-During-Selection (Neutral)

Phase 1 absorbed implementation in cycles 1-2, evidenced by:
- P1: 135-396s (long)
- P2: 13-17s (trivial, just commits)

This is acceptable when:
- Work items are clear and well-defined
- No major code changes needed
- Documentation-focused tasks

### Pattern 2: Sustained Fast Cycles

Cycles 3-5 maintained 3-minute average:
- No context pressure (stayed under 75%)
- Light work items (markers, README)
- Clean git state between cycles

### Pattern 3: Late Compaction

Single compaction at 81% in final phase:
- Server-side compaction (not workflow-triggered)
- Reduced from 81% → 9%
- Indicates efficient context usage throughout

---

## Recommendations

### 1. Document "Light Run" Pattern

This run demonstrates that P3 work can be batched efficiently:
- 5+ items completed in 27 minutes
- Good for clearing documentation backlog
- Schedule after heavy refactoring runs

### 2. Consider P3 Batching Days

Reserve some automation runs specifically for P3 tasks:
- Documentation updates
- Test marker additions
- Backlog hygiene
- Quirk resolution

### 3. Update Timing Predictions

New prediction model should include work type:
- **Light (P3 focus)**: 25-35m for 5 cycles
- **Mixed (P2/P3)**: 35-55m for 5 cycles
- **Heavy (P2 major)**: 55-90m for 5 cycles
- **Multi-feature**: 90-120m for 5 cycles

---

## Conclusions

### This Run: ✅ Exceptional

| Criterion | Assessment |
|-----------|------------|
| Completion | 5/5 cycles, all prompts |
| Speed | 27m 12s (fastest ever) |
| Quality | 8 commits, all clean |
| Context | Never exceeded 81% |
| Errors | 1 failed tool (minor) |

### Key Learnings

1. **Work type dominates timing**: P3 work runs 2-4× faster than P2
2. **Work-during-selection is fine**: For simple tasks, P1 can do implementation
3. **Context economy matters**: Staying under 80% avoids mid-run compactions
4. **Documentation batches**: Clearing doc backlog is fast and valuable

### Project State Post-Run

- **Commits**: 495 total (+8 this run)
- **Tests**: 1,300 (all passing)
- **Open Quirks**: 0 (Q-021, Q-019A both resolved)
- **Ready Queue**: 3 items (session fixtures, error path tests, refcat example)

---

## Raw Metrics

```
Workflow: backlog-processor-v2.conv
Duration: 1631.994s (27m 11.994s)
Cycles: 5/5
Prompts: 45 (9 × 5)
Turns: 243
Tool calls: 246
Compactions: 1 (end of session)
Context peak: 81%
Context final: 9%
Commits: 8
Quirks resolved: 2
Tests added: 4
```

---

*Report generated from analysis of:*
- `/home/bewest/src/copilot-do-proposal/backlogv2-yet-another-5run.log` (3,204 lines)
- Session duration: 27m 12s (real), 2m 8s (user), 11s (sys)

*This is the 26th analysis report in the sdqctl reports collection.*
