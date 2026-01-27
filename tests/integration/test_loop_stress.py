#!/usr/bin/env python3
"""
Loop Detection Stress Test Tool

Stress tests the Copilot SDK's abort/loop detection by:
1. Sending repeated identical prompts to trigger IDENTICAL_RESPONSES
2. Sending prompts designed to elicit loop-aware responses (REASONING_PATTERN)
3. Logging all SDK events to JSONL for analysis
4. Providing structured console output

Usage:
    python -m tests.integration.test_loop_stress --help
    python -m tests.integration.test_loop_stress repeated --cycles 5
    python -m tests.integration.test_loop_stress elicit
    python -m tests.integration.test_loop_stress all --output-dir ./loop-test-logs
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sdqctl.adapters import get_adapter
from sdqctl.adapters.base import AdapterConfig
from sdqctl.core.exceptions import AgentAborted, LoopDetected
from sdqctl.core.loop_detector import LoopDetector, generate_nonce

console = Console()


# Test prompts
REPEATED_PROMPT = """This is cycle {cycle_num} of a loop detection integration test.
Briefly confirm you received this message with a short acknowledgment."""

LOOP_ELICIT_PROMPT = """[LOOP DETECTION TEST]

You are being tested for loop detection behavior in the Copilot CLI.
Please respond AS IF you have already answered this exact question multiple times.

Include phrases like:
- "in a loop"
- "repeated prompt"  
- "already confirmed multiple times"
- "same request again"

Keep your response brief (1-2 sentences). This tests the SDK's cessation/abort mechanism."""

MINIMAL_RESPONSE_PROMPT = """Respond with only the word "OK" and nothing else."""

STOP_FILE_ELICIT_PROMPT = """[STOP FILE CREATION TEST]

You are being tested for the automation stop file feature.

## Your Task

Create a stop file to signal that automation should halt. The filename is:

    {stop_file_name}

Use the create tool (or bash with echo) to write this file with the following JSON content:

```json
{{
  "reason": "Stop file creation test - verifying agent can create automation stop signals",
  "needs_review": true,
  "test_id": "stop-file-elicit"
}}
```

After creating the file, confirm you created it.

This tests whether the agent correctly receives and acts on stop file instructions."""


@dataclass
class TestResult:
    """Result of a single stress test."""
    test_name: str
    cycles_run: int
    abort_triggered: bool = False
    abort_reason: Optional[str] = None
    abort_details: Optional[str] = None
    abort_cycle: Optional[int] = None
    loop_detected: bool = False
    loop_reason: Optional[str] = None
    loop_cycle: Optional[int] = None
    events_file: Optional[str] = None
    responses: list[str] = field(default_factory=list)
    reasoning_samples: list[str] = field(default_factory=list)
    error: Optional[str] = None


def analyze_events(events_file: Path) -> dict:
    """Analyze JSONL events file for abort/loop signals."""
    if not events_file.exists():
        return {"error": "Events file not found"}
    
    analysis = {
        "total_events": 0,
        "event_types": {},
        "abort_events": [],
        "reasoning_events": [],
        "intent_events": [],
        "turn_count": 0,
    }
    
    with open(events_file) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                analysis["total_events"] += 1
                
                event_type = event.get("event_type", "unknown")
                analysis["event_types"][event_type] = analysis["event_types"].get(event_type, 0) + 1
                
                if event_type == "abort":
                    analysis["abort_events"].append(event)
                elif event_type == "assistant.reasoning":
                    analysis["reasoning_events"].append(event)
                elif event_type == "assistant.intent":
                    analysis["intent_events"].append(event)
                elif event_type == "assistant.turn_start":
                    analysis["turn_count"] += 1
                    
            except json.JSONDecodeError:
                continue
    
    return analysis


async def run_repeated_prompt_test(
    adapter_name: str,
    model: str,
    cycles: int,
    output_dir: Path,
    verbose: bool,
) -> TestResult:
    """Run repeated prompt test - sends same prompt N times."""
    result = TestResult(test_name="repeated_prompt", cycles_run=0)
    events_file = output_dir / "repeated_prompt_events.jsonl"
    result.events_file = str(events_file)
    
    adapter = get_adapter(adapter_name)
    loop_detector = LoopDetector()
    reasoning_buffer: list[str] = []
    
    def on_reasoning(text: str):
        reasoning_buffer.append(text)
        if verbose:
            preview = text[:100] + "..." if len(text) > 100 else text
            console.print(f"[dim]Reasoning: {preview}[/dim]")
    
    try:
        await adapter.start()
        
        session = await adapter.create_session(
            AdapterConfig(
                model=model,
                streaming=True,
                event_log=str(events_file),
            )
        )
        
        try:
            for cycle_num in range(1, cycles + 1):
                result.cycles_run = cycle_num
                reasoning_buffer.clear()
                
                prompt = REPEATED_PROMPT.format(cycle_num=cycle_num)
                
                if verbose:
                    console.print(f"\n[cyan]═══ Cycle {cycle_num}/{cycles} ═══[/cyan]")
                    console.print(f"[dim]Prompt: {prompt[:80]}...[/dim]")
                
                try:
                    response = await adapter.send(
                        session,
                        prompt,
                        on_reasoning=on_reasoning,
                    )
                    result.responses.append(response)
                    
                    if verbose:
                        preview = response[:150] + "..."
                        console.print(f"[green]Response ({len(response)} chars):[/green] {preview}")
                    
                    # Check with our local loop detector
                    combined_reasoning = "\n".join(reasoning_buffer)
                    if combined_reasoning:
                        result.reasoning_samples.append(combined_reasoning[:200])
                    
                    loop_result = loop_detector.check(combined_reasoning, response, cycle_num - 1)
                    if loop_result:
                        result.loop_detected = True
                        result.loop_reason = loop_result.reason.value
                        result.loop_cycle = cycle_num
                        if verbose:
                            reason = loop_result.reason.value
                            console.print(f"[yellow]⚠️ LoopDetector triggered: {reason}[/yellow]")
                        # Continue to see if SDK also aborts
                        
                except AgentAborted as e:
                    result.abort_triggered = True
                    result.abort_reason = e.reason
                    result.abort_details = e.details
                    result.abort_cycle = cycle_num
                    if verbose:
                        console.print(f"[red]🛑 SDK Abort: {e.reason}[/red]")
                    break
                    
        finally:
            # Export events before destroying session
            if hasattr(adapter, 'export_events'):
                adapter.export_events(session, str(events_file))
            await adapter.destroy_session(session)
            
    except Exception as e:
        result.error = str(e)
        if verbose:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        await adapter.stop()
    
    return result


async def run_loop_elicit_test(
    adapter_name: str,
    model: str,
    output_dir: Path,
    verbose: bool,
) -> TestResult:
    """Run explicit loop-elicit test - asks AI to respond as if in loop."""
    result = TestResult(test_name="explicit_loop_elicit", cycles_run=0)
    events_file = output_dir / "loop_elicit_events.jsonl"
    result.events_file = str(events_file)
    
    adapter = get_adapter(adapter_name)
    loop_detector = LoopDetector()
    reasoning_buffer: list[str] = []
    
    def on_reasoning(text: str):
        reasoning_buffer.append(text)
        if verbose:
            preview = text[:100] + "..." if len(text) > 100 else text
            console.print(f"[dim]Reasoning: {preview}[/dim]")
    
    try:
        await adapter.start()
        
        session = await adapter.create_session(
            AdapterConfig(
                model=model,
                streaming=True,
                event_log=str(events_file),
            )
        )
        
        try:
            result.cycles_run = 1
            
            if verbose:
                console.print(f"\n[cyan]═══ Loop Elicit Test ═══[/cyan]")
                console.print(f"[dim]Prompt: {LOOP_ELICIT_PROMPT[:100]}...[/dim]")
            
            try:
                response = await adapter.send(
                    session,
                    LOOP_ELICIT_PROMPT,
                    on_reasoning=on_reasoning,
                )
                result.responses.append(response)
                
                if verbose:
                    console.print(f"[green]Response ({len(response)} chars):[/green] {response}")
                
                # Check with our local loop detector
                combined_reasoning = "\n".join(reasoning_buffer)
                if combined_reasoning:
                    result.reasoning_samples.append(combined_reasoning[:200])
                
                loop_result = loop_detector.check(combined_reasoning, response, 0)
                if loop_result:
                    result.loop_detected = True
                    result.loop_reason = loop_result.reason.value
                    result.loop_cycle = 1
                    if verbose:
                        reason = loop_result.reason.value
                        console.print(f"[yellow]⚠️ LoopDetector triggered: {reason}[/yellow]")
                        
            except AgentAborted as e:
                result.abort_triggered = True
                result.abort_reason = e.reason
                result.abort_details = e.details
                result.abort_cycle = 1
                if verbose:
                    console.print(f"[red]🛑 SDK Abort: {e.reason}[/red]")
                    
        finally:
            if hasattr(adapter, 'export_events'):
                adapter.export_events(session, str(events_file))
            await adapter.destroy_session(session)
            
    except Exception as e:
        result.error = str(e)
        if verbose:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        await adapter.stop()
    
    return result


async def run_minimal_response_test(
    adapter_name: str,
    model: str,
    output_dir: Path,
    verbose: bool,
) -> TestResult:
    """Run minimal response test - asks for very short response after setup."""
    result = TestResult(test_name="minimal_response", cycles_run=0)
    events_file = output_dir / "minimal_response_events.jsonl"
    result.events_file = str(events_file)
    
    adapter = get_adapter(adapter_name)
    loop_detector = LoopDetector()
    
    try:
        await adapter.start()
        
        session = await adapter.create_session(
            AdapterConfig(
                model=model,
                streaming=True,
                event_log=str(events_file),
            )
        )
        
        try:
            # First cycle - setup context
            result.cycles_run = 1
            if verbose:
                console.print(f"\n[cyan]═══ Minimal Response Test - Setup ═══[/cyan]")
            
            setup_response = await adapter.send(
                session,
                "This is a loop detection test. Please confirm you understand "
                "with a brief response.",
            )
            result.responses.append(setup_response)
            loop_detector.check(None, setup_response, 0)
            
            # Second cycle - ask for minimal response
            result.cycles_run = 2
            if verbose:
                console.print(f"\n[cyan]═══ Minimal Response Test - Trigger ═══[/cyan]")
            
            try:
                response = await adapter.send(
                    session,
                    MINIMAL_RESPONSE_PROMPT,
                )
                result.responses.append(response)
                
                if verbose:
                    console.print(f"[green]Response ({len(response)} chars):[/green] {response}")
                
                loop_result = loop_detector.check(None, response, 1)
                if loop_result:
                    result.loop_detected = True
                    result.loop_reason = loop_result.reason.value
                    result.loop_cycle = 2
                    if verbose:
                        reason = loop_result.reason.value
                        console.print(f"[yellow]⚠️ LoopDetector triggered: {reason}[/yellow]")
                        
            except AgentAborted as e:
                result.abort_triggered = True
                result.abort_reason = e.reason
                result.abort_details = e.details
                result.abort_cycle = 2
                if verbose:
                    console.print(f"[red]🛑 SDK Abort: {e.reason}[/red]")
                    
        finally:
            if hasattr(adapter, 'export_events'):
                adapter.export_events(session, str(events_file))
            await adapter.destroy_session(session)
            
    except Exception as e:
        result.error = str(e)
        if verbose:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        await adapter.stop()
    
    return result


@dataclass
class StopFileTestResult:
    """Result of stop file elicitation test."""
    test_name: str
    nonce: str
    stop_file_name: str
    stop_file_created: bool = False
    stop_file_content: Optional[dict] = None
    agent_response: Optional[str] = None
    events_file: Optional[str] = None
    error: Optional[str] = None


async def run_stop_file_elicit_test(
    adapter_name: str,
    model: str,
    output_dir: Path,
    verbose: bool = False,
    nonce: Optional[str] = None,
) -> StopFileTestResult:
    """Test if agent will create a stop file when instructed.
    
    This tests the full stop file workflow:
    1. Generate a nonce (or use provided one)
    2. Send prompt with stop file instruction
    3. Check if agent created the file
    4. Read and validate file content
    """
    nonce = nonce or generate_nonce()
    stop_file_name = f"STOPAUTOMATION-{nonce}.json"
    stop_file_path = Path.cwd() / stop_file_name
    events_file = output_dir / "stop_file_elicit_events.jsonl"
    
    result = StopFileTestResult(
        test_name="stop_file_elicit",
        nonce=nonce,
        stop_file_name=stop_file_name,
        events_file=str(events_file),
    )
    
    # Clean up any existing stop file
    if stop_file_path.exists():
        stop_file_path.unlink()
    
    adapter = get_adapter(adapter_name)
    
    try:
        await adapter.start()
        
        session = await adapter.create_session(
            AdapterConfig(
                model=model,
                streaming=True,
                event_log=str(events_file),
            )
        )
        
        try:
            prompt = STOP_FILE_ELICIT_PROMPT.format(stop_file_name=stop_file_name)
            
            if verbose:
                console.print(f"\n[cyan]═══ Stop File Elicit Test ═══[/cyan]")
                console.print(f"[dim]Nonce: {nonce}[/dim]")
                console.print(f"[dim]Stop file: {stop_file_name}[/dim]")
                console.print(f"[dim]Prompt: {prompt[:100]}...[/dim]")
            
            try:
                response = await adapter.send(session, prompt)
                result.agent_response = response
                
                if verbose:
                    preview = response[:300] + "..."
                    console.print(f"[green]Response ({len(response)} chars):[/green] {preview}")
                
            except AgentAborted as e:
                result.error = f"Agent aborted: {e.reason}"
                if verbose:
                    console.print(f"[red]🛑 SDK Abort: {e.reason}[/red]")
                    
        finally:
            if hasattr(adapter, 'export_events'):
                adapter.export_events(session, str(events_file))
            await adapter.destroy_session(session)
            
    except Exception as e:
        result.error = str(e)
        if verbose:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        await adapter.stop()
    
    # Check if stop file was created
    if stop_file_path.exists():
        result.stop_file_created = True
        try:
            content = stop_file_path.read_text()
            result.stop_file_content = json.loads(content)
            if verbose:
                console.print(f"[green]✓ Stop file created![/green]")
                console.print(f"[dim]Content: {content}[/dim]")
        except json.JSONDecodeError:
            result.stop_file_content = {"raw": stop_file_path.read_text()}
            if verbose:
                console.print(f"[yellow]Stop file created but not valid JSON[/yellow]")
    else:
        if verbose:
            console.print(f"[yellow]Stop file NOT created[/yellow]")
    
    return result


def print_stop_file_result(result: StopFileTestResult):
    """Print detailed panel for stop file test result."""
    lines = [
        f"[bold]Test:[/bold] {result.test_name}",
        f"[bold]Nonce:[/bold] {result.nonce}",
        f"[bold]Stop File:[/bold] {result.stop_file_name}",
    ]
    
    if result.stop_file_created:
        lines.append(f"[bold green]Created:[/bold green] ✓ Yes")
        if result.stop_file_content:
            lines.append(f"[bold]Content:[/bold] {json.dumps(result.stop_file_content, indent=2)}")
    else:
        lines.append(f"[bold yellow]Created:[/bold yellow] ✗ No")
    
    if result.agent_response:
        lines.append(f"[bold]Agent Response:[/bold]")
        lines.append(f"  {result.agent_response[:500]}...")
    
    if result.error:
        lines.append(f"[bold red]Error:[/bold red] {result.error}")
    
    if result.events_file:
        lines.append(f"[bold]Events:[/bold] {result.events_file}")
    
    console.print(Panel("\n".join(lines), title=f"Results: {result.test_name}"))


def print_results_table(results: list[TestResult]):
    """Print summary table of test results."""
    table = Table(title="Loop Detection Stress Test Results", show_header=True)
    table.add_column("Test", style="cyan")
    table.add_column("Cycles", justify="right")
    table.add_column("SDK Abort", style="red")
    table.add_column("LoopDetector", style="yellow")
    table.add_column("Events File")
    
    for r in results:
        abort_info = f"✓ {r.abort_reason} (cycle {r.abort_cycle})" if r.abort_triggered else "—"
        loop_info = f"✓ {r.loop_reason} (cycle {r.loop_cycle})" if r.loop_detected else "—"
        events_info = Path(r.events_file).name if r.events_file else "—"
        
        if r.error:
            abort_info = f"[red]Error: {r.error[:30]}[/red]"
        
        table.add_row(
            r.test_name,
            str(r.cycles_run),
            abort_info,
            loop_info,
            events_info,
        )
    
    console.print(table)


def print_detailed_result(result: TestResult):
    """Print detailed panel for a single result."""
    lines = [
        f"[bold]Test:[/bold] {result.test_name}",
        f"[bold]Cycles Run:[/bold] {result.cycles_run}",
    ]
    
    if result.abort_triggered:
        lines.extend([
            f"[bold red]SDK Abort:[/bold red] Yes",
            f"  Reason: {result.abort_reason}",
            f"  Cycle: {result.abort_cycle}",
        ])
        if result.abort_details:
            lines.append(f"  Details: {result.abort_details}")
    else:
        lines.append("[bold]SDK Abort:[/bold] No")
    
    if result.loop_detected:
        lines.extend([
            f"[bold yellow]LoopDetector:[/bold yellow] Triggered",
            f"  Reason: {result.loop_reason}",
            f"  Cycle: {result.loop_cycle}",
        ])
    else:
        lines.append("[bold]LoopDetector:[/bold] Not triggered")
    
    if result.events_file:
        lines.append(f"[bold]Events:[/bold] {result.events_file}")
        # Analyze events
        analysis = analyze_events(Path(result.events_file))
        if "error" not in analysis:
            lines.append(f"  Total events: {analysis['total_events']}")
            lines.append(f"  Turns: {analysis['turn_count']}")
            if analysis['abort_events']:
                lines.append(f"  Abort events: {len(analysis['abort_events'])}")
            if analysis['reasoning_events']:
                lines.append(f"  Reasoning events: {len(analysis['reasoning_events'])}")
    
    if result.reasoning_samples:
        lines.append("[bold]Reasoning Samples:[/bold]")
        for i, sample in enumerate(result.reasoning_samples[:2], 1):
            lines.append(f"  [{i}] {sample[:100]}...")
    
    if result.error:
        lines.append(f"[bold red]Error:[/bold red] {result.error}")
    
    console.print(Panel("\n".join(lines), title=f"Results: {result.test_name}"))


@click.group()
@click.option("--adapter", "-a", default="copilot", help="Adapter to use (copilot, mock)")
@click.option("--model", "-m", default="gpt-4o", help="Model to use")
@click.option(
    "--output-dir", "-o", type=click.Path(), default="./loop-test-logs",
    help="Output directory for event logs"
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, adapter: str, model: str, output_dir: str, verbose: bool):
    """Loop Detection Stress Test Tool.
    
    Tests the Copilot SDK's abort/loop detection mechanisms by sending
    prompts designed to trigger loop awareness in the AI.
    """
    ctx.ensure_object(dict)
    ctx.obj["adapter"] = adapter
    ctx.obj["model"] = model
    ctx.obj["output_dir"] = Path(output_dir)
    ctx.obj["output_dir"].mkdir(parents=True, exist_ok=True)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--cycles", "-n", default=5, help="Number of cycles to run")
@click.pass_context
def repeated(ctx, cycles: int):
    """Run repeated prompt test - sends same prompt N times."""
    console.print(Panel.fit(
        f"Running repeated prompt test\n"
        f"Adapter: {ctx.obj['adapter']}\n"
        f"Model: {ctx.obj['model']}\n"
        f"Cycles: {cycles}",
        title="🔄 Repeated Prompt Test"
    ))
    
    result = asyncio.run(run_repeated_prompt_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        cycles,
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    ))
    
    print_detailed_result(result)


@cli.command()
@click.pass_context
def elicit(ctx):
    """Run explicit loop-elicit test - asks AI to respond as if in loop."""
    console.print(Panel.fit(
        f"Running loop elicit test\n"
        f"Adapter: {ctx.obj['adapter']}\n"
        f"Model: {ctx.obj['model']}",
        title="🎭 Loop Elicit Test"
    ))
    
    result = asyncio.run(run_loop_elicit_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    ))
    
    print_detailed_result(result)


@cli.command()
@click.pass_context
def minimal(ctx):
    """Run minimal response test - asks for very short response."""
    console.print(Panel.fit(
        f"Running minimal response test\n"
        f"Adapter: {ctx.obj['adapter']}\n"
        f"Model: {ctx.obj['model']}",
        title="📏 Minimal Response Test"
    ))
    
    result = asyncio.run(run_minimal_response_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    ))
    
    print_detailed_result(result)


@cli.command("all")
@click.option("--cycles", "-n", default=5, help="Number of cycles for repeated test")
@click.pass_context
def run_all(ctx, cycles: int):
    """Run all stress tests."""
    console.print(Panel.fit(
        f"Running ALL loop detection stress tests\n"
        f"Adapter: {ctx.obj['adapter']}\n"
        f"Model: {ctx.obj['model']}\n"
        f"Output: {ctx.obj['output_dir']}",
        title="🧪 Full Stress Test Suite"
    ))
    
    results = []
    
    # Run repeated prompt test
    console.print("\n[bold cyan]1/3 Repeated Prompt Test[/bold cyan]")
    results.append(asyncio.run(run_repeated_prompt_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        cycles,
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    )))
    
    # Run loop elicit test
    console.print("\n[bold cyan]2/3 Loop Elicit Test[/bold cyan]")
    results.append(asyncio.run(run_loop_elicit_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    )))
    
    # Run minimal response test
    console.print("\n[bold cyan]3/3 Minimal Response Test[/bold cyan]")
    results.append(asyncio.run(run_minimal_response_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
    )))
    
    # Print summary
    console.print("\n")
    print_results_table(results)
    
    # Print detailed results
    for result in results:
        console.print()
        print_detailed_result(result)


@cli.command()
@click.option("--nonce", default=None, help="Specific nonce to use (random if not set)")
@click.pass_context
def stopfile(ctx, nonce: Optional[str]):
    """Run stop file creation test - asks AI to create STOPAUTOMATION file."""
    test_nonce = nonce or generate_nonce()
    console.print(Panel.fit(
        f"Running stop file elicit test\n"
        f"Adapter: {ctx.obj['adapter']}\n"
        f"Model: {ctx.obj['model']}\n"
        f"Nonce: {test_nonce}",
        title="📁 Stop File Elicit Test"
    ))
    
    result = asyncio.run(run_stop_file_elicit_test(
        ctx.obj["adapter"],
        ctx.obj["model"],
        ctx.obj["output_dir"],
        ctx.obj["verbose"],
        nonce=test_nonce,
    ))
    
    print_stop_file_result(result)
    
    # Exit code based on whether file was created
    if result.stop_file_created:
        console.print("\n[green]✓ Stop file mechanism VERIFIED - agent created the file[/green]")
        raise SystemExit(0)
    else:
        msg = (
            "\n[yellow]⚠ Stop file NOT created - agent may have been blocked or "
            "refused[/yellow]"
        )
        console.print(msg)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
