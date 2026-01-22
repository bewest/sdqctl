"""
GitHub Copilot SDK adapter.

Uses the official github/copilot-sdk Python package.
Install with: pip install github-copilot-sdk
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from .base import AdapterBase, AdapterConfig, AdapterSession, CompactionResult

# Lazy import to avoid hard dependency
CopilotClient = None

# Get logger for this module
logger = logging.getLogger("sdqctl.adapters.copilot")

# Custom TRACE level
TRACE = 5


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


def _ensure_copilot_sdk():
    """Ensure copilot SDK is available."""
    global CopilotClient
    if CopilotClient is None:
        try:
            from copilot import CopilotClient as _CopilotClient

            CopilotClient = _CopilotClient
        except ImportError:
            raise ImportError(
                "GitHub Copilot SDK not installed. "
                "Install with: pip install github-copilot-sdk"
            )


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
    
    def add(self, event_type: str, data: Any, turn: int, ephemeral: bool = False) -> None:
        """Record an event."""
        # Convert data to dict for serialization
        if data is None:
            data_dict = {}
        elif hasattr(data, '__dict__'):
            data_dict = {k: str(v) for k, v in vars(data).items() if not k.startswith('_')}
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
        from dataclasses import asdict
        from pathlib import Path
        
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for event in self.events:
                f.write(json.dumps(asdict(event)) + '\n')
        
        return len(self.events)
    
    def clear(self) -> None:
        """Clear accumulated events."""
        self.events.clear()


@dataclass
class TurnStats:
    """Statistics for a single turn."""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    reasoning_shown: bool = False


@dataclass 
class SessionStats:
    """Accumulated statistics for a session."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    tool_calls_succeeded: int = 0
    tool_calls_failed: int = 0
    turns: int = 0
    model: Optional[str] = None
    context_info: Optional[dict] = None
    # Intent tracking
    current_intent: Optional[str] = None
    intent_history: list = field(default_factory=list)
    # Active tools (for timing)
    active_tools: dict = field(default_factory=dict)
    # Event collector for export
    event_collector: Optional[EventCollector] = None


class CopilotAdapter(AdapterBase):
    """
    Adapter for GitHub Copilot CLI via the official SDK.

    Uses JSON-RPC communication with the Copilot CLI server.
    """

    name = "copilot"

    def __init__(
        self,
        cli_path: str = "copilot",
        cli_url: Optional[str] = None,
        use_stdio: bool = True,
    ):
        """
        Initialize Copilot adapter.

        Args:
            cli_path: Path to the copilot CLI executable
            cli_url: URL of existing CLI server (optional)
            use_stdio: Use stdio transport instead of TCP
        """
        self.cli_path = cli_path
        self.cli_url = cli_url
        self.use_stdio = use_stdio
        self.client = None
        self.sessions: dict[str, Any] = {}
        self.session_stats: dict[str, SessionStats] = {}

    async def start(self) -> None:
        """Start the Copilot CLI client."""
        _ensure_copilot_sdk()

        config = {
            "cli_path": self.cli_path,
            "use_stdio": self.use_stdio,
        }
        if self.cli_url:
            config["cli_url"] = self.cli_url

        self.client = CopilotClient(config)
        await self.client.start()

    async def stop(self) -> None:
        """Stop the Copilot CLI client."""
        if self.client:
            # Destroy all sessions
            for session_id, copilot_session in self.sessions.items():
                try:
                    await copilot_session.destroy()
                except Exception:
                    pass

            await self.client.stop()
            self.client = None
            self.sessions.clear()
            self.session_stats.clear()

    async def create_session(self, config: AdapterConfig) -> AdapterSession:
        """Create a new Copilot session."""
        if not self.client:
            raise RuntimeError("Adapter not started. Call start() first.")

        session_config = {
            "model": config.model,
            "streaming": config.streaming,
        }

        if config.tools:
            session_config["tools"] = config.tools

        copilot_session = await self.client.create_session(session_config)

        session_id = str(uuid.uuid4())[:8]
        session = AdapterSession(
            id=session_id,
            adapter=self,
            config=config,
            _internal=copilot_session,
        )

        self.sessions[session_id] = copilot_session
        stats = SessionStats(model=config.model)
        stats.event_collector = EventCollector(session_id)
        self.session_stats[session_id] = stats
        return session

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy a Copilot session."""
        if session.id in self.sessions:
            # Log final stats
            stats = self.session_stats.get(session.id)
            if stats and stats.total_input_tokens > 0:
                intent_summary = f", {len(stats.intent_history)} intents" if stats.intent_history else ""
                tool_summary = ""
                if stats.total_tool_calls > 0:
                    tool_summary = f", {stats.total_tool_calls} tools"
                    if stats.tool_calls_failed > 0:
                        tool_summary += f" ({stats.tool_calls_failed} failed)"
                logger.info(
                    f"Session complete: {stats.turns} turns, "
                    f"{stats.total_input_tokens} in / {stats.total_output_tokens} out tokens{tool_summary}{intent_summary}"
                )
            
            try:
                await session._internal.destroy()
            except Exception:
                pass
            del self.sessions[session.id]
            if session.id in self.session_stats:
                del self.session_stats[session.id]

    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_reasoning: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send a prompt and get response.
        
        Args:
            session: The adapter session
            prompt: The prompt to send
            on_chunk: Optional callback for streaming chunks
            on_reasoning: Optional callback for AI reasoning (for loop detection)
        """
        from ..core.progress import progress
        
        copilot_session = session._internal
        stats = self.session_stats.get(session.id, SessionStats())
        turn_stats = TurnStats()

        # Set up event handling
        done = asyncio.Event()
        chunks: list[str] = []
        full_response: str = ""
        reasoning_parts: list[str] = []

        def on_event(event):
            nonlocal full_response

            event_type = event.type.value if hasattr(event.type, "value") else str(event.type)
            data = event.data if hasattr(event, "data") else None

            # Record event for export (if collector is enabled)
            if stats.event_collector:
                # Mark streaming/delta events as ephemeral (can be skipped in compact exports)
                ephemeral = event_type in (
                    "assistant.message_delta", 
                    "assistant.reasoning_delta",
                    "tool.execution_partial_result",
                )
                stats.event_collector.add(event_type, data, stats.turns, ephemeral=ephemeral)

            # Session events
            if event_type == "session.start":
                context = getattr(data, "context", None)
                if context and hasattr(context, "branch"):
                    stats.context_info = {
                        "branch": getattr(context, "branch", None),
                        "cwd": getattr(context, "cwd", None),
                        "repository": getattr(context, "repository", None),
                    }
                    logger.info(f"Session: branch={context.branch}, repo={getattr(context, 'repository', 'unknown')}")
                model = getattr(data, "selected_model", None)
                if model:
                    stats.model = model
                    logger.debug(f"Model: {model}")

            elif event_type == "session.info":
                # TRACE level - raw session info is rarely needed
                if logger.isEnabledFor(TRACE):
                    logger.log(TRACE, f"Session info: {_format_data(data)}")

            elif event_type == "session.error":
                error = getattr(data, "error", None) or getattr(data, "message", str(data))
                logger.error(f"Session error: {error}")
                progress(f"  ⚠️  Error: {error}")

            elif event_type == "session.truncation":
                logger.warning("Context truncated due to size limits")
                progress("  ⚠️  Context truncated")

            # Turn events
            elif event_type == "assistant.turn_start":
                stats.turns += 1
                logger.info(f"Turn {stats.turns} started")

            elif event_type == "assistant.turn_end":
                logger.info(f"Turn {stats.turns} ended")

            elif event_type == "assistant.intent":
                intent = getattr(data, "intent", None) or getattr(data, "content", str(data))
                # Track intent changes
                if intent and intent != stats.current_intent:
                    stats.current_intent = intent
                    stats.intent_history.append({
                        "intent": intent,
                        "turn": stats.turns,
                    })
                    logger.info(f"🎯 Intent: {intent}")
                    progress(f"  🎯 {intent}")

            # Message events
            elif event_type == "assistant.message_delta":
                delta = getattr(data, "delta_content", "") or ""
                chunks.append(delta)
                if on_chunk and delta:
                    on_chunk(delta)

            elif event_type == "assistant.message":
                full_response = getattr(data, "content", "") or ""

            # Reasoning events
            elif event_type == "assistant.reasoning":
                reasoning = getattr(data, "content", "") or getattr(data, "reasoning", str(data))
                logger.debug(f"Reasoning: {reasoning[:200]}..." if len(str(reasoning)) > 200 else f"Reasoning: {reasoning}")
                reasoning_parts.append(reasoning)
                if on_reasoning:
                    on_reasoning(reasoning)

            elif event_type == "assistant.reasoning_delta":
                # Very verbose - only at TRACE level
                delta = getattr(data, "delta_content", "") or ""
                if logger.isEnabledFor(5):  # TRACE level
                    logger.log(5, f"Reasoning delta: {delta}")

            # Usage events
            elif event_type == "assistant.usage":
                input_tokens = int(getattr(data, "input_tokens", 0) or 0)
                output_tokens = int(getattr(data, "output_tokens", 0) or 0)
                turn_stats.input_tokens = input_tokens
                turn_stats.output_tokens = output_tokens
                stats.total_input_tokens += input_tokens
                stats.total_output_tokens += output_tokens
                logger.info(f"Tokens: {input_tokens} in / {output_tokens} out")

            elif event_type == "session.usage_info":
                # Extract only meaningful usage fields
                current_tokens = getattr(data, "current_tokens", None)
                token_limit = getattr(data, "token_limit", None)
                messages_length = getattr(data, "messages_length", None)
                if current_tokens is not None:
                    pct = int(100 * current_tokens / token_limit) if token_limit else 0
                    logger.debug(f"Context: {int(current_tokens):,}/{int(token_limit):,} tokens ({pct}%), {int(messages_length or 0)} messages")
                elif logger.isEnabledFor(TRACE):
                    # Full data only at TRACE
                    logger.log(TRACE, f"Usage info: {_format_data(data)}")

            # Tool events
            elif event_type == "tool.execution_start":
                tool_name = getattr(data, "name", None) or getattr(data, "tool", "unknown")
                tool_call_id = getattr(data, "tool_call_id", None) or getattr(data, "id", str(turn_stats.tool_calls))
                tool_args = getattr(data, "arguments", None) or getattr(data, "args", {})
                
                turn_stats.tool_calls += 1
                stats.total_tool_calls += 1
                
                # Track active tool for timing
                stats.active_tools[tool_call_id] = {
                    "name": tool_name,
                    "args": tool_args,
                    "start_time": datetime.now(),
                }
                
                logger.info(f"🔧 Tool: {tool_name}")
                # Log args at DEBUG level (truncated)
                if tool_args and logger.isEnabledFor(logging.DEBUG):
                    args_str = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
                    if len(args_str) > 500:
                        args_str = args_str[:500] + "..."
                    logger.debug(f"  Args: {args_str}")

            elif event_type == "tool.execution_complete":
                tool_name = getattr(data, "name", None) or getattr(data, "tool", "unknown")
                tool_call_id = getattr(data, "tool_call_id", None) or getattr(data, "id", None)
                success = getattr(data, "success", True)  # Default to success if not specified
                
                # Calculate duration if we tracked this tool
                duration_str = ""
                if tool_call_id and tool_call_id in stats.active_tools:
                    tool_info = stats.active_tools.pop(tool_call_id)
                    duration = datetime.now() - tool_info["start_time"]
                    duration_str = f" ({duration.total_seconds():.1f}s)"
                
                # Track success/failure counts
                if success:
                    stats.tool_calls_succeeded += 1
                    status_icon = "✓"
                else:
                    stats.tool_calls_failed += 1
                    status_icon = "✗"
                
                logger.info(f"  {status_icon} {tool_name}{duration_str}")

            elif event_type == "tool.execution_partial_result":
                # TRACE level - partial results are very frequent
                if logger.isEnabledFor(TRACE):
                    logger.log(TRACE, "Tool partial result")

            elif event_type == "tool.user_requested":
                tool_name = getattr(data, "name", None) or "unknown"
                logger.info(f"Tool requested (user): {tool_name}")

            # Compaction events
            elif event_type == "session.compaction_start":
                logger.info("Compaction started")
                progress("  🗜️  Compacting...")

            elif event_type == "session.compaction_complete":
                tokens_used = getattr(data, "compaction_tokens_used", None)
                if tokens_used:
                    before = getattr(tokens_used, "before", 0)
                    after = getattr(tokens_used, "after", 0)
                    logger.info(f"Compaction complete: {before} → {after} tokens")
                    progress(f"  🗜️  Compacted: {before} → {after} tokens")

            # Subagent events
            elif event_type == "subagent.started":
                agent = getattr(data, "agent", None) or getattr(data, "name", "unknown")
                logger.info(f"Subagent started: {agent}")

            elif event_type == "subagent.completed":
                agent = getattr(data, "agent", None) or getattr(data, "name", "unknown")
                logger.info(f"Subagent completed: {agent}")

            elif event_type == "subagent.failed":
                agent = getattr(data, "agent", None) or getattr(data, "name", "unknown")
                error = getattr(data, "error", "unknown")
                logger.warning(f"Subagent failed: {agent} - {error}")

            # Completion
            elif event_type == "session.idle":
                done.set()

            # Unknown events - log at TRACE for forward compatibility
            elif event_type != "unknown":
                if logger.isEnabledFor(TRACE):
                    logger.log(TRACE, f"Event: {event_type} - {_format_data(data)}")

        copilot_session.on(on_event)

        # Send the prompt
        await copilot_session.send({"prompt": prompt})

        # Wait for completion
        await done.wait()

        # Return full response or assembled chunks
        return full_response or "".join(chunks)

    def get_session_stats(self, session: AdapterSession) -> Optional[SessionStats]:
        """Get accumulated stats for a session."""
        return self.session_stats.get(session.id)

    def export_events(self, session: AdapterSession, path: str) -> int:
        """Export all recorded events for a session to JSONL file.
        
        Args:
            session: The adapter session
            path: Output file path (will be created/overwritten)
            
        Returns:
            Number of events exported
        """
        stats = self.session_stats.get(session.id)
        if stats and stats.event_collector:
            return stats.event_collector.export_jsonl(path)
        return 0

    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """Get context window usage."""
        stats = self.session_stats.get(session.id)
        if stats:
            return (stats.total_input_tokens, 128000)
        
        copilot_session = session._internal

        try:
            # Try to get messages for token estimation
            messages = await copilot_session.get_messages()
            estimated_tokens = sum(
                len(getattr(m, "content", "") or "") // 4 for m in messages
            )
        except Exception:
            estimated_tokens = 0

        # Default max for modern models
        max_tokens = 128000

        return (estimated_tokens, max_tokens)

    async def compact(
        self,
        session: AdapterSession,
        preserve: list[str],
        summary_prompt: str,
    ) -> CompactionResult:
        """Compact using Copilot's /compact command if available."""
        # First try the /compact command
        try:
            # This would require special handling in the SDK
            # For now, fall back to standard approach
            pass
        except Exception:
            pass

        # Fall back to base implementation
        return await super().compact(session, preserve, summary_prompt)

    def supports_tools(self) -> bool:
        """Copilot SDK supports tools."""
        return True

    def supports_streaming(self) -> bool:
        """Copilot SDK supports streaming."""
        return True

    def get_info(self) -> dict:
        """Get adapter information."""
        info = super().get_info()
        info["cli_path"] = self.cli_path
        info["cli_url"] = self.cli_url
        info["connected"] = self.client is not None
        return info
