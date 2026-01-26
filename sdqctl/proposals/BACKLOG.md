# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-26  
> **Purpose**: Track active work items and proposals only  
> **Archive**: Completed work → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)

---

## Active Priorities

### P0: Critical

| Item | Effort | Notes |
|------|--------|-------|
| *(No P0 items)* | | |

### P1: High

| Item | Effort | Notes |
|------|--------|-------|
| *(No P1 items)* | | |

### P2: Medium

| Item | Effort | Notes |
|------|--------|-------|
| Add integration tests | Medium | Phase 2 done: +30 tests for iterate_helpers, compact_steps. Total 1244 tests. |
| Session resilience Phase 3 | Medium | [SESSION-RESILIENCE.md](SESSION-RESILIENCE.md) - Predictive rate limiting |
| Performance benchmark suite | Medium | **Blocked by OQ-005** - needs scope decision. Track regressions. |

### P3: Low

| Item | Effort | Notes |
|------|--------|-------|
| Default verbosity key actions | Low | **Blocked by OQ-004** → [VERBOSITY-DEFAULTS.md](VERBOSITY-DEFAULTS.md) |
| Session resilience Phase 4 | Medium | [SESSION-RESILIENCE.md](SESSION-RESILIENCE.md) Compaction strategy tuning |

### Future (Unstarted)

| Item | Source | Notes |
|------|--------|-------|
| LSP support for refcat | References | Language Server Protocol for IDE integration |
| Interactive help (`--interactive`) | References | Browsable help system |
| refcat usage patterns example | P3 Workflow Examples | Cross-repo context injection |
| Multiple .conv files in mixed mode | Phase 6 deferred | Complex; requires positional prologue tracking |
| `--once` flag for non-repeating CLI prompts | Phase 6 deferred | Needs use case research |
| `--prompt` / `--file` disambiguation switches | Phase 6 deferred | Needs impact analysis |

---

## Recently Completed

| Item | Date | Notes |
|------|------|-------|
| **Session resilience Phase 2 (P2)** | 2026-01-26 | Checkpoint resume testing complete. +4 tests. Documented rate-limit recovery in COMMANDS.md. Total 1244 tests. |
| **iterate.py Modularization (P2)** | 2026-01-26 | Complete: 1397 → 791 lines (-606, 43%). Extracted 5 modules: iterate_helpers.py, compact_steps.py, prompt_steps.py, json_pipeline.py, output_steps.py. +26 tests. Target <800 ✅ |
| **run.py Modularization (P2)** | 2026-01-26 | Complete: 1523 → 973 lines (-550, 36%). Extracted elide.py, blocks.py, verify_steps.py, run_steps.py. +9 tests. Target <1000 ✅ |
| **Integration tests Phase 2 (P2)** | 2026-01-26 | +30 tests for iterate_helpers.py (23) and compact_steps.py (7). Total 1240 tests. |
| **SESSION-RESILIENCE Phase 0-1 (P2/P3)** | 2026-01-26 | Metrics instrumentation, CompactionEvent, timing props. +11 tests. |
| **StepExecutor reassessed (P2)** | 2026-01-26 | Analyzed: ~100 lines shared (not ~500). Extracted resolve_run_directory(). Full StepExecutor deferred. |
| **CONSULT-TIMEOUT (P2)** | 2026-01-26 | Phase 4: Timeout directive, expiration check on resume, clear error. 10 new tests. |
| **Compaction Simplification (P1)** | 2026-01-26 | Phase 5: Remove default prologue/epilogue. SDK-INFINITE-SESSIONS now complete. |
| **E501 lint cleanup** | 2026-01-26 | Fixed 69 issues in run.py, iterate.py, file.py. Core commands E501 clean. |
| **Loop detection: tool-aware** | 2026-01-26 | Skip minimal response check if tools called in turn. 2 new tests. |
| **claude/openai adapter stubs (P2)** | 2026-01-26 | Created stubs with NotImplementedError. Registered in registry. |
| **Q-020 Context % fix (P0)** | 2026-01-26 | Sync tokens after each `ai_adapter.send()` in run.py and iterate.py. |
| **ARCHITECTURE.md (P1)** | 2026-01-26 | Created docs/ARCHITECTURE.md: module structure, data flow, key abstractions, extension points. |
| **ConversationFile Split (P0)** | 2026-01-26 | Modularized 1819-line file into 7 modules. Largest file now 858 lines. |
| **Shared utilities extraction** | 2026-01-26 | Error handling decorators, I/O utilities, VerifierBase scan_files, ExecutionContext. +32 tests. |
| **Phase 6: Mixed Prompt Support** | 2026-01-26 | Variadic targets, `---` separator, elision into boundaries. 16 new tests. |

*Older items archived to [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)*

---

## Architecture Roadmap

> **Source**: Code review session 2026-01-25  
> **Objective**: Improve maintainability without disrupting features

### Execution Engine Extraction (P2) - ⚠️ REASSESSED

**Original Problem**: `run.py` and `iterate.py` duplicate step execution logic (~500 lines overlap)

**Analysis (2026-01-26):**
- run.py: 14 step type handlers (full single-run executor)
- iterate.py: 5 step type handlers (cycle wrapper with session context)
- Overlap: 5 types (`checkpoint`, `compact`, `prompt`, `verify_trace`, `verify_coverage`)
- **Finding**: Handlers share patterns but are NOT 1:1 duplicates. Each is context-aware:
  - run.py checkpoint: writes output, git commits
  - iterate.py checkpoint: simple session checkpoint
  - run.py prompt: single execution
  - iterate.py prompt: cycle context injection, stop file, continuation prompts

**Revised Assessment**: ~100 lines of truly shared code (patterns), not ~500.

**Revised Solution**: Extract shared helpers, not full StepExecutor

```python
# commands/utils.py additions
def resolve_run_directory(run_cwd, cwd, source_path) -> Path
```

| Task | Effort | Status |
|------|--------|--------|
| Extract run directory resolution | Low | ✅ Done (2026-01-26) |
| Extract output formatting helpers | Low | 🔲 Deferred (already in truncate_output) |
| Document why full StepExecutor deferred | Low | ✅ Done (this note) |

**Completed (2026-01-26):** `resolve_run_directory()` extracted, 3 duplicated blocks replaced, 6 tests added.

**Deferred**: Full StepExecutor refactor to Future (High effort, high risk for modest gain)

### Shared ExecutionContext (P2) - ✅ COMPLETE

**Problem**: Adapter initialization repeated in run.py, cycle.py, apply.py

**Solution**: Created `ExecutionContext` dataclass in `core/session.py`

```python
@dataclass
class ExecutionContext:
    adapter: AdapterBase
    adapter_config: AdapterConfig
    adapter_session: AdapterSession
    session: Session
    conv: ConversationFile
    verbosity: int
    console: Console
    show_prompt: bool
    json_errors: bool
```

**Completed**: 2026-01-26

| Task | Effort | Status |
|------|--------|--------|
| Define ExecutionContext in core/session.py | Low | ✅ Complete |
| Add create_execution_context() factory | Low | ✅ Complete |
| Add tests | Low | ✅ Complete (4 tests) |
| Refactor run.py to use ExecutionContext | Low | 🔲 Deferred to StepExecutor |
| Refactor iterate.py to use ExecutionContext | Low | 🔲 Deferred to StepExecutor |
| Refactor apply.py to use ExecutionContext | Low | 🔲 Deferred to StepExecutor |

### ConversationFile Split (P0) - ✅ COMPLETE

**Problem**: `conversation.py` was 1,819 lines with mixed responsibilities

**Completed**: 2026-01-26

**Final structure**:
```
core/conversation/
  __init__.py      # Re-exports for backward compatibility (69 lines)
  types.py         # DirectiveType enum + dataclasses (246 lines)
  parser.py        # parse_line() function (37 lines)
  applicator.py    # apply_directive() functions (419 lines)
  templates.py     # Template variable substitution (106 lines)
  utilities.py     # Content resolution, injection builders (204 lines)
  file.py          # ConversationFile class (858 lines)
```

**Result**: 1,819 lines → 7 modules, largest file 858 lines. All 1042 tests pass.

### Architecture Documentation (P1) - ✅ COMPLETE

**Completed**: 2026-01-26

**Deliverable**: `docs/ARCHITECTURE.md` covering:
- Module structure with package layout diagram
- Key abstractions: ConversationFile, Session, ExecutionContext, AdapterBase, VerifierBase
- Data flow diagram: conversation → renderer → adapter → SDK
- Extension points: adapters, verifiers, directives, commands
- Configuration hierarchy: defaults → config file → env → workflow → CLI
- Error handling and exit codes
- Testing strategy

| Task | Effort | Status |
|------|--------|--------|
| Document module structure | Low | ✅ Complete |
| Create data flow diagram | Low | ✅ Complete |
| Document extension points | Low | ✅ Complete |
| Add key abstractions section | Low | ✅ Complete |

### Copilot Adapter Modularization (P3)

**Problem**: `copilot.py` is 1,000+ lines with inline event handling

**Proposed structure**:
```
adapters/copilot/
  __init__.py      # CopilotAdapter (main class)
  events.py        # CopilotEventHandler
  stats.py         # SessionStats tracking
  session.py       # Session management
```

### Integration Test Expansion (P3)

| Test Area | Current | Target |
|-----------|---------|--------|
| Loop stress testing | ✅ 1 file | Keep |
| Adapter integration | ❌ None | 1 file per adapter |
| End-to-end workflows | ❌ None | 3-5 scenarios |
| CLI integration | ❌ None | Core commands |

### Metrics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Max file size | 858 lines | <500 lines | file.py (down from 1,819) |
| Lint issues (E501/F841) | 197 | 0 | |
| Integration test files | 1 | 5+ | |
| Code duplication (run/cycle) | ~500 lines | <100 lines | |

### QUIRKS Grooming (P3) - ✅ COMPLETE

**Completed:** 2026-01-25

**Result**:
- `docs/QUIRKS.md`: 960 → 135 lines (86% reduction)
- `archive/quirks/2026-01-resolved-quirks.md`: Full context preserved
- `docs/SDK-LEARNINGS.md`: Extracted actionable patterns

| File | Purpose |
|------|---------|
| `docs/QUIRKS.md` | Active quirks only (Q-017, Q-019A) + quick reference |
| `archive/quirks/` | Archived resolved quirks with full details |
| `docs/SDK-LEARNINGS.md` | Extracted patterns/learnings from resolved quirks |

### Loop Detection Refinement (P2) - ✅ COMPLETE

**Problem:** Minimal response detection (100 chars) triggers false positives on short but valid responses like Phase 6 commit acknowledgments.

**Evidence:** Run #4 stopped at Cycle 5, Phase 6 with 98-char response after successful commit.

**Root Cause:** `_check_minimal_response()` checks only response length, ignoring tool activity.

**Solution Implemented:** Skip minimal response check if tools were called in the turn.

```python
# In loop_detector.py:
def check(
    self,
    reasoning: Optional[str],
    response: str,
    cycle_number: int = 0,
    tools_called: int = 0  # NEW: tool count for this turn
) -> Optional[LoopDetected]:

# In _check_minimal_response():
def _check_minimal_response(
    self, response: str, cycle_number: int, tools_called: int = 0
) -> bool:
    if cycle_number == 0:
        return False
    if tools_called > 0:  # Agent was productive
        return False
    return len(response.strip()) < self.min_response_length
```

**Completed:** 2026-01-26

| Task | Effort | Status |
|------|--------|--------|
| Add `tools_called` param to `check()` | Low | ✅ Complete |
| Modify `_check_minimal_response()` | Low | ✅ Complete |
| Update call site in iterate.py | Low | ✅ Complete |
| Add test for tool-aware detection | Low | ✅ Complete (2 tests) |
| Update docstrings | Low | ✅ Complete |

---

## Proposals Status

| Proposal | Status | Notes |
|----------|--------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | ✅ Complete | RUN-RETRY + ON-FAILURE/ON-SUCCESS |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | ✅ Complete | All 4 phases |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | ✅ Complete | --from-json + schema_version |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | ✅ Complete | Templates + traceability verifier |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | ✅ Complete | Help implemented |
| [ITERATE-CONSOLIDATION](ITERATE-CONSOLIDATION.md) | ✅ Complete | All 6 phases complete. Mixed mode, separators, elision. |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | ✅ Complete | All 4 phases |
| [CONSULT-DIRECTIVE](CONSULT-DIRECTIVE.md) | ✅ Complete | Phase 1-4 complete. CONSULT-TIMEOUT added. |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | ✅ Complete | Taxonomy + CLI |
| [ERROR-HANDLING](ERROR-HANDLING.md) | ✅ Complete | All phases |
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | ✅ Complete | Native SDK compaction |
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | ✅ Complete | sessions resume + SESSION-NAME |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | ✅ Complete | Adapter methods + status |
| [SESSION-RESILIENCE](SESSION-RESILIENCE.md) | 🚀 Ready | P2: Metrics instrumentation (Phase 0-0.5). P3: Rate limit prediction, checkpoint resume |

---

## Security Considerations

Documented in [`docs/SECURITY-MODEL.md`](../docs/SECURITY-MODEL.md).

| Issue | Severity | Notes |
|-------|----------|-------|
| Shell injection via ALLOW-SHELL | HIGH | Documented; disabled by default |
| ~~Path traversal (refcat.py)~~ | ~~MEDIUM~~ | ✅ AUDITED (2026-01-25) - Not a vuln; CLI reads with user perms like cat/grep |
| RUN_ENV allows LD_PRELOAD | MEDIUM | Consider whitelist |
| OUTPUT-FILE path injection | LOW | Validate paths |
| ~~RUN-ASYNC resource leak~~ | ~~MEDIUM~~ | ✅ FIXED (2026-01-25) - Cleanup in finally block |

---

## Test Quality Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| No error path tests | Unknown failure behavior | 🔲 Open |
| Missing parametrization | Incomplete variant coverage | 🔲 Open |
| No test markers | Can't run selective tests | ✅ Complete (5 files, 219 tests) |
| Fixtures not scoped | Slow test runs | 🔲 Open |
| No `test_exceptions.py` | Exit codes untested | ✅ Complete |
| No `test_renderer_core.py` | Renderer logic untested | ✅ Complete |
| No `test_command_utils.py` | `run_async()` untested | ✅ Complete |

---

## References

> **Note**: Cross-reference with QUIRKS.md for quirk-related backlog items.

- [archive/](../archive/) - Archived session logs and design decisions
- [archive/2026-01-backlog-migration.md](../archive/2026-01-backlog-migration.md) - Completed items snapshot
- [docs/DIRECTIVE-REFERENCE.md](../docs/DIRECTIVE-REFERENCE.md) - Complete directive catalog
- [docs/CODE-QUALITY.md](../docs/CODE-QUALITY.md) - Code quality standards
- [docs/PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Workflow design principles
- [docs/QUIRKS.md](../docs/QUIRKS.md) - Active quirks only (Q-017, Q-019A)
- [docs/SDK-LEARNINGS.md](../docs/SDK-LEARNINGS.md) - Patterns from resolved quirks
- [archive/quirks/](../archive/quirks/) - Archived resolved quirks

**Future ideas**: LSP support for refcat, interactive help system
