"""
Adapter registry for managing available AI providers.
"""

from typing import Type

from .base import AdapterBase

# Global registry
_adapters: dict[str, Type[AdapterBase]] = {}


def register_adapter(name: str, adapter_class: Type[AdapterBase]) -> None:
    """Register an adapter class."""
    _adapters[name] = adapter_class


def get_adapter(name: str, **kwargs) -> AdapterBase:
    """Get an adapter instance by name."""
    if name not in _adapters:
        # Try to load adapter module
        _try_load_adapter(name)

    if name not in _adapters:
        available = ", ".join(_adapters.keys()) or "none"
        raise ValueError(f"Unknown adapter: {name}. Available: {available}")

    return _adapters[name](**kwargs)


def list_adapters() -> list[str]:
    """List available adapter names."""
    # Ensure built-in adapters are loaded
    _try_load_adapter("copilot")
    _try_load_adapter("mock")
    _try_load_adapter("claude")
    _try_load_adapter("openai")
    return list(_adapters.keys())


def _try_load_adapter(name: str) -> None:
    """Try to load an adapter module."""
    try:
        if name == "copilot":
            from .copilot import CopilotAdapter

            register_adapter("copilot", CopilotAdapter)
        elif name == "mock":
            from .mock import MockAdapter

            register_adapter("mock", MockAdapter)
        elif name == "claude":
            from .claude import ClaudeAdapter

            register_adapter("claude", ClaudeAdapter)
        elif name == "openai":
            from .openai import OpenAIAdapter

            register_adapter("openai", OpenAIAdapter)
    except ImportError:
        # Adapter not available (missing dependencies)
        pass
