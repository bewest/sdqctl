"""
GitHub Copilot SDK adapter.

Uses the official github/copilot-sdk Python package.
Install with: pip install github-copilot-sdk
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from sdqctl.core.models import ModelRequirements

from .base import AdapterBase, AdapterConfig, AdapterSession, CompactionResult
from .events import CopilotEventHandler, EventCollector
from .stats import SessionStats, TurnStats

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
        """Create a new Copilot session.

        Supports SDK v2 infinite sessions for automatic context management.
        When infinite_sessions is configured, the SDK handles background
        compaction automatically.
        """
        if not self.client:
            raise RuntimeError("Adapter not started. Call start() first.")

        session_config = {
            "model": config.model,
            "streaming": config.streaming,
        }

        if config.tools:
            session_config["tools"] = config.tools

        # Configure infinite sessions if specified
        if config.infinite_sessions is not None:
            infinite_cfg = config.infinite_sessions
            if infinite_cfg.enabled:
                session_config["infinite_sessions"] = {
                    "enabled": True,
                    "background_compaction_threshold": infinite_cfg.background_threshold,
                    "buffer_exhaustion_threshold": infinite_cfg.buffer_exhaustion,
                }
                bg_thresh = f"{infinite_cfg.background_threshold:.0%}"
                buf_thresh = f"{infinite_cfg.buffer_exhaustion:.0%}"
                logger.info(
                    f"Infinite sessions enabled: compact at {bg_thresh}, "
                    f"block at {buf_thresh}"
                )
            else:
                session_config["infinite_sessions"] = {"enabled": False}
                logger.debug("Infinite sessions disabled")

        copilot_session = await self.client.create_session(session_config)

        session_id = str(uuid.uuid4())[:8]
        # Capture SDK's session UUID for checkpoint resume (Q-018 fix)
        sdk_session_id = getattr(copilot_session, 'session_id', None)
        session = AdapterSession(
            id=session_id,
            adapter=self,
            config=config,
            _internal=copilot_session,
            sdk_session_id=sdk_session_id,
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
                intent_count = len(stats.intent_history)
                intent_summary = f", {intent_count} intents" if stats.intent_history else ""
                tool_summary = ""
                if stats.total_tool_calls > 0:
                    tool_summary = f", {stats.total_tool_calls} tools"
                    if stats.tool_calls_failed > 0:
                        tool_summary += f" ({stats.tool_calls_failed} failed)"
                in_tok = stats.total_input_tokens
                out_tok = stats.total_output_tokens
                logger.info(
                    f"Session complete: {stats.turns} turns, "
                    f"{in_tok} in / {out_tok} out tokens{tool_summary}{intent_summary}"
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

        # Reset per-send state (Q-014 fix: handler persists, state resets)
        stats._send_done = asyncio.Event()
        stats._send_chunks = []
        stats._send_full_response = ""
        stats._send_reasoning_parts = []
        stats._send_on_chunk = on_chunk
        stats._send_on_reasoning = on_reasoning
        stats._send_turn_stats = turn_stats

        # Q-014 fix: Only register handler once per session
        if not stats.handler_registered:
            # Create event handler with progress callback
            event_handler = CopilotEventHandler(stats, progress_fn=progress)
            copilot_session.on(event_handler.handle)
            stats.handler_registered = True

        # Send the prompt
        await copilot_session.send({"prompt": prompt})

        # Wait for completion
        await stats._send_done.wait()

        # Check if session was aborted - raise exception for caller to handle
        if stats.abort_reason:
            from ..core.exceptions import AgentAborted
            raise AgentAborted(
                reason=stats.abort_reason,
                details=stats.abort_details,
                turn_number=stats.turns,
            )

        # Return full response or assembled chunks
        return stats._send_full_response or "".join(stats._send_chunks)

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
        """Get context window usage.

        Returns current context window size (not cumulative tokens).
        Updated from session.usage_info events during send().
        """
        stats = self.session_stats.get(session.id)
        if stats and stats.current_context_tokens > 0:
            return (stats.current_context_tokens, stats.context_token_limit)

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
                logger.debug(
                    f"/compact may not have reduced tokens "
                    f"({tokens_before} → {tokens_after}), using response as summary"
                )
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

        compact_prompt = (
            f"/compact {preserve_hint}Summarize this conversation for continuation."
        ).strip()

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

        # Only add prologue/epilogue if explicitly configured
        # Phase 5: No default wrapper - /compact summary is self-contained
        if compaction_prologue:
            context_parts.append(compaction_prologue)

        # Add the summary
        context_parts.append(summary)

        if compaction_epilogue:
            context_parts.append(compaction_epilogue)

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

    async def get_cli_status(self) -> dict:
        """Get Copilot CLI version and protocol info."""
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        try:
            status = await self.client.get_status()
            return {
                "version": status.get("version", "unknown"),
                "protocol_version": status.get("protocolVersion", 1),
            }
        except Exception as e:
            logger.warning(f"get_status failed: {e}")
            return {}

    async def get_auth_status(self) -> dict:
        """Get Copilot authentication status."""
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        try:
            auth = await self.client.get_auth_status()
            return {
                "authenticated": auth.get("isAuthenticated", False),
                "auth_type": auth.get("authType"),
                "host": auth.get("host"),
                "login": auth.get("login"),
                "message": auth.get("statusMessage"),
            }
        except Exception as e:
            logger.warning(f"get_auth_status failed: {e}")
            return {"authenticated": False, "message": str(e)}

    async def list_models(self) -> list[dict]:
        """List available models with capabilities."""
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        try:
            models = await self.client.list_models()
            result = []
            for m in models:
                caps = m.get("capabilities", {})
                limits = caps.get("limits", {})
                supports = caps.get("supports", {})

                result.append({
                    "id": m.get("id", "unknown"),
                    "name": m.get("name", m.get("id", "unknown")),
                    "context_window": limits.get("max_context_window_tokens"),
                    "max_prompt": limits.get("max_prompt_tokens"),
                    "vision": supports.get("vision", False),
                    "policy_state": m.get("policy", {}).get("state"),
                    "billing_multiplier": m.get("billing", {}).get("multiplier"),
                })
            return result
        except Exception as e:
            logger.warning(f"list_models failed: {e}")
            return []

    def get_available_models(self) -> list[str]:
        """Get list of available model identifiers.

        Uses cached models from the last list_models() call, or runs
        synchronously if no cache available.

        Returns:
            List of model IDs available through Copilot.
        """
        # Use cached data if available from a previous list_models() call
        if hasattr(self, "_cached_model_ids") and self._cached_model_ids:
            return self._cached_model_ids

        # Return default models if we can't query
        return ["gpt-4", "gpt-4o", "gpt-4-turbo", "claude-sonnet-4"]

    def resolve_model_requirements(
        self,
        requirements: "ModelRequirements",
        fallback: str | None = None,
    ) -> str | None:
        """Resolve abstract model requirements to a concrete model.

        Uses Copilot's available models and the sdqctl capability registry.

        Args:
            requirements: ModelRequirements with constraints and preferences
            fallback: Fallback model if no match found

        Returns:
            Model name that satisfies requirements, or fallback/None
        """
        from sdqctl.core.models import resolve_model

        available = self.get_available_models()
        return resolve_model(requirements, available_models=available, fallback=fallback)

    # ========================================
    # Session Persistence APIs (SDK v2)
    # ========================================

    async def list_sessions(self) -> list[dict]:
        """List all available sessions with metadata.

        Returns:
            List of session metadata dicts with keys:
            - id: Session identifier
            - start_time: ISO 8601 timestamp
            - modified_time: ISO 8601 timestamp
            - summary: Optional session summary
            - is_remote: Whether session is remote
        """
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        try:
            sessions = await self.client.list_sessions()
            return [
                {
                    "id": s.get("sessionId", ""),
                    "start_time": s.get("startTime", ""),
                    "modified_time": s.get("modifiedTime", ""),
                    "summary": s.get("summary"),
                    "is_remote": s.get("isRemote", False),
                }
                for s in sessions
            ]
        except Exception as e:
            logger.warning(f"list_sessions failed: {e}")
            return []

    async def resume_session(
        self,
        session_id: str,
        config: AdapterConfig
    ) -> AdapterSession:
        """Resume an existing session by ID.

        Restores conversation history and continues from previous state.

        Args:
            session_id: The ID of the session to resume
            config: Adapter configuration for the resumed session

        Returns:
            AdapterSession for the resumed session

        Raises:
            RuntimeError: If session doesn't exist or client not started
        """
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        resume_config = {}
        if config.tools:
            resume_config["tools"] = config.tools

        copilot_session = await self.client.resume_session(
            session_id,
            resume_config if resume_config else None
        )

        # Use the original session_id (or a short version if very long)
        internal_id = session_id[:8] if len(session_id) > 8 else session_id

        session = AdapterSession(
            id=internal_id,
            adapter=self,
            config=config,
            _internal=copilot_session,
        )

        self.sessions[internal_id] = copilot_session
        stats = SessionStats(model=config.model)
        stats.event_collector = EventCollector(internal_id)
        self.session_stats[internal_id] = stats

        logger.info(f"Resumed session: {session_id}")
        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a session permanently.

        The session cannot be resumed after deletion.

        Args:
            session_id: The ID of the session to delete

        Raises:
            RuntimeError: If deletion fails
        """
        _ensure_copilot_sdk()
        if not self.client:
            await self.start()

        await self.client.delete_session(session_id)
        logger.info(f"Deleted session: {session_id}")
