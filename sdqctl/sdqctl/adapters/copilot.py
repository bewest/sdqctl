"""
GitHub Copilot SDK adapter.

Uses the official github/copilot-sdk Python package.
Install with: pip install github-copilot-sdk
"""

import asyncio
import uuid
from typing import Callable, Optional

from .base import AdapterBase, AdapterConfig, AdapterSession, CompactionResult

# Lazy import to avoid hard dependency
CopilotClient = None


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
        self.sessions: dict[str, any] = {}

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
        return session

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy a Copilot session."""
        if session.id in self.sessions:
            try:
                await session._internal.destroy()
            except Exception:
                pass
            del self.sessions[session.id]

    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send a prompt and get response."""
        copilot_session = session._internal

        # Set up event handling
        done = asyncio.Event()
        chunks: list[str] = []
        full_response: str = ""

        def on_event(event):
            nonlocal full_response

            event_type = event.type.value if hasattr(event.type, "value") else str(event.type)

            if event_type == "assistant.message_delta":
                # Streaming chunk
                delta = getattr(event.data, "delta_content", "") or ""
                chunks.append(delta)
                if on_chunk and delta:
                    on_chunk(delta)

            elif event_type == "assistant.message":
                # Final message
                full_response = getattr(event.data, "content", "") or ""

            elif event_type == "session.idle":
                # Session finished
                done.set()

        copilot_session.on(on_event)

        # Send the prompt
        await copilot_session.send({"prompt": prompt})

        # Wait for completion
        await done.wait()

        # Return full response or assembled chunks
        return full_response or "".join(chunks)

    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """Get context window usage."""
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
