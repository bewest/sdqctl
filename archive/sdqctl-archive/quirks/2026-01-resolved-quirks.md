# Archived Resolved Quirks

> **Archived:** 2026-01-25  
> **Source:** `docs/QUIRKS.md`  
> **Purpose:** Preserve investigation context and learnings from resolved quirks

---

## Table of Contents

| ID | Description | Resolution Date |
|----|-------------|-----------------|
| [Q-020](#q-020-context-percentage-shows-0-until-compaction) | Context percentage shows 0% | 2026-01-26 |
| [Q-016](#q-016-undefined-name-bugs-f821) | Undefined Name Bugs (F821) | 2026-01-25 |
| [Q-018](#q-018-session-id-mismatch-between-checkpoint-and-sdk) | Session ID Mismatch | 2026-01-25 |
| [Q-019B](#q-019b-context-percentage-diverges-after-compaction) | Context percentage divergence | 2026-01-25 |
| [Q-014](#q-014-event-handler-multiplexing-in-accumulate-mode) | Event Handler Multiplexing | 2026-01-25 |
| [Q-015](#q-015-duplicate-tool-calls-at-session-termination) | Duplicate Tool Calls | 2026-01-25 |
| [Q-013](#q-013-tool-name-shows-unknown-in-completion-logs) | Tool Name "unknown" | 2026-01-25 |
| [Q-011](#q-011-compaction-threshold-options-not-fully-wired) | Compaction Threshold | 2026-01-24 |
| [Q-010](#q-010-compact-directive-ignored-by-cycle-command) | COMPACT Ignored | 2026-01-22 |
| [Q-005](#q-005-tool-names-show-unknown-in-verbose-logs) | Tool Names "unknown" | 2026-01-22 |
| [Q-004](#q-004-verbose-logging-shows-duplicate-content) | Duplicate Logging | 2026-01-22 |
| [Q-003](#q-003-template-variables-encourage-problematic-patterns) | Template Variables | 2026-01-22 |
| [Q-002](#q-002-sdk-abort-events-not-emitted) | SDK Abort Events | 2026-01-22 |
| [Q-001](#q-001-workflow-filename-influences-agent-behavior) | Workflow Filename Influence | 2026-01-22 |

---

## Q-020: Context Percentage Shows 0% Until Compaction

**Priority:** P0 - Critical  
**Discovered:** 2026-01-26  
**Status:** ✅ FIXED (2026-01-26)

### Description

Context percentage in progress output shows **0%** at session start and during prompts, even though the SDK is tracking actual token usage. The percentage only becomes accurate after compaction.

### Evidence

From `consult-test-logs/consult-test-2026-01-25-125626.log`:
```
  Prompt 1/2 (ctx: 0%): Sending...
  Prompt 1/2 (ctx: 0%): Complete (12.1s)
```

### Root Cause

The SDK tracks tokens via `stats.total_input_tokens` (updated on each `assistant.usage` event), but sdqctl's local `ContextWindow.used_tokens` was only synced from the SDK **after compaction** (Q-019B fix), not after each prompt send.

**Locations needing sync:**
- `run.py` ~line 858 (after `ai_adapter.send()`)
- `run.py` ~line 1023 (after `ai_adapter.send()` in mixed prompt path)
- `iterate.py` ~line 1056 (after `ai_adapter.send()`)

### Resolution

Added token sync after each `ai_adapter.send()` call:
```python
# Sync local context tracking with SDK's actual token count (Q-020 fix)
tokens_used, max_tokens = await ai_adapter.get_context_usage(adapter_session)
session.context.window.used_tokens = tokens_used
session.context.window.max_tokens = max_tokens
```

**Files modified:** `sdqctl/commands/run.py`, `sdqctl/commands/iterate.py`

### Related

- Q-019B was a **partial fix** that only addressed post-compaction divergence

---

## Q-016: Undefined Name Bugs (F821)

**Priority:** P0 - Critical  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25)

### Description

Ruff linting discovered 5 undefined name errors (F821) that will cause `NameError` exceptions at runtime:

| Location | Variable | Root Cause |
|----------|----------|------------|
| `run.py:568` | `quiet` | Variable not passed to function scope |
| `run.py:1172` | `restrictions` | Not defined in RUN-RETRY block |
| `run.py:1173` | `show_streaming` | Not defined in RUN-RETRY block |
| `run.py:1376` | `pending_context` | Not defined in VERIFY step handler |
| `copilot.py:1001` | `ModelRequirements` | Forward ref string but missing import |

### Resolution

All 5 bugs fixed with minimal changes:

| Bug | Fix Applied |
|-----|-------------|
| `quiet` | Changed to `verbosity > 0` (warning only at non-quiet) |
| `restrictions` | Changed to `conv.file_restrictions` |
| `show_streaming` | Changed to `True` (matches adapter config) |
| `pending_context` | Removed dead code line (verify_output already in session) |
| `ModelRequirements` | Added `TYPE_CHECKING` import block |

**Files modified:** `sdqctl/commands/run.py`, `sdqctl/adapters/copilot.py`

---

## Q-018: Session ID Mismatch Between Checkpoint and SDK

**Priority:** P2 - Medium (UX friction)  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25)

### Description

When a workflow pauses at CONSULT (or PAUSE), sdqctl saves a checkpoint with a short session ID (e.g., `8b41b034`), but the Copilot SDK session uses a full UUID (e.g., `9859f571-b938-4b72-a8d0-472c4c3304e3`). The resume commands don't work with the checkpoint ID.

### Resolution

Implemented: Store SDK session UUID in checkpoint metadata.

**Changes:**
1. Added `sdk_session_id` field to `AdapterSession` dataclass
2. Capture `copilot_session.session_id` in `CopilotAdapter.create_session()`
3. Store `sdk_session_id` in `pause.json` checkpoint
4. Resume messages now show the correct SDK session ID

**Files modified:** `adapters/base.py`, `adapters/copilot.py`, `core/session.py`, `commands/run.py`, `commands/iterate.py`

---

## Q-019B: Context Percentage Diverges After Compaction

**Priority:** P2 - Data  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25)

### Description

After compaction, progress display showed reduced percentage but logger showed original high percentage due to two separate token tracking systems not being synchronized.

### Resolution

Added token sync after compaction in both `run.py` and `cycle.py`:
```python
tokens_after, max_tokens = await ai_adapter.get_context_usage(adapter_session)
session.context.window.used_tokens = tokens_after
```

---

## Q-014: Event Handler Multiplexing in Accumulate Mode

**Priority:** P0 - Critical  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25)

### Description

When using `--session-mode=accumulate` with the `iterate` command, event handlers were registered multiple times, causing exponential log duplication and duplicate tool execution.

### Evidence

A 30-minute, 5-cycle session showed:
- 3 turns "starting" at the same millisecond (impossible - indicates 3 event handlers)
- By session end: 25x repeated log lines per event
- **3,667 turns logged** vs expected ~150
- **3,878 tool calls** vs expected ~200

### Root Cause

**Location:** `sdqctl/adapters/copilot.py`, line 655

```python
copilot_session.on(on_event)  # Called every prompt, NEVER removed!
```

Each `send()` call registered a new event handler. In accumulate mode with N prompts, N handlers all fired for each event.

### Resolution

Register handler once per session using `stats.handler_registered` flag:
```python
if not stats.handler_registered:
    copilot_session.on(on_event)
    stats.handler_registered = True
```

---

## Q-015: Duplicate Tool Calls at Session Termination

**Priority:** P0 - Critical  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25) - by Q-014 fix

### Description

When agent creates STOPAUTOMATION file, the same tool call executed 15+ times. 15+ bash processes spawned unnecessarily.

### Root Cause

Symptom of Q-014 (event handler multiplexing). Each handler fired the same tool call independently.

### Resolution

Fixed by Q-014 - event handlers now register once per session.

---

## Q-013: Tool Name Shows "unknown" in Completion Logs

**Priority:** P1 - Medium  
**Discovered:** 2026-01-25  
**Status:** ✅ FIXED (2026-01-25)

### Description

Despite Q-005 being marked fixed, tool completion logs still showed "unknown" in many cases. A session showed **1,695 entries** with `✓ unknown`.

### Root Cause

The regression was caused by Q-014 (event handler multiplexing). Multiple handlers corrupted `stats.active_tools` dictionary.

### Resolution

Two-part fix:
1. Q-014 fix prevents dictionary corruption
2. Added fallback: use stored tool name from start event when direct extraction fails

---

## Q-011: Compaction Threshold Options Not Fully Wired

**Priority:** P2 - Low  
**Discovered:** 2026-01-23  
**Status:** ✅ FIXED (2026-01-24)

### Description

The `COMPACT` directive always triggered compaction regardless of `--min-compaction-density` setting.

### Resolution

`COMPACT` directive now checks `session.needs_compaction(min_compaction_density)` before executing. Shows "Skipping COMPACT - context below threshold" when skipped.

---

## Q-010: COMPACT Directive Ignored by Cycle Command

**Priority:** P1 - Medium  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED

### Description

The `COMPACT` directive was parsed correctly but the `iterate` command only iterated through `conv.prompts`, ignoring COMPACT, CHECKPOINT, and other step-based directives.

### Root Cause

```python
# cycle.py (before fix) - only processed prompts
for prompt in conv.prompts:  # ← missing COMPACT handling
```

### Resolution

Refactored `cycle.py` to iterate `conv.steps` instead of just `conv.prompts`.

---

## Q-005: Tool Names Show "unknown" in Verbose Logs

**Priority:** P2 - Low  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED

### Description

Tool execution events showed "unknown" as tool name instead of actual tool being executed.

### Root Cause

SDK provides tool info in multiple locations (`data.tool_name`, `data.tool_requests`). Original `_get_field()` helper only checked top-level fields.

### Resolution

Added `_get_tool_name()` helper that checks direct fields then falls back to `tool_requests[0].name`.

---

## Q-004: Verbose Logging Shows Duplicate Content

**Priority:** P2 - Low  
**Discovered:** 2026-01-22  
**Status:** ✅ IMPROVED

### Description

At `-vvvv` (maximum verbosity), delta messages contained duplicate material.

### Resolution

Removed reasoning delta logging. Recommendation: use `-v` for useful operational output.

---

## Q-003: Template Variables Encourage Problematic Patterns

**Priority:** P2 - Low  
**Discovered:** 2026-01-22  
**Status:** ✅ RESOLVED

### Description

Example workflows used `{{WORKFLOW_NAME}}` in headers, which could influence agent behavior.

### Resolution

Fixed by Q-001 (WORKFLOW_NAME excluded from prompts by default). Examples updated to use literal descriptions with explicit role PROLOGUE patterns.

---

## Q-002: SDK Abort Events Not Emitted

**Priority:** P1 - Medium  
**Discovered:** 2026-01-22  
**Status:** ✅ IMPROVED

### Description

The Copilot SDK documents an `ABORT` event type, but stress testing revealed it's **never emitted**, even when agent is stuck in loops.

### Evidence

| Test Scenario | SDK Abort Event? | Detection Method |
|---------------|------------------|------------------|
| Loop elicit prompt | ❌ No | AI reasoning contained "in a loop" |
| Repeated identical prompt | ❌ No | Minimal response length (31 chars) |

### Resolution

1. **Lowered detection thresholds** for faster loop detection
2. **Added stop file detection** - agent can create `STOPAUTOMATION-{hash}.json`
3. **Template variables** - `${STOP_FILE}` available in prompts

---

## Q-001: Workflow Filename Influences Agent Behavior

**Priority:** P0 - High Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED

### Description

The `{{WORKFLOW_NAME}}` template variable extracts the filename stem. When used in prompts, **the agent uses the filename words as semantic signals** about its intended role.

When filename contains words like "tracker", "doc", or "report", the agent may:
- Resist making code edits
- Focus on generating reports instead of modifying files
- Provide descriptions of changes instead of making them

### Resolution

`WORKFLOW_NAME` and `WORKFLOW_PATH` are now **excluded from prompts by default**.

**Migration:**
- For agent-visible content: use `{{__WORKFLOW_NAME__}}` (underscore prefix = explicit opt-in)
- For output paths: `{{WORKFLOW_NAME}}` continues to work unchanged

---

## SDK Learnings Summary

### Key Patterns Discovered

1. **Filename Semantics** (Q-001): Agent interprets filename words as role signals. Use implementation-oriented names or exclude workflow name from prompts.

2. **No SDK Abort Events** (Q-002): Can't rely on structured SDK signals for loop detection. Use client-side heuristics + stop file mechanism.

3. **Event Handler Lifecycle** (Q-014): SDK `.on()` handlers persist across session. Register once per session, not per-send.

4. **Token Tracking Divergence** (Q-019B): SDK and local token estimates diverge after compaction. Sync from SDK after any context-modifying operation.

5. **Tool Info Locations** (Q-005, Q-013): SDK provides tool info in multiple locations. Always check `tool_requests[0].name` as fallback.

### Testing Patterns

- **Accumulate mode** exposes event handler bugs
- **Multi-cycle sessions** expose resource leaks
- **Loop stress testing** reveals SDK limitations
- **Linting catches undefined variable bugs** before runtime

---

## See Also

- [QUIRKS.md](../../docs/QUIRKS.md) - Active quirks tracker
- [docs/SDK-LEARNINGS.md](../../docs/SDK-LEARNINGS.md) - Extracted patterns
- [LOOP-STRESS-TEST.md](../../docs/LOOP-STRESS-TEST.md) - Testing methodology
