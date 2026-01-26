"""
Output and error handling for iterate command.

Handles output file writing, completion display, and error handling
with checkpoint preservation.
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from rich.console import Console

from ..core.conversation import build_output_with_injection, substitute_template_variables
from ..core.exceptions import LoopDetected, MissingContextFiles
from ..utils.output import handle_error

if TYPE_CHECKING:
    from ..core.conversation import ConversationFile
    from ..core.session import Session

logger = logging.getLogger("sdqctl.commands.output_steps")


def write_cycle_output(
    all_responses: list[dict],
    conv: "ConversationFile",
    output_vars: dict[str, str],
    console: Console,
    progress: Callable[[str], None],
) -> Optional[str]:
    """Write cycle output to file if configured.

    Args:
        all_responses: List of response dicts with cycle, prompt, response
        conv: ConversationFile for output settings
        output_vars: Template variables for output path
        console: Rich Console for output
        progress: Progress callback

    Returns:
        Path to output file if written, None otherwise
    """
    if not conv.output_file:
        return None

    # Substitute template variables in output path
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
    progress(f"  Writing to {effective_output}")
    console.print(f"[green]Output written to {effective_output}[/green]")

    return effective_output


def display_completion(
    conv: "ConversationFile",
    session: "Session",
    cycle_elapsed: float,
    all_responses: list[dict],
    output_vars: dict[str, str],
    json_output: bool,
    console: Console,
    progress: Callable[[str], None],
    ai_adapter: Any,
    adapter_session: Any,
) -> None:
    """Display completion message and write output.

    Args:
        conv: ConversationFile with output settings
        session: Session for message count
        cycle_elapsed: Total elapsed time in seconds
        all_responses: List of response dicts
        output_vars: Template variables for output
        json_output: Whether to output as JSON
        console: Rich Console for output
        progress: Progress callback
        ai_adapter: AI adapter for stats
        adapter_session: Adapter session for stats
    """
    import json as json_mod

    if json_output:
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
        console.print_json(json_mod.dumps(result))
    else:
        console.print(f"\n[green]✓ Completed {conv.max_cycles} cycles[/green]")
        console.print(f"[dim]Total messages: {len(session.state.messages)}[/dim]")

        # Write output file if configured
        write_cycle_output(all_responses, conv, output_vars, console, progress)

    progress(f"Done in {cycle_elapsed:.1f}s")


def handle_loop_error(
    error: LoopDetected,
    session: "Session",
    workflow_path: Optional[str],
    json_errors: bool,
    console: Console,
) -> None:
    """Handle LoopDetected error with checkpoint.

    Args:
        error: The LoopDetected exception
        session: Session for checkpoint
        workflow_path: Path to workflow file
        json_errors: Whether to output as JSON
        console: Rich Console for output
    """
    session.state.status = "failed"
    checkpoint_path = session.save_pause_checkpoint(f"Loop detected: {error.reason.value}")
    if not json_errors:
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        logger.error(f"Loop detected: {error}")
    exit_code = handle_error(error, json_errors=json_errors, context={
        "workflow": workflow_path,
        "checkpoint": str(checkpoint_path),
    })
    sys.exit(exit_code)


def handle_missing_context_error(
    error: MissingContextFiles,
    session: "Session",
    workflow_path: Optional[str],
    json_errors: bool,
    console: Console,
) -> None:
    """Handle MissingContextFiles error with checkpoint.

    Args:
        error: The MissingContextFiles exception
        session: Session for checkpoint
        workflow_path: Path to workflow file
        json_errors: Whether to output as JSON
        console: Rich Console for output
    """
    session.state.status = "failed"
    checkpoint_path = session.save_pause_checkpoint(f"Missing context files: {error.files}")
    if not json_errors:
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        logger.error(f"Missing files: {error}")
    exit_code = handle_error(error, json_errors=json_errors, context={
        "workflow": workflow_path,
        "checkpoint": str(checkpoint_path),
    })
    sys.exit(exit_code)


def handle_generic_error(
    error: Exception,
    session: "Session",
    workflow_path: Optional[str],
    json_errors: bool,
    console: Console,
) -> None:
    """Handle generic error with checkpoint.

    Args:
        error: The exception
        session: Session for checkpoint
        workflow_path: Path to workflow file
        json_errors: Whether to output as JSON
        console: Rich Console for output

    Raises:
        Exception: Re-raises the error if not json_errors mode
    """
    session.state.status = "failed"
    checkpoint_path = session.save_pause_checkpoint(f"Error: {error}")
    if json_errors:
        exit_code = handle_error(error, json_errors=True, context={
            "workflow": workflow_path,
            "checkpoint": str(checkpoint_path),
        })
        sys.exit(exit_code)
    else:
        console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
        console.print(f"[red]Error: {error}[/red]")
        raise error
