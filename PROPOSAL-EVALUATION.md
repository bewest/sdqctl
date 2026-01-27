# Proposal vs Reality: sdqctl Evaluation Report

> **Purpose**: Compare the original `SDQCTL-PROPOSAL.md` (the vision) against the actual `sdqctl/` implementation (the reality) to document what was implemented, what was deferred, what emerged unexpectedly, and what was learned.

**Date**: January 27, 2026  
**Report Version**: 1.0

---

## Executive Summary

The original SDQCTL-PROPOSAL.md outlined a vendor-agnostic CLI for orchestrating AI-assisted development workflows with 4 core commands, 17 directives, and a 4-week implementation timeline.

**Reality exceeded expectations:**

| Metric | Proposed | Implemented | Variance |
|--------|----------|-------------|----------|
| Development time | 4 weeks | 8 days | **-75%** |
| Commands | 4 core | 18 commands | **+350%** |
| Directives | 17 | 74 | **+335%** |
| Lines of code | (unspecified) | 22,750 | — |
| Test count | (unspecified) | 1,562 | — |
| Documentation files | (unspecified) | 29 | — |

**Key finding**: The proposal captured the *correct problem* (manual orchestration of multi-context AI workflows) and *correct solution shape* (declarative ConversationFiles with context controls). However, the implementation revealed significantly more complexity in SDK integration, context management, and workflow patterns than anticipated.

---

## Feature Comparison: CLI Commands

### Proposed Commands vs Implementation

| Proposed Command | Implemented As | Status | Notes |
|------------------|----------------|--------|-------|
| `sdqctl run` | `sdqctl run` → `sdqctl iterate` | ✅ Implemented, then **deprecated** | `run` is now a thin wrapper to `iterate -n 1` |
| `sdqctl cycle` | `sdqctl iterate` | ✅ **Renamed** | "iterate" chosen for clarity (cycle implies singularity) |
| `sdqctl flow` | `sdqctl flow` | ✅ Implemented | Batch/parallel execution |
| `sdqctl apply` | `sdqctl apply` | ✅ Implemented | Per-component iteration with variable expansion |
| `sdqctl init` | `sdqctl init` | ✅ Implemented | Project initialization |
| `sdqctl status` | `sdqctl status` | ✅ Implemented | System and adapter status |
| `sdqctl resume` | `sdqctl resume` | ✅ Implemented | Checkpoint resume |
| `sdqctl compact` | — | ❌ **Not implemented** | Compaction is directive-driven, not CLI command |
| `sdqctl adapter` | — | ❌ **Not implemented** | Adapter management via config, not CLI |
| `sdqctl config` | — | ❌ **Not implemented** | Configuration via `.sdqctl.yaml` file |

### New Commands (Not in Proposal)

| Command | Purpose | Why It Emerged |
|---------|---------|----------------|
| `render` | Preview prompts without AI calls | Debugging template issues before expensive AI calls |
| `verify` | Static verification suite | Quality gates for workflows and documentation |
| `refcat` | Extract file content with line precision | Cross-repo context injection |
| `lsp` | Language server queries | Semantic type extraction for context |
| `drift` | Detect external repo changes | Ecosystem monitoring for alignment work |
| `plugin` | Plugin management | Decouple domain-specific extensions from core |
| `sessions` | Session management | SDK session lifecycle control |
| `artifact` | Artifact ID utilities | Traceability ID management |
| `validate` | Syntax validation | Pre-flight workflow checks |
| `show` | Display parsed workflow | Debugging aid |
| `help` | Built-in help system | User discoverability |

**Insight**: The proposal assumed 4 commands would suffice. Reality revealed the need for a comprehensive toolbox of 18 commands spanning execution, verification, debugging, and ecosystem management.

---

## Feature Comparison: ConversationFile Directives

### Proposed Directives vs Implementation

| Proposed Directive | Implemented | Status | Notes |
|--------------------|-------------|--------|-------|
| `MODEL` | `MODEL` | ✅ | Also added `MODEL-REQUIRES`, `MODEL-PREFERS`, `MODEL-POLICY` |
| `ADAPTER` | `ADAPTER` | ✅ | |
| `MODE` | `MODE` | ✅ | Values: audit, read-only, full |
| `MAX-CYCLES` | `MAX-CYCLES` | ✅ | |
| `CONTEXT` | `CONTEXT` | ✅ | Also added `CONTEXT-OPTIONAL`, `CONTEXT-EXCLUDE` |
| `CWD` | `CWD` | ✅ | Also added `RUN-CWD` |
| `PROMPT` | `PROMPT` | ✅ | |
| `CONTEXT-LIMIT` | `CONTEXT-LIMIT` | ✅ | |
| `ON-CONTEXT-LIMIT` | `ON-CONTEXT-LIMIT` | ✅ | |
| `ON-CONTEXT-LIMIT-PROMPT` | `ON-CONTEXT-LIMIT-PROMPT` | ✅ | |
| `CHECKPOINT-AFTER` | `CHECKPOINT-AFTER` | ✅ | |
| `CHECKPOINT-NAME` | `CHECKPOINT-NAME` | ✅ | Also added `SESSION-NAME` |
| `COMPACT-PRESERVE` | `COMPACT-PRESERVE` | ✅ | |
| `COMPACT-SUMMARY` | `COMPACT-SUMMARY` | ✅ | |
| `OUTPUT-FORMAT` | `OUTPUT-FORMAT` | ✅ | |
| `OUTPUT-FILE` | `OUTPUT-FILE` | ✅ | Also added `OUTPUT-DIR` |
| `RUN` | `RUN` | ✅ | Proposal mentioned but didn't detail |

### New Directive Categories (Not in Proposal)

#### Human-in-the-Loop (4 directives)
| Directive | Purpose |
|-----------|---------|
| `PAUSE` | Stop for human review |
| `CONSULT` | Pause with proactive question presentation |
| `CONSULT-TIMEOUT` | Expiration for CONSULT |
| `CHECKPOINT` | Named checkpoint |

#### RUN Extensions (10 directives)
| Directive | Purpose |
|-----------|---------|
| `RUN-ON-ERROR` | Error handling (stop/continue) |
| `RUN-OUTPUT` | When to include output (always/on-error/never) |
| `RUN-OUTPUT-LIMIT` | Max output chars |
| `RUN-ENV` | Environment variables |
| `RUN-TIMEOUT` | Command timeout |
| `RUN-CWD` | Working directory |
| `ALLOW-SHELL` | Enable shell features (security) |
| `RUN-ASYNC` | Asynchronous execution |
| `RUN-WAIT` | Wait for async command |
| `RUN-RETRY` | AI-assisted retry on failure |

#### Branching (3 directives)
| Directive | Purpose |
|-----------|---------|
| `ON-FAILURE` | Conditional block on RUN failure |
| `ON-SUCCESS` | Conditional block on RUN success |
| `END` | End conditional block |

#### Verification (10+ directives)
| Directive | Purpose |
|-----------|---------|
| `VERIFY` | Run verification (refs, links, traceability, etc.) |
| `VERIFY-ON-ERROR` | Error handling |
| `VERIFY-OUTPUT` | Output control |
| `VERIFY-LIMIT` | Output limit |
| `VERIFY-TRACE` | Single trace verification |
| `VERIFY-COVERAGE` | Coverage check |
| `CHECK-REFS` | Alias for VERIFY refs |
| `CHECK-LINKS` | Alias for VERIFY links |
| `CHECK-TRACEABILITY` | Alias for VERIFY traceability |

#### Context Injection (3 directives)
| Directive | Purpose |
|-----------|---------|
| `REFCAT` | Code excerpt with line precision |
| `LSP` | Type/symbol definitions from language server |
| `INCLUDE` | Include workflow fragments |

#### Prompt Injection (6 directives)
| Directive | Purpose |
|-----------|---------|
| `PROLOGUE` | Prepend to first prompt |
| `EPILOGUE` | Append to last prompt |
| `HEADER` | Prepend to output |
| `FOOTER` | Append to output |
| `HELP` | Inject help topics |
| `HELP-INLINE` | Inject help before specific prompt |

#### Compaction Control (8 directives)
| Directive | Purpose |
|-----------|---------|
| `COMPACT` | Trigger compaction |
| `COMPACT-PROLOGUE` | Before compacted summary |
| `COMPACT-EPILOGUE` | After compacted summary |
| `NEW-CONVERSATION` | Start fresh context |
| `ELIDE` | Merge adjacent elements |
| `INFINITE-SESSIONS` | SDK native compaction toggle |
| `COMPACTION-MIN` | Minimum density threshold |
| `COMPACTION-THRESHOLD` | Background compaction threshold |
| `COMPACTION-MAX` | Buffer exhaustion threshold |

#### Pre-flight (1 directive)
| Directive | Purpose |
|-----------|---------|
| `REQUIRE` | Pre-flight checks for files and commands |

**Insight**: The proposal identified 17 directives. Implementation required 74 directives (335% more) to handle real-world workflow complexity—particularly around command execution, error handling, verification, and context management.

---

## Feature Comparison: Adapter Interface

### Proposed Adapter Methods vs Implementation

| Proposed Method | Implemented | Status | Notes |
|-----------------|-------------|--------|-------|
| `start()` | `start()` | ✅ | |
| `stop()` | `stop()` | ✅ | |
| `create_session()` | `create_session()` | ✅ | |
| `send()` | `send()` | ✅ | Returns full response, not iterator |
| `get_context_usage()` | `get_context_usage()` | ✅ | Critical for compaction decisions |
| `compact()` | `compact()` | ✅ | |
| `checkpoint()` | `checkpoint()` | ✅ | |
| `restore()` | `restore()` | ⚠️ **Partial** | SDK session persistence waiting on SDK v2 |

### New Adapter Abstractions

| Abstraction | Purpose |
|-------------|---------|
| `AdapterConfig` | Configuration dataclass |
| `AdapterSession` | Session state wrapper |
| `SessionStats` | Token tracking, tool metrics |
| `TurnStats` | Per-turn statistics |
| `CompactionEvent` | Compaction tracking |
| `EventCollector` | SDK event handling |
| `CopilotEventHandler` | Copilot-specific event processing |

### Implemented Adapters

| Adapter | Status | Notes |
|---------|--------|-------|
| `copilot` | ✅ Implemented | 670 lines, primary adapter |
| `mock` | ✅ Implemented | Testing adapter |
| `claude` | ❌ **Deferred** | Listed in proposal, not implemented |
| `openai` | ❌ **Deferred** | Listed in proposal, not implemented |
| `ollama` | ❌ **Deferred** | Listed in proposal, not implemented |

**Insight**: The Copilot adapter alone required 670 lines of code and extensive event handling infrastructure. The proposal underestimated SDK integration complexity. Additional adapters were deprioritized in favor of depth over breadth.

---

## Feature Comparison: Architecture

### Proposed vs Actual Module Structure

| Proposed Module | Actual Implementation | Notes |
|-----------------|----------------------|-------|
| `sdqctl/cli.py` | `cli.py` | ✅ Main entrypoint |
| `sdqctl/commands/` | `commands/` (18 modules) | Grew from 6 proposed |
| `sdqctl/core/conversation.py` | `core/conversation/` (7 modules) | Split for maintainability |
| `sdqctl/core/context.py` | `core/context.py` | ✅ |
| `sdqctl/core/compaction.py` | Merged into adapter | Compaction is adapter-level |
| `sdqctl/core/checkpoint.py` | `core/session.py` | Merged with session |
| `sdqctl/core/session.py` | `core/session.py` | ✅ |
| `sdqctl/adapters/` | `adapters/` (6 modules) | Grew from 5 proposed |
| `sdqctl/utils/` | `utils/` | ✅ |

### New Modules (Not in Proposal)

| Module | Purpose | Lines |
|--------|---------|-------|
| `verifiers/` | Verification subsystem | 6 modules |
| `lsp/` | Language server integration | 1 module |
| `monitoring/` | Drift detection | 1 module |
| `plugins.py` | Plugin discovery | 1 module |
| `core/artifact_ids.py` | Traceability ID utilities | 213 lines |
| `core/help_commands.py` | Command help content | 550 lines |
| `core/help_topics.py` | Topic help content | 623 lines |
| `core/loop_detector.py` | Infinite loop detection | — |
| `core/refcat.py` | Line-level excerpts | — |
| `core/models.py` | Model requirements | — |

**Insight**: The proposal assumed a flat structure with ~8 modules. Reality required ~35 modules organized into subsystems. The ConversationFile parser alone needed 7 modules after refactoring (original was 1,819 lines).

---

## Unexpected Discoveries

### 1. Filename Semantics Influence Agent Behavior (Q-001)

**Discovery**: The agent interprets workflow filename words as semantic signals. A file named `progress-tracker.conv` caused the agent to focus on tracking/reporting rather than implementing changes.

**Solution**: Workflow name (`{{WORKFLOW_NAME}}`) is now excluded from prompts by default. Use `{{__WORKFLOW_NAME__}}` for explicit opt-in.

**Impact**: Template variable design now considers AI behavioral influence.

### 2. SDK Abort Events Are Never Emitted (Q-002)

**Expectation**: The SDK would emit `ABORT` events when detecting infinite loops.

**Reality**: Despite stress testing, the SDK never emitted abort signals.

**Solution**: Implemented client-side `LoopDetector` with heuristics (identical responses, minimal length, reasoning patterns) and a stop file mechanism (`STOPAUTOMATION-{hash}.json`).

**Impact**: Cannot rely on SDK for loop detection—must build client-side safeguards.

### 3. Event Handlers Persist Across Session (Q-014)

**Discovery**: SDK `.on()` handlers are never automatically removed. Each `send()` call that registers a handler adds another listener, causing exponential log duplication.

**Solution**: Register handlers once per session with a flag.

**Impact**: SDK event handling requires careful lifecycle management.

### 4. Token Tracking Requires Sync After Every Send (Q-019B, Q-020)

**Discovery**: Local token estimates diverge from SDK reality. Local tracking starts at 0 and only updates if explicitly synced.

**Solution**: After every `adapter.send()`, sync tokens from SDK.

**Impact**: Context percentage display requires active synchronization.

### 5. COMPACT Placement Determines Session Viability (v1 vs v2 workflow)

**Discovery**: The v1 workflow (6 phases, no strategic COMPACT) peaked at 55-58% context and completed 5.5/10 cycles. The v2 workflow (9 phases, COMPACT after Phase 6) peaked at 20% and completed 10/10 cycles.

**Solution**: Documented "Extended Workflow Pattern (v2)" with role shifts (Implementer → PM → Librarian) and COMPACT between phases.

**Impact**: Workflow design guidance now includes context management patterns.

### 6. Bidirectional Flow Emerges in Long Sessions

**Discovery**: Long-running sessions naturally exhibit two information flows:
- **Forward**: humans → decisions → BACKLOG.md → implementation
- **Backward**: implementation → discoveries → OPEN-QUESTIONS.md → humans

**Solution**: The CONSULT directive and question routing enable this pattern explicitly.

**Impact**: Workflows can now operate autonomously while surfacing decisions for human review.

---

## Lessons Learned

### 1. Process Over Domain

**Original assumption**: Domain-specific commands like `audit` or `migrate` would be needed.

**Learned**: Generic process commands (`iterate`, `apply`, `flow`) with `--prologue` injection are more reusable. Direction comes from context, not command names.

### 2. Typesetting Metaphor

**Original assumption**: CLI flags would follow programming conventions.

**Learned**: Document structure metaphors work better: `--prologue` (before), `--introduction` (cycle 1 only), `--epilogue` (after). Users understand these intuitively.

### 3. Agent Output Visibility

**Original assumption**: Quiet operation would be preferred.

**Learned**: Users can't debug what they can't see. Agent responses print to stdout by default. Verbosity levels (`-v`, `-vv`, `-vvv`) provide progressive detail.

### 4. Plugin System Necessity

**Original assumption**: All features would live in core.

**Learned**: Ecosystem teams (STPA, Nightscout alignment) need to extend sdqctl independently. Plugins > core features for domain-specific needs.

### 5. Compaction Is Strategy, Not Feature

**Original assumption**: Compaction would be a simple toggle.

**Learned**: Compaction requires strategic placement, threshold tuning, and preserve lists. Added 8 compaction directives and 3 CLI options.

### 6. Verification Is First-Class

**Original assumption**: Verification would be optional tooling.

**Learned**: Static verification (refs, links, traceability) is critical for workflow quality. Added `VERIFY` directive, `verify` command, and plugin verifier system.

---

## Deferred Features

### Waiting on SDK

| Feature | Blocker | Notes |
|---------|---------|-------|
| Infinite Sessions (native compaction) | SDK v2 protocol | Code ready, protocol not available |
| Session Persistence (resume by ID) | SDK v2 protocol | `sessions resume` implemented, SDK support pending |
| SDK ABORT Event Handling | SDK behavior | Code ready, SDK doesn't emit events |

### Deprioritized

| Feature | Reason | Priority |
|---------|--------|----------|
| Claude adapter | Copilot depth prioritized | P3 |
| OpenAI adapter | Copilot depth prioritized | P3 |
| Ollama adapter | Copilot depth prioritized | P3 |
| `VERIFY-IMPLEMENTED` directive | Pattern search in code | P2 |
| Cross-repo orchestration (`.flow` files) | Complexity | P3 |

### Rejected

| Feature | Reason |
|---------|--------|
| `SECTION` directive | "This is a programming language now" - complexity concern |
| `GOTO` directive | Rejected in favor of simpler ON-FAILURE blocks |

---

## Timeline: Proposed vs Actual

### Proposed (4 weeks)

| Phase | Planned | Features |
|-------|---------|----------|
| Phase 1 | Week 1 | Core CLI, ConversationFile parser, Copilot adapter |
| Phase 2 | Week 2 | Cycle, context tracking, compaction |
| Phase 3 | Week 3 | Flow, apply, parallel execution |
| Phase 4 | Week 4 | Additional adapters, documentation, tests |

### Actual (8 days)

| Phase | Actual | Features |
|-------|--------|----------|
| Phase 1 | Jan 20-21 | Foundation: CLI, parsing, adapter interface |
| Phase 2 | Jan 22-24 | Verification, pipeline, STPA workflows |
| Phase 3 | Jan 24-25 | SDK integration, quirk resolution (18 quirks) |
| Phase 4 | Jan 26 | Major refactoring (ConversationFile split, CLI modularization) |
| Phase 5 | Jan 27 | LSP, drift, plugins, benchmarks |

**Variance**: 75% faster than proposed, with 335% more features.

---

## Recommendations

### For Future Proposals

1. **Budget 3x directives** - Real workflows need far more controls than initially apparent
2. **Plan for SDK surprises** - Allocate time for quirk investigation and workarounds
3. **Design for observability first** - Users need to see what's happening
4. **Assume plugin extensibility** - Domain teams will need to extend independently

### For sdqctl Development

1. **Complete Claude/OpenAI adapters** - Vendor agnosticism remains a core value proposition
2. **Invest in VERIFY-IMPLEMENTED** - Pattern search would close the traceability loop
3. **Explore `.flow` files** - Cross-repo orchestration has real demand

### For Documentation

1. **Keep COLOPHON.md for "how it was built"** - Dogfooding story and metrics
2. **Keep this document for "proposal vs reality"** - Feature comparison and lessons
3. **Cross-reference both from README** - Different audiences need different perspectives

---

## Conclusion

The original SDQCTL-PROPOSAL.md correctly identified the problem space (manual orchestration of AI workflows) and proposed the right solution shape (declarative ConversationFiles with context controls). The implementation validated these assumptions while revealing that real-world requirements are significantly more complex.

**Key metrics:**
- **8 days** vs 4 weeks proposed (-75% time)
- **74 directives** vs 17 proposed (+335%)
- **18 commands** vs 4 proposed (+350%)
- **22,750 lines** of Python
- **1,562 tests**
- **18 quirks resolved**

The proposal succeeded as a vision document. The implementation succeeded by embracing the complexity that the proposal couldn't anticipate.

---

## References

- [SDQCTL-PROPOSAL.md](./SDQCTL-PROPOSAL.md) - Original proposal
- [sdqctl/README.md](./sdqctl/README.md) - Current implementation
- [sdqctl/docs/COLOPHON.md](./sdqctl/docs/COLOPHON.md) - Dogfooding story
- [sdqctl/docs/SDK-LEARNINGS.md](./sdqctl/docs/SDK-LEARNINGS.md) - SDK patterns
- [sdqctl/docs/QUIRKS.md](./sdqctl/docs/QUIRKS.md) - Known quirks
- [sdqctl/docs/PHILOSOPHY.md](./sdqctl/docs/PHILOSOPHY.md) - Design principles
- [sdqctl/docs/DIRECTIVE-REFERENCE.md](./sdqctl/docs/DIRECTIVE-REFERENCE.md) - All directives
- [sdqctl/docs/COMMANDS.md](./sdqctl/docs/COMMANDS.md) - All commands
