"""
Plugin management commands.

Provides commands for validating, listing, and managing sdqctl plugins.
"""

import json
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
