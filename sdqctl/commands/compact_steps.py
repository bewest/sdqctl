"""
Compact and checkpoint step handlers for workflow execution.

Handles COMPACT and CHECKPOINT directives during iterate cycles.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union

if TYPE_CHECKING:
    from ..adapters.base import AdapterConfig, AdapterSession
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
    reset_session: bool = False,
    adapter_config: Optional["AdapterConfig"] = None,
) -> Union[bool, Tuple[bool, Optional["AdapterSession"]]]:
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
        reset_session: If True, destroy old session and create new with summary
        adapter_config: Required when reset_session=True

    Returns:
        If reset_session=False: True if compaction was performed, False if skipped
        If reset_session=True: Tuple of (performed, new_adapter_session or None)
    """
    if not session.needs_compaction(min_compaction_density):
        skip_msg = "📊 Skipping COMPACT - context below threshold"
        console.print(f"[dim]{skip_msg}[/dim]")
        progress(f"  {skip_msg}")
        if reset_session:
            return False, None
        return False

    console.print("[yellow]🗜  Compacting conversation...[/yellow]")
    progress("  🗜  Compacting conversation...")

    preserve = getattr(step, 'preserve', []) if hasattr(step, 'preserve') else []
    all_preserve = conv.compact_preserve + preserve

    if reset_session and hasattr(ai_adapter, 'compact_with_session_reset'):
        if adapter_config is None:
            raise ValueError("adapter_config required when reset_session=True")

        new_session, compact_result = await ai_adapter.compact_with_session_reset(
            adapter_session,
            adapter_config,
            all_preserve,
            compaction_prologue=getattr(conv, 'compaction_prologue', None),
            compaction_epilogue=getattr(conv, 'compaction_epilogue', None),
        )

        # Sync local context tracking
        session.context.window.used_tokens = compact_result.tokens_after

        console.print("[green]🗜  Compaction complete (new session)[/green]")
        progress("  🗜  Compaction complete (new session)")
        return True, new_session

    # Standard compaction (no session reset)
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

    if reset_session:
        return True, None
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
