"""
sdqctl help - Comprehensive help system.

Usage:
    sdqctl help                    # Overview
    sdqctl help <command>          # Command help (run, cycle, flow, etc.)
    sdqctl help <topic>            # Topic help (directives, adapters, workflow)
    sdqctl help --interactive      # Interactive browsing mode
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
| `gap-ids` | Gap ID taxonomy for AID alignment |
| `5-facet` | 5-facet documentation pattern |
| `stpa` | STPA hazard analysis guide |
| `conformance` | Conformance testing format |
| `nightscout` | Nightscout ecosystem overview |

## Getting Help

```bash
sdqctl help                  # This overview
sdqctl help run              # Command help
sdqctl help directives       # Topic help
sdqctl help -i               # Interactive browsing
sdqctl <command> --help      # Click's built-in help
```

## Documentation

- README: /home/bewest/src/copilot-do-proposal/sdqctl/README.md
- Docs: /home/bewest/src/copilot-do-proposal/sdqctl/docs/
"""


@click.command("help")
@click.argument("topic", required=False)
@click.option("--list", "-l", "list_topics", is_flag=True, help="List available topics")
@click.option("--interactive", "-i", is_flag=True, help="Interactive browsing mode")
def help_cmd(topic: str, list_topics: bool, interactive: bool) -> None:
    """Show help for commands and topics.

    \b
    Examples:
      sdqctl help              # Overview
      sdqctl help run          # Command help
      sdqctl help directives   # Topic help
      sdqctl help --list       # List all topics
      sdqctl help -i           # Interactive browsing
    """
    if interactive:
        _interactive_help()
        return

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


def _interactive_help() -> None:
    """Run interactive help browser."""
    from rich.panel import Panel
    from rich.prompt import Prompt

    console.print(Panel.fit(
        "[bold cyan]sdqctl Interactive Help[/bold cyan]\n\n"
        "Type a command or topic name to view help.\n"
        "Type [bold]list[/bold] to see all topics.\n"
        "Type [bold]q[/bold] or [bold]quit[/bold] to exit.",
        title="Help Browser"
    ))

    while True:
        try:
            query = Prompt.ask("\n[cyan]help>[/cyan]", default="").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting help browser.[/dim]")
            break

        if not query:
            continue

        if query in ("q", "quit", "exit"):
            console.print("[dim]Exiting help browser.[/dim]")
            break

        if query in ("list", "ls", "?"):
            _list_topics()
            continue

        if query in ("overview", "home", "h"):
            console.print(Markdown(get_overview()))
            continue

        # Check commands
        if query in COMMAND_HELP:
            console.print(Markdown(COMMAND_HELP[query]))
            continue

        # Check topics
        if query in TOPICS:
            console.print(Markdown(TOPICS[query]))
            continue

        # Fuzzy match - check if query is prefix of any topic/command
        matches = []
        for name in list(COMMAND_HELP.keys()) + list(TOPICS.keys()):
            if name.startswith(query):
                matches.append(name)

        if len(matches) == 1:
            match = matches[0]
            if match in COMMAND_HELP:
                console.print(Markdown(COMMAND_HELP[match]))
            else:
                console.print(Markdown(TOPICS[match]))
            continue
        elif len(matches) > 1:
            console.print(f"[yellow]Multiple matches:[/yellow] {', '.join(matches)}")
            continue

        console.print(f"[yellow]Unknown: {query}[/yellow] - type 'list' to see available topics")


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
