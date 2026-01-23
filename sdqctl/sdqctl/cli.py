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
from .commands.apply import apply
from .commands.render import render
from .commands.verify import verify
from .core.logging import get_logger, setup_logging
from .core.progress import set_quiet


@click.group()
@click.version_option(version=__version__, prog_name="sdqctl")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
@click.option("-q", "--quiet", is_flag=True, help="Suppress output except errors")
@click.option("-P", "--show-prompt", is_flag=True, help="Show expanded prompts on stderr")
@click.pass_context
def cli(ctx: click.Context, verbose: int, quiet: bool, show_prompt: bool) -> None:
    """sdqctl - Software Defined Quality Control

    Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

    \b
    Commands:
      run      Execute single prompt or ConversationFile
      cycle    Run multi-cycle workflow with compaction
      flow     Execute batch/parallel workflows
      apply    Apply workflow to multiple components
      status   Show session and system status

    \b
    Verbosity (agent output):
      -v       INFO level (progress with context %)
      -vv      DEBUG level (streaming responses)
      -vvv     TRACE level (tool calls, reasoning)
      -q       Quiet mode (errors only)

    \b
    Prompt display:
      -P       Show expanded prompts on stderr (can redirect separately)

    \b
    Examples:
      sdqctl run "Audit authentication module"
      sdqctl run workflow.conv --adapter copilot
      sdqctl -vv run workflow.conv  # with debug output
      sdqctl -P run workflow.conv   # show prompts on stderr
      sdqctl -P run workflow.conv 2>prompts.log  # capture prompts
      sdqctl cycle workflow.conv --max-cycles 5
      sdqctl flow workflows/*.conv --parallel 4
      sdqctl apply workflow.conv --components "lib/*.js" --progress progress.md
    """
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["show_prompt"] = show_prompt
    setup_logging(verbose, quiet)
    set_quiet(quiet)


# Register commands
cli.add_command(run)
cli.add_command(cycle)
cli.add_command(flow)
cli.add_command(apply)
cli.add_command(status)
cli.add_command(render)
cli.add_command(verify)


@cli.command()
@click.argument("name", default=".")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-copilot", is_flag=True, help="Skip GitHub Copilot integration files")
def init(name: str, force: bool, no_copilot: bool) -> None:
    """Initialize sdqctl in a project.
    
    Creates:
    - .sdqctl.yaml config file
    - workflows/ directory with examples
    - .github/copilot-instructions.md (unless --no-copilot)
    - .github/skills/sdqctl-verify.md (unless --no-copilot)
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
    
    # Create GitHub Copilot integration files
    if not no_copilot:
        _create_copilot_files(target_dir, force, console)
    
    console.print("\n[bold]sdqctl initialized![/bold]")
    console.print("\nNext steps:")
    console.print("  1. Edit .sdqctl.yaml to configure your project")
    console.print("  2. Create workflows in the workflows/ directory")
    console.print("  3. Run: sdqctl run workflows/example-audit.conv --dry-run")
    if not no_copilot:
        console.print("  4. Copilot can now use sdqctl commands for verification")


def _create_copilot_files(target_dir, force: bool, console) -> None:
    """Create GitHub Copilot integration files."""
    from pathlib import Path
    
    github_dir = target_dir / ".github"
    skills_dir = github_dir / "skills"
    
    # Create directories
    github_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)
    
    # Create copilot-instructions.md
    instructions_file = github_dir / "copilot-instructions.md"
    if instructions_file.exists() and not force:
        console.print(f"[yellow]Copilot instructions already exist: {instructions_file}[/yellow]")
    else:
        instructions_content = """\
# sdqctl Project Instructions

This project uses **sdqctl** (Software Defined Quality Control) for declarative AI workflows.

## Workflow Files

Workflow files use the `.conv` extension and a Dockerfile-like syntax:
- `MODEL` - AI model to use
- `ADAPTER` - AI provider (copilot, claude, openai, mock)
- `CONTEXT @pattern` - Include files matching pattern
- `PROMPT` - Instructions for the AI
- `OUTPUT-FILE` - Where to write results

## Validation Commands (No LLM Required)

Before committing `.conv` workflow files, validate them:

```bash
# Check syntax of all workflows
sdqctl validate workflows/*.conv

# Inspect parsed structure
sdqctl show <file.conv>

# Preview execution without running
sdqctl run <file.conv> --dry-run
```

## Testing Workflows

Use the mock adapter to test workflow mechanics without LLM calls:

```bash
sdqctl run <file.conv> --adapter mock --verbose
```

## Status Commands

```bash
# Check system configuration
sdqctl status

# List available adapters
sdqctl status --adapters

# View active sessions
sdqctl status --sessions
```

## CI/CD Integration

These commands are safe for CI/CD pipelines (no LLM calls):
- `sdqctl validate` - Syntax validation
- `sdqctl show` - Structure inspection
- `sdqctl run --dry-run` - Execution preview
- `sdqctl run --adapter mock` - Mock execution
- `sdqctl status` - Configuration check
"""
        instructions_file.write_text(instructions_content)
        console.print(f"[green]Created: {instructions_file}[/green]")
    
    # Create sdqctl-verify skill
    skill_file = skills_dir / "sdqctl-verify.md"
    if skill_file.exists() and not force:
        console.print(f"[yellow]Skill already exists: {skill_file}[/yellow]")
    else:
        skill_content = """\
---
name: sdqctl-verify
description: Validate and inspect sdqctl workflow files without LLM calls
tools:
  - bash
---

# sdqctl Verification Skill

Use this skill to validate, inspect, and dry-run sdqctl workflows.
All commands in this skill run **without LLM calls** and are safe for CI/CD.

## Validate Workflow Syntax

Check that a `.conv` file has valid syntax:

```bash
sdqctl validate <workflow.conv>
```

Returns validation status and any syntax errors.

## Show Parsed Structure

Display the internal representation of a workflow:

```bash
sdqctl show <workflow.conv>
```

Shows: model, adapter, mode, prompts, context patterns, output config.

## Preview Execution (Dry Run)

See what would happen without actually running:

```bash
sdqctl run <workflow.conv> --dry-run
```

Shows configuration and prompts that would be sent.

## Test with Mock Adapter

Run the full workflow mechanics without LLM calls:

```bash
sdqctl run <workflow.conv> --adapter mock --verbose
```

Uses canned responses to test workflow flow, checkpoints, and output.

## Check System Status

```bash
# Overview
sdqctl status

# Available adapters
sdqctl status --adapters

# Active sessions
sdqctl status --sessions
```

## Validate All Workflows

```bash
for f in workflows/*.conv; do
  sdqctl validate "$f" || echo "FAILED: $f"
done
```

## When to Use This Skill

- **Before committing**: Validate new/modified `.conv` files
- **In CI/CD**: Verify workflow definitions are valid
- **During review**: Inspect what a workflow will do
- **Debugging**: Test workflow mechanics with mock adapter
"""
        skill_file.write_text(skill_content)
        console.print(f"[green]Created: {skill_file}[/green]")


@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--allow-missing", is_flag=True, help="Warn on missing context files instead of failing")
@click.option("--exclude", "-e", multiple=True, help="Patterns to exclude from validation (can be repeated)")
@click.option("--strict", is_flag=True, help="Fail on any issue (overrides VALIDATION-MODE)")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
def validate(workflow: str, allow_missing: bool, exclude: tuple, strict: bool, json_output: bool) -> None:
    """Validate a ConversationFile.
    
    Checks syntax and references without executing.
    
    \b
    Examples:
      sdqctl validate workflow.conv
      sdqctl validate workflow.conv --allow-missing
      sdqctl validate workflow.conv --exclude "conformance/**/*.yaml"
      sdqctl validate workflow.conv -e "*.yaml" -e "mapping/xdrip/*"
    """
    import json as json_module
    import sys
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    
    from .core.conversation import ConversationFile
    from .core.session import Session
    
    console = Console()
    
    try:
        conv = ConversationFile.from_file(Path(workflow))
        session = Session(conv)
        
        # Determine validation mode
        # CLI flags override file-level settings
        is_lenient = allow_missing or (conv.validation_mode == "lenient" and not strict)
        
        # Validate
        errors = []
        warnings = []
        
        # Check model
        if not conv.model:
            errors.append("Missing MODEL directive")
        
        # Check prompts
        if not conv.prompts:
            errors.append("No PROMPT directives found")
        
        # Check context files with new validation logic
        context_errors, context_warnings = conv.validate_context_files(
            exclude_patterns=list(exclude),
            allow_missing=is_lenient,
        )
        
        # Convert context issues to messages
        for pattern, path in context_errors:
            errors.append(f"Context pattern matches no files: {pattern}")
        for pattern, path in context_warnings:
            warnings.append(f"Context pattern matches no files (optional/excluded): {pattern}")
        
        # JSON output
        if json_output:
            result = {
                "valid": len(errors) == 0,
                "workflow": str(workflow),
                "model": conv.model,
                "adapter": conv.adapter,
                "mode": conv.mode,
                "validation_mode": "lenient" if is_lenient else "strict",
                "prompts": len(conv.prompts),
                "context_patterns": len(conv.context_files) + len(conv.context_files_optional),
                "context_files_found": session.context.get_status()['files_loaded'],
                "errors": errors,
                "warnings": warnings,
            }
            console.print_json(json_module.dumps(result))
            if errors:
                sys.exit(1)
            return
        
        # Report
        if errors:
            console.print("[red]Validation failed:[/red]")
            for error in errors:
                console.print(f"  ✗ {error}")
            if warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  ⚠ {warning}")
            sys.exit(1)
        else:
            # Show warnings if any
            if warnings:
                console.print("[yellow]Warnings (non-blocking):[/yellow]")
                for warning in warnings:
                    console.print(f"  ⚠ {warning}")
                console.print()
            
            validation_mode_str = f"Validation mode: {'lenient' if is_lenient else 'strict'}"
            optional_count = len(conv.context_files_optional)
            exclude_count = len(conv.context_exclude) + len(exclude)
            
            console.print(Panel.fit(
                f"Model: {conv.model}\n"
                f"Adapter: {conv.adapter}\n"
                f"Mode: {conv.mode}\n"
                f"Max Cycles: {conv.max_cycles}\n"
                f"Prompts: {len(conv.prompts)}\n"
                f"Context patterns: {len(conv.context_files)} required, {optional_count} optional\n"
                f"Context excludes: {exclude_count}\n"
                f"Context files found: {session.context.get_status()['files_loaded']}\n"
                f"{validation_mode_str}",
                title="[green]✓ Valid ConversationFile[/green]"
            ))
    
    except Exception as e:
        if json_output:
            console.print_json(json_module.dumps({"valid": False, "error": str(e)}))
        else:
            console.print(f"[red]Error parsing workflow: {e}[/red]")
        sys.exit(1)


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
        console.print(f"  validation_mode: {conv.validation_mode}")
        console.print(f"  context_files: {conv.context_files}")
        console.print(f"  context_files_optional: {conv.context_files_optional}")
        console.print(f"  context_exclude: {conv.context_exclude}")
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
@click.argument("checkpoint", type=click.Path(exists=True), required=False)
@click.option("--list", "list_checkpoints", is_flag=True, help="List available checkpoints")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--dry-run", is_flag=True, help="Show what would happen without executing")
@click.option("--json", "json_output", is_flag=True, help="JSON output format")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output (deprecated, use -v on main command)")
def resume(checkpoint: str, list_checkpoints: bool, adapter: str, dry_run: bool, json_output: bool, verbose: bool) -> None:
    """Resume a paused workflow from checkpoint.
    
    Continues execution from where PAUSE stopped.
    
    Examples:
        sdqctl resume ~/.sdqctl/sessions/abc123/pause.json
        sdqctl resume --list
        sdqctl resume --dry-run checkpoint.json
    """
    import asyncio
    import json
    import logging
    import sys
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    
    from .adapters import get_adapter
    from .adapters.base import AdapterConfig
    from .core.session import Session
    
    console = Console()
    resume_logger = get_logger(__name__)
    
    # Boost verbosity if --verbose flag used on this command
    if verbose and not resume_logger.isEnabledFor(logging.INFO):
        setup_logging(1)
    
    # Handle --list flag
    if list_checkpoints:
        _list_checkpoints(console, json_output)
        return
    
    # Require checkpoint if not listing
    if not checkpoint:
        console.print("[red]Error: checkpoint path required (or use --list)[/red]")
        sys.exit(1)
    
    # Handle --dry-run flag
    if dry_run:
        _dry_run_resume(checkpoint, console, json_output)
        return
    
    asyncio.run(_resume_async(checkpoint, adapter, console, json_output))


def _list_checkpoints(console, json_output: bool) -> None:
    """List all available pause checkpoints."""
    import json as json_module
    from pathlib import Path
    
    sessions_dir = Path(".sdqctl/sessions")
    if not sessions_dir.exists():
        if json_output:
            console.print_json('{"checkpoints": []}')
        else:
            console.print("[yellow]No sessions directory found[/yellow]")
        return
    
    checkpoints = list(sessions_dir.glob("*/pause.json"))
    if not checkpoints:
        if json_output:
            console.print_json('{"checkpoints": []}')
        else:
            console.print("[yellow]No checkpoints found[/yellow]")
        return
    
    if json_output:
        result = []
        for cp in sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json_module.loads(cp.read_text())
                result.append({
                    "path": str(cp),
                    "message": data.get("message", ""),
                    "timestamp": data.get("timestamp", ""),
                    "session_id": data.get("session_id", ""),
                })
            except Exception:
                result.append({"path": str(cp), "error": "corrupt"})
        console.print_json(json_module.dumps({"checkpoints": result}))
    else:
        console.print("[bold]Available checkpoints:[/bold]\n")
        for cp in sorted(checkpoints, key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json_module.loads(cp.read_text())
                msg = data.get("message", "")[:60]
                ts = data.get("timestamp", "")[:19]
                console.print(f"  {cp}")
                console.print(f"    [dim]{ts} - {msg}[/dim]\n")
            except Exception:
                console.print(f"  {cp} [red](corrupt)[/red]")


def _dry_run_resume(checkpoint: str, console, json_output: bool) -> None:
    """Show what would happen on resume without executing."""
    import json as json_module
    from pathlib import Path
    from rich.panel import Panel
    from .core.session import Session
    
    checkpoint_path = Path(checkpoint)
    try:
        session = Session.load_from_pause(checkpoint_path)
    except ValueError as e:
        if json_output:
            console.print_json(json_module.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error loading checkpoint: {e}[/red]")
        return
    
    conv = session.conversation
    
    if json_output:
        result = {
            "dry_run": True,
            "session_id": session.id,
            "workflow": str(conv.source_path) if conv.source_path else None,
            "adapter": conv.adapter,
            "model": conv.model,
            "resume_from_prompt": session.state.prompt_index + 1,
            "total_prompts": len(conv.prompts),
            "cycle_number": session.state.cycle_number + 1,
            "messages_in_context": len(session.state.messages),
            "prompts_remaining": conv.prompts[session.state.prompt_index:],
        }
        console.print_json(json_module.dumps(result))
    else:
        console.print(Panel.fit(
            f"Session ID: {session.id}\n"
            f"Workflow: {conv.source_path}\n"
            f"Adapter: {conv.adapter}\n"
            f"Model: {conv.model}\n"
            f"Resume from prompt: {session.state.prompt_index + 1}/{len(conv.prompts)}\n"
            f"Cycle: {session.state.cycle_number + 1}\n"
            f"Messages in context: {len(session.state.messages)}",
            title="[yellow]Dry Run - Resume Configuration[/yellow]"
        ))
        
        console.print("\n[bold]Prompts remaining:[/bold]")
        for i, prompt in enumerate(conv.prompts[session.state.prompt_index:], session.state.prompt_index + 1):
            preview = prompt[:80] + "..." if len(prompt) > 80 else prompt
            console.print(f"  {i}. {preview}")
        
        console.print("\n[yellow]Dry run - no execution[/yellow]")


async def _resume_async(checkpoint: str, adapter_name: str, console, json_output: bool = False) -> None:
    """Async implementation of resume command."""
    import json as json_module
    import logging
    from pathlib import Path
    from rich.panel import Panel
    
    from .adapters import get_adapter
    from .adapters.base import AdapterConfig
    from .core.session import Session
    
    resume_logger = get_logger(__name__)
    checkpoint_path = Path(checkpoint)
    
    try:
        session = Session.load_from_pause(checkpoint_path)
        conv = session.conversation
        
        if not json_output:
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
            if not json_output:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Using mock adapter instead[/yellow]")
            ai_adapter = get_adapter("mock")
        
        await ai_adapter.start()
        
        adapter_session = await ai_adapter.create_session(
            AdapterConfig(model=conv.model, streaming=True)
        )
        
        session.state.status = "running"
        responses = []
        
        # Build pause point lookup
        pause_after = {idx: msg for idx, msg in conv.pause_points}
        
        # Resume from saved prompt index
        start_idx = session.state.prompt_index
        
        for i in range(start_idx, len(conv.prompts)):
            prompt = conv.prompts[i]
            
            resume_logger.info(f"Sending prompt {i + 1}/{len(conv.prompts)}...")
            
            response = await ai_adapter.send(adapter_session, prompt)
            responses.append(response)
            
            resume_logger.debug(f"{response[:200]}..." if len(response) > 200 else response)
            
            session.add_message("user", prompt)
            session.add_message("assistant", response)
            
            # Check for another PAUSE
            if i in pause_after:
                pause_msg = pause_after[i]
                session.state.prompt_index = i + 1
                new_checkpoint = session.save_pause_checkpoint(pause_msg)
                
                await ai_adapter.destroy_session(adapter_session)
                await ai_adapter.stop()
                
                if json_output:
                    result = {
                        "status": "paused",
                        "message": pause_msg,
                        "checkpoint": str(new_checkpoint),
                        "prompts_completed": i - start_idx + 1,
                        "responses": responses,
                    }
                    console.print_json(json_module.dumps(result))
                else:
                    console.print(f"\n[yellow]⏸  PAUSED: {pause_msg}[/yellow]")
                    console.print(f"[dim]Checkpoint saved: {new_checkpoint}[/dim]")
                    console.print(f"\n[bold]To resume:[/bold] sdqctl resume {new_checkpoint}")
                return
        
        # Completed successfully
        await ai_adapter.destroy_session(adapter_session)
        await ai_adapter.stop()
        
        session.state.status = "completed"
        
        # Clean up pause checkpoint
        checkpoint_path.unlink(missing_ok=True)
        
        # Write output if configured
        if conv.output_file:
            output_content = "\n\n---\n\n".join(
                m.content for m in session.state.messages if m.role == "assistant"
            )
            Path(conv.output_file).write_text(output_content)
            if not json_output:
                console.print(f"[green]Output written to {conv.output_file}[/green]")
        
        if json_output:
            result = {
                "status": "completed",
                "prompts_completed": len(conv.prompts) - start_idx,
                "responses": responses,
                "output_file": conv.output_file,
            }
            console.print_json(json_module.dumps(result))
        else:
            console.print("\n[green]✓ Workflow completed[/green]")
    
    except Exception as e:
        if json_output:
            console.print_json(json_module.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error resuming: {e}[/red]")
        raise


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
