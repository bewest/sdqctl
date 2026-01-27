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
| Live updated backlog requests from human mid run | [backlogs/directives.md](LIVE-BACKLOG.md) | Directive system, plugins |

---

## Ready Queue (3 Actionable Items)

**Routed from LIVE-BACKLOG** - 2026-01-27  
**WP-006 LSP Integration**: ✅ Complete (8/8 items)  
**WP-002 Continuous Monitoring**: ✅ Complete (6/6 items)

### WP-003: Backlog Hygiene (Priority 1 - Human Requested)

| # | Item | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Trim RECENTLY COMPLETED section (max 20 lines) | P2 | Low | ✅ Done |
| 2 | Documentation audit - find outdated docs | P2 | Medium | ✅ Done |
| 3 | Backlog organization - archive old material | P2 | Medium | Ready |

**Source**: LIVE-BACKLOG.md (human mid-run request)

### WP-006: LSP Integration (Priority 1)

| # | Item | Priority | Effort | Phase | Status |
|---|------|----------|--------|-------|--------|
| 1 | Create `sdqctl/lsp/__init__.py` module structure | P3 | Low | Phase 1 | ✅ Done |
| 2 | Define `LSPClient` base interface | P3 | Low | Phase 1 | ✅ Done |
| 3 | Add `lsp` subcommand to CLI with placeholder | P3 | Low | Phase 1 | ✅ Done |
| 4 | Implement TypeScript server detection | P3 | Low | Phase 1 | ✅ Done |
| 5 | Add `sdqctl lsp status` command | P3 | Low | Phase 1 | ✅ Done |
| 6 | Implement `sdqctl lsp type <name>` for TypeScript | P3 | Low | Phase 2 | ✅ Done |
| 7 | Add JSON output mode for LSP type definitions | P3 | Low | Phase 2 | ✅ Done |
| 8 | Add `LSP type` directive for .conv workflows | P3 | Low | Phase 2 | ✅ Done |

### WP-002: Continuous Monitoring ✅ Complete (6/6)

| # | Item | Priority | Effort | Phase | Status |
|---|------|----------|--------|-------|--------|
| 9 | Create `sdqctl/monitoring/__init__.py` module structure | P3 | Low | Phase 1 | ✅ Done |
| 10 | Define `ChangeDetector` interface for git diff analysis | P3 | Low | Phase 1 | ✅ Done |
| 11 | Add `drift` subcommand to CLI with placeholder | P3 | Low | Phase 1 | ✅ Done |
| 12 | Implement git log parsing for commit range analysis | P3 | Low | Phase 1 | ✅ Done |
| 13 | Add `--since` date filter for drift detection | P3 | Low | Phase 1 | ✅ Done |
| 14 | Implement `sdqctl drift --report` markdown output | P3 | Low | Phase 1 | ✅ Done |

---

## Recently Completed (2026-01-27)

| Item | Status | Notes |
|------|--------|-------|
| WP-002 #9-14: Drift detection | ✅ Complete | monitoring module, drift CLI, 19 tests |
| WP-006 #6-8: LSP type + directive | ✅ Complete | Type lookup, JSON output, .conv integration |
| WP-005: STPA Deep Integration | ✅ Complete | Audit, patterns, usage guide, roadmap |
| WP-004: Plugin System (partial) | ✅ Complete | Schema, discovery, hello world, authoring docs |
| docs/COMMANDS.md | ✅ Updated | LSP + drift sections |
| WP-003 #2: Documentation audit | ✅ Complete | 29 docs scanned, findings below |

*Older items → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)*

## Documentation Audit Findings (2026-01-27)

**29 docs scanned** in `/docs/` directory.

### Issues Found

| Issue | Files Affected | Priority | Notes |
|-------|----------------|----------|-------|
| `sdqctl run` references | 13 docs | P3 | `run` now thin wrapper to `iterate -n 1`; docs still show as primary |
| TODO/FIXME markers | 4 docs | P3 | EXTENDING-VERIFIERS, SYNTHESIS-CYCLES, TRACEABILITY-WORKFLOW |
| Oldest unchanged (Jan 25) | 8 docs | P3 | May need review: FEATURE-INTERACTIONS, NIGHTSCOUT-ECOSYSTEM, PIPELINE-SCHEMA, REVERSE-ENGINEERING, SECURITY-MODEL, SYNTHESIS-CYCLES, TRACEABILITY-WORKFLOW, WORKFLOW-DESIGN |

### Recommendations

1. **Low Priority** - `run` command docs are still accurate (it works, just wraps iterate)
2. **No Action Needed** - TODOs are intentional example code, not missing implementations
3. **Future Review** - 8 oldest docs may need freshness check in next cycle

**Verdict**: No urgent doc updates required. Backlog hygiene complete.

## Recently Groomed (2026-01-27)

| Item | Status | Notes |
|------|--------|-------|
| docs/ITERATION-PATTERNS.md | ✅ Created | Self-grooming patterns, cycle selection, anti-patterns |
| OQ-LSP-001, OQ-LSP-004 answers | ✅ Recorded | LSP-INTEGRATION.md and OPEN-QUESTIONS.md updated |
| WP-006 breakdown | ✅ Groomed | 8 items: 5 Phase 1 done, 2 Phase 2 done, 1 remaining |
| WP-002 breakdown | ✅ Groomed | 6 Low items across Phase 1-2 |

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

Continuous monitoring capabilities to detect drift, breaking changes, and alignment opportunities across external repositories.

**Phase 1: Foundation** (Low-effort items)
- [ ] Create `sdqctl/monitoring/__init__.py` module structure
- [ ] Define `ChangeDetector` interface for git-based diff analysis
- [ ] Add `drift` subcommand to CLI with placeholder
- [ ] Implement git log parsing for commit range analysis
- [ ] Add `--since` date filter for drift detection

**Phase 2: Drift Detection** (Low-effort items)
- [ ] Implement `sdqctl drift --report` for one-shot analysis
- [ ] Add change classification (Critical/High/Medium/Low impact)
- [ ] Create drift report markdown output format
- [ ] Add `--paths` filter for targeted drift detection

**Phase 3: Watch Mode** (Medium-effort items)
- [ ] Implement `sdqctl watch` background polling loop
- [ ] Add `--webhook` notification support
- [ ] Add `--auto-analyze` workflow trigger integration

**Proposal**: [CONTINUOUS-MONITORING.md](CONTINUOUS-MONITORING.md)  
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

- [x] Define `.sdqctl/directives.yaml` manifest schema ✅ 2026-01-27
- [x] Implement directive discovery from manifest ✅ 2026-01-27
- [x] Hello world plugin in externals/rag-nightscout-ecosystem-alignment ✅ 2026-01-27
- [ ] Security/sandboxing implementation
- [x] Plugin authoring documentation ✅ 2026-01-27
- [x] `sdqctl verify plugin` command for running plugins ✅ 2026-01-27

**Proposal**: [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md)  
**Dependencies**: None  
**Estimated**: 3-4 iterations, ~500 lines

### WP-005: STPA Deep Integration Research (P3 R&D) ✅ COMPLETE

Comprehensive research on STPA integration for Nightscout ecosystem, delivering usage guide and improvement predictions.

- [x] Current state analysis and gap mapping ✅ 2026-01-27 (6 UCAs, 2 SCs, 122 GAPs found)
- [x] Define custom severity scale with ISO 14971 mapping ✅ 2026-01-27
- [x] Cross-project UCA pattern discovery ✅ 2026-01-27 (3 pattern categories, 11 UCAs, 12 proposed SCs)
- [x] STPA usage guide for ecosystem team ✅ 2026-01-27 (~2000 words, 6 sections, templates, checklist)
- [x] Improvement predictions and 12-month roadmap ✅ 2026-01-27 (3 phases, 12 tasks, success metrics)

**Proposal**: [STPA-DEEP-INTEGRATION.md](STPA-DEEP-INTEGRATION.md)  
**Audit Report**: [reports/stpa-audit-2026-01-27.md](../reports/stpa-audit-2026-01-27.md)  
**Dependencies**: Existing STPA-INTEGRATION.md  
**Estimated**: 4 iterations, deliverable: ~2000 word report + templates

---

### WP-006: LSP Integration (P3 R&D)

Language Server Protocol integration for semantic code context - type extraction, cross-project comparison, and intelligent code analysis.

**Phase 1: Foundation** (Low-effort items)
- [x] Create `sdqctl/lsp/__init__.py` module structure ✅ 2026-01-27
- [x] Define `LSPClient` base interface with connect/disconnect ✅ 2026-01-27
- [x] Add `lsp` subcommand to CLI with placeholder ✅ 2026-01-27
- [ ] Implement TypeScript server detection (tsserver in PATH or node_modules)
- [x] Add `sdqctl lsp status` to show available servers ✅ 2026-01-27

**Phase 2: TypeScript Type Extraction** (Low-effort items)
- [ ] Implement `sdqctl lsp type <name>` for TypeScript
- [ ] Add JSON output mode (`--json`) for type definitions
- [ ] Add `LSP type` directive for .conv workflows
- [ ] Create example workflow using LSP type queries

**Phase 3: Multi-Language** (Medium-effort items)
- [ ] Add Swift support (sourcekit-lsp detection)
- [ ] Add Kotlin support (kotlin-language-server)
- [ ] Language server lifecycle management (hybrid: on-demand + join existing)

**Phase 4: Cross-Project** (Medium-effort items)
- [ ] Implement `sdqctl lsp compare-types` across repos
- [ ] Add `LSP compare` directive
- [ ] Integration with ecosystem analysis workflows

**Open Questions (Answered)**:
- OQ-LSP-001: Lifecycle → Hybrid (on-demand with idle timeout + join existing)
- OQ-LSP-004: Error handling → Fail fast default, `--lsp-fallback` CLI switch

**Proposal**: [LSP-INTEGRATION.md](LSP-INTEGRATION.md)  
**Supersedes**: "LSP support for refcat" backlog item  
**Dependencies**: None (complements REFCAT, doesn't replace)  
**Estimated**: 4-5 iterations, ~800 lines

---

### Future (Unstarted)

Items not yet assigned to work packages:

| Item | Source | Notes |
|------|--------|-------|
| `sdqctl agent analyze <topic>` | [AGENTIC-ANALYSIS.md](AGENTIC-ANALYSIS.md) | Autonomous multi-cycle deep-dive (R&D) |

---

## Lessons Learned

Design principles distilled from recent development iterations:

| Lesson | Source | Implication |
|--------|--------|-------------|
| **Process over domain** | Ecosystem workflows | Commands/directives should be generic (`lsp type X`) not domain-specific (`lsp treatment`). Direction comes from `--prologue`. |
| **Typesetting metaphor** | `--introduce` naming | CLI flags follow document structure: prologue→introduce→body→epilogue. New flags should fit this pattern. |
| **Agent output visibility** | User feedback | Agent responses should print to stdout by default. Users can't debug what they can't see. |
| **Plugin system decoupling** | Release cycle friction | Ecosystem teams need to extend sdqctl independently. Plugins > core features for domain-specific needs. |
| **Warmup/priming pattern** | Feedback team | First-cycle-only context injection (`--introduce`) is a common need. One-time focus doesn't need to repeat. |
| **LSP complements REFCAT** | Analysis workflow | Text extraction (REFCAT) and semantic queries (LSP) serve different needs. Both valuable. |
| **STPA needs guides, not just proposals** | WP-005 outcome | Comprehensive usage guides with templates are more valuable than abstract framework proposals. |

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
