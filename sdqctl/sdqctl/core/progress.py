"""
Progress output for sdqctl.

Provides user-facing progress messages that print to stdout by default.
Separate from logging (which goes to stderr for debug/diagnostics).

Features:
- Cycle/step/prompt position tracking
- Context window usage percentage
- TTY-aware formatting (overwrites vs static lines)

Usage:
    from ..core.progress import progress, set_quiet, WorkflowProgress

    # Simple progress
    progress("Running workflow.conv...")
    progress("Done in 4.1s")

    # Enhanced workflow progress with context tracking
    wp = WorkflowProgress("workflow.conv", total_cycles=3, total_prompts=4)
    wp.start()
    wp.prompt_sending(cycle=1, prompt=1, context_pct=23.5)
    wp.prompt_complete(cycle=1, prompt=1, duration=3.2, tokens_added=847, context_pct=31.0)
    wp.done()
"""

import sys
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

# Global quiet flag - when True, suppresses progress output
_quiet = False

# Global timestamp flag - when True, includes timestamps in progress output
_show_timestamps = False

# TTY detection for progress overwrites
_is_tty = sys.stdout.isatty()


def set_quiet(quiet: bool = True) -> None:
    """Set global quiet mode."""
    global _quiet
    _quiet = quiet


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return _quiet


def set_timestamps(enabled: bool = True) -> None:
    """Enable or disable timestamps in progress output.

    When enabled, progress messages include timestamps matching logger format.
    """
    global _show_timestamps
    _show_timestamps = enabled


def is_tty() -> bool:
    """Check if stdout is a TTY (for progress overwrites)."""
    return _is_tty


def progress(message: str, end: str = "\n", flush: bool = True) -> None:
    """Print progress message to stdout (unless quiet mode).

    Args:
        message: The message to print
        end: String appended after the message (default: newline)
        flush: Whether to flush stdout immediately
    """
    if not _quiet:
        if _show_timestamps:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"{timestamp} {message}"
        print(message, end=end, flush=flush, file=sys.stdout)


def progress_step(current: int, total: int, action: str) -> None:
    """Print a step progress message.

    Example: "  Step 2/5: Sending prompt..."
    """
    progress(f"  Step {current}/{total}: {action}")


def progress_file(action: str, path: str) -> None:
    """Print a file operation message.

    Example: "  Writing output to reports/analysis.md"
    """
    progress(f"  {action} {path}")


def progress_done(duration_seconds: float) -> None:
    """Print completion message with duration.

    Example: "Done in 4.1s"
    """
    progress(f"Done in {duration_seconds:.1f}s")


def agent_response(response: str, cycle: int = 0, prompt: int = 0) -> None:
    """Print agent response to stdout (unless quiet mode).

    Displays the agent's response text for observability. Users can see
    what the agent is doing/thinking without needing -vvv.

    Args:
        response: The agent's response text
        cycle: Current cycle number (1-indexed, 0 if not in cycle mode)
        prompt: Current prompt number (1-indexed, 0 if single prompt)
    """
    if _quiet:
        return

    # Format header based on context
    if cycle > 0 and prompt > 0:
        header = f"[Agent Cycle {cycle}, Prompt {prompt}]"
    elif cycle > 0:
        header = f"[Agent Cycle {cycle}]"
    else:
        header = "[Agent]"

    # Print with clear visual separation
    print(f"\n{header}", file=sys.stdout)
    print("-" * len(header), file=sys.stdout)
    print(response, file=sys.stdout)
    print(file=sys.stdout, flush=True)


@contextmanager
def progress_timer():
    """Context manager that tracks elapsed time.

    Usage:
        with progress_timer() as timer:
            do_work()
        progress_done(timer.elapsed)
    """
    class Timer:
        def __init__(self):
            self.start = time.time()
            self.elapsed = 0.0

        def mark(self) -> float:
            self.elapsed = time.time() - self.start
            return self.elapsed

    timer = Timer()
    try:
        yield timer
    finally:
        timer.mark()


class ProgressTracker:
    """Track progress through a multi-step operation.

    Usage:
        tracker = ProgressTracker("workflow.conv", total_steps=5)
        tracker.start()
        for i in range(5):
            tracker.step(f"Processing step {i}")
            do_work()
            tracker.step_done()
        tracker.done()
    """

    def __init__(self, name: str, total_steps: int = 0):
        self.name = name
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time: Optional[float] = None
        self.step_start_time: Optional[float] = None

    def start(self) -> None:
        """Mark the start of the operation."""
        self.start_time = time.time()
        progress(f"Running {self.name}...")

    def step(self, action: str) -> None:
        """Start a new step."""
        self.current_step += 1
        self.step_start_time = time.time()
        if self.total_steps > 0:
            progress_step(self.current_step, self.total_steps, action)
        else:
            progress(f"  {action}")

    def step_done(self, result: Optional[str] = None) -> None:
        """Mark current step as complete."""
        if self.step_start_time:
            elapsed = time.time() - self.step_start_time
            if result:
                progress(f"  {result} ({elapsed:.1f}s)")
            # If no result, step message already printed

    def file_op(self, action: str, path: str) -> None:
        """Report a file operation."""
        progress_file(action, path)

    def checkpoint(self, name: str) -> None:
        """Report a checkpoint."""
        progress(f"  📌 CHECKPOINT: {name}")

    def done(self) -> None:
        """Mark operation complete."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            progress_done(elapsed)


class WorkflowProgress:
    """Enhanced progress tracking for workflow execution.

    Tracks cycle, prompt, and context usage with TTY-aware formatting.

    Usage:
        wp = WorkflowProgress("workflow.conv", total_cycles=3, total_prompts=4)
        wp.start()
        wp.prompt_sending(cycle=1, prompt=1, context_pct=23.5)
        wp.prompt_complete(cycle=1, prompt=1, duration=3.2, tokens_added=847, context_pct=31.0)
        wp.cycle_complete(cycle=1)
        wp.done()
    """

    def __init__(
        self,
        name: str,
        total_cycles: int = 1,
        total_prompts: int = 1,
        verbosity: int = 0,
    ):
        self.name = name
        self.total_cycles = total_cycles
        self.total_prompts = total_prompts
        self.verbosity = verbosity
        self.start_time: Optional[float] = None
        self.prompt_start_time: Optional[float] = None
        self._last_line_length = 0  # For TTY overwrite

    def _format_position(
        self,
        cycle: int,
        prompt: int,
        context_pct: Optional[float] = None,
    ) -> str:
        """Format cycle/prompt position string."""
        if self.total_cycles > 1:
            pos = f"[Cycle {cycle}/{self.total_cycles}] Prompt {prompt}/{self.total_prompts}"
        else:
            pos = f"Prompt {prompt}/{self.total_prompts}"

        if context_pct is not None:
            pos += f" (ctx: {context_pct:.0f}%)"

        return pos

    def _overwrite_line(self, message: str) -> None:
        """Print message, overwriting previous line if TTY."""
        if _is_tty and self._last_line_length > 0:
            # Clear previous line and write new one
            clear = "\r" + " " * self._last_line_length + "\r"
            print(clear, end="", flush=True, file=sys.stdout)

        if not _quiet:
            print(f"  {message}", end="" if _is_tty else "\n", flush=True, file=sys.stdout)
            self._last_line_length = len(message) + 2  # +2 for "  " prefix

    def _end_overwrite(self) -> None:
        """End any TTY overwrite with a newline."""
        if _is_tty and self._last_line_length > 0:
            print(file=sys.stdout)
            self._last_line_length = 0

    def start(self) -> None:
        """Mark the start of workflow execution."""
        self.start_time = time.time()
        progress(f"Running {self.name}...")

    def prompt_sending(
        self,
        cycle: int,
        prompt: int,
        context_pct: Optional[float] = None,
        preview: Optional[str] = None,
    ) -> None:
        """Report that a prompt is being sent.

        Args:
            cycle: Current cycle (1-indexed)
            prompt: Current prompt (1-indexed)
            context_pct: Context window usage percentage
            preview: Optional prompt preview (shown at -v)
        """
        self.prompt_start_time = time.time()
        pos = self._format_position(cycle, prompt, context_pct)

        if preview and self.verbosity >= 1:
            # Truncate preview
            if len(preview) > 50:
                preview = preview[:47] + "..."
            preview = preview.replace("\n", " ")
            message = f"{pos}: \"{preview}\""
        else:
            message = f"{pos}: Sending..."

        self._overwrite_line(message)

    def prompt_complete(
        self,
        cycle: int,
        prompt: int,
        duration: Optional[float] = None,
        tokens_added: Optional[int] = None,
        context_pct: Optional[float] = None,
    ) -> None:
        """Report that a prompt completed.

        Args:
            cycle: Current cycle (1-indexed)
            prompt: Current prompt (1-indexed)
            duration: Time taken in seconds
            tokens_added: Tokens added to context
            context_pct: New context window usage percentage
        """
        self._end_overwrite()

        if duration is None and self.prompt_start_time:
            duration = time.time() - self.prompt_start_time

        pos = self._format_position(cycle, prompt, context_pct)

        details = []
        if duration is not None:
            details.append(f"{duration:.1f}s")
        if tokens_added is not None:
            details.append(f"+{tokens_added} tokens")

        if details:
            progress(f"  {pos}: Complete ({', '.join(details)})")
        else:
            progress(f"  {pos}: Complete")

    def cycle_complete(self, cycle: int, compacted: bool = False) -> None:
        """Report that a cycle completed."""
        if compacted:
            progress(f"  [Cycle {cycle}/{self.total_cycles}] Complete (compacted)")
        else:
            progress(f"  [Cycle {cycle}/{self.total_cycles}] Complete")

    def file_op(self, action: str, path: str) -> None:
        """Report a file operation."""
        progress(f"  {action} {path}")

    def checkpoint(self, name: str) -> None:
        """Report a checkpoint."""
        progress(f"  📌 CHECKPOINT: {name}")

    def done(self) -> None:
        """Mark workflow complete."""
        self._end_overwrite()
        if self.start_time:
            elapsed = time.time() - self.start_time
            progress_done(elapsed)
