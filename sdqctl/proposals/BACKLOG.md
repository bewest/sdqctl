# sdqctl Proposal Backlog

> **Last Updated**: 2026-01-23 (Gap Analysis Complete - All 4 Phases)  
> **Purpose**: Track open design questions, implementation work, and future proposals

---

## Executive Summary: Tooling Gap Analysis

**Analysis Date**: 2026-01-23 | **Phases Completed**: 4/4

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

#### P2: Directive Implementation (Deferred)

| Directive | Proposal | Complexity | Recommendation |
|-----------|----------|------------|----------------|
| `ON-FAILURE` | RUN-BRANCHING | High | Defer - synthesis cycles cover 80% of use cases |
| `ON-SUCCESS` | RUN-BRANCHING | High | Defer - pairs with ON-FAILURE |
| `VERIFY-TRACE` | STPA-INTEGRATION | N/A | ✅ Use `VERIFY traceability` instead |

### Key Findings

1. **All tooling commands implemented** - No missing CLI commands
2. **Verifier infrastructure complete** - 3 verifiers: `refs`, `links`, `traceability`
3. **Help system exceeds proposal** - 11 commands + 6 topics (proposal specified nested `guidance`)
4. **ON-FAILURE blocks deferred** - RUN-RETRY covers common retry patterns

---

## Current Proposals Status

| Proposal | Status | Implementation | Notes |
|----------|--------|----------------|-------|
| [RUN-BRANCHING](RUN-BRANCHING.md) | Ready | Phase 1 ✅, Phase 2 ❌ | RUN-RETRY done, ON-FAILURE pending |
| [VERIFICATION-DIRECTIVES](VERIFICATION-DIRECTIVES.md) | Ready | Phase 1-4 ✅ | All phases complete |
| [PIPELINE-ARCHITECTURE](PIPELINE-ARCHITECTURE.md) | Ready | ✅ Complete | --from-json + schema_version implemented |
| [STPA-INTEGRATION](STPA-INTEGRATION.md) | Draft | ✅ Core complete | Templates + traceability verifier done |
| [CLI-ERGONOMICS](CLI-ERGONOMICS.md) | Analysis Complete | N/A | Help implemented, no gaps remaining |
| [MODEL-REQUIREMENTS](MODEL-REQUIREMENTS.md) | Draft | ❌ Open Questions | Abstract model selection by capability |
| [ARTIFACT-TAXONOMY](ARTIFACT-TAXONOMY.md) | Draft | Phase 0-0.5 ✅ | Taxonomy + enumeration strategies defined |

---

## Proposal vs Implementation Gap Analysis

### RUN-BRANCHING.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `RUN-RETRY N "prompt"` | Phase 1 | ✅ `conversation.py`, `run.py` | None |
| `ON-FAILURE` block | Phase 2 | ❌ Not implemented | **Implementation needed** |
| `ON-SUCCESS` block | Phase 2 | ❌ Not implemented | **Implementation needed** |
| ELIDE + branching = parse error | Design | ❌ Not enforced | Validation gap |

### VERIFICATION-DIRECTIVES.md

| Feature | Proposed | Implemented | Gap |
|---------|----------|-------------|-----|
| `sdqctl verify refs` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `sdqctl verify all` CLI | Phase 2 | ✅ `commands/verify.py` | None |
| `VERIFY refs` directive | Phase 3-4 | ✅ `conversation.py` | None |
| `VERIFY-ON-ERROR` directive | Phase 3-4 | ✅ Implemented | None |
| `VERIFY-OUTPUT` directive | Phase 3-4 | ✅ Implemented | None |
| `VERIFY-LIMIT` directive | Phase 3-4 | ✅ Implemented | None |
| `links` verifier | Phase 1 | ✅ `verifiers/links.py` | None |
| `terminology` verifier | Phase 1 | ❌ Not implemented | Future work |
| `traceability` verifier | Phase 1 | ✅ `verifiers/traceability.py` | None |
| `assertions` verifier | Phase 1 | ❌ Not implemented | Future work |

**Currently available verifiers**: `refs`, `links`, `traceability` in `sdqctl/verifiers/`

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
| `VERIFY-TRACE` directive | Phase 3 | ❌ Not implemented | Future work |
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

### Currently Implemented (40 directives)

**Metadata**: `MODEL`, `ADAPTER`, `MODE`, `MAX-CYCLES`, `CWD`  
**Context**: `CONTEXT`, `CONTEXT-OPTIONAL`, `CONTEXT-EXCLUDE`, `CONTEXT-LIMIT`, `ON-CONTEXT-LIMIT`, `VALIDATION-MODE`  
**File Control**: `ALLOW-FILES`, `DENY-FILES`, `ALLOW-DIR`, `DENY-DIR`  
**Injection**: `PROLOGUE`, `EPILOGUE`, `HEADER`, `FOOTER`  
**Prompts**: `PROMPT`, `ON-CONTEXT-LIMIT-PROMPT`  
**Compaction**: `COMPACT`, `COMPACT-PRESERVE`, `COMPACT-SUMMARY`, `COMPACT-PROLOGUE`, `COMPACT-EPILOGUE`, `NEW-CONVERSATION`, `ELIDE`  
**Checkpoints**: `CHECKPOINT`, `CHECKPOINT-AFTER`, `CHECKPOINT-NAME`, `PAUSE`  
**Output**: `OUTPUT`, `OUTPUT-FORMAT`, `OUTPUT-FILE`, `OUTPUT-DIR`  
**RUN**: `RUN`, `RUN-ON-ERROR`, `RUN-OUTPUT`, `RUN-OUTPUT-LIMIT`, `RUN-ENV`, `RUN-CWD`, `RUN-TIMEOUT`, `ALLOW-SHELL`, `RUN-ASYNC`, `RUN-WAIT`, `RUN-RETRY`  
**Verify**: `VERIFY`, `VERIFY-ON-ERROR`, `VERIFY-OUTPUT`, `VERIFY-LIMIT`  
**Debug**: `DEBUG`, `DEBUG-INTENTS`, `EVENT-LOG`

### Proposed but NOT Implemented

| Directive | Source Proposal | Priority | Complexity | Notes |
|-----------|-----------------|----------|------------|-------|
| `ON-FAILURE` | RUN-BRANCHING | P1 | High | Block-based control flow |
| `ON-SUCCESS` | RUN-BRANCHING | P1 | High | Block-based control flow |
| `VERIFY-TRACE` | STPA-INTEGRATION | P2 | Medium | `VERIFY-TRACE UCA-001 -> REQ-020` |
| `VERIFY-COVERAGE` | STPA-INTEGRATION | P2 | Medium | Check trace coverage % |
| `VERIFY-IMPLEMENTED` | STPA-INTEGRATION | P2 | Medium | Pattern search in code |
| `INCLUDE` | STPA-INTEGRATION | P3 | Low | Include other .conv files |
| `CHECK-REFS` | VERIFICATION-DIRECTIVES | P3 | Low | Alias for `VERIFY refs` |
| `CHECK-LINKS` | VERIFICATION-DIRECTIVES | P3 | Low | Alias for `VERIFY links` |
| `CHECK-TRACEABILITY` | VERIFICATION-DIRECTIVES | P3 | Low | Alias for `VERIFY traceability` |

### Rejected Directives (per proposals)

| Directive | Source | Rejection Reason |
|-----------|--------|------------------|
| `SECTION` | RUN-BRANCHING | "This is a programming language now" - GOTO considered harmful |
| `GOTO` | RUN-BRANCHING | Rejected in favor of simpler ON-FAILURE blocks |

### Directive Candidates NOT in Proposals

Potential additions based on usage patterns:

| Candidate | Description | Use Case |
|-----------|-------------|----------|
| `REQUIRE` | Fail if file/tool missing | Pre-flight checks |
| `GATE` | Wait for condition | CI integration |
| `TIMEOUT` | Global workflow timeout | Long-running protection |
| `RETRY-LIMIT` | Global retry cap | Token budget control |
| `COMPACT-IF-NEEDED` | Conditional compaction | Skip compaction below threshold (see [Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional)) |
| `INCLUDE-HELP` | Inject help topic into prompt | Agent workflow authoring (see below) |

### Help System: Agent Accessibility Gap

> **Discovered:** 2026-01-23  
> **Status:** Documented - future enhancement

#### Current State

Help content is stored inline in Python code (`sdqctl/commands/help.py`):
- `TOPICS` dict: 6 topics (directives, adapters, workflow, variables, context, examples)
- `COMMAND_HELP` dict: 11 commands
- `get_overview()` function: returns markdown overview

**Programmatic access exists** but is Python-only:
```python
from sdqctl.commands.help import TOPICS, COMMAND_HELP, get_overview
TOPICS["directives"]  # Returns full directive reference as markdown
```

#### Gap: No Help Directive

Agents authoring workflows must manually copy/paste documentation into PROLOGUE:
```dockerfile
# Current workaround - manual injection
PROLOGUE """
You are implementing an sdqctl workflow. Available directives:
- CONTEXT: Include file patterns
- PROMPT: Send prompt to AI
- RUN: Execute shell command
...
"""
```

#### Proposed Enhancement: `HELP` Directive

```dockerfile
# Proposed - automatic injection
HELP directives              # Inject full directive reference
HELP workflow                # Inject format guide
HELP variables context       # Inject multiple topics
```

**Implementation sketch:**
```python
# In conversation.py DirectiveType enum:
HELP = "HELP"

# In parser:
case DirectiveType.HELP:
    topics = directive.value.split()
    for topic in topics:
        if topic in TOPICS:
            conv.prologues.append(TOPICS[topic])
```

**Note**: This is simpler than `INCLUDE` - it only injects built-in help content, not external files.

#### Alternative: Agent-Optimized Help Format

Current help is human-optimized (tables, examples). Could add LLM-optimized variants:
- Structured examples with input→output pairs
- Common anti-patterns to avoid
- Decision trees for directive selection
- JSON-LD or structured data format

#### Priority

**P1 (Medium)** - Simple implementation, useful for meta-workflows that synthesize other workflows. See [Open Questions §HELP Directive](#p1-help-directive).

### Compaction Policy: Known Gaps

> **See Also:** [QUIRKS.md Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) and [Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional)

The compaction threshold system has documented gaps between expected and actual behavior:

| Feature | Expected | Actual | Gap |
|---------|----------|--------|-----|
| `--min-compaction-density` | Skip compaction if below N% | **NOT WIRED** - parameter ignored | [Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) |
| `COMPACT` directive | Conditional on threshold | **UNCONDITIONAL** - always triggers | [Q-012](../docs/QUIRKS.md#q-012-compact-directive-is-unconditional) |
| `CONTEXT-LIMIT N%` | Compact before any turn exceeding N% | **Cycle boundaries only** | [Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) |
| Two-tier thresholds | Operating + max thresholds | **Single threshold only** | [Q-011](../docs/QUIRKS.md#q-011-compaction-threshold-options-not-fully-wired) |

**Current workaround:** Use `cycle -n N` for automatic conditional compaction at cycle boundaries. Explicit `COMPACT` directives run unconditionally.

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
| `sdqctl artifact rename` command | P3 | 2 hours | Update all references |
| Nightscout ecosystem conventions doc | P3 | 1 hour | Cross-project patterns |

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

---

## References

- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Workflow design principles
- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
- [SYNTHESIS-CYCLES.md](../docs/SYNTHESIS-CYCLES.md) - Iterative workflow patterns
- [VALIDATION-WORKFLOW.md](../docs/VALIDATION-WORKFLOW.md) - Validation/verification guide
