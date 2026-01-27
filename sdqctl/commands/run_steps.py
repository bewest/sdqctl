"""
RUN step handlers for workflow execution.

Handles RUN, RUN-ASYNC, and RUN-WAIT directives during runs.
"""

import logging
import shlex
import subprocess
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..adapters.base import AdapterBase, AdapterSession
    from ..core.conversation import ConversationFile
    from ..core.session import Session

from .utils import resolve_run_directory, truncate_output
from .utils import run_async as run_async_util

logger = logging.getLogger("sdqctl.commands.run_steps")


async def execute_run_step(
    step: Any,
    conv: "ConversationFile",
    session: "Session",
    ai_adapter: "AdapterBase",
    adapter_session: "AdapterSession",
    console: Any,
    progress: Callable[[str], None],
    first_prompt: bool,
    run_subprocess_fn: Callable,
) -> Optional[bool]:
    """Execute a RUN step with optional retry and AI-assisted fixes.

    Args:
        step: ConversationStep with command and retry options
        conv: ConversationFile for settings
        session: Session for context
        ai_adapter: Adapter for AI communication (for retries)
        adapter_session: Current adapter session
        console: Rich console for output
        progress: Progress callback
        first_prompt: Whether this is first prompt
        run_subprocess_fn: Function to run subprocess

    Returns:
        None to continue, or False if should stop execution
    """
    from .blocks import execute_block_steps

    step_content = getattr(step, 'content', step.get('content', ''))
    command = step_content
    retry_count = getattr(step, 'retry_count', 0)
    retry_prompt = getattr(step, 'retry_prompt', '')

    # retry_count is number of retries AFTER first attempt
    max_attempts = retry_count + 1
    attempt = 0
    last_result = None

    while attempt < max_attempts:
        attempt += 1
        is_retry = attempt > 1

        if is_retry:
            logger.info(f"🔄 RUN-RETRY attempt {attempt}/{max_attempts}: {command}")
            progress(f"  🔄 Retry {attempt}/{max_attempts}: {command[:40]}...")
        else:
            logger.info(f"🔧 RUN: {command}")
            progress(f"  🔧 Running: {command[:50]}...")

        run_start = time.time()
        try:
            run_dir = resolve_run_directory(
                conv.run_cwd, conv.cwd, conv.source_path
            )

            result = run_subprocess_fn(
                command,
                allow_shell=conv.allow_shell,
                timeout=conv.run_timeout,
                cwd=run_dir,
                env=conv.run_env if conv.run_env else None,
            )
            run_elapsed = time.time() - run_start
            last_result = result

            if result.returncode == 0:
                logger.info(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                progress(f"  ✓ Command succeeded ({run_elapsed:.1f}s)")
                break  # Success - exit retry loop
            else:
                rc = result.returncode
                logger.warning(f"  ✗ Command failed (exit {rc})")
                progress(f"  ✗ Command failed (exit {result.returncode})")

                # If retries remaining, send to AI for fix
                if retry_count > 0 and attempt < max_attempts:
                    # Capture error output for AI
                    error_output = result.stdout or ""
                    if result.stderr:
                        error_output += f"\n\n[stderr]\n{result.stderr}"
                    error_output = truncate_output(
                        error_output, conv.run_output_limit
                    )

                    # Build retry prompt for AI
                    full_retry_prompt = f"""{retry_prompt}

Command that failed:
```
$ {command}
{error_output}
```

Exit code: {result.returncode}

Please analyze the error and make necessary fixes. \
After fixing, the command will be retried automatically."""

                    logger.info("  📤 Sending error to AI for fix...")
                    progress("  📤 Asking AI to fix...")

                    # Send to AI and wait for response
                    try:
                        retry_response = run_async_util(ai_adapter.run(
                            adapter_session,
                            full_retry_prompt,
                            restrictions=conv.file_restrictions,
                            stream=True,
                        ))
                        if retry_response:
                            resp_len = len(retry_response)
                            logger.info(f"  📥 AI response ({resp_len} chars)")
                            progress("  📥 AI response received, retrying...")
                            # Add AI response to session context
                            session.add_message("assistant", retry_response)
                    except Exception as ai_err:
                        logger.error(f"  ✗ AI fix request failed: {ai_err}")
                        progress(f"  ✗ AI request failed: {ai_err}")
                        break  # Can't retry without AI, exit loop

                    continue  # Retry the command

        except subprocess.TimeoutExpired as e:
            logger.error(f"  ✗ Command timed out after {conv.run_timeout}s")
            progress(f"  ✗ Command timed out after {conv.run_timeout}s")
            # Timeout - no retry (complex to handle)
            last_result = type('Result', (), {
                'returncode': -1,
                'stdout': e.stdout or '',
                'stderr': e.stderr or f'Timeout after {conv.run_timeout}s'
            })()
            break

        except Exception as e:
            logger.error(f"  ✗ Command error: {e}")
            last_result = type('Result', (), {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            })()
            break

    # After retry loop, handle final result
    if last_result:
        include_output = (
            conv.run_output == "always" or
            (conv.run_output == "on-error" and last_result.returncode != 0)
        )

        if include_output:
            output_text = last_result.stdout or ""
            if last_result.stderr:
                output_text += f"\n\n[stderr]\n{last_result.stderr}"
            output_text = truncate_output(output_text, conv.run_output_limit)

            if output_text.strip():
                rc = last_result.returncode
                status_marker = "" if rc == 0 else f" (exit {rc})"
                retry_marker = (
                    f" [after {attempt} attempt(s)]"
                    if retry_count > 0 else ""
                )
                run_context = (
                    f"```\n$ {command}{status_marker}{retry_marker}"
                    f"\n{output_text}\n```"
                )
                session.add_message("system", f"[RUN output]\n{run_context}")
                out_len = len(output_text)
                logger.debug(f"Added RUN output to context ({out_len} chars)")

        # Execute ON-FAILURE or ON-SUCCESS blocks if present
        on_failure = getattr(step, 'on_failure', None)
        on_success = getattr(step, 'on_success', None)

        if last_result.returncode != 0 and on_failure:
            logger.info("🔀 Executing ON-FAILURE block")
            progress("  🔀 Running ON-FAILURE steps...")
            await execute_block_steps(
                on_failure, conv, session, ai_adapter, adapter_session,
                console, progress, first_prompt
            )
        elif last_result.returncode == 0 and on_success:
            logger.info("🔀 Executing ON-SUCCESS block")
            progress("  🔀 Running ON-SUCCESS steps...")
            await execute_block_steps(
                on_success, conv, session, ai_adapter, adapter_session,
                console, progress, first_prompt
            )

        # Handle stop-on-error AFTER output, blocks, retries
        # Only stop if no ON-FAILURE block was present
        is_failed = last_result.returncode != 0
        should_stop = conv.run_on_error == "stop" and not on_failure
        if is_failed and should_stop:
            retry_msg = f" after {attempt} attempts" if retry_count > 0 else ""
            console.print(f"[red]RUN failed{retry_msg}: {command}[/red]")
            console.print(f"[dim]Exit code: {last_result.returncode}[/dim]")
            if last_result.stderr:
                console.print(f"[dim]stderr: {last_result.stderr[:500]}[/dim]")
            session.state.status = "failed"
            rc = last_result.returncode
            ckpt_msg = f"RUN failed: {command} (exit {rc})"
            checkpoint_path = session.save_pause_checkpoint(ckpt_msg)
            console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
            return False  # Signal to stop execution

    return None  # Continue execution


def execute_run_async_step(
    step: Any,
    conv: "ConversationFile",
    session: "Session",
    progress: Callable[[str], None],
) -> None:
    """Execute a RUN-ASYNC step (background process).

    Args:
        step: ConversationStep with command
        conv: ConversationFile for settings
        session: Session for context
        progress: Progress callback
    """
    import os

    step_content = getattr(step, 'content', step.get('content', ''))
    command = step_content

    logger.info(f"🔧 RUN-ASYNC: {command}")
    progress(f"  🔧 Starting background: {command[:50]}...")

    run_dir = resolve_run_directory(
        conv.run_cwd, conv.cwd, conv.source_path
    )

    # Build environment
    run_env = None
    if conv.run_env:
        run_env = os.environ.copy()
        run_env.update(conv.run_env)

    # Start process in background
    args = command if conv.allow_shell else shlex.split(command)
    proc = subprocess.Popen(
        args,
        shell=conv.allow_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=run_dir,
        env=run_env,
    )
    conv.async_processes.append((command, proc))
    logger.info(f"  ✓ Background process started (PID {proc.pid})")
    progress(f"  ✓ Background process started (PID {proc.pid})")
    async_msg = f"[RUN-ASYNC started]\n$ {command} (PID {proc.pid})"
    session.add_message("system", async_msg)


def execute_run_wait_step(
    step: Any,
    progress: Callable[[str], None],
) -> None:
    """Execute a RUN-WAIT step (sleep/delay).

    Args:
        step: ConversationStep with duration
        progress: Progress callback
    """
    step_content = getattr(step, 'content', step.get('content', ''))
    wait_spec = step_content.strip().lower()

    logger.info(f"⏱️ RUN-WAIT: {wait_spec}")

    # Parse duration: "5", "5s", "1m", "500ms"
    if wait_spec.endswith("ms"):
        wait_seconds = float(wait_spec[:-2]) / 1000
    elif wait_spec.endswith("m"):
        wait_seconds = float(wait_spec[:-1]) * 60
    elif wait_spec.endswith("s"):
        wait_seconds = float(wait_spec[:-1])
    else:
        wait_seconds = float(wait_spec)

    progress(f"  ⏱️ Waiting {wait_seconds}s...")
    time.sleep(wait_seconds)
    logger.info("  ✓ Wait complete")
    progress("  ✓ Wait complete")
