"""
Helper functions for iterate command.

Provides target parsing, validation, and configuration builders.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import click

from ..adapters.base import InfiniteSessionConfig

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
    compaction_threshold: int,
    buffer_threshold: int = 95,
    min_compaction_density: int = 30,
    conv_infinite_sessions: Optional[bool] = None,
    conv_compaction_min: Optional[float] = None,
    conv_compaction_threshold: Optional[float] = None,
) -> InfiniteSessionConfig:
    """Build InfiniteSessionConfig from CLI options and ConversationFile directives.

    Priority: CLI options > ConversationFile directives > defaults
    """
    # Enabled: CLI flag takes precedence, then conv directive, then default (True)
    if no_infinite_sessions:
        enabled = False
    elif conv_infinite_sessions is not None:
        enabled = conv_infinite_sessions
    else:
        enabled = True

    # Min compaction density: CLI > conv > default (30%)
    if min_compaction_density != 30:  # CLI override
        min_density = min_compaction_density / 100.0
    elif conv_compaction_min is not None:
        min_density = conv_compaction_min
    else:
        min_density = 0.30

    # Background threshold: CLI > conv > default (80%)
    if compaction_threshold != 80:  # CLI override
        bg_threshold = compaction_threshold / 100.0
    elif conv_compaction_threshold is not None:
        bg_threshold = conv_compaction_threshold
    else:
        bg_threshold = 0.80

    # Buffer exhaustion: CLI > default (95%)
    buf_threshold = buffer_threshold / 100.0

    return InfiniteSessionConfig(
        enabled=enabled,
        min_compaction_density=min_density,
        background_threshold=bg_threshold,
        buffer_exhaustion=buf_threshold,
    )
