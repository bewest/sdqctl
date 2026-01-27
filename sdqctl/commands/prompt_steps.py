"""
Prompt step handlers for iterate command.

Handles prompt building, context injection, and response processing
during workflow execution cycles.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..core.conversation import build_prompt_with_injection
from ..core.exceptions import LoopReason
from ..core.loop_detector import get_stop_file_instruction

if TYPE_CHECKING:
    from ..core.conversation import ConversationFile
    from ..core.loop_detector import LoopDetector
    from ..core.progress import WorkflowProgress
    from ..core.session import Session
    from ..utils.output import PromptWriter

logger = logging.getLogger("sdqctl.commands.prompt_steps")


@dataclass
class PromptContext:
    """Context needed for building and sending a prompt."""

    prompt: str
    prompt_idx: int
    total_prompts: int
    cycle_num: int
    max_cycles: int
    session_mode: str
    context_content: str
    template_vars: dict[str, str]
    no_stop_file_prologue: bool = False
    verbosity: int = 0


@dataclass
class PromptBuildResult:
    """Result from building a prompt with all injections."""

    full_prompt: str
    context_pct: float
    is_first: bool
    is_last: bool


def build_full_prompt(
    ctx: PromptContext,
    conv: "ConversationFile",
    session: "Session",
    loop_detector: "LoopDetector",
) -> PromptBuildResult:
    """Build a complete prompt with all injections.

    Applies:
    - Prologue/epilogue injection (based on first/last position)
    - Context injection (first prompt of cycle/session)
    - Stop file instructions (first prompt of session in accumulate mode)
    - Continuation context (subsequent cycles in accumulate mode)

    Args:
        ctx: PromptContext with current prompt state
        conv: ConversationFile for prologues, epilogues, settings
        session: Session for context content
        loop_detector: LoopDetector for stop file name

    Returns:
        PromptBuildResult with the fully built prompt
    """
    # Get context usage percentage
    ctx_status = session.context.get_status()
    context_pct = ctx_status.get("usage_percent", 0)

    # Build prompt with prologue/epilogue injection
    is_first = (ctx.prompt_idx == 0)
    is_last = (ctx.prompt_idx == ctx.total_prompts - 1)
    full_prompt = build_prompt_with_injection(
        ctx.prompt, conv.prologues, conv.epilogues,
        conv.source_path.parent if conv.source_path else None,
        ctx.template_vars,
        is_first_prompt=is_first,
        is_last_prompt=is_last
    )

    # Add context to first prompt (fresh: always, others: cycle 0)
    if ctx.prompt_idx == 0 and ctx.context_content:
        full_prompt = f"{ctx.context_content}\n\n{full_prompt}"

    # Add stop file instruction on first prompt of session (Q-002)
    # For fresh mode: inject each cycle. For accumulate: only cycle 0.
    should_inject_stop_file = (
        not ctx.no_stop_file_prologue and
        ctx.prompt_idx == 0 and
        (ctx.session_mode == "fresh" or ctx.cycle_num == 0)
    )
    if should_inject_stop_file:
        stop_instr = get_stop_file_instruction(loop_detector.stop_file_name)
        full_prompt = f"{full_prompt}\n\n{stop_instr}"

    # On subsequent cycles (accumulate), add continuation context
    is_continuation = (
        ctx.session_mode == "accumulate" and
        ctx.cycle_num > 0 and ctx.prompt_idx == 0 and
        conv.on_context_limit_prompt
    )
    if is_continuation:
        full_prompt = f"{conv.on_context_limit_prompt}\n\n{full_prompt}"

    return PromptBuildResult(
        full_prompt=full_prompt,
        context_pct=context_pct,
        is_first=is_first,
        is_last=is_last,
    )


def emit_prompt_progress(
    ctx: PromptContext,
    context_pct: float,
    workflow_progress: "WorkflowProgress",
    prompt_writer: "PromptWriter",
    full_prompt: str,
) -> None:
    """Emit progress notifications before sending a prompt.

    Args:
        ctx: PromptContext with current prompt state
        context_pct: Current context usage percentage
        workflow_progress: WorkflowProgress for progress tracking
        prompt_writer: PromptWriter for --show-prompt output
        full_prompt: The complete prompt to display
    """
    # Enhanced progress with context %
    workflow_progress.prompt_sending(
        cycle=ctx.cycle_num + 1,
        prompt=ctx.prompt_idx + 1,
        context_pct=context_pct,
        preview=ctx.prompt[:50] if ctx.verbosity >= 1 else None
    )

    # Write prompt to stderr if --show-prompt / -P enabled
    prompt_writer.write_prompt(
        full_prompt,
        cycle=ctx.cycle_num + 1,
        total_cycles=ctx.max_cycles,
        prompt_idx=ctx.prompt_idx + 1,
        total_prompts=ctx.total_prompts,
        context_pct=context_pct,
    )


@dataclass
class LoopCheckResult:
    """Result from checking for loop conditions after response."""

    detected: bool
    loop_result: Optional[Any] = None  # LoopDetected instance if detected


def check_response_loop(
    response: str,
    reasoning: list[str],
    cycle_num: int,
    ai_adapter: Any,
    adapter_session: Any,
    loop_detector: "LoopDetector",
) -> LoopCheckResult:
    """Check if response indicates a loop condition.

    Args:
        response: The AI response text
        reasoning: List of reasoning strings from the response
        cycle_num: Current cycle number (0-indexed)
        ai_adapter: AI adapter for getting session stats
        adapter_session: Current adapter session
        loop_detector: LoopDetector for checking loop conditions

    Returns:
        LoopCheckResult indicating if a loop was detected
    """
    combined = " ".join(reasoning) if reasoning else None

    # Get tool count from turn stats for tool-aware loop detection
    turn_tools = 0
    if hasattr(ai_adapter, 'get_session_stats'):
        stats = ai_adapter.get_session_stats(adapter_session)
        if stats and stats._send_turn_stats:
            turn_tools = stats._send_turn_stats.tool_calls

    loop_result = loop_detector.check(combined, response, cycle_num, turn_tools)

    if loop_result:
        return LoopCheckResult(detected=True, loop_result=loop_result)

    return LoopCheckResult(detected=False)


def format_loop_output(
    loop_result: Any,
    loop_detector: "LoopDetector",
    session: "Session",
    cycle_num: int,
    max_cycles: int,
    console: Any,
    progress: Callable[[str], None],
) -> None:
    """Format and output loop detection messages.

    Args:
        loop_result: The LoopDetected instance
        loop_detector: LoopDetector for stop file name
        session: Session for ID
        cycle_num: Current cycle number (0-indexed)
        max_cycles: Total number of cycles
        console: Rich Console for output
        progress: Progress callback
    """
    # Special handling for stop file (agent-initiated stop)
    if loop_result.reason == LoopReason.STOP_FILE:
        stop_name = loop_detector.stop_file_name
        console.print(
            f"\n[yellow]⚠️  Agent requested stop via {stop_name}[/yellow]"
        )
        console.print(f"[yellow]   Reason: {loop_result.details}[/yellow]")
        console.print(f"[yellow]   Session: {session.id}[/yellow]")
        console.print(f"[yellow]   Cycle: {cycle_num + 1}/{max_cycles}[/yellow]")
        console.print(
            "\n[dim]Review the agent's work and decide next steps.[/dim]"
        )
        progress(f"  ⚠️  Agent stop: {loop_result.details}")
    else:
        console.print(f"\n[red]⚠️  {loop_result}[/red]")
        reason_val = loop_result.reason.value
        progress(f"  ⚠️  Loop detected: {reason_val}")
