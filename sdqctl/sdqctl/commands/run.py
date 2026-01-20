"""
sdqctl run - Execute a single prompt or ConversationFile.

Usage:
    sdqctl run "Audit authentication module"
    sdqctl run workflow.conv
    sdqctl run workflow.conv --adapter copilot --model gpt-4
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile
from ..core.session import Session

console = Console()


@click.command("run")
@click.argument("target")
@click.option("--adapter", "-a", default=None, help="AI adapter (copilot, claude, openai, mock)")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--context", "-c", multiple=True, help="Additional context files")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
def run(
    target: str,
    adapter: Optional[str],
    model: Optional[str],
    context: tuple[str, ...],
    output: Optional[str],
    json_output: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Execute a single prompt or ConversationFile."""
    asyncio.run(_run_async(target, adapter, model, context, output, json_output, verbose, dry_run))


async def _run_async(
    target: str,
    adapter_name: Optional[str],
    model: Optional[str],
    extra_context: tuple[str, ...],
    output_file: Optional[str],
    json_output: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Async implementation of run command."""

    # Determine if target is a file or inline prompt
    target_path = Path(target)
    if target_path.exists() and target_path.suffix in (".conv", ".copilot"):
        # Load ConversationFile
        conv = ConversationFile.from_file(target_path)
        if verbose:
            console.print(f"[blue]Loaded workflow from {target_path}[/blue]")
    else:
        # Treat as inline prompt
        conv = ConversationFile(
            prompts=[target],
            adapter=adapter_name or "mock",
            model=model or "gpt-4",
        )
        if verbose:
            console.print("[blue]Running inline prompt[/blue]")

    # Apply overrides
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model

    # Add extra context files
    for ctx in extra_context:
        conv.context_files.append(f"@{ctx}")

    # Override output
    if output_file:
        conv.output_file = output_file

    # Create session
    session = Session(conv)

    # Show status
    if verbose or dry_run:
        status = session.get_status()
        console.print(Panel.fit(
            f"Adapter: {conv.adapter}\n"
            f"Model: {conv.model}\n"
            f"Mode: {conv.mode}\n"
            f"Prompts: {len(conv.prompts)}\n"
            f"Context files: {len(conv.context_files)}\n"
            f"Context loaded: {status['context']['files_loaded']} files",
            title="Workflow Configuration"
        ))

    if dry_run:
        console.print("\n[yellow]Dry run - no execution[/yellow]")
        
        # Show prompts
        for i, prompt in enumerate(conv.prompts, 1):
            console.print(f"\n[bold]Prompt {i}:[/bold]")
            console.print(prompt[:200] + ("..." if len(prompt) > 200 else ""))
        
        return

    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Using mock adapter instead[/yellow]")
        ai_adapter = get_adapter("mock")

    # Run workflow
    try:
        await ai_adapter.start()

        # Create adapter session
        adapter_session = await ai_adapter.create_session(
            AdapterConfig(
                model=conv.model,
                streaming=True,
            )
        )

        session.state.status = "running"
        responses = []

        # Include context in first prompt
        context_content = session.context.get_context_content()

        # Build pause point lookup: {prompt_index: message}
        pause_after = {idx: msg for idx, msg in conv.pause_points}

        for i, prompt in enumerate(conv.prompts):
            if verbose:
                console.print(f"\n[bold blue]Sending prompt {i + 1}/{len(conv.prompts)}...[/bold blue]")

            # Add context to first prompt
            full_prompt = prompt
            if i == 0 and context_content:
                full_prompt = f"{context_content}\n\n{prompt}"

            # Stream response
            if verbose:
                console.print("[dim]Response:[/dim]")

            def on_chunk(chunk: str) -> None:
                if verbose and not json_output:
                    console.print(chunk, end="")

            response = await ai_adapter.send(adapter_session, full_prompt, on_chunk=on_chunk)

            if verbose:
                console.print()  # Newline after streaming

            responses.append(response)
            session.add_message("user", prompt)
            session.add_message("assistant", response)

            # Check for PAUSE after this prompt
            if i in pause_after:
                pause_msg = pause_after[i]
                session.state.prompt_index = i + 1  # Next prompt to resume from
                checkpoint_path = session.save_pause_checkpoint(pause_msg)
                
                await ai_adapter.destroy_session(adapter_session)
                await ai_adapter.stop()
                
                console.print(f"\n[yellow]⏸  PAUSED: {pause_msg}[/yellow]")
                console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                console.print(f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}")
                return

        # Cleanup
        await ai_adapter.destroy_session(adapter_session)
        session.state.status = "completed"

        # Output
        final_output = "\n\n---\n\n".join(responses)

        if json_output:
            import json
            result = {
                "status": "completed",
                "prompts": len(conv.prompts),
                "responses": responses,
                "session": session.to_dict(),
            }
            console.print_json(json.dumps(result))
        else:
            if output_file:
                Path(output_file).write_text(final_output)
                console.print(f"\n[green]Output written to {output_file}[/green]")
            else:
                console.print("\n" + "=" * 60)
                console.print(Markdown(final_output))

    except Exception as e:
        session.state.status = "failed"
        console.print(f"[red]Error: {e}[/red]")
        raise

    finally:
        await ai_adapter.stop()
