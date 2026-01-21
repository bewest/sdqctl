"""
Progress output for sdqctl.

Provides user-facing progress messages that print to stdout by default.
Separate from logging (which goes to stderr for debug/diagnostics).

Usage:
    from ..core.progress import progress, set_quiet

    progress("Running workflow.conv...")
    progress("  Step 1/3: Sending prompt...")
    progress("Done in 4.1s")
"""

import sys
import time
from contextlib import contextmanager
from typing import Optional

# Global quiet flag - when True, suppresses progress output
_quiet = False


def set_quiet(quiet: bool = True) -> None:
    """Set global quiet mode."""
    global _quiet
    _quiet = quiet


def is_quiet() -> bool:
    """Check if quiet mode is enabled."""
    return _quiet


def progress(message: str, end: str = "\n", flush: bool = True) -> None:
    """Print progress message to stdout (unless quiet mode).
    
    Args:
        message: The message to print
        end: String appended after the message (default: newline)
        flush: Whether to flush stdout immediately
    """
    if not _quiet:
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
