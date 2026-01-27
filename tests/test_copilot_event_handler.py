"""Tests for CopilotEventHandler class.

Tests the event handling logic extracted from CopilotAdapter.send().
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from sdqctl.adapters.events import (
    CopilotEventHandler,
    EventCollector,
    _format_data,
    _get_field,
    _get_tool_name,
)
from sdqctl.adapters.stats import SessionStats, TurnStats


# Mock event types for testing
@dataclass
class MockEvent:
    """Mock event from Copilot SDK."""
    type: Any
    data: Any = None


class MockEventType:
    """Mock event type with value property."""
    def __init__(self, value: str):
        self.value = value


class TestGetField:
    """Tests for _get_field helper function."""

    def test_get_field_from_object(self):
        """Test extracting field from object attribute."""
        class Data:
            foo = "bar"
        
        assert _get_field(Data(), "foo") == "bar"

    def test_get_field_from_dict(self):
        """Test extracting field from dict."""
        data = {"foo": "bar"}
        assert _get_field(data, "foo") == "bar"

    def test_get_field_multiple_keys(self):
        """Test fallback to second key."""
        data = {"alternate": "value"}
        assert _get_field(data, "primary", "alternate") == "value"

    def test_get_field_default(self):
        """Test default value when key not found."""
        data = {}
        assert _get_field(data, "missing", default="default") == "default"

    def test_get_field_none_data(self):
        """Test handling of None data."""
        assert _get_field(None, "foo", default="safe") == "safe"


class TestGetToolName:
    """Tests for _get_tool_name helper function."""

    def test_get_tool_name_direct(self):
        """Test extracting tool_name directly."""
        data = {"tool_name": "bash"}
        assert _get_tool_name(data) == "bash"

    def test_get_tool_name_from_name(self):
        """Test fallback to name field."""
        data = {"name": "view"}
        assert _get_tool_name(data) == "view"

    def test_get_tool_name_from_tool_requests(self):
        """Test extracting from nested tool_requests."""
        data = {"tool_requests": [{"name": "grep"}]}
        assert _get_tool_name(data) == "grep"

    def test_get_tool_name_unknown(self):
        """Test default to 'unknown' when not found."""
        data = {}
        assert _get_tool_name(data) == "unknown"


class TestFormatData:
    """Tests for _format_data helper function."""

    def test_format_data_none(self):
        """Test formatting None."""
        assert _format_data(None) == "None"

    def test_format_data_dict(self):
        """Test formatting dict-like object."""
        class Data:
            foo = "bar"
            baz = 42
        
        result = _format_data(Data())
        assert "foo=bar" in result
        assert "baz=42" in result

    def test_format_data_include_fields(self):
        """Test filtering to specific fields."""
        class Data:
            foo = "bar"
            baz = 42
            secret = "hidden"
        
        result = _format_data(Data(), include_fields=["foo", "baz"])
        assert "foo=bar" in result
        assert "baz=42" in result
        assert "secret" not in result


class TestCopilotEventHandler:
    """Tests for CopilotEventHandler class."""

    @pytest.fixture
    def stats(self):
        """Create fresh SessionStats for each test."""
        s = SessionStats()
        s._send_done = asyncio.Event()
        s._send_chunks = []
        s._send_full_response = ""
        s._send_reasoning_parts = []
        s._send_turn_stats = TurnStats()
        s.event_collector = EventCollector("test-session")
        return s

    @pytest.fixture
    def handler(self, stats):
        """Create handler with progress capture."""
        progress_messages = []
        h = CopilotEventHandler(stats, progress_fn=lambda m: progress_messages.append(m))
        h.progress_messages = progress_messages
        return h

    def test_handle_turn_start(self, handler, stats):
        """Test assistant.turn_start increments turns."""
        event = MockEvent(MockEventType("assistant.turn_start"))
        handler.handle(event)
        assert stats.turns == 1

        handler.handle(event)
        assert stats.turns == 2

    def test_handle_message_delta(self, handler, stats):
        """Test assistant.message_delta collects chunks."""
        event = MockEvent(
            MockEventType("assistant.message_delta"),
            {"delta_content": "Hello "}
        )
        handler.handle(event)
        
        event2 = MockEvent(
            MockEventType("assistant.message_delta"),
            {"delta_content": "World!"}
        )
        handler.handle(event2)
        
        assert stats._send_chunks == ["Hello ", "World!"]

    def test_handle_message(self, handler, stats):
        """Test assistant.message stores full response."""
        event = MockEvent(
            MockEventType("assistant.message"),
            {"content": "Full response text"}
        )
        handler.handle(event)
        assert stats._send_full_response == "Full response text"

    def test_handle_reasoning(self, handler, stats):
        """Test assistant.reasoning collects reasoning."""
        event = MockEvent(
            MockEventType("assistant.reasoning"),
            {"content": "Let me think about this..."}
        )
        handler.handle(event)
        assert "Let me think about this..." in stats._send_reasoning_parts

    def test_handle_usage(self, handler, stats):
        """Test assistant.usage updates token counts."""
        event = MockEvent(
            MockEventType("assistant.usage"),
            {"input_tokens": 100, "output_tokens": 50}
        )
        handler.handle(event)
        
        assert stats.total_input_tokens == 100
        assert stats.total_output_tokens == 50
        assert stats._send_turn_stats.input_tokens == 100
        assert stats._send_turn_stats.output_tokens == 50

    def test_handle_tool_execution_start(self, handler, stats):
        """Test tool.execution_start tracks tool calls."""
        event = MockEvent(
            MockEventType("tool.execution_start"),
            {"tool_name": "bash", "tool_call_id": "call-1", "arguments": {"cmd": "ls"}}
        )
        handler.handle(event)
        
        assert stats.total_tool_calls == 1
        assert stats._send_turn_stats.tool_calls == 1
        assert "call-1" in stats.active_tools

    def test_handle_tool_execution_complete(self, handler, stats):
        """Test tool.execution_complete tracks success/failure."""
        # First start the tool
        start = MockEvent(
            MockEventType("tool.execution_start"),
            {"tool_name": "grep", "tool_call_id": "call-2"}
        )
        handler.handle(start)
        
        # Then complete it
        complete = MockEvent(
            MockEventType("tool.execution_complete"),
            {"tool_call_id": "call-2", "success": True}
        )
        handler.handle(complete)
        
        assert stats.tool_calls_succeeded == 1
        assert stats.tool_calls_failed == 0
        assert "call-2" not in stats.active_tools

    def test_handle_tool_execution_failed(self, handler, stats):
        """Test tool.execution_complete tracks failures."""
        start = MockEvent(
            MockEventType("tool.execution_start"),
            {"tool_name": "edit", "tool_call_id": "call-3"}
        )
        handler.handle(start)
        
        complete = MockEvent(
            MockEventType("tool.execution_complete"),
            {"tool_call_id": "call-3", "success": False}
        )
        handler.handle(complete)
        
        assert stats.tool_calls_succeeded == 0
        assert stats.tool_calls_failed == 1

    def test_handle_intent(self, handler, stats):
        """Test assistant.intent tracks intent changes."""
        event = MockEvent(
            MockEventType("assistant.intent"),
            {"intent": "Exploring codebase"}
        )
        handler.handle(event)
        
        assert stats.current_intent == "Exploring codebase"
        assert len(stats.intent_history) == 1
        assert "🎯" in handler.progress_messages[0]

    def test_handle_intent_no_duplicate(self, handler, stats):
        """Test same intent is not tracked twice."""
        event = MockEvent(
            MockEventType("assistant.intent"),
            {"intent": "Writing tests"}
        )
        handler.handle(event)
        handler.handle(event)  # Same intent again
        
        assert len(stats.intent_history) == 1

    def test_handle_session_idle(self, handler, stats):
        """Test session.idle sets done event."""
        assert not stats._send_done.is_set()
        
        event = MockEvent(MockEventType("session.idle"))
        handler.handle(event)
        
        assert stats._send_done.is_set()

    def test_handle_abort(self, handler, stats):
        """Test abort event stores reason and sets done."""
        event = MockEvent(
            MockEventType("abort"),
            {"reason": "Rate limited", "details": "Try again in 5 minutes"}
        )
        handler.handle(event)
        
        assert stats.abort_reason == "Rate limited"
        assert stats.abort_details == "Try again in 5 minutes"
        assert stats._send_done.is_set()

    def test_handle_session_error_rate_limit(self, handler, stats):
        """Test session.error detects rate limits."""
        event = MockEvent(
            MockEventType("session.error"),
            {"error": {"code": "429", "message": "Too many requests"}}
        )
        handler.handle(event)
        
        assert stats.rate_limited is True
        assert "rate limited" in handler.progress_messages[0].lower()

    def test_handle_compaction_complete(self, handler, stats):
        """Test session.compaction_complete tracks compaction."""
        event = MockEvent(
            MockEventType("session.compaction_complete"),
            {"compaction_tokens_used": {"before": 10000, "after": 3000}}
        )
        handler.handle(event)
        
        assert len(stats.compaction_events) == 1
        assert stats.compaction_events[0].tokens_before == 10000
        assert stats.compaction_events[0].tokens_after == 3000

    def test_handle_session_start(self, handler, stats):
        """Test session.start sets session info."""
        event = MockEvent(
            MockEventType("session.start"),
            {
                "context": {"branch": "main", "cwd": "/project", "repository": "test-repo"},
                "selected_model": "gpt-4"
            }
        )
        handler.handle(event)
        
        assert stats.session_start_time is not None
        assert stats.model == "gpt-4"
        assert stats.context_info["branch"] == "main"

    def test_handle_usage_info(self, handler, stats):
        """Test session.usage_info updates context tracking."""
        # Need to create mock data with attributes
        class UsageData:
            current_tokens = 50000
            token_limit = 128000
            messages_length = 25
        
        event = MockEvent(MockEventType("session.usage_info"), UsageData())
        handler.handle(event)
        
        assert stats.current_context_tokens == 50000
        assert stats.context_token_limit == 128000

    def test_events_recorded_to_collector(self, handler, stats):
        """Test events are recorded to event collector."""
        event = MockEvent(MockEventType("assistant.turn_start"))
        handler.handle(event)
        
        assert len(stats.event_collector.events) == 1
        assert stats.event_collector.events[0].event_type == "assistant.turn_start"

    def test_ephemeral_events_marked(self, handler, stats):
        """Test streaming events are marked ephemeral."""
        event = MockEvent(
            MockEventType("assistant.message_delta"),
            {"delta_content": "hi"}
        )
        handler.handle(event)
        
        assert stats.event_collector.events[0].ephemeral is True

    def test_chunk_callback_invoked(self, stats):
        """Test on_chunk callback is called."""
        chunks = []
        stats._send_on_chunk = lambda c: chunks.append(c)
        handler = CopilotEventHandler(stats)
        
        event = MockEvent(
            MockEventType("assistant.message_delta"),
            {"delta_content": "Hello"}
        )
        handler.handle(event)
        
        assert chunks == ["Hello"]

    def test_reasoning_callback_invoked(self, stats):
        """Test on_reasoning callback is called."""
        reasons = []
        stats._send_on_reasoning = lambda r: reasons.append(r)
        handler = CopilotEventHandler(stats)
        
        event = MockEvent(
            MockEventType("assistant.reasoning"),
            {"content": "Analyzing..."}
        )
        handler.handle(event)
        
        assert reasons == ["Analyzing..."]
