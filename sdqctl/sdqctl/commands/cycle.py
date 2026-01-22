"""
sdqctl cycle - Run multi-cycle workflow with compaction.

Usage:
    sdqctl cycle workflow.conv --max-cycles 5
    sdqctl cycle workflow.conv --checkpoint-dir ./checkpoints

Session Modes:
    accumulate  Context grows across cycles. Compaction triggered only when
                approaching context limit. Best for iterative refinement where
                prior context is valuable.
                
    compact     Summarize conversation after each cycle. Keeps session but
                reduces token usage. Best for long-running workflows where
                recent context matters more than full history.
                
    fresh       Start new adapter session each cycle. CONTEXT files are
                reloaded from disk, picking up any changes. Best for
                autonomous workflows that modify files between cycles.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile
from ..core.exceptions import ExitCode, LoopDetected, MissingContextFiles
from ..core.logging import get_logger
from ..core.loop_detector import LoopDetector
from ..core.progress import progress as progress_print
from ..core.session import Session
from .utils import run_async

logger = get_logger(__name__)
console = Console()


# Session mode descriptions for help and documentation
SESSION_MODES = {
    "accumulate": "Context grows, compact only at limit",
    "compact": "Summarize after each cycle",
    "fresh": "New session each cycle, reload files",
}


@click.command("cycle")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--max-cycles", "-n", type=int, default=None, help="Override max cycles")
@click.option("--session-mode", "-s", type=click.Choice(["accumulate", "compact", "fresh"]), 
              default="accumulate", help="Session handling: accumulate (grow context), compact (summarize each cycle), fresh (new session each cycle)")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--checkpoint-dir", type=click.Path(), default=None, help="Checkpoint directory")
@click.option("--prologue", multiple=True, help="Prepend to each prompt (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Append to each prompt (inline text or @file)")
@click.option("--header", multiple=True, help="Prepend to output (inline text or @file)")
@click.option("--footer", multiple=True, help="Append to output (inline text or @file)")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--event-log", default=None, help="Export SDK events to JSONL file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
@click.option("--render-only", is_flag=True, help="Render prompts without executing (no AI calls)")
def cycle(
    workflow: str,
    max_cycles: Optional[int],
    session_mode: str,
    adapter: Optional[str],
    model: Optional[str],
    checkpoint_dir: Optional[str],
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    header: tuple[str, ...],
    footer: tuple[str, ...],
    output: Optional[str],
    event_log: Optional[str],
    json_output: bool,
    dry_run: bool,
    render_only: bool,
) -> None:
    """Run multi-cycle workflow with compaction."""
    # Handle --render-only by delegating to render logic
    if render_only:
        import json
        from ..core.renderer import render_workflow, format_rendered_json, format_rendered_markdown
        
        conv = ConversationFile.from_file(Path(workflow))
        
        # Apply CLI options
        if prologue:
            conv.prologues = list(prologue) + conv.prologues
        if epilogue:
            conv.epilogues = list(epilogue) + conv.epilogues
        
        # Map session mode names for render (accumulate is canonical)
        render_session_mode = session_mode
        
        rendered = render_workflow(
            conv, 
            session_mode=render_session_mode, 
            max_cycles=max_cycles or conv.max_cycles
        )
        
        if json_output:
            output_content = json.dumps(format_rendered_json(rendered), indent=2)
        else:
            output_content = format_rendered_markdown(rendered)
        
        if output:
            output_path = Path(output)
            # Handle fresh mode with directory output
            if session_mode == "fresh" and output_path.suffix == "" and len(rendered.cycles) > 1:
                output_path.mkdir(parents=True, exist_ok=True)
                for c in rendered.cycles:
                    from ..core.renderer import RenderedWorkflow
                    single_cycle = RenderedWorkflow(
                        workflow_path=rendered.workflow_path,
                        workflow_name=rendered.workflow_name,
                        session_mode=rendered.session_mode,
                        adapter=rendered.adapter,
                        model=rendered.model,
                        max_cycles=rendered.max_cycles,
                        cycles=[c],
                        base_variables=rendered.base_variables,
                    )
                    if json_output:
                        cycle_content = json.dumps(format_rendered_json(single_cycle), indent=2)
                        cycle_file = output_path / f"cycle-{c.number}.json"
                    else:
                        cycle_content = format_rendered_markdown(single_cycle)
                        cycle_file = output_path / f"cycle-{c.number}.md"
                    cycle_file.write_text(cycle_content)
                    console.print(f"[green]Wrote {cycle_file}[/green]")
            else:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output_content)
                console.print(f"[green]Rendered to {output_path}[/green]")
        else:
            if json_output:
                console.print_json(output_content)
            else:
                console.print(output_content)
        return
    
    run_async(_cycle_async(
        workflow, max_cycles, session_mode, adapter, model, checkpoint_dir,
        prologue, epilogue, header, footer,
        output, event_log, json_output, dry_run
    ))


async def _cycle_async(
    workflow_path: str,
    max_cycles_override: Optional[int],
    session_mode: str,
    adapter_name: Optional[str],
    model: Optional[str],
    checkpoint_dir: Optional[str],
    cli_prologues: tuple[str, ...],
    cli_epilogues: tuple[str, ...],
    cli_headers: tuple[str, ...],
    cli_footers: tuple[str, ...],
    output_file: Optional[str],
    event_log_path: Optional[str],
    json_output: bool,
    dry_run: bool,
) -> None:
    """Execute multi-cycle workflow with session management.
    
    Session modes control how context is managed across cycles:
    
    - accumulate: Keep full conversation history. Compaction only triggers
      when approaching the context limit. Use for iterative refinement.
      
    - compact: Summarize conversation after each cycle to reduce tokens.
      Maintains session continuity while managing context growth.
      
    - fresh: Create new adapter session each cycle. Reloads CONTEXT files
      from disk, so file changes made during cycle N are visible in N+1.
    """
    from ..core.conversation import (
        build_prompt_with_injection,
        build_output_with_injection,
        get_standard_variables,
        substitute_template_variables,
    )
    
    import time
    cycle_start = time.time()

    # Load workflow
    conv = ConversationFile.from_file(Path(workflow_path))
    progress_print(f"Running {Path(workflow_path).name} (cycle mode, session={session_mode})...")

    # Validate mandatory context files before execution
    # Respect VALIDATION-MODE directive from the workflow file
    is_lenient = conv.validation_mode == "lenient"
    errors, warnings = conv.validate_context_files(allow_missing=is_lenient)
    
    # Show warnings
    if warnings:
        console.print(f"[yellow]Warning: Optional/excluded context files not found:[/yellow]")
        for pattern, resolved in warnings:
            console.print(f"[yellow]  - {pattern}[/yellow]")
    
    # Errors are blocking
    if errors:
        patterns = [pattern for pattern, _ in errors]
        console.print(f"[red]Error: Missing mandatory context files:[/red]")
        for pattern, resolved in errors:
            console.print(f"[red]  - {pattern} (resolved to {resolved})[/red]")
        console.print(f"[dim]Tip: Use VALIDATION-MODE lenient in workflow or pass --allow-missing[/dim]")
        raise MissingContextFiles(patterns, {p: str(r) for p, r in errors})

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
    
    # Get template variables for prompts (excludes WORKFLOW_NAME to avoid Q-001)
    template_vars = get_standard_variables(conv.source_path)
    # Get template variables for output paths (includes WORKFLOW_NAME)
    output_vars = get_standard_variables(conv.source_path, include_workflow_vars=True)

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

    # Initialize loop detector with session ID for stop file detection (Q-002)
    loop_detector = LoopDetector(session_id=session.id)
    last_reasoning: list[str] = []  # Collect reasoning from callbacks

    try:
        await ai_adapter.start()

        # Determine effective event log path (CLI overrides workflow)
        effective_event_log = event_log_path or conv.event_log
        if effective_event_log:
            effective_event_log = substitute_template_variables(effective_event_log, template_vars)

        adapter_session = await ai_adapter.create_session(
            AdapterConfig(
                model=conv.model,
                streaming=True,
                debug_categories=conv.debug_categories,
                debug_intents=conv.debug_intents,
                event_log=effective_event_log,
            )
        )
        
        try:
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
                    
                    # Add cycle number to template variables
                    cycle_vars = template_vars.copy()
                    cycle_vars["CYCLE_NUMBER"] = str(cycle_num + 1)
                    cycle_vars["CYCLE_TOTAL"] = str(conv.max_cycles)
                    cycle_vars["MAX_CYCLES"] = str(conv.max_cycles)

                    # Session mode: fresh = new session each cycle
                    if session_mode == "fresh" and cycle_num > 0:
                        await ai_adapter.destroy_session(adapter_session)
                        adapter_session = await ai_adapter.create_session(
                            AdapterConfig(
                                model=conv.model,
                                streaming=True,
                                debug_categories=conv.debug_categories,
                                debug_intents=conv.debug_intents,
                                event_log=effective_event_log,
                            )
                        )
                        # Reload CONTEXT files from disk (pick up any changes)
                        session.reload_context()
                        progress_print(f"  🔄 New session for cycle {cycle_num + 1}")

                    # Session mode: compact = compact at start of each cycle (after first)
                    if session_mode == "compact" and cycle_num > 0:
                        console.print(f"\n[yellow]Compacting before cycle {cycle_num + 1}...[/yellow]")
                        progress_print(f"  🗜  Compacting context...")
                        
                        compact_result = await ai_adapter.compact(
                            adapter_session,
                            conv.compact_preserve,
                            session.get_compaction_prompt()
                        )
                        
                        console.print(f"[green]Compacted: {compact_result.tokens_before} → {compact_result.tokens_after} tokens[/green]")
                        progress_print(f"  🗜  Compacted: {compact_result.tokens_before} → {compact_result.tokens_after} tokens")

                    # Check for compaction (accumulate mode, or when context limit reached)
                    if session_mode == "accumulate" and session.needs_compaction():
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

                    # Run all steps in this cycle (prompts, compact, etc.)
                    # For fresh mode: re-inject context on each cycle (like cycle 0)
                    if session_mode == "fresh":
                        context_content = session.context.get_context_content()
                    else:
                        context_content = session.context.get_context_content() if cycle_num == 0 else ""

                    # Use steps if available, fallback to prompts for backward compat
                    steps_to_process = conv.steps if conv.steps else [
                        {"type": "prompt", "content": p} for p in conv.prompts
                    ]
                    
                    prompt_idx = 0
                    for step in steps_to_process:
                        step_type = step.type if hasattr(step, 'type') else step.get('type')
                        step_content = step.content if hasattr(step, 'content') else step.get('content', '')
                        
                        if step_type == "prompt":
                            prompt = step_content
                            session.state.prompt_index = prompt_idx

                            # Build prompt with prologue/epilogue injection
                            full_prompt = build_prompt_with_injection(
                                prompt, conv.prologues, conv.epilogues, 
                                conv.source_path.parent if conv.source_path else None,
                                cycle_vars
                            )
                            
                            # Add context to first prompt (always for fresh, only cycle 0 for others)
                            if prompt_idx == 0 and context_content:
                                full_prompt = f"{context_content}\n\n{full_prompt}"
                            
                            # On subsequent cycles (accumulate mode), add continuation context
                            if session_mode == "accumulate" and cycle_num > 0 and prompt_idx == 0 and conv.on_context_limit_prompt:
                                full_prompt = f"{conv.on_context_limit_prompt}\n\n{full_prompt}"

                            if logger.isEnabledFor(10):  # DEBUG level
                                console.print(f"\n[dim]Prompt {prompt_idx + 1}/{len(conv.prompts)}:[/dim]")
                                console.print(f"[dim]{prompt[:100]}...[/dim]" if len(prompt) > 100 else f"[dim]{prompt}[/dim]")

                            # Clear reasoning collector before send
                            last_reasoning.clear()
                            
                            def collect_reasoning(reasoning: str) -> None:
                                last_reasoning.append(reasoning)
                            
                            response = await ai_adapter.send(
                                adapter_session, 
                                full_prompt,
                                on_reasoning=collect_reasoning
                            )
                            
                            # Check for loop after each response
                            combined_reasoning = " ".join(last_reasoning) if last_reasoning else None
                            if loop_result := loop_detector.check(combined_reasoning, response, cycle_num):
                                console.print(f"\n[red]⚠️  {loop_result}[/red]")
                                progress_print(f"  ⚠️  Loop detected: {loop_result.reason.value}")
                                raise loop_result
                            
                            session.add_message("user", prompt)
                            session.add_message("assistant", response)
                            all_responses.append({
                                "cycle": cycle_num + 1,
                                "prompt": prompt_idx + 1,
                                "response": response
                            })
                            prompt_idx += 1
                        
                        elif step_type == "compact":
                            # Execute inline COMPACT directive
                            console.print("[yellow]🗜  Compacting conversation...[/yellow]")
                            progress_print("  🗜  Compacting conversation...")
                            
                            preserve = step.preserve if hasattr(step, 'preserve') else []
                            all_preserve = conv.compact_preserve + preserve
                            compact_prompt = session.get_compaction_prompt()
                            if all_preserve:
                                compact_prompt = f"Preserve these items: {', '.join(all_preserve)}\n\n{compact_prompt}"
                            
                            compact_response = await ai_adapter.send(adapter_session, compact_prompt)
                            session.add_message("system", f"[Compaction summary]\n{compact_response}")
                            
                            console.print("[green]🗜  Compaction complete[/green]")
                            progress_print("  🗜  Compaction complete")
                        
                        elif step_type == "checkpoint":
                            # Save checkpoint mid-cycle
                            checkpoint_name = step_content or f"cycle-{cycle_num}-step"
                            checkpoint = session.create_checkpoint(checkpoint_name)
                            console.print(f"[blue]📌 Checkpoint: {checkpoint.name}[/blue]")
                            progress_print(f"  📌 Checkpoint: {checkpoint.name}")

                    progress.update(cycle_task, completed=cycle_num + 1)

            # Mark complete (session cleanup in finally block)
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
                # Include adapter stats (intents, tokens, tools) if available
                if hasattr(ai_adapter, 'get_session_stats'):
                    stats = ai_adapter.get_session_stats(adapter_session)
                    if stats:
                        result["adapter_stats"] = {
                            "total_input_tokens": stats.total_input_tokens,
                            "total_output_tokens": stats.total_output_tokens,
                            "total_tool_calls": stats.total_tool_calls,
                            "tool_calls_succeeded": getattr(stats, 'tool_calls_succeeded', 0),
                            "tool_calls_failed": getattr(stats, 'tool_calls_failed', 0),
                            "turns": stats.turns,
                            "model": stats.model,
                        }
                        # Include intent tracking if available
                        if hasattr(stats, 'current_intent'):
                            result["adapter_stats"]["current_intent"] = stats.current_intent
                            result["adapter_stats"]["intent_history"] = stats.intent_history
                console.print_json(json.dumps(result))
            else:
                console.print(f"\n[green]✓ Completed {conv.max_cycles} cycles[/green]")
                console.print(f"[dim]Total messages: {len(session.state.messages)}[/dim]")
                
                if conv.output_file:
                    # Substitute template variables in output path (use output_vars with WORKFLOW_NAME)
                    effective_output = substitute_template_variables(conv.output_file, output_vars)
                    
                    # Write final summary with header/footer injection
                    output_content = "\n\n---\n\n".join(
                        f"## Cycle {r['cycle']}, Prompt {r['prompt']}\n\n{r['response']}"
                        for r in all_responses
                    )
                    output_content = build_output_with_injection(
                        output_content, conv.headers, conv.footers,
                        conv.source_path.parent if conv.source_path else None,
                        output_vars
                    )
                    Path(effective_output).parent.mkdir(parents=True, exist_ok=True)
                    Path(effective_output).write_text(output_content)
                    progress_print(f"  Writing to {effective_output}")
                    console.print(f"[green]Output written to {effective_output}[/green]")
            
            progress_print(f"Done in {cycle_elapsed:.1f}s")
        
        finally:
            # Export events before destroying session (if configured via CLI or workflow)
            if effective_event_log and hasattr(ai_adapter, 'export_events'):
                event_count = ai_adapter.export_events(adapter_session, effective_event_log)
                if event_count > 0:
                    logger.info(f"Exported {event_count} events to {effective_event_log}")
                    progress_print(f"  📋 Exported {event_count} events to {effective_event_log}")
            
            # Always destroy session (handles both success and error paths)
            await ai_adapter.destroy_session(adapter_session)

    except LoopDetected as e:
        session.state.status = "failed"
        # Save checkpoint to preserve session state before exit
        checkpoint_path = session.save_pause_checkpoint(f"Loop detected: {e.reason.value}")
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        logger.error(f"Loop detected: {e}")
        sys.exit(e.exit_code)
    
    except MissingContextFiles as e:
        session.state.status = "failed"
        # Save checkpoint to preserve session state before exit
        checkpoint_path = session.save_pause_checkpoint(f"Missing context files: {e.patterns}")
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        logger.error(f"Missing files: {e}")
        sys.exit(e.exit_code)

    except Exception as e:
        session.state.status = "failed"
        # Save checkpoint to preserve session state before exit
        checkpoint_path = session.save_pause_checkpoint(f"Error: {e}")
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        console.print(f"[red]Error: {e}[/red]")
        raise

    finally:
        await ai_adapter.stop()
