"""
OpenAI adapter stub.

This adapter will integrate with OpenAI's API.
Currently a stub with NotImplementedError for all methods.
"""

from .base import AdapterBase, AdapterConfig, AdapterSession


class OpenAIAdapter(AdapterBase):
    """
    Adapter for OpenAI's API.

    This is a stub implementation. To use OpenAI:
    1. Install openai: pip install openai
    2. Set OPENAI_API_KEY environment variable
    3. Implement the required methods

    See: https://platform.openai.com/docs/api-reference
    """

    name = "openai"

    async def start(self) -> None:
        """Initialize the OpenAI adapter."""
        raise NotImplementedError(
            "OpenAI adapter not implemented. "
            "Contributions welcome: implement using openai Python SDK."
        )

    async def stop(self) -> None:
        """Cleanup the OpenAI adapter."""
        raise NotImplementedError("OpenAI adapter not implemented.")

    async def create_session(self, config: AdapterConfig) -> AdapterSession:
        """Create a new OpenAI conversation session."""
        raise NotImplementedError(
            "OpenAI adapter not implemented. "
            "OpenAI uses stateless API - implement message history tracking."
        )

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy an OpenAI session."""
        raise NotImplementedError("OpenAI adapter not implemented.")

    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk=None,
        on_reasoning=None,
    ) -> str:
        """Send a prompt to OpenAI and get response."""
        raise NotImplementedError(
            "OpenAI adapter not implemented. "
            "Use openai.ChatCompletion.create() for implementation."
        )

    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """Get context window usage."""
        raise NotImplementedError(
            "OpenAI adapter not implemented. "
            "Track prompt_tokens + completion_tokens from usage field in responses."
        )

    def supports_tools(self) -> bool:
        """OpenAI supports function calling."""
        return True  # OpenAI has function calling capability

    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True  # OpenAI supports streaming responses

    def get_available_models(self) -> list[str]:
        """OpenAI model options."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
        ]

    def get_info(self) -> dict:
        """Get adapter information."""
        return {
            "name": self.name,
            "status": "stub",
            "supports_tools": self.supports_tools(),
            "supports_streaming": self.supports_streaming(),
            "documentation": "https://platform.openai.com/docs/api-reference",
        }
