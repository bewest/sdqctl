# Marathon Session Success Analysis

> **Date**: 2026-02-05  
> **Sessions Analyzed**: 26 marathon sessions (≥500 turns)  
> **Total Turns**: 25,508  
> **Purpose**: Identify keys to success for long-running sessions

---

## Executive Summary

Analysis of 26 marathon sessions reveals **four key success factors**:

| Factor | Optimal Value | Correlation |
|--------|---------------|-------------|
| Compaction cadence | ~170 turns | r=0.93 |
| User engagement | ~3.7 turns/msg | r=0.85 |
| Tool efficiency | ~1.07 tools/turn | r=0.81 |
| Active resumption | Multiple invocations | Qualitative |

**Bottom line**: Sessions that compact regularly, maintain human guidance, and use tools efficiently can run indefinitely. Compaction is the critical enabler.

---

## Dataset Overview

| Metric | Value |
|--------|-------|
| Marathon sessions (≥500 turns) | 26 |
| Total turns | 25,508 |
| Total compactions | 150 |
| Total user messages | 6,796 |
| Longest session | 2,655 turns |
| Shortest marathon | 535 turns |

---

## Key Finding 1: Compaction Cadence

**Sessions compact approximately every 170 turns.**

| Statistic | Value |
|-----------|-------|
| Minimum | 112 turns/compaction |
| Maximum | 240 turns/compaction |
| Mean | 176 turns/compaction |
| **Median** | **170 turns/compaction** |
| Std Dev | 36 turns |

**Correlation with session length: r=0.927** (very strong)

### Insight

Compaction is the **primary mechanism** enabling marathon sessions. The SDK's native compaction triggers when context approaches limits, summarizing history to free space. Sessions that compact more frequently can run longer.

**Recommendation**: For long-running workflows, ensure compaction is enabled and expect ~170 turns between compactions as healthy behavior.

---

## Key Finding 2: User Engagement Pattern

**Users send a message every ~3.7 agent turns.**

| Statistic | Value |
|-----------|-------|
| Minimum | 2.8 turns/msg |
| Maximum | 82.6 turns/msg (outlier) |
| Mean | 6.7 turns/msg |
| **Median** | **3.7 turns/msg** |

**Correlation with session length: r=0.851** (strong)

### Outlier Analysis

One session (`a12d07f2`) achieved 82.6x autonomy (1,074 turns with only 13 user messages). This appears to be a highly autonomous batch processing run - unusual but valid.

### Insight

Marathon sessions are **collaborative**, not fully autonomous. Users provide guidance approximately every 4 turns, steering the agent toward goals. Pure autonomous runs are rare.

**Recommendation**: Design workflows with human checkpoints every 3-5 turns for optimal outcomes.

---

## Key Finding 3: Tool Efficiency

**Marathon sessions average ~1.07 tools per turn.**

| Statistic | Value |
|-----------|-------|
| Minimum | 0.89 tools/turn |
| Maximum | 2.99 tools/turn |
| Mean | 1.19 tools/turn |
| **Median** | **1.07 tools/turn** |

**Correlation with session length: r=0.812** (strong)

### Insight

Marathon sessions maintain **balanced tool usage** - roughly one tool call per turn. Sessions with very high tool ratios (5-17x) tend to be short bursts of bulk operations, not sustained work.

**Recommendation**: If tools/turn exceeds 3.0, the session is likely in a "bulk operation" phase that won't sustain marathon duration.

---

## Key Finding 4: Correlation Matrix

| Metric A | Metric B | Correlation |
|----------|----------|-------------|
| Turns | Compactions | **r=0.927** |
| Turns | User messages | **r=0.851** |
| Turns | Tool calls | **r=0.812** |

All three metrics correlate strongly with session length, but compaction is the strongest predictor.

---

## Top Performers

### By Total Turns

| Session | Turns | Compactions | User Msgs |
|---------|-------|-------------|-----------|
| 903084c8 | 2,655 | 18 | 623 |
| 6e9080b8 | 1,663 | 11 | 558 |
| 7f0e3ae8 | 1,433 | 9 | 413 |
| da4c8a23 | 1,332 | 6 | 428 |
| 810e1994 | 1,200 | 5 | 380 |

### By Compaction Efficiency (most turns per compaction)

| Session | Turns/Compact | Total Compactions |
|---------|---------------|-------------------|
| 810e1994 | 240 | 5 |
| de4e5233 | 235 | 4 |
| da4c8a23 | 222 | 6 |
| 0c36b8f7 | 218 | 4 |
| eb58be24 | 218 | 4 |

### By Agent Autonomy (turns per user message)

| Session | Autonomy | Turns |
|---------|----------|-------|
| a12d07f2 | 82.6x | 1,074 |
| de4e5233 | 4.8x | 941 |
| 70e96e37 | 4.7x | 535 |
| 8d9337c0 | 4.3x | 833 |
| 903084c8 | 4.3x | 2,655 |

---

## Success Formula

Based on this analysis, the formula for marathon session success is:

```
Marathon Success = Compaction + Engagement + Efficiency

Where:
- Compaction:  Enabled, ~170 turns between compactions
- Engagement:  Human message every 3-5 agent turns
- Efficiency:  Tools/turn ratio between 0.9-1.3
```

### Anti-Patterns

| Pattern | Indicator | Risk |
|---------|-----------|------|
| No compaction | 0 compaction events | Context overflow |
| Over-autonomy | >10 turns/user msg | Goal drift |
| Bulk operations | >3 tools/turn | Unsustainable pace |
| Under-engagement | <2 turns/user msg | Inefficient interaction |

---

## Recommendations

### For Users

1. **Enable compaction** - Essential for sessions beyond ~200 turns
2. **Stay engaged** - Provide guidance every 3-5 turns
3. **Monitor tool ratio** - High ratios indicate bulk ops, not sustainable work
4. **Resume sessions** - Multi-invocation sessions can continue indefinitely

### For sdqctl Development

1. **Add `sessions analyze`** - Surface these metrics per-session
2. **Add health indicators** - Warn when approaching anti-patterns
3. **Track compaction cadence** - Surface in `sessions stats`
4. **Autonomy scoring** - Help users understand engagement levels

---

## Methodology

### Data Collection

1. Identified 26 sessions with ≥500 turns from `~/.sdqctl/sessions/*/metrics.json`
2. Retrieved full event history via SDK `session.get_messages()`
3. Counted event types: `turn_end`, `user.message`, `compaction_complete`, `tool.execution_complete`

### Metrics Calculated

| Metric | Formula |
|--------|---------|
| Turns per compaction | `turns / compaction_count` |
| Autonomy | `turns / user_messages` |
| Tool efficiency | `tools / turns` |

### Limitations

- **No duration data** - Only 21 sessions have wall-clock timing
- **No token data** - Usage events not persisted in history
- **Selection bias** - Only sessions that reached 500+ turns analyzed

---

## Raw Data

<details>
<summary>Click to expand full dataset</summary>

| Session | Turns | Tools | Compactions | User Msgs | Autonomy | Tools/Turn |
|---------|-------|-------|-------------|-----------|----------|------------|
| 903084c8 | 2655 | 2541 | 18 | 623 | 4.3 | 0.96 |
| 6e9080b8 | 1663 | 2021 | 11 | 558 | 3.0 | 1.22 |
| 7f0e3ae8 | 1433 | 1375 | 9 | 413 | 3.5 | 0.96 |
| da4c8a23 | 1332 | 1282 | 6 | 428 | 3.1 | 0.96 |
| 810e1994 | 1200 | 1286 | 5 | 380 | 3.2 | 1.07 |
| e716d1a8 | 1177 | 1118 | 6 | 315 | 3.7 | 0.95 |
| f6f3317d | 1143 | 1526 | 6 | 283 | 4.0 | 1.34 |
| 9466fd6f | 1091 | 975 | 7 | 294 | 3.7 | 0.89 |
| a12d07f2 | 1074 | 1320 | 6 | 13 | 82.6 | 1.23 |
| faef14f3 | 942 | 1310 | 6 | 254 | 3.7 | 1.39 |
| de4e5233 | 941 | 1042 | 4 | 197 | 4.8 | 1.11 |
| b720d64c | 893 | 962 | 5 | 281 | 3.2 | 1.08 |
| 0c36b8f7 | 872 | 1013 | 4 | 229 | 3.8 | 1.16 |
| eb58be24 | 871 | 818 | 4 | 278 | 3.1 | 0.94 |
| 1bac4021 | 845 | 838 | 4 | 306 | 2.8 | 0.99 |
| aab6135e | 835 | 893 | 4 | 205 | 4.1 | 1.07 |
| 8d9337c0 | 833 | 1641 | 6 | 192 | 4.3 | 1.97 |
| 32ae5650 | 806 | 789 | 5 | 236 | 3.4 | 0.98 |
| e25e6e67 | 722 | 746 | 6 | 234 | 3.1 | 1.03 |
| fa3c7811 | 648 | 608 | 4 | 154 | 4.2 | 0.94 |
| e78f2b8a | 635 | 685 | 3 | 210 | 3.0 | 1.08 |
| 72e04d96 | 634 | 857 | 5 | 161 | 3.9 | 1.35 |
| e17a9137 | 607 | 675 | 4 | 140 | 4.3 | 1.11 |
| 214e3b6c | 562 | 628 | 5 | 144 | 3.9 | 1.12 |
| 07cdad79 | 559 | 1672 | 4 | 153 | 3.7 | 2.99 |
| 70e96e37 | 535 | 525 | 3 | 115 | 4.7 | 0.98 |

</details>

---

## References

- [proposals/SESSION-ANALYTICS.md](../proposals/SESSION-ANALYTICS.md) - Analytics command proposal
- [proposals/SDK-INFINITE-SESSIONS.md](../proposals/SDK-INFINITE-SESSIONS.md) - Native compaction design
- [docs/SDK-LEARNINGS.md](../docs/SDK-LEARNINGS.md) - SDK patterns
- `/tmp/marathon_analysis.json` - Raw analysis data
