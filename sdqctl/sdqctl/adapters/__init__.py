"""Adapter interface for AI providers."""

from .base import AdapterBase, AdapterConfig, CompactionResult
from .registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "AdapterBase",
    "AdapterConfig",
    "CompactionResult",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
