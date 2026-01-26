"""
Session statistics tracking for adapters.

Provides dataclasses to track token usage, tool calls, and session state.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
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
class CompactionEvent:
    """Record of a single compaction operation."""
    tokens_before: int = 0
    tokens_after: int = 0
    timestamp: Optional[datetime] = None

    @property
    def token_delta(self) -> int:
        """Tokens changed (negative = reduction)."""
        return self.tokens_after - self.tokens_before

    @property
    def effective(self) -> bool:
        """True if compaction reduced tokens."""
        return self.tokens_after < self.tokens_before


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
    # Current context window tracking (updated from session.usage_info)
    current_context_tokens: int = 0
    context_token_limit: int = 128000
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
    # Quota tracking (from assistant.usage quota_snapshots)
    quota_remaining: Optional[float] = None  # Percentage (0-100)
    quota_reset_date: Optional[str] = None  # ISO timestamp
    quota_used_requests: Optional[int] = None  # Requests consumed
    quota_entitlement_requests: Optional[int] = None  # Total allowed
    is_unlimited_quota: bool = False  # Skip warnings if unlimited
    # Rate limit detection (from session.error)
    rate_limited: bool = False
    rate_limit_message: Optional[str] = None
    # Session timing (Phase 1: Observability)
    session_start_time: Optional[datetime] = None
    # Compaction tracking (Phase 1: Observability)
    compaction_events: list = field(default_factory=list)  # List[CompactionEvent]
    # Per-send state (reset each send, used by persistent handler)
    _send_done: Optional[asyncio.Event] = None
    _send_chunks: list = field(default_factory=list)
    _send_full_response: str = ""
    _send_reasoning_parts: list = field(default_factory=list)
    _send_on_chunk: Optional[Callable] = None
    _send_on_reasoning: Optional[Callable] = None
    _send_turn_stats: Optional[TurnStats] = None

    @property
    def session_duration_seconds(self) -> Optional[float]:
        """Duration in seconds since session start."""
        if self.session_start_time is None:
            return None
        return (datetime.now() - self.session_start_time).total_seconds()

    @property
    def requests_per_minute(self) -> Optional[float]:
        """Average requests (turns) per minute."""
        duration = self.session_duration_seconds
        if duration is None or duration < 1:
            return None
        return (self.turns / duration) * 60

    @property
    def compaction_count(self) -> int:
        """Number of compactions performed."""
        return len(self.compaction_events)

    @property
    def compaction_effectiveness(self) -> Optional[float]:
        """Overall compaction ratio (< 1.0 = good, > 1.0 = bad)."""
        if not self.compaction_events:
            return None
        total_before = sum(e.tokens_before for e in self.compaction_events)
        total_after = sum(e.tokens_after for e in self.compaction_events)
        return total_after / total_before if total_before > 0 else None

    @property
    def total_tokens_saved(self) -> int:
        """Cumulative tokens saved by compaction (negative = net increase)."""
        return -sum(e.token_delta for e in self.compaction_events)
