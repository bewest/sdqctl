"""
Mock adapter for testing and development.

Provides a simple echo/scripted response adapter.
"""

import asyncio
import uuid
from typing import Callable, Optional

from .base import AdapterBase, AdapterConfig, AdapterSession


class MockAdapter(AdapterBase):
    """Mock adapter for testing."""

    name = "mock"

    def __init__(self, responses: Optional[list[str]] = None, delay: float = 0.1):
        """
        Initialize mock adapter.

        Args:
            responses: List of canned responses (cycles through them)
            delay: Simulated response delay in seconds
        """
        self.responses = responses or [
            "This is a mock response. The real adapter would connect to an AI provider.",
            "Mock response #2. Testing workflow execution.",
            "Mock response #3. All workflows complete.",
        ]
        self.delay = delay
        self.response_index = 0
        self.sessions: dict[str, dict] = {}

    async def start(self) -> None:
        """Initialize (no-op for mock)."""
        pass

    async def stop(self) -> None:
        """Cleanup (no-op for mock)."""
        self.sessions.clear()

    async def create_session(self, config: AdapterConfig) -> AdapterSession:
        """Create a mock session."""
        session_id = str(uuid.uuid4())[:8]
        session = AdapterSession(
            id=session_id,
            adapter=self,
            config=config,
            _internal={"messages": [], "tokens_used": 0},
        )
        self.sessions[session_id] = session._internal
        return session

    async def destroy_session(self, session: AdapterSession) -> None:
        """Destroy mock session."""
        if session.id in self.sessions:
            del self.sessions[session.id]

    async def send(
        self,
        session: AdapterSession,
        prompt: str,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_reasoning: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send prompt and get mock response."""
        # Simulate delay
        await asyncio.sleep(self.delay)

        # Get next response
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1

        # Track in session
        internal = self.sessions.get(session.id, {"messages": [], "tokens_used": 0})
        internal["messages"].append({"role": "user", "content": prompt})
        internal["messages"].append({"role": "assistant", "content": response})
        internal["tokens_used"] += (len(prompt) + len(response)) // 4

        # Simulate streaming if callback provided
        if on_chunk:
            words = response.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                on_chunk(chunk)
                await asyncio.sleep(self.delay / 10)

        return response

    async def get_context_usage(self, session: AdapterSession) -> tuple[int, int]:
        """Get mock context usage."""
        internal = self.sessions.get(session.id, {"tokens_used": 0})
        return (internal["tokens_used"], 128000)

    def supports_tools(self) -> bool:
        return False

    def supports_streaming(self) -> bool:
        return True
