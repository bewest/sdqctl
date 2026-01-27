"""
sdqctl status - Show session and checkpoint status.

Usage:
    sdqctl status
    sdqctl status --sessions
    sdqctl status --checkpoints
    sdqctl status --models
    sdqctl status --auth
    sdqctl status --all
"""

import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..adapters import get_adapter, list_adapters
from .utils import run_async

console = Console()

SDQCTL_DIR = Path.home() / ".sdqctl"


@click.command("status")
@click.option("--sessions", is_flag=True, help="Show session details")
@click.option("--checkpoints", is_flag=True, help="Show checkpoint details")
@click.option("--adapters", is_flag=True, help="Show available adapters")
@click.option("--models", is_flag=True, help="Show available models")
@click.option("--auth", is_flag=True, help="Show authentication status")
@click.option(
    "--all", "show_all", is_flag=True,
    help="Show all details (adapters, models, auth, sessions)"
)
@click.option(
    "--adapter", "-a", default="copilot",
    help="Adapter to query for --models/--auth (default: copilot)"
)
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def status(
    sessions: bool,
    checkpoints: bool,
    adapters: bool,
    models: bool,
    auth: bool,
    show_all: bool,
    adapter: str,
    json_output: bool,
) -> None:
    """Show session and system status."""

    if adapters and not show_all:
        _show_adapters(json_output)
        return

    if (sessions or checkpoints) and not show_all:
        _show_sessions(json_output, show_checkpoints=checkpoints)
        return

    if models and not show_all:
        run_async(_show_models_async(adapter, json_output))
        return

    if auth and not show_all:
        run_async(_show_auth_async(adapter, json_output))
        return

    if show_all:
        run_async(_show_all_async(adapter, json_output))
        return

    # Default: show overview with enhanced info
    run_async(_show_overview_async(adapter, json_output))


async def _show_overview_async(adapter_name: str, json_output: bool) -> None:
    """Show enhanced system overview with CLI status."""
    sessions_dir = SDQCTL_DIR / "sessions"
    session_count = 0
    checkpoint_count = 0

    if sessions_dir.exists():
        session_dirs = list(sessions_dir.iterdir())
        session_count = len(session_dirs)
        for session_dir in session_dirs:
            checkpoint_count += len(list(session_dir.glob("checkpoint-*.json")))

    available_adapters = list_adapters()

    # Try to get CLI and auth status from adapter
    cli_status = {}
    auth_status = {}
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            cli_status = await ai_adapter.get_cli_status()
            auth_status = await ai_adapter.get_auth_status()
        finally:
            await ai_adapter.stop()
    except Exception:
        pass  # Ignore errors - adapter may not be available

    if json_output:
        data = {
            "version": __version__,
            "sdqctl_dir": str(SDQCTL_DIR),
            "sessions": session_count,
            "checkpoints": checkpoint_count,
            "adapters": available_adapters,
        }
        if cli_status:
            data["cli_status"] = cli_status
        if auth_status:
            data["auth_status"] = auth_status
        console.print_json(json.dumps(data))
    else:
        console.print(f"\n[bold]sdqctl v{__version__}[/bold]")
        console.print("─" * 35)

        # CLI status
        if cli_status:
            version = cli_status.get("version", "unknown")
            protocol = cli_status.get("protocol_version", "?")
            console.print(f"  Copilot CLI:  v{version} (protocol v{protocol})")

        # Auth status
        if auth_status:
            if auth_status.get("authenticated"):
                login = auth_status.get("login", "unknown")
                auth_type = auth_status.get("auth_type", "?")
                console.print(f"  Auth:         [green]✓[/green] {login} ({auth_type})")
            else:
                console.print("  Auth:         [red]✗[/red] Not authenticated")

        console.print(f"  Config:       {SDQCTL_DIR}")
        console.print(f"  Sessions:     {session_count}")
        console.print(f"  Checkpoints:  {checkpoint_count}")
        console.print(f"  Adapters:     {', '.join(available_adapters) or 'none'}")
        console.print()


async def _show_models_async(adapter_name: str, json_output: bool) -> None:
    """Show available models from adapter."""
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            models = await ai_adapter.list_models()
        finally:
            await ai_adapter.stop()
    except Exception as e:
        if json_output:
            console.print_json(json.dumps({"error": str(e), "models": []}))
        else:
            console.print(f"[red]Error getting models: {e}[/red]")
        return

    if json_output:
        console.print_json(json.dumps({"models": models}))
    else:
        if not models:
            console.print("[yellow]No models available[/yellow]")
            return

        table = Table(title="Available Models")
        table.add_column("Model ID", style="cyan")
        table.add_column("Context", style="green")
        table.add_column("Vision", style="green")

        for m in models:
            context = f"{m.get('context_window', 0)//1000}K" if m.get('context_window') else "?"
            vision = "[green]✓[/green]" if m.get("vision") else "[dim]✗[/dim]"
            table.add_row(m.get("id", "unknown"), context, vision)

        console.print(table)


async def _show_auth_async(adapter_name: str, json_output: bool) -> None:
    """Show authentication status from adapter."""
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            auth_status = await ai_adapter.get_auth_status()
            cli_status = await ai_adapter.get_cli_status()
        finally:
            await ai_adapter.stop()
    except Exception as e:
        if json_output:
            console.print_json(json.dumps({"error": str(e), "auth_status": {}}))
        else:
            console.print(f"[red]Error getting auth status: {e}[/red]")
        return

    if json_output:
        data = {"auth_status": auth_status}
        if cli_status:
            data["cli_status"] = cli_status
        console.print_json(json.dumps(data))
    else:
        console.print("\n[bold]Authentication Status[/bold]")
        console.print("─" * 35)

        if cli_status:
            version = cli_status.get("version", "unknown")
            protocol = cli_status.get("protocol_version", "?")
            console.print(f"  CLI Version:  v{version}")
            console.print(f"  Protocol:     v{protocol}")

        if auth_status:
            if auth_status.get("authenticated"):
                console.print("  Status:       [green]✓ Authenticated[/green]")
                console.print(f"  Login:        {auth_status.get('login', 'unknown')}")
                console.print(f"  Auth Type:    {auth_status.get('auth_type', 'unknown')}")
                if auth_status.get("host"):
                    console.print(f"  Host:         {auth_status.get('host')}")
            else:
                console.print("  Status:       [red]✗ Not authenticated[/red]")
                if auth_status.get("message"):
                    console.print(f"  Message:      {auth_status.get('message')}")
        else:
            console.print("  [yellow]Auth status unavailable[/yellow]")
        console.print()


async def _show_all_async(adapter_name: str, json_output: bool) -> None:
    """Show all status information."""
    sessions_dir = SDQCTL_DIR / "sessions"
    session_count = 0
    checkpoint_count = 0

    if sessions_dir.exists():
        session_dirs = list(sessions_dir.iterdir())
        session_count = len(session_dirs)
        for session_dir in session_dirs:
            checkpoint_count += len(list(session_dir.glob("checkpoint-*.json")))

    available_adapters = list_adapters()

    # Get adapter info
    cli_status = {}
    auth_status = {}
    models = []
    adapter_info = []

    for name in available_adapters:
        try:
            ai_adapter = get_adapter(name)
            info = ai_adapter.get_info()
            adapter_info.append(info)

            if name == adapter_name:
                await ai_adapter.start()
                try:
                    cli_status = await ai_adapter.get_cli_status()
                    auth_status = await ai_adapter.get_auth_status()
                    models = await ai_adapter.list_models()
                finally:
                    await ai_adapter.stop()
        except Exception as e:
            adapter_info.append({"name": name, "error": str(e)})

    if json_output:
        data = {
            "version": __version__,
            "sdqctl_dir": str(SDQCTL_DIR),
            "sessions": session_count,
            "checkpoints": checkpoint_count,
            "adapters": adapter_info,
            "cli_status": cli_status,
            "auth_status": auth_status,
            "models": models,
        }
        console.print_json(json.dumps(data))
    else:
        # Header
        console.print(f"\n[bold]sdqctl v{__version__}[/bold]")
        console.print("─" * 35)

        # CLI status
        if cli_status:
            version = cli_status.get("version", "unknown")
            protocol = cli_status.get("protocol_version", "?")
            console.print(f"Copilot CLI:    v{version} (protocol v{protocol})")

        # Auth status
        if auth_status:
            if auth_status.get("authenticated"):
                login = auth_status.get("login", "unknown")
                auth_type = auth_status.get("auth_type", "?")
                console.print(
                    f"Auth:           [green]✓[/green] Authenticated as {login} ({auth_type})"
                )
                if auth_status.get("host"):
                    console.print(f"Host:           {auth_status.get('host')}")
            else:
                console.print("Auth:           [red]✗[/red] Not authenticated")

        console.print(f"Sessions:       {session_count}")
        console.print(f"Checkpoints:    {checkpoint_count}")
        console.print()

        # Adapters
        console.print("[bold]Adapters:[/bold]")
        for info in adapter_info:
            if "error" in info:
                console.print(f"  {info['name']:14} [red]✗ Error: {info['error']}[/red]")
            else:
                name = info.get("name", "unknown")
                default = " (default)" if name == "copilot" else ""
                console.print(f"  {name:14} [green]✓[/green] Available{default}")
        console.print()

        # Models
        if models:
            console.print("[bold]Models:[/bold]")
            for m in models[:10]:  # Limit display
                context = f"{m.get('context_window', 0)//1000}K" if m.get('context_window') else "?"
                vision = "✓" if m.get("vision") else "✗"
                console.print(f"  {m.get('id', 'unknown'):20} {context:8} vision: {vision}")
            if len(models) > 10:
                console.print(f"  ... and {len(models) - 10} more")
            console.print()


def _show_adapters(json_output: bool) -> None:
    """Show available adapters."""
    available = list_adapters()

    adapter_info = []
    for name in available:
        try:
            from ..adapters import get_adapter
            adapter = get_adapter(name)
            info = adapter.get_info()
            adapter_info.append(info)
        except Exception as e:
            adapter_info.append({
                "name": name,
                "error": str(e),
            })

    if json_output:
        console.print_json(json.dumps({"adapters": adapter_info}))
    else:
        table = Table(title="Available Adapters")
        table.add_column("Name", style="cyan")
        table.add_column("Tools", style="green")
        table.add_column("Streaming", style="green")
        table.add_column("Status", style="yellow")

        for info in adapter_info:
            if "error" in info:
                table.add_row(
                    info["name"],
                    "-",
                    "-",
                    f"[red]Error: {info['error']}[/red]"
                )
            else:
                table.add_row(
                    info["name"],
                    "✓" if info.get("supports_tools") else "✗",
                    "✓" if info.get("supports_streaming") else "✗",
                    "[green]Available[/green]"
                )

        console.print(table)


def _show_sessions(json_output: bool, show_checkpoints: bool = False) -> None:
    """Show session details."""
    sessions_dir = SDQCTL_DIR / "sessions"

    if not sessions_dir.exists():
        if json_output:
            console.print_json(json.dumps({"sessions": []}))
        else:
            console.print("[yellow]No sessions found[/yellow]")
        return

    session_data = []

    for session_dir in sorted(sessions_dir.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue

        session_id = session_dir.name
        checkpoints = list(session_dir.glob("checkpoint-*.json"))

        session_info = {
            "id": session_id,
            "checkpoints": len(checkpoints),
            "modified": datetime.fromtimestamp(session_dir.stat().st_mtime).isoformat(),
        }

        if show_checkpoints and checkpoints:
            session_info["checkpoint_details"] = []
            for cp_file in sorted(checkpoints):
                try:
                    cp_data = json.loads(cp_file.read_text())
                    session_info["checkpoint_details"].append({
                        "id": cp_data.get("id"),
                        "name": cp_data.get("name"),
                        "timestamp": cp_data.get("timestamp"),
                        "cycle": cp_data.get("cycle_number"),
                    })
                except Exception:
                    pass

        session_data.append(session_info)

    if json_output:
        console.print_json(json.dumps({"sessions": session_data}))
    else:
        table = Table(title="Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Checkpoints", style="green")
        table.add_column("Last Modified", style="dim")

        for session in session_data[:20]:  # Limit display
            table.add_row(
                session["id"],
                str(session["checkpoints"]),
                session["modified"][:19],
            )

        console.print(table)

        if show_checkpoints:
            for session in session_data[:5]:
                if "checkpoint_details" in session and session["checkpoint_details"]:
                    console.print(f"\n[bold]Session {session['id']} checkpoints:[/bold]")
                    for cp in session["checkpoint_details"]:
                        ts = cp['timestamp'][:19]
                        console.print(f"  - {cp['name']} (cycle {cp['cycle']}) at {ts}")

        if len(session_data) > 20:
            console.print(f"\n[dim]...and {len(session_data) - 20} more sessions[/dim]")
