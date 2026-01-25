# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-25 (Documentation gap deep review)  
> **Purpose**: Track open design questions, implementation work, and future proposals  
> **Archive**: Completed session logs and design decisions → [`archive/`](../archive/)

---

## Executive Summary: Tooling Gap Analysis

**Analysis Date**: 2026-01-23 | **Phases Completed**: 4/4  
**SDK v2 Analysis**: 2026-01-24 | **New Proposals**: 3 (**Infinite Sessions** ✅, **Session Persistence** ✅, Metadata APIs ✅)
**MODEL-REQUIREMENTS**: 2026-01-25 | All 4 phases complete (Registry → CLI → Adapter → Operator config)
**Q-014/Q-015 Fix**: 2026-01-25 | Event handler leak fixed, accumulate mode stable

Note: remember to cross reference and evaluate priorities across roadmaps.
SDK-SESSION-PERSISTENCE complete (2026-01-25): Phase 1-4 all implemented.

### Tooling Commands Status (Non-SDK)

All 8 proposed tooling commands are **fully implemented**:

| Command | Purpose | Subcommands | Status |
|---------|---------|-------------|--------|
| `render` | Preview prompts (no AI) | `run`, `cycle`, `apply`, `file` | ✅ Complete |
| `verify` | Static verification | `refs`, `links`, `traceability`, `all` | ✅ Complete (3 verifiers) |
| `validate` | Syntax checking | - | ✅ Complete |
| `show` | Display parsed workflow | - | ✅ Complete |
| `status` | Session/system info | `--adapters`, `--sessions` | ✅ Complete |
| `sessions` | Session management | `list`, `delete`, `cleanup` | ✅ Complete (2026-01-25) |
| `init` | Project initialization | - | ✅ Complete |
| `help` | Documentation access | 12 commands, 6 topics | ✅ Complete |

### Priority Recommendations
* ~~[SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md)~~ | ✅ Complete | Phase 1-4 | Native SDK compaction for cycle mode
* ~~[SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md)~~ | ✅ Complete | Phase 1-4 | `sessions resume` + `SESSION-NAME` directive
* ~~Q-014/Q-015 Event handler fix~~ | ✅ Complete | Accumulate mode now stable

#### P0: Documentation Gaps (Quick Wins)

| Gap | Location | Complexity | Status |
|-----|----------|------------|--------|
| ~~Pipeline schema docs~~ | `docs/PIPELINE-SCHEMA.md` | Low | ✅ Complete |
| ~~Verifier extension guide~~ | `docs/EXTENDING-VERIFIERS.md` | Low | ✅ Complete |

#### P1: Verifier Expansion (High Value)

| Verifier | Use Case | Complexity | Status |
|----------|----------|------------|--------|
| `traceability` | STPA REQ→SPEC→TEST validation | Moderate | ✅ Complete |
| `links` | URL/file link checking | Low | ✅ Complete |
| `terminology` | Deprecated terms + capitalization | Low | ✅ Complete |

#### P2: Directive Implementation (Deferred)

| Directive | Proposal | Complexity | Recommendation |
|-----------|----------|------------|----------------|
| `ON-FAILURE` | RUN-BRANCHING | High | ✅ Implemented 2026-01-24 |
| `ON-SUCCESS` | RUN-BRANCHING | High | ✅ Implemented 2026-01-24 |
| `VERIFY-TRACE` | STPA-INTEGRATION | Medium | ✅ Implemented 2026-01-24 |

### Key Findings

1. **All tooling commands implemented** - 8 CLI commands including new `sessions`
2. **Verifier infrastructure complete** - 5 verifiers: `refs`, `links`, `traceability`, `terminology`, `assertions`
3. **Help system exceeds proposal** - 12 commands + 6 topics
4. **Session management complete** - `sessions list|delete|cleanup` (Phase 2)

### Next Priorities

| Priority | Item | Effort | Notes |
|----------|------|--------|-------|
| P2 | Document `artifact` command | Medium | User-facing docs for traceability IDs |
| P2 | [CONSULT-DIRECTIVE Phase 4](CONSULT-DIRECTIVE.md) | Low | Refinements (timeout, partial save) - needs design review |
| P3 | STPA template variables | Low | Future work |
| P3 | CI/CD workflow examples | Low | GitHub Actions integration |

**Completed this session:**
- ~~Add `refcat` to GETTING-STARTED.md~~ ✅ (already present)
- ~~Create `docs/COMMANDS.md`~~ ✅ (already complete)
- ~~Create `docs/ADAPTERS.md`~~ ✅ 2026-01-25
- ~~MODEL-REQUIREMENTS Phase 3-4~~ ✅ 2026-01-25
- ~~Q-014/Q-015 root cause analysis~~ ✅ 2026-01-25 (Line 655 handler leak)
- ~~Q-014: Event handler multiplexing~~ ✅ 2026-01-25 (Handler registered once per session)
- ~~Q-015: Duplicate tool calls~~ ✅ 2026-01-25 (Fixed by Q-014)
- ~~Q-013: Unknown tool names regression~~ ✅ 2026-01-25 (Root cause was Q-014)

### Research Items (2026-01-25)

| ID | Topic | Hypothesis | Evidence | Status |
|----|-------|------------|----------|--------|
| ~~R-001~~ | ~~SDK 2 intent reading~~ | ~~SDK 2 may provide tool info differently~~ | Q-013 root cause was Q-014 handler leak | ✅ **RESOLVED** |
| ~~R-002~~ | ~~Accumulate mode stability~~ | ~~Event handlers accumulate across cycles~~ | 25x log duplication, 3667 turns for 5 cycles | ✅ **FIXED** |
| ~~R-003~~ | ~~Event subscription cleanup~~ | ~~`send()` lacks handler cleanup~~ | Line 655: handler now registered once | ✅ **FIXED** |

**Resolution (2026-01-25):** Fixed by registering event handler once per session with `stats.handler_registered` flag.
Handler uses session-level `_send_*` state that resets each `send()` call.

---

## Current Proposals Status

| Proposal | Status | Implementation | Notes |
|----------|--------|----------------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Implemented | Phase 1-2 ✅ | RUN-RETRY + ON-FAILURE/ON-SUCCESS complete |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Implemented | Phase 1-4 ✅ | All phases complete |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Implemented | ✅ Complete | --from-json + schema_version implemented |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Partial | ✅ Core complete | Templates + traceability verifier done |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | Implemented | N/A | Help implemented, no gaps remaining |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | Implemented | Phase 1-4 ✅ | Registry + validate + Adapter + Operator config |
| [CONSULT-DIRECTIVE](CONSULT-DIRECTIVE.md) | Partial | Phase 1-3 ✅ | CONSULT directive + prompt injection on resume |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | Implemented | ✅ Complete | Taxonomy, enumeration, `artifact` CLI commands |
| [ERROR-HANDLING](ERROR-HANDLING.md) | Implemented | Phase 0-3 ✅ | `--strict`, `--json-errors`, ON-FAILURE complete |
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | Implemented | ✅ Phase 1-4 | Native SDK compaction + directives |
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | Implemented | ✅ Phase 1-4 | `sessions resume` + `SESSION-NAME` directive |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | Implemented | Phase 1-2 ✅ | Adapter methods + status command enhanced |

---

## SDK v2 Integration (2026-01-24)

> **SDK Location**: Available locally at `../../copilot-sdk/python`  
> **Ready for Integration**: Yes - SDK v2 with Protocol Version 2 is installed and ready

The Copilot SDK has been updated to Protocol Version 2 with new capabilities. Three new proposals track their integration:

### Priority: P1 (High Impact)

| Proposal | Feature | Effort | Rationale |
|----------|---------|--------|-----------|
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | Native compaction | Medium | ✅ Complete - INFINITE-SESSIONS directives |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | Status/auth/models | Low | ✅ Complete - `sdqctl status` enhanced |

### Priority: P2 (Medium Impact)

| Proposal | Feature | Effort | Rationale |
|----------|---------|--------|-----------|
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | Session management | Medium | ✅ Complete (2026-01-25) |
| [CONSULT-DIRECTIVE](CONSULT-DIRECTIVE.md) | Human consultation | Medium | ✅ Phase 1-3 complete, Phase 4 low priority |

> **Consultation Workflow (2026-01-25):** The CONSULT directive extends PAUSE to enable workflows where 
> sdqctl runs analysis, identifies open questions, pauses, and when human resumes with `sdqctl sessions resume`, 
> the agent proactively presents the questions using `ask_user` style menus. 
> See [CONSULT-DIRECTIVE.md](CONSULT-DIRECTIVE.md) for full proposal.

### Key SDK Changes

- **Protocol Version 2** - Required for new features
- **Infinite Sessions** - Background compaction at 80% context, blocking at 95%
- **Session APIs** - `list_sessions()`, `resume_session()`, `delete_session()`
- **Metadata APIs** - `get_status()`, `get_auth_status()`, `list_models()`
- **Workspace Path** - `session.workspace_path` for session artifacts

See [COPILOT-SDK-INTEGRATION.md](../COPILOT-SDK-INTEGRATION.md) for detailed API documentation.

---

## Proposal vs Implementation Gap Analysis

### RUN-BRANCHING.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `RUN-RETRY N "prompt"` | Phase 1 | ✅ `conversation.py`, `run.py` | None |
| `ON-FAILURE` block | Phase 2 | ✅ `conversation.py`, `run.py` | None |
| `ON-SUCCESS` block | Phase 2 | ✅ `conversation.py`, `run.py` | None |
| ELIDE + branching = parse error | Design | ✅ `validate_elide_chains()` | None |

### VERIFICATION-DIRECTIVES.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `sdqctl verify refs` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `sdqctl verify links` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `sdqctl verify traceability` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `sdqctl verify all` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `VERIFY refs` directive | Phase 3-4 | ✅ `conversation.py` | None |
| `VERIFY-ON-ERROR` directive | Phase 3-4 | ✅ Implemented | None |
| `VERIFY-OUTPUT` directive | Phase 3-4 | ✅ Implemented | None |
| `VERIFY-LIMIT` directive | Phase 3-4 | ✅ Implemented | None |
| `links` verifier | Phase 1 | ✅ `verifiers/links.py` | None |
| `terminology` verifier | Phase 1 | ✅ `verifiers/terminology.py` | None |
| `traceability` verifier | Phase 1 | ✅ `verifiers/traceability.py` | None |
| `assertions` verifier | Phase 1 | ✅ `verifiers/assertions.py` | None |

**CLI commands available**: `sdqctl verify refs|links|traceability|terminology|assertions|all`

**Verifier modules**: `refs`, `links`, `traceability`, `terminology`, `assertions` in `sdqctl/verifiers/`

### PIPELINE-ARCHITECTURE.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `--from-json` flag | Phase 2 | ✅ `commands/cycle.py` | None |
| `from_rendered_json()` | Phase 3 | ✅ `core/conversation.py` | None |
| `schema_version` field | Phase 1 | ✅ `core/renderer.py` | None |
| Schema docs | Phase 1 | ✅ `docs/PIPELINE-SCHEMA.md` | None |
| `--trust-input` flag | Security | ❌ Not implemented | Low priority |

### STPA-INTEGRATION.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| STPA workflow templates | Phase 2 | ✅ `examples/workflows/stpa/` | None |
| STPA template variables | Phase 1 | ❌ Not implemented | Future work |
| `VERIFY-TRACE` directive | Phase 3 | ✅ `conversation.py` | None |
| `sdqctl verify trace` CLI | Phase 3 | ✅ `commands/verify.py` | None |
| `VERIFY-COVERAGE` directive | Phase 3 | ✅ `conversation.py` | None |
| `sdqctl verify coverage` CLI | Phase 3 | ✅ `commands/verify.py` | None |
| `VERIFY-IMPLEMENTED` directive | Phase 3 | ❌ Not implemented | Future work |
| CI JSON output format | Phase 4 | ❌ Not implemented | Future work |

### CLI-ERGONOMICS.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `sdqctl help` overview | Yes | ✅ `commands/help.py` | None |
| `sdqctl help <command>` | Yes | ✅ 11 commands | None |
| `sdqctl help <topic>` | Yes | ✅ 6 topics | None |
| `sdqctl help guidance` | Nested tier | ❌ Flattened to topics | Design divergence (acceptable) |
| Command taxonomy docs | Yes | ✅ Now in BACKLOG | None |
| `run` rename | Investigate | 🔒 Deferred | Awaiting user feedback |

---

## Directive Candidates Analysis

### Currently Implemented (73 directives)

**Metadata**: `MODEL`, `ADAPTER`, `MODE`, `MAX-CYCLES`, `CWD`  
**Model Requirements**: `MODEL-REQUIRES`, `MODEL-PREFERS`, `MODEL-POLICY`  
**Context**: `CONTEXT`, `CONTEXT-OPTIONAL`, `CONTEXT-EXCLUDE`, `CONTEXT-LIMIT`, `ON-CONTEXT-LIMIT`, `VALIDATION-MODE`, `REFCAT`  
**File Control**: `ALLOW-FILES`, `DENY-FILES`, `ALLOW-DIR`, `DENY-DIR`  
**Injection**: `PROLOGUE`, `EPILOGUE`, `HEADER`, `FOOTER`, `HELP`  
**Prompts**: `PROMPT`, `ON-CONTEXT-LIMIT-PROMPT`  
**Compaction**: `COMPACT`, `COMPACT-PRESERVE`, `COMPACT-SUMMARY`, `COMPACT-PROLOGUE`, `COMPACT-EPILOGUE`, `NEW-CONVERSATION`, `ELIDE`  
**Infinite Sessions**: `INFINITE-SESSIONS`, `COMPACTION-MIN`, `COMPACTION-THRESHOLD`  
**Checkpoints**: `CHECKPOINT`, `CHECKPOINT-AFTER`, `CHECKPOINT-NAME`, `PAUSE`, `CONSULT`  
**Output**: `OUTPUT`, `OUTPUT-FORMAT`, `OUTPUT-FILE`, `OUTPUT-DIR`  
**RUN**: `RUN`, `RUN-ON-ERROR`, `RUN-OUTPUT`, `RUN-OUTPUT-LIMIT`, `RUN-ENV`, `RUN-CWD`, `RUN-TIMEOUT`, `ALLOW-SHELL`, `RUN-ASYNC`, `RUN-WAIT`, `RUN-RETRY`  
**Branching**: `ON-FAILURE`, `ON-SUCCESS`, `END`  
**Verify**: `VERIFY`, `VERIFY-ON-ERROR`, `VERIFY-OUTPUT`, `VERIFY-LIMIT`, `VERIFY-TRACE`, `VERIFY-COVERAGE`, `CHECK-REFS`, `CHECK-LINKS`, `CHECK-TRACEABILITY`  
**Pre-flight**: `REQUIRE`  
**Inclusion**: `INCLUDE`  
**Debug**: `DEBUG`, `DEBUG-INTENTS`, `EVENT-LOG`

### Proposed but NOT Implemented

| Directive | Source Proposal | Priority | Complexity | Notes |
|-----------|-----------------|----------|------------|-------|
| `VERIFY-IMPLEMENTED` | STPA-INTEGRATION | P2 | Medium | Pattern search in code |

> **Note:** `VERIFY-COVERAGE` was implemented 2026-01-24 and is now in "Currently Implemented" list above.

> **Note:** `ON-FAILURE` and `ON-SUCCESS` were implemented 2026-01-24 - see [Session notes](#session-2026-01-24-on-failureon-success-blocks).
> 
> **Note:** `CHECK-REFS`, `CHECK-LINKS`, `CHECK-TRACEABILITY` aliases were implemented 2026-01-24.
>
> **Note:** `INCLUDE` directive implemented 2026-01-24 - see [Session notes](#session-2026-01-24-include-directive).
>
> **Note:** `VERIFY-TRACE` directive implemented 2026-01-24 - see [Session notes](#session-2026-01-24-verify-trace-directive).

### Rejected Directives (per proposals)

| Directive | Source | Rejection Reason |
|-----------|--------|------------------|
| `SECTION` | RUN-BRANCHING | "This is a programming language now" - GOTO considered harmful |
| `GOTO` | RUN-BRANCHING | Rejected in favor of simpler ON-FAILURE blocks |

### Directive Candidates NOT in Proposals

Potential additions based on usage patterns:

| Candidate | Description | Use Case |
|-----------|-------------|----------|
| ~~`REQUIRE`~~ | ~~Fail if file/tool missing~~ | ✅ Implemented 2026-01-24 - Pre-flight checks |
| `GATE` | Wait for condition | CI integration |
| `TIMEOUT` | Global workflow timeout | Long-running protection |
| `RETRY-LIMIT` | Global retry cap | Token budget control |
| ~~`COMPACT-IF-NEEDED`~~ | ~~Conditional compaction~~ | ✅ Now default behavior - `COMPACT` respects threshold ([Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional) FIXED) |
| ~~`INCLUDE-HELP`~~ | ~~Inject help topic into prompt~~ | ✅ Implemented as `HELP` directive 2026-01-24 |

### Help System: Agent Accessibility Gap

> **Discovered:** 2026-01-23  
> **Status:** ✅ RESOLVED - HELP directive implemented 2026-01-24

#### Implementation (2026-01-24)

The `HELP` directive was implemented to inject built-in help content into workflow prompts:

```dockerfile
# Single topic injection
HELP directives              # Inject directive reference

# Multiple topics
HELP workflow validation     # Inject both topics
```

**Available Topics**: directives, adapters, workflow, variables, context, examples, validation, ai

See [P1: HELP Directive](#p1-help-directive) for implementation details.

#### Future Enhancement: Agent-Optimized Help Format

Current help is human-optimized (tables, examples). Could add LLM-optimized variants:
- Structured examples with input→output pairs
- Common anti-patterns to avoid
- Decision trees for directive selection
- JSON-LD or structured data format

**Status**: Deferred - current implementation sufficient for meta-workflows.

### Compaction Policy: Known Gaps

> **See Also:** [QUIRKS.md Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) (✅ FIXED) and [Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional) (✅ FIXED)

The compaction threshold system is now fully wired:

| Feature | Expected | Actual | Status |
|---------|----------|--------|--------|
| `--min-compaction-density` | Skip compaction if below N% | ✅ **NOW WIRED** | [Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) ✅ FIXED |
| `COMPACT` directive | Conditional on threshold | ✅ **NOW CONDITIONAL** | [Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional) ✅ FIXED |
| `CONTEXT-LIMIT N%` | Compact before any turn exceeding N% | **Cycle boundaries only** | As designed |
| Two-tier thresholds | Operating + max thresholds | **Single threshold only** | Future consideration |

**Usage:** Use `cycle -n N --min-compaction-density 50` to skip compaction if context < 50% full. Both automatic and explicit `COMPACT` directives respect this threshold.

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

### 4.1 CLI Ergonomics & Tooling Gap Analysis

**Status**: Draft → Analysis Complete  
**Proposal**: [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md)  
**Last Analysis**: 2026-01-23

#### Command Taxonomy (Gap Analysis Complete)

| Command | Type | SDK Calls | Status |
|---------|------|-----------|--------|
| `run` | SDK-invoking | Yes | ✅ Implemented |
| `cycle` | SDK-invoking | Yes | ✅ Implemented |
| `flow` | SDK-invoking | Yes | ✅ Implemented |
| `apply` | SDK-invoking | Yes | ✅ Implemented |
| `resume` | SDK-invoking | Yes | ✅ Implemented |
| `render` | Tooling | No | ✅ Implemented (subcommands: run, cycle, apply, file) |
| `verify` | Tooling | No | ✅ Implemented (subcommands: refs, all) |
| `validate` | Tooling | No | ✅ Implemented |
| `show` | Tooling | No | ✅ Implemented |
| `status` | Tooling | No | ✅ Implemented |
| `init` | Tooling | No | ✅ Implemented |
| `help` | Tooling | No | ✅ Implemented (commands + topics) |

#### Help System Status

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `sdqctl help` | Overview | ✅ | None |
| `sdqctl help <command>` | Command help | ✅ 11 commands | None |
| `sdqctl help <topic>` | Topic help | ✅ 6 topics | None |
| `sdqctl help guidance [topic]` | Conceptual guidance | ❌ | **Not implemented** |
| `sdqctl help --list` | List all | ✅ | None |

#### Identified Gaps

1. **`sdqctl help guidance` subcommand** - CLI-ERGONOMICS.md proposes a nested guidance system but `help.py` implements topics directly at `sdqctl help <topic>` level instead. The two-tier structure is not needed since topics already provide guidance.

2. **Run rename investigation** - Documented in CLI-ERGONOMICS.md as "investigate only". No action needed until user feedback gathered. Current help system includes `run-vs-RUN` disambiguation (not as topic, but clarified in `directives` topic).

3. **Verifier expansion** - Only `refs` verifier exists. Consider adding:
   - `traceability` - Check requirement traces
   - `syntax` - Deep workflow validation (beyond `validate`)

#### Remaining Work Areas

- **Help system**: ✅ Complete (topics instead of nested guidance)
- **Command taxonomy**: ✅ Complete (table above)
- **Run rename investigation**: 🔒 Deferred pending user feedback

Implementation workflows (no longer needed - help system implemented):
```bash
# Original workflow paths - OBSOLETE
# sdqctl cycle examples/workflows/cli-ergonomics/01-help-system.conv --adapter copilot
# sdqctl cycle examples/workflows/cli-ergonomics/02-tooling-gap-analysis.conv --adapter copilot
# sdqctl cycle examples/workflows/cli-ergonomics/03-run-rename-assessment.conv --adapter copilot
```

---

### 4.2 Batch/Parallel Execution

Run multiple workflows concurrently:
```bash
sdqctl batch --parallel=4 workflows/*.conv
```

**Use case**: Analyze all 16 AID ecosystem projects simultaneously

---

### 4.3 Delta Detection

Identify which UCAs/requirements are affected by code changes:
```bash
sdqctl delta --since=HEAD~5 --scope=stpa
```

**Use case**: CI integration for incremental safety analysis

---

### 4.4 Cross-Project Traceability

UCAs that span multiple projects (e.g., Nightscout ↔ Loop sync issues)

**Use case**: Ecosystem-wide hazard analysis

---

### 4.5 Workflow Authoring Enhancements (from QUIRKS.md)

Ideas moved from QUIRKS.md "Future Considerations":

| Feature | Description | Priority |
|---------|-------------|----------|
| Export/import plans as JSON | Allow interpreted conversations to be serialized | P3 |
| External variable injection | Accept variables from file/stdin/env | P2 |
| Jsonnet integration | Apply logic for branching on RUN failures | P3 |
| Environment variables | Deny/accept list for env var access | P3 |

**Note**: Variable injection partially addressed by `--from-json` pipeline mode. Full external variable support would complement this.

---

## Completed

> **Full session logs archived to**: [`archive/SESSIONS/`](../archive/SESSIONS/)

### Summary

| Date | Sessions | Key Accomplishments |
|------|----------|---------------------|
| 2026-01-23 | 5 sessions | Tooling gap analysis, VERIFY directive (4 phases), RUN-RETRY, --from-json |
| 2026-01-24 | 16 sessions | Artifact taxonomy, verify CLI commands, ON-FAILURE blocks, INCLUDE directive |
| 2026-01-25 | 11 sessions | CONSULT directive, docs/COMMANDS.md, MODEL-REQUIREMENTS Phase 3-4 |
| Earlier | — | Terminology updates, regulatory context, GLOSSARY.md |

For detailed session logs, see:
- [`archive/SESSIONS/2026-01-23.md`](../archive/SESSIONS/2026-01-23.md)
- [`archive/SESSIONS/2026-01-24.md`](../archive/SESSIONS/2026-01-24.md)
- [`archive/SESSIONS/2026-01-25.md`](../archive/SESSIONS/2026-01-25.md)

---

## Design Decisions

> **Full design decisions archived to**: [`archive/DECISIONS.md`](../archive/DECISIONS.md)

Key decisions with ADRs:
- [ADR-001: ON-FAILURE Strategy](../archive/decisions/ADR-001-on-failure-strategy.md) - Both RUN-RETRY and full blocks
- [ADR-002: VERIFY Execution Model](../archive/decisions/ADR-002-verify-execution-model.md) - Blocking (synchronous)
- [ADR-003: JSON Schema Versioning](../archive/decisions/ADR-003-json-schema-versioning.md) - Explicit `schema_version` field
- [ADR-004: SDK Session Persistence](../archive/decisions/ADR-004-sdk-session-persistence.md) - Adapter methods + CLI
- [ADR-005: Compaction Priority](../archive/decisions/ADR-005-compaction-priority.md) - CLI > directives > defaults

All 12 design decisions are documented in [`archive/DECISIONS.md`](../archive/DECISIONS.md).


---

## Documentation Gaps (P2-P3)

> **Added**: 2026-01-25 | **Purpose**: Track documentation improvements identified during codebase review

### P2: Missing/Incomplete Documentation

| Gap | Location | Notes | Status |
|-----|----------|-------|--------|
| ~~`refcat` command not in GETTING-STARTED.md~~ | `docs/GETTING-STARTED.md` | Has "Precise Context with refcat" section | ✅ 2026-01-25 |
| `artifact` command undocumented | README.md, docs/ | ARTIFACT-TAXONOMY.md proposal exists but no user-facing docs | 🔲 Open |
| ~~`resume` command separate from `sessions`~~ | README.md, docs/COMMANDS.md | Clarified difference with comparison notes | ✅ 2026-01-25 |
| ~~`flow` command minimal docs~~ | docs/COMMANDS.md | Enhanced with options table, use cases, tips | ✅ 2026-01-25 |
| ~~`init` command not documented~~ | docs/GETTING-STARTED.md | Added "Initialize a Project" section with config example | ✅ 2026-01-25 |
| ~~Adapter configuration~~ | `docs/ADAPTERS.md` | How to configure each adapter (env vars, auth) | ✅ 2026-01-25 |
| Model selection guide | docs/ | When to use gpt-4 vs claude vs sonnet; MODEL-REQUIRES examples | 🔲 Open (see ADAPTERS.md §MODEL-REQUIRES) |

### P3: Cross-Reference Improvements

| Gap | Files Affected | Notes | Status |
|-----|----------------|-------|--------|
| ~~CONSULT not in README~~ | README.md | CONSULT directive now in directive table | ✅ 2026-01-25 |
| ~~SESSION-NAME not in README~~ | README.md | Directive now in directive table | ✅ 2026-01-25 |
| ~~INFINITE-SESSIONS directives not in README~~ | README.md | COMPACTION-MIN, COMPACTION-THRESHOLD now documented | ✅ 2026-01-25 |
| ~~DEBUG directives not documented~~ | README.md | DEBUG, DEBUG-INTENTS, EVENT-LOG now in directive table | ✅ 2026-01-25 |
| HELP directive examples | docs/GETTING-STARTED.md | `HELP directives workflow` syntax not shown | 🔲 Open |
| ON-FAILURE/ON-SUCCESS examples | docs/GETTING-STARTED.md | Branching directives implemented but no tutorial | 🔲 Open |
| `validate` command tutorial | docs/GETTING-STARTED.md | Referenced in CI/CD but no hands-on section | 🔲 Open |
| Copilot skill files explained | docs/GETTING-STARTED.md | `sdqctl init` creates skills but purpose unclear | 🔲 Open |

### P3: Workflow Examples Gap

| Gap | Suggested Location | Notes |
|-----|-------------------|-------|
| CONSULT workflow example | `examples/workflows/` | Show human-in-loop consultation pattern |
| refcat usage patterns | `examples/workflows/` | Cross-repo context injection example |
| ELIDE chains example | `examples/workflows/` | Multi-ELIDE optimized workflows |
| CI/CD integration | `examples/ci/` | GitHub Actions / GitLab CI examples using verify + render |

### Actionable Next Steps

1. **Quick wins** (< 30 min each):
   - ~~Add CONSULT/SESSION-NAME to README directive table~~ ✅ 2026-01-25
   - ~~Add DEBUG directives to README~~ ✅ 2026-01-25
   - ~~Add INFINITE-SESSIONS directives to README~~ ✅ 2026-01-25
   - ~~Add `refcat` section to GETTING-STARTED.md~~ ✅ 2026-01-25
   - ~~Add `init` documentation to GETTING-STARTED.md~~ ✅ 2026-01-25
   
2. **Medium effort** (1-2 hours):
   - ~~Create `docs/COMMANDS.md` with detailed command reference~~ ✅ 2026-01-25
   - ~~Add adapter configuration guide (`docs/ADAPTERS.md`)~~ ✅ 2026-01-25
   - Document `artifact` command for traceability workflows
   
3. **Future consideration**:
   - LSP support for refcat (mentioned in References)
   - Interactive docs via `sdqctl help --interactive`

### New Gaps Identified (2026-01-25 Review)

| Gap | Priority | Notes | Status |
|-----|----------|-------|--------|
| ~~HELP directive not in GETTING-STARTED examples~~ | P3 | Duplicate of §P3 Cross-Reference | See above |
| ~~Adapter env vars not documented~~ | P2 | COPILOT_SDK_AUTH, ANTHROPIC_API_KEY, OPENAI_API_KEY | ✅ docs/ADAPTERS.md |
| ~~Q-014/Q-015 research blockers~~ | P0 | **FIXED**: Handler registered once per session | ✅ 2026-01-25 |
| `ON-FAILURE`/`ON-SUCCESS` not in GETTING-STARTED | P3 | Branching directives implemented but not in tutorials | 🔲 Open |
| ~~Accumulate mode stability warning~~ | P2 | Q-014 fixed - accumulate mode now stable | ✅ 2026-01-25 |
| ~~Event handler lifecycle docs~~ | P2 | Fix documented in QUIRKS.md Q-014 section | ✅ 2026-01-25 |
| ~~Q-013 verification after Q-014 fix~~ | P1 | Root cause confirmed as Q-014 handler leak - now fixed | ✅ 2026-01-25 |
| `validate` command not in GETTING-STARTED | P3 | Referenced in CI/CD but no tutorial section | 🔲 Open |
| Copilot skill files not documented | P3 | `sdqctl init` creates skills but purpose not explained | 🔲 Open |

### Gaps Added (2026-01-25 Deep Review)

| Gap | Priority | Notes | Status |
|-----|----------|-------|--------|
| ~~`flow` command full documentation~~ | P2 | Enhanced in docs/COMMANDS.md with options table, use cases | ✅ 2026-01-25 |
| ~~`resume` vs `sessions resume` clarity~~ | P2 | Clarified in docs/COMMANDS.md with comparison notes | ✅ 2026-01-25 |
| `artifact` user-facing guide | P2 | COMMANDS.md has reference; needs GETTING-STARTED section | 🔲 Open |
| QUIRKS.md → all resolved | - | All quirks Q-001 through Q-015 now ✅ FIXED | ✅ 2026-01-25 |

---

## References
IMPORTANT: remember to cross reference our generic backlog against other task lists and backlogs.  Some quirk proposals become backlog items!

Additional IDEAS:  LSP support, for refcat and maybe other subcommands.

- [archive/](../archive/) - Archived session logs and design decisions
- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Workflow design principles
- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
- [SYNTHESIS-CYCLES.md](../docs/SYNTHESIS-CYCLES.md) - Iterative workflow patterns
- [VALIDATION-WORKFLOW.md](../docs/VALIDATION-WORKFLOW.md) - Validation/verification guide
- [ERROR-HANDLING.md](ERROR-HANDLING.md) - Error handling strategy and roadmap
