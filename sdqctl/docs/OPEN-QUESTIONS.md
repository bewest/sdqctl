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
| *(No pending questions)* | | | | | |

---

## Answered

Questions that have been answered and can be routed to work queues.

| ID | Question | Answer | Answered | Routed To |
|----|----------|--------|----------|-----------|
| OQ-006 | What is the `--once` flag use case? | Superseded by `--introduction` (cycle 1) and `--until N` (cycles 1-N) | 2026-01-27 | ✅ Complete (2026-01-27) |
| OQ-005 | What should the performance benchmark suite measure? | All: code perf + workflow timing + SDK latency (comprehensive) | 2026-01-27 | Ready Queue #1 |
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
