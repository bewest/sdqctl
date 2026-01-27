"""Adapter interface for AI providers."""

from .base import AdapterBase, AdapterConfig, CompactionResult, InfiniteSessionConfig
from .events import EventCollector, EventRecord
from .registry import get_adapter, list_adapters, register_adapter
from .stats import CompactionEvent, SessionStats, TurnStats

__all__ = [
    "AdapterBase",
    "AdapterConfig",
    "CompactionEvent",
    "CompactionResult",
    "EventCollector",
    "EventRecord",
    "InfiniteSessionConfig",
    "SessionStats",
    "TurnStats",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
