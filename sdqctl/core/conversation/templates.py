"""Template variable substitution for ConversationFile."""

from pathlib import Path
from typing import Optional


def substitute_template_variables(text: str, variables: dict[str, str]) -> str:
    """Substitute {{VARIABLE}} placeholders with values.

    Supported variables:
    - DATE: ISO date (YYYY-MM-DD)
    - DATETIME: ISO datetime
    - __WORKFLOW_NAME__: Workflow filename (explicit opt-in, Q-001 safe)
    - __WORKFLOW_PATH__: Full path to workflow (explicit opt-in, Q-001 safe)
    - WORKFLOW_NAME: Workflow filename (only in output paths, not prompts)
    - WORKFLOW_PATH: Full path to workflow (only in output paths, not prompts)
    - COMPONENT_PATH: Full path to current component
    - COMPONENT_NAME: Base name of component (without extension)
    - COMPONENT_DIR: Parent directory of component
    - COMPONENT_TYPE: Type from discovery (plugin, api, etc.)
    - ITERATION_INDEX: Current iteration number (1-based)
    - ITERATION_TOTAL: Total number of components
    - GIT_BRANCH: Current git branch (if available)
    - GIT_COMMIT: Short commit SHA (if available)
    - CWD: Current working directory

    Note: WORKFLOW_NAME/WORKFLOW_PATH are excluded from prompts by default to
    avoid influencing agent behavior. Use __WORKFLOW_NAME__ for explicit opt-in.
    See Q-001 in docs/QUIRKS.md.
    """
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def get_standard_variables(
    workflow_path: Optional[Path] = None,
    include_workflow_vars: bool = False,
    stop_file_nonce: Optional[str] = None,
) -> dict[str, str]:
    """Get standard template variables available in all contexts.

    Returns dict with DATE, DATETIME, GIT_BRANCH, GIT_COMMIT, CWD.

    Workflow path variables are NOT included by default to avoid influencing
    agent behavior (see Q-001 in docs/QUIRKS.md). Use include_workflow_vars=True
    for output paths only, or use the explicit opt-in __WORKFLOW_NAME__ variable.

    Args:
        workflow_path: Path to the workflow file
        include_workflow_vars: If True, include WORKFLOW_NAME and WORKFLOW_PATH
            (use only for output paths, not agent-visible prompts)
        stop_file_nonce: Nonce for stop file naming. When provided, adds
            STOP_FILE variable for agent stop signaling (Q-002).

    Returns:
        Dict with template variables. Always includes __WORKFLOW_NAME__ and
        __WORKFLOW_PATH__ for explicit opt-in regardless of include_workflow_vars.
    """
    import subprocess
    from datetime import datetime

    now = datetime.now()
    variables = {
        "DATE": now.strftime("%Y-%m-%d"),
        "DATETIME": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "CWD": str(Path.cwd()),
    }

    if workflow_path:
        # Always provide explicit opt-in variables (underscore prefix = explicit)
        variables["__WORKFLOW_NAME__"] = workflow_path.stem
        variables["__WORKFLOW_PATH__"] = str(workflow_path)

        # Only include unprefixed versions if explicitly requested (for output paths)
        if include_workflow_vars:
            variables["WORKFLOW_NAME"] = workflow_path.stem
            variables["WORKFLOW_PATH"] = str(workflow_path)

    # Try to get git info (fail silently if not in a git repo)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            variables["GIT_BRANCH"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            variables["GIT_COMMIT"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Add stop file variable if nonce provided (Q-002 agent stop signaling)
    if stop_file_nonce:
        variables["STOP_FILE"] = f"STOPAUTOMATION-{stop_file_nonce}.json"

    return variables
