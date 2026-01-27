# Open Questions

Questions requiring human input before work can proceed. Processed by the CONSULT workflow.

> **Purpose**: Bridge between backward stream (code → humans) and forward stream (humans → code)  
> **Workflow**: `sdqctl iterate examples/workflows/consult-questions.conv`  
> **Archive**: Answered questions >14 days → `archive/questions/`

---

## Pending

Questions awaiting human decision or clarification.

| ID | Question | Source | Priority | Asked | Context |
|----|----------|--------|----------|-------|---------|
| OQ-UP-001 | Branching strategies for upstream repos? | UPSTREAM-CONTRIBUTIONS.md | P3 | 2026-01-27 | Different repos use main/master/develop. How should delegate handle? |
| OQ-UP-002 | Auto-create issues before PRs? | UPSTREAM-CONTRIBUTIONS.md | P3 | 2026-01-27 | Some repos require issue first. Default behavior? |
| OQ-UP-003 | CLA requirement handling? | UPSTREAM-CONTRIBUTIONS.md | P3 | 2026-01-27 | How to detect/handle CLA requirements? |
| OQ-UP-004 | Project-specific CI integration? | UPSTREAM-CONTRIBUTIONS.md | P3 | 2026-01-27 | Integration with varied CI systems across repos |
| OQ-UP-005 | Additional consolidation work needed? | LIVE-BACKLOG.md | P3 | 2026-01-27 | Human asked if more consolidation proposals should be created |

---

## Answered

Questions that have been answered and can be routed to work queues.

| ID | Question | Answer | Answered | Routed To |
|----|----------|--------|----------|-----------|
| OQ-LSP-001 | Language server lifecycle? | Hybrid: on-demand with idle timeout + join existing server | 2026-01-27 | proposals/LSP-INTEGRATION.md |
| OQ-LSP-004 | LSP error handling? | Fail fast default, `--lsp-fallback` CLI switch for REFCAT fallback | 2026-01-27 | proposals/LSP-INTEGRATION.md |
| OQ-SE-002 | Self-grooming pattern? | Document in ITERATION-PATTERNS.md, implement in v3 workflow | 2026-01-27 | docs/ITERATION-PATTERNS.md |
| OQ-006 | What is the `--once` flag use case? | Superseded by `--introduction` (cycle 1) and `--until N` (cycles 1-N) | 2026-01-27 | ✅ Complete (2026-01-27) |
| OQ-005 | What should the performance benchmark suite measure? | All: code perf + workflow timing + SDK latency (comprehensive) | 2026-01-27 | ✅ Complete (2026-01-27) |
| OQ-004 | What output should appear at default verbosity? | Spinner, phase name, context %, key events, workflow, cycle/step progress | 2026-01-27 | ✅ Complete (2026-01-27) |
| OQ-001 | CONSULT Phase 4 timeout behavior? | Fail with clear error message | 2026-01-26 | ✅ Complete (2026-01-26) |
| OQ-002 | claude/openai adapters scope? | Stubs with NotImplementedError | 2026-01-26 | ✅ Complete (2026-01-26) |
| OQ-003 | StepExecutor priority? | Defer until after Q-020 (P0) | 2026-01-26 | ✅ Reassessed (2026-01-26): ~100 lines shared, extracted helpers, full StepExecutor deferred |

---

## Question Guidelines

### When to Add Questions

Add to Pending when:
- Implementation requires a design decision you can't make
- Multiple valid approaches exist with different trade-offs
- Scope is ambiguous and affects effort estimate
- Security or compatibility concerns need human review

### Question Format

Good questions include:
1. **Clear ask**: What specific decision is needed?
2. **Context**: Why does this matter? What triggered it?
3. **Options**: If known, list 2-3 approaches with trade-offs
4. **Source**: Link to the file/line that raised the question

### After Answering

When a question is answered:
1. Move from Pending to Answered with date
2. Route the decision:
   - Actionable work → BACKLOG.md Ready Queue
   - Design details → proposals/*.md
   - Documentation → docs/*.md
3. Archive answered questions >14 days old
