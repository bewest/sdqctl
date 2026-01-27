"""
Logging configuration for sdqctl.

Provides centralized logging setup with verbosity levels:
- 0 (default): WARNING - errors and warnings only
- 1 (-v):      INFO - key operations (turns, tools, tokens, intents)
- 2 (-vv):     DEBUG - detailed info (reasoning, args, context usage)
- 3+ (-vvv):   TRACE - everything (deltas, raw events, partial results)

Enhanced features:
- WorkflowLoggerAdapter: Adds workflow and phase context to log messages
- Structured logging support for machine-readable output
"""

import logging
import sys
from dataclasses import dataclass
from typing import Optional

# Custom TRACE level (more verbose than DEBUG)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    """Log at TRACE level."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


# Add trace method to Logger class
logging.Logger.trace = trace


@dataclass
class WorkflowContext:
    """Context for workflow-aware logging.

    Tracks the current workflow, cycle, and prompt position
    to provide richer log output.
    """
    workflow_name: Optional[str] = None
    workflow_path: Optional[str] = None
    cycle: Optional[int] = None
    total_cycles: Optional[int] = None
    prompt: Optional[int] = None
    total_prompts: Optional[int] = None
    phase_name: Optional[str] = None

    def format_prefix(self) -> str:
        """Format the context as a log prefix.

        Examples:
            [proposal-dev]
            [proposal-dev:1/3]
            [proposal-dev:1/3:2/4]
            [proposal-dev:Execute]
        """
        if not self.workflow_name:
            return ""

        parts = [self.workflow_name]

        # Add cycle position if known
        if self.cycle is not None:
            if self.total_cycles and self.total_cycles > 1:
                parts.append(f"{self.cycle}/{self.total_cycles}")

        # Add prompt position if known
        if self.prompt is not None and self.total_prompts:
            parts.append(f"P{self.prompt}/{self.total_prompts}")

        # Add phase name if known (alternative to prompt number)
        if self.phase_name and self.prompt is None:
            parts.append(self.phase_name)

        if len(parts) == 1:
            return f"[{parts[0]}]"
        return f"[{parts[0]}:{':'.join(parts[1:])}]"


class WorkflowLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that includes workflow context in messages.

    Usage:
        ctx = WorkflowContext(workflow_name="fix-quirks", cycle=1, total_cycles=3)
        logger = WorkflowLoggerAdapter(get_logger("sdqctl.adapters.copilot"), ctx)
        logger.info("Turn started")  # Logs: [fix-quirks:1/3] Turn started
    """

    def __init__(self, logger: logging.Logger, context: WorkflowContext):
        super().__init__(logger, {})
        self.context = context

    def process(self, msg, kwargs):
        prefix = self.context.format_prefix()
        if prefix:
            return f"{prefix} {msg}", kwargs
        return msg, kwargs

    def update_context(self, **kwargs):
        """Update context fields.

        Example:
            logger.update_context(cycle=2, prompt=1, phase_name="Select")
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

    # Add trace method for compatibility
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self.log(TRACE, msg, *args, **kwargs)


# Global workflow context for the current session
_current_workflow_context: Optional[WorkflowContext] = None


def get_workflow_context() -> Optional[WorkflowContext]:
    """Get the current workflow context."""
    return _current_workflow_context


def set_workflow_context(context: Optional[WorkflowContext]) -> None:
    """Set the current workflow context."""
    global _current_workflow_context
    _current_workflow_context = context


class WorkflowContextFormatter(logging.Formatter):
    """Formatter that includes workflow context if available."""

    def format(self, record):
        # Add workflow context prefix if available
        ctx = get_workflow_context()
        if ctx:
            prefix = ctx.format_prefix()
            if prefix:
                record.msg = f"{prefix} {record.msg}"
        return super().format(record)


def setup_logging(verbosity: int = 0, quiet: bool = False) -> logging.Logger:
    """Configure logging based on verbosity level.

    Args:
        verbosity: Number of -v flags (0=WARNING, 1=INFO, 2=DEBUG, 3+=TRACE)
        quiet: If True, suppress all output except errors

    Returns:
        The configured root logger for sdqctl
    """
    # Determine log level
    if quiet:
        level = logging.ERROR
    elif verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    else:  # verbosity >= 3
        level = TRACE

    # Get our logger
    logger = logging.getLogger("sdqctl")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Format based on verbosity
    if verbosity >= 2:
        # Detailed format for debug/trace - includes workflow context
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%H:%M:%S"
        formatter = WorkflowContextFormatter(fmt, datefmt=datefmt)
    elif verbosity == 1:
        # Simple format for info
        fmt = "[%(levelname)s] %(message)s"
        datefmt = None
        formatter = WorkflowContextFormatter(fmt, datefmt=datefmt)
    else:
        # Minimal format for warnings
        fmt = "%(message)s"
        datefmt = None
        formatter = logging.Formatter(fmt, datefmt=datefmt)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # At TRACE level, also enable debug for external libs
    if verbosity >= 3:
        logging.getLogger().setLevel(logging.DEBUG)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Module name (e.g., "sdqctl.commands.run").
              If None, returns the root sdqctl logger.

    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("sdqctl")
    return logging.getLogger(name)


def get_workflow_logger(
    name: str,
    workflow_name: Optional[str] = None,
    **context_kwargs
) -> WorkflowLoggerAdapter:
    """Get a logger with workflow context.

    Args:
        name: Module name for the base logger
        workflow_name: Name of the workflow (e.g., "fix-quirks")
        **context_kwargs: Additional context fields (cycle, prompt, etc.)

    Returns:
        WorkflowLoggerAdapter with context

    Example:
        logger = get_workflow_logger(
            "sdqctl.adapters.copilot",
            workflow_name="proposal-dev",
            cycle=1,
            total_cycles=3
        )
    """
    base_logger = get_logger(name)
    context = WorkflowContext(workflow_name=workflow_name, **context_kwargs)
    return WorkflowLoggerAdapter(base_logger, context)
