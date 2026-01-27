"""
JSON pipeline handler for iterate command.

Handles --from-json execution for external transformation pipelines.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich.console import Console

from ..adapters import get_adapter
from ..adapters.base import AdapterConfig
from ..core.conversation import ConversationFile
from ..core.loop_detector import generate_nonce, get_stop_file_instruction
from ..core.progress import progress as progress_print
from ..core.session import Session
from ..utils.output import PromptWriter
from .iterate_helpers import build_infinite_session_config

if TYPE_CHECKING:
    pass

logger = logging.getLogger("sdqctl.commands.json_pipeline")
console = Console()


async def execute_json_pipeline(
    json_data: dict,
    max_cycles_override: Optional[int],
    session_mode: str,
    adapter_name: Optional[str],
    model: Optional[str],
    checkpoint_dir: Optional[str],
    cli_prologues: tuple[str, ...],
    cli_epilogues: tuple[str, ...],
    cli_headers: tuple[str, ...],
    cli_footers: tuple[str, ...],
    output_file: Optional[str],
    event_log_path: Optional[str],
    json_output: bool,
    dry_run: bool,
    no_stop_file_prologue: bool = False,
    stop_file_nonce: Optional[str] = None,
    verbosity: int = 0,
    show_prompt: bool = False,
    min_compaction_density: int = 30,
    no_infinite_sessions: bool = False,
    compaction_threshold: int = 80,
    buffer_threshold: int = 95,
    json_errors: bool = False,
) -> None:
    """Execute workflow from pre-rendered JSON.

    Enables external transformation pipelines:
        sdqctl render cycle foo.conv --json | transform.py | sdqctl cycle --from-json -

    Args:
        json_data: Pre-rendered workflow data
        max_cycles_override: Override max cycles from CLI
        session_mode: Session mode (accumulate, compact, fresh)
        adapter_name: Override adapter name
        model: Override model name
        checkpoint_dir: Directory for checkpoints
        cli_prologues: CLI-provided prologues
        cli_epilogues: CLI-provided epilogues
        cli_headers: CLI-provided headers
        cli_footers: CLI-provided footers
        output_file: Output file path
        event_log_path: Event log file path
        json_output: Output as JSON
        dry_run: Dry run mode
        no_stop_file_prologue: Disable stop file instructions
        stop_file_nonce: Override stop file nonce
        verbosity: Verbosity level
        show_prompt: Show prompts on stderr
        min_compaction_density: Min compaction density threshold
        no_infinite_sessions: Disable infinite sessions
        compaction_threshold: Compaction threshold percentage
        buffer_threshold: Buffer threshold percentage
        json_errors: Output errors as JSON
    """
    import time

    from ..core.conversation import (
        build_output_with_injection,
        substitute_template_variables,
    )
    from ..core.loop_detector import LoopDetector

    # Initialize prompt writer for stderr output
    prompt_writer = PromptWriter(enabled=show_prompt)

    cycle_start = time.time()
    workflow_name = json_data.get("workflow_name", "json-workflow")

    # Extract configuration from JSON
    conv = ConversationFile.from_rendered_json(json_data)

    # Override with CLI options if provided
    if adapter_name:
        conv.adapter = adapter_name
    if model:
        conv.model = model

    # Apply CLI prologues/epilogues
    if cli_prologues:
        conv.prologues = list(cli_prologues) + conv.prologues
    if cli_epilogues:
        conv.epilogues = list(cli_epilogues) + conv.epilogues
    if cli_headers:
        conv.headers = list(cli_headers)
    if cli_footers:
        conv.footers = list(cli_footers)

    max_cycles = max_cycles_override or json_data.get("max_cycles", conv.max_cycles) or 1

    progress_print(f"Running from JSON ({max_cycles} cycle(s), session={session_mode})...")

    if dry_run:
        console.print(
            f"[dim]Would execute {len(conv.prompts)} prompt(s) "
            f"for {max_cycles} cycle(s)[/dim]"
        )
        console.print(f"[dim]Adapter: {conv.adapter}, Model: {conv.model}[/dim]")
        return

    # Get adapter
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Adapter error: {e}[/red]")
        return

    # Create adapter config with infinite sessions (merge CLI + conv file settings)
    infinite_config = build_infinite_session_config(
        no_infinite_sessions, compaction_threshold, buffer_threshold, min_compaction_density,
        conv_infinite_sessions=conv.infinite_sessions,
        conv_compaction_min=conv.compaction_min,
        conv_compaction_threshold=conv.compaction_threshold,
    )
    adapter_config = AdapterConfig(
        model=conv.model,
        event_log_path=event_log_path,
        debug_intents=conv.debug_intents,
        infinite_sessions=infinite_config,
    )

    # Initialize session
    session = Session(workflow=workflow_name)

    # Stop file handling
    stop_file_nonce_value = stop_file_nonce or generate_nonce()
    loop_detector = LoopDetector(
        max_cycles=max_cycles,
        stop_file_nonce=stop_file_nonce_value,
    )

    # Create adapter session
    adapter_session = await ai_adapter.create_session(adapter_config)
    session.sdk_session_id = adapter_session.sdk_session_id  # Q-018 fix

    try:
        responses = []

        for cycle_num in range(1, max_cycles + 1):
            progress_print(f"  Cycle {cycle_num}/{max_cycles}")

            # Check for stop file
            if loop_detector.check_stop_file():
                console.print("[yellow]Stop file detected, exiting[/yellow]")
                break

            # Build prompts for this cycle
            template_vars = json_data.get("template_variables", {}).copy()
            template_vars["CYCLE_NUMBER"] = str(cycle_num)
            template_vars["CYCLE_TOTAL"] = str(max_cycles)
            template_vars["STOP_FILE"] = f"STOPAUTOMATION-{stop_file_nonce_value}.json"

            for prompt_idx, prompt_text in enumerate(conv.prompts):
                # Substitute any remaining template variables
                final_prompt = substitute_template_variables(prompt_text, template_vars)

                # Add stop file instruction to first prompt
                if prompt_idx == 0 and cycle_num == 1 and not no_stop_file_prologue:
                    stop_instruction = get_stop_file_instruction(stop_file_nonce_value)
                    final_prompt = f"{stop_instruction}\n\n{final_prompt}"

                # Show prompt if enabled
                prompt_writer.write_prompt(
                    final_prompt,
                    cycle=cycle_num,
                    total_cycles=max_cycles,
                    prompt_num=prompt_idx + 1,
                    total_prompts=len(conv.prompts)
                )

                # Execute prompt
                response = await ai_adapter.run(
                    adapter_session,
                    final_prompt,
                    stream=verbosity >= 2,
                )
                responses.append(response)

                # Add to session
                session.add_message("user", final_prompt)
                session.add_message("assistant", response)

            # Handle session mode
            if session_mode == "compact" and cycle_num < max_cycles:
                progress_print("    Compacting...")
                await ai_adapter.compact(adapter_session)
            elif session_mode == "fresh" and cycle_num < max_cycles:
                progress_print("    Fresh session...")
                adapter_session = await ai_adapter.create_session(adapter_config)

        # Output
        session.state.status = "completed"
        total_elapsed = time.time() - cycle_start

        raw_output = "\n\n---\n\n".join(responses)
        final_output = build_output_with_injection(
            raw_output, conv.headers, conv.footers,
            base_path=Path.cwd(),
            variables=template_vars
        )

        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            Path(output_file).write_text(final_output)
            console.print(f"[green]Output written to {output_file}[/green]")
        else:
            console.print(final_output)

        progress_print(f"  Completed in {total_elapsed:.1f}s")

    finally:
        await ai_adapter.close_session(adapter_session)
