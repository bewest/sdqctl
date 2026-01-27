"""
Base adapter interface for AI providers.

All adapters must implement this interface to be used with sdqctl.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from sdqctl.core.models import ModelRequirements


@dataclass
class InfiniteSessionConfig:
    """Configuration for SDK infinite sessions with automatic context compaction.

    When enabled, the SDK automatically manages context window limits through
    background compaction, without requiring manual COMPACT directives.

    Attributes:
        enabled: Whether infinite sessions are enabled (default: True for cycle mode)
        min_compaction_density: Skip compaction if context below this % (default: 0.30)
        background_threshold: Start background compaction at this % (default: 0.80)
        buffer_exhaustion: Block until compaction complete at this % (default: 0.95)
    """
    enabled: bool = True
    min_compaction_density: float = 0.30
    background_threshold: float = 0.80
    buffer_exhaustion: float = 0.95


@dataclass
class AdapterConfig:
    """Configuration for an adapter."""

    model: str = "gpt-4"
    streaming: bool = True
    tools: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    # Debug configuration (from ConversationFile DEBUG directives)
    debug_categories: list[str] = field(default_factory=list)  # session, tool, intent, event, all
    debug_intents: bool = False  # Verbose intent tracking
    event_log: Optional[str] = None  # Path for event export

    # Infinite sessions configuration (SDK v2)
    infinite_sessions: Optional[InfiniteSessionConfig] = None


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
    sdk_session_id: Optional[str] = None  # SDK's session UUID for resume


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

    # Metadata APIs (optional - adapters may override)

    async def get_cli_status(self) -> dict:
        """Get CLI/backend version and protocol info.

        Returns:
            Dict with version info, or empty dict if not supported.
            Example: {"version": "0.0.394", "protocol_version": 2}
        """
        return {}

    async def get_auth_status(self) -> dict:
        """Get authentication status.

        Returns:
            Dict with auth info, or empty dict if not supported.
            Example: {"authenticated": True, "login": "user", "auth_type": "user"}
        """
        return {}

    async def list_models(self) -> list[dict]:
        """List available models with capabilities.

        Returns:
            List of model info dicts, or empty list if not supported.
            Example: [{"id": "gpt-4", "context_window": 128000, "vision": True}]
        """
        return []

    def get_available_models(self) -> list[str]:
        """Get list of available model identifiers.

        Returns:
            List of model IDs available through this adapter.
            Default implementation returns empty list (use sdqctl registry).
        """
        return []

    def resolve_model_requirements(
        self,
        requirements: "ModelRequirements",
        fallback: str | None = None,
    ) -> str | None:
        """Resolve abstract model requirements to a concrete model.

        This allows adapters to use their own model availability and
        capabilities data for resolution. Default implementation defers
        to sdqctl's built-in registry.

        Args:
            requirements: ModelRequirements with constraints and preferences
            fallback: Fallback model if no match found

        Returns:
            Model name that satisfies requirements, or fallback/None
        """
        # Import here to avoid circular imports
        from sdqctl.core.models import resolve_model

        available = self.get_available_models() or None
        return resolve_model(requirements, available_models=available, fallback=fallback)
