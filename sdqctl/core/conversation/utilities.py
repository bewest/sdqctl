"""Utility functions for ConversationFile content resolution and building."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .templates import get_standard_variables, substitute_template_variables

if TYPE_CHECKING:
    from .file import ConversationFile

logger = logging.getLogger("sdqctl.core.conversation")


def resolve_content_reference(value: str, base_path: Optional[Path] = None) -> str:
    """Resolve @file references to file content.

    Args:
        value: Either inline text or @path/to/file reference
        base_path: Base path for relative file references (workflow directory)

    Returns:
        The resolved content (file contents or original value)

    Note:
        Resolution order for relative paths:
        1. CWD (current working directory) - intuitive for CLI users
        2. base_path (workflow file directory) - for self-contained workflows

        Logs a warning if file reference cannot be resolved.
    """
    if value.startswith("@"):
        file_path = value[1:]  # Remove @ prefix

        # Absolute paths resolve directly
        if Path(file_path).is_absolute():
            full_path = Path(file_path)
            if full_path.exists():
                return full_path.read_text()
            else:
                logger.warning(f"File reference not found: {value} (resolved to {full_path})")
                return value

        # Try CWD first (intuitive for CLI users)
        cwd_path = Path.cwd() / file_path
        if cwd_path.exists():
            return cwd_path.read_text()

        # Fall back to base_path (workflow directory)
        if base_path:
            full_path = base_path / file_path
            if full_path.exists():
                return full_path.read_text()

        # Neither worked - log warning with both attempted paths
        if base_path:
            logger.warning(
                f"File reference not found: {value} "
                f"(tried {cwd_path} and {base_path / file_path})"
            )
        else:
            logger.warning(f"File reference not found: {value} (resolved to {cwd_path})")
        return value
    return value


def apply_iteration_context(conv: "ConversationFile", component_path: str,
                            iteration_index: int = 1, iteration_total: int = 1,
                            component_type: str = "unknown") -> "ConversationFile":
    """Create a copy of ConversationFile with template variables substituted.

    Args:
        conv: The original ConversationFile
        component_path: Path to the current component
        iteration_index: Current iteration number (1-based)
        iteration_total: Total number of iterations
        component_type: Type of component from discovery

    Returns:
        A new ConversationFile with substituted values
    """
    from copy import deepcopy

    path_obj = Path(component_path)

    # Combine standard variables with component-specific ones
    # Exclude WORKFLOW_NAME from prompts to avoid Q-001 (agent behavior influenced by filename)
    variables = get_standard_variables(conv.source_path)
    variables.update({
        "COMPONENT_PATH": str(component_path),
        "COMPONENT_NAME": path_obj.stem,
        "COMPONENT_DIR": str(path_obj.parent),
        "COMPONENT_TYPE": component_type,
        "ITERATION_INDEX": str(iteration_index),
        "ITERATION_TOTAL": str(iteration_total),
    })

    # Get output-specific variables (includes WORKFLOW_NAME for output paths)
    output_variables = get_standard_variables(conv.source_path, include_workflow_vars=True)
    output_variables.update(variables)

    # Deep copy to avoid modifying original
    new_conv = deepcopy(conv)

    # Substitute in prompts (no WORKFLOW_NAME - Q-001 fix)
    new_conv.prompts = [substitute_template_variables(p, variables) for p in new_conv.prompts]

    # Substitute in prologues and epilogues (no WORKFLOW_NAME - Q-001 fix)
    new_conv.prologues = [substitute_template_variables(p, variables) for p in new_conv.prologues]
    new_conv.epilogues = [substitute_template_variables(e, variables) for e in new_conv.epilogues]

    # Substitute in headers and footers (output context, includes WORKFLOW_NAME)
    new_conv.headers = [
        substitute_template_variables(h, output_variables) for h in new_conv.headers
    ]
    new_conv.footers = [
        substitute_template_variables(f, output_variables) for f in new_conv.footers
    ]

    # Substitute in steps (no WORKFLOW_NAME - Q-001 fix)
    for step in new_conv.steps:
        step.content = substitute_template_variables(step.content, variables)

    # Substitute in output paths (includes WORKFLOW_NAME)
    if new_conv.output_file:
        new_conv.output_file = substitute_template_variables(new_conv.output_file, output_variables)
    if new_conv.output_dir:
        new_conv.output_dir = substitute_template_variables(new_conv.output_dir, output_variables)

    return new_conv


def build_prompt_with_injection(prompt: str, prologues: list[str], epilogues: list[str],
                                 base_path: Optional[Path] = None,
                                 variables: Optional[dict[str, str]] = None,
                                 is_first_prompt: bool = False,
                                 is_last_prompt: bool = False) -> str:
    """Build a complete prompt with prologue/epilogue injection.

    Prologues are only injected on the first prompt of a conversation/cycle.
    Epilogues are only injected on the last prompt of a conversation/cycle.

    Args:
        prompt: The main prompt text
        prologues: List of prologue content (inline or @file references)
        epilogues: List of epilogue content (inline or @file references)
        base_path: Base path for resolving @file references
        variables: Template variables for substitution
        is_first_prompt: If True, prepend prologues to this prompt
        is_last_prompt: If True, append epilogues to this prompt

    Returns:
        Complete prompt with prologues prepended (if first) and epilogues appended (if last)
    """
    variables = variables or {}
    parts = []

    # Resolve and add prologues only on first prompt
    if is_first_prompt:
        for prologue in prologues:
            content = resolve_content_reference(prologue, base_path)
            content = substitute_template_variables(content, variables)
            parts.append(content)

    # Add main prompt
    parts.append(substitute_template_variables(prompt, variables))

    # Resolve and add epilogues only on last prompt
    if is_last_prompt:
        for epilogue in epilogues:
            content = resolve_content_reference(epilogue, base_path)
            content = substitute_template_variables(content, variables)
            parts.append(content)

    return "\n\n".join(parts)


def build_output_with_injection(output: str, headers: list[str], footers: list[str],
                                 base_path: Optional[Path] = None,
                                 variables: Optional[dict[str, str]] = None) -> str:
    """Build complete output with header/footer injection.

    Args:
        output: The main output content
        headers: List of header content (inline or @file references)
        footers: List of footer content (inline or @file references)
        base_path: Base path for resolving @file references
        variables: Template variables for substitution

    Returns:
        Complete output with headers prepended and footers appended
    """
    variables = variables or {}
    parts = []

    # Resolve and add headers
    for header in headers:
        content = resolve_content_reference(header, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)

    # Add main output
    parts.append(output)

    # Resolve and add footers
    for footer in footers:
        content = resolve_content_reference(footer, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)

    return "\n\n".join(parts)


def parse_timeout_duration(value: str) -> int:
    """Parse a timeout string like "1h", "30m", "7d" to seconds.

    Supported units:
    - s: seconds
    - m: minutes
    - h: hours
    - d: days

    Args:
        value: Timeout string (e.g., "1h", "30m", "7d", "90s")

    Returns:
        Duration in seconds

    Raises:
        ValueError: If the format is invalid
    """
    value = value.strip().lower()
    if not value:
        raise ValueError("Empty timeout value")

    # Try to parse as plain number (assume seconds)
    try:
        return int(value)
    except ValueError:
        pass

    # Parse with unit suffix
    unit_multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    unit = value[-1]
    if unit not in unit_multipliers:
        raise ValueError(
            f"Invalid timeout unit '{unit}'. Use s/m/h/d (e.g., '1h', '30m', '7d')"
        )

    try:
        amount = int(value[:-1])
    except ValueError:
        raise ValueError(f"Invalid timeout number: {value[:-1]}")

    return amount * unit_multipliers[unit]
