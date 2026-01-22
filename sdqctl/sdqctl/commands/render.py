"""
sdqctl render - Render workflow prompts without executing.

Produces fully-resolved prompts with all context, templates, prologues,
and epilogues expanded. Useful for debugging and templating.

Usage:
    sdqctl render workflow.conv
    sdqctl render workflow.conv --json
    sdqctl render workflow.conv -o rendered.md
    sdqctl render workflow.conv -s fresh -n 3 -o rendered/
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


@click.command("render")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--session-mode", "-s", type=click.Choice(["accumulate", "compact", "fresh"]),
              default="accumulate", help="Session mode (affects output structure for fresh)")
@click.option("--cycles", "-n", type=int, default=None, help="Number of cycles to render")
@click.option("--cycle", type=int, default=None, help="Render only this cycle number")
@click.option("--prompt", type=int, default=None, help="Render only this prompt number")
@click.option("--output", "-o", default=None, help="Output file or directory")
@click.option("--json", "json_output", is_flag=True, help="JSON output format")
@click.option("--no-context", is_flag=True, help="Exclude context file contents")
@click.option("--no-sections", is_flag=True, help="Omit section markers")
@click.option("--prologue", multiple=True, help="Additional prologue (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Additional epilogue (inline text or @file)")
def render(
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
) -> None:
    """Render workflow prompts without executing.
    
    Produces fully-resolved prompts with all context, templates,
    prologues, and epilogues expanded. No AI calls are made.
    
    \b
    Examples:
      sdqctl render workflow.conv                  # stdout
      sdqctl render workflow.conv --json           # JSON format
      sdqctl render workflow.conv -o rendered.md   # to file
      sdqctl render workflow.conv -s fresh -n 3    # 3 fresh cycles
      sdqctl render workflow.conv --cycle 2        # only cycle 2
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
        errors, warnings = conv.validate_context_files(allow_missing=True)
        all_issues = errors + warnings
        if all_issues:
            console.print(f"[yellow]Warning: Some context files not found:[/yellow]")
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
                console.print(f"[red]Error: Cycle {cycle} not in range 1-{len(rendered.cycles)}[/red]")
                sys.exit(1)
            rendered.cycles = [rendered.cycles[cycle - 1]]
        
        # Filter to specific prompt if requested
        if prompt is not None:
            for c in rendered.cycles:
                if prompt < 1 or prompt > len(c.prompts):
                    console.print(f"[red]Error: Prompt {prompt} not in range 1-{len(c.prompts)}[/red]")
                    sys.exit(1)
                c.prompts = [c.prompts[prompt - 1]]
        
        # Format output
        if json_output:
            output_content = json.dumps(format_rendered_json(rendered), indent=2)
        else:
            output_content = format_rendered_markdown(
                rendered,
                show_sections=not no_sections,
                include_context=not no_context,
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
                    single_cycle = rendered
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
                        cycle_content = json.dumps(format_rendered_json(single_cycle_copy), indent=2)
                        cycle_file = output_path / f"cycle-{c.number}.json"
                    else:
                        cycle_content = format_rendered_markdown(
                            single_cycle_copy,
                            show_sections=not no_sections,
                            include_context=not no_context,
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
