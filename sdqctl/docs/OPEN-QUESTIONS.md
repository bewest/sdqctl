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
| OQ-004 | What output should appear at default verbosity? | [VERBOSITY-DEFAULTS.md](../proposals/VERBOSITY-DEFAULTS.md) | P3 | 2026-01-26 | Proposal drafted with 4 alternatives. Awaiting decision. |

---

## Answered

Questions that have been answered and can be routed to work queues.

| ID | Question | Answer | Answered | Routed To |
|----|----------|--------|----------|-----------|
| OQ-001 | CONSULT Phase 4 timeout behavior? | Fail with clear error message | 2026-01-26 | ✅ Complete (2026-01-26) |
| OQ-002 | claude/openai adapters scope? | Stubs with NotImplementedError | 2026-01-26 | ✅ Complete (2026-01-26) |
| OQ-003 | StepExecutor priority? | Defer until after Q-020 (P0) | 2026-01-26 | BACKLOG.md P2: StepExecutor (Q-020 done) |

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
