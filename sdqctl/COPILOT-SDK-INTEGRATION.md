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
    session_id="my-session",    # Enables stop file detection
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
4. `STOP_FILE` - Agent creates `STOPAUTOMATION-{hash}.json` (Q-002 feature)

**Agent stop signaling:** Use `{{STOP_FILE}}` template variable in prompts to tell the agent the exact filename to create when it needs to stop.

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
- Events auto-generated from schema (forward-compatible via `UNKNOWN`)
- Permission handler is async-capable (can prompt user)
- Intent is ephemeral (not persisted) - must capture explicitly
