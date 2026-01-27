# Copilot SDK Integration Proposal for sdqctl

> **Status**: Draft  
> **Date**: 2026-01-21  
> **Scope**: Enhanced debugging, logging, and permission handling via Copilot SDK

## Executive Summary

The GitHub Copilot SDK exposes **34 event types** and a **permission handler system** that can significantly enhance sdqctl's observability and control. This proposal outlines how to integrate these capabilities for better debugging, logging, and workflow governance.

---

## SDK Event Architecture

### All 34 Event Types

```python
class SessionEventType(Enum):
    # Session lifecycle
    SESSION_START = "session.start"
    SESSION_RESUME = "session.resume"
    SESSION_IDLE = "session.idle"
    SESSION_ERROR = "session.error"
    SESSION_INFO = "session.info"
    SESSION_MODEL_CHANGE = "session.model_change"
    SESSION_HANDOFF = "session.handoff"
    SESSION_TRUNCATION = "session.truncation"
    SESSION_USAGE_INFO = "session.usage_info"
    SESSION_COMPACTION_START = "session.compaction_start"
    SESSION_COMPACTION_COMPLETE = "session.compaction_complete"
    
    # User/Assistant messages
    USER_MESSAGE = "user.message"
    ASSISTANT_TURN_START = "assistant.turn_start"
    ASSISTANT_TURN_END = "assistant.turn_end"
    ASSISTANT_INTENT = "assistant.intent"        # ← Key for intent tracking
    ASSISTANT_REASONING = "assistant.reasoning"
    ASSISTANT_REASONING_DELTA = "assistant.reasoning_delta"
    ASSISTANT_MESSAGE = "assistant.message"
    ASSISTANT_MESSAGE_DELTA = "assistant.message_delta"
    ASSISTANT_USAGE = "assistant.usage"
    
    # Tool execution
    TOOL_USER_REQUESTED = "tool.user_requested"
    TOOL_EXECUTION_START = "tool.execution_start"
    TOOL_EXECUTION_PARTIAL_RESULT = "tool.execution_partial_result"
    TOOL_EXECUTION_COMPLETE = "tool.execution_complete"
    
    # Sub-agents
    SUBAGENT_STARTED = "subagent.started"
    SUBAGENT_COMPLETED = "subagent.completed"
    SUBAGENT_FAILED = "subagent.failed"
    SUBAGENT_SELECTED = "subagent.selected"
    
    # Hooks
    HOOK_START = "hook.start"
    HOOK_END = "hook.end"
    
    # System
    SYSTEM_MESSAGE = "system.message"
    PENDING_MESSAGES_MODIFIED = "pending_messages.modified"
    ABORT = "abort"
    
    # Forward compatibility
    UNKNOWN = "unknown"
```

### Permission System

```python
# Permission request types
kind: Literal["shell", "write", "mcp", "read", "url"]

# Response options
"approved"
"denied-by-rules"
"denied-no-approval-rule-and-could-not-request-from-user"
"denied-interactively-by-user"
```

---

## Current State (copilot.py adapter)

| Event | Status | Current Use |
|-------|--------|-------------|
| `session.start` | ✅ Logged | Context info extraction |
| `session.error` | ✅ Logged | Error reporting |
| `session.idle` | ✅ Handled | Completion signal |
| `session.truncation` | ✅ Logged | Context size warnings |
| `session.handoff` | ✅ Logged | Session transfer tracking |
| `session.model_change` | ✅ Tracked | Model updates in stats |
| `assistant.intent` | ✅ Tracked | Intent history stored |
| `assistant.message` | ✅ Captured | Response extraction |
| `assistant.message_delta` | ✅ Streaming | Real-time output |
| `assistant.usage` | ✅ Tracked | Token counting |
| `tool.execution_start/complete` | ✅ Logged | Tool tracking with timing |
| `hook.start/hook.end` | ✅ Logged | Hook execution tracking |
| `subagent.started/completed/failed` | ✅ Logged | Subagent tracking |
| `abort` | ✅ **Raises AgentAborted** | Graceful workflow stop |
| **Permission handler** | ❌ Not implemented | - |

---

## Proposed Enhancements

### 1. Permission Handler Integration

**New ConversationFile Directives:**
```dockerfile
# Shell command permissions
ALLOW-SHELL echo,ls,cat,grep
DENY-SHELL rm,sudo,chmod

# Permission mode
PERMISSION-MODE strict      # Deny all not explicitly allowed
PERMISSION-MODE permissive  # Allow all not explicitly denied (default)
PERMISSION-MODE interactive # Prompt user for each request

# URL permissions
ALLOW-URLS https://api.github.com/*
DENY-URLS *
```

**Implementation:**
```python
def _create_permission_handler(self, config: AdapterConfig):
    async def on_permission_request(
        request: PermissionRequest, 
        invocation: dict
    ) -> PermissionRequestResult:
        kind = request.get("kind", "unknown")
        
        if kind == "read":
            return self._check_file_permission(request, config.file_restrictions)
        elif kind == "write":
            return self._check_file_permission(request, config.file_restrictions)
        elif kind == "shell":
            return self._check_shell_permission(request, config.shell_rules)
        elif kind == "url":
            return self._check_url_permission(request, config.url_rules)
        
        return {"kind": "denied-by-rules"}
    
    return on_permission_request
```

### 2. Intent Tracking

**Store and expose intent history:**
```python
@dataclass 
class SessionStats:
    current_intent: Optional[str] = None
    intent_history: list[dict] = field(default_factory=list)

# In event handler:
elif event_type == "assistant.intent":
    intent = getattr(data, "intent", None)
    if intent:
        stats.current_intent = intent
        stats.intent_history.append({
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "turn": stats.turns,
        })
        logger.info(f"🎯 Intent: {intent}")
        progress(f"  🎯 {intent}")
```

**ConversationFile:**
```dockerfile
DEBUG-INTENTS true
OUTPUT-INCLUDE intents
```

### 3. Structured Event Export

```python
@dataclass
class EventRecord:
    event_type: str
    timestamp: datetime
    data: dict
    session_id: str
    turn: int
    ephemeral: bool = False

class EventCollector:
    def export_jsonl(self, path: Path) -> None:
        with open(path, 'w') as f:
            for event in self.events:
                f.write(json.dumps(asdict(event)) + '\n')
```

**CLI Options:**
```bash
sdqctl run workflow.conv --event-log events.jsonl
sdqctl run workflow.conv -vvv  # TRACE level shows all events
```

### 4. Enhanced Tool Logging

```python
elif event_type == "tool.execution_start":
    tool_name = getattr(data, "tool_name", "unknown")
    args = getattr(data, "arguments", {})
    tool_call_id = getattr(data, "tool_call_id", None)
    
    stats.active_tools[tool_call_id] = {
        "name": tool_name,
        "args": args,
        "start_time": datetime.now(),
    }
    
    logger.info(f"🔧 Tool: {tool_name}")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"  Args: {json.dumps(args)[:500]}")

elif event_type == "tool.execution_complete":
    tool_call_id = getattr(data, "tool_call_id", None)
    success = getattr(data, "success", False)
    
    if tool_call_id in stats.active_tools:
        tool_info = stats.active_tools.pop(tool_call_id)
        duration = datetime.now() - tool_info["start_time"]
        
        status = "✓" if success else "✗"
        logger.info(f"  {status} {tool_info['name']} ({duration.total_seconds():.1f}s)")
```

### 5. Debug ConversationFile Directives

```dockerfile
# Enable debug output for specific categories
DEBUG session,tool,permission

# Verbose intent tracking
DEBUG-INTENTS true

# Log all permission decisions
DEBUG-PERMISSIONS true

# Export events to file
EVENT-LOG ./debug/events-{{DATETIME}}.jsonl

# Pause on permission denial
DEBUG-PAUSE-ON deny

# Include tool execution details in output
OUTPUT-INCLUDE tools
```

### 6. Comprehensive Session Metrics

```python
@dataclass 
class SessionMetrics:
    # Timing
    total_duration_ms: float = 0
    
    # Tokens
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    
    # Tools
    tool_calls_total: int = 0
    tool_calls_succeeded: int = 0
    tool_calls_failed: int = 0
    
    # Permissions
    permission_requests: int = 0
    permissions_approved: int = 0
    permissions_denied: int = 0
    
    # Intents
    unique_intents: set = field(default_factory=set)
    intent_changes: int = 0
    
    # Sub-agents
    subagent_invocations: int = 0
    subagent_failures: int = 0

    def to_summary(self) -> str:
        return f"""Session Metrics:
  Duration: {self.total_duration_ms/1000:.1f}s
  Tokens: {self.total_input_tokens} in / {self.total_output_tokens} out
  Tools: {self.tool_calls_total} ({self.tool_calls_succeeded} ok, {self.tool_calls_failed} failed)
  Permissions: {self.permissions_approved}/{self.permission_requests} approved
  Intents: {len(self.unique_intents)} unique"""
```

---

## Implementation Priority

### Phase 1: Core Debugging (High Priority)
- [ ] Intent tracking & exposure in SessionStats
- [ ] Enhanced tool logging with args/results  
- [ ] Event export to JSONL (`--event-log`)
- [ ] TRACE level (`-vvv`) shows all events

### Phase 2: Permission System (Medium Priority)
- [ ] Permission handler integration with `on_permission_request`
- [ ] Shell command rules (ALLOW-SHELL/DENY-SHELL)
- [ ] URL rules (ALLOW-URLS/DENY-URLS)
- [ ] Interactive permission mode

### Phase 3: Advanced Features (Lower Priority)
- [ ] Sub-agent lifecycle tracking
- [ ] Session handoff tracking
- [ ] Real-time event streaming API

---

## Example: Debug Session

```bash
# Maximum visibility
sdqctl run audit.conv -vvv --event-log debug.jsonl

# Output:
# [09:15:03] [TRACE] Event: session.start
# [09:15:03] [INFO] Session: branch=main, repo=myapp
# [09:15:04] [INFO] 🎯 Intent: Exploring codebase
# [09:15:05] [INFO] 🔧 Tool: grep
# [09:15:05] [DEBUG]   Args: {"pattern": "auth", "path": "lib/"}
# [09:15:06] [INFO]   ✓ grep (1.2s)
# [09:15:07] [INFO] 🎯 Intent: Analyzing authentication
# [09:15:08] [INFO] 🔐 Permission: write (allowed by ALLOW-FILES)
# [09:15:10] [INFO] Tokens: 4521 in / 892 out

# Event log (debug.jsonl):
{"event_type":"session.start","timestamp":"2026-01-21T09:15:03Z",...}
{"event_type":"assistant.intent","data":{"intent":"Exploring codebase"},...}
{"event_type":"tool.execution_start","data":{"tool_name":"grep"},...}
```

---

## Gap: SDK Abort Event Not Observed

### Current State (2026-01-22)

The SDK documents an `ABORT = "abort"` event type, and our adapter handles it:

```python
# From copilot.py lines 530-541
elif event_type == "abort":
    reason = getattr(data, "reason", None)
    logger.warning(f"🛑 Agent abort signal: {reason}")
    stats.abort_reason = reason
    done.set()
```

**However, stress testing revealed this event is never emitted by the SDK.** See `docs/LOOP-STRESS-TEST.md`.

### Test Evidence

| Test Scenario | Cycles | SDK Abort Event? | How Loop Was Detected |
|---------------|--------|------------------|----------------------|
| Loop elicit prompt | 1 | ❌ No | AI reasoning contained "in a loop" |
| Repeated identical prompt | 15 | ❌ No | Minimal response length (31 chars) |
| Minimal response prompt | 2 | ❌ No | Response < 50 chars threshold |

Event types captured: `assistant.*`, `session.*`, `tool.*`, `user.message` — but **no `abort`**.

### Expected vs Actual

| Expectation | Reality |
|-------------|---------|
| SDK detects agentic loops internally | Unknown - no signal emitted |
| SDK emits `abort` event with reason | Never observed in testing |
| Client can rely on structured signal | Must analyze content heuristically |

### Desired Behavior

We would like the SDK to emit an `abort` event when:

1. **Repetition detected** - Same prompt/response pattern N times
2. **Reasoning indicates loop** - AI's internal reasoning mentions being stuck
3. **Token budget exhausted** - Session approaching limits with no progress
4. **Tool call loops** - Same tool called repeatedly with same args

**Expected event schema:**
```json
{
  "type": "abort",
  "data": {
    "reason": "loop_detected" | "token_limit" | "repetition" | "user_requested",
    "details": "Detected 3 identical responses in sequence",
    "turn": 5,
    "confidence": 0.95
  }
}
```

### Current Workaround

The `LoopDetector` class provides client-side detection with four mechanisms:

```python
from sdqctl.core.loop_detector import LoopDetector, LoopReason

detector = LoopDetector(
    nonce="mytest123",          # Optional: override random nonce
    identical_threshold=2,      # N identical responses (Q-002: lowered from 3)
    min_response_length=100,    # Chars below = suspicious (Q-002: raised from 50)
)

# Check after each turn
if result := detector.check(reasoning, response, cycle_number):
    raise result  # LoopDetected exception
```

**Detection mechanisms:**
1. `REASONING_PATTERN` - AI mentions "in a loop", "repeated prompt", etc.
2. `IDENTICAL_RESPONSES` - Same response N times in row
3. `MINIMAL_RESPONSE` - Response under threshold after first cycle
4. `STOP_FILE` - Agent creates `STOPAUTOMATION-{nonce}.json` (Q-002 feature)

**Agent stop signaling (enabled by default):** Stop file instructions are automatically injected on the first prompt. The agent can create `{{STOP_FILE}}` to signal it needs human review. Use `--no-stop-file-prologue` to disable or `--stop-file-nonce=VALUE` to pin the nonce.

This is functional but:
- Requires content parsing (fragile for some mechanisms)
- May miss cases the SDK sees internally
- Adds latency vs native signal

### Feature Request

**Request:** Emit `abort` event when the SDK/agent detects it should stop.

**Rationale:**
1. The SDK likely has internal signals we can't observe
2. Structured events are more reliable than content parsing
3. Enables cleaner workflow orchestration (sdqctl, CI/CD)
4. Aligns with existing event-driven architecture

**Priority:** Medium-High — critical for robust agentic workflows

---

## Notes

- SDK is in **technical preview** - API may change
- **SDK v2 is available locally** at `../../copilot-sdk/python` with Protocol Version 2
- Events auto-generated from schema (forward-compatible via `UNKNOWN`)
- Permission handler is async-capable (can prompt user)
- Intent is ephemeral (not persisted) - must capture explicitly

---

## Gap: Programmatic Compaction API

**Status:** ❓ Partial - Slash command exists, no direct API  
**Investigated:** 2026-01-22

### Current State

The SDK **emits** compaction events but doesn't expose a direct API to **trigger** compaction:

**Events available (read-only):**
```python
SESSION_COMPACTION_START = "session.compaction_start"   # Fired when compaction begins
SESSION_COMPACTION_COMPLETE = "session.compaction_complete"  # Fired when done
```

**CopilotSession methods (no compact):**
```python
abort()           # Abort current operation
destroy()         # End session
get_messages()    # Get message history
on()              # Subscribe to events
send()            # Send message
send_and_wait()   # Send and await response
```

### Slash Command Works

The `/compact` slash command works when sent as a user message:

```bash
$ copilot -p "/compact"
The `/compact` command summarizes conversation history to reduce context window usage.
Since this is a fresh conversation with no prior history to summarize, there's nothing to compact.
```

### Current Implementation in sdqctl

```python
# sdqctl/adapters/copilot.py
async def compact(self, session, preserve, summary_prompt) -> CompactionResult:
    """Compact using Copilot's /compact slash command."""
    # Try /compact command (generates summary but doesn't reduce context)
    compact_prompt = f"/compact Preserve: {', '.join(preserve)}. {summary_prompt}"
    response = await self.send(session, compact_prompt)
    
    # Return the summary (context window not actually reduced)
    return CompactionResult(summary=response, ...)
```

### Testing Results (2026-01-22)

**Finding:** The `/compact` slash command generates a summary but **does NOT reduce the context window**.

```
Tokens before /compact: 9,076
Tokens after /compact:  27,392  ← INCREASED (summary added to context)
```

The `/compact` command:
- ✅ Generates a useful summary of the conversation
- ✅ Works as a user message
- ❌ Does NOT trigger actual context truncation
- ❌ Does NOT fire `session.compaction_start/complete` events
- ❌ Adds to token count rather than reducing it

**Conclusion:** `/compact` is a **summary generation** command, not a true compaction mechanism. To actually reduce context, we would need either:
1. A native `session.compact()` API that truncates message history
2. Manual session reset with summary injection

### Feature Request

**Ideal API:**
```python
# Programmatic compaction that actually reduces context
result = await session.compact(preserve=["key decisions"])
# result.tokens_before = 50000
# result.tokens_after = 5000  ← Actually reduced

# Or truncation API
await session.truncate(keep_last=10, summary="Previous context summary...")
```

**Benefits of native compaction:**
- Actually reduces token count
- SDK handles message history truncation
- Preserves internal structure
- Fires proper `session.compaction_*` events

### Current Best Practice

For now, the most reliable approach is **fresh session mode** for long workflows:
- Start new session each cycle
- Inject summary from previous session as context
- Reload CONTEXT files from disk (picks up any changes)

---

## Implemented: Client-Side Compaction (2026-01-23)

Since the SDK's `/compact` command doesn't reduce context, we implemented **client-side compaction with session reset**. This approach:

1. Uses `/compact` to generate a summary
2. Destroys the current session
3. Creates a new session with the summary injected as context
4. Continues with remaining workflow prompts

### New Directives

```dockerfile
# Content injected before the compacted summary
COMPACT-PROLOGUE This conversation has been compacted. Previous context:

# Content injected after the compacted summary
COMPACT-EPILOGUE Continue from the summary above.
```

### New CLI Option

```bash
# Skip compaction if context usage is below threshold
sdqctl run workflow.conv --min-compaction-density 30
# This skips compaction if context is less than 30% full
```

### Session Structure After Compaction

When a `COMPACT` directive triggers:
1. Current session is summarized via `/compact`
2. Old session is destroyed
3. New session receives:
   ```
   [COMPACT-PROLOGUE or default text]
   
   [Summary from /compact]
   
   [COMPACT-EPILOGUE or default text]
   ```
4. Workflow continues with remaining prompts

### Implementation

```python
# In CopilotAdapter
async def compact_with_session_reset(
    self,
    session: AdapterSession,
    config: AdapterConfig,
    preserve: list[str],
    compaction_prologue: Optional[str] = None,
    compaction_epilogue: Optional[str] = None,
) -> tuple[AdapterSession, CompactionResult]:
    # 1. Get summary
    summary = await self.send(session, "/compact ...")
    
    # 2. Destroy old session
    await self.destroy_session(session)
    
    # 3. Create new session with compacted context
    new_session = await self.create_session(config)
    compacted_context = f"{prologue}\n\n{summary}\n\n{epilogue}"
    await self.send(new_session, compacted_context)
    
    return new_session, CompactionResult(...)
```

This achieves actual token reduction by starting fresh while preserving context through the summary.

---

## Implemented: ELIDE Directive

The `ELIDE` directive enables merging adjacent workflow elements into a single prompt, eliminating unnecessary agent turns between them.

### Problem

Without ELIDE, each element gets its own agent turn:
```dockerfile
PROMPT Check the test output.
RUN pytest -v
PROMPT Fix any errors.
```
This generates 3 separate prompts with 3 responses, including a potentially wasteful "I see the test output..." response.

### Solution

The `ELIDE` directive merges the element above with the element below:
```dockerfile
PROMPT Check the test output.
RUN pytest -v
ELIDE
PROMPT Fix any errors.
# Becomes a single merged prompt:
#   Check the test output.
#   [pytest output]
#   Fix any errors.
```

### Benefits

1. **Token efficiency** - No wasted tokens on intermediate "acknowledgment" responses
2. **Faster execution** - Fewer API round trips
3. **Better context coherence** - Agent sees related information together

### Implementation

The `process_elided_steps()` function in `run.py`:
1. Scans steps for ELIDE markers
2. Merges consecutive elements connected by ELIDE
3. Creates `merged_prompt` steps with embedded RUN placeholders
4. Executes RUN commands inline and injects output before sending

```python
# Example merged step structure
ConversationStep(
    type="merged_prompt",
    content="Check output.\n\n{{RUN:0:pytest -v}}\n\nFix errors.",
    run_commands=["pytest -v"]  # Attached for inline execution
)
```

### Chaining

Multiple ELIDEs chain together:
```dockerfile
PROMPT Review.
ELIDE
RUN build
ELIDE
RUN test
ELIDE
PROMPT Fix all issues.
# All four elements become one prompt
```

---

## Implemented: Render Subcommand Restructuring

The render command has been restructured from a single command to a command group with subcommands.

### Old Way (Deprecated)
```bash
sdqctl run workflow.conv --render-only
sdqctl cycle workflow.conv --render-only
```

### New Way
```bash
sdqctl render run workflow.conv
sdqctl render cycle workflow.conv
sdqctl render apply workflow.conv
```

### New Features

**Plan Mode** - Show file references without expanding content:
```bash
sdqctl render run workflow.conv --plan
```

Output shows `@file` references and token estimates instead of full content:
```markdown
### Context Files
- `@lib/auth.js` (1,234 tokens est.)
- `@tests/auth.test.js` (567 tokens est.)

### Prompt 1
**Prompt (raw):**
Analyze the authentication module.
```

**Full Mode** (default) - Expands all content as before.

### Benefits

1. **Cleaner API** - `render run`, `render cycle`, `render apply` match the execution commands
2. **Plan mode** - Quick overview without expensive file expansion
3. **Better discoverability** - `sdqctl render --help` shows all options
4. **Backwards compatible** - `--render-only` still works (with deprecation warning)

---

## SDK v2 Capabilities (2026-01-24)

The Copilot SDK has been updated to Protocol Version 2 with significant new features. This section documents the new capabilities and their potential integration into sdqctl.

### New API Overview

| Feature | SDK API | Status | Proposal |
|---------|---------|--------|----------|
| **Infinite Sessions** | `infinite_sessions` config | ✅ Integrated | [SDK-INFINITE-SESSIONS](proposals/SDK-INFINITE-SESSIONS.md) |
| **Session Resume** | `client.resume_session(id)` | ✅ Adapter methods | [SDK-SESSION-PERSISTENCE](proposals/SDK-SESSION-PERSISTENCE.md) |
| **Session List** | `client.list_sessions()` | ✅ Adapter methods | [SDK-SESSION-PERSISTENCE](proposals/SDK-SESSION-PERSISTENCE.md) |
| **Session Delete** | `client.delete_session(id)` | ✅ Adapter methods | [SDK-SESSION-PERSISTENCE](proposals/SDK-SESSION-PERSISTENCE.md) |
| **Get Status** | `client.get_status()` | ✅ Integrated | [SDK-METADATA-APIS](proposals/SDK-METADATA-APIS.md) |
| **Get Auth Status** | `client.get_auth_status()` | ✅ Integrated | [SDK-METADATA-APIS](proposals/SDK-METADATA-APIS.md) |
| **List Models** | `client.list_models()` | ✅ Integrated | [SDK-METADATA-APIS](proposals/SDK-METADATA-APIS.md) |
| **Workspace Path** | `session.workspace_path` | Not captured | [SDK-INFINITE-SESSIONS](proposals/SDK-INFINITE-SESSIONS.md) |
| **Custom Session IDs** | `session_id="name"` | Not integrated | [SDK-SESSION-PERSISTENCE](proposals/SDK-SESSION-PERSISTENCE.md) |

### Infinite Sessions (Native Compaction)

The SDK now provides **automatic context management** with background compaction:

```python
session = await client.create_session({
    "model": "gpt-5",
    "infinite_sessions": {
        "enabled": True,
        "background_compaction_threshold": 0.80,  # Start compacting at 80%
        "buffer_exhaustion_threshold": 0.95,      # Block at 95%
    },
})

# Session workspace for artifacts
print(session.workspace_path)  # ~/.copilot/session-state/{session_id}/
```

**Events emitted:**
- `session.compaction_start` - Background compaction started
- `session.compaction_complete` - Compaction finished with token counts

**Impact on sdqctl:**
- Could replace client-side compaction in `cycle` mode
- Aligns with `--min-compaction-density` (skip if below threshold)
- Native handling is more efficient than session reset approach

### Session Persistence APIs

**Status**: Phase 1 Complete (2026-01-25) - Adapter methods implemented

```python
# sdqctl adapter usage (implemented):
adapter = CopilotAdapter()
await adapter.start()

# List all sessions
sessions = await adapter.list_sessions()
# Returns: [{"id": ..., "start_time": ..., "modified_time": ..., "summary": ..., "is_remote": ...}, ...]

# Resume existing session
session = await adapter.resume_session("my-analysis", config)

# Delete session permanently
await adapter.delete_session("my-analysis")
```

**SDK direct usage:**
```python
# List all sessions
sessions = await client.list_sessions()
# Returns: [{sessionId, startTime, modifiedTime, summary?, isRemote}, ...]

# Resume existing session (conversation history restored)
session = await client.resume_session("my-analysis")

# Delete session permanently
await client.delete_session("my-analysis")
```

**Remaining work (Phase 2-4):**
- `sdqctl sessions list/delete/cleanup` CLI commands
- `sdqctl resume SESSION_ID` for multi-day workflows
- Named sessions via `SESSION-NAME` directive

### Metadata APIs

```python
# CLI version and protocol
status = await client.get_status()
# {"version": "0.0.394", "protocolVersion": 2}

# Authentication state
auth = await client.get_auth_status()
# {"isAuthenticated": True, "authType": "user", "login": "bewest", ...}

# Available models with capabilities
models = await client.list_models()
# [{id, name, capabilities: {supports: {vision}, limits: {max_context_window_tokens}}, ...}]
```

**Impact on sdqctl:**
- Enhanced `sdqctl status` with CLI version, auth status
- Model discovery for `MODEL-REQUIRES` directive
- Capability-based model selection

### Cookbook Patterns

The SDK now includes a [Python Cookbook](../../copilot-sdk/cookbook/python/) with practical recipes:

| Recipe | Pattern | sdqctl Relevance |
|--------|---------|------------------|
| [Error Handling](../../copilot-sdk/cookbook/python/error-handling.md) | try/finally cleanup, timeout context | Adapter robustness |
| [Multiple Sessions](../../copilot-sdk/cookbook/python/multiple-sessions.md) | Parallel independent sessions | Future: parallel cycles |
| [Persisting Sessions](../../copilot-sdk/cookbook/python/persisting-sessions.md) | Resume by ID, list, delete | Multi-day workflows |
| [Managing Local Files](../../copilot-sdk/cookbook/python/managing-local-files.md) | AI-powered file organization | Example patterns |
| [PR Visualization](../../copilot-sdk/cookbook/python/pr-visualization.md) | MCP server + no custom tools | Tool-free patterns |

### Protocol Version

```python
# From copilot/sdk_protocol_version.py
SDK_PROTOCOL_VERSION = 2
```

The SDK requires Protocol Version 2 for all new features. Ensure Copilot CLI is updated to a compatible version.

### Next Steps

1. **P1: Infinite Sessions** - Integrate for `cycle` mode (see proposal)
2. **P1: Metadata APIs** - Enhance `sdqctl status` command
3. **P2: Session Persistence** - Enable resume workflows
4. **P2: Error Handling** - Adopt cookbook patterns in adapter
