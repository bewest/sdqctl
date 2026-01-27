# Design Decisions

This document summarizes all major design decisions made during sdqctl development.
For detailed rationale, see the linked ADRs or proposals.

---

## Decision Summary

| ID | Decision | Status | Date | ADR |
|----|----------|--------|------|-----|
| D-001 | ON-FAILURE: Both RUN-RETRY and full blocks | Accepted | 2026-01-23 | [ADR-001](decisions/ADR-001-on-failure-strategy.md) |
| D-002 | VERIFY execution: Blocking (synchronous) | Accepted | 2026-01-23 | [ADR-002](decisions/ADR-002-verify-execution-model.md) |
| D-003 | JSON schema versioning with `schema_version` field | Accepted | 2026-01-23 | [ADR-003](decisions/ADR-003-json-schema-versioning.md) |
| D-004 | SDK session persistence via adapter methods | Accepted | 2026-01-25 | [ADR-004](decisions/ADR-004-sdk-session-persistence.md) |
| D-005 | Compaction: CLI flags override directives override defaults | Accepted | 2026-01-25 | [ADR-005](decisions/ADR-005-compaction-priority.md) |
| D-006 | Artifact IDs: Allow both scoped and global, prefer scoped for multi-project | Accepted | 2026-01-24 | — |
| D-007 | Verification strictness: Configurable with `--strict`, default warn | Accepted | 2026-01-24 | — |
| D-008 | REFCAT directive for code excerpt injection | Accepted | 2026-01-24 | — |
| D-009 | HELP directive for agent-accessible documentation | Accepted | 2026-01-24 | — |
| D-010 | LSP/semantic extraction: Deferred to future work | Deferred | 2026-01-24 | — |
| D-011 | Documentation reorganization (human vs AI): Deferred | Deferred | 2026-01-24 | — |
| D-012 | Time-based estimates replaced with complexity labels | Accepted | 2026-01-25 | — |
| D-013 | Feature interactions: ELIDE incompatible with branching | Accepted | 2026-01-25 | — |
| D-014 | Code complexity thresholds: >500 lines = plan split, >1000 = required | Accepted | 2026-01-25 | — |
| D-015 | Backlog organization: Completed work archived, active items only | Accepted | 2026-01-25 | — |

---

## Decision Details

### D-001: ON-FAILURE Strategy

**Status**: Accepted  
**Date**: 2026-01-23  
**Proposal**: [RUN-BRANCHING.md](../proposals/RUN-BRANCHING.md)

**Decision**: Implement both RUN-RETRY and ON-FAILURE blocks.

- **Phase 1**: `RUN-RETRY N "prompt"` — simple retry with AI fix attempt
- **Phase 2**: `ON-FAILURE`/`ON-SUCCESS` blocks — full branching for complex cases

RUN-RETRY covers 80% of use cases with minimal complexity.

---

### D-002: VERIFY Execution Model

**Status**: Accepted  
**Date**: 2026-01-23  
**Proposal**: [VERIFICATION-DIRECTIVES.md](../proposals/VERIFICATION-DIRECTIVES.md)

**Decision**: Blocking (synchronous) execution.

Each VERIFY completes before the next directive. Results guaranteed available for subsequent PROMPTs.

---

### D-003: JSON Schema Versioning

**Status**: Accepted  
**Date**: 2026-01-23  
**Proposal**: [PIPELINE-ARCHITECTURE.md](../proposals/PIPELINE-ARCHITECTURE.md)

**Decision**: Add explicit `schema_version` field to JSON output.

```json
{
  "schema_version": "1.0",
  "workflow": "...",
  ...
}
```

Versioning policy: major.minor where major = breaking changes.

---

### D-004: SDK Session Persistence

**Status**: Accepted  
**Date**: 2026-01-25  
**Proposal**: [SDK-SESSION-PERSISTENCE.md](../proposals/SDK-SESSION-PERSISTENCE.md)

**Decision**: Implement session persistence via adapter methods.

- `list_sessions()` - List available sessions
- `resume_session(session_id, config)` - Resume a session
- `delete_session(session_id)` - Delete a session
- `SESSION-NAME` directive for workflow files
- `sessions resume` CLI command

---

### D-005: Compaction Priority

**Status**: Accepted  
**Date**: 2026-01-25  
**Proposal**: [SDK-INFINITE-SESSIONS.md](../proposals/SDK-INFINITE-SESSIONS.md)

**Decision**: Layered priority for compaction settings.

Priority order (highest to lowest):
1. CLI flags (`--compact`, `--compaction-min`)
2. Workflow directives (`COMPACT`, `COMPACTION-MIN`, `COMPACTION-THRESHOLD`)
3. Defaults

---

### D-006: Artifact ID Scoping

**Status**: Accepted  
**Date**: 2026-01-24  
**Proposal**: [ARTIFACT-TAXONOMY.md](../proposals/ARTIFACT-TAXONOMY.md)

**Decision**: Allow both scoped and global IDs, prefer scoped for multi-project.

| Context | Format | Example |
|---------|--------|---------|
| Single project | Simple | `REQ-001`, `UCA-015` |
| Cross-project refs | Scoped | `REQ-LOOP-001`, `UCA-TRIO-015` |
| Ecosystem docs | Scoped | `GAP-XDRIP-003` |

The `traceability` verifier detects collisions when simple IDs are used across projects.

---

### D-007: Verification Strictness

**Status**: Accepted  
**Date**: 2026-01-24  
**Proposal**: [ARTIFACT-TAXONOMY.md](../proposals/ARTIFACT-TAXONOMY.md)

**Decision**: Configurable with `--strict` flag, default warn.

```bash
# Default: warn on orphans, exit 0
sdqctl verify traceability

# Strict: fail on orphans, exit 1 (for CI)
sdqctl verify traceability --strict
```

---

### D-008: REFCAT Directive

**Status**: Accepted  
**Date**: 2026-01-24  
**Proposal**: [REFCAT-DESIGN.md](../proposals/REFCAT-DESIGN.md)

**Decision**: Implement REFCAT directive for code excerpt injection.

```dockerfile
REFCAT @sdqctl/core/context.py#L182-L194
REFCAT loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

---

### D-009: HELP Directive

**Status**: Accepted  
**Date**: 2026-01-24  
**Proposal**: [BACKLOG.md §Help System Gap](../proposals/BACKLOG.md)

**Decision**: Implement HELP directive for agent-accessible documentation.

```dockerfile
HELP directives      # Inject directive reference
HELP workflow        # Inject workflow design guide
```

---

### D-010: LSP/Semantic Extraction

**Status**: Deferred  
**Date**: 2026-01-24  
**Proposal**: [REFCAT-DESIGN.md §1.3](../proposals/REFCAT-DESIGN.md)

**Decision**: Defer LSP integration to future work.

Semantic extractors for language-aware content extraction are documented as aspirational. Consider tree-sitter as lighter-weight alternative.

---

### D-011: Documentation Reorganization

**Status**: Deferred  
**Date**: 2026-01-24

**Decision**: Keep flat documentation structure for now.

Proposed split into `reference/` (AI-optimized), `guides/` (human-optimized), and `concepts/` (shared) is deferred until docs exceed 20 files or AI integration issues emerge.

---

### D-012: Time-Based Estimates

**Status**: Accepted  
**Date**: 2026-01-25

**Decision**: Replace time-based effort estimates with complexity labels.

- **Low**: Few files, well-understood pattern
- **Moderate**: Multiple files/components
- **High**: Many files, architectural changes

Replaced hours/days/weeks in 10 documentation files.

---

### D-013: Feature Interaction Matrix

**Status**: Accepted  
**Date**: 2026-01-25  
**Document**: [docs/FEATURE-INTERACTIONS.md](../docs/FEATURE-INTERACTIONS.md)

**Decision**: Document and enforce feature interaction rules.

Key interactions:
- ELIDE + RUN-BRANCHING: ❌ Parse error (branching not allowed in ELIDE chains)
- COMPACT + VERIFY: ✅ VERIFY output treated as normal context
- RUN-RETRY + MAX-CYCLES: ✅ Retry counts separately from cycle limit

---

### D-014: Code Complexity Thresholds

**Status**: Accepted  
**Date**: 2026-01-25  
**Document**: [docs/CODE-QUALITY.md](../docs/CODE-QUALITY.md)

**Decision**: Establish file size thresholds for maintainability.

| Threshold | Action |
|-----------|--------|
| >300 lines | Consider if logic can be split |
| >500 lines | Plan refactoring |
| >1000 lines | Split required |

---

### D-015: Backlog Organization

**Status**: Accepted  
**Date**: 2026-01-25

**Decision**: Keep BACKLOG.md focused on active work only.

- Completed work → `archive/` (session logs, migration snapshots)
- Design decisions → `archive/DECISIONS.md`
- Reference material → `docs/` (DIRECTIVE-REFERENCE.md, CODE-QUALITY.md)
- Active items only remain in BACKLOG.md

Target: <300 lines in BACKLOG.md

---

## References

- [proposals/](../proposals/) - Original proposals with full context
- [BACKLOG.md](../proposals/BACKLOG.md) - Active work items
- [decisions/](decisions/) - Architecture Decision Records
