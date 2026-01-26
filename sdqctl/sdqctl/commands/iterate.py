"""
sdqctl iterate - Execute a workflow with optional multi-cycle iteration.

Usage:
    sdqctl iterate workflow.conv              # Single execution (default -n 1)
    sdqctl iterate workflow.conv -n 5         # Multi-cycle execution
    sdqctl iterate "Audit this module"        # Inline prompt
    sdqctl iterate workflow.conv -s fresh     # Fresh session each cycle

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
from ..adapters.base import AdapterConfig, InfiniteSessionConfig
from ..core.conversation import ConversationFile
from ..core.exceptions import LoopDetected, LoopReason, MissingContextFiles
from ..core.logging import WorkflowContext, get_logger, set_workflow_context
from ..core.loop_detector import LoopDetector, generate_nonce, get_stop_file_instruction
from ..core.progress import WorkflowProgress
from ..core.progress import progress as progress_print
from ..core.session import Session
from ..utils.output import PromptWriter, handle_error
from .compact_steps import execute_checkpoint_step, execute_compact_step
from .iterate_helpers import (
    SESSION_MODES,
    TURN_SEPARATOR,
    TurnGroup,
    build_infinite_session_config,
    is_workflow_file,
    parse_targets,
    validate_targets,
)
from .utils import run_async
from .verify_steps import execute_verify_coverage_step, execute_verify_trace_step

logger = get_logger(__name__)
console = Console()


@click.command("iterate")
@click.argument("targets", nargs=-1)
@click.option("--from-json", "from_json", type=click.Path(),
              help="Read workflow from JSON file or - for stdin")
@click.option("--max-cycles", "-n", type=int, default=None, help="Override max cycles")
@click.option("--session-mode", "-s", type=click.Choice(["accumulate", "compact", "fresh"]),
              default="accumulate",
              help="accumulate (grow), compact (summarize), fresh (new each cycle)")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--context", "-c", multiple=True, help="Additional context files")
@click.option("--allow-files", multiple=True,
              help="Glob pattern for allowed files (can be repeated)")
@click.option("--deny-files", multiple=True,
              help="Glob pattern for denied files (can be repeated)")
@click.option("--allow-dir", multiple=True, help="Directory to allow (can be repeated)")
@click.option("--deny-dir", multiple=True, help="Directory to deny (can be repeated)")
@click.option("--session-name", default=None,
              help="Named session for resumability (resumes if exists)")
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
@click.option("--min-compaction-density", type=int, default=30,
              help="Skip compaction if context usage below this % (default: 30)")
@click.option("--no-infinite-sessions", is_flag=True,
              help="Disable SDK infinite sessions (use client-side compaction)")
@click.option("--compaction-threshold", type=int, default=80,
              help="Start background compaction at this % (default: 80)")
@click.option("--buffer-threshold", type=int, default=95,
              help="Block until compaction at this % (default: 95)")
@click.option("--no-stop-file-prologue", is_flag=True,
              help="Disable automatic stop file instructions")
@click.option("--stop-file-nonce", default=None,
              help="Override stop file nonce (random if not set)")
@click.pass_context
def iterate(
    ctx: click.Context,
    targets: tuple[str, ...],
    from_json: Optional[str],
    max_cycles: Optional[int],
    session_mode: str,
    adapter: Optional[str],
    model: Optional[str],
    context: tuple[str, ...],
    allow_files: tuple[str, ...],
    deny_files: tuple[str, ...],
    allow_dir: tuple[str, ...],
    deny_dir: tuple[str, ...],
    session_name: Optional[str],
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
    min_compaction_density: int,
    no_infinite_sessions: bool,
    compaction_threshold: int,
    buffer_threshold: int,
    no_stop_file_prologue: bool,
    stop_file_nonce: Optional[str],
) -> None:
    """Execute a workflow with optional multi-cycle iteration.

    TARGETS can be a mix of .conv file paths and inline prompt strings.
    Use --- between items to force separate turns (default: adjacent items elide).
    Maximum one .conv file allowed in mixed mode.

    Examples:

    \b
    # Single .conv file
    sdqctl iterate workflow.conv

    \b
    # Inline prompt
    sdqctl iterate "Audit authentication module"

    \b
    # Multi-cycle execution
    sdqctl iterate workflow.conv -n 5

    \b
    # Mixed: prompts + .conv (items elide at boundaries)
    sdqctl iterate "Setup context" workflow.conv "Final summary"

    \b
    # Mixed with separators (force separate turns)
    sdqctl iterate "First task" --- workflow.conv --- "Separate final task"

    \b
    # Fresh session each cycle
    sdqctl iterate workflow.conv -n 3 -s fresh
    """
    # Parse and validate targets
    groups = parse_targets(targets)
    workflow_path, pre_prompts, post_prompts = validate_targets(groups)

    # Validate: need either targets or --from-json
    if not targets and not from_json:
        raise click.UsageError("Either TARGETS argument(s) or --from-json is required")
    if targets and from_json:
        raise click.UsageError("Cannot use both TARGETS argument(s) and --from-json")

    # Handle --render-only by delegating to render logic
    if render_only:
        import json
        import warnings

        from ..core.renderer import format_rendered_json, format_rendered_markdown, render_workflow

        # Deprecation warning
        warnings.warn(
            "--render-only is deprecated, use 'sdqctl render cycle' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        console.print(
            "[yellow]⚠ --render-only is deprecated. "
            "Use: sdqctl render cycle workflow.conv[/yellow]"
        )

        if not workflow_path:
            raise click.UsageError("--render-only requires a .conv file")

        conv = ConversationFile.from_file(Path(workflow_path))

        # Apply mixed mode prompts as prologues/epilogues
        effective_prologues = list(prologue) + pre_prompts + conv.prologues
        effective_epilogues = conv.epilogues + post_prompts + list(epilogue)
        conv.prologues = effective_prologues
        conv.epilogues = effective_epilogues

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

    # Handle --from-json input
    if from_json:
        import json as json_module
        import sys

        if from_json == "-":
            json_data = json_module.load(sys.stdin)
        else:
            json_data = json_module.loads(Path(from_json).read_text())

        # Validate schema version
        schema_version = json_data.get("schema_version", "1.0")
        major_version = int(schema_version.split(".")[0])
        if major_version > 1:
            raise click.UsageError(f"Unsupported schema version: {schema_version} (max: 1.x)")

        # Get verbosity and show_prompt from context
        verbosity = ctx.obj.get("verbosity", 0) if ctx.obj else 0
        show_prompt_flag = ctx.obj.get("show_prompt", False) if ctx.obj else False
        json_errors = ctx.obj.get("json_errors", False) if ctx.obj else False

        run_async(_cycle_from_json_async(
            json_data, max_cycles, session_mode, adapter, model, checkpoint_dir,
            prologue, epilogue, header, footer,
            output, event_log, json_output, dry_run, no_stop_file_prologue, stop_file_nonce,
            verbosity=verbosity, show_prompt=show_prompt_flag,
            json_errors=json_errors
        ))
        return

    # Get verbosity and show_prompt from context
    verbosity = ctx.obj.get("verbosity", 0) if ctx.obj else 0
    show_prompt_flag = ctx.obj.get("show_prompt", False) if ctx.obj else False
    json_errors = ctx.obj.get("json_errors", False) if ctx.obj else False

    run_async(_cycle_async(
        workflow_path, pre_prompts, post_prompts,
        max_cycles, session_mode, adapter, model,
        context, allow_files, deny_files, allow_dir, deny_dir, session_name,
        checkpoint_dir,
        prologue, epilogue, header, footer,
        output, event_log, json_output, dry_run, no_stop_file_prologue, stop_file_nonce,
        verbosity=verbosity, show_prompt=show_prompt_flag,
        min_compaction_density=min_compaction_density,
        no_infinite_sessions=no_infinite_sessions,
        compaction_threshold=compaction_threshold,
        buffer_threshold=buffer_threshold,
        json_errors=json_errors
    ))


async def _cycle_from_json_async(
    json_data: dict,
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
    no_stop_file_prologue: bool = False,
    stop_file_nonce: Optional[str] = None,
    verbosity: int = 0,
    show_prompt: bool = False,
    min_compaction_density: int = 30,
    no_infinite_sessions: bool = False,
    compaction_threshold: int = 80,
    buffer_threshold: int = 95,
    json_errors: bool = False,
) -> None:
    """Execute workflow from pre-rendered JSON.

    Enables external transformation pipelines:
        sdqctl render cycle foo.conv --json | transform.py | sdqctl cycle --from-json -
    """
    import time

    from ..core.conversation import (
        build_output_with_injection,
        substitute_template_variables,
    )
    from ..core.loop_detector import LoopDetector

    # Initialize prompt writer for stderr output
    prompt_writer = PromptWriter(enabled=show_prompt)

    cycle_start = time.time()
    workflow_name = json_data.get("workflow_name", "json-workflow")

    # Extract configuration from JSON
    conv = ConversationFile.from_rendered_json(json_data)

    # Override with CLI options if provided
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model

    # Apply CLI prologues/epilogues
    if cli_prologues:
        conv.prologues = list(cli_prologues) + conv.prologues
    if cli_epilogues:
        conv.epilogues = list(cli_epilogues) + conv.epilogues
    if cli_headers:
        conv.headers = list(cli_headers)
    if cli_footers:
        conv.footers = list(cli_footers)

    max_cycles = max_cycles_override or json_data.get("max_cycles", conv.max_cycles) or 1

    progress_print(f"Running from JSON ({max_cycles} cycle(s), session={session_mode})...")

    if dry_run:
        console.print(
            f"[dim]Would execute {len(conv.prompts)} prompt(s) "
            f"for {max_cycles} cycle(s)[/dim]"
        )
        console.print(f"[dim]Adapter: {conv.adapter}, Model: {conv.model}[/dim]")
        return

    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Adapter error: {e}[/red]")
        return

    # Create adapter config with infinite sessions (merge CLI + conv file settings)
    infinite_config = build_infinite_session_config(
        no_infinite_sessions, compaction_threshold, buffer_threshold, min_compaction_density,
        conv_infinite_sessions=conv.infinite_sessions,
        conv_compaction_min=conv.compaction_min,
        conv_compaction_threshold=conv.compaction_threshold,
    )
    adapter_config = AdapterConfig(
        model=conv.model,
        event_log_path=event_log_path,
        debug_intents=conv.debug_intents,
        infinite_sessions=infinite_config,
    )

    # Initialize session
    session = Session(workflow=workflow_name)

    # Stop file handling
    stop_file_nonce_value = stop_file_nonce or generate_nonce()
    loop_detector = LoopDetector(
        max_cycles=max_cycles,
        stop_file_nonce=stop_file_nonce_value,
    )

    # Create adapter session
    adapter_session = await ai_adapter.create_session(adapter_config)
    session.sdk_session_id = adapter_session.sdk_session_id  # Q-018 fix

    try:
        responses = []

        for cycle_num in range(1, max_cycles + 1):
            progress_print(f"  Cycle {cycle_num}/{max_cycles}")

            # Check for stop file
            if loop_detector.check_stop_file():
                console.print("[yellow]Stop file detected, exiting[/yellow]")
                break

            # Build prompts for this cycle
            template_vars = json_data.get("template_variables", {}).copy()
            template_vars["CYCLE_NUMBER"] = str(cycle_num)
            template_vars["CYCLE_TOTAL"] = str(max_cycles)
            template_vars["STOP_FILE"] = f"STOPAUTOMATION-{stop_file_nonce_value}.json"

            for prompt_idx, prompt_text in enumerate(conv.prompts):
                # Substitute any remaining template variables
                final_prompt = substitute_template_variables(prompt_text, template_vars)

                # Add stop file instruction to first prompt
                if prompt_idx == 0 and cycle_num == 1 and not no_stop_file_prologue:
                    stop_instruction = get_stop_file_instruction(stop_file_nonce_value)
                    final_prompt = f"{stop_instruction}\n\n{final_prompt}"

                # Show prompt if enabled
                prompt_writer.write_prompt(
                    final_prompt,
                    cycle=cycle_num,
                    total_cycles=max_cycles,
                    prompt_num=prompt_idx + 1,
                    total_prompts=len(conv.prompts)
                )

                # Execute prompt
                response = await ai_adapter.run(
                    adapter_session,
                    final_prompt,
                    stream=verbosity >= 2,
                )
                responses.append(response)

                # Add to session
                session.add_message("user", final_prompt)
                session.add_message("assistant", response)

            # Handle session mode
            if session_mode == "compact" and cycle_num < max_cycles:
                progress_print("    Compacting...")
                await ai_adapter.compact(adapter_session)
            elif session_mode == "fresh" and cycle_num < max_cycles:
                progress_print("    Fresh session...")
                adapter_session = await ai_adapter.create_session(adapter_config)

        # Output
        session.state.status = "completed"
        total_elapsed = time.time() - cycle_start

        raw_output = "\n\n---\n\n".join(responses)
        final_output = build_output_with_injection(
            raw_output, conv.headers, conv.footers,
            base_path=Path.cwd(),
            variables=template_vars
        )

        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            Path(output_file).write_text(final_output)
            console.print(f"[green]Output written to {output_file}[/green]")
        else:
            console.print(final_output)

        progress_print(f"  Completed in {total_elapsed:.1f}s")

    finally:
        await ai_adapter.close_session(adapter_session)


async def _cycle_async(
    workflow_path: Optional[str],
    pre_prompts: list[str],
    post_prompts: list[str],
    max_cycles_override: Optional[int],
    session_mode: str,
    adapter_name: Optional[str],
    model: Optional[str],
    extra_context: tuple[str, ...],
    allow_files: tuple[str, ...],
    deny_files: tuple[str, ...],
    allow_dir: tuple[str, ...],
    deny_dir: tuple[str, ...],
    session_name: Optional[str],
    checkpoint_dir: Optional[str],
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
    min_compaction_density: int = 30,
    no_infinite_sessions: bool = False,
    compaction_threshold: int = 80,
    buffer_threshold: int = 95,
    json_errors: bool = False,
) -> None:
    """Execute multi-cycle workflow with session management.

    Supports mixed mode: inline prompts can be combined with a .conv file.
    Pre-prompts elide into the first turn, post-prompts into the last.

    Session modes control how context is managed across cycles:

    - accumulate: Keep full conversation history. Compaction only triggers
      when approaching the context limit. Use for iterative refinement.

    - compact: Summarize conversation after each cycle to reduce tokens.
      Maintains session continuity while managing context growth.

    - fresh: Create new adapter session each cycle. Reloads CONTEXT files
      from disk, so file changes made during cycle N are visible in N+1.
    """
    # Initialize prompt writer for stderr output
    prompt_writer = PromptWriter(enabled=show_prompt)

    import time

    from ..core.conversation import (
        build_output_with_injection,
        build_prompt_with_injection,
        get_standard_variables,
        substitute_template_variables,
    )
    cycle_start = time.time()

    # Handle mixed mode: load .conv file or create from inline prompts
    if workflow_path:
        # Load workflow file
        conv = ConversationFile.from_file(Path(workflow_path))
        progress_print(
            f"Running {Path(workflow_path).name} "
            f"(cycle mode, session={session_mode})..."
        )
    else:
        # Pure inline prompt mode - combine pre_prompts and post_prompts as single prompt
        all_prompts = pre_prompts + post_prompts
        if not all_prompts:
            raise click.UsageError("No prompts provided")
        conv = ConversationFile(
            prompts=all_prompts,
            adapter=adapter_name or "copilot",
            model=model or "gpt-4",
        )
        progress_print(f"Running inline prompt(s) (cycle mode, session={session_mode})...")

    # Validate mandatory context files before execution
    # Respect VALIDATION-MODE directive from the workflow file
    is_lenient = conv.validation_mode == "lenient"
    errors, warnings = conv.validate_context_files(allow_missing=is_lenient)

    # Show warnings
    if warnings:
        console.print("[yellow]Warning: Optional/excluded context files not found:[/yellow]")
        for pattern, resolved in warnings:
            console.print(f"[yellow]  - {pattern}[/yellow]")

    # Errors are blocking
    if errors:
        patterns = [pattern for pattern, _ in errors]
        console.print("[red]Error: Missing mandatory context files:[/red]")
        for pattern, resolved in errors:
            console.print(f"[red]  - {pattern} (resolved to {resolved})[/red]")
        console.print(
            "[dim]Tip: Use VALIDATION-MODE lenient in workflow "
            "or pass --allow-missing[/dim]"
        )
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

    # Mixed mode elision: pre_prompts elide into first turn, post_prompts into last
    # Priority: CLI prologues > pre_prompts > file prologues
    # Priority: file epilogues > post_prompts > CLI epilogues
    effective_prologues = list(cli_prologues) + pre_prompts + conv.prologues
    effective_epilogues = conv.epilogues + post_prompts + list(cli_epilogues)
    conv.prologues = effective_prologues
    conv.epilogues = effective_epilogues

    if cli_headers:
        conv.headers = list(cli_headers) + conv.headers
    if cli_footers:
        conv.footers = list(cli_footers) + conv.footers

    # Add extra context files from CLI (Phase 1 feature from run.py)
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

    # Create session for checkpointing
    session_dir = Path(checkpoint_dir) if checkpoint_dir else None
    session = Session(conv, session_dir=session_dir)

    # Generate nonce for stop file (once per command invocation)
    nonce = stop_file_nonce if stop_file_nonce else generate_nonce()

    # Get template variables for prompts (excludes WORKFLOW_NAME to avoid Q-001)
    # Includes STOP_FILE for agent stop signaling (Q-002)
    template_vars = get_standard_variables(conv.source_path, stop_file_nonce=nonce)
    # Get template variables for output paths (includes WORKFLOW_NAME)
    output_vars = get_standard_variables(conv.source_path, include_workflow_vars=True)

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

    # Initialize loop detector with nonce for stop file detection (Q-002)
    loop_detector = LoopDetector(nonce=nonce)

    # Check if stop file already exists (previous run may have requested stop)
    if loop_detector.stop_file_path.exists():
        try:
            content = loop_detector.stop_file_path.read_text()
            import json
            stop_data = json.loads(content)
            reason = stop_data.get("reason", "Unknown reason")
        except (json.JSONDecodeError, IOError):
            reason = "Could not read stop file content"

        console.print(Panel(
            f"[bold yellow]⚠️  Stop file exists from previous run[/bold yellow]\n\n"
            f"[bold]File:[/bold] {loop_detector.stop_file_name}\n"
            f"[bold]Reason:[/bold] {reason}\n\n"
            f"A previous automation run requested human review.\n"
            f"Please review the agent's work before continuing.\n\n"
            f"[dim]To continue: Remove the stop file and run again[/dim]\n"
            f"[dim]    rm {loop_detector.stop_file_name}[/dim]",
            title="🛑 Review Required",
            border_style="yellow",
        ))
        return

    last_reasoning: list[str] = []  # Collect reasoning from callbacks

    try:
        await ai_adapter.start()

        # Determine effective event log path (CLI overrides workflow)
        effective_event_log = event_log_path or conv.event_log
        if effective_event_log:
            effective_event_log = substitute_template_variables(effective_event_log, template_vars)

        # Build infinite sessions config from CLI options + conv file directives
        infinite_config = build_infinite_session_config(
            no_infinite_sessions, compaction_threshold, buffer_threshold, min_compaction_density,
            conv_infinite_sessions=conv.infinite_sessions,
            conv_compaction_min=conv.compaction_min,
            conv_compaction_threshold=conv.compaction_threshold,
        )

        adapter_config = AdapterConfig(
            model=conv.model,
            streaming=True,
            debug_categories=conv.debug_categories,
            debug_intents=conv.debug_intents,
            event_log=effective_event_log,
            infinite_sessions=infinite_config,
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
                logger.debug(
                    f"Could not resume session '{effective_session_name}': {e}, "
                    "creating new"
                )
                adapter_session = await ai_adapter.create_session(adapter_config)
                if verbosity > 0:
                    console.print(f"[dim]Created new session: {effective_session_name}[/dim]")
        else:
            adapter_session = await ai_adapter.create_session(adapter_config)
        session.sdk_session_id = adapter_session.sdk_session_id  # Q-018 fix

        try:
            session.state.status = "running"
            all_responses = []

            # Set workflow context for enhanced logging
            workflow_name = conv.source_path.stem if conv.source_path else "workflow"
            workflow_ctx = WorkflowContext(
                workflow_name=workflow_name,
                workflow_path=str(conv.source_path) if conv.source_path else None,
                total_cycles=conv.max_cycles,
                total_prompts=len(conv.prompts),
            )
            set_workflow_context(workflow_ctx)

            # Initialize enhanced workflow progress tracker
            workflow_progress = WorkflowProgress(
                name=str(conv.source_path or workflow_path),
                total_cycles=conv.max_cycles,
                total_prompts=len(conv.prompts),
                verbosity=verbosity,
            )

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

                    # Update workflow context for logging
                    workflow_ctx.cycle = cycle_num + 1

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
                                infinite_sessions=infinite_config,
                            )
                        )
                        # Reload CONTEXT files from disk (pick up any changes)
                        session.reload_context()
                        progress_print(f"  🔄 New session for cycle {cycle_num + 1}")

                    # Session mode: compact = compact at start of each cycle (after first)
                    if session_mode == "compact" and cycle_num > 0:
                        console.print(
                            f"\n[yellow]Compacting before cycle {cycle_num + 1}...[/yellow]"
                        )
                        progress_print("  🗜  Compacting context...")

                        compact_result = await ai_adapter.compact(
                            adapter_session,
                            conv.compact_preserve,
                            session.get_compaction_prompt()
                        )

                        tokens_msg = (
                            f"{compact_result.tokens_before} → "
                            f"{compact_result.tokens_after} tokens"
                        )
                        console.print(f"[green]Compacted: {tokens_msg}[/green]")
                        progress_print(f"  🗜  Compacted: {tokens_msg}")

                    # Check for compaction (accumulate mode, or when context limit reached)
                    needs_compact = session.needs_compaction(min_compaction_density)
                    if session_mode == "accumulate" and needs_compact:
                        console.print("\n[yellow]Context near limit, compacting...[/yellow]")
                        progress_print("  🗜  Compacting context...")

                        compact_result = await ai_adapter.compact(
                            adapter_session,
                            conv.compact_preserve,
                            session.get_compaction_prompt()
                        )

                        tokens_msg = (
                            f"{compact_result.tokens_before} → "
                            f"{compact_result.tokens_after} tokens"
                        )
                        console.print(f"[green]Compacted: {tokens_msg}[/green]")
                        progress_print(f"  🗜  Compacted: {tokens_msg}")

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
                        context_content = (
                            session.context.get_context_content()
                            if cycle_num == 0 else ""
                        )

                    # Use steps if available, fallback to prompts for backward compat
                    steps_to_process = conv.steps if conv.steps else [
                        {"type": "prompt", "content": p} for p in conv.prompts
                    ]
                    total_prompts = len(conv.prompts)

                    prompt_idx = 0
                    for step in steps_to_process:
                        step_type = (
                            step.type if hasattr(step, 'type')
                            else step.get('type')
                        )
                        step_content = (
                            step.content if hasattr(step, 'content')
                            else step.get('content', '')
                        )

                        if step_type == "prompt":
                            prompt = step_content
                            session.state.prompt_index = prompt_idx

                            # Update workflow context for logging
                            workflow_ctx.prompt = prompt_idx + 1

                            # Get context usage percentage
                            ctx_status = session.context.get_status()
                            context_pct = ctx_status.get("usage_percent", 0)

                            # Build prompt with prologue/epilogue injection
                            is_first = (prompt_idx == 0)
                            is_last = (prompt_idx == total_prompts - 1)
                            full_prompt = build_prompt_with_injection(
                                prompt, conv.prologues, conv.epilogues,
                                conv.source_path.parent if conv.source_path else None,
                                cycle_vars,
                                is_first_prompt=is_first,
                                is_last_prompt=is_last
                            )

                            # Add context to first prompt (fresh: always, others: cycle 0)
                            if prompt_idx == 0 and context_content:
                                full_prompt = f"{context_content}\n\n{full_prompt}"

                            # Add stop file instruction on first prompt of session (Q-002)
                            # For fresh mode: inject each cycle. For accumulate: only cycle 0.
                            should_inject_stop_file = (
                                not no_stop_file_prologue and
                                prompt_idx == 0 and
                                (session_mode == "fresh" or cycle_num == 0)
                            )
                            if should_inject_stop_file:
                                stop_instr = get_stop_file_instruction(
                                    loop_detector.stop_file_name
                                )
                                full_prompt = f"{full_prompt}\n\n{stop_instr}"

                            # On subsequent cycles (accumulate), add continuation context
                            is_continuation = (
                                session_mode == "accumulate" and
                                cycle_num > 0 and prompt_idx == 0 and
                                conv.on_context_limit_prompt
                            )
                            if is_continuation:
                                full_prompt = (
                                    f"{conv.on_context_limit_prompt}\n\n{full_prompt}"
                                )

                            # Enhanced progress with context %
                            workflow_progress.prompt_sending(
                                cycle=cycle_num + 1,
                                prompt=prompt_idx + 1,
                                context_pct=context_pct,
                                preview=prompt[:50] if verbosity >= 1 else None
                            )

                            # Write prompt to stderr if --show-prompt / -P enabled
                            prompt_writer.write_prompt(
                                full_prompt,
                                cycle=cycle_num + 1,
                                total_cycles=conv.max_cycles,
                                prompt_idx=prompt_idx + 1,
                                total_prompts=total_prompts,
                                context_pct=context_pct,
                            )

                            # Clear reasoning collector before send
                            last_reasoning.clear()

                            def collect_reasoning(reasoning: str) -> None:
                                last_reasoning.append(reasoning)

                            response = await ai_adapter.send(
                                adapter_session,
                                full_prompt,
                                on_reasoning=collect_reasoning
                            )

                            # Sync local context tracking with SDK's token count (Q-020)
                            tokens_used, max_tokens = await ai_adapter.get_context_usage(
                                adapter_session
                            )
                            session.context.window.used_tokens = tokens_used
                            session.context.window.max_tokens = max_tokens

                            # Update context usage after response
                            ctx_status = session.context.get_status()
                            new_context_pct = ctx_status.get("usage_percent", 0)

                            # Enhanced progress completion
                            workflow_progress.prompt_complete(
                                cycle=cycle_num + 1,
                                prompt=prompt_idx + 1,
                                context_pct=new_context_pct,
                            )

                            # Check for loop after each response
                            combined = " ".join(last_reasoning) if last_reasoning else None
                            # Get tool count from turn stats for tool-aware loop detection
                            turn_tools = 0
                            if hasattr(ai_adapter, 'get_session_stats'):
                                stats = ai_adapter.get_session_stats(adapter_session)
                                if stats and stats._send_turn_stats:
                                    turn_tools = stats._send_turn_stats.tool_calls
                            loop_result = loop_detector.check(
                                combined, response, cycle_num, turn_tools
                            )
                            if loop_result:
                                # Special handling for stop file (agent-initiated stop)
                                if loop_result.reason == LoopReason.STOP_FILE:
                                    stop_name = loop_detector.stop_file_name
                                    console.print(
                                        f"\n[yellow]⚠️  Agent requested stop via "
                                        f"{stop_name}[/yellow]"
                                    )
                                    console.print(
                                        f"[yellow]   Reason: {loop_result.details}[/yellow]"
                                    )
                                    console.print(
                                        f"[yellow]   Session: {session.id}[/yellow]"
                                    )
                                    console.print(
                                        f"[yellow]   Cycle: {cycle_num + 1}/"
                                        f"{conv.max_cycles}[/yellow]"
                                    )
                                    console.print(
                                        "\n[dim]Review the agent's work and "
                                        "decide next steps.[/dim]"
                                    )
                                    progress_print(
                                        f"  ⚠️  Agent stop: {loop_result.details}"
                                    )
                                else:
                                    console.print(f"\n[red]⚠️  {loop_result}[/red]")
                                    reason_val = loop_result.reason.value
                                    progress_print(f"  ⚠️  Loop detected: {reason_val}")
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
                            await execute_compact_step(
                                step, conv, session, ai_adapter, adapter_session,
                                min_compaction_density, console, progress_print
                            )

                        elif step_type == "checkpoint":
                            execute_checkpoint_step(
                                step, session, cycle_num, console, progress_print
                            )

                        elif step_type == "verify_trace":
                            execute_verify_trace_step(step, conv, progress_print)

                        elif step_type == "verify_coverage":
                            execute_verify_coverage_step(step, conv, progress_print)

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
                    # Substitute template variables in output path
                    effective_output = substitute_template_variables(
                        conv.output_file, output_vars
                    )

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
        if not json_errors:
            console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
            logger.error(f"Loop detected: {e}")
        exit_code = handle_error(e, json_errors=json_errors, context={
            "workflow": workflow_path,
            "checkpoint": str(checkpoint_path),
        })
        sys.exit(exit_code)

    except MissingContextFiles as e:
        session.state.status = "failed"
        # Save checkpoint to preserve session state before exit
        checkpoint_path = session.save_pause_checkpoint(f"Missing context files: {e.files}")
        if not json_errors:
            console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
            logger.error(f"Missing files: {e}")
        exit_code = handle_error(e, json_errors=json_errors, context={
            "workflow": workflow_path,
            "checkpoint": str(checkpoint_path),
        })
        sys.exit(exit_code)

    except Exception as e:
        session.state.status = "failed"
        # Save checkpoint to preserve session state before exit
        checkpoint_path = session.save_pause_checkpoint(f"Error: {e}")
        if json_errors:
            exit_code = handle_error(e, json_errors=True, context={
                "workflow": workflow_path,
                "checkpoint": str(checkpoint_path),
            })
            sys.exit(exit_code)
        else:
            console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
            console.print(f"[red]Error: {e}[/red]")
            raise

    finally:
        # Clear workflow context
        set_workflow_context(None)
        await ai_adapter.stop()
