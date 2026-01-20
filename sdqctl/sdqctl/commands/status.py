"""
sdqctl status - Show session and checkpoint status.

Usage:
    sdqctl status
    sdqctl status --sessions
    sdqctl status --checkpoints
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..adapters import list_adapters

console = Console()

SDQCTL_DIR = Path.home() / ".sdqctl"


@click.command("status")
@click.option("--sessions", is_flag=True, help="Show session details")
@click.option("--checkpoints", is_flag=True, help="Show checkpoint details")
@click.option("--adapters", is_flag=True, help="Show available adapters")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def status(
    sessions: bool,
    checkpoints: bool,
    adapters: bool,
    json_output: bool,
) -> None:
    """Show session and system status."""

    if adapters:
        _show_adapters(json_output)
        return

    if sessions or checkpoints:
        _show_sessions(json_output, show_checkpoints=checkpoints)
        return

    # Default: show overview
    _show_overview(json_output)


def _show_overview(json_output: bool) -> None:
    """Show system overview."""
    sessions_dir = SDQCTL_DIR / "sessions"
    session_count = 0
    checkpoint_count = 0

    if sessions_dir.exists():
        session_dirs = list(sessions_dir.iterdir())
        session_count = len(session_dirs)
        for session_dir in session_dirs:
            checkpoint_count += len(list(session_dir.glob("checkpoint-*.json")))

    available_adapters = list_adapters()

    if json_output:
        console.print_json(json.dumps({
            "sdqctl_dir": str(SDQCTL_DIR),
            "sessions": session_count,
            "checkpoints": checkpoint_count,
            "adapters": available_adapters,
        }))
    else:
        console.print("\n[bold]sdqctl Status[/bold]\n")
        console.print(f"  Config directory: {SDQCTL_DIR}")
        console.print(f"  Sessions: {session_count}")
        console.print(f"  Checkpoints: {checkpoint_count}")
        console.print(f"  Available adapters: {', '.join(available_adapters) or 'none'}")
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
                        console.print(f"  - {cp['name']} (cycle {cp['cycle']}) at {cp['timestamp'][:19]}")

        if len(session_data) > 20:
            console.print(f"\n[dim]...and {len(session_data) - 20} more sessions[/dim]")
