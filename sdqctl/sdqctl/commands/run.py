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
from ..core.conversation import ConversationFile, substitute_template_variables
from ..core.exceptions import ExitCode, MissingContextFiles
from ..core.logging import get_logger
from ..core.loop_detector import get_stop_file_instruction
from ..core.progress import WorkflowProgress, progress
from ..core.session import Session
from ..utils.output import PromptWriter, handle_error, print_json_error
from .utils import run_async

logger = get_logger(__name__)


def _run_subprocess(
    command: str,
    allow_shell: bool,
    timeout: int,
    cwd: Path,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Execute a subprocess with consistent settings.

    Args:
        command: Command string to execute
        allow_shell: If True, use shell=True (allows pipes, redirects)
        timeout: Timeout in seconds
        cwd: Working directory for command
        env: Additional environment variables (merged with os.environ)

    Returns:
        CompletedProcess with stdout/stderr captured as text
    """
    import os

    # Merge env with current environment (env overrides)
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)

    args = command if allow_shell else shlex.split(command)
    return subprocess.run(
        args,
        shell=allow_shell,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        env=run_env,
    )


def _truncate_output(text: str, limit: Optional[int]) -> str:
    """Truncate output to limit if set.

    Args:
        text: Output text to potentially truncate
        limit: Max characters (None = no limit)

    Returns:
        Original text or truncated text with marker
    """
    if limit is None or len(text) <= limit:
        return text
    # Keep first half and last quarter, with truncation marker
    head_size = limit * 2 // 3
    tail_size = limit // 3
    truncated = len(text) - limit
    return f"{text[:head_size]}\n\n[... {truncated} chars truncated ...]\n\n{text[-tail_size:]}"


async def _execute_block_steps(
    steps: list,
    conv: ConversationFile,
    session,
    ai_adapter,
    adapter_session,
    console,
    progress_fn,
    first_prompt: bool,
) -> None:
    """Execute steps inside an ON-FAILURE or ON-SUCCESS block.

    Handles a subset of step types appropriate for blocks:
    - prompt: Send to AI
    - run: Execute command (no nested blocks, no retry)
    - checkpoint: Save state
    - compact: Compress context
    - pause: Wait for user

    Args:
        steps: List of ConversationStep objects to execute
        conv: Parent ConversationFile for settings
        session: Current Session object
        ai_adapter: Adapter for AI communication
        adapter_session: Current adapter session
        console: Rich console for output
        progress_fn: Progress callback function
        first_prompt: Whether this is the first prompt in session
    """
    for block_step in steps:
        step_type = block_step.type
        step_content = block_step.content if hasattr(block_step, 'content') else ""

        if step_type == "prompt":
            # Send prompt to AI
            logger.info(f"  📝 Block PROMPT: {step_content[:50]}...")
            progress_fn("    📝 Block prompt...")

            response = await ai_adapter.send(adapter_session, step_content)
            session.add_message("assistant", response)

            # Display response
            console.print(Panel(Markdown(response), title="[cyan]AI Response (Block)[/cyan]"))

        elif step_type == "run":
            # Execute command (simplified, no nested blocks or retry)
            command = step_content
            logger.info(f"  🔧 Block RUN: {command}")
            progress_fn(f"    🔧 Running: {command[:40]}...")

            try:
                run_dir = Path(conv.cwd) if conv.cwd else Path.cwd()
                result = subprocess.run(
                    command if conv.allow_shell else shlex.split(command),
                    shell=conv.allow_shell,
                    capture_output=True,
                    text=True,
                    timeout=conv.run_timeout,
                    cwd=run_dir,
                )

                if result.returncode == 0:
                    logger.info("    ✓ Block RUN succeeded")
                    progress_fn("    ✓ Command succeeded")
                else:
                    logger.warning(f"    ✗ Block RUN failed (exit {result.returncode})")
                    progress_fn(f"    ✗ Command failed (exit {result.returncode})")

                # Add output to context
                if result.stdout or result.stderr:
                    output_text = result.stdout or ""
                    if result.stderr:
                        output_text += f"\n[stderr]\n{result.stderr}"
                    output_text = _truncate_output(output_text, conv.run_output_limit)
                    run_msg = f"[Block RUN output]\n```\n$ {command}\n{output_text}\n```"
                    session.add_message("system", run_msg)

            except subprocess.TimeoutExpired:
                logger.error("    ✗ Block RUN timed out")
                progress_fn(f"    ✗ Timeout after {conv.run_timeout}s")
            except Exception as e:
                logger.error(f"    ✗ Block RUN error: {e}")
                progress_fn(f"    ✗ Error: {e}")

        elif step_type == "checkpoint":
            checkpoint_name = step_content or "block-checkpoint"
            logger.info(f"  💾 Block CHECKPOINT: {checkpoint_name}")
            progress_fn(f"    💾 Checkpoint: {checkpoint_name}")
            session.save_pause_checkpoint(checkpoint_name)

        elif step_type == "compact":
            logger.info("  🗜  Block COMPACT")
            progress_fn("    🗜  Compacting...")
            compact_prompt = "Summarize the conversation so far, preserving key context."
            response = await ai_adapter.send(adapter_session, compact_prompt)
            session.add_message("system", f"[Compaction summary]\n{response}")

        elif step_type == "pause":
            pause_msg = "⏸  Paused by ON-FAILURE/ON-SUCCESS block. Press Enter to continue..."
            console.print(f"[yellow]{pause_msg}[/yellow]")
            input()

        elif step_type == "consult":
            topic = step_content or "Open Questions"
            console.print(f"[yellow]⏸  CONSULT: {topic}[/yellow]")
            console.print("[dim]Consultation required. Press Enter to continue...[/dim]")
            input()


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


def process_elided_steps(steps: list) -> list:
    """Process ELIDE directives by merging adjacent steps into single prompts.

    ELIDE merges the element above with the element below into a single prompt,
    avoiding an agent turn between them. This is useful for combining test output
    with error-fixing instructions, or context with instructions.

    Example:
        PROMPT Analyze the test results below.
        RUN pytest tests/ -v
        ELIDE
        PROMPT Fix any failing tests you find.

    Becomes a single merged prompt with test output injected.

    Args:
        steps: List of ConversationStep objects or dicts

    Returns:
        List of merged steps with ELIDE markers removed
    """
    if not steps:
        return steps

    def get_type(step) -> str:
        return step.type if hasattr(step, 'type') else step.get('type', '')

    def get_content(step) -> str:
        return step.content if hasattr(step, 'content') else step.get('content', '')

    # Find ELIDE positions and build merged groups
    # A group is a list of consecutive steps connected by ELIDE
    groups = []
    current_group = []

    for step in steps:
        step_type = get_type(step)

        if step_type == "elide":
            # ELIDE marks that we should continue the current group
            # If current_group is empty, start with previous group's last item
            continue
        else:
            # Check if this step should be merged with the previous group
            # by looking back to see if the previous non-elide step was followed by ELIDE
            should_merge = False
            if current_group:
                # Look back in original steps to see if there was an ELIDE between
                for i, s in enumerate(steps):
                    if s is step:
                        # Found current step, look backwards for ELIDE
                        j = i - 1
                        while j >= 0:
                            if get_type(steps[j]) == "elide":
                                should_merge = True
                                break
                            elif get_type(steps[j]) != "elide":
                                break
                            j -= 1
                        break

            if should_merge:
                current_group.append(step)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [step]

    if current_group:
        groups.append(current_group)

    # Now merge each group into a single step
    from ..core.conversation import ConversationStep
    merged_steps = []

    for group in groups:
        if len(group) == 1:
            # No merging needed
            merged_steps.append(group[0])
        else:
            # Merge multiple steps into a single merged prompt step
            # Combine prompts, run outputs become placeholders for later injection
            merged_contents = []
            merged_run_commands = []
            has_prompt = False

            for step in group:
                step_type = get_type(step)
                content = get_content(step)

                if step_type == "prompt":
                    merged_contents.append(content)
                    has_prompt = True
                elif step_type == "run":
                    # Store RUN command to be executed and output injected
                    merged_run_commands.append(content)
                    # Add placeholder that will be replaced with output
                    merged_contents.append(f"{{{{RUN:{len(merged_run_commands) - 1}:{content}}}}}")
                elif step_type in ("checkpoint", "compact", "new_conversation"):
                    # Control steps break the merge - shouldn't happen in valid ELIDE usage
                    logger.warning(f"ELIDE cannot merge control step type '{step_type}'")
                    # Add as-is for now
                    merged_steps.append(step)
                    continue

            if has_prompt or merged_contents:
                merged_step = ConversationStep(
                    type="merged_prompt",
                    content="\n\n".join(merged_contents),
                )
                # Attach run commands for later execution
                merged_step.run_commands = merged_run_commands  # type: ignore
                merged_steps.append(merged_step)

    logger.debug(f"Processed {len(steps)} steps with ELIDE into {len(merged_steps)} merged steps")
    return merged_steps


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
        console.print("[yellow]⚠ --render-only is deprecated. Use: sdqctl render run workflow.conv[/yellow]")

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
                console.print("[dim]Tip: Use VALIDATION-MODE lenient or --allow-missing to continue[/dim]")
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
                adapter_session = await ai_adapter.resume_session(effective_session_name, adapter_config)
                logger.info(f"Resumed session: {effective_session_name}")
                if verbosity > 0:
                    console.print(f"[dim]Resumed session: {effective_session_name}[/dim]")
            except Exception as e:
                # Session doesn't exist, create new with session name
                # Note: SDK may not support named session creation directly,
                # so we create a regular session and track the name
                logger.debug(f"Could not resume session '{effective_session_name}': {e}, creating new")
                adapter_session = await ai_adapter.create_session(adapter_config)
                if verbosity > 0:
                    console.print(f"[dim]Created new session: {effective_session_name}[/dim]")
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

                    response = await ai_adapter.send(adapter_session, full_prompt, on_chunk=on_chunk)

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
                            console.print(f"\n[bold]To resume:[/bold] sdqctl sessions resume {session.sdk_session_id}")
                        else:
                            console.print(f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}")
                        return  # Session cleanup handled by finally blocks

                    # Check for CONSULT after this prompt
                    if prompt_idx in consult_after:
                        topic = consult_after[prompt_idx]
                        session.state.prompt_index = prompt_count  # Next prompt to resume from
                        session.state.status = "consulting"  # Mark as awaiting consultation
                        checkpoint_path = session.save_pause_checkpoint(f"CONSULT: {topic}")

                        console.print(f"\n[yellow]⏸  CONSULT: {topic}[/yellow]")
                        console.print("[dim]Session paused for human consultation.[/dim]")
                        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")

                        # Show resume instructions with SDK session ID (Q-018)
                        if session.sdk_session_id:
                            console.print(f"\n[bold]To resume:[/bold] sdqctl sessions resume {session.sdk_session_id}")
                        elif conv.session_name:
                            console.print(f"\n[bold]To resume:[/bold] copilot --resume {conv.session_name}")
                        else:
                            console.print(f"\n[bold]To resume:[/bold] sdqctl resume {checkpoint_path}")

                        console.print("[dim]On resume, the agent will proactively present open questions.[/dim]")
                        return  # Session cleanup handled by finally blocks

                elif step_type == "merged_prompt":
                    # Handle ELIDE-merged prompts - execute embedded RUN commands and send as single prompt
                    merged_content = step_content
                    run_commands = getattr(step, 'run_commands', [])

                    logger.info(f"🔗 Processing ELIDE-merged prompt with {len(run_commands)} embedded RUN commands")

                    # Execute embedded RUN commands and replace placeholders
                    for idx, cmd in enumerate(run_commands):
                        placeholder = f"{{{{RUN:{idx}:{cmd}}}}}"

                        logger.info(f"  🔧 RUN: {cmd}")
                        progress(f"  🔧 Running: {cmd[:50]}...")

                        try:
                            # Determine working directory
                            if conv.run_cwd:
                                run_dir = Path(conv.run_cwd)
                                if not run_dir.is_absolute():
                                    base = conv.source_path.parent if conv.source_path else Path.cwd()
                                    run_dir = base / run_dir
                            elif conv.cwd:
                                run_dir = Path(conv.cwd)
                            else:
                                run_dir = Path.cwd()

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

                            status_marker = "" if result.returncode == 0 else f" (exit {result.returncode})"
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

                    response = await ai_adapter.send(adapter_session, full_prompt, on_chunk=on_chunk)

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
                            compact_prompt = f"Preserve these items: {', '.join(preserve)}\n\n{compact_prompt}"

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
                    # Execute shell command (with optional retry-with-AI-fix)
                    command = step_content
                    retry_count = getattr(step, 'retry_count', 0) if hasattr(step, 'retry_count') else 0
                    retry_prompt = getattr(step, 'retry_prompt', '') if hasattr(step, 'retry_prompt') else ''

                    max_attempts = retry_count + 1  # retry_count is number of retries AFTER first attempt
                    attempt = 0
                    last_result = None

                    while attempt < max_attempts:
                        attempt += 1
                        is_retry = attempt > 1

                        if is_retry:
                            logger.info(f"🔄 RUN-RETRY attempt {attempt}/{max_attempts}: {command}")
                            progress(f"  🔄 Retry {attempt}/{max_attempts}: {command[:40]}...")
                        else:
                            logger.info(f"🔧 RUN: {command}")
                            progress(f"  🔧 Running: {command[:50]}...")

                        run_start = time.time()
                        try:
                            # Determine working directory: run_cwd overrides cwd
                            if conv.run_cwd:
                                run_dir = Path(conv.run_cwd)
                                if not run_dir.is_absolute():
                                    base = conv.source_path.parent if conv.source_path else Path.cwd()
                                    run_dir = base / run_dir
                            elif conv.cwd:
                                run_dir = Path(conv.cwd)
                            else:
                                run_dir = Path.cwd()

                            result = _run_subprocess(
                                command,
                                allow_shell=conv.allow_shell,
                                timeout=conv.run_timeout,
                                cwd=run_dir,
                                env=conv.run_env if conv.run_env else None,
                            )
                            run_elapsed = time.time() - run_start
                            last_result = result

                            if result.returncode == 0:
                                logger.info(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                                progress(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                                break  # Success - exit retry loop
                            else:
                                logger.warning(f"  ✗ Command failed with exit code {result.returncode}")
                                progress(f"  ✗ Command failed (exit {result.returncode})")

                                # If retries remaining, send to AI for fix
                                if retry_count > 0 and attempt < max_attempts:
                                    # Capture error output for AI
                                    error_output = result.stdout or ""
                                    if result.stderr:
                                        error_output += f"\n\n[stderr]\n{result.stderr}"
                                    error_output = _truncate_output(error_output, conv.run_output_limit)

                                    # Build retry prompt for AI
                                    full_retry_prompt = f"""{retry_prompt}

Command that failed:
```
$ {command}
{error_output}
```

Exit code: {result.returncode}

Please analyze the error and make necessary fixes. After fixing, the command will be retried automatically."""

                                    logger.info("  📤 Sending error to AI for fix...")
                                    progress("  📤 Asking AI to fix...")

                                    # Send to AI and wait for response
                                    try:
                                        retry_response = run_async(ai_adapter.run(
                                            adapter_session,
                                            full_retry_prompt,
                                            restrictions=conv.file_restrictions,
                                            stream=True,
                                        ))
                                        if retry_response:
                                            logger.info(f"  📥 AI fix response received ({len(retry_response)} chars)")
                                            progress("  📥 AI response received, retrying...")
                                            # Add AI response to session context
                                            session.add_message("assistant", retry_response)
                                    except Exception as ai_err:
                                        logger.error(f"  ✗ AI fix request failed: {ai_err}")
                                        progress(f"  ✗ AI request failed: {ai_err}")
                                        break  # Can't retry without AI, exit loop

                                    continue  # Retry the command

                        except subprocess.TimeoutExpired as e:
                            logger.error(f"  ✗ Command timed out after {conv.run_timeout}s")
                            progress(f"  ✗ Command timed out after {conv.run_timeout}s")
                            # Timeout - no retry (complex to handle)
                            last_result = type('Result', (), {
                                'returncode': -1,
                                'stdout': e.stdout or '',
                                'stderr': e.stderr or f'Timeout after {conv.run_timeout}s'
                            })()
                            break

                        except Exception as e:
                            logger.error(f"  ✗ Command error: {e}")
                            last_result = type('Result', (), {
                                'returncode': -1,
                                'stdout': '',
                                'stderr': str(e)
                            })()
                            break

                    # After retry loop, handle final result
                    if last_result:
                        include_output = (
                            conv.run_output == "always" or
                            (conv.run_output == "on-error" and last_result.returncode != 0)
                        )

                        if include_output:
                            output_text = last_result.stdout or ""
                            if last_result.stderr:
                                output_text += f"\n\n[stderr]\n{last_result.stderr}"
                            output_text = _truncate_output(output_text, conv.run_output_limit)

                            if output_text.strip():
                                status_marker = "" if last_result.returncode == 0 else f" (exit {last_result.returncode})"
                                retry_marker = f" [after {attempt} attempt(s)]" if retry_count > 0 else ""
                                run_context = f"```\n$ {command}{status_marker}{retry_marker}\n{output_text}\n```"
                                session.add_message("system", f"[RUN output]\n{run_context}")
                                logger.debug(f"Added RUN output to context ({len(output_text)} chars)")

                        # Execute ON-FAILURE or ON-SUCCESS blocks if present
                        if last_result.returncode != 0 and step.on_failure:
                            logger.info("🔀 Executing ON-FAILURE block")
                            progress("  🔀 Running ON-FAILURE steps...")
                            await _execute_block_steps(
                                step.on_failure, conv, session, ai_adapter, adapter_session,
                                console, progress, first_prompt
                            )
                        elif last_result.returncode == 0 and step.on_success:
                            logger.info("🔀 Executing ON-SUCCESS block")
                            progress("  🔀 Running ON-SUCCESS steps...")
                            await _execute_block_steps(
                                step.on_success, conv, session, ai_adapter, adapter_session,
                                console, progress, first_prompt
                            )

                        # Handle stop-on-error AFTER capturing output, blocks, and exhausting retries
                        # Only stop if no ON-FAILURE block was present (block handles the failure)
                        if last_result.returncode != 0 and conv.run_on_error == "stop" and not step.on_failure:
                            retry_msg = f" after {attempt} attempts" if retry_count > 0 else ""
                            console.print(f"[red]RUN failed{retry_msg}: {command}[/red]")
                            console.print(f"[dim]Exit code: {last_result.returncode}[/dim]")
                            if last_result.stderr:
                                console.print(f"[dim]stderr: {last_result.stderr[:500]}[/dim]")
                            session.state.status = "failed"
                            checkpoint_path = session.save_pause_checkpoint(f"RUN failed: {command} (exit {last_result.returncode})")
                            console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                            return

                elif step_type == "run_async":
                    # Execute command in background without waiting
                    command = step_content
                    logger.info(f"🔧 RUN-ASYNC: {command}")
                    progress(f"  🔧 Starting background: {command[:50]}...")

                    # Determine working directory
                    if conv.run_cwd:
                        run_dir = Path(conv.run_cwd)
                        if not run_dir.is_absolute():
                            base = conv.source_path.parent if conv.source_path else Path.cwd()
                            run_dir = base / run_dir
                    elif conv.cwd:
                        run_dir = Path(conv.cwd)
                    else:
                        run_dir = Path.cwd()

                    # Build environment
                    run_env = None
                    if conv.run_env:
                        import os
                        run_env = os.environ.copy()
                        run_env.update(conv.run_env)

                    # Start process in background
                    args = command if conv.allow_shell else shlex.split(command)
                    proc = subprocess.Popen(
                        args,
                        shell=conv.allow_shell,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=run_dir,
                        env=run_env,
                    )
                    conv.async_processes.append((command, proc))
                    logger.info(f"  ✓ Background process started (PID {proc.pid})")
                    progress(f"  ✓ Background process started (PID {proc.pid})")
                    session.add_message("system", f"[RUN-ASYNC started]\n$ {command} (PID {proc.pid})")

                elif step_type == "run_wait":
                    # Wait/sleep for specified duration
                    wait_spec = step_content.strip().lower()
                    logger.info(f"⏱️ RUN-WAIT: {wait_spec}")

                    # Parse duration: "5", "5s", "1m", "500ms"
                    if wait_spec.endswith("ms"):
                        wait_seconds = float(wait_spec[:-2]) / 1000
                    elif wait_spec.endswith("m"):
                        wait_seconds = float(wait_spec[:-1]) * 60
                    elif wait_spec.endswith("s"):
                        wait_seconds = float(wait_spec[:-1])
                    else:
                        wait_seconds = float(wait_spec)

                    progress(f"  ⏱️ Waiting {wait_seconds}s...")
                    time.sleep(wait_seconds)
                    logger.info("  ✓ Wait complete")
                    progress("  ✓ Wait complete")

                elif step_type == "verify":
                    # Run verification step
                    from ..verifiers import VERIFIERS

                    verify_type = step.verify_type if hasattr(step, 'verify_type') else step.get('verify_type', 'all')
                    verify_options = step.verify_options if hasattr(step, 'verify_options') else step.get('verify_options', {})

                    logger.info(f"🔍 VERIFY: {verify_type}")
                    progress(f"  🔍 Verifying: {verify_type}")

                    # Determine path to verify (workflow dir by default)
                    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    if 'path' in verify_options:
                        verify_path = Path(verify_options['path'])

                    # Run appropriate verifier(s)
                    verification_results = []
                    if verify_type == "all":
                        verifier_names = list(VERIFIERS.keys())
                    else:
                        verifier_names = [verify_type]

                    all_passed = True
                    for name in verifier_names:
                        if name in VERIFIERS:
                            verifier = VERIFIERS[name]()
                            result = verifier.verify(verify_path)
                            verification_results.append((name, result))
                            if not result.passed:
                                all_passed = False
                                logger.warning(f"  ✗ {name}: {len(result.errors)} errors")
                            else:
                                logger.info(f"  ✓ {name}: passed")
                        else:
                            logger.warning(f"  ⚠ Unknown verifier: {name}")

                    # Format output for context injection
                    verify_output_lines = ["## Verification Results\n"]
                    for name, result in verification_results:
                        status = "✅ Passed" if result.passed else "❌ Failed"
                        verify_output_lines.append(f"### {name}\n{status}: {result.summary}\n")
                        if result.errors and conv.verify_output in ("always", "on-error"):
                            for err in result.errors[:10]:  # Limit to first 10 errors
                                verify_output_lines.append(f"- ERROR {err.file}:{err.line}: {err.message}")
                            if len(result.errors) > 10:
                                verify_output_lines.append(f"- ... and {len(result.errors) - 10} more errors")

                    verify_output = "\n".join(verify_output_lines)

                    # Apply output limit if set
                    if conv.verify_limit:
                        verify_output = _truncate_output(verify_output, conv.verify_limit)

                    # Inject into session context based on verify_output setting
                    should_inject = (
                        conv.verify_output == "always" or
                        (conv.verify_output == "on-error" and not all_passed)
                    )
                    if should_inject and conv.verify_output != "never":
                        session.add_message("system", verify_output)
                        # Note: verify_output already added to session context above

                    # Handle failure based on verify_on_error setting
                    if not all_passed:
                        if conv.verify_on_error == "fail":
                            raise RuntimeError(f"Verification failed: {verify_type}")
                        elif conv.verify_on_error == "warn":
                            progress(f"  ⚠ Verification warning: {verify_type}")
                        # continue: just proceed

                elif step_type == "verify_trace":
                    # Run VERIFY-TRACE step (check specific trace link)
                    from ..verifiers.traceability import TraceabilityVerifier

                    verify_options = step.verify_options if hasattr(step, 'verify_options') else step.get('verify_options', {})
                    from_id = verify_options.get('from', '')
                    to_id = verify_options.get('to', '')

                    logger.info(f"🔍 VERIFY-TRACE: {from_id} -> {to_id}")
                    progress(f"  🔍 Verifying trace: {from_id} -> {to_id}")

                    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    verifier = TraceabilityVerifier()
                    result = verifier.verify_trace(from_id, to_id, verify_path)

                    if result.passed:
                        logger.info(f"  ✓ Trace verified: {result.summary}")
                    else:
                        logger.warning(f"  ✗ Trace failed: {result.summary}")
                        if conv.verify_on_error == "fail":
                            raise RuntimeError(f"VERIFY-TRACE failed: {from_id} -> {to_id}")
                        elif conv.verify_on_error == "warn":
                            progress("  ⚠ Trace verification warning")

                elif step_type == "verify_coverage":
                    # Run VERIFY-COVERAGE step (check coverage metrics)
                    from ..verifiers.traceability import TraceabilityVerifier

                    verify_options = step.verify_options if hasattr(step, 'verify_options') else step.get('verify_options', {})
                    report_only = verify_options.get('report_only', False)
                    metric = verify_options.get('metric')
                    op = verify_options.get('op')
                    threshold = verify_options.get('threshold')

                    logger.info(f"🔍 VERIFY-COVERAGE: {'report' if report_only else f'{metric} {op} {threshold}'}")
                    progress("  🔍 Verifying coverage")

                    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
                    verifier = TraceabilityVerifier()

                    if report_only:
                        result = verifier.verify_coverage(verify_path)
                    else:
                        result = verifier.verify_coverage(verify_path, metric=metric, op=op, threshold=threshold)

                    if result.passed:
                        logger.info(f"  ✓ Coverage: {result.summary}")
                    else:
                        logger.warning(f"  ✗ Coverage failed: {result.summary}")
                        if conv.verify_on_error == "fail":
                            raise RuntimeError(f"VERIFY-COVERAGE failed: {result.summary}")
                        elif conv.verify_on_error == "warn":
                            progress("  ⚠ Coverage verification warning")

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
                    # Substitute template variables in output path (use output_vars with WORKFLOW_NAME)
                    effective_output = substitute_template_variables(effective_output, output_vars)
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
