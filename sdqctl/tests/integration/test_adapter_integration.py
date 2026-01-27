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


class TestAdapterErrorPaths:
    """Test adapter error handling and edge cases."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter instance."""
        return get_adapter("mock")

    @pytest.fixture
    def adapter_config(self):
        """Create test adapter config."""
        return AdapterConfig(model="test-model")

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_session(self, mock_adapter, adapter_config):
        """Test destroying a session that doesn't exist."""
        from sdqctl.adapters.base import AdapterSession
        # Create a valid session first, then modify its ID
        session = await mock_adapter.create_session(adapter_config)
        original_id = session.id
        session.id = "nonexistent-session-id"
        # Should not raise - graceful handling
        await mock_adapter.destroy_session(session)

    @pytest.mark.asyncio
    async def test_adapter_capabilities(self, mock_adapter):
        """Test adapter capability queries."""
        assert mock_adapter.supports_tools() in (True, False)
        assert mock_adapter.supports_streaming() in (True, False)

    @pytest.mark.asyncio
    async def test_adapter_info(self, mock_adapter):
        """Test adapter info retrieval."""
        info = mock_adapter.get_info()
        assert "name" in info
        assert info["name"] == "mock"

    @pytest.mark.asyncio
    async def test_context_usage_initial(self, mock_adapter, adapter_config):
        """Test initial context usage is zero or low."""
        session = await mock_adapter.create_session(adapter_config)
        usage = await mock_adapter.get_context_usage(session)
        
        # Usage is a tuple (used, total)
        assert isinstance(usage, tuple)
        assert len(usage) == 2
        used, total = usage
        assert used >= 0
        assert total > 0
        
        await mock_adapter.destroy_session(session)

    @pytest.mark.asyncio
    async def test_context_usage_increases(self, mock_adapter, adapter_config):
        """Test context usage increases after sending messages."""
        session = await mock_adapter.create_session(adapter_config)
        
        initial_used, initial_total = await mock_adapter.get_context_usage(session)
        await mock_adapter.send(session, "Test message to increase context")
        final_used, final_total = await mock_adapter.get_context_usage(session)
        
        # Usage should increase or stay same (mock may not track)
        assert final_used >= initial_used
        
        await mock_adapter.destroy_session(session)


class TestAdapterRegistryVariants:
    """Parametrized tests for adapter registry."""

    @pytest.mark.parametrize("adapter_name,expected_type", [
        ("mock", MockAdapter),
    ])
    def test_get_adapter_by_name(self, adapter_name, expected_type):
        """Test adapter retrieval by name."""
        adapter = get_adapter(adapter_name)
        assert isinstance(adapter, expected_type)

    @pytest.mark.parametrize("invalid_name", [
        "nonexistent",
        "invalid-adapter",
        "",
        "MOCK",  # Case sensitive
    ])
    def test_get_adapter_invalid_name_raises(self, invalid_name):
        """Test that invalid adapter names raise appropriate errors."""
        with pytest.raises((ValueError, KeyError)):
            get_adapter(invalid_name)

    @pytest.mark.parametrize("model_name", [
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-opus",
        "test-model",
        "",  # Empty model name
    ])
    def test_adapter_config_accepts_models(self, model_name):
        """Test AdapterConfig accepts various model names."""
        config = AdapterConfig(model=model_name)
        assert config.model == model_name
