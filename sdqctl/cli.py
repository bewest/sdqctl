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
from .commands.apply import apply
from .commands.artifact import artifact
from .commands.flow import flow
from .commands.help import help_cmd
from .commands.drift import drift
from .commands.init import init
from .commands.iterate import iterate
from .commands.lsp import lsp
from .commands.plugin import plugin
from .commands.refcat import refcat
from .commands.render import render
from .commands.resume import resume
from .commands.run import run
from .commands.sessions import sessions
from .commands.status import status
from .commands.verify import verify
from .commands.workspace import workspace
from .core.logging import setup_logging
from .core.progress import set_quiet, set_timestamps


@click.group()
@click.version_option(version=__version__, prog_name="sdqctl")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
@click.option("-q", "--quiet", is_flag=True, help="Suppress output except errors")
@click.option("-P", "--show-prompt", is_flag=True, help="Show expanded prompts on stderr")
@click.option("--json-errors", is_flag=True, help="Output errors as JSON for CI integration")
@click.pass_context
def cli(
    ctx: click.Context, verbose: int, quiet: bool, show_prompt: bool, json_errors: bool
) -> None:
    """sdqctl - Software Defined Quality Control

    Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

    \b
    Commands:
      iterate  Execute workflow with optional multi-cycle iteration
      run      Execute single prompt or ConversationFile
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
    Error output:
      --json-errors  Output errors as structured JSON (for CI integration)

    \b
    Examples:
      sdqctl iterate workflow.conv              # single execution
      sdqctl iterate workflow.conv -n 5         # multi-cycle
      sdqctl run "Audit authentication module"  # inline prompt
      sdqctl -vv iterate workflow.conv          # with debug output
      sdqctl flow workflows/*.conv --parallel 4
      sdqctl apply workflow.conv --components "lib/*.js" --progress progress.md
      sdqctl --json-errors iterate workflow.conv 2>&1 | jq .error  # CI mode
    """
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["show_prompt"] = show_prompt
    ctx.obj["json_errors"] = json_errors
    setup_logging(verbose, quiet)
    # When json_errors is enabled, also set quiet to suppress progress messages
    set_quiet(quiet or json_errors)
    # Enable timestamps when verbose to align with logger format (Q-019A)
    set_timestamps(verbose >= 1 and not quiet and not json_errors)


# Register commands
cli.add_command(run)
cli.add_command(iterate)
cli.add_command(flow)
cli.add_command(apply)
cli.add_command(status)
cli.add_command(render)
cli.add_command(verify)
cli.add_command(lsp)
cli.add_command(plugin)
cli.add_command(drift)
cli.add_command(refcat)
cli.add_command(artifact)
cli.add_command(sessions)
cli.add_command(help_cmd)
cli.add_command(workspace)


# Deprecated alias for 'cycle' command
@cli.command("cycle", hidden=True)
@click.argument("targets", nargs=-1)
@click.option("--from-json", "from_json", type=click.Path())
@click.option("--max-cycles", "-n", type=int, default=None)
@click.option(
    "--session-mode", "-s",
    type=click.Choice(["accumulate", "compact", "fresh"]),
    default="accumulate",
)
@click.option("--adapter", "-a", default=None)
@click.option("--model", "-m", default=None)
@click.option("--context", "-c", multiple=True)
@click.option("--allow-files", multiple=True)
@click.option("--deny-files", multiple=True)
@click.option("--allow-dir", multiple=True)
@click.option("--deny-dir", multiple=True)
@click.option("--session-name", default=None)
@click.option("--checkpoint-dir", type=click.Path(), default=None)
@click.option("--prologue", multiple=True)
@click.option("--epilogue", multiple=True)
@click.option("--header", multiple=True)
@click.option("--footer", multiple=True)
@click.option("--output", "-o", default=None)
@click.option("--event-log", default=None)
@click.option("--json", "json_output", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--render-only", is_flag=True)
@click.option("--compaction-min", type=int, default=None)
@click.option("--min-compaction-density", type=int, default=None, hidden=True)
@click.option("--no-infinite-sessions", is_flag=True)
@click.option("--compaction-threshold", type=int, default=None)
@click.option("--compaction-max", type=int, default=None)
@click.option("--buffer-threshold", type=int, default=None, hidden=True)
@click.option("--no-stop-file-prologue", is_flag=True)
@click.option("--stop-file-nonce", default=None)
@click.pass_context
def cycle_alias(ctx, **kwargs):
    """[DEPRECATED] Use 'sdqctl iterate' instead."""
    click.secho(
        "⚠ 'sdqctl cycle' is deprecated. Use 'sdqctl iterate' instead.",
        fg="yellow", err=True
    )
    ctx.invoke(iterate, **kwargs)


# Register init command from commands/init.py
cli.add_command(init)


@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
@click.option(
    "--allow-missing", is_flag=True,
    help="Warn on missing context files instead of failing",
)
@click.option(
    "--exclude", "-e", multiple=True,
    help="Patterns to exclude from validation (can be repeated)",
)
@click.option("--strict", is_flag=True, help="Fail on any issue (overrides VALIDATION-MODE)")
@click.option("--check-model", is_flag=True, help="Validate MODEL-REQUIRES can be resolved")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
def validate(
    workflow: str,
    allow_missing: bool,
    exclude: tuple,
    strict: bool,
    check_model: bool,
    json_output: bool,
) -> None:
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

        # Check REFCAT refs
        refcat_errors, refcat_warnings = conv.validate_refcat_refs(
            allow_missing=is_lenient,
        )

        # Convert REFCAT issues to messages
        for ref, msg in refcat_errors:
            errors.append(f"REFCAT ref invalid: {ref} ({msg})")
        for ref, msg in refcat_warnings:
            warnings.append(f"REFCAT ref invalid (allowed-missing): {ref} ({msg})")

        # Check HELP topics
        help_errors = conv.validate_help_topics()
        for topic, msg in help_errors:
            errors.append(f"HELP topic invalid: {msg}")

        # Check ELIDE chain compatibility
        elide_errors = conv.validate_elide_chains()
        for msg in elide_errors:
            errors.append(f"ELIDE chain invalid: {msg}")

        # Check REQUIRE directives (pre-flight checks)
        require_errors = conv.validate_requirements()
        for req, msg in require_errors:
            errors.append(f"REQUIRE failed: {msg}")

        # Check MODEL-REQUIRES resolution if requested
        resolved_model = None
        model_req_count = 0
        if conv.model_requirements:
            model_req_count = len(conv.model_requirements.requirements)
            if check_model:
                from .core.models import resolve_model
                resolved_model = resolve_model(conv.model_requirements, fallback=conv.model)
                if resolved_model is None and not conv.model:
                    errors.append("MODEL-REQUIRES cannot be resolved to any known model")
            else:
                # Just report we have model requirements
                from .core.models import resolve_model
                resolved_model = resolve_model(conv.model_requirements, fallback=conv.model)

        # JSON output
        if json_output:
            result = {
                "valid": len(errors) == 0,
                "workflow": str(workflow),
                "model": conv.model,
                "resolved_model": resolved_model,
                "model_requirements": model_req_count,
                "adapter": conv.adapter,
                "mode": conv.mode,
                "validation_mode": "lenient" if is_lenient else "strict",
                "prompts": len(conv.prompts),
                "context_patterns": len(conv.context_files) + len(conv.context_files_optional),
                "context_files_found": session.context.get_status()['files_loaded'],
                "requirements": len(conv.requirements),
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
            req_count = len(conv.requirements)

            # Build requirements line if any
            req_line = f"Requirements: {req_count} (all passed)\n" if req_count > 0 else ""

            # Build model requirements line if any
            model_req_line = ""
            if model_req_count > 0:
                model_req_line = f"Model requirements: {model_req_count}\n"
                if resolved_model:
                    model_req_line += f"Resolved model: {resolved_model}\n"

            console.print(Panel.fit(
                f"Model: {conv.model}\n"
                f"Adapter: {conv.adapter}\n"
                f"Mode: {conv.mode}\n"
                f"Max Cycles: {conv.max_cycles}\n"
                f"Prompts: {len(conv.prompts)}\n"
                f"Context patterns: {len(conv.context_files)} required, {optional_count} optional\n"
                f"Context excludes: {exclude_count}\n"
                f"Context files found: {session.context.get_status()['files_loaded']}\n"
                f"{req_line}"
                f"{model_req_line}"
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


# Register resume command from commands/resume.py
cli.add_command(resume)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
