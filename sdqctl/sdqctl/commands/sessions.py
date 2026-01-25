"""
sdqctl sessions - Manage conversation sessions.

Usage:
    sdqctl sessions list
    sdqctl sessions list --format json
    sdqctl sessions list --filter "audit-*"
    sdqctl sessions delete SESSION_ID
    sdqctl sessions delete SESSION_ID --force
    sdqctl sessions cleanup --older-than 7d
    sdqctl sessions cleanup --older-than 30d --dry-run
"""

import json
import re
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..adapters import get_adapter
from .utils import run_async

console = Console()

# Consultation prompt injected when resuming a CONSULT session
CONSULTATION_PROMPT = """You are resuming a paused consultation session.

Topic: {topic}

Your task:
1. Review the work done so far in context
2. Identify all open questions that need human input
3. Present each question clearly with choices where applicable
4. Use the ask_user tool to collect answers interactively
5. After all questions are answered, summarize the decisions
6. Signal readiness to continue with: "All questions resolved. Ready to continue."

Be concise. Present one question at a time. Offer reasonable defaults."""


def parse_duration(duration_str: str) -> datetime:
    """Parse duration string like '7d', '24h', '30m' into a cutoff datetime.
    
    Returns the datetime that is `duration` ago from now.
    """
    match = re.match(r"^(\d+)([dhm])$", duration_str.lower())
    if not match:
        raise click.BadParameter(
            f"Invalid duration format: {duration_str}. Use format like '7d', '24h', '30m'"
        )
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == "d":
        delta = timedelta(days=value)
    elif unit == "h":
        delta = timedelta(hours=value)
    elif unit == "m":
        delta = timedelta(minutes=value)
    else:
        raise click.BadParameter(f"Unknown duration unit: {unit}")
    
    return datetime.now(timezone.utc) - delta


def format_age(timestamp_str: str) -> str:
    """Format ISO timestamp as human-readable age like '2h ago', '3d ago'."""
    try:
        # Parse ISO timestamp, handle various formats
        ts = timestamp_str.replace("Z", "+00:00")
        if "+" not in ts and "-" not in ts[10:]:
            ts += "+00:00"
        dt = datetime.fromisoformat(ts)
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"
    except (ValueError, TypeError):
        return "unknown"


@click.group("sessions")
def sessions():
    """Manage conversation sessions.
    
    \b
    Commands:
      list     List all available sessions
      delete   Delete a session permanently
      cleanup  Clean up old sessions
    
    \b
    Examples:
      sdqctl sessions list
      sdqctl sessions list --format json
      sdqctl sessions list --filter "audit-*"
      sdqctl sessions delete my-session-id
      sdqctl sessions cleanup --older-than 7d --dry-run
    """
    pass


@sessions.command("list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), 
              default="table", help="Output format")
@click.option("--filter", "name_filter", help="Filter by session name pattern (glob)")
@click.option("--adapter", "-a", default="copilot", help="Adapter to use (default: copilot)")
def list_sessions(output_format: str, name_filter: Optional[str], adapter: str):
    """List all available sessions.
    
    Shows session ID, last modified time, and remote status.
    Use --filter to filter by session name pattern (e.g., 'audit-*').
    """
    run_async(_list_sessions_async(output_format, name_filter, adapter))


async def _list_sessions_async(output_format: str, name_filter: Optional[str], adapter_name: str):
    """Async implementation of list_sessions."""
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            sessions_list = await ai_adapter.list_sessions()
        finally:
            await ai_adapter.stop()
    except Exception as e:
        if output_format == "json":
            console.print_json(json.dumps({"error": str(e), "sessions": []}))
        else:
            console.print(f"[red]Error listing sessions: {e}[/red]")
        return
    
    # Filter by pattern if provided
    if name_filter:
        sessions_list = [s for s in sessions_list if fnmatch(s.get("id", ""), name_filter)]
    
    # Filter out remote sessions (per design decision)
    sessions_list = [s for s in sessions_list if not s.get("is_remote", False)]
    
    # Sort by modified time (newest first)
    sessions_list.sort(key=lambda s: s.get("modified_time", ""), reverse=True)
    
    if output_format == "json":
        console.print_json(json.dumps({"sessions": sessions_list}))
    else:
        if not sessions_list:
            if name_filter:
                console.print(f"[yellow]No sessions matching '{name_filter}'[/yellow]")
            else:
                console.print("[yellow]No sessions found[/yellow]")
            return
        
        table = Table(title="Sessions")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Modified", style="dim")
        table.add_column("Summary", style="green", max_width=40)
        
        for s in sessions_list[:50]:  # Limit display
            age = format_age(s.get("modified_time", ""))
            summary = s.get("summary") or ""
            if len(summary) > 37:
                summary = summary[:37] + "..."
            table.add_row(s.get("id", "unknown"), age, summary)
        
        console.print(table)
        
        if len(sessions_list) > 50:
            console.print(f"\n[dim]...and {len(sessions_list) - 50} more sessions[/dim]")
        
        # Prompt for old sessions cleanup
        old_sessions = [
            s for s in sessions_list 
            if _is_older_than(s.get("modified_time", ""), days=30)
        ]
        if old_sessions:
            console.print(
                f"\n[dim]Tip: {len(old_sessions)} sessions are older than 30 days. "
                "Use 'sdqctl sessions cleanup --older-than 30d' to remove them.[/dim]"
            )


def _is_older_than(timestamp_str: str, days: int) -> bool:
    """Check if timestamp is older than specified days."""
    try:
        ts = timestamp_str.replace("Z", "+00:00")
        if "+" not in ts and "-" not in ts[10:]:
            ts += "+00:00"
        dt = datetime.fromisoformat(ts)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return dt < cutoff
    except (ValueError, TypeError):
        return False


@sessions.command("delete")
@click.argument("session_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--adapter", "-a", default="copilot", help="Adapter to use (default: copilot)")
def delete_session(session_id: str, force: bool, adapter: str):
    """Delete a session permanently.
    
    The session cannot be resumed after deletion.
    """
    if not force:
        if not click.confirm(f"Delete session '{session_id}'?"):
            console.print("[yellow]Aborted[/yellow]")
            return
    
    run_async(_delete_session_async(session_id, adapter))


async def _delete_session_async(session_id: str, adapter_name: str):
    """Async implementation of delete_session."""
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            await ai_adapter.delete_session(session_id)
            console.print(f"[green]Deleted session: {session_id}[/green]")
        finally:
            await ai_adapter.stop()
    except Exception as e:
        console.print(f"[red]Error deleting session: {e}[/red]")


@sessions.command("cleanup")
@click.option("--older-than", "older_than", required=True, 
              help="Delete sessions older than (e.g., 7d, 24h)")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
@click.option("--adapter", "-a", default="copilot", help="Adapter to use (default: copilot)")
def cleanup_sessions(older_than: str, dry_run: bool, adapter: str):
    """Clean up old sessions.
    
    Deletes sessions that haven't been modified in the specified duration.
    
    \b
    Duration format:
      7d  - 7 days
      24h - 24 hours
      30m - 30 minutes
    
    \b
    Examples:
      sdqctl sessions cleanup --older-than 7d --dry-run
      sdqctl sessions cleanup --older-than 30d
    """
    try:
        cutoff = parse_duration(older_than)
    except click.BadParameter as e:
        console.print(f"[red]{e.message}[/red]")
        return
    
    run_async(_cleanup_sessions_async(cutoff, dry_run, adapter))


async def _cleanup_sessions_async(cutoff: datetime, dry_run: bool, adapter_name: str):
    """Async implementation of cleanup_sessions."""
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        try:
            sessions_list = await ai_adapter.list_sessions()
            
            # Filter out remote sessions and find old ones
            old_sessions = []
            for s in sessions_list:
                if s.get("is_remote", False):
                    continue
                try:
                    ts = s.get("modified_time", "").replace("Z", "+00:00")
                    if "+" not in ts and "-" not in ts[10:]:
                        ts += "+00:00"
                    dt = datetime.fromisoformat(ts)
                    if dt < cutoff:
                        old_sessions.append(s)
                except (ValueError, TypeError):
                    continue
            
            if not old_sessions:
                console.print("[green]No sessions to clean up[/green]")
                return
            
            if dry_run:
                console.print(f"[yellow]Would delete {len(old_sessions)} sessions:[/yellow]")
                for s in old_sessions:
                    age = format_age(s.get("modified_time", ""))
                    console.print(f"  {s.get('id', 'unknown'):40} {age}")
            else:
                deleted = 0
                for s in old_sessions:
                    try:
                        await ai_adapter.delete_session(s["id"])
                        console.print(f"  Deleted: {s['id']}")
                        deleted += 1
                    except Exception as e:
                        console.print(f"  [red]Failed to delete {s['id']}: {e}[/red]")
                
                console.print(f"\n[green]Deleted {deleted} sessions[/green]")
        finally:
            await ai_adapter.stop()
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")


@sessions.command("resume")
@click.argument("session_id")
@click.option("--prompt", "-p", help="Send an immediate prompt after resuming")
@click.option("--adapter", "-a", default="copilot", help="Adapter to use (default: copilot)")
@click.option("--model", "-m", help="Model to use for resumed session")
@click.option("--streaming/--no-streaming", default=True, help="Enable/disable streaming output")
def resume_session_cmd(
    session_id: str,
    prompt: Optional[str],
    adapter: str,
    model: Optional[str],
    streaming: bool,
):
    """Resume a previous conversation session.
    
    Restores conversation history and continues from where you left off.
    Use --prompt to send an immediate message.
    
    \b
    Examples:
      sdqctl sessions resume security-audit-2026-01
      sdqctl sessions resume my-session --prompt "Continue with auth module"
    """
    run_async(_resume_session_async(
        session_id=session_id,
        prompt=prompt,
        adapter_name=adapter,
        model=model,
        streaming=streaming,
    ))


async def _resume_session_async(
    session_id: str,
    prompt: Optional[str],
    adapter_name: str,
    model: Optional[str],
    streaming: bool,
):
    """Async implementation of resume session command."""
    from ..adapters.base import AdapterConfig
    from rich.markdown import Markdown
    from rich.panel import Panel
    
    try:
        ai_adapter = get_adapter(adapter_name)
        await ai_adapter.start()
        
        try:
            # Build config for resumed session
            config = AdapterConfig(
                model=model or "gpt-4",
                streaming=streaming,
            )
            
            # Check for local checkpoint with CONSULT status
            consult_topic = None
            session_dir = Path.home() / ".sdqctl" / "sessions" / session_id
            checkpoint_file = session_dir / "pause.json"
            if checkpoint_file.exists():
                try:
                    checkpoint_data = json.loads(checkpoint_file.read_text())
                    if checkpoint_data.get("status") == "consulting":
                        # Extract topic from message (format: "CONSULT: {topic}")
                        message = checkpoint_data.get("message", "")
                        if message.startswith("CONSULT: "):
                            consult_topic = message[9:]  # Strip "CONSULT: " prefix
                        else:
                            consult_topic = "Open Questions"
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Resume the session
            console.print(f"[dim]Resuming session: {session_id}[/dim]")
            session = await ai_adapter.resume_session(session_id, config)
            console.print(f"[green]✓[/green] Session resumed")
            
            # If this was a CONSULT session, inject consultation prompt
            if consult_topic and not prompt:
                console.print(f"\n[yellow]📋 Consultation: {consult_topic}[/yellow]")
                console.print("[dim]Agent will present open questions...[/dim]\n")
                prompt = CONSULTATION_PROMPT.format(topic=consult_topic)
            
            # Send prompt if provided
            if prompt:
                # Don't show full consultation prompt (it's verbose)
                display_prompt = prompt if not consult_topic else f"[Consultation: {consult_topic}]"
                console.print(Panel(display_prompt, title="Prompt", border_style="blue"))
                
                response = await ai_adapter.send(session, prompt)
                
                # Display response
                if response:
                    md = Markdown(response)
                    console.print(Panel(md, title="Response", border_style="green"))
            else:
                console.print(
                    "\n[dim]Session resumed. Use --prompt to send a message.[/dim]"
                )
        finally:
            await ai_adapter.stop()
            
    except Exception as e:
        console.print(f"[red]Error resuming session: {e}[/red]")
