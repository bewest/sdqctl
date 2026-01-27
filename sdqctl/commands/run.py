"""
sdqctl run - [DEPRECATED] Execute a single prompt or ConversationFile.

DEPRECATED: Use 'sdqctl iterate' instead. This command forwards to iterate -n 1.

Usage:
    sdqctl iterate "Audit authentication module"
    sdqctl iterate workflow.conv
    sdqctl iterate workflow.conv --adapter copilot --model gpt-4
"""

from typing import Optional

import click

from .blocks import execute_block_steps  # noqa: F401

# Backward-compatible re-exports for tests
from .elide import process_elided_steps  # noqa: F401
from .iterate import iterate
from .utils import run_subprocess, truncate_output  # noqa: F401

# Aliases for internal use (keep _ prefix for backward compat with tests)
_run_subprocess = run_subprocess
_truncate_output = truncate_output
_execute_block_steps = execute_block_steps  # backward compat


@click.command("run", hidden=True)
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
    """[DEPRECATED] Execute a single prompt or ConversationFile.

    This command is deprecated. Use 'sdqctl iterate' instead.

    Examples:

    \b
    # Use iterate instead:
    sdqctl iterate "Audit authentication module"
    sdqctl iterate workflow.conv
    """
    # Emit deprecation warning
    click.secho(
        "⚠ 'sdqctl run' is deprecated. Use 'sdqctl iterate' instead.",
        fg="yellow", err=True
    )

    # Forward to iterate with max_cycles=1
    ctx.invoke(
        iterate,
        targets=(target,),  # Convert single target to tuple
        from_json=None,
        max_cycles=1,  # run is single execution
        session_mode="accumulate",
        adapter=adapter,
        model=model,
        context=context,
        allow_files=allow_files,
        deny_files=deny_files,
        allow_dir=allow_dir,
        deny_dir=deny_dir,
        session_name=session_name,
        checkpoint_dir=None,
        prologue=prologue,
        epilogue=epilogue,
        header=header,
        footer=footer,
        output=output,
        event_log=event_log,
        json_output=json_output,
        dry_run=dry_run,
        render_only=render_only,
        compaction_min=min_compaction_density,  # run's default is 0
        min_compaction_density=None,
        no_infinite_sessions=False,
        compaction_threshold=None,
        compaction_max=None,
        buffer_threshold=None,
        no_stop_file_prologue=no_stop_file_prologue,
        stop_file_nonce=stop_file_nonce,
    )
