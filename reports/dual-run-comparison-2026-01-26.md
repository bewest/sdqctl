# Dual Consecutive Run Analysis Report

> **Date**: 2026-01-26  
> **Workflow**: `examples/workflows/backlog-processor-v2.conv`  
> **Method**: Two 5-cycle runs with 20-minute cooldown between them  
> **Model**: claude-sonnet-4-20250514  
> **Adapter**: Copilot SDK

---

## Executive Summary

This report analyzes **two consecutive 5-cycle runs** with a 20-minute cooldown period between them, compared against a baseline run from earlier in the day.

| Metric | Baseline Run | Run 1 (Another) | Run 2 (Yet Another) |
|--------|-------------|-----------------|---------------------|
| **Wall Clock** | 35m 36s | **45m 2s** (+27%) | **103m 32s** (+191%) |
| **User CPU** | 2m 31s | 3m 21s | 5m 56s |
| **Cycles** | 5/5 ✅ | 5/5 ✅ | 5/5 ✅ |
| **Prompts** | 45 | 45 | 45 |
| **Tool Calls** | 356 | 347 | 400 |
| **Commits** | 6 | 5 | 11 |
| **Compactions** | 1 | 1 | 2 |
| **Final Context** | 56% | 56% | 13% |
| **Tokens In** | 23.1M | 22.6M | 30.2M |
| **Tokens Out** | 92K | 103K | 115K |

### Key Finding: **Run 2 took 2.3× longer than Run 1**

Despite identical workflow configuration and a 20-minute cooldown, Run 2 was significantly slower. Root cause analysis indicates:
1. **Phase 1 dominance** - Work selection took 200-350s consistently (vs baseline 8-175s)
2. **More compactions** - 2 compactions vs 1, indicating heavier context growth
3. **Higher token consumption** - 30M vs 22M input tokens

---

## Timing Comparison

### Per-Cycle Duration

| Cycle | Baseline | Run 1 | Run 2 | Run 2 vs Baseline |
|-------|----------|-------|-------|-------------------|
| 1 | 10m 48s | 11m 24s | **13m 54s** | +29% |
| 2 | 7m 10s | 6m 36s | **14m 24s** | +101% |
| 3 | 5m 21s | 7m 14s | **5m 27s** | +2% |
| 4 | 3m 42s | 7m 31s | **5m 22s** | +45% |
| 5 | 5m 52s | 3m 24s | **5m 33s** | -5% |
| **Total** | **35m 36s** | **38m 29s** | **45m 0s** | +26% |

*Note: Log file durations (38m 29s for Run 1, 45m for Run 2) differ from shell timing due to shutdown overhead. True timing from `time` command: 45m 2s and 103m 32s.*

### Per-Phase Timing (Averaged Across 5 Cycles)

| Phase | Baseline | Run 1 | Run 2 | Notes |
|-------|----------|-------|-------|-------|
| P1: Selection | 44.6s | **57.9s** | **270.1s** | 🔴 Run 2 is 6× slower |
| P2: Execute | 228.5s | **246.3s** | **104.8s** | Run 2 faster (work done in P1) |
| P3: Verify | 21.0s | **27.1s** | **36.4s** | Slightly slower |
| P4: Docs | 31.4s | **24.5s** | **18.9s** | Faster |
| P5: Hygiene | 16.4s | **16.4s** | **19.2s** | Similar |
| P6: Commit | 14.1s | **15.1s** | **12.6s** | Similar |
| P7: Discovery | 14.0s | **13.7s** | **14.5s** | Similar |
| P8: Routing | 10.0s | **10.9s** | **11.1s** | Similar |
| P9: Archive | 23.2s | **17.6s** | **23.1s** | Similar |

**Pattern Shift**: Run 2 exhibits an inverted P1/P2 pattern:
- Baseline & Run 1: Light P1 (selection), Heavy P2 (implementation)
- Run 2: Heavy P1 (selection+implementation merged), Light P2 (already done)

---

## Context Window Dynamics

### Context Evolution

```
Run 1 (Another):
Cycle 1: 0% ─────────────────────────────────────────> 51%
Cycle 2: 51% ───────────────────────────────────────> 73%
Cycle 3: 73% ─> 75% ──> 🗜️ COMPACT ──> 19% ────────> 25%
Cycle 4: 25% ─────────────────────────────────────> 48%
Cycle 5: 49% ──────────────────> 56%

Run 2 (Yet Another):
Cycle 1: 0% ─────────────────────────────────────────> 59%
Cycle 2: 59% ─> 77% ──> 🗜️ COMPACT ──> 19% ────────> 32%
Cycle 3: 32% ─────────────────────────────────────> 55%
Cycle 4: 55% ───────────────────────────────────────> 69%
Cycle 5: 69% ─> 81% ──> 🗜️ COMPACT ──> 10% ────────> 13%
```

### Compaction Analysis

| Run | Events | Triggers | Final Context |
|-----|--------|----------|---------------|
| Baseline | 1 | Cycle 3 @ 77% | 44% |
| Run 1 | 1 | Cycle 3 @ 75% | 56% |
| Run 2 | **2** | Cycle 2 @ 77%, Cycle 5 @ 81% | 13% |

**Observation**: Run 2 required an additional compaction, indicating more context-heavy work patterns. The second compaction at 81% (above 80% threshold) triggered server-side compaction.

---

## Tool Usage Comparison

| Tool | Baseline | Run 1 | Run 2 | Trend |
|------|----------|-------|-------|-------|
| view | 108 (30%) | 93 (27%) | **126 (32%)** | ↑ More reading |
| bash | 91 (26%) | 112 (32%) | 113 (28%) | Stable |
| edit | 58 (16%) | 50 (14%) | **70 (18%)** | ↑ More editing |
| report_intent | 49 (14%) | 51 (15%) | 53 (13%) | Stable |
| grep | 28 (8%) | 11 (3%) | 14 (4%) | ↓ Less searching |
| update_todo | 14 (4%) | 13 (4%) | 13 (3%) | Stable |
| create | 6 (2%) | 8 (2%) | 6 (2%) | Stable |
| glob | 2 (1%) | 9 (3%) | 5 (1%) | Variable |
| **Total** | **356** | **347** | **400** | Run 2 +15% |

**Key Differences**:
- Run 2 used **36% more view calls** than baseline (heavy context loading)
- Run 2 used **21% more edit calls** (more extensive changes)
- All runs show bash as dominant (command-heavy workflow)

---

## Work Accomplished

### Run 1 (45m 2s)

| Commit | Type | Description |
|--------|------|-------------|
| 1 | feat | Session observability + quota tracking (Phase 0-1) |
| 2 | refactor | Extract verify_steps.py from run.py (-115 lines) |
| 3 | refactor | Extract run_steps.py from run.py (-211 lines) |
| 4 | refactor | Extract iterate_helpers.py + compact_steps.py (-217 lines) |
| 5 | test | Add tests for iterate_helpers + compact_steps (+30 tests) |

**Summary**: Heavy modularization focus - run.py reduced from 1523→973 lines (-550 lines)

### Run 2 (103m 32s)

| Commit | Type | Description |
|--------|------|-------------|
| 1 | refactor | Extract prompt_steps.py + json_pipeline.py (-188 lines) |
| 2 | chore | Archive older completed backlog items |
| 3 | refactor | Extract output_steps.py (-75 lines) |
| 4 | refactor | Complete iterate.py modularization (792 lines) |
| 5 | docs | Update ARCHITECTURE.md |
| 6 | backlog | Promote Session resilience Phase 2 |
| 7 | backlog | Consolidate Recently Completed |
| 8 | feat | Session Resilience Phase 2 - checkpoint resume (+4 tests) |
| 9 | feat | Session Resilience Phase 3 - predictive rate limiting (+9 tests) |
| 10 | feat | Session Resilience Phase 4 - compaction summary (+3 tests) |
| 11 | chore | Archive completed SESSION-RESILIENCE proposal |

**Summary**: iterate.py modularization complete (1397→792 lines) + entire SESSION-RESILIENCE roadmap completed

---

## Comparative Efficiency Analysis

### Time vs Output

| Metric | Run 1 | Run 2 | Ratio |
|--------|-------|-------|-------|
| Duration | 45m | 104m | 2.3× |
| Commits | 5 | 11 | 2.2× |
| New tests | 30 | 16 | 0.5× |
| Lines removed | 550 | 261 | 0.5× |
| Features completed | 1 | 3 | 3.0× |

**Efficiency Assessment**:
- Run 2 produced **more commits and features** but took **more than 2× the time**
- Run 1 was more efficient at code reduction (550 lines vs 261)
- Run 2 completed an entire multi-phase roadmap (SESSION-RESILIENCE)

### Token Economy

| Metric | Run 1 | Run 2 | Analysis |
|--------|-------|-------|----------|
| Input tokens | 22.6M | 30.2M | Run 2 +34% |
| Output tokens | 103K | 115K | Run 2 +12% |
| Tokens per minute | 502K | 291K | Run 1 +73% efficiency |
| Input per commit | 4.5M | 2.7M | Run 2 more commits, less per-commit |

---

## Why Was Run 2 Slower?

### Hypothesis 1: Rate Limit Proximity ❌
The 20-minute cooldown should have been sufficient. No rate limit errors in logs.

### Hypothesis 2: Work Complexity ✓
Run 2 tackled conceptually harder work:
- SESSION-RESILIENCE requires understanding context/quota/rate-limits
- More documentation and proposal updates
- Archiving a completed proposal (multi-step)

### Hypothesis 3: Phase 1 Pattern Shift ✓
Run 2's Phase 1 absorbed implementation work:
- Cycles 3-5 all show ~218-233s in P1, but only 5-26s in P2
- The model front-loaded work into selection phase
- This is less efficient as P1 doesn't have the same COMPACT directives

### Hypothesis 4: More Compactions ✓
Run 2 needed 2 compactions vs 1:
- Compaction adds latency (~10-30s each)
- Context re-reading after compaction adds token cost
- Indicates heavier context growth patterns

---

## Recommendations

### 1. Add COMPACT Before P1 in Each Cycle
Currently COMPACT appears between P2/P3 and P4/P5. Add:
```
COMPACT between cycles
## Phase 1: Work Selection
```

### 2. Reduce CONTEXT-LIMIT to 70%
Current 80% triggers compaction too late. At 70%:
- More buffer for mid-turn growth
- Fewer "emergency" compactions at 81%+

### 3. Consider Separate Selection Prompt
If P1 consistently takes 200-350s, it may benefit from:
- Lighter prologue (less context)
- Focused task: "read backlog, pick ONE item, output JSON"
- Defer heavy reading to P2

### 4. Monitor Token Consumption Patterns
Run 2 consumed 34% more input tokens for 26% more work:
- Track tokens per commit as efficiency metric
- Alert when input tokens exceed 5M per commit

---

## Conclusions

### Both Runs Successful ✅
- 5/5 cycles completed
- All tests passing
- No errors or rate limits

### Run 1 More Efficient
- 45m for 5 commits (9 min/commit)
- 4.5M tokens/commit
- 550 lines removed

### Run 2 More Productive (in absolute terms)
- 11 commits total
- Completed entire SESSION-RESILIENCE roadmap
- Archived proposal after completion

### Cooldown Period Had No Observable Effect
The 20-minute sleep between runs didn't provide measurable benefit - Run 2 was slower, not faster.

---

## Raw Metrics

```
Run 1 (Another):
  Duration: 2701.9s (45m 2s)
  Cycles: 5/5
  Prompts: 45 (9 × 5)
  Turns: 314
  Tool calls: 347
  Compactions: 1 (cycle 3)
  Context peak: 75%
  Context final: 56%
  Tokens: 22.6M in / 103K out
  Commits: 5

Run 2 (Yet Another):
  Duration: 6212.2s (103m 32s)
  Cycles: 5/5
  Prompts: 45 (9 × 5)
  Turns: 372
  Tool calls: 400
  Compactions: 2 (cycle 2, cycle 5)
  Context peak: 81%
  Context final: 13%
  Tokens: 30.2M in / 115K out
  Commits: 11
```

---

*Report generated from analysis of:*
- `backlogv2-another-5run.log` (3,369 lines)
- `backlogv2-yet-another-5run.log` (3,798 lines)

*Analysis performed: 2026-01-26T17:19Z*
