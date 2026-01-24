# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-24 (SDK v2 Capabilities Added)  
> **Purpose**: Track open design questions, implementation work, and future proposals

---

## Executive Summary: Tooling Gap Analysis

**Analysis Date**: 2026-01-23 | **Phases Completed**: 4/4  
**SDK v2 Analysis**: 2026-01-24 | **New Proposals**: 3 (Infinite Sessions, Session Persistence, Metadata APIs)

Note: remember to cross reference and evaluate priorities across roadmaps.
Error handling phases 0-3 complete (2026-01-24). Next priorities: SDK integration (P1) and STPA directives (P2).

### Tooling Commands Status (Non-SDK)

All 7 proposed tooling commands are **fully implemented**:

| Command | Purpose | Subcommands | Status |
|---------|---------|-------------|--------|
| `render` | Preview prompts (no AI) | `run`, `cycle`, `apply`, `file` | ✅ Complete |
| `verify` | Static verification | `refs`, `links`, `traceability`, `all` | ✅ Complete (3 verifiers) |
| `validate` | Syntax checking | - | ✅ Complete |
| `show` | Display parsed workflow | - | ✅ Complete |
| `status` | Session/system info | `--adapters`, `--sessions` | ✅ Complete |
| `init` | Project initialization | - | ✅ Complete |
| `help` | Documentation access | 11 commands, 6 topics | ✅ Complete |

### Priority Recommendations

#### P0: Documentation Gaps (Quick Wins)

| Gap | Location | Effort | Status |
|-----|----------|--------|--------|
| Pipeline schema docs | `docs/PIPELINE-SCHEMA.md` | 1 hour | ✅ Complete |
| Verifier extension guide | `docs/EXTENDING-VERIFIERS.md` | 1 hour | ✅ Complete |

#### P1: Verifier Expansion (High Value)

| Verifier | Use Case | Effort | Status |
|----------|----------|--------|--------|
| `traceability` | STPA REQ→SPEC→TEST validation | 4 hours | ✅ Complete |
| `links` | URL/file link checking | 2 hours | ✅ Complete |
| `terminology` | Deprecated terms + capitalization | 2 hours | ✅ Complete |

#### P2: Directive Implementation (Deferred)

| Directive | Proposal | Complexity | Recommendation |
|-----------|----------|------------|----------------|
| `ON-FAILURE` | RUN-BRANCHING | High | ✅ Implemented 2026-01-24 |
| `ON-SUCCESS` | RUN-BRANCHING | High | ✅ Implemented 2026-01-24 |
| `VERIFY-TRACE` | STPA-INTEGRATION | Medium | ✅ Implemented 2026-01-24 |

### Key Findings

1. **All tooling commands implemented** - No missing CLI commands
2. **Verifier infrastructure complete** - 3 verifiers: `refs`, `links`, `traceability`
3. **Help system exceeds proposal** - 11 commands + 6 topics (proposal specified nested `guidance`)
4. **ON-FAILURE blocks deferred** - RUN-RETRY covers common retry patterns

---

## Current Proposals Status

| Proposal | Status | Implementation | Notes |
|----------|--------|----------------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Implemented | Phase 1-2 ✅ | RUN-RETRY + ON-FAILURE/ON-SUCCESS complete |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Implemented | Phase 1-4 ✅ | All phases complete |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Implemented | ✅ Complete | --from-json + schema_version implemented |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Partial | ✅ Core complete | Templates + traceability verifier done |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | Implemented | N/A | Help implemented, no gaps remaining |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | Draft | ❌ Open Questions | Abstract model selection by capability |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | Implemented | ✅ Complete | Taxonomy, enumeration, `artifact` CLI commands |
| [ERROR-HANDLING](ERROR-HANDLING.md) | Implemented | Phase 0-3 ✅ | `--strict`, `--json-errors`, ON-FAILURE complete |
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | Draft | ❌ Not started | Native SDK compaction for cycle mode |
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | Draft | ❌ Not started | Resume/list/delete sessions |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | Implemented | Phase 1-2 ✅ | Adapter methods + status command enhanced |

---

## SDK v2 Integration (2026-01-24)

The Copilot SDK has been updated to Protocol Version 2 with new capabilities. Three new proposals track their integration:

### Priority: P1 (High Impact)

| Proposal | Feature | Effort | Rationale |
|----------|---------|--------|-----------|
| [SDK-INFINITE-SESSIONS](SDK-INFINITE-SESSIONS.md) | Native compaction | Medium | Replace client-side compaction, simpler code |
| [SDK-METADATA-APIS](SDK-METADATA-APIS.md) | Status/auth/models | Low | ✅ Complete - `sdqctl status` enhanced |

### Priority: P2 (Medium Impact)

| Proposal | Feature | Effort | Rationale |
|----------|---------|--------|-----------|
| [SDK-SESSION-PERSISTENCE](SDK-SESSION-PERSISTENCE.md) | Session management | Medium | Multi-day workflows, resume capability |

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
| `VERIFY-COVERAGE` directive | Phase 3 | ❌ Not implemented | Future work |
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

### Currently Implemented (48 directives)

**Metadata**: `MODEL`, `ADAPTER`, `MODE`, `MAX-CYCLES`, `CWD`  
**Context**: `CONTEXT`, `CONTEXT-OPTIONAL`, `CONTEXT-EXCLUDE`, `CONTEXT-LIMIT`, `ON-CONTEXT-LIMIT`, `VALIDATION-MODE`  
**File Control**: `ALLOW-FILES`, `DENY-FILES`, `ALLOW-DIR`, `DENY-DIR`  
**Injection**: `PROLOGUE`, `EPILOGUE`, `HEADER`, `FOOTER`  
**Prompts**: `PROMPT`, `ON-CONTEXT-LIMIT-PROMPT`  
**Compaction**: `COMPACT`, `COMPACT-PRESERVE`, `COMPACT-SUMMARY`, `COMPACT-PROLOGUE`, `COMPACT-EPILOGUE`, `NEW-CONVERSATION`, `ELIDE`  
**Checkpoints**: `CHECKPOINT`, `CHECKPOINT-AFTER`, `CHECKPOINT-NAME`, `PAUSE`  
**Output**: `OUTPUT`, `OUTPUT-FORMAT`, `OUTPUT-FILE`, `OUTPUT-DIR`  
**RUN**: `RUN`, `RUN-ON-ERROR`, `RUN-OUTPUT`, `RUN-OUTPUT-LIMIT`, `RUN-ENV`, `RUN-CWD`, `RUN-TIMEOUT`, `ALLOW-SHELL`, `RUN-ASYNC`, `RUN-WAIT`, `RUN-RETRY`  
**Branching**: `ON-FAILURE`, `ON-SUCCESS`, `END`  
**Verify**: `VERIFY`, `VERIFY-ON-ERROR`, `VERIFY-OUTPUT`, `VERIFY-LIMIT`, `CHECK-REFS`, `CHECK-LINKS`, `CHECK-TRACEABILITY`  
**Pre-flight**: `REQUIRE`  
**Inclusion**: `INCLUDE`  
**Debug**: `DEBUG`, `DEBUG-INTENTS`, `EVENT-LOG`

### Proposed but NOT Implemented

| Directive | Source Proposal | Priority | Complexity | Notes |
|-----------|-----------------|----------|------------|-------|
| `VERIFY-COVERAGE` | STPA-INTEGRATION | P2 | Medium | Check trace coverage % |
| `VERIFY-IMPLEMENTED` | STPA-INTEGRATION | P2 | Medium | Pattern search in code |

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

### Session 2026-01-23 (Tooling Gap Analysis)

- [x] **Phase 1: Command Inventory** - Classified 12 commands (5 SDK, 7 tooling)
- [x] **Phase 2: Proposal Comparison** - Compared 5 proposals vs implementation
- [x] **Phase 3: Directive Candidates** - Analyzed 40 implemented, 9 proposed, 2 rejected
- [x] **Phase 4: Priority Recommendations** - P0/P1/P2 priorities documented
- [x] **BACKLOG.md updated** - Executive summary, gap tables, recommendations

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

## Open Questions / Discussion

> **Session**: 2026-01-24 | **Topic**: Validation/Verification Workflow Documentation

### P0: REFCAT Directive Implementation

**Status**: ✅ Complete  
**Proposal**: [REFCAT-DESIGN.md](REFCAT-DESIGN.md)

**Completed** (2026-01-24):
- ✅ `sdqctl refcat` CLI command with full P0/P1 feature support
- ✅ Core module `sdqctl/core/refcat.py` with parsing, extraction, formatting
- ✅ 46 unit tests passing
- ✅ **REFCAT directive** in `.conv` files (implemented 2026-01-24)
- ✅ Validation integration (`sdqctl validate` checks REFCAT refs)
- ✅ Renderer integration (REFCAT excerpts in rendered output)
- ✅ 14 additional tests for directive parsing, validation, and rendering

**Usage**:

```dockerfile
# Extract specific lines into context
REFCAT @sdqctl/core/context.py#L182-L194
REFCAT loop:LoopKit/Sources/Algorithm.swift#L100-L200

# Multiple refs on one line
REFCAT @file1.py#L10-L20 @file2.py#L1-L50
```

**Implementation** (commit `a1f1f07`):
- `DirectiveType.REFCAT` in `conversation.py`
- `refcat_refs` field in `ConversationFile` dataclass
- `validate_refcat_refs()` method
- `render_cycle()` extracts REFCAT content
- `format_rendered_markdown()` and `format_rendered_json()` include excerpts

---

### P1: Semantic Extraction + LSP Integration

**Status**: Future Work  
**Proposal**: [REFCAT-DESIGN.md §1.3](REFCAT-DESIGN.md)

The REFCAT design includes semantic extractors for language-aware content extraction:

```bash
# Proposed (not yet implemented)
sdqctl refcat @file.py#/def my_func/:function   # Extract complete function
sdqctl refcat @file.py#/class Foo/:class        # Extract complete class
sdqctl refcat @file.py#/pattern/:block          # Extract indentation block
```

**Enhancement opportunity**: Integrate with Language Server Protocol (LSP) for:
- Accurate function/class boundary detection
- Symbol navigation across files
- Type information extraction
- Cross-reference resolution

**Potential LSP integrations**:
- `pyright` / `pylsp` for Python
- `typescript-language-server` for TypeScript/JavaScript
- `gopls` for Go
- `sourcekit-lsp` for Swift

**Trade-offs**:
- LSP servers add dependencies and startup time
- Fallback to regex/indentation when LSP unavailable
- Consider tree-sitter as lighter-weight alternative

**Decision**: Defer to future work. Document as aspirational in REFCAT-DESIGN.md.

---

### P1: HELP Directive

**Status**: ✅ Complete  
**Proposal**: [BACKLOG.md §Help System Gap](BACKLOG.md#help-system-agent-accessibility-gap)  
**Implemented**: 2026-01-24

A simple directive to inject built-in help content into workflow prompts:

```dockerfile
# Inject single topic
HELP directives              # Inject directive reference

# Inject multiple topics
HELP workflow validation     # Inject both topics
```

**Use case**: AI agents authoring .conv workflows need to know directive syntax. 

**Implementation** (2026-01-24):
- `DirectiveType.HELP` in `conversation.py`
- `help_topics` field in `ConversationFile` dataclass
- Topics resolved during rendering via `render_cycle()`
- Validation via `validate_help_topics()` method
- 10 tests in `test_conversation.py` and `test_render_command.py`

**Available Topics**: directives, adapters, workflow, variables, context, examples, validation, ai

---

### P2: Documentation Reorganization (Human vs AI Consumption)

**Status**: Proposal  
**Discovered**: 2026-01-24

Current documentation structure mixes human-oriented and AI-oriented content:

#### Current Issues

| Issue | Location | Impact |
|-------|----------|--------|
| Duplicate terminology explanations | PHILOSOPHY.md, GLOSSARY.md | Maintenance burden, risk of drift |
| Future enhancements mixed with quirks | QUIRKS.md (now fixed) | Confusing scope |
| Design decisions scattered | Multiple docs | Hard to find authoritative source |
| No clear AI-optimized entry point | - | AI agents must parse verbose prose |

#### Proposed Structure

```
docs/
├── reference/           # AI-optimized (structured, concise)
│   ├── DIRECTIVES.md    # Table-driven directive reference
│   ├── COMMANDS.md      # CLI command reference
│   ├── VARIABLES.md     # Template variable reference
│   └── ERRORS.md        # Error codes and resolutions
├── guides/              # Human-optimized (narrative, examples)
│   ├── GETTING-STARTED.md
│   ├── WORKFLOW-DESIGN.md
│   ├── SYNTHESIS-CYCLES.md
│   └── TRACEABILITY-WORKFLOW.md
├── concepts/            # Shared (both audiences)
│   ├── PHILOSOPHY.md
│   └── GLOSSARY.md
└── maintenance/         # Internal
    ├── QUIRKS.md
    └── FEATURE-INTERACTIONS.md
```

#### Benefits

1. **AI agents**: Can `HELP directives` to get `reference/DIRECTIVES.md` (structured, parseable)
2. **Humans**: Continue reading narrative guides
3. **Maintenance**: Clear ownership per doc type

#### Decision

**Deferred** - Current flat structure is workable. Consider if docs exceed 20 files or AI integration issues emerge.

---

### Session 2026-01-24 (Documentation)

- [x] **VALIDATION-WORKFLOW.md** - Created comprehensive validation workflow guide
- [x] **Help topic: validation** - Added `sdqctl help validation` 
- [x] **README.md** - Added cross-reference to validation workflow docs
- [x] **BACKLOG.md** - Added open questions section with prioritized items

### Session 2026-01-24 (Artifact Taxonomy)

- [x] **ARTIFACT-TAXONOMY.md** - Created comprehensive proposal with:
  - All artifact types enumerated (REQ, SPEC, TEST, GAP, UCA, SC, Q, BUG, PROP)
  - STPA safety artifacts (LOSS, HAZ)
  - Relationship hierarchy and validation rules
  - Enumeration strategies (sequential, category-scoped, project-scoped)
  - ID lifecycle and collision avoidance
  - Formatting guidelines

- [x] **Traceability verifier extended** (2026-01-24):
  - Added LOSS, HAZ, BUG, PROP, Q, IQ patterns
  - Extended TRACE_CHAIN for full STPA: LOSS → HAZ → UCA → SC → REQ
  - Added STANDALONE_TYPES (GAP, BUG, PROP, Q, IQ) allowed without links
  - Orphan detection for LOSS and HAZ (top of safety chain)
  - Coverage metrics: loss_to_haz, haz_to_uca
  - 11 new tests in test_verifiers.py

**Remaining future work:**

| Task | Priority | Effort | Notes |
|------|----------|--------|-------|
| ~~Add artifact summary to TRACEABILITY-WORKFLOW.md~~ | ~~P2~~ | ~~30 min~~ | ✅ Done 2026-01-24 |
| ~~Create artifact templates (REQ, GAP, UCA, SPEC)~~ | ~~P3~~ | ~~1 hour~~ | ✅ Done 2026-01-24 - `examples/templates/artifacts/` |
| ~~`sdqctl artifact next` command~~ | ~~P3~~ | ~~2 hours~~ | ✅ Done 2026-01-24 - includes `list` subcommand |
| ~~`sdqctl artifact rename` command~~ | ~~P3~~ | ~~2 hours~~ | ✅ Done 2026-01-24 - `--dry-run` and `--json` flags |
| ~~`sdqctl artifact retire` command~~ | ~~P3~~ | ~~2 hours~~ | ✅ Done 2026-01-24 - `--reason`, `--successor`, `--dry-run`, `--json` flags |
| ~~Nightscout ecosystem conventions doc~~ | ~~P3~~ | ~~1 hour~~ | ✅ Done 2026-01-24 - `docs/NIGHTSCOUT-ECOSYSTEM.md` |

### Session 2026-01-24 (Documentation Philosophy)

- [x] **PHILOSOPHY.md** - Created comprehensive workflow design philosophy guide
  - Command roles: run (1 iteration) vs cycle (N iterations)
  - Anatomy of effective conversation files
  - Double diamond design pattern
  - Backlog-driven workflow design
  - Anti-patterns documentation
  - Reference examples table (6 good workflow patterns)
- [x] **GLOSSARY.md** - Enhanced terminology definitions
  - Added Prompt/Phase/Iteration/Cycle table
  - Added run vs cycle command disambiguation
  - Clarified that phases are NOT selectable steps
- [x] **Cross-references** - Added PHILOSOPHY.md links to:
  - GETTING-STARTED.md
  - SYNTHESIS-CYCLES.md
  - WORKFLOW-DESIGN.md
  - README.md
- [x] **Fixed broken link** - examples/workflows/README.md QUINE-WORKFLOWS.md → SYNTHESIS-CYCLES.md
- [x] **Audited 31 conv files** - Identified 7 good examples vs 24 needing improvements

#### Conv File Audit Summary

**Good Examples** (correct terminology, escape hatches, backlog-driven):
- `fix-quirks.conv` - Excellent terminology docs in comments
- `implement-improvements.conv` - Clear Triage→Implement→Document
- `proposal-development.conv` - State relay between cycles
- `sdk-debug-integration.conv` - Single item selection, blocker handling
- `test-discovery.conv` - Clear MODE audit, feeds implementation
- `deep-analysis.conv` - Good CHECKPOINT/COMPACT usage
- `REFCAT-DIRECTIVE.conv` - RUN-ON-ERROR for escape hatches

**Common Issues in Other Files**:
- Single-pass workflows (MAX-CYCLES 1) labeled as synthesis cycles
- Implicit cycle/phase definitions without explicit comments
- Missing escape hatches for blocker documentation
- No persistent backlog tracking between iterations

**Terminology Fixes Applied (2026-01-24)**:
- Fixed `# === Cycle N:` → `# === Phase N:` in 6 conv files
- Added Terminology comments to implement-improvements, proposal-development, sdk-debug-integration

#### Recommended Next Commands

**Universal Backlog Processor** (new - works across all domains):

```bash
# Process main proposal backlog (10 cycles)
sdqctl cycle examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --adapter copilot -n 10

# Process quirks backlog
sdqctl cycle examples/workflows/backlog-processor.conv \
  --prologue docs/QUIRKS.md \
  --adapter copilot -n 5

# Process multiple domains in one run
sdqctl cycle examples/workflows/backlog-processor.conv \
  --prologue proposals/BACKLOG.md \
  --prologue proposals/REFCAT-DESIGN.md \
  --prologue proposals/ARTIFACT-TAXONOMY.md \
  --adapter copilot -n 10

# With philosophy context for terminology work
sdqctl cycle examples/workflows/backlog-processor.conv \
  --prologue docs/PHILOSOPHY.md \
  --prologue docs/GLOSSARY.md \
  --prologue proposals/BACKLOG.md \
  --adapter copilot -n 5
```

**Domain-Specific Alternatives**:

```bash
# Fix quirks specifically
sdqctl cycle examples/workflows/fix-quirks.conv \
  --prologue docs/PHILOSOPHY.md \
  --adapter copilot -n 3

# Documentation sync
sdqctl run examples/workflows/documentation-sync.conv \
  --prologue docs/PHILOSOPHY.md \
  --adapter copilot

# Proposal development for design decisions
sdqctl cycle examples/workflows/proposal-development.conv \
  --prologue proposals/CLI-ERGONOMICS.md \
  --adapter copilot
```

### Session 2026-01-24 (Unified Backlog Processor)

- [x] **backlog-processor.conv** - Created universal backlog iteration workflow
  - Works across ALL domains via `--prologue` injection
  - 4-phase pattern: select → execute → verify → triage
  - Aggressive COMPACT for long `-n 10+` runs
  - Git commit per meaningful change
  - No hardcoded file paths - fully reusable
- [x] **PHILOSOPHY.md** - Added Backlog Processor Pattern section
  - Documented universal workflow pattern
  - Added usage examples with multiple `--prologue` combinations
- [x] **BACKLOG.md** - Updated recommended commands
  - Universal backlog processor commands
  - Domain-specific alternatives

### Session 2026-01-24 (Verify CLI Commands)

- [x] **`sdqctl verify links`** - Added CLI command for links verifier
  - Scans markdown files for broken internal/external links
  - Options: `--json`, `--verbose`, `--path`
- [x] **`sdqctl verify traceability`** - Added CLI command with full features
  - `--coverage` flag shows detailed artifact coverage metrics
  - `--strict` flag treats warnings as errors
  - Coverage report format per ARTIFACT-TAXONOMY.md specification
  - Supports all artifact types: LOSS, HAZ, UCA, SC, REQ, SPEC, TEST, GAP, BUG, PROP, Q, IQ
- [x] **`sdqctl verify terminology`** - Added terminology consistency verifier
  - Detects deprecated terms (e.g., "quine" → "synthesis cycle")
  - Checks capitalization consistency (e.g., "nightscout" → "Nightscout", "stpa" → "STPA")
  - Auto-detects glossary from docs/GLOSSARY.md
  - Skips code blocks and CLI contexts
  - Options: `--glossary`, `--strict`, `--json`, `--verbose`
  - 12 tests in test_verifiers.py
- [x] **`sdqctl verify assertions`** - Added assertion tracing verifier
  - Scans Python, Swift, Kotlin, TypeScript for assertions
  - Detects trace IDs (REQ-NNN, SC-NNN, UCA-NNN) in messages/comments
  - `--require-message` and `--require-trace` flags for strict mode
  - Options: `--json`, `--verbose`, `--path`
  - 12 tests in test_verifiers.py
- [x] **`docs/NIGHTSCOUT-ECOSYSTEM.md`** - Created ecosystem conventions doc
  - workspace.lock.json configuration
  - Cross-project REFCAT reference syntax
  - Artifact ID ranges by project (loop, aaps, trio, xdrip, ns)
  - STPA artifact conventions for multi-project analysis
  - Verification commands and workflow patterns
- [x] **BACKLOG.md** - Updated verify command table with new CLI entries

### Session 2026-01-24 (Bug Investigation)

- [x] **BUG-001 investigation** - Compaction fails on empty context
  - Investigated reproduction steps with mock adapter
  - Cannot reproduce: empty context + COMPACT works correctly
  - Root cause: Issue likely specific to historical edge case or already fixed
  - Added regression test: `test_compact_with_empty_context` in `test_cycle_command.py`
  - Marked as RESOLVED in ARTIFACT-TAXONOMY.md

- [x] **ELIDE + RUN-RETRY validation** - Implement parse error for incompatible constructs
  - Added `validate_elide_chains()` method in `conversation.py`
  - Validates that RUN-RETRY cannot be used inside ELIDE chains
  - ELIDE merges steps into single turn; RUN-RETRY needs multiple turns
  - Integrated into `sdqctl validate` command
  - 4 tests in `test_conversation.py::TestElideChainValidation`
  - 1 CLI test in `test_cli.py::TestValidateCommand`

### Session 2026-01-24 (Q-012 Fix)

- [x] **Q-012: COMPACT directive now conditional** - Fix unconditional compaction
  - Added `session.needs_compaction(min_compaction_density)` check to COMPACT handling
  - Updated both `run.py` and `cycle.py` to check threshold before compacting
  - Shows "Skipping COMPACT - context below threshold" when skipped
  - Updated 2 tests, added `test_compact_executes_with_min_density_zero`
  - Marked Q-012 as FIXED in QUIRKS.md
  - **All quirks now resolved** - no active quirks remain
  - Commit: `d2e58df`

### Session 2026-01-24 (Error Handling Phase 1)

- [x] **Add `--strict` to all verify commands** - Production hardening
  - Added `--strict` flag to `verify refs`, `verify links`, `verify all`
  - `--strict` promotes warnings to errors for CI integration
  - Updated ERROR-HANDLING.md Phase 1 status to Complete
  - Added 4 tests in `test_cli.py::TestVerifyStrict`
  - Documentation: `sdqctl verify all --strict` for CI builds

### Session 2026-01-24 (SDK Metadata APIs Phase 1)

- [x] **Add metadata methods to adapters** - SDK v2 integration
  - Added `get_cli_status()`, `get_auth_status()`, `list_models()` to base adapter
  - Implemented in copilot adapter (calls SDK methods)
  - Implemented in mock adapter (returns test data)
  - Added 4 tests in `test_adapters.py::TestAdapterMetadataAPIs`
  - Updated SDK-METADATA-APIS.md Phase 1 to Complete

### Session 2026-01-24 (SDK Metadata APIs Phase 2)

- [x] **Enhanced status command** - SDK v2 metadata integration
  - Added `--models` flag to show available models with context/vision info
  - Added `--auth` flag to show authentication status details
  - Added `--all` flag for comprehensive status view
  - Added `-a/--adapter` option to specify which adapter to query
  - Implemented async metadata retrieval from adapters
  - Added 4 new tests in `tests/test_cli.py::TestStatusCommand`
  - Updated SDK-METADATA-APIS.md Phase 2 to Complete

### Session 2026-01-24 (Error Handling Phase 3)

- [x] **`--json-errors` global flag** - Structured error output for CI
  - Added `--json-errors` flag to main CLI group
  - Creates JSON output for all error types (MissingContextFiles, LoopDetected, etc.)
  - Suppresses progress messages when enabled (uses quiet mode)
  - Extended `core/exceptions.py` with:
    - `RunCommandFailed` exception for RUN directive failures
    - `exception_to_json()` function for exception serialization
    - `format_json_error()` function for JSON string output
    - New exit codes: `RUN_FAILED`, `VALIDATION_FAILED`, `VERIFY_FAILED`
  - Extended `utils/output.py` with:
    - `handle_error()` function for consistent error handling
    - `print_json_error()` function for ad-hoc JSON errors
  - Updated run and cycle commands to use structured error output
  - Added 3 tests in `tests/test_cli.py::TestJsonErrors`
  - Updated ERROR-HANDLING.md Phase 3 to Complete

### Session 2026-01-24 (REQUIRE Directive)

- [x] **`REQUIRE` directive** - Pre-flight checks for files and commands
  - Added `DirectiveType.REQUIRE` in `conversation.py`
  - Added `requirements` field to `ConversationFile` dataclass
  - Supports file requirements: `REQUIRE @pyproject.toml`
  - Supports command requirements: `REQUIRE cmd:git`
  - Supports multiple items: `REQUIRE @README.md cmd:python @tests/`
  - Supports glob patterns: `REQUIRE @*.py`
  - Added `validate_requirements()` method with file and command checking
  - Integrated into `sdqctl validate` command
  - Added 11 tests in `tests/test_conversation.py::TestRequireDirectiveParsing` and `TestRequireDirectiveValidation`
  - Added 2 CLI tests in `tests/test_cli.py::TestValidateCommand`
  - Updated directive count: 40 → 41 directives

### Session 2026-01-24 (ON-FAILURE/ON-SUCCESS Blocks)

- [x] **ON-FAILURE/ON-SUCCESS blocks** - Conditional execution after RUN (ERROR-HANDLING Phase 2)
  - Added `DirectiveType.ON_FAILURE`, `ON_SUCCESS`, `END` in `conversation.py`
  - Added `on_failure` and `on_success` list fields to `ConversationStep`
  - Implemented block parsing in `ConversationFile.parse()` with:
    - Block context tracking
    - Error checking for blocks without RUN, unclosed blocks, nested blocks
  - Added `_apply_directive_to_block()` helper for block-scoped directives
  - Updated `validate_elide_chains()` to detect blocks in ELIDE chains
  - Added `_execute_block_steps()` in `run.py` for executing block content
  - Updated RUN step handling to execute blocks based on exit code
  - Added 9 tests in `tests/test_conversation.py::TestOnFailureDirectiveParsing`
  - Updated directive count: 41 → 44 directives (ON-FAILURE, ON-SUCCESS, END)
  - Updated RUN-BRANCHING.md status to Implemented
  - Updated ERROR-HANDLING.md Phase 2 to Complete

### Session 2026-01-24 (Backlog Cohesiveness Audit)

- [x] **ARTIFACT-TAXONOMY.md** - Status updated: PROPOSAL → IMPLEMENTED (commit 0b3d463)
  - All artifact commands verified: `next`, `list`, `rename`, `retire`
- [x] **BACKLOG.md** - Fixed stale RUN-BRANCHING gap table (commit 35bbb2f)
  - ON-FAILURE/ON-SUCCESS marked as ✅ implemented
- [x] **ERROR-HANDLING.md** - Status updated: Draft → Implemented (commit 507a677)
  - ON-FAILURE/ON-SUCCESS moved to Implemented table

### Session 2026-01-24 (CHECK-* Aliases)

- [x] **Cohesiveness fix** - Fixed stale directive tables in BACKLOG.md (commit be4503f)
  - Updated directive count 41 → 44
  - Added Branching category (ON-FAILURE, ON-SUCCESS, END)
  - Removed ON-FAILURE/ON-SUCCESS from "NOT Implemented" table
- [x] **CHECK-* directive aliases** - Implemented verification shortcuts (commit 599166b)
  - Added `CHECK-REFS` (alias for `VERIFY refs`)
  - Added `CHECK-LINKS` (alias for `VERIFY links`)
  - Added `CHECK-TRACEABILITY` (alias for `VERIFY traceability`)
  - Updated directive count 44 → 47
  - Added 4 tests in `TestCheckAliasDirectives`
  - All 870 tests pass

### Session 2026-01-24 (INCLUDE Directive)

- [x] **`INCLUDE` directive** - Include other .conv files for workflow composition
  - Added `DirectiveType.INCLUDE` in `conversation.py`
  - Added `included_files` field to `ConversationFile` dataclass
  - Implemented `_process_include()` method with:
    - Recursive parsing of included files
    - Cycle detection to prevent infinite loops
    - Path resolution relative to including file
    - Merge of steps, context, prologues, epilogues, REFCAT refs
  - Metadata (MODEL, ADAPTER, etc.) is NOT merged from included files
  - Added 8 tests in `TestIncludeDirectiveParsing`
  - Updated directive count 47 → 48
  - All 878 tests pass

**Syntax:**
```dockerfile
# Include a common setup file
INCLUDE common/setup.conv

# Include from subdirectory
INCLUDE verification/stpa-checks.conv
```

**Use cases:**
- Reusable workflow fragments (common prologues, verification steps)
- Modular STPA workflow templates
- Shared context definitions across projects

### Session 2026-01-24 (VERIFY-TRACE Directive)

- [x] **`VERIFY-TRACE` directive** - Check specific trace links between artifacts
  - Added `DirectiveType.VERIFY_TRACE` in `conversation.py`
  - Added `verify_trace_links` field to `ConversationFile` dataclass
  - Parses `VERIFY-TRACE FROM_ID -> TO_ID` syntax (supports both `->` and `→`)
  - Added `verify_trace()` method to `TraceabilityVerifier`:
    - Checks if both artifacts exist in documentation
    - Detects direct links (same line with arrow)
    - Detects indirect links via BFS through trace chain
  - Added `sdqctl verify trace "FROM -> TO"` CLI command
  - Added 4 tests in `TestVerifyTraceDirective`
  - Added 5 tests in `TestTraceabilityVerifyTrace`
  - Updated directive count 48 → 49
  - All 887 tests pass

**Syntax:**
```dockerfile
# Check that UCA has safety constraint
VERIFY-TRACE UCA-001 -> SC-001

# Check scoped artifact links
VERIFY-TRACE UCA-BOLUS-003 → REQ-020
```

**CLI:**
```bash
# Verify specific trace link
sdqctl verify trace "UCA-001 -> SC-001"

# JSON output
sdqctl verify trace "SC-001 -> REQ-001" --json
```

---

## References
IMPORTANT: remember to cross reference our generic backlog against other task lists and backlogs.  Some quirk proposals become backlog items!

Additional IDEAS:  LSP support, for refcat and maybe other subcommands.

- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Workflow design principles
- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
- [SYNTHESIS-CYCLES.md](../docs/SYNTHESIS-CYCLES.md) - Iterative workflow patterns
- [VALIDATION-WORKFLOW.md](../docs/VALIDATION-WORKFLOW.md) - Validation/verification guide
- [ERROR-HANDLING.md](ERROR-HANDLING.md) - Error handling strategy and roadmap
