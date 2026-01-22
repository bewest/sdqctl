"""Tests for CopilotAdapter using mocked SDK."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sdqctl.adapters.base import AdapterConfig
from sdqctl.adapters.copilot import (
    CopilotAdapter,
    SessionStats,
    TurnStats,
    _ensure_copilot_sdk,
)


# Mock event types for testing
@dataclass
class MockEvent:
    """Mock event from Copilot SDK."""
    type: str
    data: Any = None


class MockEventType:
    """Mock event type with value property."""
    def __init__(self, value: str):
        self.value = value


# Test fixtures

@pytest.fixture
def mock_copilot_client():
    """Create a mocked CopilotClient."""
    client = AsyncMock()
    client.start = AsyncMock()
    client.stop = AsyncMock()
    client.create_session = AsyncMock()
    return client


@pytest.fixture
def mock_copilot_session():
    """Create a mocked Copilot session."""
    session = MagicMock()
    session.send = AsyncMock()
    session.destroy = AsyncMock()
    session.get_messages = AsyncMock(return_value=[])
    
    # Store event handler for testing
    session._event_handler = None
    
    def on_handler(handler: Callable):
        session._event_handler = handler
    
    session.on = on_handler
    return session


class TestCopilotAdapterInit:
    """Test CopilotAdapter initialization."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        adapter = CopilotAdapter()
        
        assert adapter.cli_path == "copilot"
        assert adapter.cli_url is None
        assert adapter.use_stdio is True
        assert adapter.client is None
        assert adapter.sessions == {}
        assert adapter.session_stats == {}
    
    def test_init_with_custom_path(self):
        """Test initialization with custom CLI path."""
        adapter = CopilotAdapter(cli_path="/usr/local/bin/copilot")
        
        assert adapter.cli_path == "/usr/local/bin/copilot"
    
    def test_init_with_url(self):
        """Test initialization with server URL."""
        adapter = CopilotAdapter(cli_url="http://localhost:8080")
        
        assert adapter.cli_url == "http://localhost:8080"
        assert adapter.use_stdio is True


class TestCopilotAdapterLifecycle:
    """Test adapter start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_creates_client(self, mock_copilot_client):
        """Test start() initializes CopilotClient."""
        adapter = CopilotAdapter()
        
        with patch("sdqctl.adapters.copilot.CopilotClient", mock_copilot_client):
            with patch("sdqctl.adapters.copilot._ensure_copilot_sdk"):
                # Manually set the client since we're mocking the import
                adapter.client = mock_copilot_client
                await adapter.client.start()
                
                mock_copilot_client.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_cleans_up(self, mock_copilot_client, mock_copilot_session):
        """Test stop() destroys sessions and stops client."""
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        adapter.sessions["test-id"] = mock_copilot_session
        adapter.session_stats["test-id"] = SessionStats()
        
        await adapter.stop()
        
        assert adapter.client is None
        assert adapter.sessions == {}
        assert adapter.session_stats == {}
        mock_copilot_session.destroy.assert_called_once()
        mock_copilot_client.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_handles_session_destroy_error(self, mock_copilot_client, mock_copilot_session):
        """Test stop() continues even if session destroy fails."""
        mock_copilot_session.destroy.side_effect = Exception("Session error")
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        adapter.sessions["test-id"] = mock_copilot_session
        
        # Should not raise
        await adapter.stop()
        
        assert adapter.client is None
        assert adapter.sessions == {}


class TestCopilotAdapterSessions:
    """Test session creation and destruction."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, mock_copilot_client, mock_copilot_session):
        """Test create_session() returns AdapterSession."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        config = AdapterConfig(model="gpt-4", streaming=True)
        session = await adapter.create_session(config)
        
        assert session.id is not None
        assert len(session.id) == 8  # UUID prefix
        assert session.adapter is adapter
        assert session.config == config
        assert session._internal is mock_copilot_session
        assert session.id in adapter.sessions
        assert session.id in adapter.session_stats
    
    @pytest.mark.asyncio
    async def test_create_session_not_started(self):
        """Test create_session() raises if not started."""
        adapter = CopilotAdapter()
        
        with pytest.raises(RuntimeError, match="not started"):
            await adapter.create_session(AdapterConfig())
    
    @pytest.mark.asyncio
    async def test_create_session_with_tools(self, mock_copilot_client, mock_copilot_session):
        """Test create_session() passes tools to SDK."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        tools = [{"name": "test_tool"}]
        config = AdapterConfig(model="gpt-4", tools=tools)
        await adapter.create_session(config)
        
        call_args = mock_copilot_client.create_session.call_args[0][0]
        assert call_args["tools"] == tools
    
    @pytest.mark.asyncio
    async def test_destroy_session(self, mock_copilot_client, mock_copilot_session):
        """Test destroy_session() cleans up."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        session_id = session.id
        
        await adapter.destroy_session(session)
        
        assert session_id not in adapter.sessions
        assert session_id not in adapter.session_stats
        mock_copilot_session.destroy.assert_called()
    
    @pytest.mark.asyncio
    async def test_destroy_session_logs_stats(self, mock_copilot_client, mock_copilot_session, caplog):
        """Test destroy_session() logs final stats."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        # Add some usage
        stats = adapter.session_stats[session.id]
        stats.total_input_tokens = 100
        stats.total_output_tokens = 200
        stats.turns = 3
        
        await adapter.destroy_session(session)
        
        # Stats should be logged (check via logging capture if needed)


class TestCopilotAdapterSend:
    """Test send() message handling."""
    
    @pytest.mark.asyncio
    async def test_send_returns_response(self, mock_copilot_client, mock_copilot_session):
        """Test send() returns assembled response."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        # Simulate event stream
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate turn start
            event = MagicMock()
            event.type = MockEventType("assistant.turn_start")
            handler(event)
            
            # Simulate message chunks
            for chunk in ["Hello", " ", "World"]:
                event = MagicMock()
                event.type = MockEventType("assistant.message_delta")
                event.data = MagicMock(delta_content=chunk)
                handler(event)
            
            # Simulate full message
            event = MagicMock()
            event.type = MockEventType("assistant.message")
            event.data = MagicMock(content="Hello World")
            handler(event)
            
            # Simulate idle
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        
        response = await adapter.send(session, "Test prompt")
        
        assert response == "Hello World"
    
    @pytest.mark.asyncio
    async def test_send_calls_on_chunk(self, mock_copilot_client, mock_copilot_session):
        """Test send() calls on_chunk callback for streaming."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig(streaming=True))
        chunks_received = []
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            for chunk in ["A", "B", "C"]:
                event = MagicMock()
                event.type = MockEventType("assistant.message_delta")
                event.data = MagicMock(delta_content=chunk)
                handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        
        await adapter.send(session, "Test", on_chunk=lambda c: chunks_received.append(c))
        
        assert chunks_received == ["A", "B", "C"]


class TestCopilotAdapterEventHandling:
    """Test event handler for various SDK event types."""
    
    @pytest.mark.asyncio
    async def test_intent_tracking(self, mock_copilot_client, mock_copilot_session):
        """Test assistant.intent events are captured in session stats."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate turn start
            event = MagicMock()
            event.type = MockEventType("assistant.turn_start")
            handler(event)
            
            # Simulate first intent
            event = MagicMock()
            event.type = MockEventType("assistant.intent")
            event.data = MagicMock(intent="Exploring codebase")
            handler(event)
            
            # Simulate second intent (should be added to history)
            event = MagicMock()
            event.type = MockEventType("assistant.intent")
            event.data = MagicMock(intent="Implementing feature")
            handler(event)
            
            # Simulate same intent again (should NOT be added)
            event = MagicMock()
            event.type = MockEventType("assistant.intent")
            event.data = MagicMock(intent="Implementing feature")
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        await adapter.send(session, "Test")
        
        stats = adapter.session_stats[session.id]
        assert stats.current_intent == "Implementing feature"
        assert len(stats.intent_history) == 2
        assert stats.intent_history[0]["intent"] == "Exploring codebase"
        assert stats.intent_history[1]["intent"] == "Implementing feature"
        # Each entry should have a turn number
        assert "turn" in stats.intent_history[0]
    
    @pytest.mark.asyncio
    async def test_session_start_captures_context(self, mock_copilot_client, mock_copilot_session):
        """Test session.start event captures context info."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate session.start
            event = MagicMock()
            event.type = MockEventType("session.start")
            event.data = MagicMock(
                context=MagicMock(branch="main", cwd="/test", repository="test/repo"),
                selected_model="gpt-4-turbo"
            )
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        await adapter.send(session, "Test")
        
        stats = adapter.session_stats[session.id]
        assert stats.model == "gpt-4-turbo"
        assert stats.context_info is not None
        assert stats.context_info["branch"] == "main"
    
    @pytest.mark.asyncio
    async def test_usage_event_accumulates_tokens(self, mock_copilot_client, mock_copilot_session):
        """Test assistant.usage event accumulates token counts."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate usage event
            event = MagicMock()
            event.type = MockEventType("assistant.usage")
            event.data = MagicMock(input_tokens=100, output_tokens=50)
            handler(event)
            
            # Second usage event
            event = MagicMock()
            event.type = MockEventType("assistant.usage")
            event.data = MagicMock(input_tokens=80, output_tokens=40)
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        await adapter.send(session, "Test")
        
        stats = adapter.session_stats[session.id]
        assert stats.total_input_tokens == 180
        assert stats.total_output_tokens == 90
    
    @pytest.mark.asyncio
    async def test_tool_execution_counted(self, mock_copilot_client, mock_copilot_session):
        """Test tool.execution_start increments tool count."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate tool calls
            for tool in ["view", "edit", "grep"]:
                event = MagicMock()
                event.type = MockEventType("tool.execution_start")
                event.data = MagicMock(name=tool)
                handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        await adapter.send(session, "Test")
        
        stats = adapter.session_stats[session.id]
        assert stats.total_tool_calls == 3
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_timing_and_status(self, mock_copilot_client, mock_copilot_session):
        """Test tool execution tracks timing and success/failure status."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        
        async def simulate_events(*args, **kwargs):
            handler = mock_copilot_session._event_handler
            
            # Simulate successful tool
            event = MagicMock()
            event.type = MockEventType("tool.execution_start")
            event.data = MagicMock(name="view", tool_call_id="tc1", arguments={"path": "/test.py"})
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("tool.execution_complete")
            event.data = MagicMock(name="view", tool_call_id="tc1", success=True)
            handler(event)
            
            # Simulate failed tool
            event = MagicMock()
            event.type = MockEventType("tool.execution_start")
            event.data = MagicMock(name="edit", tool_call_id="tc2", arguments={"path": "/missing.py"})
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("tool.execution_complete")
            event.data = MagicMock(name="edit", tool_call_id="tc2", success=False)
            handler(event)
            
            event = MagicMock()
            event.type = MockEventType("session.idle")
            handler(event)
        
        mock_copilot_session.send = simulate_events
        await adapter.send(session, "Test")
        
        stats = adapter.session_stats[session.id]
        assert stats.total_tool_calls == 2
        assert stats.tool_calls_succeeded == 1
        assert stats.tool_calls_failed == 1
        # Active tools should be empty after completion
        assert len(stats.active_tools) == 0


class TestCopilotAdapterInfo:
    """Test adapter info methods."""
    
    def test_supports_tools(self):
        """Test supports_tools() returns True."""
        adapter = CopilotAdapter()
        assert adapter.supports_tools() is True
    
    def test_supports_streaming(self):
        """Test supports_streaming() returns True."""
        adapter = CopilotAdapter()
        assert adapter.supports_streaming() is True
    
    def test_get_info(self):
        """Test get_info() returns adapter details."""
        adapter = CopilotAdapter(cli_path="/custom/path", cli_url="http://test:8080")
        info = adapter.get_info()
        
        assert info["name"] == "copilot"
        assert info["cli_path"] == "/custom/path"
        assert info["cli_url"] == "http://test:8080"
        assert info["connected"] is False
    
    def test_get_info_when_connected(self, mock_copilot_client):
        """Test get_info() shows connected when client exists."""
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        info = adapter.get_info()
        assert info["connected"] is True


class TestCopilotAdapterContextUsage:
    """Test context usage estimation."""
    
    @pytest.mark.asyncio
    async def test_get_context_usage_with_stats(self, mock_copilot_client, mock_copilot_session):
        """Test get_context_usage() uses accumulated stats."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        adapter.session_stats[session.id].total_input_tokens = 5000
        
        used, max_tokens = await adapter.get_context_usage(session)
        
        assert used == 5000
        assert max_tokens == 128000
    
    @pytest.mark.asyncio
    async def test_get_context_usage_estimates_from_messages(self, mock_copilot_client, mock_copilot_session):
        """Test get_context_usage() estimates tokens if no stats."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        # Return messages for estimation
        mock_copilot_session.get_messages.return_value = [
            MagicMock(content="Hello" * 100),  # 500 chars = ~125 tokens
            MagicMock(content="World" * 100),  # 500 chars = ~125 tokens
        ]
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig())
        # Remove stats entry to force message-based estimation
        del adapter.session_stats[session.id]
        
        used, max_tokens = await adapter.get_context_usage(session)
        
        assert used == 250  # 1000 chars / 4
        assert max_tokens == 128000


class TestCopilotAdapterGetSessionStats:
    """Test session stats retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, mock_copilot_client, mock_copilot_session):
        """Test get_session_stats() returns accumulated stats."""
        mock_copilot_client.create_session.return_value = mock_copilot_session
        
        adapter = CopilotAdapter()
        adapter.client = mock_copilot_client
        
        session = await adapter.create_session(AdapterConfig(model="gpt-4"))
        
        # Update stats
        stats = adapter.session_stats[session.id]
        stats.turns = 5
        stats.total_input_tokens = 1000
        stats.total_output_tokens = 2000
        stats.total_tool_calls = 10
        
        retrieved = adapter.get_session_stats(session)
        
        assert retrieved is not None
        assert retrieved.turns == 5
        assert retrieved.total_input_tokens == 1000
        assert retrieved.total_output_tokens == 2000
        assert retrieved.total_tool_calls == 10
        assert retrieved.model == "gpt-4"
    
    def test_get_session_stats_unknown_session(self):
        """Test get_session_stats() returns None for unknown session."""
        adapter = CopilotAdapter()
        
        # Create a fake session with required config
        from sdqctl.adapters.base import AdapterSession, AdapterConfig
        fake_session = AdapterSession(id="unknown", adapter=adapter, config=AdapterConfig())
        
        assert adapter.get_session_stats(fake_session) is None


class TestEnsureCopilotSdk:
    """Test SDK import helper."""
    
    def test_ensure_raises_import_error(self):
        """Test _ensure_copilot_sdk raises helpful error if not installed."""
        with patch.dict("sys.modules", {"copilot": None}):
            with patch("sdqctl.adapters.copilot.CopilotClient", None):
                import sdqctl.adapters.copilot as mod
                mod.CopilotClient = None
                
                with pytest.raises(ImportError, match="GitHub Copilot SDK not installed"):
                    _ensure_copilot_sdk()
