"""
Integration tests for adapter functionality.

Tests adapter initialization, session management, and message exchange
using the mock adapter for deterministic behavior.
"""

import pytest
from pathlib import Path

from sdqctl.adapters.registry import get_adapter
from sdqctl.adapters.base import AdapterConfig
from sdqctl.adapters.mock import MockAdapter


class TestAdapterIntegration:
    """Integration tests for adapter lifecycle."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter instance."""
        return get_adapter("mock")

    @pytest.fixture
    def adapter_config(self):
        """Create test adapter config."""
        return AdapterConfig(model="test-model")

    def test_adapter_factory_returns_correct_type(self):
        """Test get_adapter returns correct adapter type."""
        adapter = get_adapter("mock")
        assert isinstance(adapter, MockAdapter)

    @pytest.mark.asyncio
    async def test_adapter_session_lifecycle(self, mock_adapter, adapter_config):
        """Test full adapter session lifecycle."""
        # Create session
        session = await mock_adapter.create_session(adapter_config)
        assert session is not None
        assert session.id is not None

        # Send message
        response = await mock_adapter.send(session, "Test prompt")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

        # Destroy session
        await mock_adapter.destroy_session(session)

    @pytest.mark.asyncio
    async def test_adapter_multiple_messages(self, mock_adapter, adapter_config):
        """Test sending multiple messages in a session."""
        session = await mock_adapter.create_session(adapter_config)

        responses = []
        for i in range(3):
            response = await mock_adapter.send(
                session, 
                f"Message {i + 1}"
            )
            responses.append(response)

        assert len(responses) == 3
        assert all(r is not None for r in responses)

        await mock_adapter.destroy_session(session)

    @pytest.mark.asyncio
    async def test_adapter_handles_empty_prompt(self, mock_adapter, adapter_config):
        """Test adapter handles empty prompts gracefully."""
        session = await mock_adapter.create_session(adapter_config)
        
        response = await mock_adapter.send(session, "")
        assert response is not None

        await mock_adapter.destroy_session(session)


class TestAdapterConfigVariants:
    """Test adapter configuration variants."""

    def test_mock_adapter_instantiation(self):
        """Test mock adapter instantiation."""
        adapter = get_adapter("mock")
        assert adapter is not None
        assert isinstance(adapter, MockAdapter)

    def test_mock_adapter_with_custom_responses(self):
        """Test mock adapter with custom responses."""
        adapter = MockAdapter(responses=["Custom response 1", "Custom response 2"])
        assert len(adapter.responses) == 2

    @pytest.mark.asyncio
    async def test_adapter_session_isolation(self):
        """Test that multiple adapter sessions are isolated."""
        adapter = get_adapter("mock")
        config = AdapterConfig(model="test-model")

        session1 = await adapter.create_session(config)
        session2 = await adapter.create_session(config)

        # Sessions should be independent
        assert session1.id != session2.id

        response1 = await adapter.send(session1, "Session 1 message")
        response2 = await adapter.send(session2, "Session 2 message")

        assert response1 is not None
        assert response2 is not None

        await adapter.destroy_session(session1)
        await adapter.destroy_session(session2)
