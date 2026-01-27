"""
Claude adapter stub.

This adapter will integrate with Anthropic's Claude API.
Currently a stub with NotImplementedError for all methods.
"""

from .base import AdapterBase, AdapterConfig, AdapterSession


class ClaudeAdapter(AdapterBase):
    """
    Adapter for Anthropic's Claude API.

    This is a stub implementation. To use Claude:
    1. Install anthropic: pip install anthropic
    2. Set ANTHROPIC_API_KEY environment variable
    3. Implement the required methods

    See: https://docs.anthropic.com/claude/reference/getting-started-with-the-api
    """

    name = "claude"

    async def start(self) -> None:
        """Initialize the Claude adapter."""
        raise NotImplementedError(
            "Claude adapter not implemented. "
            "Contributions welcome: implement using anthropic Python SDK."
        )

    async def stop(self) -> None:
        """Cleanup the Claude adapter."""
        raise NotImplementedError("Claude adapter not implemented.")

    async def create_session(self, config: AdapterConfig) -> AdapterSession:
        """Create a new Claude conversation session."""
        raise NotImplementedError(
            "Claude adapter not implemented. "
            "Claude uses stateless API - implement message history tracking."
        )

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy a Claude session."""
        raise NotImplementedError("Claude adapter not implemented.")

    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk=None,
        on_reasoning=None,
    ) -> str:
        """Send a prompt to Claude and get response."""
        raise NotImplementedError(
            "Claude adapter not implemented. "
            "Use anthropic.Anthropic().messages.create() for implementation."
        )

    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """Get context window usage."""
        raise NotImplementedError(
            "Claude adapter not implemented. "
            "Track input_tokens + output_tokens from usage field in responses."
        )

    def supports_tools(self) -> bool:
        """Claude supports tool use."""
        return True  # Claude has tool_use capability

    def supports_streaming(self) -> bool:
        """Claude supports streaming."""
        return True  # Claude supports streaming responses

    def get_available_models(self) -> list[str]:
        """Claude model options."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def get_info(self) -> dict:
        """Get adapter information."""
        return {
            "name": self.name,
            "status": "stub",
            "supports_tools": self.supports_tools(),
            "supports_streaming": self.supports_streaming(),
            "documentation": "https://docs.anthropic.com/claude/reference",
        }
