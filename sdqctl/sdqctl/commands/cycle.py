"""
sdqctl cycle - Run multi-cycle workflow with compaction.

Usage:
    sdqctl cycle workflow.conv --max-cycles 5
    sdqctl cycle workflow.conv --checkpoint-dir ./checkpoints
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile
from ..core.logging import get_logger
from ..core.progress import progress as progress_print
from ..core.session import Session

logger = get_logger(__name__)
console = Console()


@click.command("cycle")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--max-cycles", "-n", type=int, default=None, help="Override max cycles")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--checkpoint-dir", type=click.Path(), default=None, help="Checkpoint directory")
@click.option("--prologue", multiple=True, help="Prepend to each prompt (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Append to each prompt (inline text or @file)")
@click.option("--header", multiple=True, help="Prepend to output (inline text or @file)")
@click.option("--footer", multiple=True, help="Append to output (inline text or @file)")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
def cycle(
    workflow: str,
    max_cycles: Optional[int],
    adapter: Optional[str],
    model: Optional[str],
    checkpoint_dir: Optional[str],
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    header: tuple[str, ...],
    footer: tuple[str, ...],
    output: Optional[str],
    json_output: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Run multi-cycle workflow with compaction."""
    asyncio.run(_cycle_async(
        workflow, max_cycles, adapter, model, checkpoint_dir,
        prologue, epilogue, header, footer,
        output, json_output, verbose, dry_run
    ))


async def _cycle_async(
    workflow_path: str,
    max_cycles_override: Optional[int],
    adapter_name: Optional[str],
    model: Optional[str],
    checkpoint_dir: Optional[str],
    cli_prologues: tuple[str, ...],
    cli_epilogues: tuple[str, ...],
    cli_headers: tuple[str, ...],
    cli_footers: tuple[str, ...],
    output_file: Optional[str],
    json_output: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Async implementation of cycle command."""
    from ..core.conversation import (
        build_prompt_with_injection,
        build_output_with_injection,
        get_standard_variables,
    )
    
    import time
    cycle_start = time.time()

    # Load workflow
    conv = ConversationFile.from_file(Path(workflow_path))
    progress_print(f"Running {Path(workflow_path).name} (cycle mode)...")

    # Apply overrides
    if max_cycles_override:
        conv.max_cycles = max_cycles_override
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model
    if output_file:
        conv.output_file = output_file
    
    # Add CLI-provided prologues/epilogues (prepend to file-defined ones)
    if cli_prologues:
        conv.prologues = list(cli_prologues) + conv.prologues
    if cli_epilogues:
        conv.epilogues = list(cli_epilogues) + conv.epilogues
    if cli_headers:
        conv.headers = list(cli_headers) + conv.headers
    if cli_footers:
        conv.footers = list(cli_footers) + conv.footers
    
    # Get template variables for this workflow
    template_vars = get_standard_variables(conv.source_path)

    # Create session
    session_dir = Path(checkpoint_dir) if checkpoint_dir else None
    session = Session(conv, session_dir=session_dir)

    if dry_run:
        console.print(Panel.fit(
            f"Workflow: {workflow_path}\n"
            f"Adapter: {conv.adapter}\n"
            f"Model: {conv.model}\n"
            f"Max Cycles: {conv.max_cycles}\n"
            f"Prompts per cycle: {len(conv.prompts)}\n"
            f"Context limit: {int(conv.context_limit * 100)}%\n"
            f"On context limit: {conv.on_context_limit}",
            title="Cycle Configuration"
        ))
    else:
        logger.info(f"Loaded workflow from {workflow_path}")
        logger.debug(f"Adapter: {conv.adapter}, Model: {conv.model}, Max Cycles: {conv.max_cycles}")

    if dry_run:
        console.print("\n[yellow]Dry run - no execution[/yellow]")
        return

    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Using mock adapter instead[/yellow]")
        ai_adapter = get_adapter("mock")

    try:
        await ai_adapter.start()

        adapter_session = await ai_adapter.create_session(
            AdapterConfig(model=conv.model, streaming=True)
        )

        session.state.status = "running"
        all_responses = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            cycle_task = progress.add_task(
                f"Cycle 1/{conv.max_cycles}",
                total=conv.max_cycles
            )

            # Run cycles
            for cycle_num in range(conv.max_cycles):
                session.state.cycle_number = cycle_num
                progress.update(
                    cycle_task,
                    description=f"Cycle {cycle_num + 1}/{conv.max_cycles}",
                    completed=cycle_num
                )
                progress_print(f"  Cycle {cycle_num + 1}/{conv.max_cycles}...")

                # Check for compaction
                if session.needs_compaction():
                    console.print(f"\n[yellow]Context near limit, compacting...[/yellow]")
                    progress_print(f"  🗜  Compacting context...")
                    
                    compact_result = await ai_adapter.compact(
                        adapter_session,
                        conv.compact_preserve,
                        session.get_compaction_prompt()
                    )
                    
                    console.print(f"[green]Compacted: {compact_result.tokens_before} → {compact_result.tokens_after} tokens[/green]")
                    progress_print(f"  🗜  Compacted: {compact_result.tokens_before} → {compact_result.tokens_after} tokens")

                # Checkpoint if configured
                if session.should_checkpoint():
                    checkpoint = session.create_checkpoint(f"cycle-{cycle_num}")
                    console.print(f"[blue]Checkpoint saved: {checkpoint.name}[/blue]")
                    progress_print(f"  📌 Checkpoint: {checkpoint.name}")

                # Run all prompts in this cycle
                context_content = session.context.get_context_content() if cycle_num == 0 else ""

                for prompt_idx, prompt in enumerate(conv.prompts):
                    session.state.prompt_index = prompt_idx

                    # Build prompt with prologue/epilogue injection
                    full_prompt = build_prompt_with_injection(
                        prompt, conv.prologues, conv.epilogues, 
                        conv.source_path.parent if conv.source_path else None,
                        template_vars
                    )
                    
                    # Add context to first prompt of first cycle
                    if cycle_num == 0 and prompt_idx == 0 and context_content:
                        full_prompt = f"{context_content}\n\n{full_prompt}"
                    
                    # On subsequent cycles, add continuation context
                    if cycle_num > 0 and prompt_idx == 0 and conv.on_context_limit_prompt:
                        full_prompt = f"{conv.on_context_limit_prompt}\n\n{full_prompt}"

                    if logger.isEnabledFor(10):  # DEBUG level
                        console.print(f"\n[dim]Prompt {prompt_idx + 1}/{len(conv.prompts)}:[/dim]")
                        console.print(f"[dim]{prompt[:100]}...[/dim]" if len(prompt) > 100 else f"[dim]{prompt}[/dim]")

                    response = await ai_adapter.send(adapter_session, full_prompt)
                    
                    session.add_message("user", prompt)
                    session.add_message("assistant", response)
                    all_responses.append({
                        "cycle": cycle_num + 1,
                        "prompt": prompt_idx + 1,
                        "response": response
                    })

                progress.update(cycle_task, completed=cycle_num + 1)

        # Cleanup
        await ai_adapter.destroy_session(adapter_session)
        session.state.status = "completed"
        cycle_elapsed = time.time() - cycle_start

        # Output
        if json_output:
            import json
            result = {
                "status": "completed",
                "cycles_completed": conv.max_cycles,
                "responses": all_responses,
                "session": session.to_dict(),
            }
            console.print_json(json.dumps(result))
        else:
            console.print(f"\n[green]✓ Completed {conv.max_cycles} cycles[/green]")
            console.print(f"[dim]Total messages: {len(session.state.messages)}[/dim]")
            
            if conv.output_file:
                # Write final summary with header/footer injection
                output_content = "\n\n---\n\n".join(
                    f"## Cycle {r['cycle']}, Prompt {r['prompt']}\n\n{r['response']}"
                    for r in all_responses
                )
                output_content = build_output_with_injection(
                    output_content, conv.headers, conv.footers,
                    conv.source_path.parent if conv.source_path else None,
                    template_vars
                )
                Path(conv.output_file).parent.mkdir(parents=True, exist_ok=True)
                Path(conv.output_file).write_text(output_content)
                progress_print(f"  Writing to {conv.output_file}")
                console.print(f"[green]Output written to {conv.output_file}[/green]")
        
        progress_print(f"Done in {cycle_elapsed:.1f}s")

    except Exception as e:
        session.state.status = "failed"
        console.print(f"[red]Error: {e}[/red]")
        raise

    finally:
        await ai_adapter.stop()
