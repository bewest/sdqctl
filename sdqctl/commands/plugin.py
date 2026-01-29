"""
Plugin management commands.

Provides commands for validating, listing, and managing sdqctl plugins.
"""

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

import click

from ..plugins import (
    DirectiveHandler,
    PluginManifest,
    discover_manifests,
    load_plugin_verifiers,
)

# Valid capabilities that plugins can request
VALID_CAPABILITIES = frozenset({
    "read_files",      # Read files in workspace
    "write_files",     # Write to specific paths
    "run_commands",    # Execute shell commands
    "network",         # Make network requests
    "adapter_access",  # Full adapter API access
})

# Default capabilities (implicit if none specified)
DEFAULT_CAPABILITIES = frozenset({"read_files", "run_commands"})


@click.group()
def plugin() -> None:
    """Plugin management commands."""
    pass


@plugin.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_plugins(ctx: click.Context, as_json: bool) -> None:
    """List discovered plugins."""
    manifests = discover_manifests()

    if not manifests:
        if as_json:
            click.echo(json.dumps({"plugins": [], "manifests": []}))
        else:
            click.echo("No plugins discovered.")
        return

    plugins = load_plugin_verifiers()

    if as_json:
        output = {
            "manifests": [str(m) for m in manifests],
            "plugins": [
                {
                    "name": p.name,
                    "type": p.handler.directive_type,
                    "description": p.description,
                    "handler": p.handler.handler,
                    "workspace": str(p.workspace_root),
                }
                for p in plugins.values()
            ],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"Discovered {len(manifests)} manifest(s):")
        for m in manifests:
            click.echo(f"  {m}")
        click.echo()
        click.echo(f"Registered {len(plugins)} plugin(s):")
        for name, p in plugins.items():
            click.echo(f"  {p.handler.directive_type} {name}: {p.description}")


@plugin.command("validate")
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--strict", is_flag=True, help="Fail on warnings")
@click.pass_context
def validate_plugin(ctx: click.Context, path: str | None, strict: bool) -> None:
    """Validate plugin structure and manifest.

    PATH: Path to plugin directory or manifest file (default: .sdqctl/)
    """
    if path:
        plugin_path = Path(path)
        if plugin_path.is_file():
            manifest_path = plugin_path
        else:
            manifest_path = plugin_path / "directives.yaml"
            if not manifest_path.exists():
                manifest_path = plugin_path / ".sdqctl" / "directives.yaml"
    else:
        manifest_path = Path.cwd() / ".sdqctl" / "directives.yaml"

    if not manifest_path.exists():
        click.echo(f"Error: Manifest not found: {manifest_path}", err=True)
        ctx.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    # Parse manifest
    try:
        manifest = PluginManifest.from_file(manifest_path)
    except Exception as e:
        click.echo(f"Error: Failed to parse manifest: {e}", err=True)
        ctx.exit(1)

    click.echo(f"Validating: {manifest_path}")
    click.echo(f"  Version: {manifest.version}")
    click.echo(f"  Handlers: {len(manifest.handlers)}")
    click.echo()

    # Validate each handler
    for handler in manifest.handlers:
        handler_errors, handler_warnings = _validate_handler(
            handler, manifest_path.parent.parent
        )
        errors.extend(handler_errors)
        warnings.extend(handler_warnings)

    # Report results
    if warnings:
        click.echo("Warnings:")
        for w in warnings:
            click.echo(f"  ⚠️  {w}")
        click.echo()

    if errors:
        click.echo("Errors:")
        for e in errors:
            click.echo(f"  ❌ {e}")
        click.echo()
        click.echo(f"Validation failed: {len(errors)} error(s)")
        ctx.exit(1)
    elif warnings and strict:
        click.echo(f"Validation failed (strict): {len(warnings)} warning(s)")
        ctx.exit(1)
    else:
        click.echo("✅ Validation passed")


def _validate_handler(
    handler: DirectiveHandler, workspace_root: Path
) -> tuple[list[str], list[str]]:
    """Validate a single handler configuration.

    Returns:
        Tuple of (errors, warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"[{handler.directive_type} {handler.name}]"

    # Check handler command exists
    if not handler.handler:
        errors.append(f"{prefix} Missing 'handler' field")
    else:
        # Try to resolve the handler command
        parts = handler.handler.split()
        if parts:
            cmd = parts[0]
            if cmd == "python":
                # Check if script exists
                if len(parts) > 1:
                    script_path = workspace_root / parts[1]
                    if not script_path.exists():
                        errors.append(
                            f"{prefix} Handler script not found: {parts[1]}"
                        )
            # Other commands assumed to be system commands

    # Check description
    if not handler.description:
        warnings.append(f"{prefix} Missing 'description' field")

    # Validate timeout
    if handler.timeout <= 0:
        errors.append(f"{prefix} Invalid timeout: {handler.timeout}")
    elif handler.timeout > 300:
        warnings.append(f"{prefix} Long timeout ({handler.timeout}s) may delay workflows")

    # Validate requires (capabilities)
    for cap in handler.requires:
        if cap not in VALID_CAPABILITIES:
            warnings.append(f"{prefix} Unknown capability: {cap}")

    return errors, warnings


@plugin.command("capabilities")
def list_capabilities() -> None:
    """List available plugin capabilities."""
    click.echo("Available capabilities:")
    click.echo()
    caps = {
        "read_files": ("Read files within workspace", True),
        "write_files": ("Write files to specific paths", False),
        "run_commands": ("Execute shell commands", True),
        "network": ("Make network requests", False),
        "adapter_access": ("Access AI adapter APIs directly", False),
    }
    for cap, (desc, is_default) in caps.items():
        default = " (default)" if is_default else ""
        click.echo(f"  {cap}: {desc}{default}")


@plugin.command("run")
@click.argument("directive_type")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--timeout", type=int, default=None, help="Override handler timeout")
@click.option(
    "--workspace", "-w", type=click.Path(exists=True),
    help="Workspace root (default: cwd)"
)
@click.pass_context
def run_directive(
    ctx: click.Context,
    directive_type: str,
    name: str,
    as_json: bool,
    timeout: int | None,
    workspace: str | None,
) -> None:
    """Run a plugin directive handler directly.

    DIRECTIVE_TYPE: The directive type (e.g., VERIFY, HYGIENE)
    NAME: The handler name (e.g., queue-stats, ecosystem-gaps)

    \b
    Examples:
      sdqctl plugin run HYGIENE queue-stats
      sdqctl plugin run VERIFY ecosystem-gaps --json
      sdqctl plugin run HYGIENE check-queues --workspace /path/to/project
    """
    workspace_root = Path(workspace) if workspace else Path.cwd()

    # Find the handler in discovered manifests
    handler = _find_handler(directive_type.upper(), name, workspace_root)

    if handler is None:
        if as_json:
            click.echo(json.dumps({
                "success": False,
                "error": f"Handler not found: {directive_type} {name}",
            }))
        else:
            click.echo(f"Error: Handler not found: {directive_type} {name}", err=True)
            click.echo("Run 'sdqctl plugin list' to see available handlers.", err=True)
        ctx.exit(1)

    # Execute the handler
    result = _execute_handler(handler, workspace_root, timeout)

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if result.get("stdout"):
                click.echo(result["stdout"])
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if result.get("stderr"):
                click.echo(result["stderr"], err=True)
            ctx.exit(result.get("exit_code", 1))


def _find_handler(
    directive_type: str, name: str, workspace_root: Path
) -> DirectiveHandler | None:
    """Find a handler by type and name in discovered manifests."""
    for manifest_path in discover_manifests(workspace_root):
        try:
            manifest = PluginManifest.from_file(manifest_path)
            for handler in manifest.handlers:
                if (
                    handler.directive_type.upper() == directive_type.upper()
                    and handler.name == name
                ):
                    return handler
        except Exception:
            pass
    return None


def _execute_handler(
    handler: DirectiveHandler,
    workspace_root: Path,
    timeout_override: int | None = None,
) -> dict[str, Any]:
    """Execute a handler command and return results.

    Returns:
        Dict with success, stdout, stderr, exit_code, error keys
    """
    cmd = handler.handler

    # Substitute placeholders
    cmd = cmd.replace("{root}", str(workspace_root))
    cmd = cmd.replace("{workspace}", str(workspace_root))

    effective_timeout = timeout_override or handler.timeout

    try:
        result = subprocess.run(
            shlex.split(cmd),
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "handler": handler.name,
            "directive_type": handler.directive_type,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Handler timed out after {effective_timeout}s",
            "handler": handler.name,
            "directive_type": handler.directive_type,
            "exit_code": 124,  # Standard timeout exit code
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"Handler not found: {e}",
            "handler": handler.name,
            "directive_type": handler.directive_type,
            "exit_code": 127,  # Standard command not found exit code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "handler": handler.name,
            "directive_type": handler.directive_type,
            "exit_code": 1,
        }


@plugin.command("handlers")
@click.option("--type", "dtype", help="Filter by directive type")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_handlers(ctx: click.Context, dtype: str | None, as_json: bool) -> None:
    """List all plugin handlers (including non-VERIFY types).

    Unlike 'plugin list' which only shows VERIFY plugins registered as verifiers,
    this command shows ALL handlers from manifests (VERIFY, HYGIENE, TRACE, etc).
    """
    manifests = discover_manifests()

    handlers: list[dict[str, Any]] = []
    for manifest_path in manifests:
        try:
            manifest = PluginManifest.from_file(manifest_path)
            workspace = manifest_path.parent.parent

            for handler in manifest.handlers:
                if dtype and handler.directive_type.upper() != dtype.upper():
                    continue
                handlers.append({
                    "directive_type": handler.directive_type,
                    "name": handler.name,
                    "description": handler.description,
                    "handler": handler.handler,
                    "timeout": handler.timeout,
                    "workspace": str(workspace),
                    "manifest": str(manifest_path),
                })
        except Exception:
            pass

    if as_json:
        click.echo(json.dumps({"handlers": handlers}, indent=2))
    else:
        if not handlers:
            click.echo("No handlers discovered.")
            return

        # Group by directive type
        by_type: dict[str, list[dict]] = {}
        for h in handlers:
            t = h["directive_type"]
            by_type.setdefault(t, []).append(h)

        for dtype_name, type_handlers in sorted(by_type.items()):
            click.echo(f"\n{dtype_name}:")
            for h in type_handlers:
                click.echo(f"  {h['name']}: {h['description']}")
