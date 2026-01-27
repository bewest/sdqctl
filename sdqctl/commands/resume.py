"""
resume command - Resume a paused workflow from checkpoint.

Continues execution from where PAUSE stopped.
"""

import asyncio
import json as json_module
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.logging import get_logger, setup_logging
from ..core.session import Session

if TYPE_CHECKING:
    pass


@click.command()
@click.argument("checkpoint", type=click.Path(exists=True), required=False)
@click.option("--list", "list_checkpoints", is_flag=True, help="List available checkpoints")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--dry-run", is_flag=True, help="Show what would happen without executing")
@click.option("--json", "json_output", is_flag=True, help="JSON output format")
@click.option(
    "--verbose", "-v", is_flag=True,
    help="Verbose output (deprecated, use -v on main command)",
)
def resume(
    checkpoint: str,
    list_checkpoints: bool,
    adapter: str,
    dry_run: bool,
    json_output: bool,
    verbose: bool,
) -> None:
    """Resume a paused workflow from checkpoint.

    Continues execution from where PAUSE stopped.

    Examples:
        sdqctl resume ~/.sdqctl/sessions/abc123/pause.json
        sdqctl resume --list
        sdqctl resume --dry-run checkpoint.json
    """
    console = Console()
    resume_logger = get_logger(__name__)

    # Boost verbosity if --verbose flag used on this command
    if verbose and not resume_logger.isEnabledFor(logging.INFO):
        setup_logging(1)

    # Handle --list flag
    if list_checkpoints:
        _list_checkpoints(console, json_output)
        return

    # Require checkpoint if not listing
    if not checkpoint:
        console.print("[red]Error: checkpoint path required (or use --list)[/red]")
        sys.exit(1)

    # Handle --dry-run flag
    if dry_run:
        _dry_run_resume(checkpoint, console, json_output)
        return

    asyncio.run(_resume_async(checkpoint, adapter, console, json_output))


def _list_checkpoints(console: Console, json_output: bool) -> None:
    """List all available pause checkpoints."""
    sessions_dir = Path(".sdqctl/sessions")
    if not sessions_dir.exists():
        if json_output:
            console.print_json('{"checkpoints": []}')
        else:
            console.print("[yellow]No sessions directory found[/yellow]")
        return

    checkpoints = list(sessions_dir.glob("*/pause.json"))
    if not checkpoints:
        if json_output:
            console.print_json('{"checkpoints": []}')
        else:
            console.print("[yellow]No checkpoints found[/yellow]")
        return

    if json_output:
        result = []
        for cp in sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json_module.loads(cp.read_text())
                result.append({
                    "path": str(cp),
                    "message": data.get("message", ""),
                    "timestamp": data.get("timestamp", ""),
                    "session_id": data.get("session_id", ""),
                })
            except Exception:
                result.append({"path": str(cp), "error": "corrupt"})
        console.print_json(json_module.dumps({"checkpoints": result}))
    else:
        console.print("[bold]Available checkpoints:[/bold]\n")
        for cp in sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json_module.loads(cp.read_text())
                msg = data.get("message", "")[:60]
                ts = data.get("timestamp", "")[:19]
                console.print(f"  {cp}")
                console.print(f"    [dim]{ts} - {msg}[/dim]\n")
            except Exception:
                console.print(f"  {cp} [red](corrupt)[/red]")


def _dry_run_resume(checkpoint: str, console: Console, json_output: bool) -> None:
    """Show what would happen on resume without executing."""
    checkpoint_path = Path(checkpoint)
    try:
        session = Session.load_from_pause(checkpoint_path)
    except ValueError as e:
        if json_output:
            console.print_json(json_module.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error loading checkpoint: {e}[/red]")
        return

    conv = session.conversation

    if json_output:
        result = {
            "dry_run": True,
            "session_id": session.id,
            "workflow": str(conv.source_path) if conv.source_path else None,
            "adapter": conv.adapter,
            "model": conv.model,
            "resume_from_prompt": session.state.prompt_index + 1,
            "total_prompts": len(conv.prompts),
            "cycle_number": session.state.cycle_number + 1,
            "messages_in_context": len(session.state.messages),
            "prompts_remaining": conv.prompts[session.state.prompt_index:],
        }
        console.print_json(json_module.dumps(result))
    else:
        console.print(Panel.fit(
            f"Session ID: {session.id}\n"
            f"Workflow: {conv.source_path}\n"
            f"Adapter: {conv.adapter}\n"
            f"Model: {conv.model}\n"
            f"Resume from prompt: {session.state.prompt_index + 1}/{len(conv.prompts)}\n"
            f"Cycle: {session.state.cycle_number + 1}\n"
            f"Messages in context: {len(session.state.messages)}",
            title="[yellow]Dry Run - Resume Configuration[/yellow]"
        ))

        console.print("\n[bold]Prompts remaining:[/bold]")
        remaining_prompts = conv.prompts[session.state.prompt_index:]
        for i, prompt in enumerate(remaining_prompts, session.state.prompt_index + 1):
            preview = prompt[:80] + "..." if len(prompt) > 80 else prompt
            console.print(f"  {i}. {preview}")

        console.print("\n[yellow]Dry run - no execution[/yellow]")


async def _resume_async(
    checkpoint: str, adapter_name: str, console: Console, json_output: bool = False
) -> None:
    """Async implementation of resume command."""
    resume_logger = get_logger(__name__)
    checkpoint_path = Path(checkpoint)

    try:
        session = Session.load_from_pause(checkpoint_path)
        conv = session.conversation

        if not json_output:
            console.print(Panel.fit(
                f"Session ID: {session.id}\n"
                f"Workflow: {conv.source_path}\n"
                f"Resuming from prompt: {session.state.prompt_index + 1}/{len(conv.prompts)}\n"
                f"Messages in history: {len(session.state.messages)}",
                title="[blue]Resuming Paused Workflow[/blue]"
            ))

        # Apply adapter override
        if adapter_name:
            conv.adapter = adapter_name

        # Get adapter
        try:
            ai_adapter = get_adapter(conv.adapter)
        except ValueError as e:
            if not json_output:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Using mock adapter instead[/yellow]")
            ai_adapter = get_adapter("mock")

        await ai_adapter.start()

        adapter_session = await ai_adapter.create_session(
            AdapterConfig(model=conv.model, streaming=True)
        )

        session.state.status = "running"
        responses = []

        # Build pause point lookup
        pause_after = {idx: msg for idx, msg in conv.pause_points}

        # Resume from saved prompt index
        start_idx = session.state.prompt_index

        for i in range(start_idx, len(conv.prompts)):
            prompt = conv.prompts[i]

            resume_logger.info(f"Sending prompt {i + 1}/{len(conv.prompts)}...")

            response = await ai_adapter.send(adapter_session, prompt)
            responses.append(response)

            resume_logger.debug(f"{response[:200]}..." if len(response) > 200 else response)

            session.add_message("user", prompt)
            session.add_message("assistant", response)

            # Check for another PAUSE
            if i in pause_after:
                pause_msg = pause_after[i]
                session.state.prompt_index = i + 1
                new_checkpoint = session.save_pause_checkpoint(pause_msg)

                await ai_adapter.destroy_session(adapter_session)
                await ai_adapter.stop()

                if json_output:
                    result = {
                        "status": "paused",
                        "message": pause_msg,
                        "checkpoint": str(new_checkpoint),
                        "prompts_completed": i - start_idx + 1,
                        "responses": responses,
                    }
                    console.print_json(json_module.dumps(result))
                else:
                    console.print(f"\n[yellow]⏸  PAUSED: {pause_msg}[/yellow]")
                    console.print(f"[dim]Checkpoint saved: {new_checkpoint}[/dim]")
                    console.print(f"\n[bold]To resume:[/bold] sdqctl resume {new_checkpoint}")
                return

        # Completed successfully
        await ai_adapter.destroy_session(adapter_session)
        await ai_adapter.stop()

        session.state.status = "completed"

        # Clean up pause checkpoint
        checkpoint_path.unlink(missing_ok=True)

        # Write output if configured
        if conv.output_file:
            output_content = "\n\n---\n\n".join(
                m.content for m in session.state.messages if m.role == "assistant"
            )
            Path(conv.output_file).write_text(output_content)
            if not json_output:
                console.print(f"[green]Output written to {conv.output_file}[/green]")

        if json_output:
            result = {
                "status": "completed",
                "prompts_completed": len(conv.prompts) - start_idx,
                "responses": responses,
                "output_file": conv.output_file,
            }
            console.print_json(json_module.dumps(result))
        else:
            console.print("\n[green]✓ Workflow completed[/green]")

    except Exception as e:
        if json_output:
            console.print_json(json_module.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error resuming: {e}[/red]")
        raise
