"""
Session statistics tracking for adapters.

Provides dataclasses to track token usage, tool calls, and session state.
"""

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .events import EventCollector


@dataclass
class TurnStats:
    """Statistics for a single turn."""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    reasoning_shown: bool = False


@dataclass
class SessionStats:
    """Accumulated statistics for a session."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    tool_calls_succeeded: int = 0
    tool_calls_failed: int = 0
    turns: int = 0
    model: Optional[str] = None
    context_info: Optional[dict] = None
    # Intent tracking
    current_intent: Optional[str] = None
    intent_history: list = field(default_factory=list)
    # Active tools (for timing)
    active_tools: dict = field(default_factory=dict)
    # Event collector for export
    event_collector: Optional["EventCollector"] = None
    # Abort tracking
    abort_reason: Optional[str] = None
    abort_details: Optional[str] = None
    # Handler registration tracking (Q-014 fix)
    handler_registered: bool = False
    # Per-send state (reset each send, used by persistent handler)
    _send_done: Optional[asyncio.Event] = None
    _send_chunks: list = field(default_factory=list)
    _send_full_response: str = ""
    _send_reasoning_parts: list = field(default_factory=list)
    _send_on_chunk: Optional[Callable] = None
    _send_on_reasoning: Optional[Callable] = None
    _send_turn_stats: Optional[TurnStats] = None
