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
| Live updated backlog requests from human mid run | [LIVE-BACKLOG.md](LIVE-BACKLOG.md) | Live backlog requests |

---

## Ready Queue (0 Actionable Items)

**All items complete or blocked** - 2026-01-27  
**Note**: WP-003 blocked pending human review of OQ-UP-001..004

### WP-003: Upstream Contribution (Priority 1) - BLOCKED

| # | Item | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Implement `sdqctl delegate <GAP-ID>` command | P3 | Low | ⏸️ Blocked: OQ-UP-001..004 |
| 2 | Implement `sdqctl upstream status` command | P3 | Low | ⏸️ Blocked: OQ-UP-001..004 |

**Blocker**: 4 open questions in UPSTREAM-CONTRIBUTIONS.md routed to OPEN-QUESTIONS.md

### WP-004: Plugin Security (Priority 2) ✅ Complete

| # | Item | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 3 | Implement plugin sandboxing/security | P3 | Medium | ✅ Done |

---

### WP-006: LSP Integration ✅ Complete (8/8)

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
| WP-004 #3: Plugin security | ✅ Complete | plugin command, capability validation, 30 tests |
| docs/COLOPHON.md | ✅ Complete | Dogfooding story, metrics, construction journey |
| WP-002 #9-14: Drift detection | ✅ Complete | monitoring module, drift CLI, 19 tests |
| WP-006 #6-8: LSP type + directive | ✅ Complete | Type lookup, JSON output, .conv integration |
| WP-005: STPA Deep Integration | ✅ Complete | Audit, patterns, usage guide, roadmap |
| WP-004: Plugin System (Phase 1-3) | ✅ Complete | Schema, discovery, validation, security |
| docs/COMMANDS.md | ✅ Updated | LSP + drift + plugin sections |
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

### Completed Work Packages

| WP | Name | Status | Key Deliverables |
|----|------|--------|------------------|
| WP-001 | SDK Economy Optimization | ✅ Complete | Domain backlogs, metrics schema, core/metrics.py |
| WP-002 | Continuous Monitoring | ✅ Complete | monitoring module, drift CLI, 19 tests |
| WP-005 | STPA Deep Integration | ✅ Complete | Audit, patterns, usage guide, roadmap |
| WP-006 | LSP Integration | ✅ Complete | lsp module, type lookup, LSP directive |

*Details → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)*

### WP-003: Upstream Contribution (P3 R&D)

Related items for contributing fixes upstream:
- [ ] `sdqctl delegate <GAP-ID>` - Draft upstream fixes
- [ ] `sdqctl upstream status` - Track contribution status

**Dependencies**: WP-002 (needs drift detection) ✅  
**Estimated**: 2 iterations, ~300 lines

### WP-004: Plugin System (P3 R&D) - Partial

Enable ecosystem teams to extend sdqctl with custom directives/commands.

- [x] Define `.sdqctl/directives.yaml` manifest schema ✅
- [x] Implement directive discovery from manifest ✅
- [x] Hello world plugin ✅
- [ ] Security/sandboxing implementation
- [x] Plugin authoring documentation ✅
- [x] `sdqctl verify plugin` command ✅

**Proposal**: [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md)  
**Remaining**: Security/sandboxing (1 item)

---

### Future (Unstarted)

Items not yet assigned to work packages:

| Item | Source | Notes |
|------|--------|-------|
| `sdqctl agent analyze <topic>` | [AGENTIC-ANALYSIS.md](AGENTIC-ANALYSIS.md) | Autonomous multi-cycle deep-dive (R&D) |
| WP-006 Phase 3: Multi-language LSP | [LSP-INTEGRATION.md](LSP-INTEGRATION.md) | Swift, Kotlin support |
| WP-006 Phase 4: Cross-project compare | [LSP-INTEGRATION.md](LSP-INTEGRATION.md) | `lsp compare-types` |
| WP-004 Phase 4: Ecosystem adoption | [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md) | Migrate tools to plugin format, gather feedback |

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

### Completed Refactors

| Item | Result | Date |
|------|--------|------|
| ConversationFile Split (P0) | 1,819 → 7 modules, largest 858 lines | 2026-01-26 |
| Architecture Documentation (P1) | docs/ARCHITECTURE.md | 2026-01-26 |
| CLI Modularization (P2) | 966 → 413 lines (-57%) | 2026-01-26 |
| Copilot Adapter (P3) | 1,143 → 670 lines (-41%) | 2026-01-26 |
| QUIRKS Grooming (P3) | 960 → 135 lines (-86%) | 2026-01-25 |
| Loop Detection (P2) | Tool-aware minimal response check | 2026-01-26 |
| SharedExecutionContext (P2) | core/session.py ExecutionContext | 2026-01-26 |
| Execution Engine Reassessed | ~100 lines shared, helpers extracted | 2026-01-26 |

*Details → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)*

### Remaining

| Item | Status | Notes |
|------|--------|-------|
| Integration Test Expansion (P3) | Open | Need adapter, e2e, CLI tests |
| Full StepExecutor | Deferred | High effort, modest gain |

### Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Max file size | 858 lines | <1000 |
| Lint issues | 0 | 0 ✅ |
| Integration test files | 1 | 5+ |

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
