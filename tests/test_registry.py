"""Tests for sdqctl adapter registry."""

from unittest.mock import patch, MagicMock

import pytest

from sdqctl.adapters.registry import (
    register_adapter,
    get_adapter,
    list_adapters,
    _try_load_adapter,
    _adapters,
)
from sdqctl.adapters.base import AdapterBase


@pytest.fixture(autouse=True)
def reset_registry():
    """Clear and reset registry before each test."""
    # Store original state
    original = _adapters.copy()
    _adapters.clear()
    yield
    # Restore
    _adapters.clear()
    _adapters.update(original)


class MockTestAdapter(AdapterBase):
    """Test adapter for registry tests."""
    name = "test_adapter"
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    
    async def start(self):
        pass
    
    async def stop(self):
        pass
    
    async def create_session(self, config):
        pass
    
    async def destroy_session(self, session):
        pass
    
    async def send(self, session, prompt, on_chunk=None):
        return "test response"
    
    async def get_context_usage(self, session):
        return (0, 128000)


class TestRegisterAdapter:
    """Test register_adapter function."""
    
    def test_register_new_adapter(self):
        """Test registering a new adapter."""
        register_adapter("custom", MockTestAdapter)
        
        assert "custom" in _adapters
        assert _adapters["custom"] is MockTestAdapter
    
    def test_register_overwrites(self):
        """Test registering with same name overwrites."""
        class OtherAdapter(MockTestAdapter):
            name = "other"
        
        register_adapter("custom", MockTestAdapter)
        register_adapter("custom", OtherAdapter)
        
        assert _adapters["custom"] is OtherAdapter
    
    def test_register_multiple_adapters(self):
        """Test registering multiple adapters."""
        class AdapterA(MockTestAdapter):
            name = "a"
        
        class AdapterB(MockTestAdapter):
            name = "b"
        
        register_adapter("adapter_a", AdapterA)
        register_adapter("adapter_b", AdapterB)
        
        assert "adapter_a" in _adapters
        assert "adapter_b" in _adapters


class TestGetAdapter:
    """Test get_adapter function."""
    
    def test_get_registered_adapter(self):
        """Test getting a registered adapter."""
        register_adapter("test", MockTestAdapter)
        
        adapter = get_adapter("test")
        
        assert isinstance(adapter, MockTestAdapter)
    
    def test_get_adapter_with_kwargs(self):
        """Test adapter receives kwargs."""
        register_adapter("test", MockTestAdapter)
        
        adapter = get_adapter("test", foo="bar", count=42)
        
        assert adapter.kwargs == {"foo": "bar", "count": 42}
    
    def test_get_unknown_adapter_raises(self):
        """Test getting unknown adapter raises ValueError."""
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent")
    
    def test_error_message_lists_available(self):
        """Test error message includes available adapters."""
        register_adapter("available1", MockTestAdapter)
        register_adapter("available2", MockTestAdapter)
        
        with pytest.raises(ValueError) as exc_info:
            get_adapter("missing")
        
        assert "available1" in str(exc_info.value)
        assert "available2" in str(exc_info.value)
    
    def test_get_mock_adapter(self):
        """Test getting the built-in mock adapter."""
        # This should auto-load the mock adapter
        adapter = get_adapter("mock")
        
        assert adapter is not None
        assert adapter.name == "mock"
    
    def test_get_adapter_lazy_loads(self):
        """Test get_adapter loads adapter if not registered."""
        # Clear to ensure not pre-loaded
        _adapters.clear()
        
        # Getting mock should trigger lazy load
        adapter = get_adapter("mock")
        
        assert "mock" in _adapters


class TestListAdapters:
    """Test list_adapters function."""
    
    def test_list_includes_registered(self):
        """Test list includes registered adapters."""
        register_adapter("custom1", MockTestAdapter)
        register_adapter("custom2", MockTestAdapter)
        
        adapters = list_adapters()
        
        assert "custom1" in adapters
        assert "custom2" in adapters
    
    def test_list_triggers_builtin_load(self):
        """Test list_adapters loads built-in adapters."""
        _adapters.clear()
        
        adapters = list_adapters()
        
        # Should include mock at minimum
        assert "mock" in adapters
    
    def test_list_returns_list(self):
        """Test list_adapters returns a list."""
        adapters = list_adapters()
        
        assert isinstance(adapters, list)
    
    def test_list_empty_when_none_available(self):
        """Test empty list when no adapters available."""
        _adapters.clear()
        
        # Patch _try_load_adapter to do nothing
        with patch("sdqctl.adapters.registry._try_load_adapter"):
            adapters = list_adapters()
        
        assert adapters == []


class TestTryLoadAdapter:
    """Test _try_load_adapter function."""
    
    def test_load_mock(self):
        """Test loading mock adapter."""
        _adapters.clear()
        
        _try_load_adapter("mock")
        
        assert "mock" in _adapters
    
    def test_load_copilot(self):
        """Test loading copilot adapter."""
        _adapters.clear()
        
        _try_load_adapter("copilot")
        
        assert "copilot" in _adapters
    
    def test_load_unknown_does_nothing(self):
        """Test loading unknown name does nothing."""
        _adapters.clear()
        
        _try_load_adapter("unknown_adapter_xyz")
        
        assert "unknown_adapter_xyz" not in _adapters
    
    def test_load_handles_import_error(self):
        """Test loading handles ImportError gracefully."""
        _adapters.clear()
        
        # These may fail if dependencies not installed
        # Should not raise
        _try_load_adapter("claude")
        _try_load_adapter("openai")
        
        # May or may not be present depending on dependencies


class TestRegistryIntegration:
    """Integration tests for adapter registry."""
    
    def test_get_adapter_creates_new_instance(self):
        """Test each get_adapter call creates new instance."""
        register_adapter("test", MockTestAdapter)
        
        adapter1 = get_adapter("test")
        adapter2 = get_adapter("test")
        
        assert adapter1 is not adapter2
    
    def test_registry_isolation(self):
        """Test registry changes don't leak between tests."""
        # This test relies on the autouse fixture
        register_adapter("isolated_test", MockTestAdapter)
        assert "isolated_test" in _adapters
    
    def test_mock_adapter_is_functional(self):
        """Test loaded mock adapter works."""
        adapter = get_adapter("mock")
        
        # Check it has expected methods
        assert hasattr(adapter, "start")
        assert hasattr(adapter, "stop")
        assert hasattr(adapter, "create_session")
        assert hasattr(adapter, "send")
    
    @pytest.mark.asyncio
    async def test_mock_adapter_async_methods(self):
        """Test mock adapter async methods work."""
        adapter = get_adapter("mock")
        
        await adapter.start()
        
        from sdqctl.adapters.base import AdapterConfig
        session = await adapter.create_session(AdapterConfig())
        
        response = await adapter.send(session, "test prompt")
        assert response is not None
        
        await adapter.destroy_session(session)
        await adapter.stop()
