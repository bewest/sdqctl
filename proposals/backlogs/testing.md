# Testing Backlog

> **Domain**: Test infrastructure, coverage, fixtures, markers  
> **Parent**: [BACKLOG.md](../BACKLOG.md)  
> **Last Updated**: 2026-01-27

---

## Active Items

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| *(No active items)* | | | | |

---

## Completed

*Migrated from main BACKLOG.md 2026-01-27 (WP-001 step 3)*

| Item | Date | Notes |
|------|------|-------|
| **Test documentation (P3)** | 2026-01-27 | Created tests/README.md: markers, fixtures, parametrization patterns, best practices. |
| **Verify command integration tests (P3)** | 2026-01-27 | Added TestVerifyCommandIntegration (14 tests): refs, links, traceability, coverage, terminology, assertions. |
| **Consult/Pause workflow tests (P3)** | 2026-01-27 | Added TestConsultWorkflows (6 tests) + TestPauseWorkflows (3 tests). Total 1435 tests. |
| **Add CLI integration tests (P2)** | 2026-01-27 | Created test_cli_integration.py with 17 tests: render (4), validate (2), iterate (3), cycle (2), status (2), help (4). |
| **Add end-to-end workflow tests (P2)** | 2026-01-27 | Extended test_workflow_integration.py with 5 new classes: EndToEndWorkflows (2), ErrorHandling (1), Verify (1), Compact (1). Total 1386 tests. |
| **Add parametrized test variants (P3)** | 2026-01-27 | Added TestDirectiveVariants (18 cases) and parametrized TestConsultTimeoutErrors (4 cases) to test_conversation_errors.py. |
| **Extend adapter integration tests (P3)** | 2026-01-27 | Added TestAdapterErrorPaths (5 tests) and TestAdapterRegistryVariants (10 parametrized cases). Total 1364 tests. |
| **Add error path tests (P3)** | 2026-01-27 | Created test_conversation_errors.py with 29 tests for malformed .conv input, invalid directives, missing files, block errors, encoding, edge cases. Total 1329 tests. |
| **Add @pytest.mark.slow (P3)** | 2026-01-26 | Marked 1 slow test (timeout test). Enables `pytest -m "not slow"` for faster runs (~1s savings). |
| **Expand test markers (P3)** | 2026-01-26 | Added tests/integration/conftest.py with auto-marker. 15 integration tests now selectable with `-m integration`. |
| **Session-scoped fixtures + error tests (P3)** | 2026-01-27 | Session-scoped fixtures, 29 error path tests. Total 1314 tests. |
| **Parametrized tests + adapter integration (P3)** | 2026-01-27 | Directive variants (18 cases), adapter error paths (15 tests). Total 1349 tests. |
| **CLI + workflow integration tests (P2)** | 2026-01-27 | CLI integration (17 tests), end-to-end workflow (5 tests). Total 1386 tests. |
| **Flow + Apply integration tests (P3)** | 2026-01-27 | Flow command (6 tests), Apply command (6 tests). Total 1398 tests. |
| **Sessions + Artifact integration tests (P3)** | 2026-01-27 | Sessions command (7 tests), Artifact command (7 tests). Total 1412 tests. |
| **Integration tests Phase 2 (P2)** | 2026-01-26 | +30 tests for iterate_helpers.py (23) and compact_steps.py (7). Total 1240 tests. |
| **Loop detection: tool-aware** | 2026-01-26 | Skip minimal response check if tools called in turn. 2 new tests. |

---

## References

- [tests/README.md](../../tests/README.md) - Test documentation
- [docs/CODE-QUALITY.md](../../docs/CODE-QUALITY.md) - Quality standards
