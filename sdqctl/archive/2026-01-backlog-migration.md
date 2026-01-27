# Backlog Migration Archive - January 2026

> **Archived**: 2026-01-25  
> **Source**: proposals/BACKLOG.md  
> **Reason**: Reduce active backlog size (~1000 → <300 lines); preserve historical record  
> **Decision**: [D-015](DECISIONS.md#d-015-backlog-organization)

This file contains completed work items, resolved research, and historical analysis
that was previously in BACKLOG.md. This content is preserved for reference but is
no longer actively tracked.

---

## Tooling Commands Status (All Complete)

All 8 proposed tooling commands were fully implemented by 2026-01-25:

| Command | Purpose | Subcommands | Completion |
|---------|---------|-------------|------------|
| `render` | Preview prompts (no AI) | `run`, `cycle`, `apply`, `file` | 2026-01-23 |
| `verify` | Static verification | `refs`, `links`, `traceability`, `all` | 2026-01-23 |
| `validate` | Syntax checking | — | 2026-01-23 |
| `show` | Display parsed workflow | — | 2026-01-23 |
| `status` | Session/system info | `--adapters`, `--sessions`, `--models`, `--auth` | 2026-01-23 |
| `sessions` | Session management | `list`, `delete`, `cleanup`, `resume` | 2026-01-25 |
| `init` | Project initialization | — | 2026-01-23 |
| `help` | Documentation access | 12 commands, 6 topics | 2026-01-23 |

---

## SDK v2 Integration (All Complete)

> **Analysis Date**: 2026-01-24  
> **SDK Location**: `../../copilot-sdk/python`

| Feature | Proposal | Status | Completion | ADR |
|---------|----------|--------|------------|-----|
| Infinite Sessions | SDK-INFINITE-SESSIONS.md | ✅ Complete | 2026-01-25 | — |
| Session Persistence | SDK-SESSION-PERSISTENCE.md | ✅ Complete | 2026-01-25 | [ADR-004](decisions/ADR-004-sdk-session-persistence.md) |
| Metadata APIs | SDK-METADATA-APIS.md | ✅ Complete | 2026-01-25 | — |

### Key SDK Changes (Protocol Version 2)

- **Infinite Sessions** - Background compaction at 80% context, blocking at 95%
- **Session APIs** - `list_sessions()`, `resume_session()`, `delete_session()`
- **Metadata APIs** - `get_status()`, `get_auth_status()`, `list_models()`
- **Workspace Path** - `session.workspace_path` for session artifacts

---

## Research Items (All Resolved)

| ID | Topic | Hypothesis | Resolution | Date |
|----|-------|------------|------------|------|
| R-001 | SDK 2 intent reading | SDK 2 may provide tool info differently | Root cause was Q-014 handler leak | 2026-01-25 |
| R-002 | Accumulate mode stability | Event handlers accumulate across cycles | Fixed with handler-once pattern (line 655) | 2026-01-25 |
| R-003 | Event subscription cleanup | `send()` lacks handler cleanup | Handler registered once per session with flag | 2026-01-25 |

---

## Proposal vs Implementation Gap Analysis (Complete)

All proposals analyzed and gaps closed as of 2026-01-25.

### RUN-BRANCHING.md

| Feature | Proposed | Status |
|---------|----------|--------|
| `RUN-RETRY N "prompt"` | Phase 1 | ✅ Implemented |
| `ON-FAILURE` block | Phase 2 | ✅ Implemented |
| `ON-SUCCESS` block | Phase 2 | ✅ Implemented |
| ELIDE + branching = parse error | Design | ✅ Enforced |

### VERIFICATION-DIRECTIVES.md

| Feature | Proposed | Status |
|---------|----------|--------|
| `sdqctl verify refs` CLI | Phase 2 | ✅ Implemented |
| `sdqctl verify links` CLI | Phase 2 | ✅ Implemented |
| `sdqctl verify traceability` CLI | Phase 2 | ✅ Implemented |
| `sdqctl verify all` CLI | Phase 2 | ✅ Implemented |
| `VERIFY refs` directive | Phase 3-4 | ✅ Implemented |
| `VERIFY-ON-ERROR` directive | Phase 3-4 | ✅ Implemented |
| `VERIFY-OUTPUT` directive | Phase 3-4 | ✅ Implemented |
| `VERIFY-LIMIT` directive | Phase 3-4 | ✅ Implemented |
| `links` verifier | Phase 1 | ✅ Implemented |
| `terminology` verifier | Phase 1 | ✅ Implemented |
| `traceability` verifier | Phase 1 | ✅ Implemented |
| `assertions` verifier | Phase 1 | ✅ Implemented |

### PIPELINE-ARCHITECTURE.md

| Feature | Proposed | Status |
|---------|----------|--------|
| `--from-json` flag | Phase 1 | ✅ Implemented |
| `schema_version` field | Phase 2 | ✅ Implemented |
| Pipeline validation | Phase 3 | ✅ Implemented |

### CLI-ERGONOMICS.md

| Feature | Proposed | Status |
|---------|----------|--------|
| `sdqctl help <topic>` | — | ✅ 6 topics implemented |
| `sdqctl help <command>` | — | ✅ 12 commands documented |
| `--list` flag | — | ✅ Implemented |

---

## Priority 3: Implementation Tasks (All Complete)

### 3.1 `--from-json` Flag

**Status**: ✅ Complete (2026-01-24)

Enables external transformation of rendered workflows:
```bash
sdqctl render cycle workflow.conv --json \
  | jq '.cycles[0].prompts[0].resolved += " (modified)"' \
  | sdqctl cycle --from-json -
```

### 3.2 STPA Workflow Templates

**Status**: ✅ Complete (2026-01-24)

Templates created in `examples/workflows/stpa/`:
- `hazard-analysis.conv`
- `uca-identification.conv`
- `safety-constraint-derivation.conv`

### 3.3 VERIFY Directive Implementation

**Status**: ✅ Complete (2026-01-24)

All verifiers implemented:
- `refs` - @-reference validation
- `links` - URL/file link checking
- `traceability` - STPA chain validation
- `terminology` - Deprecated term detection
- `assertions` - Assertion documentation check

---

## Documentation Gaps (Completed Items)

| Gap | Location | Status | Date |
|-----|----------|--------|------|
| Pipeline schema docs | `docs/PIPELINE-SCHEMA.md` | ✅ | 2026-01-24 |
| Verifier extension guide | `docs/EXTENDING-VERIFIERS.md` | ✅ | 2026-01-24 |
| Security model | `docs/SECURITY-MODEL.md` | ✅ | 2026-01-25 |
| Model selection guide | `docs/ADAPTERS.md` | ✅ | 2026-01-25 |
| HELP directive examples | `docs/GETTING-STARTED.md` | ✅ | 2026-01-25 |
| ON-FAILURE/ON-SUCCESS tutorial | `docs/GETTING-STARTED.md` | ✅ | 2026-01-25 |
| `validate` command tutorial | `docs/GETTING-STARTED.md` | ✅ | 2026-01-25 |
| Copilot skill files docs | `docs/GETTING-STARTED.md` | ✅ | 2026-01-25 |
| CONSULT/SESSION-NAME in README | `README.md` | ✅ | 2026-01-25 |
| DEBUG directives in README | `README.md` | ✅ | 2026-01-25 |
| INFINITE-SESSIONS in README | `README.md` | ✅ | 2026-01-25 |
| `flow` command full documentation | `docs/COMMANDS.md` | ✅ | 2026-01-25 |
| `resume` vs `sessions resume` clarity | `docs/COMMANDS.md` | ✅ | 2026-01-25 |
| `artifact` user-facing guide | `docs/GETTING-STARTED.md` | ✅ | 2026-01-25 |

---

## Code Quality Fixes (Completed)

### Critical: Undefined Name Bugs (F821) - FIXED

5 bugs fixed (2026-01-25):

| Location | Variable | Fix Applied |
|----------|----------|-------------|
| `run.py:568` | `quiet` | Changed to `verbosity > 0` |
| `run.py:1172` | `restrictions` | Changed to `conv.file_restrictions` |
| `run.py:1173` | `show_streaming` | Changed to `True` |
| `run.py:1376` | `pending_context` | Removed dead code |
| `copilot.py:1001` | `ModelRequirements` | Added TYPE_CHECKING import |

### Linting Issues - 90% Fixed

**Before**: 1,994 issues | **After**: 197 issues | **Fixed**: 1,797 (90%)

| Category | Before | After |
|----------|--------|-------|
| W293 (whitespace in blank lines) | 1,617 | 0 |
| W291 (trailing whitespace) | 63 | 0 |
| F541 (f-string no placeholders) | 41 | 0 |
| F401 (unused imports) | 35 | 0 |
| I001 (unsorted imports) | 34 | 0 |
| F811 (redefinition) | 1 | 0 |

### Architecture Fixes

| Issue | Resolution | Date |
|-------|------------|------|
| Commands→core→commands circular import | Created `core/help_topics.py` | 2026-01-25 |
| Q-014 Event handler leak | Handler registered once per session | 2026-01-25 |
| Q-015 Duplicate tool calls | Fixed by Q-014 | 2026-01-25 |
| Q-013 Unknown tool names | Root cause was Q-014 | 2026-01-25 |
| RUN-ASYNC orphan processes | Added finally block cleanup | 2026-01-25 |

---

## Quirks Resolved

All quirks Q-001 through Q-018 resolved as of 2026-01-25.
See [docs/QUIRKS.md](../docs/QUIRKS.md) for details.

| Quirk | Resolution | Date |
|-------|------------|------|
| Q-018 | SDK session UUID stored in checkpoint for resume | 2026-01-25 |
| Q-016 | Undefined name bugs fixed | 2026-01-25 |
| Q-014/Q-015 | Event handler leak and duplicate tools | 2026-01-25 |
| Q-013 | Tool name "unknown" in logs | 2026-01-25 |

---

## Completed Items - 2026-01-27 Archive

Items archived from BACKLOG.md "Recently Completed" section.

| Item | Date | Notes |
|------|------|-------|
| **Performance benchmark suite (P3)** | 2026-01-27 | Created benchmarks/: bench_parsing.py, bench_rendering.py, bench_workflow.py, bench_sdk.py, run.py. Covers code perf, workflow timing, SDK latency. |
| **Directive discovery from manifest (P3)** | 2026-01-27 | WP-004 step 2: Created sdqctl/plugins.py. Loads .sdqctl/directives.yaml, registers PluginVerifier handlers. 21 tests. Total 1497 tests. |
| **Define severity scale (P3)** | 2026-01-27 | WP-005 step 2: Created docs/stpa-severity-scale.md. 4-level scale (S1-S4) with ISO 14971 mapping. 6 UCAs classified. |
| **Audit STPA artifacts (P3)** | 2026-01-27 | WP-005 step 1: Created reports/stpa-audit-2026-01-27.md. Found 6 UCAs, 2 SCs, 122 GAPs. SC coverage 17%, HAZ missing. |
| **Define directives.yaml schema (P3)** | 2026-01-27 | WP-004 step 1: Created docs/directives-schema.json. Defines version, directives map, handlers, args, timeout, requires. |
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

---

## References

- [BACKLOG.md](../proposals/BACKLOG.md) - Current active items
- [DECISIONS.md](DECISIONS.md) - Design decisions
- [SESSIONS/2026-01-25.md](SESSIONS/2026-01-25.md) - Session logs

---

## Architecture Roadmap Details (Archived 2026-01-27)

### Execution Engine Extraction - Reassessed

**Original Problem**: `run.py` and `iterate.py` duplicate step execution logic

**Analysis (2026-01-26)**:
- run.py: 14 step type handlers
- iterate.py: 5 step type handlers
- Overlap: 5 types but NOT 1:1 duplicates (context-aware)
- **Finding**: ~100 lines of truly shared code, not ~500

**Solution**: Extract `resolve_run_directory()` helper, defer full StepExecutor

### ConversationFile Split (P0)

```
core/conversation/
  __init__.py      # Re-exports (69 lines)
  types.py         # DirectiveType enum (246 lines)
  parser.py        # parse_line() (37 lines)
  applicator.py    # apply_directive() (419 lines)
  templates.py     # Template substitution (106 lines)
  utilities.py     # Content resolution (204 lines)
  file.py          # ConversationFile class (858 lines)
```

### Copilot Adapter Modularization

```
adapters/
  copilot.py       # CopilotAdapter (670 lines)
  events.py        # CopilotEventHandler (585 lines)
  stats.py         # SessionStats (191 lines)
```

### CLI Modularization

```
commands/
  init.py     # init command (276 lines)
  resume.py   # resume command (292 lines)
```

### Loop Detection Refinement

Skip minimal response check if tools were called:
```python
def _check_minimal_response(self, response, cycle_number, tools_called=0):
    if tools_called > 0:  # Agent was productive
        return False
    return len(response.strip()) < self.min_response_length
```
