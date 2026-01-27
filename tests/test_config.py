"""Tests for sdqctl/core/config.py - Configuration loading."""

import pytest
from pathlib import Path
from unittest.mock import patch

pytestmark = pytest.mark.unit


class TestConfig:
    """Test Config dataclass."""
    
    def test_config_default_values(self):
        """Config has sensible defaults."""
        from sdqctl.core.config import Config
        
        config = Config()
        assert config.defaults.adapter == "copilot"
        assert config.defaults.model == "gpt-4"
        assert config.context.limit == 0.8
        assert config.context.on_limit == "compact"
        assert config.checkpoints.enabled is True
    
    def test_config_from_dict_empty(self):
        """Config.from_dict handles empty dict."""
        from sdqctl.core.config import Config
        
        config = Config.from_dict({})
        assert config.defaults.adapter == "copilot"
        assert config.defaults.model == "gpt-4"
    
    def test_config_from_dict_with_defaults(self):
        """Config.from_dict parses defaults section."""
        from sdqctl.core.config import Config
        
        data = {
            "defaults": {
                "adapter": "openai",
                "model": "gpt-4-turbo",
            }
        }
        config = Config.from_dict(data)
        assert config.defaults.adapter == "openai"
        assert config.defaults.model == "gpt-4-turbo"
    
    def test_config_from_dict_with_project(self):
        """Config.from_dict parses project section."""
        from sdqctl.core.config import Config
        
        data = {"project": {"name": "my-project"}}
        config = Config.from_dict(data)
        assert config.project_name == "my-project"
    
    def test_config_from_dict_context_percent_string(self):
        """Config.from_dict parses context limit as percentage string."""
        from sdqctl.core.config import Config
        
        data = {"context": {"limit": "70%", "on_limit": "stop"}}
        config = Config.from_dict(data)
        assert config.context.limit == 0.7
        assert config.context.on_limit == "stop"
    
    def test_config_from_dict_context_float(self):
        """Config.from_dict parses context limit as float."""
        from sdqctl.core.config import Config
        
        data = {"context": {"limit": 0.65}}
        config = Config.from_dict(data)
        assert config.context.limit == 0.65
    
    def test_config_from_dict_context_int_percent(self):
        """Config.from_dict parses context limit as integer percent."""
        from sdqctl.core.config import Config
        
        data = {"context": {"limit": 75}}
        config = Config.from_dict(data)
        assert config.context.limit == 0.75
    
    def test_config_from_dict_checkpoints(self):
        """Config.from_dict parses checkpoints section."""
        from sdqctl.core.config import Config
        
        data = {
            "checkpoints": {
                "enabled": False,
                "directory": "custom/checkpoints",
            }
        }
        config = Config.from_dict(data)
        assert config.checkpoints.enabled is False
        assert config.checkpoints.directory == "custom/checkpoints"
    
    def test_config_from_dict_stores_source_path(self):
        """Config.from_dict stores source path."""
        from sdqctl.core.config import Config
        
        path = Path("/some/path/.sdqctl.yaml")
        config = Config.from_dict({}, source_path=path)
        assert config.source_path == path


class TestLoadConfig:
    """Test load_config function."""
    
    def test_load_config_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """load_config returns defaults when no config file exists."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        config = load_config(use_cache=False)
        assert config.defaults.adapter == "copilot"
        assert config.defaults.model == "gpt-4"
    
    def test_load_config_from_cwd(self, tmp_path, monkeypatch):
        """load_config finds config in current directory."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("""
defaults:
  adapter: claude
  model: claude-3-opus
""")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        config = load_config(use_cache=False)
        assert config.defaults.adapter == "claude"
        assert config.defaults.model == "claude-3-opus"
        assert config.source_path == config_file
    
    def test_load_config_from_explicit_path(self, tmp_path):
        """load_config loads from explicit path."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text("""
defaults:
  adapter: mock
""")
        clear_config_cache()
        
        config = load_config(path=config_file, use_cache=False)
        assert config.defaults.adapter == "mock"
    
    def test_load_config_searches_parent_dirs(self, tmp_path, monkeypatch):
        """load_config searches parent directories."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        # Create config in parent
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  adapter: parent-adapter")
        
        # Create and chdir to subdirectory
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        clear_config_cache()
        
        config = load_config(use_cache=False)
        assert config.defaults.adapter == "parent-adapter"
    
    def test_load_config_stops_at_git_root(self, tmp_path, monkeypatch):
        """load_config stops searching at git root."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        # Create config above git root (should NOT be found)
        (tmp_path / ".sdqctl.yaml").write_text("defaults:\n  adapter: above-git")
        
        # Create git repo subdirectory
        git_repo = tmp_path / "repo"
        git_repo.mkdir()
        (git_repo / ".git").mkdir()
        
        monkeypatch.chdir(git_repo)
        clear_config_cache()
        
        config = load_config(use_cache=False)
        # Should return defaults, not the config above git root
        assert config.defaults.adapter == "copilot"
    
    def test_load_config_caching(self, tmp_path, monkeypatch):
        """load_config caches result."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  adapter: cached")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        config1 = load_config()
        
        # Modify file
        config_file.write_text("defaults:\n  adapter: modified")
        
        # Should still return cached value
        config2 = load_config()
        assert config2.defaults.adapter == "cached"
        assert config1 is config2  # Same object
    
    def test_load_config_handles_yaml_error(self, tmp_path, monkeypatch):
        """load_config handles invalid YAML gracefully."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("invalid: yaml: content: [")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        # Should return defaults, not crash
        config = load_config(use_cache=False)
        assert config.defaults.adapter == "copilot"


class TestHelperFunctions:
    """Test config helper functions."""
    
    def test_get_default_adapter(self, tmp_path, monkeypatch):
        """get_default_adapter returns config value."""
        from sdqctl.core.config import get_default_adapter, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  adapter: custom-adapter")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        assert get_default_adapter() == "custom-adapter"
    
    def test_get_default_model(self, tmp_path, monkeypatch):
        """get_default_model returns config value."""
        from sdqctl.core.config import get_default_model, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  model: gpt-5")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        assert get_default_model() == "gpt-5"
    
    def test_get_context_limit(self, tmp_path, monkeypatch):
        """get_context_limit returns config value."""
        from sdqctl.core.config import get_context_limit, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("context:\n  limit: 60%")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        assert get_context_limit() == 0.6
    
    def test_get_checkpoint_directory(self, tmp_path, monkeypatch):
        """get_checkpoint_directory returns config value."""
        from sdqctl.core.config import get_checkpoint_directory, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("checkpoints:\n  directory: my/checkpoints")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        assert get_checkpoint_directory() == "my/checkpoints"
    
    def test_clear_config_cache(self, tmp_path, monkeypatch):
        """clear_config_cache clears the cached config."""
        from sdqctl.core.config import load_config, clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  adapter: first")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        config1 = load_config()
        assert config1.defaults.adapter == "first"
        
        # Modify file and clear cache
        config_file.write_text("defaults:\n  adapter: second")
        clear_config_cache()
        
        config2 = load_config()
        assert config2.defaults.adapter == "second"


class TestConfigIntegration:
    """Test config integration with ConversationFile."""
    
    def test_conversation_file_uses_config_defaults(self, tmp_path, monkeypatch):
        """ConversationFile uses defaults from config."""
        from sdqctl.core.config import clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("""
defaults:
  adapter: custom-adapter
  model: custom-model
context:
  limit: 50%
""")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        # Import after setting up config
        from sdqctl.core.conversation import ConversationFile
        
        conv = ConversationFile()
        assert conv.adapter == "custom-adapter"
        assert conv.model == "custom-model"
        assert conv.context_limit == 0.5
    
    def test_conversation_file_explicit_values_override_config(self, tmp_path, monkeypatch):
        """Explicit ConversationFile values override config."""
        from sdqctl.core.config import clear_config_cache
        
        config_file = tmp_path / ".sdqctl.yaml"
        config_file.write_text("defaults:\n  adapter: config-adapter")
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        from sdqctl.core.conversation import ConversationFile
        
        conv = ConversationFile(adapter="explicit-adapter")
        assert conv.adapter == "explicit-adapter"
