# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-23  
> **Purpose**: Track open design questions, implementation work, and future proposals

---

## Current Proposals Status

| Proposal | Status | Blocking Issues |
|----------|--------|-----------------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Draft | ON-FAILURE design decision |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Draft | Blocking vs parallel execution |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Draft | Schema versioning, `--from-json` impl |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Draft | Depends on above three |

---

## Priority 1: Feature Interaction Matrix

**Status**: 🔴 Not started  
**Blocks**: All implementation work

Before implementing any proposal, we need clarity on how features compose:

### Interaction Questions

| Feature A | Feature B | Question | Decision |
|-----------|-----------|----------|----------|
| ELIDE | RUN-BRANCHING | Can ELIDE chain contain ON-FAILURE? | ❓ Proposed: No (parse error) |
| COMPACT | VERIFY | What happens to VERIFY output after compaction? | ❓ |
| ELIDE | VERIFY | Does VERIFY output get elided into next prompt? | ❓ |
| RUN-RETRY | MAX-CYCLES | Does retry count against cycle limit? | ❓ |
| CHECKPOINT | RUN-BRANCHING | Can checkpoint inside ON-FAILURE block? | ❓ |
| PIPELINE (--from-json) | Template vars | Which takes precedence? | ❓ |

### Deliverable

- [ ] Add `docs/FEATURE-INTERACTIONS.md` with interaction matrix
- [ ] Update each proposal with "Interactions" section
- [ ] Resolve blocking questions marked ❓ above

---

## Priority 2: Design Decisions

### 2.1 ON-FAILURE: Full Blocks vs RUN-RETRY Only

**Status**: 🔴 Undecided  
**Proposal**: [RUN-BRANCHING.md](RUN-BRANCHING.md)

**Options**:
- **A) RUN-RETRY only**: Simple retry with count, no arbitrary failure handling
- **B) Full ON-FAILURE blocks**: Arbitrary directives on failure (PROMPT, RUN, etc.)
- **C) Both**: RUN-RETRY for simple cases, ON-FAILURE for complex

**Trade-offs**:
| Option | Complexity | Power | Risk |
|--------|------------|-------|------|
| A | Low | Limited | None |
| B | Medium | High | Infinite loops |
| C | High | Maximum | Complexity |

**Decision**: ❓ TBD

---

### 2.2 VERIFY Execution Model

**Status**: 🔴 Undecided  
**Proposal**: [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md)

**Options**:
- **A) Blocking**: Each VERIFY completes before next directive
- **B) Parallel**: All VERIFYs run concurrently, results collected
- **C) Deferred**: VERIFYs queue up, execute at cycle end

**Decision**: ❓ TBD

---

### 2.3 JSON Schema Versioning

**Status**: 🔴 Undecided  
**Proposal**: [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md)

**Questions**:
- Should `--json` output include schema version?
- How to handle schema evolution (breaking changes)?
- Validation: strict vs lenient mode?

**Decision**: ❓ TBD

---

## Priority 3: Implementation Tasks

### 3.1 `--from-json` Flag

**Status**: 🟡 Designed, not implemented  
**Proposal**: [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md)

```bash
sdqctl render cycle foo.conv --json | transform.py | sdqctl cycle --from-json -
```

- [ ] Parse JSON from stdin
- [ ] Apply template variable overrides
- [ ] Execute workflow
- [ ] Handle validation errors gracefully

---

### 3.2 STPA Workflow Templates

**Status**: 🟡 Proposal exists, no templates  
**Proposal**: [STPA-INTEGRATION.md](STPA-INTEGRATION.md)

- [ ] `workflows/stpa/control-action-audit.conv`
- [ ] `workflows/stpa/trace-verification.conv`
- [ ] `workflows/stpa/gap-analysis.conv`
- [ ] Test with Loop bolus analysis

---

### 3.3 VERIFY Directive Implementation

**Status**: 🟡 Designed, not implemented  
**Proposal**: [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md)

- [ ] VERIFY-REFS (check @-references exist)
- [ ] VERIFY-LINKS (check URLs valid)
- [ ] VERIFY-TRACE (check traceability links)
- [ ] JSON output format

---

## Priority 4: Future Proposals

### 4.1 Batch/Parallel Execution

Run multiple workflows concurrently:
```bash
sdqctl batch --parallel=4 workflows/*.conv
```

**Use case**: Analyze all 16 AID ecosystem projects simultaneously

---

### 4.2 Delta Detection

Identify which UCAs/requirements are affected by code changes:
```bash
sdqctl delta --since=HEAD~5 --scope=stpa
```

**Use case**: CI integration for incremental safety analysis

---

### 4.3 Cross-Project Traceability

UCAs that span multiple projects (e.g., Nightscout ↔ Loop sync issues)

**Use case**: Ecosystem-wide hazard analysis

---

## Completed

- [x] Terminology update: "quine" → "synthesis cycles" (commit 5e57ee3)
- [x] Regulatory context: ISO 14971 + IEC 62304 (commit 93be572)
- [x] GLOSSARY.md with terminology definitions
- [x] SYNTHESIS-CYCLES.md (renamed from QUINE-WORKFLOWS.md)

---

## References

- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
- [SYNTHESIS-CYCLES.md](../docs/SYNTHESIS-CYCLES.md) - Iterative workflow patterns
