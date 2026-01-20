"""Output formatting utilities."""

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


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
