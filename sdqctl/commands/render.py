"""
sdqctl render - Render workflow prompts without executing.

Produces fully-resolved prompts with all context, templates, prologues,
and epilogues expanded. Useful for debugging and templating.

Usage:
    sdqctl render workflow.conv
    sdqctl render workflow.conv --json
    sdqctl render workflow.conv -o rendered.md
    sdqctl render run workflow.conv     # Equivalent to: sdqctl run --render-only
    sdqctl render cycle workflow.conv   # Equivalent to: sdqctl cycle --render-only
    sdqctl render apply workflow.conv   # Equivalent to: sdqctl apply --render-only
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ..core.conversation import ConversationFile
from ..core.exceptions import MissingContextFiles
from ..core.logging import get_logger
from ..core.renderer import (
    format_rendered_json,
    format_rendered_markdown,
    render_workflow,
)

logger = get_logger(__name__)
console = Console()


def _render_common(
    workflow: str,
    session_mode: str,
    cycles: Optional[int],
    cycle: Optional[int],
    prompt: Optional[int],
    output: Optional[str],
    json_output: bool,
    no_context: bool,
    no_sections: bool,
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    plan_mode: bool = False,
) -> None:
    """Common render logic for all render subcommands.

    Args:
        plan_mode: If True, show @file references instead of expanding content
    """
    try:
        # Load workflow
        conv = ConversationFile.from_file(Path(workflow))
        logger.info(f"Loaded workflow: {workflow}")

        # Apply CLI overrides
        if prologue:
            conv.prologues = list(prologue) + conv.prologues
        if epilogue:
            conv.epilogues = list(epilogue) + conv.epilogues

        # Validate context files (render is lenient - only warns)
        errors, warns = conv.validate_context_files(allow_missing=True)
        all_issues = errors + warns
        if all_issues:
            console.print("[yellow]Warning: Some context files not found:[/yellow]")
            for pattern, resolved in all_issues:
                console.print(f"[yellow]  - {pattern}[/yellow]")

        # Render workflow
        rendered = render_workflow(
            conv=conv,
            session_mode=session_mode,
            max_cycles=cycles,
            include_context=not no_context,
        )

        # Filter to specific cycle if requested
        if cycle is not None:
            if cycle < 1 or cycle > len(rendered.cycles):
                console.print(
                    f"[red]Error: Cycle {cycle} not in range "
                    f"1-{len(rendered.cycles)}[/red]"
                )
                sys.exit(1)
            rendered.cycles = [rendered.cycles[cycle - 1]]

        # Filter to specific prompt if requested
        if prompt is not None:
            for c in rendered.cycles:
                if prompt < 1 or prompt > len(c.prompts):
                    console.print(
                        f"[red]Error: Prompt {prompt} not in range "
                        f"1-{len(c.prompts)}[/red]"
                    )
                    sys.exit(1)
                c.prompts = [c.prompts[prompt - 1]]

        # Format output
        if json_output:
            rendered_json = format_rendered_json(rendered, plan_mode=plan_mode)
            output_content = json.dumps(rendered_json, indent=2)
        else:
            output_content = format_rendered_markdown(
                rendered,
                show_sections=not no_sections,
                include_context=not no_context,
                plan_mode=plan_mode,
            )

        # Write output
        if output:
            output_path = Path(output)

            # Handle fresh mode with directory output
            if session_mode == "fresh" and output_path.suffix == "" and len(rendered.cycles) > 1:
                # Write separate files per cycle
                output_path.mkdir(parents=True, exist_ok=True)
                for c in rendered.cycles:
                    # Create single-cycle rendered workflow for formatting
                    single_cycle_copy = type(rendered)(
                        workflow_path=rendered.workflow_path,
                        workflow_name=rendered.workflow_name,
                        session_mode=rendered.session_mode,
                        adapter=rendered.adapter,
                        model=rendered.model,
                        max_cycles=rendered.max_cycles,
                        cycles=[c],
                        base_variables=rendered.base_variables,
                    )

                    if json_output:
                        rendered_json = format_rendered_json(
                            single_cycle_copy, plan_mode=plan_mode
                        )
                        cycle_content = json.dumps(rendered_json, indent=2)
                        cycle_file = output_path / f"cycle-{c.number}.json"
                    else:
                        cycle_content = format_rendered_markdown(
                            single_cycle_copy,
                            show_sections=not no_sections,
                            include_context=not no_context,
                            plan_mode=plan_mode,
                        )
                        cycle_file = output_path / f"cycle-{c.number}.md"

                    cycle_file.write_text(cycle_content)
                    console.print(f"[green]Wrote {cycle_file}[/green]")
            else:
                # Write single file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output_content)
                console.print(f"[green]Wrote {output_path}[/green]")
        else:
            # Output to stdout
            if json_output:
                console.print_json(output_content)
            else:
                console.print(output_content)

    except MissingContextFiles as e:
        console.print(f"[red]Error: Missing mandatory context files: {e.patterns}[/red]")
        sys.exit(e.exit_code)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Render failed")
        sys.exit(1)


# Common options for all render subcommands
def common_render_options(f):
    """Decorator for common render options."""
    f = click.option(
        "--session-mode", "-s",
        type=click.Choice(["accumulate", "compact", "fresh"]),
        default="accumulate",
        help="Session mode (affects output structure for fresh)"
    )(f)
    f = click.option(
        "--cycles", "-n", type=int, default=None,
        help="Number of cycles to render"
    )(f)
    f = click.option(
        "--cycle", type=int, default=None,
        help="Render only this cycle number"
    )(f)
    f = click.option(
        "--prompt", type=int, default=None,
        help="Render only this prompt number"
    )(f)
    f = click.option("--output", "-o", default=None, help="Output file or directory")(f)
    f = click.option("--json", "json_output", is_flag=True, help="JSON output format")(f)
    f = click.option("--no-context", is_flag=True, help="Exclude context file contents")(f)
    f = click.option("--no-sections", is_flag=True, help="Omit section markers")(f)
    f = click.option(
        "--prologue", multiple=True,
        help="Additional prologue (inline text or @file)"
    )(f)
    f = click.option(
        "--epilogue", multiple=True,
        help="Additional epilogue (inline text or @file)"
    )(f)
    f = click.option(
        "--plan", "plan_mode", is_flag=True,
        help="Show @file references without expanding content"
    )(f)
    f = click.option(
        "--full", "full_mode", is_flag=True,
        help="Fully expand all content (default)"
    )(f)
    return f


@click.group("render")
@click.pass_context
def render(ctx: click.Context) -> None:
    """Render workflow prompts without executing.

    Produces fully-resolved prompts with all context, templates,
    prologues, and epilogues expanded. No AI calls are made.

    \b
    Commands:
      render run      Render a single-cycle workflow
      render cycle    Render a multi-cycle workflow
      render apply    Render a per-component workflow

    \b
    Modes:
      --plan    Show @file references instead of expanding content
      --full    Fully expand all content (default)

    \b
    Examples:
      sdqctl render run workflow.conv                  # stdout
      sdqctl render run workflow.conv --plan           # show file refs only
      sdqctl render run workflow.conv --json           # JSON format
      sdqctl render cycle workflow.conv -n 3           # render 3 cycles
    """
    pass


# Default render command (backwards compat with old `sdqctl render workflow.conv`)
@render.command("file", hidden=False)
@click.argument("workflow", type=click.Path(exists=True))
@common_render_options
def render_file(
    workflow: str,
    session_mode: str,
    cycles: Optional[int],
    cycle: Optional[int],
    prompt: Optional[int],
    output: Optional[str],
    json_output: bool,
    no_context: bool,
    no_sections: bool,
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    plan_mode: bool,
    full_mode: bool,
) -> None:
    """Render a workflow file (legacy, use 'render run' instead).

    \b
    Examples:
      sdqctl render file workflow.conv
      sdqctl render file workflow.conv --plan
    """
    _render_common(
        workflow=workflow,
        session_mode=session_mode,
        cycles=cycles,
        cycle=cycle,
        prompt=prompt,
        output=output,
        json_output=json_output,
        no_context=no_context,
        no_sections=no_sections,
        prologue=prologue,
        epilogue=epilogue,
        plan_mode=plan_mode,
    )


@render.command("run")
@click.argument("workflow", type=click.Path(exists=True))
@common_render_options
def render_run(
    workflow: str,
    session_mode: str,
    cycles: Optional[int],
    cycle: Optional[int],
    prompt: Optional[int],
    output: Optional[str],
    json_output: bool,
    no_context: bool,
    no_sections: bool,
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    plan_mode: bool,
    full_mode: bool,
) -> None:
    """Render workflow for run command (single cycle).

    Equivalent to: sdqctl run workflow.conv --render-only

    \b
    Examples:
      sdqctl render run workflow.conv
      sdqctl render run workflow.conv --plan
      sdqctl render run workflow.conv --json -o rendered.json
    """
    _render_common(
        workflow=workflow,
        session_mode="accumulate",
        cycles=1,
        cycle=cycle,
        prompt=prompt,
        output=output,
        json_output=json_output,
        no_context=no_context,
        no_sections=no_sections,
        prologue=prologue,
        epilogue=epilogue,
        plan_mode=plan_mode,
    )


@render.command("cycle")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--max-cycles", "-n", type=int, default=None, help="Maximum cycles to render")
@common_render_options
def render_cycle(
    workflow: str,
    max_cycles: Optional[int],
    session_mode: str,
    cycles: Optional[int],
    cycle: Optional[int],
    prompt: Optional[int],
    output: Optional[str],
    json_output: bool,
    no_context: bool,
    no_sections: bool,
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    plan_mode: bool,
    full_mode: bool,
) -> None:
    """Render workflow for cycle command (multi-cycle).

    Equivalent to: sdqctl cycle workflow.conv --render-only

    \b
    Examples:
      sdqctl render cycle workflow.conv --max-cycles 5
      sdqctl render cycle workflow.conv -n 3 --plan
      sdqctl render cycle workflow.conv -s fresh -o cycles/
    """
    # max_cycles takes precedence over cycles
    num_cycles = max_cycles or cycles

    _render_common(
        workflow=workflow,
        session_mode=session_mode,
        cycles=num_cycles,
        cycle=cycle,
        prompt=prompt,
        output=output,
        json_output=json_output,
        no_context=no_context,
        no_sections=no_sections,
        prologue=prologue,
        epilogue=epilogue,
        plan_mode=plan_mode,
    )


@render.command("apply")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--components", "-c", multiple=True, help="Component patterns to render")
@common_render_options
def render_apply(
    workflow: str,
    components: tuple[str, ...],
    session_mode: str,
    cycles: Optional[int],
    cycle: Optional[int],
    prompt: Optional[int],
    output: Optional[str],
    json_output: bool,
    no_context: bool,
    no_sections: bool,
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    plan_mode: bool,
    full_mode: bool,
) -> None:
    """Render workflow for apply command (per-component).

    Equivalent to: sdqctl apply workflow.conv --render-only

    Shows how the workflow would be rendered for each component.

    \b
    Examples:
      sdqctl render apply workflow.conv --components "lib/*.js"
      sdqctl render apply workflow.conv -c "src/**/*.py" --plan
    """
    # For apply, we'd need to discover components and render each
    # For now, just render the base workflow with a note
    console.print(
        "[yellow]Note: Rendering base workflow. "
        "Use --components to specify targets.[/yellow]"
    )

    if components:
        console.print(f"[dim]Component patterns: {list(components)}[/dim]")

    _render_common(
        workflow=workflow,
        session_mode=session_mode,
        cycles=cycles,
        cycle=cycle,
        prompt=prompt,
        output=output,
        json_output=json_output,
        no_context=no_context,
        no_sections=no_sections,
        prologue=prologue,
        epilogue=epilogue,
        plan_mode=plan_mode,
    )
