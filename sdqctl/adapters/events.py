"""
Event collection and recording for adapter sessions.

Provides infrastructure to capture and export SDK events during execution.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from .stats import SessionStats


# Get logger for this module
logger = logging.getLogger("sdqctl.adapters.copilot")

# Custom TRACE level
TRACE = 5


def _get_field(data: Any, *keys: str, default: Any = None) -> Any:
    """Extract a field from data, trying multiple attribute/key names.

    Handles both object attributes and dict-like access patterns, which is
    important because SDK event data may come as either depending on version.

    Args:
        data: SDK event data (object or dict)
        *keys: Attribute/key names to try in order
        default: Value to return if no key is found

    Returns:
        The first found value, or default if none found
    """
    if data is None:
        return default

    for key in keys:
        # Try attribute access first (for SDK Data objects)
        val = getattr(data, key, None)
        if val is not None:
            return val
        # Try dict-style access (if data is dict or has __getitem__)
        if isinstance(data, dict):
            val = data.get(key)
            if val is not None:
                return val

    return default


def _get_tool_name(data: Any) -> str:
    """Extract tool name from event data, handling nested structures.

    Tool name can appear in:
    - data.tool_name (direct field)
    - data.name (generic name field)
    - data.tool (short name)
    - data.tool_requests[0].name (nested in tool_requests list)

    Returns:
        Tool name string, or "unknown" if not found
    """
    # Try direct fields first
    name = _get_field(data, "tool_name", "name", "tool")
    if name:
        return name

    # Check for tool_requests list (contains ToolRequest objects)
    tool_requests = _get_field(data, "tool_requests")
    if tool_requests and isinstance(tool_requests, list) and len(tool_requests) > 0:
        first_request = tool_requests[0]
        name = _get_field(first_request, "name", "tool_name")
        if name:
            return name

    return "unknown"


def _format_data(data: Any, include_fields: list[str] | None = None) -> str:
    """Format SDK Data object for logging, filtering out None values.

    Args:
        data: SDK event data object
        include_fields: If provided, only include these fields. Otherwise include all non-None.

    Returns:
        Compact string representation with only meaningful values
    """
    if data is None:
        return "None"

    # Try to extract meaningful fields
    result = {}
    try:
        # Get all attributes that don't start with underscore
        for attr in dir(data):
            if attr.startswith("_"):
                continue
            if callable(getattr(data, attr, None)):
                continue
            if include_fields and attr not in include_fields:
                continue
            val = getattr(data, attr, None)
            if val is not None:
                result[attr] = val
    except Exception:
        return str(data)[:200]

    if not result:
        return "{}"

    # Format compactly
    parts = [f"{k}={v}" for k, v in result.items()]
    return ", ".join(parts)


@dataclass
class EventRecord:
    """Record of a single SDK event for export."""
    event_type: str
    timestamp: str  # ISO format
    data: dict
    session_id: str
    turn: int
    ephemeral: bool = False


class EventCollector:
    """Accumulates SDK events during a session for export."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: list[EventRecord] = []

    def add(
        self, event_type: str, data: Any, turn: int, ephemeral: bool = False
    ) -> None:
        """Record an event."""
        # Convert data to dict for serialization
        if data is None:
            data_dict = {}
        elif hasattr(data, '__dict__'):
            data_dict = {
                k: str(v) for k, v in vars(data).items() if not k.startswith('_')
            }
        elif isinstance(data, dict):
            data_dict = {k: str(v) for k, v in data.items()}
        else:
            data_dict = {"value": str(data)}

        record = EventRecord(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data_dict,
            session_id=self.session_id,
            turn=turn,
            ephemeral=ephemeral,
        )
        self.events.append(record)

    def export_jsonl(self, path: str) -> int:
        """Export events to JSONL file. Returns count of events written."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for event in self.events:
                f.write(json.dumps(asdict(event)) + '\n')

        return len(self.events)

    def clear(self) -> None:
        """Clear accumulated events."""
        self.events.clear()


class CopilotEventHandler:
    """Handles SDK events for a Copilot session.

    Processes all event types and updates SessionStats accordingly.
    Designed to be registered once per session and reused across sends.
    """

    def __init__(self, stats: "SessionStats", progress_fn: Optional[Callable[[str], None]] = None):
        """Initialize handler.

        Args:
            stats: SessionStats instance to update
            progress_fn: Optional callback for progress messages
        """
        self.stats = stats
        self.progress = progress_fn or (lambda x: None)

    def handle(self, event: Any) -> None:
        """Process a single SDK event.

        Args:
            event: SDK event object with .type and .data attributes
        """
        stats = self.stats

        event_type = event.type.value if hasattr(event.type, "value") else str(event.type)
        data = event.data if hasattr(event, "data") else None

        # Record event for export (if collector is enabled)
        if stats.event_collector:
            ephemeral = event_type in (
                "assistant.message_delta",
                "assistant.reasoning_delta",
                "tool.execution_partial_result",
            )
            stats.event_collector.add(event_type, data, stats.turns, ephemeral=ephemeral)

        # Session events
        if event_type == "session.start":
            self._handle_session_start(data)

        elif event_type == "session.info":
            if logger.isEnabledFor(TRACE):
                logger.log(TRACE, f"Session info: {_format_data(data)}")

        elif event_type == "session.error":
            self._handle_session_error(data)

        elif event_type == "session.truncation":
            logger.warning("Context truncated due to size limits")
            self.progress("  ⚠️  Context truncated")

        # Turn events
        elif event_type == "assistant.turn_start":
            stats.turns += 1
            logger.info(f"Turn {stats.turns} started")

        elif event_type == "assistant.turn_end":
            logger.info(f"Turn {stats.turns} ended")

        elif event_type == "assistant.intent":
            self._handle_intent(data)

        # Message events
        elif event_type == "assistant.message_delta":
            delta = _get_field(data, "delta_content", default="")
            stats._send_chunks.append(delta)
            if stats._send_on_chunk and delta:
                stats._send_on_chunk(delta)

        elif event_type == "assistant.message":
            stats._send_full_response = _get_field(data, "content", default="")

        # Reasoning events
        elif event_type == "assistant.reasoning":
            reasoning = _get_field(data, "content", "reasoning", default=str(data))
            if len(str(reasoning)) > 200:
                logger.debug(f"Reasoning: {reasoning[:200]}...")
            else:
                logger.debug(f"Reasoning: {reasoning}")
            stats._send_reasoning_parts.append(reasoning)
            if stats._send_on_reasoning:
                stats._send_on_reasoning(reasoning)

        elif event_type == "assistant.reasoning_delta":
            # Skip logging deltas - we get full reasoning in assistant.reasoning
            pass

        # Usage events
        elif event_type == "assistant.usage":
            self._handle_usage(data)

        elif event_type == "session.usage_info":
            self._handle_usage_info(data)

        # Tool events
        elif event_type == "tool.execution_start":
            self._handle_tool_start(data)

        elif event_type == "tool.execution_complete":
            self._handle_tool_complete(data)

        elif event_type == "tool.execution_partial_result":
            if logger.isEnabledFor(TRACE):
                logger.log(TRACE, "Tool partial result")

        elif event_type == "tool.user_requested":
            tool_name = _get_tool_name(data)
            logger.info(f"Tool requested (user): {tool_name}")

        # Compaction events
        elif event_type == "session.compaction_start":
            logger.info("Compaction started")
            self.progress("  🗜️  Compacting...")

        elif event_type == "session.compaction_complete":
            self._handle_compaction_complete(data)

        # Subagent events
        elif event_type == "subagent.started":
            agent = _get_field(data, "agent_name", "agent", "name", default="unknown")
            logger.info(f"Subagent started: {agent}")

        elif event_type == "subagent.completed":
            agent = _get_field(data, "agent_name", "agent", "name", default="unknown")
            logger.info(f"Subagent completed: {agent}")

        elif event_type == "subagent.failed":
            agent = _get_field(data, "agent_name", "agent", "name", default="unknown")
            error = _get_field(data, "error", default="unknown")
            logger.warning(f"Subagent failed: {agent} - {error}")

        # Hook events
        elif event_type == "hook.start":
            hook_name = _get_field(data, "hook_type", "name", "hook", default="unknown")
            logger.info(f"🪝 Hook started: {hook_name}")

        elif event_type == "hook.end":
            hook_name = _get_field(data, "hook_type", "name", "hook", default="unknown")
            success = _get_field(data, "success", default=True)
            status_icon = "✓" if success else "✗"
            logger.info(f"  {status_icon} Hook: {hook_name}")

        # Session handoff (model change, context transfer)
        elif event_type == "session.handoff":
            target = _get_field(data, "target", "to", default="unknown")
            reason = _get_field(data, "reason")
            reason_str = f" ({reason})" if reason else ""
            logger.info(f"Session handoff → {target}{reason_str}")
            self.progress(f"  ➜ Handoff: {target}")

        elif event_type == "session.model_change":
            old_model = _get_field(data, "from", "old_model", default="unknown")
            new_model = _get_field(data, "to", "new_model", default="unknown")
            logger.info(f"Model changed: {old_model} → {new_model}")
            stats.model = new_model

        # ABORT event - agent signals it should stop
        elif event_type == "abort":
            reason = _get_field(data, "reason", "message", default="unknown")
            details = _get_field(data, "details")
            logger.warning(f"🛑 Agent abort signal: {reason}")
            self.progress(f"  🛑 Abort: {reason}")
            stats.abort_reason = reason
            stats.abort_details = details
            if stats._send_done:
                stats._send_done.set()

        # Completion
        elif event_type == "session.idle":
            if stats._send_done:
                stats._send_done.set()

        # Unknown events - log at TRACE for forward compatibility
        elif event_type != "unknown":
            if logger.isEnabledFor(TRACE):
                logger.log(TRACE, f"Event: {event_type} - {_format_data(data)}")

    def _handle_session_start(self, data: Any) -> None:
        """Handle session.start event."""
        stats = self.stats
        stats.session_start_time = datetime.now()

        context = _get_field(data, "context")
        if context:
            branch = _get_field(context, "branch")
            if branch:
                stats.context_info = {
                    "branch": branch,
                    "cwd": _get_field(context, "cwd"),
                    "repository": _get_field(context, "repository"),
                }
                repo = _get_field(context, "repository", default="unknown")
                logger.info(f"Session: branch={branch}, repo={repo}")
        model = _get_field(data, "selected_model")
        if model:
            stats.model = model
            logger.debug(f"Model: {model}")

    def _handle_session_error(self, data: Any) -> None:
        """Handle session.error event."""
        stats = self.stats
        error = _get_field(data, "error", "message", default=str(data))
        error_type = _get_field(data, "error_type", "errorType", default=None)
        error_code = None

        # Extract code from ErrorClass structure
        error_obj = _get_field(data, "error", default=None)
        if isinstance(error_obj, dict):
            error_code = error_obj.get("code")
            error = error_obj.get("message", str(error_obj))
        elif hasattr(error_obj, "code"):
            error_code = getattr(error_obj, "code", None)
            error = getattr(error_obj, "message", str(error_obj))

        # Detect rate limit errors
        is_rate_limit = (
            error_code == "429"
            or error_code == 429
            or error_type == "rate_limit"
            or "rate limit" in str(error).lower()
            or "too many requests" in str(error).lower()
            or "restricts the number" in str(error).lower()
        )

        if is_rate_limit:
            stats.rate_limited = True
            stats.rate_limit_message = str(error)
            logger.warning(f"🛑 Rate limit hit: {error}")
            self.progress("  🛑 Rate limited - wait before retrying")
        else:
            logger.error(f"Session error: {error}")
            self.progress(f"  ⚠️  Error: {error}")

    def _handle_intent(self, data: Any) -> None:
        """Handle assistant.intent event."""
        stats = self.stats
        intent = _get_field(data, "intent", "content", default=str(data))
        if intent and intent != stats.current_intent:
            stats.current_intent = intent
            stats.intent_history.append({
                "intent": intent,
                "turn": stats.turns,
            })
            logger.info(f"🎯 Intent: {intent}")
            self.progress(f"  🎯 {intent}")

    def _handle_usage(self, data: Any) -> None:
        """Handle assistant.usage event."""
        stats = self.stats
        input_tokens = int(_get_field(data, "input_tokens", default=0) or 0)
        output_tokens = int(_get_field(data, "output_tokens", default=0) or 0)
        if stats._send_turn_stats:
            stats._send_turn_stats.input_tokens = input_tokens
            stats._send_turn_stats.output_tokens = output_tokens
        stats.total_input_tokens += input_tokens
        stats.total_output_tokens += output_tokens
        logger.info(f"Tokens: {input_tokens} in / {output_tokens} out")

        # Parse quota_snapshots for rate limit awareness
        quota_snapshots = _get_field(data, "quota_snapshots", "quotaSnapshots", default={})
        if quota_snapshots:
            self._parse_quota_snapshots(quota_snapshots)

    def _parse_quota_snapshots(self, quota_snapshots: dict) -> None:
        """Parse quota snapshot data for rate limit awareness."""
        stats = self.stats
        for quota_type, snapshot in (quota_snapshots or {}).items():
            if hasattr(snapshot, "__iter__") or isinstance(snapshot, dict):
                remaining = _get_field(
                    snapshot, "remaining_percentage", "remainingPercentage", default=None
                )
                is_unlimited = _get_field(
                    snapshot, "is_unlimited_entitlement", "isUnlimitedEntitlement", default=False
                )
                reset_date = _get_field(snapshot, "reset_date", "resetDate", default=None)
                used_requests = _get_field(
                    snapshot, "used_requests", "usedRequests", default=None
                )
                entitlement = _get_field(
                    snapshot, "entitlement_requests", "entitlementRequests", default=None
                )

                if is_unlimited:
                    stats.is_unlimited_quota = True
                elif remaining is not None:
                    if stats.quota_remaining is None:
                        stats.quota_remaining = float(remaining)
                    else:
                        stats.quota_remaining = min(stats.quota_remaining, float(remaining))
                    stats.quota_reset_date = reset_date
                    if used_requests is not None:
                        stats.quota_used_requests = int(used_requests)
                    if entitlement is not None:
                        stats.quota_entitlement_requests = int(entitlement)

                    # Warn when quota is low
                    warning = stats.get_rate_limit_warning()
                    if warning:
                        logger.warning(f"⚠️  {warning}")
                        self.progress(f"  ⚠️  {warning}")

    def _handle_usage_info(self, data: Any) -> None:
        """Handle session.usage_info event."""
        stats = self.stats
        current_tokens = _get_field(data, "current_tokens")
        token_limit = _get_field(data, "token_limit")
        messages_length = _get_field(data, "messages_length")
        if current_tokens is not None:
            pct = int(100 * current_tokens / token_limit) if token_limit else 0
            cur = int(current_tokens)
            lim = int(token_limit)
            msgs = int(messages_length or 0)
            stats.current_context_tokens = cur
            stats.context_token_limit = lim
            logger.debug(f"Context: {cur:,}/{lim:,} tokens ({pct}%), {msgs} messages")
        elif logger.isEnabledFor(TRACE):
            logger.log(TRACE, f"Usage info: {_format_data(data)}")

    def _handle_tool_start(self, data: Any) -> None:
        """Handle tool.execution_start event."""
        stats = self.stats
        tool_name = _get_tool_name(data)
        if stats._send_turn_stats:
            default_id = str(stats._send_turn_stats.tool_calls)
        else:
            default_id = "0"
        tool_call_id = _get_field(data, "tool_call_id", "id", default=default_id)
        tool_args = _get_field(data, "arguments", "args", default={})

        if stats._send_turn_stats:
            stats._send_turn_stats.tool_calls += 1
        stats.total_tool_calls += 1

        stats.active_tools[tool_call_id] = {
            "name": tool_name,
            "args": tool_args,
            "start_time": datetime.now(),
        }

        logger.info(f"🔧 Tool: {tool_name}")
        if tool_args and logger.isEnabledFor(logging.DEBUG):
            if isinstance(tool_args, dict):
                args_str = json.dumps(tool_args)
            else:
                args_str = str(tool_args)
            if len(args_str) > 500:
                args_str = args_str[:500] + "..."
            logger.debug(f"  Args: {args_str}")

    def _handle_tool_complete(self, data: Any) -> None:
        """Handle tool.execution_complete event."""
        stats = self.stats
        tool_name = _get_tool_name(data)
        tool_call_id = _get_field(data, "tool_call_id", "id")
        success = _get_field(data, "success", default=True)
        result = _get_field(data, "result", "output", default=None)

        # Calculate duration if we tracked this tool
        duration_str = ""
        if tool_call_id and tool_call_id in stats.active_tools:
            tool_info = stats.active_tools.pop(tool_call_id)
            duration = datetime.now() - tool_info["start_time"]
            duration_str = f" ({duration.total_seconds():.1f}s)"
            if tool_name == "unknown" and tool_info.get("name"):
                tool_name = tool_info["name"]

        if success:
            stats.tool_calls_succeeded += 1
            status_icon = "✓"
        else:
            stats.tool_calls_failed += 1
            status_icon = "✗"

        result_summary = ""
        if result and logger.isEnabledFor(logging.DEBUG):
            result_str = str(result)
            if len(result_str) > 100:
                lines = result_str.count('\n')
                if lines > 5:
                    result_summary = f" → {lines} lines"
                else:
                    result_summary = f" → {len(result_str)} chars"
            elif result_str and result_str != "None":
                result_summary = f" → {result_str[:50]}..."

        logger.info(f"  {status_icon} {tool_name}{duration_str}{result_summary}")

    def _handle_compaction_complete(self, data: Any) -> None:
        """Handle session.compaction_complete event."""
        stats = self.stats
        tokens_used = _get_field(data, "compaction_tokens_used")
        if tokens_used:
            before = _get_field(tokens_used, "before", default=0)
            after = _get_field(tokens_used, "after", default=0)
            logger.info(f"Compaction complete: {before} → {after} tokens")
            self.progress(f"  🗜️  Compacted: {before} → {after} tokens")

            from .stats import CompactionEvent
            stats.compaction_events.append(CompactionEvent(
                tokens_before=int(before) if before else 0,
                tokens_after=int(after) if after else 0,
                timestamp=datetime.now(),
            ))
