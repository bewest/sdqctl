# SDK Learnings

> **Extracted:** 2026-01-25  
> **Source:** [Resolved Quirks Archive](../archive/quirks/2026-01-resolved-quirks.md)  
> **Purpose:** Actionable patterns for working with the Copilot SDK

---

## Behavioral Patterns

### 1. Filename Semantics Influence Agent Role (Q-001)

The agent interprets workflow filename words as semantic signals about its intended role.

**Problem:** A file named `progress-tracker.conv` caused the agent to focus on tracking/reporting rather than implementing changes.

**Solution:**
- Use implementation-oriented filenames: `implement-*.conv`, `edit-*.conv`
- `{{WORKFLOW_NAME}}` is excluded from prompts by default
- Use `{{__WORKFLOW_NAME__}}` for explicit opt-in when needed

### 2. SDK Abort Events Are Not Emitted (Q-002)

The SDK documents an `ABORT` event type, but **it is never emitted** during stress testing.

**Implication:** Cannot rely on structured SDK signals for loop detection.

**Solution:**
- Use client-side `LoopDetector` with heuristics (identical responses, minimal length, reasoning patterns)
- Implement stop file mechanism (`STOPAUTOMATION-{hash}.json`)
- Lower detection thresholds for faster response

---

## Session Management

### 3. Event Handlers Persist Across Session (Q-014)

SDK `.on()` handlers are never automatically removed. Each `send()` call that registers a handler adds another listener.

**Problem:** In accumulate mode with N prompts, N handlers all fire for each event → exponential duplication.

**Solution:**
```python
# Register handler ONCE per session
if not stats.handler_registered:
    copilot_session.on(on_event)
    stats.handler_registered = True
```

### 4. Token Tracking Requires Sync After Every Send (Q-019B, Q-020)

The SDK and local token estimates diverge. Local tracking starts at 0 and only updates if explicitly synced.

**Problem:** 
- Q-019B: After SDK compacts, local `used_tokens` still shows old value
- Q-020: Before any compaction, local shows 0% even with real token usage

**Solution:**
```python
# After EVERY ai_adapter.send() call, sync from SDK
tokens_used, max_tokens = await adapter.get_context_usage(session)
session.context.window.used_tokens = tokens_used
session.context.window.max_tokens = max_tokens
```

**Key insight:** The SDK tracks tokens internally via `assistant.usage` events. The local `ContextWindow` is just a mirror and must be explicitly synced after each interaction.

---

## Tool Handling

### 5. Tool Info in Multiple Locations (Q-005, Q-013)

SDK provides tool information in different event fields depending on the event type.

**Locations:**
- `data.tool_name` - Direct field (most common)
- `data.name` - Generic name field
- `data.tool_requests[0].name` - Nested list (for batch calls)

**Solution:**
```python
def _get_tool_name(data: Any) -> str:
    # Try direct fields first
    name = _get_field(data, "tool_name", "name", "tool")
    if name:
        return name
    
    # Fallback to tool_requests
    tool_requests = getattr(data, "tool_requests", None)
    if tool_requests and len(tool_requests) > 0:
        return getattr(tool_requests[0], "name", "unknown")
    
    return "unknown"
```

### 6. Store Tool Start Info for Completion (Q-013)

Tool completion events may not contain the tool name. Track start info in a dictionary keyed by `tool_call_id`.

```python
# On tool.execution_started
stats.active_tools[tool_call_id] = {
    "name": tool_name,
    "start_time": datetime.now()
}

# On tool.execution_complete
if tool_call_id in stats.active_tools:
    tool_info = stats.active_tools.pop(tool_call_id)
    if tool_name == "unknown":
        tool_name = tool_info.get("name", "unknown")
```

---

## Testing Recommendations

### Stress Test Patterns That Expose Bugs

| Pattern | What It Exposes |
|---------|-----------------|
| `--session-mode=accumulate` | Event handler leaks, state corruption |
| Multi-cycle sessions (10+) | Resource leaks, token tracking drift |
| Loop-inducing prompts | SDK abort limitations, detection gaps |
| Compaction boundaries | Token sync issues, display divergence |

### Linting Catches Runtime Bugs

Ruff linting with `--select F821` found 5 undefined name bugs that would crash at runtime. Run linting before commits.

---

## Quick Reference

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Agent won't edit files | Filename semantics | Implementation-oriented name or exclude `{{WORKFLOW_NAME}}` |
| Stuck in loop, no abort | SDK limitation | Use client-side `LoopDetector` |
| Duplicate log entries | Handler multiplexing | Register handler once per session |
| Wrong context percentage | Token tracking drift | Sync tokens from SDK after compaction |
| Tool shows "unknown" | Info in nested field | Check `tool_requests[0].name` |
| Context bloat over cycles | No COMPACT between phases | Add COMPACT after implementation phases |

---

## Workflow Efficiency Patterns

### COMPACT Placement Matters

Based on cross-run analysis (v1 vs v2 workflow):

| Workflow | Context Peak | Cycles Completed |
|----------|--------------|------------------|
| v1 (6 phases, no strategic COMPACT) | 55-58% | 5.5/10 |
| v2 (9 phases, COMPACT after Phase 6) | **20%** | **10/10** |

**Key insight**: Placing COMPACT after the implementation stream (Phase 6) clears tool output and file contents before PM/Librarian phases. This keeps context lean for 10+ cycle runs.

### Role Shift Improves Focus

The v2 workflow uses explicit role shifts:
- **Implementer** (Phases 1-6): Edit code, run tests
- **Project Manager** (Phases 7-8): Discover candidates, route to queues
- **Librarian** (Phase 9): Archive, maintain file sizes

Each role shift allows the model to refocus context on the new task.

### Bidirectional Flow Discovery

Long-running sessions reveal two streams of work:

```
FORWARD: humans → decisions → BACKLOG.md → implementation
BACKWARD: implementation → discoveries → OPEN-QUESTIONS.md → humans
```

This pattern enables autonomous operation while surfacing design decisions for human review.

---

## See Also

- [Resolved Quirks Archive](../archive/quirks/2026-01-resolved-quirks.md) - Full investigation context
- [QUIRKS.md](QUIRKS.md) - Active quirks tracker
- [LOOP-STRESS-TEST.md](LOOP-STRESS-TEST.md) - Testing methodology
- [PHILOSOPHY.md](PHILOSOPHY.md) - Extended Workflow Pattern (v2)
