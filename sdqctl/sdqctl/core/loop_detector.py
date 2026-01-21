"""
Loop detection for AI workflow cycles.

Detects when the AI has entered a repetitive state and the workflow
should be aborted to avoid wasting tokens.
"""

import hashlib
import logging
import re
from collections import deque
from dataclasses import dataclass, field
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
MIN_RESPONSE_LENGTH = 50

# Number of identical responses to trigger detection
IDENTICAL_RESPONSE_THRESHOLD = 3


@dataclass
class LoopDetector:
    """Detects repetitive loops in AI workflow execution.
    
    Monitors three signals:
    1. Reasoning patterns - AI explicitly mentions being in a loop
    2. Identical responses - Same response N times in a row
    3. Minimal responses - Very short responses after first cycle
    
    Usage:
        detector = LoopDetector()
        for cycle in range(max_cycles):
            response = await ai.send(prompt)
            reasoning = get_reasoning()  # From adapter
            if result := detector.check(reasoning, response, cycle):
                raise result
    """
    
    # Configuration
    identical_threshold: int = IDENTICAL_RESPONSE_THRESHOLD
    min_response_length: int = MIN_RESPONSE_LENGTH
    
    # State
    response_hashes: deque = field(default_factory=lambda: deque(maxlen=5))
    response_lengths: list[int] = field(default_factory=list)
    last_reasoning: Optional[str] = None
    
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
        
        return None
    
    def reset(self) -> None:
        """Reset detector state for a new workflow."""
        self.response_hashes.clear()
        self.response_lengths.clear()
        self.last_reasoning = None
