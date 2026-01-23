# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-23 (Session complete)  
> **Purpose**: Track open design questions, implementation work, and future proposals

---

## Current Proposals Status

| Proposal | Status | Notes |
|----------|--------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Ready | Decision: RUN-RETRY first, then ON-FAILURE |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Ready | Decision: Synchronous execution |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Ready | Decision: Add schema_version |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Draft | Depends on above three |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | Draft | Help system, command taxonomy, run rename investigation |

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

**Status**: ✅ Complete  
**Proposal**: [STPA-INTEGRATION.md](STPA-INTEGRATION.md)

- [x] `workflows/stpa/control-action-audit.conv` - UCA discovery
- [x] `workflows/stpa/trace-verification.conv` - Traceability validation
- [x] `workflows/stpa/gap-analysis.conv` - Iterative gap closure
- [x] `workflows/stpa/README.md` - Documentation

---

### 3.3 VERIFY Directive Implementation

**Status**: ✅ Complete  
**Proposal**: [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md)

Phase 1 (Core Library) ✅:
- [x] `sdqctl/verifiers/base.py` - VerificationResult, VerificationError, Verifier protocol
- [x] `sdqctl/verifiers/refs.py` - RefsVerifier (check @-references)
- [x] `sdqctl/verifiers/__init__.py` - VERIFIERS registry
- [x] `tests/test_verifiers.py` - 11 tests

Phase 2 (CLI Commands) ✅:
- [x] `sdqctl verify refs` - Reference verification command
- [x] `sdqctl verify all` - Run all verifications

Phase 3 (Directive Parsing) ✅:
- [x] VERIFY, VERIFY-ON-ERROR, VERIFY-OUTPUT, VERIFY-LIMIT directives
- [x] ConversationStep with verify_type and verify_options
- [x] 8 parsing tests

Phase 4 (Execution Integration) ✅:
- [x] Run verifiers during workflow execution
- [x] Context injection based on verify_output setting
- [x] Error handling based on verify_on_error setting

---

## Priority 4: Future Proposals

### 4.1 CLI Ergonomics (NEW)

**Status**: Draft  
**Proposal**: [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md)

Three work areas:
- **Help system**: `sdqctl help guidance [topic]` for discoverable documentation
- **Command taxonomy**: Classify SDK-invoking vs tooling commands
- **Run rename investigation**: Assess `yield`/`do`/`exec` as alternatives

Implementation workflows:
```bash
sdqctl cycle examples/workflows/cli-ergonomics/01-help-system.conv --adapter copilot
sdqctl cycle examples/workflows/cli-ergonomics/02-tooling-gap-analysis.conv --adapter copilot
sdqctl cycle examples/workflows/cli-ergonomics/03-run-rename-assessment.conv --adapter copilot
```

---

### 4.2 Batch/Parallel Execution

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

### Session 2026-01-23 (Documentation)

- [x] **Documentation update** - Added VERIFY directive and CLI docs (commit 6efe526)
  - VERIFY directives in README table
  - `sdqctl verify` CLI command documented
  - STPA workflows referenced in GETTING-STARTED
  - Recently Completed section updated

### Session 2026-01-23 (Phase 3-4)

- [x] **VERIFY directive parsing** - Phase 3 complete (commit 52ec86c)
- [x] **VERIFY execution integration** - Phase 4 complete (commit 3e29120)
- [x] VERIFY directive: all 4 phases COMPLETE, 19 tests total

### Session 2026-01-23 (Phase 1-2)

- [x] **STPA workflow templates** - 3 workflows + README (commit 1f9fc31)
- [x] **Verify CLI commands** - `sdqctl verify refs`, `sdqctl verify all` (commit 816a7db)
- [x] **Verifier core library** - base.py, refs.py, 10 tests

### Session 2026-01-23

- [x] **Feature Interaction Matrix** - Resolved all blocking design decisions (COMPACT+VERIFY, RUN-BRANCH+CHECKPOINT)
- [x] **RUN-RETRY directive** - AI-assisted retry on command failure (commit 3f75074)
- [x] **--from-json flag** - Pipeline input for cycle command (commit 90242c5)
- [x] **Schema versioning** - Added schema_version to JSON output
- [x] Design decisions documented: ON-FAILURE strategy, VERIFY execution model

### Earlier

- [x] Terminology update: "quine" → "synthesis cycles" (commit 5e57ee3)
- [x] Regulatory context: ISO 14971 + IEC 62304 (commit 93be572)
- [x] GLOSSARY.md with terminology definitions
- [x] SYNTHESIS-CYCLES.md (renamed from QUINE-WORKFLOWS.md)

---

## References

- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
- [SYNTHESIS-CYCLES.md](../docs/SYNTHESIS-CYCLES.md) - Iterative workflow patterns
