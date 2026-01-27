"""
sdqctl flow - Execute batch/parallel workflows.

Usage:
    sdqctl flow workflows/*.conv --parallel 4
    sdqctl flow flow-definition.yaml
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile
from ..core.logging import get_logger
from ..core.session import Session
from .utils import run_async

logger = get_logger(__name__)
console = Console()


@click.command("flow")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--parallel", "-p", type=int, default=1, help="Parallel execution limit")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--prologue", multiple=True, help="Prepend to each prompt (inline text or @file)")
@click.option("--epilogue", multiple=True, help="Append to each prompt (inline text or @file)")
@click.option("--header", multiple=True, help="Prepend to output (inline text or @file)")
@click.option("--footer", multiple=True, help="Append to output (inline text or @file)")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="Output directory")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
@click.option("--continue-on-error", is_flag=True, help="Continue if a workflow fails")
def flow(
    patterns: tuple[str, ...],
    parallel: int,
    adapter: Optional[str],
    model: Optional[str],
    prologue: tuple[str, ...],
    epilogue: tuple[str, ...],
    header: tuple[str, ...],
    footer: tuple[str, ...],
    output_dir: Optional[str],
    json_output: bool,
    dry_run: bool,
    continue_on_error: bool,
) -> None:
    """Execute batch/parallel workflows."""
    run_async(_flow_async(
        patterns, parallel, adapter, model,
        prologue, epilogue, header, footer,
        output_dir, json_output, dry_run, continue_on_error
    ))


async def _flow_async(
    patterns: tuple[str, ...],
    parallel_limit: int,
    adapter_name: Optional[str],
    model: Optional[str],
    cli_prologues: tuple[str, ...],
    cli_epilogues: tuple[str, ...],
    cli_headers: tuple[str, ...],
    cli_footers: tuple[str, ...],
    output_dir: Optional[str],
    json_output: bool,
    dry_run: bool,
    continue_on_error: bool,
) -> None:
    """Async implementation of flow command."""
    from ..core.conversation import (
        build_output_with_injection,
        build_prompt_with_injection,
        get_standard_variables,
    )

    # Collect workflow files
    workflow_files: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.is_file():
            workflow_files.append(path)
        elif "*" in pattern:
            # Glob pattern
            base_path = Path(pattern.split("*")[0].rstrip("/") or ".")
            glob_pattern = pattern[len(str(base_path)):].lstrip("/")
            workflow_files.extend(base_path.glob(glob_pattern))
        else:
            console.print(f"[yellow]Warning: {pattern} not found[/yellow]")

    # Filter for .conv files
    workflow_files = [f for f in workflow_files if f.suffix in (".conv", ".copilot")]

    if not workflow_files:
        console.print("[red]No workflow files found[/red]")
        return

    # Sort for consistent ordering
    workflow_files.sort()

    console.print(f"\n[bold]Found {len(workflow_files)} workflows[/bold]")
    for wf in workflow_files:
        logger.debug(f"  - {wf}")

    if dry_run:
        console.print(
            f"\n[yellow]Would execute {len(workflow_files)} workflows "
            f"with parallelism {parallel_limit}[/yellow]"
        )
        return

    # Create output directory
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get adapter
    try:
        ai_adapter = get_adapter(adapter_name or "mock")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        ai_adapter = get_adapter("mock")

    await ai_adapter.start()

    # Semaphore for parallel limit
    semaphore = asyncio.Semaphore(parallel_limit)
    results: dict[str, dict] = {}

    async def run_workflow(wf_path: Path, progress: Progress, task_id: TaskID) -> dict:
        """Run a single workflow."""
        async with semaphore:
            progress.update(task_id, description=f"Running {wf_path.name}")

            try:
                conv = ConversationFile.from_file(wf_path)

                # Apply overrides
                if adapter_name:
                    conv.adapter = adapter_name
                if model:
                    conv.model = model

                # Add CLI-provided prologues/epilogues (prepend to file-defined ones)
                if cli_prologues:
                    conv.prologues = list(cli_prologues) + conv.prologues
                if cli_epilogues:
                    conv.epilogues = list(cli_epilogues) + conv.epilogues
                if cli_headers:
                    conv.headers = list(cli_headers) + conv.headers
                if cli_footers:
                    conv.footers = list(cli_footers) + conv.footers

                # Get template variables for this workflow
                template_vars = get_standard_variables(conv.source_path)

                session = Session(conv)

                # Create adapter session
                adapter_session = await ai_adapter.create_session(
                    AdapterConfig(model=conv.model, streaming=False)
                )

                responses = []
                context_content = session.context.get_context_content()

                for i, prompt in enumerate(conv.prompts):
                    # Build prompt with prologue/epilogue injection
                    is_first = (i == 0)
                    is_last = (i == len(conv.prompts) - 1)
                    full_prompt = build_prompt_with_injection(
                        prompt, conv.prologues, conv.epilogues,
                        conv.source_path.parent if conv.source_path else None,
                        template_vars,
                        is_first_prompt=is_first,
                        is_last_prompt=is_last
                    )
                    if i == 0 and context_content:
                        full_prompt = f"{context_content}\n\n{full_prompt}"

                    response = await ai_adapter.send(adapter_session, full_prompt)
                    responses.append(response)

                await ai_adapter.destroy_session(adapter_session)

                # Write output with header/footer injection
                if output_dir:
                    output_file = Path(output_dir) / f"{wf_path.stem}-result.md"
                    output_content = "\n\n---\n\n".join(responses)
                    output_content = build_output_with_injection(
                        output_content, conv.headers, conv.footers,
                        conv.source_path.parent if conv.source_path else None,
                        template_vars
                    )
                    output_file.write_text(output_content)

                progress.update(task_id, completed=1)

                return {
                    "workflow": str(wf_path),
                    "status": "completed",
                    "prompts": len(conv.prompts),
                    "responses": len(responses),
                }

            except Exception as e:
                progress.update(task_id, completed=1)
                error_result = {
                    "workflow": str(wf_path),
                    "status": "failed",
                    "error": str(e),
                }
                if not continue_on_error:
                    raise
                return error_result

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:

            main_task = progress.add_task("Overall", total=len(workflow_files))
            tasks = []

            for wf_path in workflow_files:
                task_id = progress.add_task(f"Pending {wf_path.name}", total=1)
                tasks.append(run_workflow(wf_path, progress, task_id))
                progress.update(main_task, advance=0)

            # Run all workflows
            completed = await asyncio.gather(*tasks, return_exceptions=continue_on_error)

            for i, result in enumerate(completed):
                wf_path = workflow_files[i]
                if isinstance(result, Exception):
                    results[str(wf_path)] = {
                        "workflow": str(wf_path),
                        "status": "failed",
                        "error": str(result),
                    }
                else:
                    results[str(wf_path)] = result
                progress.update(main_task, advance=1)

    finally:
        await ai_adapter.stop()

    # Summary
    completed_count = sum(1 for r in results.values() if r["status"] == "completed")
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")

    if json_output:
        import json
        console.print_json(json.dumps({
            "total": len(workflow_files),
            "completed": completed_count,
            "failed": failed_count,
            "results": list(results.values()),
        }))
    else:
        console.print("\n[bold]Flow Results[/bold]")
        console.print(f"  Completed: [green]{completed_count}[/green]")
        console.print(f"  Failed: [red]{failed_count}[/red]")

        if failed_count > 0:
            console.print("\n[bold red]Failed workflows:[/bold red]")
            for path, result in results.items():
                if result["status"] == "failed":
                    console.print(f"  - {path}: {result.get('error', 'Unknown error')}")
