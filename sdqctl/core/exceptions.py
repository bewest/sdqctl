"""
Custom exceptions for sdqctl.

Provides specific exception types with associated exit codes
for different failure modes. All exceptions support JSON serialization
for CI integration via --json-errors flag.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ExitCode:
    """Standard exit codes for sdqctl."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISSING_FILES = 2
    LOOP_DETECTED = 3
    AGENT_ABORTED = 4
    RUN_FAILED = 5
    VALIDATION_FAILED = 6
    VERIFY_FAILED = 7


class LoopReason(Enum):
    """Reasons for loop detection."""
    REASONING_PATTERN = "reasoning_pattern"  # AI reasoning mentions loop
    IDENTICAL_RESPONSES = "identical_responses"  # N identical responses
    MINIMAL_RESPONSE = "minimal_response"  # Response too short
    STOP_FILE = "stop_file"  # Agent created stop signal file (Q-002)


@dataclass
class LoopDetected(Exception):
    """Raised when a repetitive loop is detected in AI responses.

    Attributes:
        reason: The type of loop signal detected
        details: Human-readable explanation
        cycle_number: Which cycle detected the loop
    """
    reason: LoopReason
    details: str
    cycle_number: Optional[int] = None

    def __str__(self) -> str:
        cycle_info = f" (cycle {self.cycle_number})" if self.cycle_number else ""
        return f"Loop detected{cycle_info}: {self.details}"

    @property
    def exit_code(self) -> int:
        return ExitCode.LOOP_DETECTED


@dataclass
class MissingContextFiles(Exception):
    """Raised when mandatory CONTEXT files are missing.

    Attributes:
        files: List of missing file patterns/paths
        resolved_paths: Optional dict mapping patterns to resolved paths
    """
    files: list[str]
    resolved_paths: Optional[dict[str, str]] = None

    def __str__(self) -> str:
        if len(self.files) == 1:
            return f"Missing mandatory context file: {self.files[0]}"
        return f"Missing {len(self.files)} mandatory context files: {', '.join(self.files)}"

    @property
    def exit_code(self) -> int:
        return ExitCode.MISSING_FILES


@dataclass
class AgentAborted(Exception):
    """Raised when the agent signals it should stop (via SDK abort event).

    This occurs when the agent determines continuing would be unproductive,
    such as repeated requests or circular workflows.

    Attributes:
        reason: Reason for abort (from SDK event)
        details: Additional context
        turn_number: Which turn triggered the abort
    """
    reason: str = "unknown"
    details: Optional[str] = None
    turn_number: Optional[int] = None

    def __str__(self) -> str:
        turn_info = f" (turn {self.turn_number})" if self.turn_number else ""
        detail_info = f": {self.details}" if self.details else ""
        return f"Agent aborted{turn_info} - {self.reason}{detail_info}"

    @property
    def exit_code(self) -> int:
        return ExitCode.AGENT_ABORTED


@dataclass
class RunCommandFailed(Exception):
    """Raised when a RUN directive command fails.

    Attributes:
        command: The command that failed
        exit_code_val: Exit code from the command
        stderr: Standard error output
        stdout: Standard output
        timeout: Whether the command timed out
    """
    command: str
    exit_code_val: int
    stderr: Optional[str] = None
    stdout: Optional[str] = None
    timeout: bool = False

    def __str__(self) -> str:
        if self.timeout:
            return f"Command timed out: {self.command}"
        return f"Command failed with exit code {self.exit_code_val}: {self.command}"

    @property
    def exit_code(self) -> int:
        return ExitCode.RUN_FAILED


def exception_to_json(exc: Exception, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Convert an exception to a JSON-serializable dictionary.

    Args:
        exc: The exception to convert
        context: Optional additional context (workflow, cycle, etc.)

    Returns:
        JSON-serializable dict with error details
    """
    error_dict: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
    }

    # Add exit code if available
    if hasattr(exc, "exit_code"):
        error_dict["exit_code"] = exc.exit_code
    else:
        error_dict["exit_code"] = ExitCode.GENERAL_ERROR

    # Add specific fields for known exception types
    if isinstance(exc, LoopDetected):
        error_dict["reason"] = exc.reason.value
        error_dict["details"] = exc.details
        if exc.cycle_number is not None:
            error_dict["cycle_number"] = exc.cycle_number

    elif isinstance(exc, MissingContextFiles):
        error_dict["files"] = exc.files
        if exc.resolved_paths:
            error_dict["resolved_paths"] = exc.resolved_paths

    elif isinstance(exc, AgentAborted):
        error_dict["reason"] = exc.reason
        if exc.details:
            error_dict["details"] = exc.details
        if exc.turn_number is not None:
            error_dict["turn_number"] = exc.turn_number

    elif isinstance(exc, RunCommandFailed):
        error_dict["command"] = exc.command
        error_dict["command_exit_code"] = exc.exit_code_val
        error_dict["timeout"] = exc.timeout
        if exc.stderr:
            error_dict["stderr"] = exc.stderr[:2000]  # Truncate for JSON
        if exc.stdout:
            error_dict["stdout"] = exc.stdout[:2000]  # Truncate for JSON

    # Add context if provided
    if context:
        error_dict["context"] = context

    return {"error": error_dict}


def format_json_error(exc: Exception, context: Optional[dict[str, Any]] = None) -> str:
    """Format an exception as a JSON string.

    Args:
        exc: The exception to format
        context: Optional additional context

    Returns:
        JSON string with error details
    """
    return json.dumps(exception_to_json(exc, context), indent=2, default=str)
