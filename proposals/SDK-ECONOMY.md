# SDK Economy: Iteration Efficiency Improvements

> **Status**: Draft  
> **Created**: 2026-01-26  
> **Author**: sdqctl development  
> **Priority**: P1 (High Value)

---

## Problem Statement

Analysis of recent `sdqctl iterate` runs reveals a core efficiency problem:

| Metric | Observed | Desired |
|--------|----------|---------|
| Items completed per iteration | 1-2 | 3-5 |
| SDK rate limit exhaustion | Frequent | Rare |
| Context utilization at stop | 20-58% | 60-80% |

**Root Cause**: Single iterations often complete only ONE P0 task, then stop or move to trivial work (lint fixes, minor docs), exhausting SDK rate limits on minimal progress.

### Two Opposing Tensions

1. **Repo organization for taskability**: Agents need to evaluate and select work efficiently
2. **Back-pressure for humans**: Design decisions and blockers must escalate appropriately

**Current Gap**: The repo organization and workflow prompts don't reliably surface a **batch of related, substantial work** that an iteration can complete with good SDK economy.

---

## Evidence from Experience Reports

### v2-workflow-analysis-2026-01-26

| Cycle | Work Completed | Type |
|-------|---------------|------|
| 1 | conversation.py split (P0) | Major refactor |
| 2 | ARCHITECTURE.md (P1) | Documentation |
| 3-10 | E501 lint fixes | Trivial |

**Observation**: After P0/P1 completed in cycles 1-2, remaining 8 cycles spent on lint fixes—poor SDK economy.

### iterate-run-analysis-2026-01-26

| Cycle | Work Completed | Duration |
|-------|---------------|----------|
| 1 | Mixed Prompt/File CLI | 541s |
| 2 | ExecutionContext | 327s |
| 3 | I/O Utilities | 276s |
| 4 | VerifierBase scan_files | 442s |
| 5 | Error Handling Decorators | 240s |

**Observation**: Each cycle completed ONE item. With 3-5 items per cycle, same work in 2 cycles instead of 5.

---

## Proposed Improvements

### 1. Repo Organization: Work Packages

**Concept**: Group related backlog items into "work packages" that can complete together.

```markdown
## Work Package: Modularization (P2)
Related items that share context and can complete in one iteration:
- [ ] Extract run_async() to utils
- [ ] Extract output formatting helpers
- [ ] Add tests for extracted utilities

Estimated: 1 iteration, 3 items, ~150 lines changed
```

**Benefits**:
- Agent sees related items together
- Shared context reduces re-reading files
- Clear scope for one iteration

### 2. Prompt Improvements: Batch Selection

Update Phase 1 (Selection) prompts to encourage batching:

**Current**:
```
Select the SINGLE highest-priority actionable item.
```

**Proposed**:
```
Select 2-4 RELATED items that can complete together in this iteration.
Prefer items that:
- Share the same files or modules
- Have similar complexity (all Low or all Medium)
- Can be verified together

If only 1 high-priority item exists, that's acceptable.
```

### 3. Cross-Domain Evaluation

Update Phase 1 to explicitly evaluate ALL backlogs:

```
**Cross-Domain Scan (Required):**
Before selecting, scan these sources for candidates:
1. proposals/BACKLOG.md - Ready Queue
2. docs/QUIRKS.md - Active quirks
3. Any --prologue files provided

Select the best batch across ALL sources, not just the first file.
```

### 4. Iteration Budget Guidance

Add explicit budget expectations to help agents pace work:

```
**Iteration Budget (Guidance):**
- Target: 3-5 items OR ~150-250 lines changed
- Maximum: 500 lines changed (split larger work)
- Minimum: If only 1 item available, complete it thoroughly
```

### 5. Protection Policies

Add policies to prevent low-value modifications:

```
**Policies:**
- Do NOT modify .conv files without approved proposal
- Do NOT delete/archive items without approved proposal
- Route design decisions to OPEN-QUESTIONS.md
- Trivial work (lint fixes) should batch 5+ items together
```

---

## Implementation Options

### Option A: Modify backlog-processor-v2.conv

Update existing workflow prompts with new guidance.

**Pros**: Single source of truth, incremental improvement
**Cons**: Risk breaking working workflow, needs careful testing

### Option B: Create backlog-processor-v3.conv

New workflow with economy improvements, run parallel with v2.

**Pros**: A/B testing, preserve working v2, clean optimization
**Cons**: Two files to maintain during transition

### Option C: Repo Reorganization + v2 Updates

Restructure BACKLOG.md with work packages, update v2 prompts.

**Pros**: Addresses root cause (repo organization)
**Cons**: Higher effort, more files changed

**Recommendation**: Option C — Repo reorganization is the root fix; prompt changes alone won't solve the underlying structure problem.

---

## Immediate Changes (No Code Required)

These can be applied now via prompt updates:

| Change | File | Notes |
|--------|------|-------|
| Batch selection guidance | backlog-processor-v2.conv Phase 1 | "Select 2-4 related items" |
| Cross-domain evaluation | backlog-processor-v2.conv Phase 1 | "Scan ALL --prologue files" |
| Protection policies | backlog-processor-v2.conv Phase 2 | Don't modify conv/archives |
| Iteration budget | backlog-processor-v2.conv Prologue | "Target: 3-5 items" |

---

## Deferred Changes (Future Work)

| Change | Effort | Notes |
|--------|--------|-------|
| Work package markers in BACKLOG.md | Low | ✅ **DONE** - Added WP-001, WP-002, WP-003 |
| Domain-partitioned queues | Medium | Separate files per domain? → WP-001 |
| `sdqctl workpackage` command | Medium | CLI for managing packages |
| Iteration metrics tracking | Medium | Items/cycle, lines/cycle → WP-001 |
| backlog-processor-v3.conv | Medium | Full optimization → WP-001 |

---

## Existing Mechanisms (No New Directives)

The following already support economy improvements:

### Multiple `--prologue` Files
```bash
sdqctl iterate workflow.conv \
  --prologue proposals/BACKLOG.md \
  --prologue docs/QUIRKS.md \
  --prologue proposals/SDK-ECONOMY.md \
  --adapter copilot -n 10
```

### ELIDE for Context Efficiency
```dockerfile
PROMPT Analyze the output.
ELIDE
RUN pytest -v
ELIDE
PROMPT Fix failures.
# Single agent turn with embedded output
```

### COMPACT for Long Runs
```dockerfile
# After Phase 6, compact before PM phases
COMPACT
```

---

## Open Questions

| ID | Question | Impact |
|----|----------|--------|
| OQ-SE-001 | Optimal batch size? (2-4 vs 3-5 items) | Prompt wording |
| OQ-SE-002 | Work packages: explicit markers vs agent inference? | Repo structure |
| OQ-SE-003 | How to measure SDK economy? (items/token, items/minute) | Metrics |
| OQ-SE-004 | Domain queues: replace BACKLOG.md or supplement? | File organization |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Items per iteration | 1-2 | 3-5 |
| Context utilization at stop | 20-58% | 60-80% |
| Cycles before rate limit | ~5 | ~10 |
| Trivial work batching | 1 item | 5+ items |

---

## References

- `reports/v2-workflow-analysis-2026-01-26.md` - 10-cycle run metrics
- `reports/iterate-run-analysis-2026-01-26.md` - 5.5-cycle run analysis
- `docs/PHILOSOPHY.md` - Workflow design principles
- `docs/GLOSSARY.md` - Scope partitioning terminology
- `examples/workflows/backlog-processor-v2.conv` - Current workflow
