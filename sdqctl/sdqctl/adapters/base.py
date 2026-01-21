"""
Base adapter interface for AI providers.

All adapters must implement this interface to be used with sdqctl.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional


@dataclass
class AdapterConfig:
    """Configuration for an adapter."""

    model: str = "gpt-4"
    streaming: bool = True
    tools: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    preserved_content: str
    summary: str
    tokens_before: int
    tokens_after: int


@dataclass
class AdapterSession:
    """Represents an active session with an adapter."""

    id: str
    adapter: "AdapterBase"
    config: AdapterConfig
    _internal: Any = None  # Adapter-specific session object


class AdapterBase(ABC):
    """
    Base class for AI provider adapters.

    Adapters provide a consistent interface for different AI providers
    (Copilot SDK, Anthropic, OpenAI, Ollama, etc.)
    """

    name: str = "base"

    @abstractmethod
    async def start(self) -> None:
        """Initialize the adapter (e.g., start server, authenticate)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Cleanup the adapter."""
        pass

    @abstractmethod
    async def create_session(self, config: AdapterConfig) -> AdapterSession:
        """Create a new conversation session."""
        pass

    @abstractmethod
    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy a session."""
        pass

    @abstractmethod
    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_reasoning: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Send a prompt and get response.

        Args:
            session: The session to send to
            prompt: The prompt text
            on_chunk: Optional callback for streaming chunks
            on_reasoning: Optional callback for AI reasoning (for loop detection)

        Returns:
            The complete response text
        """
        pass

    @abstractmethod
    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """
        Get context window usage.

        Returns:
            Tuple of (used_tokens, max_tokens)
        """
        pass

    async def compact(
        self,
        session: AdapterSession,
        preserve: list[str],
        summary_prompt: str,
    ) -> CompactionResult:
        """
        Compact the conversation context.

        Default implementation sends a summarization prompt.
        Adapters may override with more sophisticated approaches.
        """
        prompt = f"""Summarize this conversation for continuation.

PRESERVE these items: {', '.join(preserve)}

{summary_prompt}

Provide a concise summary that captures all essential information.
"""
        summary = await self.send(session, prompt)

        used, max_tokens = await self.get_context_usage(session)

        return CompactionResult(
            preserved_content=summary,
            summary=summary,
            tokens_before=used,
            tokens_after=len(summary) // 4,  # Rough estimate
        )

    async def checkpoint(self, session: AdapterSession, name: str) -> str:
        """
        Save session state.

        Returns checkpoint ID. Default implementation uses session ID.
        """
        return f"{session.id}-{name}"

    async def restore(self, checkpoint_id: str) -> Optional[AdapterSession]:
        """
        Restore session from checkpoint.

        Default implementation returns None (not supported).
        """
        return None

    def supports_tools(self) -> bool:
        """Check if adapter supports tool/function calling."""
        return False

    def supports_streaming(self) -> bool:
        """Check if adapter supports streaming responses."""
        return True

    def get_info(self) -> dict:
        """Get adapter information."""
        return {
            "name": self.name,
            "supports_tools": self.supports_tools(),
            "supports_streaming": self.supports_streaming(),
        }
