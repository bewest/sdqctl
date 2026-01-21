"""
sdqctl run - Execute a single prompt or ConversationFile.

Usage:
    sdqctl run "Audit authentication module"
    sdqctl run workflow.conv
    sdqctl run workflow.conv --adapter copilot --model gpt-4
    sdqctl run workflow.conv --allow-files "./lib/*" --deny-files "./lib/special"
"""

import logging
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from .utils import run_async
from ..core.conversation import ConversationFile, FileRestrictions, substitute_template_variables
from ..core.exceptions import MissingContextFiles
from ..core.logging import get_logger
from ..core.progress import progress, ProgressTracker
from ..core.session import Session

logger = get_logger(__name__)


def git_commit_checkpoint(
    checkpoint_name: str,
    output_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> bool:
    """Commit outputs to git as a checkpoint.
    
    Returns True if commit succeeded, False otherwise.
    """
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False  # Not in a git repo
        
        # Stage output files
        files_to_add = []
        if output_file and output_file.exists():
            files_to_add.append(str(output_file))
        if output_dir and output_dir.exists():
            files_to_add.append(str(output_dir))
        
        if not files_to_add:
            return False  # Nothing to commit
        
        # Add files
        subprocess.run(["git", "add"] + files_to_add, check=True)
        
        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            return False  # No changes to commit
        
        # Commit
        commit_msg = f"checkpoint: {checkpoint_name}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True,
        )
        return True
        
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False  # git not installed

console = Console()


@click.command("run")
@click.argument("target")
@click.option("--adapter", "-a", default=None, help="AI adapter (copilot, claude, openai, mock)")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--context", "-c", multiple=True, help="Additional context files")
@click.option("--allow-files", multiple=True, help="Glob pattern for allowed files (can be repeated)")
@click.option("--deny-files", multiple=True, help="Glob pattern for denied files (can be repeated)")
@click.option("--allow-dir", multiple=True, help="Directory to allow (can be repeated)")
@click.option("--deny-dir", multiple=True, help="Directory to deny (can be repeated)")
@click.option("--prologue", multiple=True, help="Prepend to each prompt (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Append to each prompt (inline text or @file)")
@click.option("--header", multiple=True, help="Prepend to output (inline text or @file)")
@click.option("--footer", multiple=True, help="Append to output (inline text or @file)")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
def run(
    target: str,
    adapter: Optional[str],
    model: Optional[str],
    context: tuple[str, ...],
    allow_files: tuple[str, ...],
    deny_files: tuple[str, ...],
    allow_dir: tuple[str, ...],
    deny_dir: tuple[str, ...],
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    header: tuple[str, ...],
    footer: tuple[str, ...],
    output: Optional[str],
    json_output: bool,
    dry_run: bool,
) -> None:
    """Execute a single prompt or ConversationFile.
    
    Examples:
    
    \b
    # Run inline prompt
    sdqctl run "Audit authentication module"
    
    \b
    # Run workflow file
    sdqctl run workflow.conv
    
    \b
    # Focus on lib, exclude special module
    sdqctl run "Analyze code" --allow-files "./lib/*" --deny-files "./lib/special"
    
    \b
    # Add context to every prompt
    sdqctl run workflow.conv --prologue "Date: 2026-01-21" --epilogue @templates/footer.md
    
    \b
    # Add header/footer to output
    sdqctl run workflow.conv --header "# Report" --footer @templates/disclaimer.md
    """
    run_async(_run_async(
        target, adapter, model, context, 
        allow_files, deny_files, allow_dir, deny_dir,
        prologue, epilogue, header, footer,
        output, json_output, dry_run
    ))


async def _run_async(
    target: str,
    adapter_name: Optional[str],
    model: Optional[str],
    extra_context: tuple[str, ...],
    allow_files: tuple[str, ...],
    deny_files: tuple[str, ...],
    allow_dir: tuple[str, ...],
    deny_dir: tuple[str, ...],
    cli_prologues: tuple[str, ...],
    cli_epilogues: tuple[str, ...],
    cli_headers: tuple[str, ...],
    cli_footers: tuple[str, ...],
    output_file: Optional[str],
    json_output: bool,
    dry_run: bool,
) -> None:
    """Async implementation of run command."""
    from ..core.conversation import (
        build_prompt_with_injection,
        build_output_with_injection,
        get_standard_variables,
    )
    
    import time
    start_time = time.time()

    # Determine if target is a file or inline prompt
    target_path = Path(target)
    if target_path.exists() and target_path.suffix in (".conv", ".copilot"):
        # Load ConversationFile
        conv = ConversationFile.from_file(target_path)
        logger.info(f"Loaded workflow from {target_path}")
        progress(f"Running {target_path.name}...")
        
        # Validate mandatory context files before execution
        missing_files = conv.validate_context_files()
        if missing_files:
            patterns = [pattern for pattern, _ in missing_files]
            console.print(f"[red]Error: Missing mandatory context files:[/red]")
            for pattern, resolved in missing_files:
                console.print(f"[red]  - {pattern} (resolved to {resolved})[/red]")
            sys.exit(MissingContextFiles(patterns).exit_code)
    else:
        # Treat as inline prompt
        conv = ConversationFile(
            prompts=[target],
            adapter=adapter_name or "mock",
            model=model or "gpt-4",
        )
        logger.info("Running inline prompt")
        progress("Running inline prompt...")

    # Apply overrides
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model

    # Add extra context files
    for ctx in extra_context:
        conv.context_files.append(f"@{ctx}")

    # Merge CLI file restrictions with file-defined ones
    # CLI allow patterns replace file patterns, CLI deny patterns add to file patterns
    if allow_files or deny_files or allow_dir or deny_dir:
        conv.file_restrictions = conv.file_restrictions.merge_with_cli(
            list(allow_files) + list(f"{d}/**" for d in allow_dir),
            list(deny_files) + list(f"{d}/**" for d in deny_dir),
        )
        logger.info(f"File restrictions: allow={conv.file_restrictions.allow_patterns}, deny={conv.file_restrictions.deny_patterns}")

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

    # Override output
    if output_file:
        conv.output_file = output_file

    # Create session
    session = Session(conv)

    # Show status
    if dry_run:
        status = session.get_status()
        restrictions_info = ""
        if conv.file_restrictions.allow_patterns or conv.file_restrictions.deny_patterns:
            restrictions_info = f"\nAllow patterns: {conv.file_restrictions.allow_patterns}\nDeny patterns: {conv.file_restrictions.deny_patterns}"
        
        console.print(Panel.fit(
            f"Adapter: {conv.adapter}\n"
            f"Model: {conv.model}\n"
            f"Mode: {conv.mode}\n"
            f"Prompts: {len(conv.prompts)}\n"
            f"Context files: {len(conv.context_files)}\n"
            f"Context loaded: {status['context']['files_loaded']} files"
            f"{restrictions_info}",
            title="Workflow Configuration"
        ))
    else:
        logger.debug(f"Adapter: {conv.adapter}, Model: {conv.model}, Mode: {conv.mode}")
        logger.debug(f"Prompts: {len(conv.prompts)}, Context files: {len(conv.context_files)}")

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
        
        try:
            session.state.status = "running"
            responses = []

            # Include context in first prompt
            context_content = session.context.get_context_content()

            # Build pause point lookup: {prompt_index: message}
            pause_after = {idx: msg for idx, msg in conv.pause_points}

            # Process steps (includes prompts, checkpoints, compact, etc.)
            # Fall back to prompts list if no steps defined (backward compat)
            prompt_count = 0
            total_prompts = len(conv.prompts)
            first_prompt = True
            
            steps_to_process = conv.steps if conv.steps else [
                {"type": "prompt", "content": p} for p in conv.prompts
            ]
            
            for step in steps_to_process:
                step_type = step.type if hasattr(step, 'type') else step.get('type')
                step_content = step.content if hasattr(step, 'content') else step.get('content', '')
            
                if step_type == "prompt":
                    prompt = step_content
                    prompt_count += 1
                    step_start = time.time()
                    
                    logger.info(f"Sending prompt {prompt_count}/{total_prompts}...")
                    progress(f"  Step {prompt_count}/{total_prompts}: Sending prompt...")

                    # Build prompt with prologue/epilogue injection
                    base_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    injected_prompt = build_prompt_with_injection(
                        prompt, conv.prologues, conv.epilogues,
                        base_path=base_path,
                        variables=template_vars
                    )
                    
                    # Add context to first prompt
                    full_prompt = injected_prompt
                    if first_prompt and context_content:
                        full_prompt = f"{context_content}\n\n{injected_prompt}"
                        first_prompt = False

                    # Stream response
                    logger.debug("Awaiting response...")

                    def on_chunk(chunk: str) -> None:
                        if logger.isEnabledFor(logging.DEBUG) and not json_output:
                            console.print(chunk, end="")

                    response = await ai_adapter.send(adapter_session, full_prompt, on_chunk=on_chunk)

                    if logger.isEnabledFor(logging.DEBUG):
                        console.print()  # Newline after streaming

                    step_elapsed = time.time() - step_start
                    progress(f"  Step {prompt_count}/{total_prompts}: Response received ({step_elapsed:.1f}s)")

                    responses.append(response)
                    session.add_message("user", prompt)
                    session.add_message("assistant", response)

                    # Check for PAUSE after this prompt
                    prompt_idx = prompt_count - 1
                    if prompt_idx in pause_after:
                        pause_msg = pause_after[prompt_idx]
                        session.state.prompt_index = prompt_count  # Next prompt to resume from
                        checkpoint_path = session.save_pause_checkpoint(pause_msg)
                        
                        console.print(f"\n[yellow]⏸  PAUSED: {pause_msg}[/yellow]")
                        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                        console.print(f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}")
                        return  # Session cleanup handled by finally blocks
            
                elif step_type == "checkpoint":
                    # Save session state and commit outputs to git
                    checkpoint_name = step_content or f"checkpoint-{len(session.state.checkpoints) + 1}"
                    
                    logger.info(f"📌 CHECKPOINT: {checkpoint_name}")
                    progress(f"  📌 CHECKPOINT: {checkpoint_name}")
                    
                    # Write current output to file if configured
                    if conv.output_file and responses:
                        current_output = "\n\n---\n\n".join(responses)
                        output_path = Path(conv.output_file)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(current_output)
                        logger.debug(f"Output written to {output_path}")
                        progress(f"  Writing to {output_path}")
                    
                    # Save session checkpoint
                    checkpoint = session.create_checkpoint(checkpoint_name)
                    
                    # Commit to git
                    output_path = Path(conv.output_file) if conv.output_file else None
                    output_dir = Path(conv.output_dir) if conv.output_dir else None
                    
                    if git_commit_checkpoint(checkpoint_name, output_path, output_dir):
                        console.print(f"[green]✓ Git commit: checkpoint: {checkpoint_name}[/green]")
                        progress(f"  ✓ Git commit created")
                    else:
                        logger.debug("No git changes to commit")
            
                elif step_type == "compact":
                    # Request compaction from the AI
                    logger.info("🗜  COMPACTING conversation...")
                    progress("  🗜  Compacting conversation...")
                    
                    preserve = step.preserve if hasattr(step, 'preserve') else []
                    compact_prompt = session.get_compaction_prompt()
                    if preserve:
                        compact_prompt = f"Preserve these items: {', '.join(preserve)}\n\n{compact_prompt}"
                    
                    response = await ai_adapter.send(adapter_session, compact_prompt)
                    session.add_message("system", f"[Compaction summary]\n{response}")
                    
                    logger.debug("Conversation compacted")
                    progress("  🗜  Compaction complete")
            
                elif step_type == "new_conversation":
                    # End current session, start fresh
                    logger.info("🔄 Starting new conversation...")
                    progress("  🔄 Starting new conversation...")
                    
                    await ai_adapter.destroy_session(adapter_session)
                    adapter_session = await ai_adapter.create_session(
                        AdapterConfig(model=conv.model, streaming=True)
                    )
                    first_prompt = True  # Re-include context in next prompt
                    
                    logger.debug("New session created")
            
                elif step_type == "run":
                    # Execute shell command
                    command = step_content
                    logger.info(f"🔧 RUN: {command}")
                    progress(f"  🔧 Running: {command[:50]}...")
                    
                    run_start = time.time()
                    try:
                        # Security: Use shell=False by default, require ALLOW-SHELL for shell features
                        if conv.allow_shell:
                            # Shell mode enabled - allows pipes, redirects, etc.
                            result = subprocess.run(
                                command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=conv.run_timeout,
                                cwd=conv.cwd or Path.cwd(),
                            )
                        else:
                            # Safe mode - no shell injection possible
                            result = subprocess.run(
                                shlex.split(command),
                                shell=False,
                                capture_output=True,
                                text=True,
                                timeout=conv.run_timeout,
                                cwd=conv.cwd or Path.cwd(),
                            )
                        run_elapsed = time.time() - run_start
                        
                        # Determine if we should include output
                        include_output = (
                            conv.run_output == "always" or
                            (conv.run_output == "on-error" and result.returncode != 0)
                        )
                        
                        if result.returncode == 0:
                            logger.info(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                            progress(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                        else:
                            logger.warning(f"  ✗ Command failed with exit code {result.returncode}")
                            progress(f"  ✗ Command failed (exit {result.returncode})")
                            
                        # Add output to context for next prompt if configured
                        # NOTE: Capture output BEFORE any early return to preserve debugging context
                        if include_output:
                            output_text = result.stdout or ""
                            if result.stderr:
                                output_text += f"\n\n[stderr]\n{result.stderr}"
                            
                            # Store as context for next prompt (add to session messages)
                            if output_text.strip():
                                status_marker = "" if result.returncode == 0 else f" (exit {result.returncode})"
                                run_context = f"```\n$ {command}{status_marker}\n{output_text}\n```"
                                session.add_message("system", f"[RUN output]\n{run_context}")
                                logger.debug(f"Added RUN output to context ({len(output_text)} chars)")
                        
                        # Handle stop-on-error AFTER capturing output
                        if result.returncode != 0 and conv.run_on_error == "stop":
                                console.print(f"[red]RUN failed: {command}[/red]")
                                console.print(f"[dim]Exit code: {result.returncode}[/dim]")
                                if result.stderr:
                                    console.print(f"[dim]stderr: {result.stderr[:500]}[/dim]")
                                session.state.status = "failed"
                                return  # Session cleanup handled by finally blocks
                    
                    except subprocess.TimeoutExpired as e:
                        logger.error(f"  ✗ Command timed out after {conv.run_timeout}s")
                        progress(f"  ✗ Command timed out after {conv.run_timeout}s")
                        
                        # Capture partial output (always - timeout output is valuable for debugging)
                        partial_stdout = e.stdout or ""
                        partial_stderr = e.stderr or ""
                        partial_output = partial_stdout
                        if partial_stderr:
                            partial_output += f"\n\n[stderr]\n{partial_stderr}"
                        
                        if partial_output.strip():
                            run_context = f"```\n$ {command}\n[TIMEOUT after {conv.run_timeout}s]\n{partial_output}\n```"
                            session.add_message("system", f"[RUN timeout - partial output]\n{run_context}")
                            logger.debug(f"Captured partial output on timeout ({len(partial_output)} chars)")
                        
                        if conv.run_on_error == "stop":
                            console.print(f"[red]RUN timed out: {command}[/red]")
                            session.state.status = "failed"
                            return  # Session cleanup handled by finally blocks
                    
                    except Exception as e:
                        logger.error(f"  ✗ Command error: {e}")
                        
                        if conv.run_on_error == "stop":
                            console.print(f"[red]RUN error: {e}[/red]")
                            session.state.status = "failed"
                            return

            # Mark complete (session cleanup in finally block)
            session.state.status = "completed"

            # Output with header/footer injection
            raw_output = "\n\n---\n\n".join(responses)
            base_path = conv.source_path.parent if conv.source_path else Path.cwd()
            final_output = build_output_with_injection(
                raw_output, conv.headers, conv.footers,
                base_path=base_path,
                variables=template_vars
            )
            total_elapsed = time.time() - start_time

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
                # Use conv.output_file which includes both CLI override and workflow OUTPUT-FILE
                effective_output = conv.output_file
                if effective_output:
                    # Substitute template variables in output path
                    effective_output = substitute_template_variables(effective_output, template_vars)
                    output_path = Path(effective_output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(final_output)
                    progress(f"  Writing to {effective_output}")
                    console.print(f"\n[green]Output written to {effective_output}[/green]")
                else:
                    console.print("\n" + "=" * 60)
                    console.print(Markdown(final_output))
            
            progress(f"Done in {total_elapsed:.1f}s")
        
        finally:
            # Always destroy session (handles both success and error paths)
            await ai_adapter.destroy_session(adapter_session)

    except Exception as e:
        session.state.status = "failed"
        console.print(f"[red]Error: {e}[/red]")
        raise

    finally:
        await ai_adapter.stop()
