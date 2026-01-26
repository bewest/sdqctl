"""
Helper functions for iterate command.

Provides target parsing, validation, and configuration builders.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click

from ..adapters.base import InfiniteSessionConfig

if TYPE_CHECKING:
    from logging import Logger

    from rich.console import Console

    from ..adapters.base import AdapterBase, AdapterConfig, AdapterSession
    from ..core.loop_detector import LoopDetector
    from ..core.session import Session

logger = logging.getLogger("sdqctl.commands.iterate_helpers")


# Turn separator for forcing turn boundaries in mixed mode
TURN_SEPARATOR = "---"


@dataclass
class TurnGroup:
    """A group of items that will be elided into a single turn."""
    items: list[str] = field(default_factory=list)


def is_workflow_file(item: str) -> bool:
    """Check if item is an existing .conv or .copilot file."""
    path = Path(item)
    return path.exists() and path.suffix in (".conv", ".copilot")


def parse_targets(targets: tuple[str, ...]) -> list[TurnGroup]:
    """Parse mixed targets into turn groups separated by ---.

    Args:
        targets: Tuple of target strings (prompts, file paths, or separators)

    Returns:
        List of TurnGroup objects. Empty groups are filtered out.
    """
    groups: list[TurnGroup] = []
    current: list[str] = []

    for item in targets:
        if item == TURN_SEPARATOR:
            if current:
                groups.append(TurnGroup(items=current))
                current = []
        else:
            current.append(item)

    if current:
        groups.append(TurnGroup(items=current))

    return groups


def validate_targets(
    groups: list[TurnGroup]
) -> tuple[Optional[str], list[str], list[str]]:
    """Validate mixed target constraints and extract components.

    Args:
        groups: List of TurnGroup objects from parse_targets

    Returns:
        Tuple of (workflow_path, pre_prompts, post_prompts)
        - workflow_path: Path to the single .conv file, or None
        - pre_prompts: Prompts before the workflow file
        - post_prompts: Prompts after the workflow file

    Raises:
        click.UsageError: If more than one .conv file is found
    """
    workflow_path: Optional[str] = None
    pre_prompts: list[str] = []
    post_prompts: list[str] = []
    workflow_found = False
    conv_files: list[str] = []

    # First pass: find all .conv files
    for group in groups:
        for item in group.items:
            if is_workflow_file(item):
                conv_files.append(item)

    if len(conv_files) > 1:
        raise click.UsageError(
            f"Mixed mode allows only ONE .conv file, found {len(conv_files)}: "
            f"{conv_files}"
        )

    # Second pass: categorize items
    for group in groups:
        for item in group.items:
            if is_workflow_file(item):
                workflow_path = item
                workflow_found = True
            elif workflow_found:
                post_prompts.append(item)
            else:
                pre_prompts.append(item)

    return workflow_path, pre_prompts, post_prompts


# Session mode descriptions for help and documentation
SESSION_MODES = {
    "accumulate": "Context grows, compact only at limit",
    "compact": "Summarize after each cycle",
    "fresh": "New session each cycle, reload files",
}


def build_infinite_session_config(
    no_infinite_sessions: bool,
    compaction_threshold: Optional[int],
    buffer_threshold: Optional[int] = None,
    min_compaction_density: Optional[int] = None,
    conv_infinite_sessions: Optional[bool] = None,
    conv_compaction_min: Optional[float] = None,
    conv_compaction_threshold: Optional[float] = None,
    conv_compaction_max: Optional[float] = None,
) -> InfiniteSessionConfig:
    """Build InfiniteSessionConfig from CLI options and ConversationFile directives.

    Priority: CLI options > ConversationFile directives > defaults

    Args:
        no_infinite_sessions: CLI flag to disable infinite sessions
        compaction_threshold: CLI background threshold (None=use directive/default)
        buffer_threshold: CLI buffer exhaustion threshold (None=use directive/default)
        min_compaction_density: CLI min density (None=use directive/default)
        conv_infinite_sessions: ConversationFile INFINITE-SESSIONS directive
        conv_compaction_min: ConversationFile COMPACTION-MIN directive (0.0-1.0)
        conv_compaction_threshold: ConversationFile COMPACTION-THRESHOLD directive (0.0-1.0)
        conv_compaction_max: ConversationFile COMPACTION-MAX directive (0.0-1.0)
    """
    # Enabled: CLI flag takes precedence, then conv directive, then default (True)
    if no_infinite_sessions:
        enabled = False
    elif conv_infinite_sessions is not None:
        enabled = conv_infinite_sessions
    else:
        enabled = True

    # Min compaction density: CLI > conv > default (30%)
    if min_compaction_density is not None:
        min_density = min_compaction_density / 100.0
    elif conv_compaction_min is not None:
        min_density = conv_compaction_min
    else:
        min_density = 0.30

    # Background threshold: CLI > conv > default (80%)
    if compaction_threshold is not None:
        bg_threshold = compaction_threshold / 100.0
    elif conv_compaction_threshold is not None:
        bg_threshold = conv_compaction_threshold
    else:
        bg_threshold = 0.80

    # Buffer exhaustion: CLI > conv > default (95%)
    if buffer_threshold is not None:
        buf_threshold = buffer_threshold / 100.0
    elif conv_compaction_max is not None:
        buf_threshold = conv_compaction_max
    else:
        buf_threshold = 0.95

    return InfiniteSessionConfig(
        enabled=enabled,
        min_compaction_density=min_density,
        background_threshold=bg_threshold,
        buffer_exhaustion=buf_threshold,
    )


def check_existing_stop_file(
    loop_detector: "LoopDetector",
    console: "Console",
) -> bool:
    """Check if a stop file exists from a previous run.

    Args:
        loop_detector: LoopDetector with stop file path
        console: Rich Console for output

    Returns:
        True if stop file exists and user should not continue, False otherwise
    """
    import json

    from rich.panel import Panel

    if not loop_detector.stop_file_path.exists():
        return False

    try:
        content = loop_detector.stop_file_path.read_text()
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
    return True


async def create_or_resume_session(
    ai_adapter: "AdapterBase",
    adapter_config: "AdapterConfig",
    session_name: Optional[str],
    verbosity: int,
    console: "Console",
    logger: "Logger",
) -> "AdapterSession":
    """Create or resume an adapter session.

    Args:
        ai_adapter: The AI adapter
        adapter_config: Configuration for the session
        session_name: Optional named session to resume
        verbosity: Verbosity level for output
        console: Rich Console for output
        logger: Logger for debug output

    Returns:
        The created or resumed adapter session
    """
    if session_name:
        # Named session: resume if exists, otherwise create new
        try:
            adapter_session = await ai_adapter.resume_session(session_name, adapter_config)
            logger.info(f"Resumed session: {session_name}")
            if verbosity > 0:
                console.print(f"[dim]Resumed session: {session_name}[/dim]")
        except Exception as e:
            # Session doesn't exist, create new with session name
            logger.debug(f"Could not resume session '{session_name}': {e}, creating new")
            adapter_session = await ai_adapter.create_session(adapter_config)
            if verbosity > 0:
                console.print(f"[dim]Created new session: {session_name}[/dim]")
    else:
        adapter_session = await ai_adapter.create_session(adapter_config)

    return adapter_session


async def recreate_fresh_session(
    ai_adapter: "AdapterBase",
    adapter_session: "AdapterSession",
    adapter_config: "AdapterConfig",
    session: "Session",
    cycle_num: int,
    progress_print,
) -> "AdapterSession":
    """Destroy and recreate session for 'fresh' mode (new session each cycle).

    Args:
        ai_adapter: The adapter instance
        adapter_session: Current adapter session to destroy
        adapter_config: Config for new session
        session: The iteration session (for reload_context)
        cycle_num: Current cycle number (for logging)
        progress_print: Function to print progress messages

    Returns:
        New adapter session
    """
    from ..core.session import Session  # noqa: F401 - used in TYPE_CHECKING

    await ai_adapter.destroy_session(adapter_session)
    new_session = await ai_adapter.create_session(adapter_config)
    # Reload CONTEXT files from disk (pick up any changes)
    session.reload_context()
    progress_print(f"  🔄 New session for cycle {cycle_num + 1}")
    return new_session


async def perform_compaction(
    ai_adapter: "AdapterBase",
    adapter_session: "AdapterSession",
    conv,
    session: "Session",
    reason: str,
    console: "Console",
    progress_print,
) -> None:
    """Perform context compaction and log result.

    Args:
        ai_adapter: The adapter instance
        adapter_session: Current adapter session
        conv: Conversation with compact_preserve setting
        session: The session with compaction prompt
        reason: Human-readable reason (e.g., "before cycle 2", "context near limit")
        console: Console for output
        progress_print: Function for progress messages
    """
    console.print(f"\n[yellow]Compacting {reason}...[/yellow]")
    progress_print("  🗜  Compacting context...")

    compact_result = await ai_adapter.compact(
        adapter_session,
        conv.compact_preserve,
        session.get_compaction_prompt()
    )

    tokens_msg = f"{compact_result.tokens_before} → {compact_result.tokens_after} tokens"
    console.print(f"[green]Compacted: {tokens_msg}[/green]")
    progress_print(f"  🗜  Compacted: {tokens_msg}")
