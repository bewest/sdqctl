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
    # Abort tracking
    abort_reason: Optional[str] = None
    abort_details: Optional[str] = None


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

            elif event_type == "session.info":
                # TRACE level - raw session info is rarely needed
                if logger.isEnabledFor(TRACE):
                    logger.log(TRACE, f"Session info: {_format_data(data)}")

            elif event_type == "session.error":
                error = _get_field(data, "error", "message", default=str(data))
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
                intent = _get_field(data, "intent", "content", default=str(data))
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
                delta = _get_field(data, "delta_content", default="")
                chunks.append(delta)
                if on_chunk and delta:
                    on_chunk(delta)

            elif event_type == "assistant.message":
                full_response = _get_field(data, "content", default="")

            # Reasoning events
            elif event_type == "assistant.reasoning":
                reasoning = _get_field(data, "content", "reasoning", default=str(data))
                logger.debug(f"Reasoning: {reasoning[:200]}..." if len(str(reasoning)) > 200 else f"Reasoning: {reasoning}")
                reasoning_parts.append(reasoning)
                if on_reasoning:
                    on_reasoning(reasoning)

            elif event_type == "assistant.reasoning_delta":
                # Skip logging deltas - we get full reasoning in assistant.reasoning
                # This avoids duplicate content at verbose levels (Q-004)
                delta = _get_field(data, "delta_content", default="")
                # Only log deltas if explicitly requested via very high verbosity
                # and no full reasoning has been received yet
                pass  # Intentionally skip logging to reduce noise

            # Usage events
            elif event_type == "assistant.usage":
                input_tokens = int(_get_field(data, "input_tokens", default=0) or 0)
                output_tokens = int(_get_field(data, "output_tokens", default=0) or 0)
                turn_stats.input_tokens = input_tokens
                turn_stats.output_tokens = output_tokens
                stats.total_input_tokens += input_tokens
                stats.total_output_tokens += output_tokens
                logger.info(f"Tokens: {input_tokens} in / {output_tokens} out")

            elif event_type == "session.usage_info":
                # Extract only meaningful usage fields
                current_tokens = _get_field(data, "current_tokens")
                token_limit = _get_field(data, "token_limit")
                messages_length = _get_field(data, "messages_length")
                if current_tokens is not None:
                    pct = int(100 * current_tokens / token_limit) if token_limit else 0
                    logger.debug(f"Context: {int(current_tokens):,}/{int(token_limit):,} tokens ({pct}%), {int(messages_length or 0)} messages")
                elif logger.isEnabledFor(TRACE):
                    # Full data only at TRACE
                    logger.log(TRACE, f"Usage info: {_format_data(data)}")

            # Tool events
            elif event_type == "tool.execution_start":
                tool_name = _get_tool_name(data)
                tool_call_id = _get_field(data, "tool_call_id", "id", default=str(turn_stats.tool_calls))
                tool_args = _get_field(data, "arguments", "args", default={})
                
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
                
                # Track success/failure counts
                if success:
                    stats.tool_calls_succeeded += 1
                    status_icon = "✓"
                else:
                    stats.tool_calls_failed += 1
                    status_icon = "✗"
                
                # Format result summary for better observability
                result_summary = ""
                if result and logger.isEnabledFor(logging.DEBUG):
                    result_str = str(result)
                    if len(result_str) > 100:
                        # Count lines for file listings
                        lines = result_str.count('\n')
                        if lines > 5:
                            result_summary = f" → {lines} lines"
                        else:
                            result_summary = f" → {len(result_str)} chars"
                    elif result_str and result_str != "None":
                        result_summary = f" → {result_str[:50]}..."
                
                logger.info(f"  {status_icon} {tool_name}{duration_str}{result_summary}")

            elif event_type == "tool.execution_partial_result":
                # TRACE level - partial results are very frequent
                if logger.isEnabledFor(TRACE):
                    logger.log(TRACE, "Tool partial result")

            elif event_type == "tool.user_requested":
                tool_name = _get_tool_name(data)
                logger.info(f"Tool requested (user): {tool_name}")

            # Compaction events
            elif event_type == "session.compaction_start":
                logger.info("Compaction started")
                progress("  🗜️  Compacting...")

            elif event_type == "session.compaction_complete":
                tokens_used = _get_field(data, "compaction_tokens_used")
                if tokens_used:
                    before = _get_field(tokens_used, "before", default=0)
                    after = _get_field(tokens_used, "after", default=0)
                    logger.info(f"Compaction complete: {before} → {after} tokens")
                    progress(f"  🗜️  Compacted: {before} → {after} tokens")

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
                progress(f"  ➜ Handoff: {target}")

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
                progress(f"  🛑 Abort: {reason}")
                # Store abort info for later retrieval
                stats.abort_reason = reason
                stats.abort_details = details
                # Signal completion so we don't hang
                done.set()

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

        # Check if session was aborted - raise exception for caller to handle
        if stats.abort_reason:
            from ..core.exceptions import AgentAborted
            raise AgentAborted(
                reason=stats.abort_reason,
                details=stats.abort_details,
                turn_number=stats.turns,
            )

        # Return full response or assembled chunks
        return full_response or "".join(chunks)

    def get_session_stats(self, session: AdapterSession) -> Optional[SessionStats]:
        """Get accumulated stats for a session."""
        return self.session_stats.get(session.id)

    def was_aborted(self, session: AdapterSession) -> bool:
        """Check if the session received an abort signal.
        
        Use this after catching AgentAborted to determine if graceful
        stop was requested by the agent.
        """
        stats = self.session_stats.get(session.id)
        return stats is not None and stats.abort_reason is not None

    def get_abort_info(self, session: AdapterSession) -> Optional[tuple[str, Optional[str]]]:
        """Get abort reason and details if session was aborted.
        
        Returns:
            Tuple of (reason, details) or None if not aborted
        """
        stats = self.session_stats.get(session.id)
        if stats and stats.abort_reason:
            return (stats.abort_reason, stats.abort_details)
        return None

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
        """Compact using Copilot's /compact slash command.
        
        The /compact command triggers native SDK compaction which is more
        efficient than re-summarization. Falls back to base implementation
        if /compact doesn't work as expected.
        """
        tokens_before, _ = await self.get_context_usage(session)
        
        # Try /compact command first (native SDK compaction)
        try:
            # Build preserve instruction if provided
            preserve_hint = ""
            if preserve:
                preserve_hint = f"Preserve: {', '.join(preserve)}. "
            
            compact_prompt = f"/compact {preserve_hint}{summary_prompt}".strip()
            response = await self.send(session, compact_prompt)
            
            tokens_after, _ = await self.get_context_usage(session)
            
            # If tokens reduced significantly, /compact worked
            if tokens_after < tokens_before * 0.8:
                logger.info(f"Native /compact succeeded: {tokens_before} → {tokens_after} tokens")
                return CompactionResult(
                    preserved_content=response,
                    summary=response,
                    tokens_before=tokens_before,
                    tokens_after=tokens_after,
                )
            else:
                logger.debug(f"/compact may not have reduced tokens ({tokens_before} → {tokens_after}), using response as summary")
                return CompactionResult(
                    preserved_content=response,
                    summary=response,
                    tokens_before=tokens_before,
                    tokens_after=tokens_after,
                )
                
        except Exception as e:
            logger.warning(f"/compact command failed: {e}, falling back to summarization")
        
        # Fall back to base implementation (sends summarization prompt)
        return await super().compact(session, preserve, summary_prompt)

    async def compact_with_session_reset(
        self,
        session: AdapterSession,
        config: AdapterConfig,
        preserve: list[str],
        compaction_prologue: Optional[str] = None,
        compaction_epilogue: Optional[str] = None,
        prologues: Optional[list[str]] = None,
        epilogues: Optional[list[str]] = None,
    ) -> tuple[AdapterSession, CompactionResult]:
        """Compact by getting summary and creating a new session.
        
        This implements client-side compaction:
        1. Get summary via /compact
        2. Destroy current session
        3. Create new session with compacted context injected
        
        The new session receives context in this order:
        - epilogues (from .conv file)
        - compaction_prologue (from COMPACT-PROLOGUE)
        - compacted summary
        - compaction_epilogue (from COMPACT-EPILOGUE)
        
        Args:
            session: Current session to compact
            config: Config for new session
            preserve: Items to preserve in summary
            compaction_prologue: Content before summary (COMPACT-PROLOGUE)
            compaction_epilogue: Content after summary (COMPACT-EPILOGUE)
            prologues: Regular prologues to inject
            epilogues: Regular epilogues to inject
            
        Returns:
            Tuple of (new_session, compaction_result)
        """
        tokens_before, _ = await self.get_context_usage(session)
        
        # Get summary via /compact
        preserve_hint = ""
        if preserve:
            preserve_hint = f"Preserve: {', '.join(preserve)}. "
        
        compact_prompt = f"/compact {preserve_hint}Summarize this conversation for continuation.".strip()
        
        try:
            summary = await self.send(session, compact_prompt)
        except Exception as e:
            logger.warning(f"/compact failed: {e}, using fallback summarization")
            summary = await self.send(session, f"Summarize this conversation. {preserve_hint}")
        
        logger.info(f"🗜️ Compaction: got summary ({len(summary)} chars)")
        
        # Destroy old session
        await self.destroy_session(session)
        
        # Create new session
        new_session = await self.create_session(config)
        
        # Build compacted context
        context_parts = []
        
        # Add epilogues first (workflow-level context)
        if epilogues:
            for epilogue in epilogues:
                context_parts.append(epilogue)
        
        # Add compaction prologue
        if compaction_prologue:
            context_parts.append(compaction_prologue)
        else:
            context_parts.append("This conversation has been compacted. Summary of previous context:")
        
        # Add the summary
        context_parts.append(summary)
        
        # Add compaction epilogue
        if compaction_epilogue:
            context_parts.append(compaction_epilogue)
        else:
            context_parts.append("Continue from the context above.")
        
        compacted_context = "\n\n".join(context_parts)
        
        # Send compacted context to establish new session
        await self.send(new_session, compacted_context)
        
        tokens_after, _ = await self.get_context_usage(new_session)
        
        logger.info(f"🗜️ Compaction complete: {tokens_before} → {tokens_after} tokens (new session)")
        
        return new_session, CompactionResult(
            preserved_content=compacted_context,
            summary=summary,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )

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
