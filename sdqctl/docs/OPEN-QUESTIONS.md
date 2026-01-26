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
| OQ-001 | What should CONSULT Phase 4 timeout behavior be? | proposals/CONSULT-DIRECTIVE.md | P2 | 2026-01-26 | Options: return partial, retry, fail |
| OQ-002 | Should claude/openai adapters be full implementations or stubs? | proposals/BACKLOG.md | P2 | 2026-01-26 | Stubs would raise NotImplementedError |
| OQ-003 | StepExecutor priority - implement now or defer? | proposals/BACKLOG.md | P2 | 2026-01-26 | Medium effort, uses ExecutionContext |
| OQ-004 | What are "default verbosity key actions"? | proposals/BACKLOG.md | P3 | 2026-01-26 | Item lacks scope. What specific actions should show at verbosity=0? |

---

## Answered

Questions that have been answered and can be routed to work queues.

| ID | Question | Answer | Answered | Routed To |
|----|----------|--------|----------|-----------|
| | | | | |

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
