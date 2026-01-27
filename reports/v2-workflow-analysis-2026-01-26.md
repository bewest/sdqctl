# sdqctl v2 Workflow Analysis

> **Date**: 2026-01-26  
> **Command**: `sdqctl -vvv iterate examples/workflows/backlog-processor-v2.conv --adapter copilot -n 10`  
> **Workflow Version**: backlog-processor-v2 (9-phase with PM/Librarian roles)  
> **First test of v2 workflow**

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Duration** | 54m 34s (3274s) |
| **Cycles Completed** | 10/10 (100%) |
| **Commits** | 33 |
| **Work Items Completed** | 12+ |
| **Tool Calls** | 539 (0 failures) |
| **Context Peak** | 20% (26,129/128,000 tokens) |

**Outstanding Success**: The v2 workflow completed all 10 cycles without stopping, demonstrating excellent efficiency. The new Phase 7-8-9 (PM/Librarian) phases worked as designed.

---

## Key Metrics

### Session Statistics

| Metric | Value |
|--------|-------|
| Total Turns | 443 |
| Input Tokens | 36,918,465 |
| Output Tokens | 139,165 |
| Token Ratio | 265:1 (in:out) |
| Tool Calls | 539 |
| Tool Success Rate | 100% |
| Context Peak | 20% |

### Tool Usage Distribution

| Tool | Calls | % of Total |
|------|-------|------------|
| bash | 158 | 29.3% |
| view | 146 | 27.1% |
| report_intent | 96 | 17.8% |
| edit | 92 | 17.1% |
| update_todo | 25 | 4.6% |
| create | 14 | 2.6% |
| grep | 4 | 0.7% |
| glob | 4 | 0.7% |

---

## Major Accomplishments

### P0: Split conversation.py ✅

The flagship P0 task was completed in Cycle 1:

| Before | After |
|--------|-------|
| 1 file, 1,819 lines | 7 modules in `core/conversation/` |

**New module structure**:
- `types.py` (246 lines) - DirectiveType enum, dataclasses
- `parser.py` (37 lines) - parse_line() function
- `applicator.py` (419 lines) - apply_directive() functions
- `templates.py` (106 lines) - Template variable substitution
- `utilities.py` (204 lines) - Content resolution, builders
- `file.py` (858 lines) - ConversationFile class
- `__init__.py` (69 lines) - Backward-compatible re-exports

### P1: Create ARCHITECTURE.md ✅

Created comprehensive architecture documentation covering:
- Module structure with package layout
- Key abstractions
- Data flow diagrams
- Extension points
- Configuration hierarchy

### Additional Work Completed

| Cycle | Work Item | Type |
|-------|-----------|------|
| 3 | test_exceptions.py | Test |
| 4 | test_renderer_core.py | Test |
| 5 | test_command_utils.py | Test |
| 6 | Pytest markers (unit/integration/slow) | Test infra |
| 7 | OQ-004 scope clarification | Documentation |
| 8 | E501 fixes (13 issues) | Lint |
| 9 | E501 fixes (9 issues in session.py) | Lint |
| 10 | E501 fixes (10 issues in copilot.py) | Lint |

### Lint Progress

| Metric | Before | After |
|--------|--------|-------|
| E501 (line too long) | 192 | 171 |
| F821 (undefined name) | 3 | 0 |
| F401 (unused import) | 1 | 0 |
| Total issues | 214 | ~171 |

---

## Phase Analysis

### Cycle Timing (All 9 Phases)

| Cycle | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | Total |
|-------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 1 | 645.9s | 145.6s | 46.9s | 69.8s | 40.5s | 25.3s | 78.2s | 34.9s | 37.7s | **1124.8s** |
| 2 | 73.1s | 61.8s | 20.7s | 24.5s | 9.1s | 8.4s | 14.7s | 7.9s | 28.1s | **248.3s** |
| 3 | 8.7s | 48.0s | 20.3s | 18.4s | 8.8s | 7.4s | 9.7s | 8.4s | 25.5s | **155.2s** |
| 4-10 | ~10s | ~50-80s | ~20s | ~20s | ~9s | ~8s | ~10s | ~8s | ~25s | ~160-200s |

### Phase Time Distribution

| Phase | Role | Avg Time | % of Cycle |
|-------|------|----------|------------|
| P1: Selection | Implementer | ~50s | 15% |
| P2: Execute | Implementer | ~70s | 21% |
| P3: Verify | Implementer | ~20s | 6% |
| P4: Documentation | Implementer | ~25s | 8% |
| P5: Hygiene | Implementer | ~10s | 3% |
| P6: Commit | Implementer | ~8s | 2% |
| P7: Candidates | PM | ~20s | 6% |
| P8: Routing | PM | ~10s | 3% |
| P9: Archive | Librarian | ~28s | 8% |

**Key Insight**: Cycle 1 took 1125s (34% of total) due to P0 complexity. Cycles 2-10 averaged 239s each.

---

## New Phases Evaluation (v2 Additions)

### Phase 7: Candidate Discovery ✅

**Behavior**: Agent scanned proposals/, code, and identified lint issues to work on.

**Observation**: After P0/P1 completed, Phase 7 effectively pivoted to P3 lint work, generating E501 fix candidates.

### Phase 8: Queue Routing ✅

**Behavior**: Maintained Ready Queue state, proper prioritization.

**Result**: Backlog transitions:
- P0: 1 → 0 items (conversation.py split completed)
- P1: 1 → 0 items (ARCHITECTURE.md completed)
- P3 items properly cycled through

### Phase 9: Archive & Integrate ✅

**Behavior**: Created `archive/SESSIONS/2026-01-26.md` with detailed session log.

**File Size Discipline**:
| File | Lines | Target | Status |
|------|-------|--------|--------|
| BACKLOG.md | 279 | <300 | ✅ OK |
| OPEN-QUESTIONS.md | 60 | - | ✅ OK |
| QUIRKS.md | 183 | <200 | ✅ OK |

---

## Context Efficiency

### Context Growth

```
Cycle 1 Start:   6% ( 8,298 tokens)
Cycle 1 End:     1% (after COMPACT)
Cycle 10 End:   20% (26,129 tokens)
```

**Exceptional efficiency**: Context never approached 60% limit. COMPACT after Phase 6 kept context lean.

### Comparison to v1 Workflow

| Metric | v1 (5 cycles) | v2 (10 cycles) |
|--------|---------------|----------------|
| Duration | 31 min | 55 min |
| Cycles | 5.5 | 10 |
| Work items | 5 | 12+ |
| Context peak | 58% | 20% |
| Tool success | 99.4% | 100% |

**v2 is more efficient per-cycle** with better context management.

---

## Open Questions Generated

The workflow properly routed design questions to OPEN-QUESTIONS.md:

| ID | Question | Priority |
|----|----------|----------|
| OQ-001 | CONSULT Phase 4 timeout behavior | P2 |
| OQ-002 | claude/openai adapter scope | P2 |
| OQ-003 | StepExecutor priority | P2 |
| OQ-004 | Default verbosity key actions scope | P3 |

This demonstrates the bidirectional flow working as designed.

---

## Recommendations

### 1. Phase 7 Candidate Quality

**Observation**: After major work completed, Phase 7 focused heavily on lint issues.

**Recommendation**: Add variety guidance to Phase 7 prompt:
```
Prefer candidates from different categories:
- At least 1 implementation/refactor
- At least 1 documentation
- At least 1 test gap
```

### 2. Session Archive Efficiency

**Observation**: Phase 9 updated session archive every cycle (10 commits just for archive).

**Recommendation**: Consider aggregating session log updates - commit once per cycle with all changes, or batch archive updates every 3 cycles.

### 3. Context Headroom

**Observation**: Context peaked at only 20% despite 10 cycles.

**Recommendation**: The 60% COMPACT threshold is conservative. Consider raising to 70% or adding mid-session COMPACT for runs >15 cycles.

### 4. Blocked Item Tracking

**Observation**: "Default verbosity key actions" correctly marked as blocked by OQ-004.

**Recommendation**: Add clear visual indicator in BACKLOG.md for blocked items:
```
| ⏸️ Default verbosity key actions | Low | **Blocked by OQ-004** |
```

---

## Comparison: Prediction vs Actual

| Prediction | Actual | Accuracy |
|------------|--------|----------|
| Duration: 45-90 min | 55 min | ✅ |
| Cycles: 2-4 | 10 | ❌ Exceeded expectations |
| P0 completion in 1 cycle | Yes (1125s) | ✅ |
| Phase 7-8-9 work | All functional | ✅ |
| Ready Queue = 3 | Maintained | ✅ |
| New OPEN-QUESTIONS | 4 entries | ✅ |
| Context peak | 58% predicted, 20% actual | ✅ Better than expected |

**Key Miss**: Predicted 2-4 cycles due to P0 complexity. Agent completed P0+P1 quickly and continued through P3 lint work for full 10 cycles.

---

## Repository State After Run

### File Structure Changes

```
sdqctl/core/conversation/    # NEW - 7 modules
  __init__.py
  applicator.py
  file.py
  parser.py
  templates.py
  types.py
  utilities.py

docs/ARCHITECTURE.md         # NEW - 200+ lines
archive/SESSIONS/2026-01-26.md  # NEW - session log
```

### Test Status

- Total tests: 1042
- All passing
- New test files: 3 (test_exceptions.py, test_renderer_core.py, test_command_utils.py)
- Pytest markers added

### Commits (33 total)

Major commits:
- `959e7b6` refactor(core): modularize conversation.py + add ARCHITECTURE.md
- `6d0bdb6` test: add test_exceptions.py
- `0850ec1` test: add test_renderer_core.py
- `6edd019` test: add test_command_utils.py
- `50263c0` test: add pytest markers

---

## Conclusion

The v2 workflow with 9 phases performed exceptionally well:

1. **P0/P1 completed**: Both high-priority items done in first 2 cycles
2. **100% tool success**: No failures across 539 tool calls
3. **Excellent context efficiency**: 20% peak vs 60% limit
4. **PM/Librarian phases working**: Proper candidate generation, routing, and archival
5. **Full cycle completion**: 10/10 cycles without STOPAUTOMATION

The bidirectional workflow design (code → questions → humans) is functioning as intended, with OPEN-QUESTIONS.md capturing design decisions that need human input.

---

## Appendix

### Log File Details

- **File**: `../even-more-backlog.log`
- **Lines**: 5,067
- **Duration**: 3274 seconds

### System Resources

| Resource | Value |
|----------|-------|
| Real Time | 54m 34s |
| User Time | 3m 38s (6.6% CPU) |
| Sys Time | 19s |
| Efficiency | Low CPU expected (API-bound) |
