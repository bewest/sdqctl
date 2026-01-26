# Run Prediction Document

> **Created**: 2026-01-26T17:26Z  
> **Purpose**: Document predictions before running to enable post-hoc analysis  
> **Workflow**: `examples/workflows/backlog-processor-v2.conv`

---

## Baseline Data (3 Prior Runs)

| Run | Date | Duration | Commits | Compactions | Tokens In |
|-----|------|----------|---------|-------------|-----------|
| Baseline | 2026-01-26 AM | 35m 36s | 6 | 1 | 23.1M |
| Run 1 | 2026-01-26 AM | 45m 2s | 5 | 1 | 22.6M |
| Run 2 | 2026-01-26 AM | 103m 32s | 11 | 2 | 30.2M |

**Averages**: 61m duration, 7.3 commits, 1.3 compactions, 25.3M tokens

---

## Current State

### Large Files (>500 lines)

| File | Lines | Status |
|------|-------|--------|
| `adapters/copilot.py` | 1,143 | 🔴 Next modularization target (in P2 queue) |
| `commands/run.py` | 973 | ✅ Under 1000 |
| `commands/iterate.py` | 791 | ✅ Under 800 |
| `commands/help.py` | 698 | ⚠️ Consider split |
| `commands/artifact.py` | 689 | ⚠️ Consider split |
| `verifiers/traceability.py` | 685 | ⚠️ Consider split |

### P2 Ready Queue

1. Add integration tests (ongoing)
2. **Copilot adapter modularization** (1143 → split into events.py, stats.py, session.py)
3. Performance benchmark suite (blocked by OQ-005)

---

## Predictions

### Timing

| Scenario | Duration | Probability | Trigger |
|----------|----------|-------------|---------|
| Fast | 35-45m | 25% | Picks easy integration tests |
| **Medium** | **55-75m** | **50%** | Picks copilot.py modularization |
| Slow | 85-110m | 25% | Complex feature or rate limit |

**Point estimate**: 65 minutes (±15m)

### Outcomes

| Metric | Predicted Range | Most Likely |
|--------|-----------------|-------------|
| Cycles completed | 5/5 | 5/5 ✅ |
| Compactions | 1-2 | 1 |
| Tool calls | 340-420 | 370 |
| Commits | 4-9 | 6 |
| Tests added | 10-40 | 20 |
| Context peak | 70-85% | 77% |
| Final context | 40-60% | 50% |
| Tokens in | 20-30M | 24M |

### Work Accomplished (Predicted)

Most likely items to be completed:
1. **Copilot adapter modularization** (P2, highest priority non-blocked)
2. Integration tests (ongoing, incremental)

Less likely:
- Performance benchmark (blocked)
- Verbosity defaults (blocked, P3)

---

## Experimental Adjustment: Modularity Prologue

### Hypothesis

Adding a modularity directive via CLI prologue will:
1. Prioritize `copilot.py` modularization in cycle 1
2. Encourage proactive splitting when files grow
3. Reduce time spent on integration tests (lower priority)

### CLI Command with Modularity Prologue

```bash
time sdqctl -vvv iterate examples/workflows/backlog-processor-v2.conv \
  --adapter copilot -n 5 \
  --prologue "
---
**CODE MODULARITY PRIORITY**:
- Files >500 lines should be split when touched
- copilot.py (1143 lines) is the priority modularization target
- Extract logical units: event handling, stats tracking, session management
- Target: no file >800 lines after this session
---
" 2>&1 | tee ../backlogv2-modularity-run.log
```

### Expected Impact

| Metric | Without Prologue | With Modularity Prologue |
|--------|------------------|--------------------------|
| copilot.py tackled | 60% chance | 85% chance |
| Lines reduced | 0-300 | 300-500 |
| New modules created | 0-2 | 2-4 |
| Duration impact | baseline | +5-10m (more careful work) |

---

## Validation Criteria

After the run, compare actual vs predicted:

### Success Criteria (Prediction Validated)

- [ ] Duration within 55-75m range
- [ ] 5/5 cycles completed
- [ ] 1-2 compactions
- [ ] copilot.py modularization started or completed
- [ ] 4-9 commits made

### Rejection Criteria (Prediction Failed)

- Duration <40m or >100m
- Fewer than 4/5 cycles completed
- 3+ compactions (context management issue)
- copilot.py not touched at all
- <3 or >12 commits

---

## Post-Run Analysis Template

```markdown
## Actual Results

| Metric | Predicted | Actual | Accuracy |
|--------|-----------|--------|----------|
| Duration | 65m | ___ | ___% |
| Cycles | 5/5 | ___ | ___ |
| Compactions | 1 | ___ | ___ |
| Commits | 6 | ___ | ___ |
| copilot.py lines | reduce to ~800 | ___ | ___ |

## Observations

- Prologue impact: ___
- Unexpected behaviors: ___
- Model decision patterns: ___

## Lessons Learned

1. ___
2. ___
```

---

*Document created for experimental validation of workflow predictions.*
