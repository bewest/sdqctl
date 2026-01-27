"""
Compact and checkpoint step handlers for workflow execution.

Handles COMPACT and CHECKPOINT directives during iterate cycles.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..core.conversation import ConversationFile
    from ..core.session import Session

logger = logging.getLogger("sdqctl.commands.compact_steps")


async def execute_compact_step(
    step: Any,
    conv: "ConversationFile",
    session: "Session",
    ai_adapter: Any,
    adapter_session: Any,
    min_compaction_density: float,
    console: Any,
    progress: Callable[[str], None],
) -> bool:
    """Execute a COMPACT step.

    Args:
        step: ConversationStep with optional preserve list
        conv: ConversationFile for compact_preserve setting
        session: Session for compaction state
        ai_adapter: AI adapter for sending compaction prompt
        adapter_session: Adapter session for API calls
        min_compaction_density: Threshold for compaction
        console: Console for output
        progress: Progress callback

    Returns:
        True if compaction was performed, False if skipped
    """
    if not session.needs_compaction(min_compaction_density):
        skip_msg = "📊 Skipping COMPACT - context below threshold"
        console.print(f"[dim]{skip_msg}[/dim]")
        progress(f"  {skip_msg}")
        return False

    console.print("[yellow]🗜  Compacting conversation...[/yellow]")
    progress("  🗜  Compacting conversation...")

    preserve = getattr(step, 'preserve', []) if hasattr(step, 'preserve') else []
    all_preserve = conv.compact_preserve + preserve
    compact_prompt = session.get_compaction_prompt()

    if all_preserve:
        preserve_list = ', '.join(all_preserve)
        compact_prompt = f"Preserve these items: {preserve_list}\n\n{compact_prompt}"

    compact_response = await ai_adapter.send(adapter_session, compact_prompt)
    summary_msg = f"[Compaction summary]\n{compact_response}"
    session.add_message("system", summary_msg)

    # Sync local context tracking with SDK token count
    tokens_after, _ = await ai_adapter.get_context_usage(adapter_session)
    session.context.window.used_tokens = tokens_after

    console.print("[green]🗜  Compaction complete[/green]")
    progress("  🗜  Compaction complete")
    return True


def execute_checkpoint_step(
    step: Any,
    session: "Session",
    cycle_num: int,
    console: Any,
    progress: Callable[[str], None],
) -> str:
    """Execute a CHECKPOINT step.

    Args:
        step: ConversationStep with optional checkpoint name in content
        session: Session for creating checkpoint
        cycle_num: Current cycle number for default name
        console: Console for output
        progress: Progress callback

    Returns:
        Checkpoint name
    """
    step_content = getattr(step, 'content', '') if hasattr(step, 'content') else ''
    checkpoint_name = step_content or f"cycle-{cycle_num}-step"

    checkpoint = session.create_checkpoint(checkpoint_name)
    console.print(f"[blue]📌 Checkpoint: {checkpoint.name}[/blue]")
    progress(f"  📌 Checkpoint: {checkpoint.name}")

    return checkpoint.name
