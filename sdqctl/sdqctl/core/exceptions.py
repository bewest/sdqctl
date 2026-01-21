"""
Custom exceptions for sdqctl.

Provides specific exception types with associated exit codes
for different failure modes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExitCode:
    """Standard exit codes for sdqctl."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISSING_FILES = 2
    LOOP_DETECTED = 3


class LoopReason(Enum):
    """Reasons for loop detection."""
    REASONING_PATTERN = "reasoning_pattern"  # AI reasoning mentions loop
    IDENTICAL_RESPONSES = "identical_responses"  # N identical responses
    MINIMAL_RESPONSE = "minimal_response"  # Response too short


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
