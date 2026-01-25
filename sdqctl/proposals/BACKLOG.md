# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-25  
> **Purpose**: Track active work items and proposals only  
> **Archive**: Completed work → [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)

---

## Active Priorities

### P0: Critical (None)

No critical items.

### P1: High

| Item | Effort | Notes |
|------|--------|-------|
| ~~Split `run()` function (~1000 lines)~~ | ~~High~~ | Superseded by iterate consolidation |

### P2: Medium

| Item | Effort | Notes |
|------|--------|-------|
| **Consolidate run+cycle → iterate** | Medium | See [ITERATE-CONSOLIDATION.md](ITERATE-CONSOLIDATION.md) ✅ Ready |
| Extract StepExecutor from iterate.py | Medium | See [Architecture Roadmap](#architecture-roadmap) |
| Create shared ExecutionContext dataclass | Low | Unify adapter initialization |
| Audit refcat.py path handling | Low | Verify traversal prevention |
| Add RUN-ENV secret masking | Low | Mask env vars in logs |
| CONSULT-DIRECTIVE Phase 4 | Low | Timeout, partial save refinements |
| claude/openai adapter stubs | Medium | Implement or clarify scope in ADAPTERS.md |
| Fix RUN-ASYNC process cleanup leak | Low | Add finally block to terminate orphan processes |
| Extract common utilities (`utils/io.py`) | Low | Deduplicate ~50 JSON output + 65 file I/O patterns |
| Enhance VerifierBase with shared scanning | Low | Move repeated file scanning logic to base class |
| Add error handling decorator pattern | Low | `@handle_io_errors` for common exception wrapping |

### P3: Low

| Item | Effort | Notes |
|------|--------|-------|
| Fix E501 lint issues (192 remaining) | Low | Refactor during normal development |
| Review F841 unused variables (5) | Low | Needs manual review |
| Split conversation.py (~1768 lines) | High | parser.py, validator.py, directives.py |
| Modularize copilot.py (~1000 lines) | Medium | events.py, stats.py, session.py |
| Add integration tests | Medium | Beyond loop stress testing |
| Add py.typed marker | Low | Enable downstream type checking |
| Default verbosity key actions | Low | Q-004: show key actions without `-v` |
| Test parametrization and markers | Low | `@pytest.mark.unit/integration` |
| Performance benchmark suite | Medium | Track regressions |
| Add `test_exceptions.py` | Low | Test exit codes, JSON serialization |
| Add `test_renderer_core.py` | Low | Unit tests for RenderedPrompt, RenderedCycle |
| Add `test_command_utils.py` | Low | Test `run_async()` function |
| Error path test coverage | Medium | File I/O errors, permissions, timeouts |

### Future (Unstarted)

| Item | Source | Notes |
|------|--------|-------|
| LSP support for refcat | References | Language Server Protocol for IDE integration |
| Interactive help (`--interactive`) | References | Browsable help system |
| refcat usage patterns example | P3 Workflow Examples | Cross-repo context injection |

---

## Architecture Roadmap

> **Source**: Code review session 2026-01-25  
> **Objective**: Improve maintainability without disrupting features

### Execution Engine Extraction (P2)

**Problem**: `run.py` and `cycle.py` duplicate step execution logic (~500 lines overlap)

**Solution**: Create `core/executor.py`

```python
class StepExecutor:
    """Unified execution engine for workflow steps."""
    async def execute_prompt(self, step, session, adapter) -> StepResult
    async def execute_run(self, step, session, config) -> StepResult
    async def execute_verify(self, step, session) -> StepResult
    async def execute_compact(self, step, session, adapter) -> StepResult
```

| Task | Effort | Status |
|------|--------|--------|
| Design StepExecutor interface | Low | 🔲 Open |
| Extract common execution logic from run.py | Medium | 🔲 Open |
| Refactor cycle.py to use StepExecutor | Medium | 🔲 Open |
| Add StepExecutor tests | Medium | 🔲 Open |

### Shared ExecutionContext (P2)

**Problem**: Adapter initialization repeated in run.py, cycle.py, apply.py

**Solution**: Create `ExecutionContext` dataclass

```python
@dataclass
class ExecutionContext:
    adapter: AdapterBase
    session: Session
    conv: ConversationFile
    verbosity: int
    console: Console
```

| Task | Effort | Status |
|------|--------|--------|
| Define ExecutionContext in core/session.py | Low | 🔲 Open |
| Refactor run.py to use ExecutionContext | Low | 🔲 Open |
| Refactor cycle.py to use ExecutionContext | Low | 🔲 Open |
| Refactor apply.py to use ExecutionContext | Low | 🔲 Open |

### ConversationFile Split (P3)

**Problem**: `conversation.py` is 1,768 lines with mixed responsibilities

**Proposed structure**:
```
core/conversation/
  __init__.py      # Re-exports ConversationFile
  parser.py        # DirectiveParser (line-by-line parsing)
  validator.py     # ConversationValidator (semantic checks)
  directives.py    # DirectiveType enum + DirectiveSpec
  templates.py     # Template variable substitution
```

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

| Metric | Current | Target |
|--------|---------|--------|
| Max file size | 1,768 lines | <500 lines |
| Lint issues (E501/F841) | 197 | 0 |
| Integration test files | 1 | 5+ |
| Code duplication (run/cycle) | ~500 lines | <100 lines |

---

## Proposals Status

| Proposal | Status | Notes |
|----------|--------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | ✅ Complete | RUN-RETRY + ON-FAILURE/ON-SUCCESS |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | ✅ Complete | All 4 phases |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | ✅ Complete | --from-json + schema_version |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | ✅ Complete | Templates + traceability verifier |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | ✅ Complete | Help implemented |
| [ITERATE-CONSOLIDATION](ITERATE-CONSOLIDATION.md) | 🟡 Ready | run+cycle → iterate |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | ✅ Complete | All 4 phases |
| [CONSULT-DIRECTIVE](CONSULT-DIRECTIVE.md) | Partial | Phase 4 pending (timeout, partial save) |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | ✅ Complete | Taxonomy + CLI |
| [ERROR-HANDLING](ERROR-HANDLING.md) | ✅ Complete | All phases |
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | ✅ Complete | Native SDK compaction |
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | ✅ Complete | sessions resume + SESSION-NAME |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | ✅ Complete | Adapter methods + status |

---

## Security Considerations

Documented in [`docs/SECURITY-MODEL.md`](../docs/SECURITY-MODEL.md).

| Issue | Severity | Notes |
|-------|----------|-------|
| Shell injection via ALLOW-SHELL | HIGH | Documented; disabled by default |
| Path traversal (refcat.py) | MEDIUM | Audit pending (P2) |
| RUN_ENV allows LD_PRELOAD | MEDIUM | Consider whitelist |
| OUTPUT-FILE path injection | LOW | Validate paths |
| RUN-ASYNC resource leak | MEDIUM | Orphan processes; fix pending (P2) |

---

## Test Quality Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| No error path tests | Unknown failure behavior | 🔲 Open |
| Missing parametrization | Incomplete variant coverage | 🔲 Open |
| No test markers | Can't run selective tests | 🔲 Open |
| Fixtures not scoped | Slow test runs | 🔲 Open |
| No `test_exceptions.py` | Exit codes untested | 🔲 Open |
| No `test_renderer_core.py` | Renderer logic untested | 🔲 Open |
| No `test_command_utils.py` | `run_async()` untested | 🔲 Open |

---

## References

> **Note**: Cross-reference with QUIRKS.md for quirk-related backlog items.

- [archive/](../archive/) - Archived session logs and design decisions
- [archive/2026-01-backlog-migration.md](../archive/2026-01-backlog-migration.md) - Completed items snapshot
- [docs/DIRECTIVE-REFERENCE.md](../docs/DIRECTIVE-REFERENCE.md) - Complete directive catalog
- [docs/CODE-QUALITY.md](../docs/CODE-QUALITY.md) - Code quality standards
- [docs/PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Workflow design principles
- [docs/QUIRKS.md](../docs/QUIRKS.md) - Known quirks (all resolved)

**Future ideas**: LSP support for refcat, interactive help system
