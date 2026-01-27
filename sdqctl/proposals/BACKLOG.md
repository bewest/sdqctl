# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-27  
> **Purpose**: Track active work items and proposals only  
> **Archive**: Completed work → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)

## Domain Backlogs

| Domain | File | Description |
|--------|------|-------------|
| Testing | [backlogs/testing.md](backlogs/testing.md) | Test infrastructure, coverage, fixtures |
| CLI | [backlogs/cli.md](backlogs/cli.md) | Commands, flags, help, UX |
| SDK | [backlogs/sdk-integration.md](backlogs/sdk-integration.md) | Copilot SDK, adapters, sessions |
| Architecture | [backlogs/architecture.md](backlogs/architecture.md) | Module structure, refactoring |
| Directives | [backlogs/directives.md](backlogs/directives.md) | Directive system, plugins |

---

## Ready Queue (5 Actionable Items)

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| 1 | Define `.sdqctl/directives.yaml` schema | P3 | Low | WP-004 step 1: JSON schema for plugin manifest. All OQs resolved. |
| 2 | Audit existing STPA artifacts | P3 | Low | WP-005 step 1: Count UCAs, SCs, coverage in ecosystem workspace. All OQs resolved. |
| 3 | Define custom severity scale with ISO 14971 mapping | P3 | Low | WP-005 step 2: Simple 3-5 level scale with standard mapping. |
| 4 | Implement directive discovery from manifest | P3 | Medium | WP-004 step 2: Load directives.yaml, register handlers. |
| 5 | Performance benchmark suite | P3 | Medium | **UNBLOCKED** - OQ-005 resolved. Scope: code + workflow + SDK (comprehensive). |

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
| *(No P2 items)* | | |

### P3: Low

| Item | Effort | Notes |
|------|--------|-------|
| *(All P3 Low items promoted to Ready Queue)* | | |

---

## Work Packages

Pre-grouped items that can complete together in 1-2 iterations. Prioritized within Ready Queue.

### WP-001: SDK Economy Optimization (P3) ✅ COMPLETE

Related items for improving iteration efficiency:
- [x] Domain-partitioned queues (Medium) - Separate backlogs per domain ✅ 2026-01-27
- [x] Iteration metrics tracking (Medium) - Items/cycle, lines/cycle metrics ✅ 2026-01-27
- [ ] backlog-processor-v3.conv (High) - Full economy optimization (future)

**Specification (2026-01-27)**:

**Domain-Partitioned Queues**:
- 5 domains: `testing`, `cli`, `sdk-integration`, `architecture`, `directives`
- Structure: `proposals/backlogs/{domain}.md` with main BACKLOG.md cross-referencing
- Items tagged with domain; cross-cutting items stay in main backlog
- Partition strategy: keyword matching on item description

**Iteration Metrics**:
- Work output: items/cycle, lines/cycle, tests/cycle
- Token efficiency: in/out ratio, estimated cost per item
- Duration: time/cycle, time/item
- Storage: `~/.sdqctl/sessions/{id}/metrics.json` (raw) + `reports/metrics/` (summaries)

**Dependencies**: Work package markers (this item) must complete first.  
**Estimated**: 2 iterations, ~200 lines

### WP-002: Continuous Monitoring (P3 R&D)

Related items for external repo monitoring:
- [ ] `sdqctl watch` - Monitor external repos for changes
- [ ] `sdqctl drift` - One-shot drift detection

**Dependencies**: None (R&D track)  
**Estimated**: 2 iterations, ~400 lines

### WP-003: Upstream Contribution (P3 R&D)

Related items for contributing fixes upstream:
- [ ] `sdqctl delegate <GAP-ID>` - Draft upstream fixes
- [ ] `sdqctl upstream status` - Track contribution status

**Dependencies**: WP-002 (needs drift detection)  
**Estimated**: 2 iterations, ~300 lines

### WP-004: Plugin System (P3 R&D)

Enable ecosystem teams to extend sdqctl with custom directives/commands independently of sdqctl release cycle.

- [ ] Define `.sdqctl/directives.yaml` manifest schema
- [ ] Implement directive discovery from manifest
- [ ] Hello world plugin in externals/rag-nightscout-ecosystem-alignment
- [ ] Security/sandboxing implementation
- [ ] Plugin authoring documentation

**Proposal**: [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md)  
**Dependencies**: None  
**Estimated**: 3-4 iterations, ~500 lines

### WP-005: STPA Deep Integration Research (P3 R&D)

Comprehensive research on STPA integration for Nightscout ecosystem, delivering usage guide and improvement predictions.

- [ ] Current state analysis and gap mapping
- [ ] Cross-project UCA pattern discovery
- [ ] STPA usage guide for ecosystem team
- [ ] Improvement predictions and 12-month roadmap

**Proposal**: [STPA-DEEP-INTEGRATION.md](STPA-DEEP-INTEGRATION.md)  
**Dependencies**: Existing STPA-INTEGRATION.md  
**Estimated**: 4 iterations, deliverable: ~2000 word report + templates

---

### Future (Unstarted)

Items not yet assigned to work packages:

| Item | Source | Notes |
|------|--------|-------|
| `sdqctl agent analyze <topic>` | [AGENTIC-ANALYSIS.md](AGENTIC-ANALYSIS.md) | Autonomous multi-cycle deep-dive (R&D) |

---

## Recently Completed

| Item | Date | Notes |
|------|------|-------|
| **Add metrics collection (P3)** | 2026-01-27 | WP-001 step 4: Created core/metrics.py, emit_metrics() to session dir. ~80 lines. Tracks tokens, cycles, duration. |
| **Migrate testing items (P3)** | 2026-01-27 | WP-001 step 3: Moved 17 test-related items to proposals/backlogs/testing.md. |
| **Define `metrics.json` schema (P3)** | 2026-01-27 | WP-001 step 2: Created docs/metrics-schema.json with work_output, token_efficiency, duration metrics. JSON Schema draft-07. |
| **Create `proposals/backlogs/` directory (P3)** | 2026-01-27 | WP-001 step 1: Created 5 domain backlog files (testing, cli, sdk-integration, architecture, directives) with headers and cross-references. |
| **Fix 5 lint issues (P3)** | 2026-01-27 | Fixed 2 E501 (line-too-long), 2 F401 (unused-import), 1 I001 (import-sort) in iterate.py, workspace.py, verify.py, artifact_ids.py, run.py. All 1476 tests pass. |
| **Agent output on stdout (P3)** | 2026-01-27 | Added `agent_response()` function. Agent responses now print to stdout by default. Respects `--quiet`. 4 tests. Total 1476 tests. |
| **`--introduction` and `--until` flags (P3)** | 2026-01-27 | Added `--introduction` (cycle 1 only) and `--until N` (cycles 1-N) prompt injection. 5 tests. Total 1472 tests. |
| **Default verbosity key actions (P3)** | 2026-01-27 | Verified existing implementation meets OQ-004 requirements: spinner, phase, context %, events, cycle/step progress all visible at default verbosity. |
| **Work package markers (P3)** | 2026-01-27 | Added WP-001 (SDK Economy), WP-002 (Monitoring), WP-003 (Upstream). Consolidated items from Future section. |
| **Disambiguation flags (P3)** | 2026-01-27 | Added `--prompt/-p` and `--file/-f` to iterate command. Clarifies ambiguous input. 5 tests. Total 1467 tests. |
| **Interactive help (P3)** | 2026-01-27 | Added `--interactive` / `-i` flag for browsable help. Features: list, topic lookup, prefix match, overview. 7 tests. Total 1462 tests. |
| **REFCAT glob support (P3)** | 2026-01-27 | Added glob expansion for REFCAT directive. `REFCAT @src/**/*.py` now expands to individual files. 9 tests. Total 1455 tests. |
| **HELP-INLINE directive (P3)** | 2026-01-27 | Added HELP-INLINE for mid-workflow help injection. Merges with next prompt. 6 tests. |
| **Ecosystem help topics (P3)** | 2026-01-27 | Added gap-ids, 5-facet, stpa, conformance, nightscout topics. 5 tests. Total 1446 tests. |
| **Q-019A: Progress timestamps (P3)** | 2026-01-26 | Added `set_timestamps()` to core/progress.py. Enabled when `-v` used. +4 tests. Total 1300 tests. |
| **iterate.py exit code alignment** | 2026-01-26 | Verified: MissingContextFiles already returns exit code 2 via `ExitCode.MISSING_FILES`. No fix needed. |
| **copilot.py further modularization (P2)** | 2026-01-26 | Reassessed: 670 lines includes 121 blank + docstrings. Core logic ~500 lines. Already extracted events.py (585) + stats.py (191). No further extraction needed. |
| **Q-021: `---` separator documentation (P2)** | 2026-01-26 | Documented `--` prefix requirement in `iterate --help` and COMMANDS.md. |
| **traceability.py modularization (P2)** | 2026-01-26 | Complete: 685 → 571 lines (-17%). Extracted traceability_coverage.py (135 lines). |
| **verify.py modularization (P2)** | 2026-01-26 | Complete: 641 → 532 lines (-17%). Extracted verify_output.py (114 lines). |
| **artifact.py modularization (P2)** | 2026-01-26 | Complete: 689 → 500 lines (-27%). Extracted core/artifact_ids.py (213 lines). |
| **help.py modularization (P2)** | 2026-01-26 | Complete: 698 → 156 lines (-78%). Extracted COMMAND_HELP to core/help_commands.py (550 lines). |
| **Compaction config unification (P2)** | 2026-01-26 | Complete: COMPACTION-MAX directive, CLI naming alignment, None defaults. +8 tests. Total 1296 tests. |
| **`run` command deprecation (P2)** | 2026-01-26 | Complete: 972 → 125 lines. Thin wrapper forwards to `iterate -n 1`. All 1288 tests pass. |
| **CLI modularization (P2)** | 2026-01-26 | Complete: 966 → 413 lines (-553, 57%). Extracted init.py (276 lines) and resume.py (292 lines). |
| **Copilot adapter modularization (P2)** | 2026-01-26 | Complete: 1143 → 670 lines (-473, 41%). Extracted CopilotEventHandler class to events.py. +32 tests. Total 1288 tests. |
| **Session resilience Phase 4 (P2)** | 2026-01-26 | Compaction summary display complete. +3 tests. Shows effectiveness ratio in completion output. Total 1256 tests. |
| **Session resilience Phase 3 (P2)** | 2026-01-26 | Predictive rate limiting complete. +9 tests. Added estimated_remaining_requests, estimated_minutes_remaining, warning integration. Total 1253 tests. |
| **Session resilience Phase 2 (P2)** | 2026-01-26 | Checkpoint resume testing complete. +4 tests. Documented rate-limit recovery in COMMANDS.md. |
| **SESSION-RESILIENCE (P2)** | 2026-01-26 | **PROPOSAL COMPLETE** - All 5 phases (0-4). Quota tracking, rate limit prediction, checkpoint resume, compaction metrics. |
| **iterate.py Modularization (P2)** | 2026-01-26 | Complete: 1397 → 791 lines (-606, 43%). Extracted 5 modules: iterate_helpers.py, compact_steps.py, prompt_steps.py, json_pipeline.py, output_steps.py. +26 tests. Target <800 ✅ |
| **run.py Modularization (P2)** | 2026-01-26 | Complete: 1523 → 973 lines (-550, 36%). Extracted elide.py, blocks.py, verify_steps.py, run_steps.py. +9 tests. Target <1000 ✅ |
| **SESSION-RESILIENCE Phase 0-1 (P2/P3)** | 2026-01-26 | Metrics instrumentation, CompactionEvent, timing props. +11 tests. |
| **StepExecutor reassessed (P2)** | 2026-01-26 | Analyzed: ~100 lines shared (not ~500). Extracted resolve_run_directory(). Full StepExecutor deferred. |
| **CONSULT-TIMEOUT (P2)** | 2026-01-26 | Phase 4: Timeout directive, expiration check on resume, clear error. 10 new tests. |
| **Compaction Simplification (P1)** | 2026-01-26 | Phase 5: Remove default prologue/epilogue. SDK-INFINITE-SESSIONS now complete. |
| **E501 lint cleanup** | 2026-01-26 | Fixed 69 issues in run.py, iterate.py, file.py. Core commands E501 clean. |
| **claude/openai adapter stubs (P2)** | 2026-01-26 | Created stubs with NotImplementedError. Registered in registry. |
| **Q-020 Context % fix (P0)** | 2026-01-26 | Sync tokens after each `ai_adapter.send()` in run.py and iterate.py. |
| **ARCHITECTURE.md (P1)** | 2026-01-26 | Created docs/ARCHITECTURE.md: module structure, data flow, key abstractions, extension points. |
| **ConversationFile Split (P0)** | 2026-01-26 | Modularized 1819-line file into 7 modules. Largest file now 858 lines. |
| **Shared utilities extraction** | 2026-01-26 | Error handling decorators, I/O utilities, VerifierBase scan_files, ExecutionContext. +32 tests. |
| **Phase 6: Mixed Prompt Support** | 2026-01-26 | Variadic targets, `---` separator, elision into boundaries. 16 new tests. |

*Test-related items migrated to [`proposals/backlogs/testing.md`](backlogs/testing.md)*  
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

### Copilot Adapter Modularization (P3) - ✅ COMPLETE

**Problem**: `copilot.py` was 1,143 lines with inline event handling

**Completed**: 2026-01-26

**Final structure**:
```
adapters/
  copilot.py       # CopilotAdapter main class (670 lines)
  events.py        # EventCollector + CopilotEventHandler + helpers (585 lines)
  stats.py         # SessionStats, TurnStats, CompactionEvent (191 lines)
```

**Result**: 1,143 → 670 lines (41% reduction). Event handling extracted to `CopilotEventHandler` class.

### CLI Modularization (P2) - ✅ COMPLETE

**Problem**: `cli.py` was 966 lines with embedded `init` and `resume` commands

**Completed**: 2026-01-26

**Final structure**:
```
commands/
  init.py     # init command + _create_copilot_files (276 lines)
  resume.py   # resume command + _resume_async (292 lines)
```

**Result**: cli.py 966 → 413 lines (57% reduction).

| Task | Effort | Status |
|------|--------|--------|
| Extract init command to commands/init.py | Low | ✅ Complete |
| Extract resume command to commands/resume.py | Low | ✅ Complete |
| Update cli.py imports | Low | ✅ Complete |
| Fix test imports | Low | ✅ Complete (4 imports in test_resume.py) |

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
| Max file size | 413 lines | <500 lines | cli.py (down from 966) |
| Lint issues (E501/F841) | 0 | 0 | ✅ Clean |
| Integration test files | 1 | 5+ | |
| Code duplication (run/cycle) | ~100 lines | <100 lines | ✅ Helpers extracted |

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
| [ITERATE-CONSOLIDATION](ITERATE-CONSOLIDATION.md) | ✅ Complete | All phases complete. `run` deprecated to thin wrapper (972 → 125 lines). |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | ✅ Complete | All 4 phases |
| [CONSULT-DIRECTIVE](CONSULT-DIRECTIVE.md) | ✅ Complete | Phase 1-4 complete. CONSULT-TIMEOUT added. |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | ✅ Complete | Taxonomy + CLI |
| [ERROR-HANDLING](ERROR-HANDLING.md) | ✅ Complete | All phases |
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | ✅ Complete | Native SDK compaction |
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | ✅ Complete | sessions resume + SESSION-NAME |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | ✅ Complete | Adapter methods + status |
| [SESSION-RESILIENCE](archive/SESSION-RESILIENCE.md) | ✅ Complete | All 5 phases. Quota tracking, rate limit prediction, compaction metrics. |
| [COMPACTION-UNIFICATION](COMPACTION-UNIFICATION.md) | ✅ Complete | COMPACTION-MAX directive, CLI alignment, None defaults. |
| [HELP-INLINE](HELP-INLINE.md) | ✅ Complete | HELP-INLINE directive + ecosystem topics (gap-ids, 5-facet, stpa, conformance, nightscout). |
| [VERBOSITY-DEFAULTS](VERBOSITY-DEFAULTS.md) | ✅ Complete | Verified existing implementation meets OQ-004 requirements. |
| [SDK-ECONOMY](SDK-ECONOMY.md) | 📝 Draft | Iteration efficiency: batch selection, work packages, protection policies. |

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
| No error path tests | Unknown failure behavior | ✅ Complete (29 tests in test_conversation_errors.py) |
| Missing parametrization | Incomplete variant coverage | 🔲 Open |
| No test markers | Can't run selective tests | ✅ Complete (5 files, 219 tests) |
| Fixtures not scoped | Slow test runs | ✅ Complete (session-scoped fixtures added) |
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
