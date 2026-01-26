"""Adapter interface for AI providers."""

from .base import AdapterBase, AdapterConfig, CompactionResult, InfiniteSessionConfig
from .events import EventCollector, EventRecord
from .registry import get_adapter, list_adapters, register_adapter
from .stats import SessionStats, TurnStats

__all__ = [
    "AdapterBase",
    "AdapterConfig",
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
