"""
Block step execution for ON-FAILURE and ON-SUCCESS handlers.

Handles execution of steps within conditional blocks during conversation runs.
"""

import logging
import shlex
import subprocess
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel

from .utils import truncate_output

logger = logging.getLogger("sdqctl.commands.blocks")


async def execute_block_steps(
    steps: list,
    conv,
    session,
    ai_adapter,
    adapter_session,
    console,
    progress_fn,
    first_prompt: bool,
) -> None:
    """Execute steps inside an ON-FAILURE or ON-SUCCESS block.

    Handles a subset of step types appropriate for blocks:
    - prompt: Send to AI
    - run: Execute command (no nested blocks, no retry)
    - checkpoint: Save state
    - compact: Compress context
    - pause: Wait for user

    Args:
        steps: List of ConversationStep objects to execute
        conv: Parent ConversationFile for settings
        session: Current Session object
        ai_adapter: Adapter for AI communication
        adapter_session: Current adapter session
        console: Rich console for output
        progress_fn: Progress callback function
        first_prompt: Whether this is the first prompt in session
    """
    for block_step in steps:
        step_type = block_step.type
        step_content = block_step.content if hasattr(block_step, 'content') else ""

        if step_type == "prompt":
            # Send prompt to AI
            logger.info(f"  📝 Block PROMPT: {step_content[:50]}...")
            progress_fn("    📝 Block prompt...")

            response = await ai_adapter.send(adapter_session, step_content)
            session.add_message("assistant", response)

            # Display response
            console.print(Panel(Markdown(response), title="[cyan]AI Response (Block)[/cyan]"))

        elif step_type == "run":
            # Execute command (simplified, no nested blocks or retry)
            command = step_content
            logger.info(f"  🔧 Block RUN: {command}")
            progress_fn(f"    🔧 Running: {command[:40]}...")

            try:
                run_dir = Path(conv.cwd) if conv.cwd else Path.cwd()
                result = subprocess.run(
                    command if conv.allow_shell else shlex.split(command),
                    shell=conv.allow_shell,
                    capture_output=True,
                    text=True,
                    timeout=conv.run_timeout,
                    cwd=run_dir,
                )

                if result.returncode == 0:
                    logger.info("    ✓ Block RUN succeeded")
                    progress_fn("    ✓ Command succeeded")
                else:
                    logger.warning(f"    ✗ Block RUN failed (exit {result.returncode})")
                    progress_fn(f"    ✗ Command failed (exit {result.returncode})")

                # Add output to context
                if result.stdout or result.stderr:
                    output_text = result.stdout or ""
                    if result.stderr:
                        output_text += f"\n[stderr]\n{result.stderr}"
                    output_text = truncate_output(output_text, conv.run_output_limit)
                    run_msg = f"[Block RUN output]\n```\n$ {command}\n{output_text}\n```"
                    session.add_message("system", run_msg)

            except subprocess.TimeoutExpired:
                logger.error("    ✗ Block RUN timed out")
                progress_fn(f"    ✗ Timeout after {conv.run_timeout}s")
            except Exception as e:
                logger.error(f"    ✗ Block RUN error: {e}")
                progress_fn(f"    ✗ Error: {e}")

        elif step_type == "checkpoint":
            checkpoint_name = step_content or "block-checkpoint"
            logger.info(f"  💾 Block CHECKPOINT: {checkpoint_name}")
            progress_fn(f"    💾 Checkpoint: {checkpoint_name}")
            session.save_pause_checkpoint(checkpoint_name)

        elif step_type == "compact":
            logger.info("  🗜  Block COMPACT")
            progress_fn("    🗜  Compacting...")
            compact_prompt = "Summarize the conversation so far, preserving key context."
            response = await ai_adapter.send(adapter_session, compact_prompt)
            session.add_message("system", f"[Compaction summary]\n{response}")

        elif step_type == "pause":
            pause_msg = "⏸  Paused by ON-FAILURE/ON-SUCCESS block. Press Enter to continue..."
            console.print(f"[yellow]{pause_msg}[/yellow]")
            input()

        elif step_type == "consult":
            topic = step_content or "Open Questions"
            console.print(f"[yellow]⏸  CONSULT: {topic}[/yellow]")
            console.print("[dim]Consultation required. Press Enter to continue...[/dim]")
            input()
