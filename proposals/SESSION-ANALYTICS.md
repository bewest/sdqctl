# Session Analytics: Historical Insights & Reporting

> **Status**: Draft  
> **Created**: 2026-02-05  
> **Author**: sdqctl development  
> **Priority**: P2 (Medium Value)  
> **Related**: [SDK-ECONOMY.md](SDK-ECONOMY.md), [SDK-SESSION-PERSISTENCE.md](SDK-SESSION-PERSISTENCE.md)

---

## Problem Statement

Session metrics are collected but underutilized. Users lack visibility into:
- **Aggregate patterns** across all sessions
- **Outlier detection** for unusual runs
- **Trend analysis** over time
- **SDK cost estimation** based on token usage

Current state:
- `sessions list --verbose` shows per-session metrics
- `sessions stats SESSION_ID` shows single session detail
- No aggregate analytics or historical insights

---

## Evidence from Backfill Analysis (2026-02-05)

Analysis of 197 sessions revealed valuable patterns:

| Metric | Value | Insight |
|--------|-------|---------|
| Total turns | 40,774 | Heavy usage |
| Total tool calls | 49,851 | 1.22 tools/turn avg |
| Sessions >1000 turns | 11 | Marathon sessions need attention |
| Sessions >5 tools/turn | 5 | Bulk parallel operations |
| Max session | 2,655 turns | Potential compaction candidate |

**Key Finding**: Token usage is NOT available for historical sessions (streaming-only events). Only turns/tools can be backfilled.

---

## Proposed Commands

### 1. `sessions analytics` - Aggregate Insights

```bash
sdqctl sessions analytics [--format json|table|csv]
```

**Output:**
```
Session Analytics Summary
=========================

Totals:
  Sessions:     197
  Turns:        40,774
  Tool calls:   49,851
  Duration:     127.3h (21 sessions with timing)

Averages:
  Turns/session:    207
  Tools/turn:       1.22
  Duration/session: 6.1h

Distribution:
  Single-turn:      7 (3.6%)
  Short (2-10):     34 (17.3%)
  Medium (11-100):  68 (34.5%)
  Long (101-500):   49 (24.9%)
  Marathon (500+):  39 (19.8%)

Token Efficiency (21 sessions with data):
  Input tokens:     736M
  Output tokens:    3M
  IO ratio:         0.41%
```

### 2. `sessions outliers` - Detect Anomalies

```bash
sdqctl sessions outliers [--metric turns|tools_per_turn|duration] [--threshold 2.0]
```

**Output:**
```
Session Outliers (>2σ from mean)
================================

By Turns (threshold: 927):
  903084c8  2655 turns  2541 tools  0.96 t/turn
  6e9080b8  1663 turns  2021 tools  1.22 t/turn
  7f0e3ae8  1433 turns  1375 tools  0.96 t/turn
  ...

By Tools/Turn (threshold: 5.27):
  7cb3966d  17.00 t/turn  85 tools   5 turns
  5f890a55  12.75 t/turn  51 tools   4 turns
  99a11c9e   6.75 t/turn  108 tools  16 turns
  ...

Recommendations:
  • Consider compaction for sessions >1000 turns
  • High tool ratios indicate bulk file operations (normal)
```

### 3. `sessions trends` - Time-Based Analysis

```bash
sdqctl sessions trends [--period day|week|month] [--since YYYY-MM-DD]
```

**Output:**
```
Session Trends (last 30 days)
=============================

        Sessions  Turns   Tools   Avg Duration
Week 1      23     4,521   5,201      5.2h
Week 2      31     6,892   8,104      4.8h
Week 3      28     5,103   5,892      6.1h
Week 4      35     7,234   8,455      5.5h

Growth: +52% sessions, +60% turns over period
```

### 4. `sessions export` - Data Export

```bash
sdqctl sessions export [--format csv|json|parquet] [--output FILE]
```

Export all metrics for external analysis (Jupyter, Grafana, etc.)

---

## Implementation Plan

### Phase 1: Core Analytics (P2, Low Effort)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 1 | Add `sessions analytics` command | Low | 🔲 |
| 2 | Add `sessions outliers` command | Low | 🔲 |
| 3 | Add `--format` flag (json/table/csv) | Low | 🔲 |
| 4 | Add tests for analytics commands | Low | 🔲 |

### Phase 2: Trends & Export (P3, Medium Effort)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 5 | Add `sessions trends` command | Medium | 🔲 |
| 6 | Add `sessions export` command | Medium | 🔲 |
| 7 | Parse session start times from SDK | Low | 🔲 |
| 8 | Document analytics in COMMANDS.md | Low | 🔲 |

### Phase 3: Recommendations Engine (P3, Medium Effort)

| # | Item | Effort | Status |
|---|------|--------|--------|
| 9 | Add compaction recommendations | Medium | 🔲 |
| 10 | Add cost estimation from tokens | Medium | 🔲 |
| 11 | Integrate with `sessions list` summary | Low | 🔲 |

---

## Technical Notes

### Metrics Available

| Metric | Historical | New Sessions | Notes |
|--------|------------|--------------|-------|
| Turns | ✅ Backfillable | ✅ | From `turn_end` events |
| Tool calls | ✅ Backfillable | ✅ | From `tool.execution_complete` |
| Duration | ❌ | ✅ | Only tracked on `destroy_session()` |
| Input tokens | ❌ | ✅ | Streaming-only, not persisted |
| Output tokens | ❌ | ✅ | Streaming-only, not persisted |

### Storage Location

```
~/.sdqctl/sessions/<session_id>/metrics.json
```

### Backfill Script

```bash
# Already exists at /tmp/backfill_metrics.py
python backfill_metrics.py [--dry-run] [--limit N]
```

Fetches turns/tools from SDK session history for sessions missing metrics.

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Analytics visibility | Per-session only | Aggregate view |
| Outlier detection | Manual grep | Automated |
| Export capability | None | CSV/JSON/Parquet |
| Time to insights | ~10 min Python | ~1 sec CLI |

---

## Open Questions

| ID | Question | Impact |
|----|----------|--------|
| OQ-SA-001 | Should `sessions analytics` run automatically at end of long sessions? | UX |
| OQ-SA-002 | Add Prometheus/Grafana export format? | Observability |
| OQ-SA-003 | Integrate with GitHub Actions for CI metrics? | Automation |
| OQ-SA-004 | Store analytics summary in a separate file for quick access? | Performance |

---

## References

- `sdqctl/commands/sessions.py` - Existing sessions command
- `sdqctl/adapters/copilot.py` - Metrics persistence logic
- `/tmp/backfill_metrics.py` - Backfill script for historical data
- [SDK-ECONOMY.md](SDK-ECONOMY.md) - Token efficiency analysis
- [docs/COMMANDS.md](../docs/COMMANDS.md) - CLI documentation
