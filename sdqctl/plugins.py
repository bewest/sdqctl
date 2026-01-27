"""
Plugin discovery and registration for sdqctl.

Loads custom directives from .sdqctl/directives.yaml manifests.
Supports workspace-local and user-global plugins.

See: proposals/PLUGIN-SYSTEM.md
Schema: docs/directives-schema.json
"""

import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .verifiers.base import VerificationError, VerificationResult


@dataclass
class DirectiveHandler:
    """Configuration for a plugin directive handler."""

    name: str
    directive_type: str  # e.g., "VERIFY", "TRACE"
    handler: str  # Shell command to execute
    description: str
    args: list[dict[str, Any]] = field(default_factory=list)
    timeout: int = 30
    requires: list[str] = field(default_factory=list)  # Capabilities
    
    # Valid capabilities
    VALID_CAPABILITIES = frozenset({
        "read_files",      # Read files in workspace
        "write_files",     # Write to specific paths
        "run_commands",    # Execute shell commands
        "network",         # Make network requests
        "adapter_access",  # Full adapter API access
    })
    
    def validate_capabilities(self) -> list[str]:
        """Return list of invalid capabilities."""
        return [c for c in self.requires if c not in self.VALID_CAPABILITIES]


@dataclass
class PluginManifest:
    """Parsed .sdqctl/directives.yaml manifest."""

    version: int
    handlers: list[DirectiveHandler] = field(default_factory=list)
    source_path: Path | None = None

    @classmethod
    def from_file(cls, path: Path) -> "PluginManifest":
        """Load manifest from YAML file."""
        content = path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid manifest: expected dict, got {type(data)}")

        version = data.get("version", 1)
        handlers: list[DirectiveHandler] = []

        directives = data.get("directives", {})
        for directive_type, subcommands in directives.items():
            if not isinstance(subcommands, dict):
                continue
            for name, config in subcommands.items():
                if not isinstance(config, dict):
                    continue
                handler = DirectiveHandler(
                    name=name,
                    directive_type=directive_type.upper(),
                    handler=config.get("handler", ""),
                    description=config.get("description", ""),
                    args=config.get("args", []),
                    timeout=config.get("timeout", 30),
                    requires=config.get("requires", []),
                )
                handlers.append(handler)

        return cls(version=version, handlers=handlers, source_path=path)


class PluginVerifier:
    """Verifier that wraps a plugin handler command."""

    def __init__(self, handler: DirectiveHandler, workspace_root: Path):
        self.handler = handler
        self.workspace_root = workspace_root
        self.name = handler.name
        self.description = handler.description

    def verify(self, root: Path, **options: Any) -> VerificationResult:
        """Execute the plugin handler and return results."""
        cmd = self.handler.handler

        # Substitute {root} placeholder if present
        cmd = cmd.replace("{root}", str(root))
        cmd = cmd.replace("{workspace}", str(self.workspace_root))

        try:
            result = subprocess.run(
                shlex.split(cmd),
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=self.handler.timeout,
            )

            if result.returncode == 0:
                return VerificationResult(
                    passed=True,
                    summary=f"Plugin '{self.name}' passed",
                    details={"stdout": result.stdout, "stderr": result.stderr},
                )
            else:
                return VerificationResult(
                    passed=False,
                    summary=f"Plugin '{self.name}' failed (exit {result.returncode})",
                    errors=[
                        VerificationError(
                            file=str(self.workspace_root),
                            line=None,
                            message=result.stderr or result.stdout or "Unknown error",
                        )
                    ],
                    details={"stdout": result.stdout, "stderr": result.stderr},
                )

        except subprocess.TimeoutExpired:
            return VerificationResult(
                passed=False,
                summary=f"Plugin '{self.name}' timed out after {self.handler.timeout}s",
                errors=[
                    VerificationError(
                        file=str(self.workspace_root),
                        line=None,
                        message=f"Handler timed out after {self.handler.timeout} seconds",
                    )
                ],
            )
        except FileNotFoundError as e:
            return VerificationResult(
                passed=False,
                summary=f"Plugin '{self.name}' handler not found",
                errors=[
                    VerificationError(
                        file=str(self.workspace_root),
                        line=None,
                        message=f"Handler not found: {e}",
                        fix_hint=f"Check that '{cmd}' exists and is executable",
                    )
                ],
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                summary=f"Plugin '{self.name}' error: {e}",
                errors=[
                    VerificationError(
                        file=str(self.workspace_root),
                        line=None,
                        message=str(e),
                    )
                ],
            )


def discover_manifests(start_path: Path | None = None) -> list[Path]:
    """Find .sdqctl/directives.yaml manifests.

    Searches:
    1. Workspace-local: {start_path}/.sdqctl/directives.yaml
    2. User-global: ~/.sdqctl/directives.yaml

    Args:
        start_path: Starting directory (default: cwd)

    Returns:
        List of manifest paths found, workspace-local first
    """
    manifests: list[Path] = []
    start = start_path or Path.cwd()

    # Workspace-local
    local = start / ".sdqctl" / "directives.yaml"
    if local.exists():
        manifests.append(local)

    # Also check parent directories up to git root
    current = start
    for _ in range(10):  # Limit depth
        parent = current.parent
        if parent == current:
            break
        local = parent / ".sdqctl" / "directives.yaml"
        if local.exists() and local not in manifests:
            manifests.append(local)
        # Stop at git root
        if (parent / ".git").exists():
            break
        current = parent

    # User-global
    user_global = Path.home() / ".sdqctl" / "directives.yaml"
    if user_global.exists() and user_global not in manifests:
        manifests.append(user_global)

    return manifests


def load_plugin_verifiers(
    start_path: Path | None = None,
) -> dict[str, PluginVerifier]:
    """Load all plugin verifiers from discovered manifests.

    Args:
        start_path: Starting directory for manifest discovery

    Returns:
        Dict mapping verifier names to PluginVerifier instances
    """
    verifiers: dict[str, PluginVerifier] = {}
    start = start_path or Path.cwd()

    for manifest_path in discover_manifests(start):
        try:
            manifest = PluginManifest.from_file(manifest_path)
            workspace_root = manifest_path.parent.parent  # .sdqctl/../

            for handler in manifest.handlers:
                if handler.directive_type == "VERIFY":
                    # Register as a verifier
                    key = handler.name
                    if key not in verifiers:  # First wins (workspace over global)
                        verifiers[key] = PluginVerifier(handler, workspace_root)

        except Exception:
            # Skip invalid manifests silently
            pass

    return verifiers


def register_plugins(verifiers_registry: dict[str, type]) -> dict[str, PluginVerifier]:
    """Register plugin verifiers into the global VERIFIERS registry.

    This function is called during sdqctl initialization to extend
    the built-in verifiers with plugin-defined ones.

    Args:
        verifiers_registry: The VERIFIERS dict from sdqctl.verifiers

    Returns:
        Dict of plugin verifiers that were registered
    """
    plugins = load_plugin_verifiers()

    for name, plugin_verifier in plugins.items():
        if name not in verifiers_registry:
            # Register a factory that returns the plugin verifier
            # We use a closure to capture the specific plugin instance
            def make_factory(pv: PluginVerifier):
                class PluginVerifierWrapper:
                    name = pv.name
                    description = pv.description

                    def __init__(self):
                        self._verifier = pv

                    def verify(self, root: Path, **options: Any) -> VerificationResult:
                        return self._verifier.verify(root, **options)

                return PluginVerifierWrapper

            verifiers_registry[name] = make_factory(plugin_verifier)

    return plugins
