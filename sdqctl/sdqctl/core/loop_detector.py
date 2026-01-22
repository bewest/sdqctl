"""
Loop detection for AI workflow cycles.

Detects when the AI has entered a repetitive state and the workflow
should be aborted to avoid wasting tokens.

Supports multiple detection mechanisms:
1. Reasoning patterns - AI explicitly mentions being in a loop
2. Identical responses - Same response N times in a row
3. Minimal responses - Very short responses after first cycle
4. Stop file - Agent creates a signal file to request automation stop
"""

import hashlib
import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .exceptions import LoopDetected, LoopReason

logger = logging.getLogger("sdqctl.core.loop_detector")


# Patterns in AI reasoning that indicate loop awareness
LOOP_REASONING_PATTERNS = [
    r"\bin a loop\b",
    r"\bsame (?:workflow )?prompt (?:being )?repeated\b",
    r"\brepeated (?:prompt|request|question)\b",
    r"\balready (?:confirmed|answered|responded).*(?:multiple|several) times\b",
    r"\bkeep(?:ing)? (?:my )?response minimal\b",
    r"\brepetitive (?:cycle|loop|pattern)\b",
]

# Minimum response length after first cycle (chars)
# Lowered to 100 to catch degraded responses faster (Q-002 fix)
MIN_RESPONSE_LENGTH = 100

# Number of identical responses to trigger detection
# Lowered to 2 for faster loop detection (Q-002 fix)
IDENTICAL_RESPONSE_THRESHOLD = 2


@dataclass
class LoopDetector:
    """Detects repetitive loops in AI workflow execution.
    
    Monitors four signals:
    1. Reasoning patterns - AI explicitly mentions being in a loop
    2. Identical responses - Same response N times in a row
    3. Minimal responses - Very short responses after first cycle
    4. Stop file - Agent creates STOPAUTOMATION-{session_hash}.json
    
    Usage:
        detector = LoopDetector(session_id="my-session")
        for cycle in range(max_cycles):
            response = await ai.send(prompt)
            reasoning = get_reasoning()  # From adapter
            if result := detector.check(reasoning, response, cycle):
                raise result
    """
    
    # Configuration
    identical_threshold: int = IDENTICAL_RESPONSE_THRESHOLD
    min_response_length: int = MIN_RESPONSE_LENGTH
    session_id: Optional[str] = None  # For stop file hash
    stop_file_dir: Optional[Path] = None  # Directory to check for stop file
    
    # State
    response_hashes: deque = field(default_factory=lambda: deque(maxlen=5))
    response_lengths: list[int] = field(default_factory=list)
    last_reasoning: Optional[str] = None
    
    def __post_init__(self):
        """Initialize derived values."""
        if self.stop_file_dir is None:
            self.stop_file_dir = Path.cwd()
    
    @property
    def stop_file_name(self) -> str:
        """Get the stop file name for this session.
        
        Uses a hash of session_id for security (agent must know the ID).
        """
        if self.session_id:
            session_hash = hashlib.sha256(self.session_id.encode()).hexdigest()[:12]
            return f"STOPAUTOMATION-{session_hash}.json"
        return "STOPAUTOMATION.json"
    
    @property
    def stop_file_path(self) -> Path:
        """Full path to the stop file."""
        return self.stop_file_dir / self.stop_file_name
    
    def _check_stop_file(self) -> Optional[dict]:
        """Check if the agent has created a stop file.
        
        Returns the stop file contents if found, None otherwise.
        """
        try:
            if self.stop_file_path.exists():
                content = self.stop_file_path.read_text()
                logger.info(f"Stop file found: {self.stop_file_path}")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"reason": content.strip() or "Agent requested stop"}
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not check stop file: {e}")
        return None
    
    def _hash_response(self, response: str) -> str:
        """Create a fast hash of response content.
        
        Uses first 200 chars + length for speed while still
        catching duplicates.
        """
        normalized = response.strip().lower()
        sample = normalized[:200] + str(len(normalized))
        return hashlib.md5(sample.encode()).hexdigest()[:16]
    
    def _check_reasoning_pattern(self, reasoning: str) -> Optional[str]:
        """Check if reasoning contains loop-aware patterns.
        
        Returns the matched pattern or None.
        """
        if not reasoning:
            return None
            
        reasoning_lower = reasoning.lower()
        for pattern in LOOP_REASONING_PATTERNS:
            if re.search(pattern, reasoning_lower):
                return pattern
        return None
    
    def _check_identical_responses(self) -> bool:
        """Check if last N responses are identical."""
        if len(self.response_hashes) < self.identical_threshold:
            return False
        
        # Get last N hashes
        recent = list(self.response_hashes)[-self.identical_threshold:]
        return len(set(recent)) == 1
    
    def _check_minimal_response(self, response: str, cycle_number: int) -> bool:
        """Check if response is suspiciously short.
        
        Only triggers after first cycle to allow short initial responses.
        """
        if cycle_number == 0:
            return False
        
        return len(response.strip()) < self.min_response_length
    
    def check(
        self, 
        reasoning: Optional[str], 
        response: str, 
        cycle_number: int = 0
    ) -> Optional[LoopDetected]:
        """Check for loop conditions.
        
        Args:
            reasoning: AI reasoning text (from assistant.reasoning event)
            response: AI response text
            cycle_number: Current cycle number (0-indexed)
            
        Returns:
            LoopDetected exception if loop detected, None otherwise
        """
        self.last_reasoning = reasoning
        
        # Track response
        response_hash = self._hash_response(response)
        self.response_hashes.append(response_hash)
        self.response_lengths.append(len(response.strip()))
        
        # Check 1: Reasoning pattern
        if reasoning:
            if pattern := self._check_reasoning_pattern(reasoning):
                logger.debug(f"Loop detected via reasoning pattern: {pattern}")
                return LoopDetected(
                    reason=LoopReason.REASONING_PATTERN,
                    details=f"AI reasoning indicates loop awareness (pattern: {pattern})",
                    cycle_number=cycle_number + 1
                )
        
        # Check 2: Identical responses
        if self._check_identical_responses():
            logger.debug(f"Loop detected: {self.identical_threshold} identical responses")
            return LoopDetected(
                reason=LoopReason.IDENTICAL_RESPONSES,
                details=f"Last {self.identical_threshold} responses were identical",
                cycle_number=cycle_number + 1
            )
        
        # Check 3: Minimal response (only after first cycle)
        if self._check_minimal_response(response, cycle_number):
            logger.debug(f"Loop detected: minimal response ({len(response)} chars)")
            return LoopDetected(
                reason=LoopReason.MINIMAL_RESPONSE,
                details=f"Response too short ({len(response.strip())} chars, min: {self.min_response_length})",
                cycle_number=cycle_number + 1
            )
        
        # Check 4: Stop file (agent-initiated stop signal)
        if stop_data := self._check_stop_file():
            reason = stop_data.get("reason", "Agent requested stop")
            logger.info(f"Loop detected via stop file: {reason}")
            return LoopDetected(
                reason=LoopReason.STOP_FILE,
                details=f"Agent created stop file: {reason}",
                cycle_number=cycle_number + 1
            )
        
        return None
    
    def reset(self) -> None:
        """Reset detector state for a new workflow."""
        self.response_hashes.clear()
        self.response_lengths.clear()
        self.last_reasoning = None
    
    def cleanup_stop_file(self) -> bool:
        """Remove the stop file if it exists.
        
        Returns True if file was removed, False otherwise.
        """
        try:
            if self.stop_file_path.exists():
                self.stop_file_path.unlink()
                logger.debug(f"Cleaned up stop file: {self.stop_file_path}")
                return True
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not remove stop file: {e}")
        return False
