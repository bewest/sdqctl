"""
sdqctl help - Comprehensive help system.

Usage:
    sdqctl help                    # Overview
    sdqctl help <command>          # Command help (run, cycle, flow, etc.)
    sdqctl help <topic>            # Topic help (directives, adapters, workflow)
"""

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ..core.help_commands import COMMAND_HELP
from ..core.help_topics import TOPICS

console = Console()


def get_overview() -> str:
    """Return overview help text."""
    return """
# sdqctl - Software Defined Quality Control

Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

## Quick Start

```bash
sdqctl init                          # Initialize in project
sdqctl run "Audit auth module"       # Run single prompt
sdqctl run workflow.conv             # Run workflow file
sdqctl cycle workflow.conv -n 5      # Multi-cycle execution
sdqctl status                        # Check status
```

## Commands

| Command | Description |
|---------|-------------|
| `run` | Execute single prompt or workflow |
| `cycle` | Multi-cycle workflow execution |
| `flow` | Batch/parallel workflows |
| `apply` | Apply workflow to multiple components |
| `render` | Preview prompts (no AI calls) |
| `verify` | Static verification |
| `validate` | Validate ConversationFile |
| `show` | Display parsed ConversationFile |
| `status` | Show session status |
| `sessions` | Manage conversation sessions |
| `init` | Initialize project |
| `resume` | Resume paused workflow |

## Topics

| Topic | Description |
|-------|-------------|
| `ai` | Workflow authoring guidance for AI agents |
| `directives` | ConversationFile directive reference |
| `adapters` | AI provider configuration |
| `workflow` | ConversationFile format guide |
| `variables` | Template variable reference |
| `context` | Context management guide |
| `examples` | Example workflows |
| `validation` | Static verification workflow guide |

## Getting Help

```bash
sdqctl help                  # This overview
sdqctl help run              # Command help
sdqctl help directives       # Topic help
sdqctl <command> --help      # Click's built-in help
```

## Documentation

- README: /home/bewest/src/copilot-do-proposal/sdqctl/README.md
- Docs: /home/bewest/src/copilot-do-proposal/sdqctl/docs/
"""


@click.command("help")
@click.argument("topic", required=False)
@click.option("--list", "-l", "list_topics", is_flag=True, help="List available topics")
def help_cmd(topic: str, list_topics: bool) -> None:
    """Show help for commands and topics.

    \b
    Examples:
      sdqctl help              # Overview
      sdqctl help run          # Command help
      sdqctl help directives   # Topic help
      sdqctl help --list       # List all topics
    """
    if list_topics:
        _list_topics()
        return

    if topic is None:
        # Show overview
        console.print(Markdown(get_overview()))
        return

    topic_lower = topic.lower()

    # Check if it's a command
    if topic_lower in COMMAND_HELP:
        console.print(Markdown(COMMAND_HELP[topic_lower]))
        return

    # Check if it's a topic
    if topic_lower in TOPICS:
        console.print(Markdown(TOPICS[topic_lower]))
        return

    # Unknown topic
    console.print(f"[yellow]Unknown topic: {topic}[/yellow]\n")
    _list_topics()


def _list_topics() -> None:
    """List available help topics."""
    console.print("\n[bold]Commands[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="dim")

    for cmd in sorted(COMMAND_HELP.keys()):
        desc = COMMAND_HELP[cmd].split("\n")[2].strip("# ")  # First heading
        table.add_row(cmd, desc)

    console.print(table)

    console.print("\n[bold]Topics[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="dim")

    topic_descriptions = {
        "directives": "ConversationFile directive reference",
        "adapters": "AI provider configuration",
        "workflow": "ConversationFile format guide",
        "variables": "Template variable reference",
        "context": "Context management guide",
        "examples": "Example workflows",
        "ai": "Workflow authoring guidance for AI agents",
        "validation": "Static verification workflow guide",
    }

    for topic in sorted(TOPICS.keys()):
        table.add_row(topic, topic_descriptions.get(topic, ""))

    console.print(table)
    console.print("\nUsage: sdqctl help <command|topic>")
