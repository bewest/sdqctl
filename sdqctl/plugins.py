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
from typing import Any, Callable

import yaml

from .core.conversation.types import register_custom_directive
from .verifiers.base import VerificationError, VerificationResult


@dataclass
class DirectiveExecutionContext:
    """Context passed to custom directive handlers during execution.
    
    Provides handlers with access to workspace info, session state,
    and output channels.
    """
    
    workspace_root: Path
    directive_name: str
    directive_value: str
    line_number: int
    
    # Optional session context
    session_id: str | None = None
    cycle_number: int = 1
    
    # Output configuration
    inject_output: bool = True  # Whether to inject output into prompt
    
    def __post_init__(self):
        self._output_buffer: list[str] = []
        self._errors: list[str] = []
    
    def emit(self, text: str) -> None:
        """Emit text to be injected into the conversation."""
        self._output_buffer.append(text)
    
    def error(self, message: str) -> None:
        """Record an error message."""
        self._errors.append(message)
    
    @property
    def output(self) -> str:
        """Get all emitted output."""
        return "\n".join(self._output_buffer)
    
    @property
    def errors(self) -> list[str]:
        """Get all recorded errors."""
        return self._errors.copy()
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self._errors) > 0


@dataclass
class DirectiveExecutionResult:
    """Result of executing a custom directive."""
    
    success: bool
    output: str = ""
    errors: list[str] = field(default_factory=list)
    inject_into_prompt: bool = True
    
    @classmethod
    def ok(cls, output: str = "", inject: bool = True) -> "DirectiveExecutionResult":
        """Create a successful result."""
        return cls(success=True, output=output, inject_into_prompt=inject)
    
    @classmethod
    def fail(cls, errors: list[str], output: str = "") -> "DirectiveExecutionResult":
        """Create a failed result."""
        return cls(success=False, output=output, errors=errors)


# Type alias for directive hook functions
DirectiveHookFn = Callable[[DirectiveExecutionContext], DirectiveExecutionResult]

# Registry for custom directive execution hooks
_DIRECTIVE_HOOKS: dict[str, DirectiveHookFn] = {}


def register_directive_hook(directive_type: str, hook: DirectiveHookFn) -> None:
    """Register an execution hook for a custom directive type.
    
    Args:
        directive_type: The directive type (e.g., "HYGIENE", "TRACE")
        hook: Function to execute when directive is encountered
    """
    _DIRECTIVE_HOOKS[directive_type.upper()] = hook


def unregister_directive_hook(directive_type: str) -> None:
    """Unregister a directive execution hook."""
    _DIRECTIVE_HOOKS.pop(directive_type.upper(), None)


def get_directive_hook(directive_type: str) -> DirectiveHookFn | None:
    """Get the execution hook for a directive type."""
    return _DIRECTIVE_HOOKS.get(directive_type.upper())


def has_directive_hook(directive_type: str) -> bool:
    """Check if a directive type has a registered hook."""
    return directive_type.upper() in _DIRECTIVE_HOOKS


def clear_directive_hooks() -> None:
    """Clear all directive hooks (for testing)."""
    _DIRECTIVE_HOOKS.clear()


def execute_custom_directive(
    directive_type: str,
    directive_value: str,
    workspace_root: Path,
    line_number: int = 0,
    session_id: str | None = None,
    cycle_number: int = 1,
) -> DirectiveExecutionResult:
    """Execute a custom directive using its registered hook.
    
    Args:
        directive_type: The directive type (e.g., "HYGIENE")
        directive_value: The directive value/arguments
        workspace_root: Path to workspace root
        line_number: Line number in source file
        session_id: Optional session identifier
        cycle_number: Current iteration cycle
        
    Returns:
        DirectiveExecutionResult with success status and output
    """
    hook = get_directive_hook(directive_type)
    if hook is None:
        return DirectiveExecutionResult.fail(
            [f"No execution hook registered for directive type: {directive_type}"]
        )
    
    ctx = DirectiveExecutionContext(
        workspace_root=workspace_root,
        directive_name=directive_type,
        directive_value=directive_value,
        line_number=line_number,
        session_id=session_id,
        cycle_number=cycle_number,
    )
    
    try:
        return hook(ctx)
    except Exception as e:
        return DirectiveExecutionResult.fail([f"Hook execution error: {e}"])


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
    inject: bool = True  # Whether to inject output into prompt (for ELIDE support)
    
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
                    inject=config.get("inject", True),  # Default: inject output
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
                # Register the directive type in the custom registry
                register_custom_directive(handler.directive_type, {
                    "name": handler.name,
                    "handler": handler.handler,
                    "description": handler.description,
                    "source": str(manifest_path),
                })
                
                if handler.directive_type == "VERIFY":
                    # Register as a verifier
                    key = handler.name
                    if key not in verifiers:  # First wins (workspace over global)
                        verifiers[key] = PluginVerifier(handler, workspace_root)

        except Exception:
            # Skip invalid manifests silently
            pass

    return verifiers


def _create_shell_hook(handler: DirectiveHandler, workspace_root: Path) -> DirectiveHookFn:
    """Create an execution hook for a shell-based plugin handler.
    
    Args:
        handler: The directive handler configuration
        workspace_root: Root path for command execution
        
    Returns:
        A DirectiveHookFn that executes the handler command
    """
    def hook(ctx: DirectiveExecutionContext) -> DirectiveExecutionResult:
        cmd = handler.handler
        
        # Substitute placeholders
        cmd = cmd.replace("{root}", str(ctx.workspace_root))
        cmd = cmd.replace("{workspace}", str(workspace_root))
        cmd = cmd.replace("{value}", ctx.directive_value)
        cmd = cmd.replace("{directive}", ctx.directive_name)
        
        try:
            result = subprocess.run(
                shlex.split(cmd),
                cwd=workspace_root,
                capture_output=True,
                text=True,
                timeout=handler.timeout,
            )
            
            output = result.stdout
            if result.returncode == 0:
                return DirectiveExecutionResult.ok(output=output)
            else:
                error_msg = result.stderr or result.stdout or f"Exit code {result.returncode}"
                return DirectiveExecutionResult.fail(
                    errors=[error_msg],
                    output=output,
                )
                
        except subprocess.TimeoutExpired:
            return DirectiveExecutionResult.fail(
                [f"Handler timed out after {handler.timeout} seconds"]
            )
        except FileNotFoundError as e:
            return DirectiveExecutionResult.fail(
                [f"Handler not found: {e}"]
            )
        except Exception as e:
            return DirectiveExecutionResult.fail([str(e)])
    
    return hook


def load_plugin_hooks(start_path: Path | None = None) -> dict[str, DirectiveHookFn]:
    """Load all plugin directive hooks from discovered manifests.
    
    Registers hooks for ALL directive types (not just VERIFY).
    
    Args:
        start_path: Starting directory for manifest discovery
        
    Returns:
        Dict mapping directive types to their execution hooks
    """
    hooks: dict[str, DirectiveHookFn] = {}
    start = start_path or Path.cwd()
    
    for manifest_path in discover_manifests(start):
        try:
            manifest = PluginManifest.from_file(manifest_path)
            workspace_root = manifest_path.parent.parent
            
            for handler in manifest.handlers:
                dtype = handler.directive_type.upper()
                
                # Register the directive type
                register_custom_directive(dtype, {
                    "name": handler.name,
                    "handler": handler.handler,
                    "description": handler.description,
                    "source": str(manifest_path),
                })
                
                # Create and register execution hook
                if dtype not in hooks:  # First wins
                    hook = _create_shell_hook(handler, workspace_root)
                    hooks[dtype] = hook
                    register_directive_hook(dtype, hook)
                    
        except Exception:
            pass
    
    return hooks


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
