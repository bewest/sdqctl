"""
sdqctl apply - Apply a workflow to multiple components.

Usage:
    sdqctl apply workflow.conv --components "lib/plugins/*.js"
    sdqctl apply workflow.conv --components "lib/plugins/*.js" --progress progress.md
    sdqctl apply workflow.conv --from-discovery components.json --parallel 4
"""

import asyncio
import glob as glob_module
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile, apply_iteration_context
from ..core.logging import get_logger
from ..core.progress import progress as progress_print
from ..core.session import Session

logger = get_logger(__name__)
console = Console()


@click.command("apply")
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--components", "-c", help="Glob pattern for components to iterate over")
@click.option("--from-discovery", "discovery_file", type=click.Path(exists=True), 
              help="JSON file from sdqctl discover")
@click.option("--progress", "progress_file", help="Progress tracker file (markdown)")
@click.option("--parallel", "-p", default=1, type=int, help="Number of parallel executions")
@click.option("--adapter", "-a", default=None, help="AI adapter override")
@click.option("--model", "-m", default=None, help="Model override")
@click.option("--output-dir", "-o", default=None, help="Output directory for results")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--dry-run", is_flag=True, help="Show what would happen")
def apply(
    workflow: str,
    components: Optional[str],
    discovery_file: Optional[str],
    progress_file: Optional[str],
    parallel: int,
    adapter: Optional[str],
    model: Optional[str],
    output_dir: Optional[str],
    verbose: bool,
    dry_run: bool,
) -> None:
    """Apply a workflow to multiple components.
    
    Iterates over a list of components (from glob pattern or discovery file)
    and runs the workflow for each, substituting template variables like
    {{COMPONENT_PATH}}, {{COMPONENT_NAME}}, etc.
    
    Examples:
    
    \b
    # Apply to all plugins
    sdqctl apply workflow.conv --components "lib/plugins/*.js"
    
    \b
    # Apply with progress tracking
    sdqctl apply workflow.conv -c "lib/plugins/*.js" --progress progress.md
    
    \b
    # Apply from discovery output
    sdqctl apply workflow.conv --from-discovery components.json
    
    \b
    # Parallel execution
    sdqctl apply workflow.conv -c "lib/**/*.js" --parallel 4
    """
    asyncio.run(_apply_async(
        workflow, components, discovery_file, progress_file,
        parallel, adapter, model, output_dir, verbose, dry_run
    ))


async def _apply_async(
    workflow_path: str,
    components_pattern: Optional[str],
    discovery_file: Optional[str],
    progress_file: Optional[str],
    parallel: int,
    adapter_name: Optional[str],
    model: Optional[str],
    output_dir: Optional[str],
    verbose: bool,
    dry_run: bool,
) -> None:
    """Async implementation of apply command."""
    import time as time_module
    apply_start = time_module.time()
    
    # Load workflow
    conv = ConversationFile.from_file(Path(workflow_path))
    logger.info(f"Loaded workflow from {workflow_path}")
    progress_print(f"Applying {Path(workflow_path).name}...")
    
    # Apply overrides
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model
    if output_dir:
        conv.output_dir = output_dir
    
    # Get component list
    component_list = []
    
    if discovery_file:
        # Load from discovery JSON
        discovery_data = json.loads(Path(discovery_file).read_text())
        if isinstance(discovery_data, list):
            component_list = discovery_data
        elif "components" in discovery_data:
            component_list = discovery_data["components"]
        else:
            console.print("[red]Error: Discovery file must contain 'components' array[/red]")
            return
        
        # Extract paths from component objects
        component_paths = []
        for comp in component_list:
            if isinstance(comp, str):
                component_paths.append({"path": comp, "type": "unknown"})
            elif isinstance(comp, dict) and "path" in comp:
                component_paths.append(comp)
            else:
                console.print(f"[yellow]Warning: Skipping invalid component: {comp}[/yellow]")
        component_list = component_paths
        
    elif components_pattern:
        # Expand glob pattern
        paths = glob_module.glob(components_pattern, recursive=True)
        component_list = [{"path": p, "type": "unknown"} for p in sorted(paths)]
    else:
        console.print("[red]Error: Must specify --components or --from-discovery[/red]")
        return
    
    if not component_list:
        console.print("[yellow]No components found matching pattern[/yellow]")
        return
    
    progress_print(f"  Found {len(component_list)} components")
    
    # Show what we'll process
    console.print(Panel.fit(
        f"Workflow: {workflow_path}\n"
        f"Components: {len(component_list)}\n"
        f"Parallel: {parallel}\n"
        f"Adapter: {conv.adapter}\n"
        f"Model: {conv.model}",
        title="Apply Configuration"
    ))
    
    if dry_run:
        table = Table(title="Components")
        table.add_column("Index", style="dim")
        table.add_column("Path")
        table.add_column("Type")
        for i, comp in enumerate(component_list, 1):
            table.add_row(str(i), comp["path"], comp.get("type", "unknown"))
        console.print(table)
    else:
        for comp in component_list:
            logger.debug(f"  - {comp['path']} ({comp.get('type', 'unknown')})")
    
    if dry_run:
        console.print("\n[yellow]Dry run - no execution[/yellow]")
        
        # Show what template substitution would produce for first component
        if component_list:
            first = component_list[0]
            test_conv = apply_iteration_context(
                conv, first["path"], 1, len(component_list), first.get("type", "unknown")
            )
            console.print("\n[bold]Example substitution (component 1):[/bold]")
            for i, prompt in enumerate(test_conv.prompts[:2], 1):
                preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
                console.print(f"  Prompt {i}: {preview}")
            if test_conv.output_file:
                console.print(f"  Output: {test_conv.output_file}")
        return
    
    # Initialize progress tracker
    progress_data = ProgressTracker(progress_file, component_list)
    progress_data.write_initial()
    
    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Using mock adapter instead[/yellow]")
        ai_adapter = get_adapter("mock")
    
    await ai_adapter.start()
    
    try:
            # Process components (sequential or parallel)
            if parallel > 1:
                # Parallel execution with semaphore
                semaphore = asyncio.Semaphore(parallel)
                tasks = []
                for i, comp in enumerate(component_list, 1):
                    task = _process_component_with_semaphore(
                        semaphore, conv, comp, i, len(component_list),
                        ai_adapter, progress_data
                    )
                    tasks.append(task)
                await asyncio.gather(*tasks)
            else:
                # Sequential execution with progress bar
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Processing components...", total=len(component_list))
                    
                    for i, comp in enumerate(component_list, 1):
                        progress.update(task, description=f"[{i}/{len(component_list)}] {comp['path']}")
                        await _process_single_component(
                            conv, comp, i, len(component_list),
                            ai_adapter, progress_data
                        )
                        progress.advance(task)
    
    finally:
        await ai_adapter.stop()
        progress_data.write_final()
    
    # Summary
    apply_elapsed = time_module.time() - apply_start
    progress_print(f"Done in {apply_elapsed:.1f}s")
    console.print(f"\n[green]✓ Completed {len(component_list)} components[/green]")
    if progress_file:
        console.print(f"[dim]Progress saved to: {progress_file}[/dim]")


async def _process_component_with_semaphore(
    semaphore: asyncio.Semaphore,
    conv: ConversationFile,
    component: dict,
    index: int,
    total: int,
    ai_adapter,
    progress_data: "ProgressTracker",
) -> None:
    """Process a single component with semaphore for parallel limiting."""
    async with semaphore:
        await _process_single_component(
            conv, component, index, total, ai_adapter, progress_data
        )


async def _process_single_component(
    conv: ConversationFile,
    component: dict,
    index: int,
    total: int,
    ai_adapter,
    progress_data: "ProgressTracker",
) -> None:
    """Process a single component through the workflow."""
    component_path = component["path"]
    component_type = component.get("type", "unknown")
    
    start_time = time.time()
    progress_data.update_status(component_path, "running")
    progress_print(f"  [{index}/{total}] Processing {component_path}...")
    
    try:
        # Apply template variables
        instance_conv = apply_iteration_context(
            conv, component_path, index, total, component_type
        )
        
        # Create session
        session = Session(instance_conv)
        
        # Create adapter session
        adapter_session = await ai_adapter.create_session(
            AdapterConfig(model=instance_conv.model, streaming=True)
        )
        
        responses = []
        context_content = session.context.get_context_content()
        
        for i, prompt in enumerate(instance_conv.prompts):
            logger.debug(f"  [{index}/{total}] Prompt {i+1}/{len(instance_conv.prompts)}")
            
            full_prompt = prompt
            if i == 0 and context_content:
                full_prompt = f"{context_content}\n\n{prompt}"
            
            response = await ai_adapter.send(adapter_session, full_prompt)
            responses.append(response)
            session.add_message("user", prompt)
            session.add_message("assistant", response)
        
        await ai_adapter.destroy_session(adapter_session)
        
        # Write output
        output_path = None
        if instance_conv.output_file:
            output_path = Path(instance_conv.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_content = "\n\n---\n\n".join(responses)
            output_path.write_text(output_content)
            progress_print(f"  [{index}/{total}] Writing to {output_path}")
        
        duration = time.time() - start_time
        progress_print(f"  [{index}/{total}] Done ({duration:.1f}s)")
        progress_data.update_status(
            component_path, "done", 
            output=str(output_path) if output_path else None,
            duration=duration
        )
        
    except Exception as e:
        duration = time.time() - start_time
        progress_print(f"  [{index}/{total}] Failed: {e}")
        progress_data.update_status(component_path, "failed", error=str(e), duration=duration)
        logger.warning(f"  Error processing {component_path}: {e}")


class ProgressTracker:
    """Tracks and writes progress for component iteration."""
    
    def __init__(self, progress_file: Optional[str], components: list[dict]):
        self.progress_file = Path(progress_file) if progress_file else None
        self.components = components
        self.status: dict[str, dict] = {
            comp["path"]: {"status": "pending", "output": None, "duration": None, "error": None}
            for comp in components
        }
        self.start_time = datetime.now()
    
    def update_status(
        self, 
        component_path: str, 
        status: str, 
        output: Optional[str] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update the status of a component."""
        self.status[component_path] = {
            "status": status,
            "output": output,
            "duration": duration,
            "error": error,
        }
        self._write_progress()
    
    def write_initial(self) -> None:
        """Write initial progress file."""
        self._write_progress()
    
    def write_final(self) -> None:
        """Write final progress file."""
        self._write_progress()
    
    def _write_progress(self) -> None:
        """Write current progress to file."""
        if not self.progress_file:
            return
        
        lines = [
            "## Iteration Progress",
            "",
            f"Started: {self.start_time.isoformat()}",
            "",
            "| Component | Status | Output | Duration |",
            "|-----------|--------|--------|----------|",
        ]
        
        done_count = 0
        running_count = 0
        pending_count = 0
        failed_count = 0
        
        for comp in self.components:
            path = comp["path"]
            info = self.status.get(path, {"status": "pending"})
            status = info["status"]
            
            # Status emoji
            if status == "done":
                status_str = "✅ Done"
                done_count += 1
            elif status == "running":
                status_str = "🔄 Running"
                running_count += 1
            elif status == "failed":
                status_str = "❌ Failed"
                failed_count += 1
            else:
                status_str = "⏳ Pending"
                pending_count += 1
            
            output = info.get("output") or "-"
            duration = f"{info['duration']:.1f}s" if info.get("duration") else "-"
            
            # Truncate long paths
            display_path = Path(path).name
            lines.append(f"| {display_path} | {status_str} | {output} | {duration} |")
        
        lines.extend([
            "",
            f"**Summary:** {done_count}/{len(self.components)} complete"
            + (f", {running_count} running" if running_count else "")
            + (f", {pending_count} pending" if pending_count else "")
            + (f", {failed_count} failed" if failed_count else ""),
        ])
        
        self.progress_file.write_text("\n".join(lines))
