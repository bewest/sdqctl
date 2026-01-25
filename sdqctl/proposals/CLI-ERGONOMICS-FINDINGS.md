# Documentation & Open Questions from CLI Ergonomics Session

> **Date**: 2026-01-23  
> **Source**: Planning session for CLI ergonomics workflows

---

## Documentation Gaps Identified

### 1. CHECKPOINT Only Works with `iterate` ❗

**Gap**: Not clearly documented that `run` ignores CHECKPOINT directives.

**Current state**: GETTING-STARTED.md says `run` is for "testing a workflow design" but doesn't mention CHECKPOINT limitation.

**Recommendation**: Add explicit callout:

```markdown
> **Note**: CHECKPOINT directives are only processed by `iterate`. 
> Use `sdqctl run` for quick tests, but switch to `iterate` for 
> workflows where you need resumability.
```

**Files to update**:
- docs/GETTING-STARTED.md (run vs cycle section)
- README.md (command table)

---

### 2. Sequential Workflow Execution Pattern

**Gap**: No documentation on running multiple workflows in sequence.

**Discovery**: Running 3 workflows sequentially completed 50% faster than predicted because context fully resets between runs.

**Recommendation**: Add to SYNTHESIS-CYCLES.md or CONTEXT-MANAGEMENT.md:

```markdown
### Sequential Workflow Execution

For multi-deliverable work, run workflows sequentially:

\`\`\`bash
sdqctl run 01-design.conv --adapter copilot && \
sdqctl run 02-implement.conv --adapter copilot && \
sdqctl run 03-verify.conv --adapter copilot
\`\`\`

**Benefits**:
- Fresh context for each workflow
- Faster than predicted (no context degradation)
- Each workflow focused on one deliverable

**When to use**: When deliverables are independent and don't need shared context.
\`\`\`

---

### 3. Throughput Expectations

**Gap**: No guidance on expected output volume.

**Discovery**: 
- Predicted ~300 lines output
- Actual: 2,229 lines (7x more)
- Throughput: ~110 lines/minute

**Recommendation**: Add to CONTEXT-MANAGEMENT.md:

```markdown
### Expected Throughput

With well-structured workflows (4-phase pattern, strategic COMPACTs):

| Metric | Typical Range |
|--------|---------------|
| Lines per workflow | 500-2000 |
| Throughput | 50-150 lines/min |
| Duration per phase | 3-5 min |

**Factors affecting throughput**:
- Context file size (more input = more processing)
- COMPACT frequency (more = fresher context)
- Task complexity (research vs implementation)
```

---

### 4. run vs RUN Disambiguation

**Gap**: Potential confusion between `sdqctl run` command and `RUN` directive.

**Current state**: CLI-ERGONOMICS.md proposes renaming to `yield` but no interim documentation.

**Recommendation**: Add clarification to GLOSSARY.md:

```markdown
### run (command) vs RUN (directive)

**`sdqctl run`** - CLI command to execute a workflow with an AI agent.
Yields control to the agent for the duration of the conversation.

**`RUN`** - Directive in .conv files to execute shell commands.
Example: `RUN pytest tests/ -v`

These are **unrelated** despite sharing a name. The CLI command orchestrates
AI conversations; the directive executes local shell commands.
```

---

## Open Questions Identified

### Q1: Should `run` process CHECKPOINT for consistency?

**Context**: Currently `run` ignores CHECKPOINT. Users may expect it to work.

**Options**:
- A) Keep as-is (run is lightweight, cycle is full-featured)
- B) Make run process CHECKPOINT (less confusion, more feature parity)
- C) Emit warning when run encounters CHECKPOINT

**Recommendation**: Option C - warn users to switch to cycle

---

### Q2: Should we document estimation heuristics?

**Context**: We predicted 30-40 min, actual was 20 min. Predictions help planning.

**Options**:
- A) Add estimation guide (phases × 5 min baseline)
- B) Add `sdqctl estimate workflow.conv` command
- C) Leave as user experience

**Recommendation**: Option A - lightweight documentation

---

### Q3: Over-delivery pattern - feature or concern?

**Context**: Predicted ~300 lines, got 2,229. Agent produced comprehensive implementation.

**Questions**:
- Is this desirable? (More complete, but may over-engineer)
- Should we add MAX-OUTPUT directive to limit scope?
- Is this a prompt engineering issue?

**Recommendation**: Document as feature; add note about scoping prompts explicitly if minimal output desired.

---

### Q4: Help system verification needed

**Context**: Workflows created `sdqctl/commands/help.py` (946 lines) but we couldn't test it due to environment issues.

**Action needed**:
```bash
pip install -e .
sdqctl help
sdqctl help guidance elide
pytest tests/test_help_command.py -v
```

---

## Lessons to Document

### Lesson #28: Sequential runs combine well
Multiple workflows in sequence complete faster than single large workflow because context fully resets.

### Lesson #29: ELIDE + RUN synergy
Pattern: `RUN → COMPACT → ELIDE → PROMPT "analyze"` efficiently processes test output.

### Lesson #30: Over-delivery is common
Structured workflows with clear specs tend to produce comprehensive implementations. Scope explicitly if minimal output desired.

---

## Proposed Actions

### Immediate (P1)
- [ ] Test help command works
- [x] Add CHECKPOINT note to run vs cycle docs
- [x] Add run vs RUN clarification to GLOSSARY.md

### Soon (P2)
- [x] Document sequential workflow pattern
- [x] Add throughput expectations
- [x] Add lessons #28-31 to SYNTHESIS-CYCLES.md

### Later (P3)
- [ ] Decide on Q1 (run + CHECKPOINT warning)
- [ ] Decide on estimation tooling
- [ ] Review rename assessment findings

---

## References

- reports/cli-ergonomics-experience-2026-01-23.md
- proposals/CLI-ERGONOMICS.md
- proposals/BACKLOG.md
