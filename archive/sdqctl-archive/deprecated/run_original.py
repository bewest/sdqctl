"""
sdqctl run - Execute a single prompt or ConversationFile.

Usage:
    sdqctl run "Audit authentication module"
    sdqctl run workflow.conv
    sdqctl run workflow.conv --adapter copilot --model gpt-4
    sdqctl run workflow.conv --allow-files "./lib/*" --deny-files "./lib/special"
"""

import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile, substitute_template_variables
from ..core.exceptions import ExitCode, MissingContextFiles
from ..core.logging import get_logger
from ..core.loop_detector import get_stop_file_instruction
from ..core.progress import WorkflowProgress, progress
from ..core.session import Session
from ..utils.output import PromptWriter, handle_error, print_json_error
from .blocks import execute_block_steps
from .elide import process_elided_steps
from .run_steps import (
    execute_run_async_step,
    execute_run_step,
    execute_run_wait_step,
)
from .utils import (
    git_commit_checkpoint,
    resolve_run_directory,
    run_async,
    run_subprocess,
    truncate_output,
)
from .verify_steps import (
    execute_verify_coverage_step,
    execute_verify_step,
    execute_verify_trace_step,
)

logger = get_logger(__name__)


# Aliases for internal use (keep _ prefix for backward compat with tests)
_run_subprocess = run_subprocess
_truncate_output = truncate_output
_execute_block_steps = execute_block_steps  # backward compat


console = Console()


@click.command("run")
@click.argument("target")
@click.option("--adapter", "-a", default=None, help="AI adapter (copilot, claude, openai, mock)")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--context", "-c", multiple=True, help="Additional context files")
@click.option("--allow-files", multiple=True, help="Glob pattern for allowed files")
@click.option("--deny-files", multiple=True, help="Glob pattern for denied files")
@click.option("--allow-dir", multiple=True, help="Directory to allow (can be repeated)")
@click.option("--deny-dir", multiple=True, help="Directory to deny (can be repeated)")
@click.option("--prologue", multiple=True, help="Prepend to each prompt (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Append to each prompt (inline text or @file)")
@click.option("--header", multiple=True, help="Prepend to output (inline text or @file)")
@click.option("--footer", multiple=True, help="Append to output (inline text or @file)")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--event-log", default=None, help="Export SDK events to JSONL file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
@click.option("--render-only", is_flag=True, help="Render prompts without executing (no AI calls)")
@click.option("--min-compaction-density", type=int, default=0,
              help="Skip compaction if context below this % (e.g., 30 = skip if < 30%)")
@click.option("--no-stop-file-prologue", is_flag=True, help="Disable stop file instructions")
@click.option("--stop-file-nonce", default=None, help="Override stop file nonce")
@click.option("--session-name", default=None, help="Named session for resumability")
@click.pass_context
def run(
    ctx: click.Context,
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
    event_log: Optional[str],
    json_output: bool,
    dry_run: bool,
    render_only: bool,
    min_compaction_density: int,
    no_stop_file_prologue: bool,
    stop_file_nonce: Optional[str],
    session_name: Optional[str],
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

    \b
    # Render prompts without executing (no AI calls)
    sdqctl run workflow.conv --render-only
    """
    # Handle --render-only by delegating to render command logic
    if render_only:
        import json as json_module
        import warnings

        from ..core.renderer import format_rendered_json, format_rendered_markdown, render_workflow

        # Deprecation warning
        warnings.warn(
            "--render-only is deprecated, use 'sdqctl render run' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        console.print(
            "[yellow]⚠ --render-only is deprecated. "
            "Use: sdqctl render run workflow.conv[/yellow]"
        )

        target_path = Path(target)
        if target_path.exists() and target_path.suffix in (".conv", ".copilot"):
            conv = ConversationFile.from_file(target_path)
        else:
            # Inline prompt - create minimal ConversationFile
            conv = ConversationFile()
            conv.prompts = [target]

        # Apply CLI options
        if prologue:
            conv.prologues = list(prologue) + conv.prologues
        if epilogue:
            conv.epilogues = list(epilogue) + conv.epilogues
        for pattern in context:
            conv.context_files.append(pattern)

        rendered = render_workflow(conv, session_mode="accumulate", max_cycles=1)

        if json_output:
            output_content = json_module.dumps(format_rendered_json(rendered), indent=2)
            console.print_json(output_content)
        else:
            output_content = format_rendered_markdown(rendered)
            if output:
                Path(output).write_text(output_content)
                console.print(f"[green]Rendered to {output}[/green]")
            else:
                console.print(output_content)
        return

    # Get verbosity and show_prompt from context
    verbosity = ctx.obj.get("verbosity", 0) if ctx.obj else 0
    show_prompt_flag = ctx.obj.get("show_prompt", False) if ctx.obj else False
    json_errors = ctx.obj.get("json_errors", False) if ctx.obj else False

    run_async(_run_async(
        target, adapter, model, context,
        allow_files, deny_files, allow_dir, deny_dir,
        prologue, epilogue, header, footer,
        output, event_log, json_output, dry_run, no_stop_file_prologue, stop_file_nonce,
        verbosity=verbosity, show_prompt=show_prompt_flag,
        min_compaction_density=min_compaction_density,
        json_errors=json_errors,
        session_name=session_name,
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
    event_log_path: Optional[str],
    json_output: bool,
    dry_run: bool,
    no_stop_file_prologue: bool = False,
    stop_file_nonce: Optional[str] = None,
    verbosity: int = 0,
    show_prompt: bool = False,
    min_compaction_density: int = 0,
    json_errors: bool = False,
    session_name: Optional[str] = None,
) -> None:
    """Async implementation of run command."""
    from ..core.conversation import (
        build_output_with_injection,
        build_prompt_with_injection,
        get_standard_variables,
    )
    from ..core.loop_detector import generate_nonce

    # Initialize prompt writer for stderr output
    prompt_writer = PromptWriter(enabled=show_prompt)

    start_time = time.time()

    # Determine if target is a file or inline prompt
    target_path = Path(target)
    if target_path.exists() and target_path.suffix in (".conv", ".copilot"):
        # Load ConversationFile
        conv = ConversationFile.from_file(target_path)
        logger.info(f"Loaded workflow from {target_path}")
        progress(f"Running {target_path.name}...")

        # Validate mandatory context files before execution
        # Respect VALIDATION-MODE directive from the workflow file
        is_lenient = conv.validation_mode == "lenient"
        errors, warnings = conv.validate_context_files(allow_missing=is_lenient)

        # Show warnings (quiet = verbosity == 0)
        if warnings and verbosity > 0:
            console.print("[yellow]Warning: Optional/excluded context files not found:[/yellow]")
            for pattern, resolved in warnings:
                console.print(f"[yellow]  - {pattern}[/yellow]")

        # Errors are blocking
        if errors:
            patterns = [pattern for pattern, _ in errors]
            resolved_paths = {pattern: resolved for pattern, resolved in errors}
            exc = MissingContextFiles(patterns, resolved_paths)
            if json_errors:
                exit_code = handle_error(exc, json_errors=True, context={"workflow": str(target)})
                sys.exit(exit_code)
            else:
                console.print("[red]Error: Missing mandatory context files:[/red]")
                for pattern, resolved in errors:
                    console.print(f"[red]  - {pattern} (resolved to {resolved})[/red]")
                tip = "Tip: Use VALIDATION-MODE lenient or --allow-missing"
                console.print(f"[dim]{tip} to continue[/dim]")
                sys.exit(exc.exit_code)
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
        logger.info(
            f"File restrictions: allow={conv.file_restrictions.allow_patterns}, "
            f"deny={conv.file_restrictions.deny_patterns}"
        )

    # Add CLI-provided prologues/epilogues (prepend to file-defined ones)
    if cli_prologues:
        conv.prologues = list(cli_prologues) + conv.prologues
    if cli_epilogues:
        conv.epilogues = list(cli_epilogues) + conv.epilogues
    if cli_headers:
        conv.headers = list(cli_headers) + conv.headers
    if cli_footers:
        conv.footers = list(cli_footers) + conv.footers

    # Generate nonce for stop file (once per command invocation)
    nonce = stop_file_nonce if stop_file_nonce else generate_nonce()

    # Get template variables for prompts (excludes WORKFLOW_NAME to avoid Q-001)
    # Includes STOP_FILE for agent stop signaling (Q-002)
    template_vars = get_standard_variables(conv.source_path, stop_file_nonce=nonce)
    # Get template variables for output paths (includes WORKFLOW_NAME)
    output_vars = get_standard_variables(conv.source_path, include_workflow_vars=True)

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
            restrictions_info = (
                f"\nAllow patterns: {conv.file_restrictions.allow_patterns}"
                f"\nDeny patterns: {conv.file_restrictions.deny_patterns}"
            )

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

    # Check if stop file already exists (previous run may have requested stop)
    stop_file_path = Path.cwd() / f"STOPAUTOMATION-{nonce}.json"
    if stop_file_path.exists():
        try:
            content = stop_file_path.read_text()
            import json as json_mod
            stop_data = json_mod.loads(content)
            reason = stop_data.get("reason", "Unknown reason")
        except (json_mod.JSONDecodeError, IOError):
            reason = "Could not read stop file content"

        console.print(Panel(
            f"[bold yellow]⚠️  Stop file exists from previous run[/bold yellow]\n\n"
            f"[bold]File:[/bold] {stop_file_path.name}\n"
            f"[bold]Reason:[/bold] {reason}\n\n"
            f"A previous automation run requested human review.\n"
            f"Please review the agent's work before continuing.\n\n"
            f"[dim]To continue: Remove the stop file and run again[/dim]\n"
            f"[dim]    rm {stop_file_path.name}[/dim]",
            title="🛑 Review Required",
            border_style="yellow",
        ))
        return

    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        if json_errors:
            print_json_error(
                "AdapterError",
                str(e),
                ExitCode.GENERAL_ERROR,
                {"adapter": conv.adapter, "fallback": "mock"}
            )
        else:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Using mock adapter instead[/yellow]")
        ai_adapter = get_adapter("mock")

    # Run workflow
    try:
        await ai_adapter.start()

        # Determine effective event log path (CLI overrides workflow)
        effective_event_log = event_log_path or conv.event_log
        if effective_event_log:
            effective_event_log = substitute_template_variables(effective_event_log, template_vars)

        # Build adapter config
        adapter_config = AdapterConfig(
            model=conv.model,
            streaming=True,
            debug_categories=conv.debug_categories,
            debug_intents=conv.debug_intents,
            event_log=effective_event_log,
        )

        # Determine session name: CLI overrides workflow directive
        effective_session_name = session_name or conv.session_name

        # Create or resume adapter session based on session name
        if effective_session_name:
            # Named session: resume if exists, otherwise create new
            try:
                adapter_session = await ai_adapter.resume_session(
                    effective_session_name, adapter_config
                )
                logger.info(f"Resumed session: {effective_session_name}")
                if verbosity > 0:
                    console.print(f"[dim]Resumed session: {effective_session_name}[/dim]")
            except Exception as e:
                # Session doesn't exist, create new with session name
                # Note: SDK may not support named session creation directly,
                # so we create a regular session and track the name
                logger.debug(
                    f"Could not resume session '{effective_session_name}': {e}"
                )
                adapter_session = await ai_adapter.create_session(adapter_config)
                if verbosity > 0:
                    msg = f"[dim]Created new session: {effective_session_name}[/dim]"
                    console.print(msg)
        else:
            adapter_session = await ai_adapter.create_session(adapter_config)

        # Store SDK session ID for checkpoint resume (Q-018)
        session.sdk_session_id = adapter_session.sdk_session_id

        try:
            session.state.status = "running"
            responses = []

            # Include context in first prompt
            context_content = session.context.get_context_content()

            # Build pause point lookup: {prompt_index: message}
            pause_after = {idx: msg for idx, msg in conv.pause_points}

            # Build consult point lookup: {prompt_index: topic}
            consult_after = {idx: topic for idx, topic in conv.consult_points}

            # Process steps (includes prompts, checkpoints, compact, etc.)
            # Fall back to prompts list if no steps defined (backward compat)
            prompt_count = 0
            total_prompts = len(conv.prompts)
            first_prompt = True

            # Initialize workflow progress tracker
            workflow_progress = WorkflowProgress(
                name=str(conv.source_path or target),
                total_cycles=1,  # run command is single cycle
                total_prompts=total_prompts,
                verbosity=verbosity,
            )

            steps_to_process = conv.steps if conv.steps else [
                {"type": "prompt", "content": p} for p in conv.prompts
            ]

            # Process ELIDE directives - merge adjacent steps into single prompts
            steps_to_process = process_elided_steps(steps_to_process)

            for step in steps_to_process:
                step_type = step.type if hasattr(step, 'type') else step.get('type')
                step_content = step.content if hasattr(step, 'content') else step.get('content', '')

                if step_type == "prompt":
                    prompt = step_content
                    prompt_count += 1
                    step_start = time.time()

                    # Get context usage percentage
                    ctx_status = session.context.get_status()
                    context_pct = ctx_status.get("usage_percent", 0)

                    logger.info(f"Sending prompt {prompt_count}/{total_prompts}...")

                    # Use enhanced progress with context %
                    workflow_progress.prompt_sending(
                        cycle=1, prompt=prompt_count,
                        context_pct=context_pct,
                        preview=prompt[:50] if verbosity >= 1 else None
                    )

                    # Build prompt with prologue/epilogue injection
                    base_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    is_first = (prompt_count == 1)
                    is_last = (prompt_count == total_prompts)
                    injected_prompt = build_prompt_with_injection(
                        prompt, conv.prologues, conv.epilogues,
                        base_path=base_path,
                        variables=template_vars,
                        is_first_prompt=is_first,
                        is_last_prompt=is_last
                    )

                    # Add context to first prompt
                    full_prompt = injected_prompt
                    if first_prompt and context_content:
                        full_prompt = f"{context_content}\n\n{injected_prompt}"

                    # Add stop file instruction on first prompt (Q-002)
                    if first_prompt and not no_stop_file_prologue:
                        stop_file_name = f"STOPAUTOMATION-{nonce}.json"
                        stop_instruction = get_stop_file_instruction(stop_file_name)
                        full_prompt = f"{full_prompt}\n\n{stop_instruction}"

                    if first_prompt:
                        first_prompt = False

                    # Write prompt to stderr if --show-prompt / -P enabled
                    prompt_writer.write_prompt(
                        full_prompt,
                        cycle=1,
                        total_cycles=1,
                        prompt_idx=prompt_count,
                        total_prompts=total_prompts,
                        context_pct=context_pct,
                    )

                    # Stream response
                    logger.debug("Awaiting response...")

                    def on_chunk(chunk: str) -> None:
                        if logger.isEnabledFor(logging.DEBUG) and not json_output:
                            console.print(chunk, end="")

                    response = await ai_adapter.send(
                        adapter_session, full_prompt, on_chunk=on_chunk
                    )

                    if logger.isEnabledFor(logging.DEBUG):
                        console.print()  # Newline after streaming

                    step_elapsed = time.time() - step_start

                    # Sync local context tracking with SDK's actual token count (Q-020 fix)
                    tokens_used, max_tokens = await ai_adapter.get_context_usage(adapter_session)
                    session.context.window.used_tokens = tokens_used
                    session.context.window.max_tokens = max_tokens

                    # Update context usage after response
                    ctx_status = session.context.get_status()
                    new_context_pct = ctx_status.get("usage_percent", 0)

                    # Use enhanced progress completion
                    workflow_progress.prompt_complete(
                        cycle=1, prompt=prompt_count,
                        duration=step_elapsed,
                        context_pct=new_context_pct,
                    )

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
                        # Show resume with SDK session ID (Q-018)
                        if session.sdk_session_id:
                            sid = session.sdk_session_id
                            console.print(
                                f"\n[bold]To resume:[/bold] sdqctl sessions resume {sid}"
                            )
                        else:
                            console.print(
                                f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}"
                            )
                        return  # Session cleanup handled by finally blocks

                    # Check for CONSULT after this prompt
                    if prompt_idx in consult_after:
                        topic = consult_after[prompt_idx]
                        session.state.prompt_index = prompt_count  # Next prompt to resume from
                        session.state.status = "consulting"  # Mark as awaiting consultation

                        # Calculate expiration time if CONSULT-TIMEOUT is set
                        expires_at = None
                        if conv.consult_timeout:
                            from datetime import timedelta

                            from ..core.conversation.utilities import parse_timeout_duration
                            try:
                                timeout_secs = parse_timeout_duration(conv.consult_timeout)
                                expires_at = (
                                    datetime.now(timezone.utc) + timedelta(seconds=timeout_secs)
                                ).isoformat()
                            except ValueError as e:
                                console.print(
                                    f"[yellow]Warning: Invalid CONSULT-TIMEOUT: {e}[/yellow]"
                                )

                        checkpoint_path = session.save_pause_checkpoint(
                            f"CONSULT: {topic}", expires_at=expires_at
                        )

                        console.print(f"\n[yellow]⏸  CONSULT: {topic}[/yellow]")
                        console.print("[dim]Session paused for human consultation.[/dim]")
                        if expires_at:
                            console.print(
                                f"[dim]Expires at: {expires_at} (CONSULT-TIMEOUT: "
                                f"{conv.consult_timeout})[/dim]"
                            )
                        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")

                        # Show resume instructions with SDK session ID (Q-018)
                        if session.sdk_session_id:
                            sid = session.sdk_session_id
                            console.print(
                                f"\n[bold]To resume:[/bold] sdqctl sessions resume {sid}"
                            )
                        elif conv.session_name:
                            console.print(
                                f"\n[bold]To resume:[/bold] copilot --resume "
                                f"{conv.session_name}"
                            )
                        else:
                            console.print(
                                f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}"
                            )

                        msg = "On resume, the agent will proactively present open questions."
                        console.print(f"[dim]{msg}[/dim]")
                        return  # Session cleanup handled by finally blocks

                elif step_type == "merged_prompt":
                    # Handle ELIDE-merged prompts - execute embedded RUN commands
                    merged_content = step_content
                    run_commands = getattr(step, 'run_commands', [])

                    cmd_count = len(run_commands)
                    logger.info(f"🔗 Processing ELIDE-merged prompt with {cmd_count} RUN commands")

                    # Execute embedded RUN commands and replace placeholders
                    for idx, cmd in enumerate(run_commands):
                        placeholder = f"{{{{RUN:{idx}:{cmd}}}}}"

                        logger.info(f"  🔧 RUN: {cmd}")
                        progress(f"  🔧 Running: {cmd[:50]}...")

                        try:
                            run_dir = resolve_run_directory(
                                conv.run_cwd, conv.cwd, conv.source_path
                            )

                            result = _run_subprocess(
                                cmd,
                                allow_shell=conv.allow_shell,
                                timeout=conv.run_timeout,
                                cwd=run_dir,
                                env=conv.run_env if conv.run_env else None,
                            )

                            output_text = result.stdout or ""
                            if result.stderr:
                                output_text += f"\n\n[stderr]\n{result.stderr}"
                            output_text = _truncate_output(output_text, conv.run_output_limit)

                            status_marker = (
                                "" if result.returncode == 0
                                else f" (exit {result.returncode})"
                            )
                            run_output = f"```\n$ {cmd}{status_marker}\n{output_text}\n```"

                        except Exception as e:
                            logger.error(f"  ✗ RUN failed: {e}")
                            run_output = f"```\n$ {cmd} (failed)\nError: {e}\n```"

                        merged_content = merged_content.replace(placeholder, run_output)

                    # Now send the merged prompt as a single prompt
                    prompt = merged_content
                    prompt_count += 1
                    step_start = time.time()

                    ctx_status = session.context.get_status()
                    context_pct = ctx_status.get("usage_percent", 0)

                    logger.info(f"Sending merged prompt {prompt_count}/{total_prompts}...")

                    workflow_progress.prompt_sending(
                        cycle=1, prompt=prompt_count,
                        context_pct=context_pct,
                        preview=f"[merged] {prompt[:40]}..." if verbosity >= 1 else None
                    )

                    # Build with prologue/epilogue
                    base_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    is_first = (prompt_count == 1)
                    is_last = (prompt_count == total_prompts)
                    injected_prompt = build_prompt_with_injection(
                        prompt, conv.prologues, conv.epilogues,
                        base_path=base_path,
                        variables=template_vars,
                        is_first_prompt=is_first,
                        is_last_prompt=is_last
                    )

                    full_prompt = injected_prompt
                    if first_prompt and context_content:
                        full_prompt = f"{context_content}\n\n{injected_prompt}"

                    if first_prompt and not no_stop_file_prologue:
                        stop_file_name = f"STOPAUTOMATION-{nonce}.json"
                        stop_instruction = get_stop_file_instruction(stop_file_name)
                        full_prompt = f"{full_prompt}\n\n{stop_instruction}"

                    if first_prompt:
                        first_prompt = False

                    prompt_writer.write_prompt(
                        full_prompt,
                        cycle=1,
                        total_cycles=1,
                        prompt_idx=prompt_count,
                        total_prompts=total_prompts,
                        context_pct=context_pct,
                    )

                    logger.debug("Awaiting response...")

                    def on_chunk(chunk: str) -> None:
                        if logger.isEnabledFor(logging.DEBUG) and not json_output:
                            console.print(chunk, end="")

                    response = await ai_adapter.send(
                        adapter_session, full_prompt, on_chunk=on_chunk
                    )

                    if logger.isEnabledFor(logging.DEBUG):
                        console.print()

                    step_elapsed = time.time() - step_start

                    # Sync local context tracking with SDK's actual token count (Q-020 fix)
                    tokens_used, max_tokens = await ai_adapter.get_context_usage(adapter_session)
                    session.context.window.used_tokens = tokens_used
                    session.context.window.max_tokens = max_tokens

                    ctx_status = session.context.get_status()
                    new_context_pct = ctx_status.get("usage_percent", 0)

                    workflow_progress.prompt_complete(
                        cycle=1, prompt=prompt_count,
                        duration=step_elapsed,
                        context_pct=new_context_pct,
                    )

                    responses.append(response)
                    session.add_message("user", f"[merged prompt]\n{prompt}")
                    session.add_message("assistant", response)

                elif step_type == "checkpoint":
                    # Save session state and commit outputs to git
                    ckpt_idx = len(session.state.checkpoints) + 1
                    checkpoint_name = step_content or f"checkpoint-{ckpt_idx}"

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
                    session.create_checkpoint(checkpoint_name)

                    # Commit to git
                    output_path = Path(conv.output_file) if conv.output_file else None
                    output_dir = Path(conv.output_dir) if conv.output_dir else None

                    if git_commit_checkpoint(checkpoint_name, output_path, output_dir):
                        console.print(f"[green]✓ Git commit: checkpoint: {checkpoint_name}[/green]")
                        progress("  ✓ Git commit created")
                    else:
                        logger.debug("No git changes to commit")

                elif step_type == "compact":
                    # Request compaction from the AI (conditional on threshold)
                    if session.needs_compaction(min_compaction_density):
                        logger.info("🗜  COMPACTING conversation...")
                        progress("  🗜  Compacting conversation...")

                        preserve = step.preserve if hasattr(step, 'preserve') else []
                        compact_prompt = session.get_compaction_prompt()
                        if preserve:
                            preserve_list = ', '.join(preserve)
                            compact_prompt = (
                                f"Preserve these items: {preserve_list}\n\n{compact_prompt}"
                            )

                        response = await ai_adapter.send(adapter_session, compact_prompt)
                        session.add_message("system", f"[Compaction summary]\n{response}")

                        # Sync local context tracking with SDK's actual token count
                        tokens_after, _ = await ai_adapter.get_context_usage(adapter_session)
                        session.context.window.used_tokens = tokens_after

                        logger.debug("Conversation compacted")
                        progress("  🗜  Compaction complete")
                    else:
                        logger.info("📊 Skipping COMPACT - context below threshold")
                        progress("  📊 Skipping COMPACT - context below threshold")

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
                    result = await execute_run_step(
                        step, conv, session, ai_adapter, adapter_session,
                        console, progress, first_prompt, _run_subprocess
                    )
                    if result is False:
                        return  # Stop execution

                elif step_type == "run_async":
                    execute_run_async_step(step, conv, session, progress)

                elif step_type == "run_wait":
                    execute_run_wait_step(step, progress)

                elif step_type == "verify":
                    execute_verify_step(step, conv, session, progress)

                elif step_type == "verify_trace":
                    execute_verify_trace_step(step, conv, progress)

                elif step_type == "verify_coverage":
                    execute_verify_coverage_step(step, conv, progress)

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
                # Use conv.output_file which includes both CLI override and workflow OUTPUT-FILE
                effective_output = conv.output_file
                if effective_output:
                    # Substitute template variables in output path
                    effective_output = substitute_template_variables(
                        effective_output, output_vars
                    )
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
            # Export events before destroying session (if configured via CLI or workflow)
            if effective_event_log and hasattr(ai_adapter, 'export_events'):
                event_count = ai_adapter.export_events(adapter_session, effective_event_log)
                if event_count > 0:
                    logger.info(f"Exported {event_count} events to {effective_event_log}")
                    progress(f"  📋 Exported {event_count} events to {effective_event_log}")

            # Always destroy session (handles both success and error paths)
            await ai_adapter.destroy_session(adapter_session)

    except Exception as e:
        session.state.status = "failed"
        console.print(f"[red]Error: {e}[/red]")
        raise

    finally:
        # Cleanup RUN-ASYNC background processes to prevent orphans
        if conv.async_processes:
            for cmd, proc in conv.async_processes:
                if proc.poll() is None:  # Still running
                    logger.info(f"Terminating background process PID {proc.pid}: {cmd[:50]}")
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Force killing PID {proc.pid}")
                        proc.kill()
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to cleanup PID {proc.pid}: {cleanup_err}")
            conv.async_processes.clear()

        await ai_adapter.stop()
