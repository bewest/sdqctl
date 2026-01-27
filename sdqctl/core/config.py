"""
Configuration file loading for sdqctl.

Loads .sdqctl.yaml from project root or home directory.
Config values provide defaults that can be overridden by CLI options.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ConfigDefaults:
    """Default values from config file."""
    adapter: str = "copilot"
    model: str = "gpt-4"


@dataclass
class ConfigContext:
    """Context settings from config file."""
    limit: float = 0.8  # 80%
    on_limit: str = "compact"


@dataclass
class ConfigCheckpoints:
    """Checkpoint settings from config file."""
    enabled: bool = True
    directory: str = ".sdqctl/checkpoints"


@dataclass
class Config:
    """Loaded configuration."""
    project_name: str = ""
    defaults: ConfigDefaults = field(default_factory=ConfigDefaults)
    context: ConfigContext = field(default_factory=ConfigContext)
    checkpoints: ConfigCheckpoints = field(default_factory=ConfigCheckpoints)
    source_path: Optional[Path] = None

    @classmethod
    def from_dict(cls, data: dict, source_path: Optional[Path] = None) -> "Config":
        """Create Config from parsed YAML dict."""
        config = cls(source_path=source_path)

        # Project
        if "project" in data and isinstance(data["project"], dict):
            config.project_name = data["project"].get("name", "")

        # Defaults
        if "defaults" in data and isinstance(data["defaults"], dict):
            defaults = data["defaults"]
            config.defaults.adapter = defaults.get("adapter", config.defaults.adapter)
            config.defaults.model = defaults.get("model", config.defaults.model)

        # Context
        if "context" in data and isinstance(data["context"], dict):
            ctx = data["context"]
            limit = ctx.get("limit", "80%")
            if isinstance(limit, str) and limit.endswith("%"):
                config.context.limit = float(limit.rstrip("%")) / 100
            elif isinstance(limit, (int, float)):
                config.context.limit = float(limit) if limit <= 1 else float(limit) / 100
            config.context.on_limit = ctx.get("on_limit", config.context.on_limit)

        # Checkpoints
        if "checkpoints" in data and isinstance(data["checkpoints"], dict):
            cp = data["checkpoints"]
            config.checkpoints.enabled = cp.get("enabled", config.checkpoints.enabled)
            config.checkpoints.directory = cp.get("directory", config.checkpoints.directory)

        return config


# Global cached config
_cached_config: Optional[Config] = None


def load_config(path: Optional[Path] = None, use_cache: bool = True) -> Config:
    """Load .sdqctl.yaml from project root or home.

    Search order:
    1. Explicit path if provided
    2. .sdqctl.yaml in current directory
    3. .sdqctl.yaml in parent directories (up to git root or /)
    4. ~/.sdqctl.yaml in home directory

    Args:
        path: Explicit path to config file
        use_cache: Whether to use cached config (default True)

    Returns:
        Loaded Config, or default Config if no file found
    """
    global _cached_config

    if use_cache and _cached_config is not None:
        return _cached_config

    config_path = None

    if path and path.exists():
        config_path = path
    else:
        # Search current directory and parents
        search_dir = Path.cwd()
        while search_dir != search_dir.parent:
            candidate = search_dir / ".sdqctl.yaml"
            if candidate.exists():
                config_path = candidate
                break
            # Stop at git root
            if (search_dir / ".git").exists():
                break
            search_dir = search_dir.parent

        # Fall back to home directory
        if config_path is None:
            home_config = Path.home() / ".sdqctl.yaml"
            if home_config.exists():
                config_path = home_config

    if config_path is None:
        config = Config()
    else:
        try:
            data = yaml.safe_load(config_path.read_text())
            config = Config.from_dict(data or {}, source_path=config_path)
        except (yaml.YAMLError, OSError) as e:
            # Log warning but return defaults
            import logging
            logging.getLogger("sdqctl.core.config").warning(
                f"Failed to load config from {config_path}: {e}"
            )
            config = Config()

    if use_cache:
        _cached_config = config

    return config


def clear_config_cache() -> None:
    """Clear the cached config (useful for testing)."""
    global _cached_config
    _cached_config = None


def get_default_adapter() -> str:
    """Get default adapter from config."""
    return load_config().defaults.adapter


def get_default_model() -> str:
    """Get default model from config."""
    return load_config().defaults.model


def get_context_limit() -> float:
    """Get default context limit from config."""
    return load_config().context.limit


def get_checkpoint_directory() -> str:
    """Get checkpoint directory from config."""
    return load_config().checkpoints.directory
