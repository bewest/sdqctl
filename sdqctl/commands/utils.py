"""
Shared utilities for command implementations.
"""

import asyncio
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Coroutine, Optional


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute an async coroutine synchronously.

    Provides consistent async execution across all commands.
    Centralizes error handling and event loop management.

    Usage:
        def my_command(...):
            run_async(_my_command_async(...))
    """
    return asyncio.run(coro)


def run_subprocess(
    command: str,
    allow_shell: bool,
    timeout: int,
    cwd: Path,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Execute a subprocess with consistent settings.

    Args:
        command: Command string to execute
        allow_shell: If True, use shell=True (allows pipes, redirects)
        timeout: Timeout in seconds
        cwd: Working directory for command
        env: Additional environment variables (merged with os.environ)

    Returns:
        CompletedProcess with stdout/stderr captured as text
    """
    # Merge env with current environment (env overrides)
    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)

    args = command if allow_shell else shlex.split(command)
    return subprocess.run(
        args,
        shell=allow_shell,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        env=run_env,
    )


def truncate_output(text: str, limit: Optional[int]) -> str:
    """Truncate output to limit if set.

    Args:
        text: Output text to potentially truncate
        limit: Max characters (None = no limit)

    Returns:
        Original text or truncated text with marker
    """
    if limit is None or len(text) <= limit:
        return text
    # Keep first half and last quarter, with truncation marker
    head_size = limit * 2 // 3
    tail_size = limit // 3
    truncated = len(text) - limit
    return f"{text[:head_size]}\n\n[... {truncated} chars truncated ...]\n\n{text[-tail_size:]}"


def git_commit_checkpoint(
    checkpoint_name: str,
    output_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> bool:
    """Commit outputs to git as a checkpoint.

    Returns True if commit succeeded, False otherwise.
    """
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False  # Not in a git repo

        # Stage output files
        files_to_add = []
        if output_file and output_file.exists():
            files_to_add.append(str(output_file))
        if output_dir and output_dir.exists():
            files_to_add.append(str(output_dir))

        if not files_to_add:
            return False  # Nothing to commit

        # Add files
        subprocess.run(["git", "add"] + files_to_add, check=True)

        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if result.returncode == 0:
            return False  # No changes to commit

        # Commit
        commit_msg = f"checkpoint: {checkpoint_name}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True,
        )
        return True

    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False  # git not installed


def resolve_run_directory(
    run_cwd: Optional[str],
    cwd: Optional[str],
    source_path: Optional[Path],
) -> Path:
    """Resolve the working directory for RUN commands.

    Priority:
    1. run_cwd (RUN-CWD directive) - relative to source_path or CWD
    2. cwd (CWD directive) - absolute or relative
    3. Current working directory

    Args:
        run_cwd: RUN-CWD directive value (optional)
        cwd: CWD directive value (optional)
        source_path: Path to the .conv file (optional)

    Returns:
        Resolved absolute Path for command execution
    """
    if run_cwd:
        run_dir = Path(run_cwd)
        if not run_dir.is_absolute():
            base = source_path.parent if source_path else Path.cwd()
            run_dir = base / run_dir
        return run_dir
    elif cwd:
        return Path(cwd)
    else:
        return Path.cwd()

