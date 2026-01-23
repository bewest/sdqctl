# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-23  
> **Purpose**: Track open design questions, implementation work, and future proposals

---

## Current Proposals Status

| Proposal | Status | Notes |
|----------|--------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Ready | Decision: RUN-RETRY first, then ON-FAILURE |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Ready | Decision: Synchronous execution |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Ready | Decision: Add schema_version |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Draft | Depends on above three |

---

## Priority 1: Feature Interaction Matrix

**Status**: ✅ Complete  
**Document**: [docs/FEATURE-INTERACTIONS.md](../docs/FEATURE-INTERACTIONS.md)

All interaction questions resolved:

| Feature A | Feature B | Decision |
|-----------|-----------|----------|
| ELIDE | RUN-BRANCHING | ❌ Parse error (branching not allowed in ELIDE chains) |
| COMPACT | VERIFY | ✅ VERIFY output treated as normal context |
| ELIDE | VERIFY | ✅ VERIFY output embedded in merged prompt |
| RUN-RETRY | MAX-CYCLES | ✅ Retry counts separately from cycle limit |
| CHECKPOINT | RUN-BRANCHING | ✅ Checkpoints allowed inside branches |
| PIPELINE (--from-json) | Template vars | ✅ JSON stdin takes precedence |

---

## Priority 2: Design Decisions

### 2.1 ON-FAILURE: Full Blocks vs RUN-RETRY Only

**Status**: ✅ Decided  
**Proposal**: [RUN-BRANCHING.md](RUN-BRANCHING.md)

**Decision**: **Option C — Both RUN-RETRY and ON-FAILURE blocks**

Implementation order:
1. **Phase 1**: `RUN-RETRY N "prompt"` — simple retry with AI fix attempt
2. **Phase 2**: `ON-FAILURE`/`ON-SUCCESS` blocks — full branching for complex cases

RUN-RETRY covers 80% of use cases with minimal complexity.

---

### 2.2 VERIFY Execution Model

**Status**: ✅ Decided  
**Proposal**: [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md)

**Decision**: **Option A — Blocking (synchronous)**

Each VERIFY completes before the next directive. Results guaranteed available for subsequent PROMPTs.

---

### 2.3 JSON Schema Versioning

**Status**: ✅ Decided  
**Proposal**: [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md)

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

## Priority 3: Implementation Tasks

### 3.1 `--from-json` Flag

**Status**: ✅ Complete  
**Proposal**: [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md)

```bash
sdqctl render cycle foo.conv --json | transform.py | sdqctl cycle --from-json -
```

Implemented:
- [x] Parse JSON from stdin or file
- [x] `ConversationFile.from_rendered_json()` method
- [x] Schema version validation
- [x] Execute workflow from pre-rendered prompts
- [x] Tests and documentation

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
