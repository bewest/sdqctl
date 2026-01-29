# Documentation Backlog

> **Domain**: Documentation quality, coherency, autonomous operation optimization  
> **Parent**: [BACKLOG.md](../BACKLOG.md)  
> **Last Updated**: 2026-01-29

---

## Active Items

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| DOC-001 | **Documentation coherency audit** | P2 | 2-3 iterations | Review all docs for autonomous operation optimization |
| DOC-002 | **Deprecation cleanup** | P2 | 1 iteration | Remove/update stale v1 patterns, align with v2/v3 |
| DOC-003 | **HELP-INLINE topic expansion** | P2 | 1 iteration | Add topics for subproject onboarding |
| DOC-004 | **Subproject tooling guide** | P2 | 1 iteration | Guide for externals to use verification/directives |

---

## Backlog Details

### DOC-001: Documentation coherency audit

**Goal**: Systematically review all 29 docs for coherency optimized for autonomous operation.

**Scope** (by section):

| Section | Files | Focus Area |
|---------|-------|------------|
| Core | GETTING-STARTED.md, COMMANDS.md | Entry point clarity, v2 workflow |
| Architecture | ARCHITECTURE.md, IO-ARCHITECTURE.md | Module accuracy, current state |
| Directives | DIRECTIVE-REFERENCE.md, PLUGIN-AUTHORING.md | Complete, v2-aligned |
| Context | CONTEXT-MANAGEMENT.md, CONVERSATION-LIFECYCLE.md | Infinite sessions, compaction |
| Workflows | WORKFLOW-DESIGN.md, ITERATION-PATTERNS.md, SYNTHESIS-CYCLES.md | v2 patterns |
| Verification | VALIDATION-WORKFLOW.md, EXTENDING-VERIFIERS.md, TRACEABILITY-WORKFLOW.md | Plugin integration |
| Adapters | ADAPTERS.md, SDK-LEARNINGS.md | SDK native features |
| Meta | PHILOSOPHY.md, COLOPHON.md, GLOSSARY.md | Consistent terminology |
| Troubleshooting | TROUBLESHOOTING.md, QUIRKS.md | Current issues |
| Domain | NIGHTSCOUT-ECOSYSTEM.md, stpa-severity-scale.md | Accuracy |

**Criteria for each doc**:
1. ✅ Accurate (reflects current implementation)
2. ✅ Coherent (consistent with other docs)
3. ✅ Autonomous-friendly (clear, unambiguous for AI consumption)
4. ✅ v2-aligned (uses iterate, not run as primary)
5. ✅ No stale TODO/FIXME markers

**Output**: Updated docs + coherency issues logged to OPEN-QUESTIONS.md

---

### DOC-002: Deprecation cleanup

**Goal**: Remove or update stale v1 patterns, align with v2 best practices.

**Known issues** (from 2026-01-27 audit):
- 13 docs reference `sdqctl run` as primary (now thin wrapper to `iterate -n 1`)
- 4 docs have TODO/FIXME markers
- 8 docs unchanged since Jan 25

**v2 best practices to enforce**:
- `iterate` as primary command (not `run`)
- `--session-mode` for context management
- Infinite sessions enabled by default
- Plugin directives for custom verification

**v3 patterns to introduce** (proposals):
- HELP-INLINE for mid-workflow guidance
- Custom directive types (DIR-001..003)
- Model requirements abstraction (MODEL-REQUIRES, MODEL-PREFERS)

---

### DOC-003: HELP-INLINE topic expansion

**Goal**: Expand help topics for subproject onboarding and tooling guidance.

**Current topics** (13):
- directives, adapters, workflow, variables, context, examples
- validation, ai, gap-ids, stpa, conformance, nightscout

**Proposed new topics**:

| Topic | Description | Use Case |
|-------|-------------|----------|
| `plugins` | Plugin authoring quick reference | Subprojects extending sdqctl |
| `verify` | Verification directive patterns | Using VERIFY in workflows |
| `iterate` | Iteration patterns and modes | Multi-cycle workflows |
| `compaction` | Context compaction strategies | Long-running sessions |
| `externals` | Working with external repos | Submodule/external project setup |
| `tooling-onboard` | Quick start for new subprojects | Combined onboarding guide |

**Implementation**:
- Add topics to `sdqctl/core/help_topics.py`
- Update `sdqctl help --list` output
- Document in DIRECTIVE-REFERENCE.md

---

### DOC-004: Subproject tooling guide

**Goal**: Create comprehensive guide for external projects (like rag-nightscout-ecosystem-alignment) to:
1. Set up `.sdqctl/directives.yaml` for custom verifiers
2. Use VERIFY directives in their workflows
3. Create custom directive types (when DIR-001..003 complete)
4. Use HELP-INLINE for mid-workflow guidance

**Structure**:
```
docs/SUBPROJECT-SETUP.md
├── Quick Start (5 min setup)
├── Plugin Authoring (custom VERIFY handlers)
├── Workflow Patterns (common .conv patterns)
├── Verification Integration (VERIFY in CI)
├── Custom Directives (future: DIR-001..003)
└── Troubleshooting
```

**Dependencies**: 
- Partially blocked on DIR-001..003 for custom directive types section
- Can proceed with VERIFY plugin and HELP-INLINE sections now

---

## Priority Ordering

1. **DOC-002** (Deprecation cleanup) - Foundation for coherency
2. **DOC-003** (HELP-INLINE expansion) - Enables DOC-004
3. **DOC-004** (Subproject guide) - High user value
4. **DOC-001** (Full coherency audit) - Comprehensive review

---

## Completed

| Item | Date | Notes |
|------|------|-------|
| DOC-002 Phase 1: GETTING-STARTED.md | 2026-01-29 | Updated all `run` → `iterate`, added deprecation note |
| Initial documentation structure | 2026-01-21 | 29 docs created |
| Documentation audit | 2026-01-27 | Issues logged in BACKLOG.md |

---

## References

- [HELP-INLINE.md](../HELP-INLINE.md) - HELP-INLINE proposal
- [PLUGIN-SYSTEM.md](../PLUGIN-SYSTEM.md) - Plugin system
- [DIRECTIVE-REFERENCE.md](../../docs/DIRECTIVE-REFERENCE.md) - Directive catalog
- [backlogs/directives.md](directives.md) - DIR-001..003 custom directive types
