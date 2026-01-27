"""Output formatting utilities.

Provides TTY-aware console output for sdqctl:
- stdout console: for progress and agent responses
- stderr console: for prompts (via --show-prompt / -P)
- JSON error output for CI integration (--json-errors)

TTY detection (git-style):
- When stdout is a TTY: Rich formatting, colors, progress updates
- When stdout redirected: Plain text, no colors, no progress overwrites
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional, Union

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from ..core.exceptions import ExitCode, format_json_error

# TTY detection for git-style behavior
_stdout_is_tty = sys.stdout.isatty()
_stderr_is_tty = sys.stderr.isatty()

# Main console (stdout) - for progress and agent responses
console = Console(
    force_terminal=_stdout_is_tty,
    no_color=not _stdout_is_tty,
)

# Stderr console - for prompts and diagnostics
stderr_console = Console(
    file=sys.stderr,
    force_terminal=_stderr_is_tty,
    no_color=not _stderr_is_tty,
)


def is_stdout_tty() -> bool:
    """Check if stdout is a TTY (for conditional formatting)."""
    return _stdout_is_tty


def is_stderr_tty() -> bool:
    """Check if stderr is a TTY (for conditional formatting)."""
    return _stderr_is_tty


class PromptWriter:
    """Write expanded prompts to stderr with cycle/step context.

    Used when --show-prompt / -P flag is enabled.

    Usage:
        writer = PromptWriter(enabled=ctx.obj.get("show_prompt", False))
        writer.write_prompt(prompt_text, cycle=1, total_cycles=3,
                           prompt_idx=2, total_prompts=4, context_pct=31.5)
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.console = stderr_console

    def write_prompt(
        self,
        prompt: str,
        cycle: int = 1,
        total_cycles: int = 1,
        prompt_idx: int = 1,
        total_prompts: int = 1,
        context_pct: Optional[float] = None,
    ) -> None:
        """Write a prompt to stderr with context information.

        Args:
            prompt: The fully expanded prompt text
            cycle: Current cycle number (1-indexed)
            total_cycles: Total number of cycles
            prompt_idx: Current prompt index (1-indexed)
            total_prompts: Total number of prompts
            context_pct: Context window usage percentage (optional)
        """
        if not self.enabled:
            return

        # Build header
        if total_cycles > 1:
            header = f"[Cycle {cycle}/{total_cycles}, Prompt {prompt_idx}/{total_prompts}]"
        else:
            header = f"[Prompt {prompt_idx}/{total_prompts}]"

        if context_pct is not None:
            header += f" (ctx: {context_pct:.0f}%)"

        # Output with formatting if TTY, plain if redirected
        if _stderr_is_tty:
            self.console.print()
            self.console.print(Rule(header, style="dim"))
            self.console.print(prompt)
            self.console.print(Rule(style="dim"))
        else:
            # Plain text for redirection/logging
            separator = "─" * 60
            self.console.print(f"\n{header} {separator}")
            self.console.print(prompt)
            self.console.print(separator)


def format_output(data: Any, format: str = "markdown", title: str = None) -> str:
    """Format data for output.

    Args:
        data: Data to format
        format: Output format (markdown, json, text)
        title: Optional title

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps(data, indent=2, default=str)

    if format == "markdown":
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            lines = []
            if title:
                lines.append(f"# {title}\n")
            for key, value in data.items():
                if isinstance(value, dict):
                    lines.append(f"## {key}\n")
                    for k, v in value.items():
                        lines.append(f"- **{k}**: {v}")
                else:
                    lines.append(f"- **{key}**: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            if title:
                lines.append(f"# {title}\n")
            for item in data:
                if isinstance(item, dict):
                    lines.append(f"- {json.dumps(item)}")
                else:
                    lines.append(f"- {item}")
            return "\n".join(lines)

    # Default: text
    return str(data)


def print_panel(content: str, title: str = None, style: str = "blue") -> None:
    """Print content in a panel."""
    console.print(Panel(content, title=title, border_style=style))


def print_markdown(content: str) -> None:
    """Print markdown content."""
    console.print(Markdown(content))


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]Error: {message}[/red]")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓ {message}[/green]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠ {message}[/yellow]")


def handle_error(
    exc: Exception,
    json_errors: bool = False,
    context: Optional[dict[str, Any]] = None,
) -> int:
    """Handle an exception with appropriate output format.

    Args:
        exc: The exception to handle
        json_errors: If True, output JSON format; otherwise Rich format
        context: Optional additional context (workflow, cycle, etc.)

    Returns:
        Exit code to use for sys.exit()
    """
    if json_errors:
        print(format_json_error(exc, context))
    else:
        print_error(str(exc))

    # Return appropriate exit code
    if hasattr(exc, "exit_code"):
        return exc.exit_code
    return ExitCode.GENERAL_ERROR


def print_json(data: Any, file: Optional[Any] = None) -> None:
    """Print data as formatted JSON to stdout or specified file.

    Consolidates the common pattern: console.print_json(json.dumps(data, indent=2))

    Args:
        data: Data to serialize and print
        file: Optional file object (defaults to stdout via console)
    """
    json_str = json.dumps(data, indent=2, default=str)
    if file:
        print(json_str, file=file)
    else:
        console.print_json(json_str)


def write_json_file(path: Union[Path, str], data: Any) -> None:
    """Write data as formatted JSON to a file.

    Consolidates the common pattern: Path(...).write_text(json.dumps(data, indent=2))

    Args:
        path: Path to write to (parent directories created if needed)
        data: Data to serialize
    """
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str))


def read_json_file(path: Union[Path, str]) -> Any:
    """Read and parse JSON from a file.

    Args:
        path: Path to read from

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    p = Path(path) if not isinstance(path, Path) else path
    return json.loads(p.read_text())


def write_text_file(path: Union[Path, str], content: str) -> None:
    """Write text content to a file, creating parent directories.

    Args:
        path: Path to write to
        content: Text content to write
    """
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def print_json_error(
    error_type: str,
    message: str,
    exit_code: int = ExitCode.GENERAL_ERROR,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Print a structured JSON error without an exception.

    Args:
        error_type: Error type name (e.g., "ValidationError")
        message: Human-readable error message
        exit_code: Exit code to include
        details: Optional additional details
    """
    error_dict: dict[str, Any] = {
        "type": error_type,
        "message": message,
        "exit_code": exit_code,
    }
    if details:
        error_dict.update(details)
    print(json.dumps({"error": error_dict}, indent=2))
