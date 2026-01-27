# Long Backlog Session Experience Report

> **Date**: 2026-01-24  
> **Duration**: 78m 40s (real), 5m 0.5s (user), 0m 20s (sys)  
> **Cycles**: 10  
> **Final Context**: 46% (59,946/128,000 tokens)
> **Goal**: Enable long-lived unattended automation sessions

---

## Executive Summary

Successfully ran the **longest automated session to date**: 78 minutes processing 10 backlog cycles with 14 commits. The session demonstrated that context management via COMPACT directives enables sustained operation well beyond typical interactive limits.

**Key Finding**: Multi-prologue injection creates a **first-prologue bias** where the model disproportionately selects items from the first document (BACKLOG.md) even when higher-value items exist in subsequent prologues (REFCAT-DESIGN.md, ARTIFACT-TAXONOMY.md).

**Root Cause**: Missing explicit instruction to "Review all the following roadmaps to select a high value taskable area" in the workflow's PROLOGUE section.

**Impact on Long-Lived Sessions**: This bias undermines cross-document prioritization, which is critical for unattended operation where humans cannot redirect focus.

---

## Execution Details

### Command
```bash
time sdqctl -vvv cycle --session-mode=fresh \
  examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md \
  --prologue proposals/ARTIFACT-TAXONOMY.md \
  --adapter copilot -n 10
```

### Timing Analysis

| Phase | Duration | Notes |
|-------|----------|-------|
| Cycle 1 | ~10m 30s | HELP directive + traceability patterns (2 items) |
| Cycle 2 | ~2m 40s | Artifact summary docs |
| Cycle 3 | ~8m | Artifact templates + `artifact next` command |
| Cycle 4 | ~3m 15s | `artifact rename` command |
| Cycle 5 | ~4m | `verify links` + `verify traceability` CLI |
| Cycle 6 | ~9m | Terminology verifier + ecosystem conventions |
| Cycle 7 | ~6m | `artifact retire` command |
| Cycle 8 | ~13m 30s | Assertions verifier + README update + Q-011 fix |
| Cycle 9 | ~9m 30s | BUG-001 resolution + ELIDE/RUN-RETRY validation |
| Cycle 10 | ~5m 15s | Q-012 COMPACT threshold fix |
| **Total** | **78m 40s** | 10 cycles, 14 commits |

### Context Window Progression

| Cycle | Start Context | End Context | Compaction |
|-------|---------------|-------------|------------|
| 1 | 0% | 2% | ✓ |
| 2 | 2% | 4% | ✓ |
| 3 | 4% | 6% | ✓ |
| 4 | 6% | 7% | ✓ |
| 5 | 8% | 9% | ✓ |
| 6 | 10% | 11% | ✓ |
| 7 | 12% | 13% | ✓ |
| 8 | 14% | 15% | ✓ |
| 9 | 16% | 17% | ✓ |
| 10 | 18% | 19% (46% at compaction) | ✓ |

**Observation**: Context grew linearly ~2% per cycle despite COMPACT. Final compaction brought 46% down for next cycle readiness.

---

## Multi-Prologue Bias Analysis

### The Problem

When multiple `--prologue` files are injected, the model exhibited strong bias toward the first file:

| Prologue | Mentions in Log | Items Selected From |
|----------|-----------------|---------------------|
| BACKLOG.md | 288 | ~12 (80%) |
| ARTIFACT-TAXONOMY.md | 97 | ~2 (13%) |
| REFCAT-DESIGN.md | 35 | ~1 (7%) |

### Evidence from Work Item Sources

| Cycle | Work Item | Source |
|-------|-----------|--------|
| 1 | HELP Directive Implementation | BACKLOG.md §P1 |
| 1 | Extend traceability verifier patterns | BACKLOG.md Session 2026-01-24 |
| 2 | Add artifact summary to TRACEABILITY-WORKFLOW | BACKLOG.md line 728 |
| 3 | Create artifact templates | BACKLOG.md (refs ARTIFACT-TAXONOMY) |
| 3 | `sdqctl artifact next` command | BACKLOG.md |
| 4 | `artifact rename` command | ARTIFACT-TAXONOMY.md §CLI |
| 5 | `verify links` + `traceability` CLI | BACKLOG.md |
| 6 | Terminology verifier | BACKLOG.md Phase 1 |
| 6 | Nightscout ecosystem conventions | BACKLOG.md |
| 7 | `artifact retire` command | ARTIFACT-TAXONOMY.md line 523 |
| 8 | Assertions verifier | BACKLOG.md Phase 1 |
| 9 | BUG-001 empty context | ARTIFACT-TAXONOMY.md (via BACKLOG ref) |
| 9 | ELIDE + RUN-RETRY validation | BACKLOG.md |
| 10 | Q-012 COMPACT threshold | BACKLOG.md |

### Why This Happened

The `backlog-processor.conv` workflow says:

```
PROLOGUE 1. Select ONE item from the injected backlog(s)
```

This instruction doesn't emphasize cross-document review. The model:
1. Reads prologue content in order (BACKLOG.md first)
2. Finds actionable items in BACKLOG.md immediately
3. Selects without scanning subsequent prologues for higher-value items

### Impact on Long-Lived Unattended Sessions

For unattended operation, this bias is problematic because:
- **Suboptimal ordering**: P2 items from BACKLOG.md may be selected over P0 items in ARTIFACT-TAXONOMY.md
- **Document neglect**: Entire roadmaps (REFCAT-DESIGN.md) may go unaddressed
- **Human expectation mismatch**: User expects equal consideration of all prologues

---

## Items Completed

### Summary by Source

| Source | Items Completed | LOC Added | Tests Added |
|--------|-----------------|-----------|-------------|
| BACKLOG.md | 10 | ~2,500 | ~60 |
| ARTIFACT-TAXONOMY.md | 3 | ~600 | ~20 |
| REFCAT-DESIGN.md | 1 | ~100 | ~5 |
| **Total** | **14** | **~3,200** | **~85** |

### Commits Produced

```
f927095 feat: Add HELP directive for injecting help topics
32bbcb2 feat: Extend traceability verifier with STPA and development artifacts
f1de98d docs: add artifact types quick reference to TRACEABILITY-WORKFLOW.md
50b5412 Add artifact templates for traceability documentation
c05cbf2 Add sdqctl artifact command for ID management
c36bb1a feat(artifact): add rename command for artifact ID refactoring
21c0b91 feat(verify): add links and traceability CLI subcommands
835ff49 feat(verifiers): Add terminology verifier
128fd86 docs: Add Nightscout ecosystem conventions
9bbb353 feat(artifact): add retire command for artifact lifecycle management
1fc0437 feat: add assertions verifier for code assertion tracing
e616a81 docs: update README and help with new verifiers
29f1cad fix(Q-011): wire --min-compaction-density into compaction logic
247f62a BUG-001: Resolve empty context compaction issue
dd7e6db ELIDE + RUN-RETRY validation: Reject incompatible constructs
d2e58df fix(Q-012): COMPACT directive now conditional on threshold
f2bd559 docs: update BACKLOG.md to reflect Q-012 fix
```

---

## Lessons Learned

### Lesson #31: Multi-prologue requires explicit cross-document instruction

**Problem**: Model defaults to first-document bias without explicit instruction.

**Fix**: Add to first PROLOGUE in workflow:
```
PROLOGUE Review ALL the following roadmaps to select a high-value taskable area.
PROLOGUE Prioritize by: P0 > P1 > P2 across ALL documents, not just the first.
```

### Lesson #32: Context grows ~2% per cycle with aggressive COMPACT

Even with COMPACT after each phase, context grew from 0% to 46% over 10 cycles. This means:
- **~20 cycles** before hitting 60% CONTEXT-LIMIT
- **~30 cycles** before potential context exhaustion
- For longer sessions, consider more aggressive compaction or periodic "hard reset" via `--session-mode=fresh` mid-run.

### Lesson #33: 78 minutes is sustainable with 4-phase structure

The 4-phase pattern (select → execute → verify → commit) with COMPACTs between phases enables ~80-minute unattended runs. Key factors:
- `MAX-CYCLES 1` per workflow cycle (10 workflow cycles = 10 work items)
- `COMPACT` after phases 2, 3, 4
- `ELIDE` to merge verification output with next prompt

### Lesson #34: Per-cycle commit discipline enables recovery

Each cycle committed its changes, producing 14 atomic commits. If the session had failed at cycle 8, cycles 1-7 work would have been preserved. This is critical for unattended operation.

### Lesson #35: Duplicate tool calls indicate context pressure

Log shows duplicate entries (6x the same edit/bash call) toward the end. This suggests:
- Context nearing limits causes model uncertainty
- Multiple tool calls indicate hedging behavior
- May want to trigger COMPACT proactively when duplicates detected

---

## Recommendations

### 1. Update `backlog-processor.conv` with Cross-Document Instruction

```diff
 PROLOGUE You are an implementation assistant processing a backlog of work items.
 PROLOGUE Your job is to:
-PROLOGUE 1. Select ONE item from the injected backlog(s)
+PROLOGUE 1. Review ALL injected documents and select ONE highest-value item
+PROLOGUE    - Scan each --prologue file for P0/P1 items before deciding
+PROLOGUE    - Do not default to the first document
 PROLOGUE 2. Implement the change directly (EDIT FILES, don't just describe)
```

### 2. Add Document Source Tracking to Phase 1 Output

Modify Phase 1 prompt to require:
```
**Source Document**: [BACKLOG.md | REFCAT-DESIGN.md | ARTIFACT-TAXONOMY.md]
**Reason for Selection**: [Why this over items in other documents]
```

This makes bias visible and forces cross-document consideration.

### 3. Consider `--priority-file` Flag (Future)

New CLI option that specifies priority weighting:
```bash
sdqctl cycle workflow.conv \
  --prologue BACKLOG.md --priority 1.0 \
  --prologue REFCAT-DESIGN.md --priority 2.0 \  # Boost REFCAT items
  --prologue ARTIFACT-TAXONOMY.md --priority 1.5
```

### 4. Add Duplicate Detection for Early Compaction

When the adapter detects 3+ identical tool calls in sequence, trigger preemptive compaction:
```python
if self._detect_duplicate_calls(recent_calls, threshold=3):
    self._trigger_emergency_compact()
```

### 5. For Future Long Sessions: Increase `-n` Incrementally

| Session Type | Recommended `-n` | Expected Duration |
|--------------|------------------|-------------------|
| Quick check | 3 | ~25 min |
| Normal work | 5 | ~40 min |
| Extended | 10 | ~80 min |
| Maximum tested | 10 | 78 min ✓ |
| Experimental | 15 | ~120 min (untested) |

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Total duration | 78m 40s |
| Cycles completed | 10/10 |
| Commits produced | 14 |
| Lines added | ~3,200 |
| Tests added | ~85 |
| Context at end | 46% |
| Prologue bias ratio | 80:13:7 (BACKLOG:ARTIFACT:REFCAT) |
| Throughput | ~41 LOC/minute |
| Items/hour | ~10.7 |

---

## Next Steps

1. **Apply Lesson #31**: Update `backlog-processor.conv` with cross-document instruction
2. **Test improvement**: Run another 10-cycle session with updated workflow
3. **Push for 15 cycles**: Test session stability at 120+ minutes
4. **Monitor duplicate detection**: Instrument adapter to log duplicate tool calls

---

## Appendix: Full Cycle Timeline

| Time | Event |
|------|-------|
| 12:25:01 | Session start |
| 12:25:34 | Cycle 1 P1 - Selected HELP directive |
| 12:30:11 | Cycle 1 P1 - HELP complete (f927095) |
| 12:35:44 | Cycle 2 P1 - Selected artifact summary docs |
| 12:38:38 | Cycle 2 complete |
| 12:39:05 | Cycle 3 P1 - Selected artifact templates |
| 12:46:15 | Cycle 3 complete |
| ... | ... |
| 13:37:15 | Cycle 10 P1 start |
| 13:43:28 | Cycle 10 complete, final compaction |
| 13:43:40 | Session end |

**Total wall-clock**: 78m 39s
