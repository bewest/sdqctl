"""
Tests for Adapters - sdqctl/adapters/

P0 Critical - Adapter interface verification.
"""

import pytest
import asyncio

from sdqctl.adapters.mock import MockAdapter
from sdqctl.adapters.base import AdapterBase, AdapterConfig, AdapterSession
from sdqctl.adapters.registry import get_adapter, list_adapters


class TestMockAdapterLifecycle:
    """Tests for mock adapter lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test adapter start/stop work correctly."""
        adapter = MockAdapter()
        
        await adapter.start()  # Should not raise
        await adapter.stop()   # Should clear sessions
        
        assert len(adapter.sessions) == 0

    @pytest.mark.asyncio
    async def test_stop_clears_sessions(self):
        """Test stop clears all sessions."""
        adapter = MockAdapter()
        await adapter.start()
        
        # Create a session
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)
        assert len(adapter.sessions) == 1
        
        # Stop should clear
        await adapter.stop()
        assert len(adapter.sessions) == 0


class TestMockAdapterSession:
    """Tests for mock adapter session management."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        adapter = MockAdapter()
        config = AdapterConfig(model="gpt-4", streaming=True)
        
        session = await adapter.create_session(config)
        
        assert session.id is not None
        assert len(session.id) == 8
        assert session.adapter == adapter
        assert session.config == config
        assert session.id in adapter.sessions

    @pytest.mark.asyncio
    async def test_destroy_session(self):
        """Test session destruction."""
        adapter = MockAdapter()
        config = AdapterConfig()
        
        session = await adapter.create_session(config)
        session_id = session.id
        
        await adapter.destroy_session(session)
        
        assert session_id not in adapter.sessions

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_session(self):
        """Test destroying non-existent session doesn't raise."""
        adapter = MockAdapter()
        config = AdapterConfig()
        
        session = await adapter.create_session(config)
        await adapter.destroy_session(session)
        
        # Second destroy should not raise
        await adapter.destroy_session(session)


class TestMockAdapterSend:
    """Tests for mock adapter send functionality."""

    @pytest.mark.asyncio
    async def test_send_returns_response(self):
        """Test send returns canned response."""
        adapter = MockAdapter(
            responses=["Response 1", "Response 2", "Response 3"],
            delay=0.01,
        )
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        response1 = await adapter.send(session, "First prompt")
        response2 = await adapter.send(session, "Second prompt")
        
        assert response1 == "Response 1"
        assert response2 == "Response 2"

    @pytest.mark.asyncio
    async def test_send_cycles_responses(self):
        """Test send cycles through response list."""
        adapter = MockAdapter(responses=["A", "B"], delay=0.01)
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        r1 = await adapter.send(session, "P1")
        r2 = await adapter.send(session, "P2")
        r3 = await adapter.send(session, "P3")  # Cycles back
        
        assert r1 == "A"
        assert r2 == "B"
        assert r3 == "A"

    @pytest.mark.asyncio
    async def test_send_tracks_messages(self):
        """Test send tracks messages in session."""
        adapter = MockAdapter(responses=["Response"], delay=0.01)
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        await adapter.send(session, "Test prompt")
        
        internal = adapter.sessions[session.id]
        assert len(internal["messages"]) == 2  # user + assistant
        assert internal["messages"][0]["role"] == "user"
        assert internal["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_send_calls_on_chunk(self):
        """Test streaming callback is invoked."""
        adapter = MockAdapter(responses=["Hello world"], delay=0.01)
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        chunks = []
        def on_chunk(chunk):
            chunks.append(chunk)
        
        await adapter.send(session, "Test", on_chunk=on_chunk)
        
        # Should have received chunks
        assert len(chunks) > 0
        # Joined chunks should equal response
        assert "".join(chunks) == "Hello world"

    @pytest.mark.asyncio
    async def test_send_updates_token_count(self):
        """Test send updates token usage."""
        adapter = MockAdapter(responses=["A short response"], delay=0.01)
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        await adapter.send(session, "A test prompt")
        
        internal = adapter.sessions[session.id]
        assert internal["tokens_used"] > 0


class TestMockAdapterContextUsage:
    """Tests for context usage tracking."""

    @pytest.mark.asyncio
    async def test_get_context_usage(self):
        """Test context usage returns (used, max)."""
        adapter = MockAdapter(responses=["Response"], delay=0.01)
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        # Initially zero
        used, max_tokens = await adapter.get_context_usage(session)
        assert used == 0
        assert max_tokens == 128000
        
        # After send
        await adapter.send(session, "Test prompt")
        used, max_tokens = await adapter.get_context_usage(session)
        assert used > 0
        assert max_tokens == 128000


class TestMockAdapterCapabilities:
    """Tests for adapter capability reporting."""

    def test_supports_tools(self):
        """Mock adapter doesn't support tools."""
        adapter = MockAdapter()
        assert adapter.supports_tools() is False

    def test_supports_streaming(self):
        """Mock adapter supports streaming."""
        adapter = MockAdapter()
        assert adapter.supports_streaming() is True

    def test_get_info(self):
        """Test adapter info reporting."""
        adapter = MockAdapter()
        info = adapter.get_info()
        
        assert info["name"] == "mock"
        assert info["supports_tools"] is False
        assert info["supports_streaming"] is True


class TestAdapterRegistry:
    """Tests for adapter registry."""

    def test_get_adapter_mock(self):
        """Test mock adapter retrieval."""
        adapter = get_adapter("mock")
        
        assert adapter is not None
        assert isinstance(adapter, MockAdapter)

    def test_get_adapter_unknown_raises(self):
        """Test ValueError for unknown adapter."""
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent-adapter")

    def test_list_adapters(self):
        """Test listing available adapters."""
        adapters = list_adapters()
        
        assert isinstance(adapters, list)
        assert "mock" in adapters


class TestAdapterBaseCompact:
    """Tests for base adapter compaction."""

    @pytest.mark.asyncio
    async def test_compact_default_implementation(self):
        """Test default compact sends summarization prompt."""
        adapter = MockAdapter(
            responses=["Summary of conversation"],
            delay=0.01,
        )
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        result = await adapter.compact(
            session,
            preserve=["findings", "recommendations"],
            summary_prompt="Focus on security issues",
        )
        
        assert result.summary == "Summary of conversation"
        assert result.preserved_content == "Summary of conversation"


class TestAdapterBaseCheckpoint:
    """Tests for base adapter checkpoint."""

    @pytest.mark.asyncio
    async def test_checkpoint_default(self):
        """Test default checkpoint returns ID."""
        adapter = MockAdapter()
        config = AdapterConfig()
        session = await adapter.create_session(config)
        
        checkpoint_id = await adapter.checkpoint(session, "test-checkpoint")
        
        assert session.id in checkpoint_id
        assert "test-checkpoint" in checkpoint_id

    @pytest.mark.asyncio
    async def test_restore_default(self):
        """Test default restore returns None (not supported)."""
        adapter = MockAdapter()
        
        restored = await adapter.restore("some-checkpoint-id")
        
        assert restored is None


class TestAdapterMetadataAPIs:
    """Tests for adapter metadata APIs (get_cli_status, get_auth_status, list_models)."""

    @pytest.mark.asyncio
    async def test_get_cli_status_mock(self):
        """Test mock adapter returns CLI status."""
        adapter = MockAdapter()
        status = await adapter.get_cli_status()
        
        assert "version" in status
        assert "protocol_version" in status
        assert status["version"] == "0.0.0-mock"
        assert status["protocol_version"] == 2

    @pytest.mark.asyncio
    async def test_get_auth_status_mock(self):
        """Test mock adapter returns auth status."""
        adapter = MockAdapter()
        auth = await adapter.get_auth_status()
        
        assert auth["authenticated"] is True
        assert auth["auth_type"] == "mock"
        assert auth["login"] == "mock-user"
        assert "message" in auth

    @pytest.mark.asyncio
    async def test_list_models_mock(self):
        """Test mock adapter returns model list."""
        adapter = MockAdapter()
        models = await adapter.list_models()
        
        assert len(models) >= 1
        model = models[0]
        assert "id" in model
        assert "name" in model
        assert "context_window" in model
        assert "vision" in model
        assert model["id"] == "mock-model"

    @pytest.mark.asyncio
    async def test_base_adapter_metadata_defaults(self):
        """Test base adapter returns empty defaults."""
        # Create a minimal concrete adapter
        class MinimalAdapter(AdapterBase):
            async def start(self): pass
            async def stop(self): pass
            async def create_session(self, config): pass
            async def destroy_session(self, session): pass
            async def send(self, session, prompt, **kw): return ""
            async def get_context_usage(self, session): return (0, 128000)
        
        adapter = MinimalAdapter()
        
        # Base implementation returns empty/defaults
        assert await adapter.get_cli_status() == {}
        assert await adapter.get_auth_status() == {}
        assert await adapter.list_models() == []
