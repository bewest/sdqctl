"""
GitHub Copilot SDK adapter.

Uses the official github/copilot-sdk Python package.
Install with: pip install github-copilot-sdk
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from .base import AdapterBase, AdapterConfig, AdapterSession, CompactionResult

# Lazy import to avoid hard dependency
CopilotClient = None

# Get logger for this module
logger = logging.getLogger("sdqctl.adapters.copilot")


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
    turns: int = 0
    model: Optional[str] = None
    context_info: Optional[dict] = None


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
        self.sessions: dict[str, any] = {}
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
        self.session_stats[session_id] = SessionStats(model=config.model)
        return session

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy a Copilot session."""
        if session.id in self.sessions:
            # Log final stats
            stats = self.session_stats.get(session.id)
            if stats and stats.total_input_tokens > 0:
                logger.info(
                    f"Session complete: {stats.turns} turns, "
                    f"{stats.total_input_tokens} in / {stats.total_output_tokens} out tokens"
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
    ) -> str:
        """Send a prompt and get response."""
        from ..core.progress import progress
        
        copilot_session = session._internal
        stats = self.session_stats.get(session.id, SessionStats())
        turn_stats = TurnStats()

        # Set up event handling
        done = asyncio.Event()
        chunks: list[str] = []
        full_response: str = ""

        def on_event(event):
            nonlocal full_response

            event_type = event.type.value if hasattr(event.type, "value") else str(event.type)
            data = event.data if hasattr(event, "data") else None

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
                logger.debug(f"Session info: {data}")

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
                logger.info(f"Intent: {intent}")

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
                logger.debug(f"Usage info: {data}")

            # Tool events
            elif event_type == "tool.execution_start":
                tool_name = getattr(data, "name", None) or getattr(data, "tool", "unknown")
                turn_stats.tool_calls += 1
                stats.total_tool_calls += 1
                logger.info(f"Tool: {tool_name}")

            elif event_type == "tool.execution_complete":
                tool_name = getattr(data, "name", None) or getattr(data, "tool", "unknown")
                logger.debug(f"Tool complete: {tool_name}")

            elif event_type == "tool.execution_partial_result":
                logger.debug(f"Tool partial result")

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

            # Unknown events - log at debug for forward compatibility
            elif event_type != "unknown":
                logger.debug(f"Event: {event_type}")

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
