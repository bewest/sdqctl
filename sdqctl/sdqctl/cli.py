#!/usr/bin/env python3
"""
sdqctl - Software Defined Quality Control

A vendor-agnostic CLI for orchestrating AI-assisted development workflows
with reproducible context management and declarative workflow definitions.

Usage:
    sdqctl run "Audit authentication module"
    sdqctl run workflow.conv
    sdqctl cycle workflow.conv --max-cycles 5
    sdqctl flow workflows/*.conv --parallel 4
    sdqctl status

For more information: sdqctl --help
"""

import click

from . import __version__
from .commands.run import run
from .commands.cycle import cycle
from .commands.flow import flow
from .commands.status import status


@click.group()
@click.version_option(version=__version__, prog_name="sdqctl")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """sdqctl - Software Defined Quality Control

    Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

    \b
    Commands:
      run      Execute single prompt or ConversationFile
      cycle    Run multi-cycle workflow with compaction
      flow     Execute batch/parallel workflows
      status   Show session and system status

    \b
    Examples:
      sdqctl run "Audit authentication module"
      sdqctl run workflow.conv --adapter copilot
      sdqctl cycle workflow.conv --max-cycles 5
      sdqctl flow workflows/*.conv --parallel 4
    """
    ctx.ensure_object(dict)


# Register commands
cli.add_command(run)
cli.add_command(cycle)
cli.add_command(flow)
cli.add_command(status)


@cli.command()
@click.argument("name", default=".")
@click.option("--force", is_flag=True, help="Overwrite existing files")
def init(name: str, force: bool) -> None:
    """Initialize sdqctl in a project.
    
    Creates a .sdqctl.yaml config file and example workflows.
    """
    from pathlib import Path
    from rich.console import Console
    
    console = Console()
    target_dir = Path(name).resolve()
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True)
    
    config_file = target_dir / ".sdqctl.yaml"
    workflows_dir = target_dir / "workflows"
    
    # Create config
    if config_file.exists() and not force:
        console.print(f"[yellow]Config already exists: {config_file}[/yellow]")
    else:
        config_content = """\
# sdqctl configuration
# See: https://github.com/bewest/copilot-do-proposal

project:
  name: my-project
  
defaults:
  adapter: copilot
  model: gpt-4
  
context:
  limit: 80%
  on_limit: compact
  
checkpoints:
  enabled: true
  directory: .sdqctl/checkpoints
"""
        config_file.write_text(config_content)
        console.print(f"[green]Created: {config_file}[/green]")
    
    # Create workflows directory
    if not workflows_dir.exists():
        workflows_dir.mkdir()
        console.print(f"[green]Created: {workflows_dir}/[/green]")
    
    # Create example workflow
    example_workflow = workflows_dir / "example-audit.conv"
    if example_workflow.exists() and not force:
        console.print(f"[yellow]Example already exists: {example_workflow}[/yellow]")
    else:
        example_content = """\
# Example security audit workflow
# Run with: sdqctl run workflows/example-audit.conv

MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 1

# Context files to include
# CONTEXT @lib/auth/*.js
# CONTEXT @tests/auth.test.js

# Context window settings
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

PROMPT Analyze the codebase for security vulnerabilities.
PROMPT Focus on authentication, input validation, and data handling.
PROMPT Generate a security report with severity ratings.

OUTPUT-FORMAT markdown
OUTPUT-FILE security-audit.md
"""
        example_workflow.write_text(example_content)
        console.print(f"[green]Created: {example_workflow}[/green]")
    
    console.print("\n[bold]sdqctl initialized![/bold]")
    console.print("\nNext steps:")
    console.print("  1. Edit .sdqctl.yaml to configure your project")
    console.print("  2. Create workflows in the workflows/ directory")
    console.print("  3. Run: sdqctl run workflows/example-audit.conv --dry-run")


@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
def validate(workflow: str) -> None:
    """Validate a ConversationFile.
    
    Checks syntax and references without executing.
    """
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    
    from .core.conversation import ConversationFile
    from .core.session import Session
    
    console = Console()
    
    try:
        conv = ConversationFile.from_file(Path(workflow))
        session = Session(conv)
        
        # Validate
        issues = []
        
        # Check model
        if not conv.model:
            issues.append("Missing MODEL directive")
        
        # Check prompts
        if not conv.prompts:
            issues.append("No PROMPT directives found")
        
        # Check context files
        for pattern in conv.context_files:
            files = session.context.resolve_pattern(pattern)
            if not files:
                issues.append(f"Context pattern matches no files: {pattern}")
        
        # Report
        if issues:
            console.print("[red]Validation failed:[/red]")
            for issue in issues:
                console.print(f"  - {issue}")
        else:
            console.print(Panel.fit(
                f"Model: {conv.model}\n"
                f"Adapter: {conv.adapter}\n"
                f"Mode: {conv.mode}\n"
                f"Max Cycles: {conv.max_cycles}\n"
                f"Prompts: {len(conv.prompts)}\n"
                f"Context patterns: {len(conv.context_files)}\n"
                f"Context files found: {session.context.get_status()['files_loaded']}",
                title="[green]✓ Valid ConversationFile[/green]"
            ))
    
    except Exception as e:
        console.print(f"[red]Error parsing workflow: {e}[/red]")


@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
def show(workflow: str) -> None:
    """Display a parsed ConversationFile.
    
    Shows the internal representation of a workflow file.
    """
    from pathlib import Path
    from rich.console import Console
    from rich.syntax import Syntax
    
    from .core.conversation import ConversationFile
    
    console = Console()
    
    try:
        conv = ConversationFile.from_file(Path(workflow))
        
        # Show original content
        original = Path(workflow).read_text()
        console.print("[bold]Original file:[/bold]")
        console.print(Syntax(original, "dockerfile", theme="monokai", line_numbers=True))
        
        # Show parsed representation
        console.print("\n[bold]Parsed representation:[/bold]")
        console.print(f"  model: {conv.model}")
        console.print(f"  adapter: {conv.adapter}")
        console.print(f"  mode: {conv.mode}")
        console.print(f"  max_cycles: {conv.max_cycles}")
        console.print(f"  context_files: {conv.context_files}")
        console.print(f"  context_limit: {conv.context_limit}")
        console.print(f"  on_context_limit: {conv.on_context_limit}")
        console.print(f"  prompts: {len(conv.prompts)} total")
        for i, prompt in enumerate(conv.prompts, 1):
            preview = prompt[:60] + "..." if len(prompt) > 60 else prompt
            console.print(f"    [{i}] {preview}")
        console.print(f"  compact_preserve: {conv.compact_preserve}")
        console.print(f"  checkpoint_after: {conv.checkpoint_after}")
        console.print(f"  pause_points: {conv.pause_points}")
        console.print(f"  output_format: {conv.output_format}")
        console.print(f"  output_file: {conv.output_file}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument("checkpoint", type=click.Path(exists=True))
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def resume(checkpoint: str, adapter: str, verbose: bool) -> None:
    """Resume a paused workflow from checkpoint.
    
    Continues execution from where PAUSE stopped.
    
    Example:
        sdqctl resume ~/.sdqctl/sessions/abc123/pause.json
    """
    import asyncio
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    
    from .adapters import get_adapter
    from .adapters.base import AdapterConfig
    from .core.session import Session
    
    console = Console()
    
    asyncio.run(_resume_async(checkpoint, adapter, verbose, console))


async def _resume_async(checkpoint: str, adapter_name: str, verbose: bool, console) -> None:
    """Async implementation of resume command."""
    from pathlib import Path
    from rich.panel import Panel
    
    from .adapters import get_adapter
    from .adapters.base import AdapterConfig
    from .core.session import Session
    
    checkpoint_path = Path(checkpoint)
    
    try:
        session = Session.load_from_pause(checkpoint_path)
        conv = session.conversation
        
        console.print(Panel.fit(
            f"Session ID: {session.id}\n"
            f"Workflow: {conv.source_path}\n"
            f"Resuming from prompt: {session.state.prompt_index + 1}/{len(conv.prompts)}\n"
            f"Messages in history: {len(session.state.messages)}",
            title="[blue]Resuming Paused Workflow[/blue]"
        ))
        
        # Apply adapter override
        if adapter_name:
            conv.adapter = adapter_name
        
        # Get adapter
        try:
            ai_adapter = get_adapter(conv.adapter)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Using mock adapter instead[/yellow]")
            ai_adapter = get_adapter("mock")
        
        await ai_adapter.start()
        
        adapter_session = await ai_adapter.create_session(
            AdapterConfig(model=conv.model, streaming=True)
        )
        
        session.state.status = "running"
        
        # Build pause point lookup
        pause_after = {idx: msg for idx, msg in conv.pause_points}
        
        # Resume from saved prompt index
        start_idx = session.state.prompt_index
        
        for i in range(start_idx, len(conv.prompts)):
            prompt = conv.prompts[i]
            
            if verbose:
                console.print(f"\n[bold blue]Sending prompt {i + 1}/{len(conv.prompts)}...[/bold blue]")
            
            response = await ai_adapter.send(adapter_session, prompt)
            
            if verbose:
                console.print(f"[dim]{response[:200]}...[/dim]" if len(response) > 200 else f"[dim]{response}[/dim]")
            
            session.add_message("user", prompt)
            session.add_message("assistant", response)
            
            # Check for another PAUSE
            if i in pause_after:
                pause_msg = pause_after[i]
                session.state.prompt_index = i + 1
                new_checkpoint = session.save_pause_checkpoint(pause_msg)
                
                await ai_adapter.destroy_session(adapter_session)
                await ai_adapter.stop()
                
                console.print(f"\n[yellow]⏸  PAUSED: {pause_msg}[/yellow]")
                console.print(f"[dim]Checkpoint saved: {new_checkpoint}[/dim]")
                console.print(f"\n[bold]To resume:[/bold] sdqctl resume {new_checkpoint}")
                return
        
        # Completed successfully
        await ai_adapter.destroy_session(adapter_session)
        await ai_adapter.stop()
        
        session.state.status = "completed"
        console.print("\n[green]✓ Workflow completed[/green]")
        
        # Clean up pause checkpoint
        checkpoint_path.unlink(missing_ok=True)
        
        # Write output if configured
        if conv.output_file:
            output_content = "\n\n---\n\n".join(
                m.content for m in session.state.messages if m.role == "assistant"
            )
            Path(conv.output_file).write_text(output_content)
            console.print(f"[green]Output written to {conv.output_file}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error resuming: {e}[/red]")
        raise


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
