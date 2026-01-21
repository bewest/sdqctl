"""
Tests for loop detection in AI workflow cycles.
"""

import pytest
from sdqctl.core.loop_detector import LoopDetector, LOOP_REASONING_PATTERNS
from sdqctl.core.exceptions import LoopDetected, LoopReason


class TestLoopDetectorReasoningPatterns:
    """Test reasoning pattern detection."""

    def test_detects_loop_in_reasoning(self):
        """Reasoning mentioning 'in a loop' triggers detection."""
        detector = LoopDetector()
        result = detector.check(
            "The user is clearly in a loop with the same prompt",
            "Some response",
            cycle_number=1
        )
        assert result is not None
        assert result.reason == LoopReason.REASONING_PATTERN

    def test_detects_repeated_prompt(self):
        """Reasoning about repeated prompts triggers detection."""
        detector = LoopDetector()
        result = detector.check(
            "The same workflow prompt being repeated",
            "Some response",
            cycle_number=2
        )
        assert result is not None
        assert result.reason == LoopReason.REASONING_PATTERN

    def test_detects_already_confirmed_multiple_times(self):
        """Reasoning about already confirming multiple times triggers detection."""
        detector = LoopDetector()
        result = detector.check(
            "I've already confirmed multiple times that the report is current",
            "Confirmed.",
            cycle_number=3
        )
        assert result is not None
        assert result.reason == LoopReason.REASONING_PATTERN

    def test_detects_keeping_response_minimal(self):
        """Reasoning about keeping response minimal triggers detection."""
        detector = LoopDetector()
        result = detector.check(
            "I should keep my response minimal",
            "OK.",
            cycle_number=2
        )
        assert result is not None
        assert result.reason == LoopReason.REASONING_PATTERN

    def test_no_detection_on_normal_reasoning(self):
        """Normal reasoning doesn't trigger detection."""
        detector = LoopDetector()
        result = detector.check(
            "I'll analyze the code and provide recommendations",
            "Here's my analysis of the authentication module...",
            cycle_number=1
        )
        assert result is None

    def test_no_detection_on_empty_reasoning(self):
        """Empty reasoning doesn't trigger detection."""
        detector = LoopDetector()
        # Use response long enough to not trigger minimal response detection
        result = detector.check(None, "This is a normal response with enough content to pass the length check", cycle_number=1)
        assert result is None


class TestLoopDetectorIdenticalResponses:
    """Test identical response detection."""

    def test_detects_three_identical_responses(self):
        """Three identical responses trigger detection."""
        detector = LoopDetector()
        
        # Use response long enough to not trigger minimal response detection
        response = "Same response every time with enough content to pass length check easily"
        
        # First two responses - no detection
        for i in range(2):
            result = detector.check(None, response, cycle_number=i)
            assert result is None
        
        # Third identical response - detection
        result = detector.check(None, response, cycle_number=2)
        assert result is not None
        assert result.reason == LoopReason.IDENTICAL_RESPONSES

    def test_no_detection_with_different_responses(self):
        """Different responses don't trigger detection."""
        detector = LoopDetector()
        
        # Responses long enough to not trigger minimal response detection
        responses = [
            "First unique response with enough content to pass the length check requirement",
            "Second different response with sufficient content to avoid minimal detection",
            "Third varied response that has plenty of characters in it to be valid",
            "Fourth distinct response with adequate length to pass all detection checks",
        ]
        
        for i, response in enumerate(responses):
            result = detector.check(None, response, cycle_number=i)
            assert result is None

    def test_no_detection_with_two_identical_then_different(self):
        """Two identical then different response doesn't trigger."""
        detector = LoopDetector()
        
        # Responses long enough to not trigger minimal response detection
        same = "Same response with enough content to pass the length check requirement"
        different = "Different response with sufficient length to avoid minimal detection"
        
        detector.check(None, same, cycle_number=0)
        detector.check(None, same, cycle_number=1)
        result = detector.check(None, different, cycle_number=2)
        
        assert result is None

    def test_custom_identical_threshold(self):
        """Custom threshold for identical detection."""
        detector = LoopDetector(identical_threshold=2)
        
        detector.check(None, "Same", cycle_number=0)
        result = detector.check(None, "Same", cycle_number=1)
        
        assert result is not None
        assert result.reason == LoopReason.IDENTICAL_RESPONSES


class TestLoopDetectorMinimalResponse:
    """Test minimal response detection."""

    def test_detects_minimal_response_after_first_cycle(self):
        """Very short response after first cycle triggers detection."""
        detector = LoopDetector()
        
        # First cycle - normal response, no detection even if short
        result = detector.check(None, "OK", cycle_number=0)
        assert result is None
        
        # Second cycle - short response triggers detection
        result = detector.check(None, "OK", cycle_number=1)
        assert result is not None
        assert result.reason == LoopReason.MINIMAL_RESPONSE

    def test_no_detection_on_first_cycle(self):
        """Short response on first cycle doesn't trigger detection."""
        detector = LoopDetector()
        result = detector.check(None, "OK", cycle_number=0)
        assert result is None

    def test_no_detection_on_normal_length_response(self):
        """Response above threshold doesn't trigger detection."""
        detector = LoopDetector()
        
        # First cycle
        detector.check(None, "Normal response with enough content", cycle_number=0)
        
        # Second cycle with adequate length
        long_response = "This is a response with more than 50 characters of content."
        result = detector.check(None, long_response, cycle_number=1)
        assert result is None

    def test_custom_min_response_length(self):
        """Custom minimum response length threshold."""
        detector = LoopDetector(min_response_length=100)
        
        detector.check(None, "Normal response", cycle_number=0)
        result = detector.check(None, "Short", cycle_number=1)
        
        assert result is not None
        assert result.reason == LoopReason.MINIMAL_RESPONSE


class TestLoopDetectorCycleInfo:
    """Test cycle number reporting."""

    def test_cycle_number_in_exception(self):
        """Loop detection includes cycle number in exception."""
        detector = LoopDetector()
        result = detector.check(
            "The user is in a loop",
            "Response",
            cycle_number=4
        )
        assert result is not None
        assert result.cycle_number == 5  # 1-indexed in output

    def test_reset_clears_state(self):
        """Reset clears all detection state."""
        detector = LoopDetector()
        
        # Use responses long enough to not trigger minimal detection
        response = "Same response with enough content to pass the length check requirement"
        
        # Build up state
        detector.check(None, response, cycle_number=0)
        detector.check(None, response, cycle_number=1)
        
        # Reset
        detector.reset()
        
        # After reset, need 3 more identical to trigger
        result = detector.check(None, response, cycle_number=0)
        assert result is None
        result = detector.check(None, response, cycle_number=1)
        assert result is None


class TestLoopReasoningPatterns:
    """Test the regex patterns themselves."""

    def test_all_patterns_compile(self):
        """All loop reasoning patterns are valid regex."""
        import re
        for pattern in LOOP_REASONING_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_pattern_examples(self):
        """Test specific pattern matching examples."""
        import re
        
        test_cases = [
            ("in a loop", r"\bin a loop\b", True),
            ("inalooptest", r"\bin a loop\b", False),  # word boundaries
            ("same prompt being repeated", r"\bsame (?:workflow )?prompt (?:being )?repeated\b", True),
            ("same workflow prompt repeated", r"\bsame (?:workflow )?prompt (?:being )?repeated\b", True),
            ("already confirmed multiple times", r"\balready (?:confirmed|answered|responded).*(?:multiple|several) times\b", True),
            ("keep my response minimal", r"\bkeep(?:ing)? (?:my )?response minimal\b", True),
            ("keeping response minimal", r"\bkeep(?:ing)? (?:my )?response minimal\b", True),
        ]
        
        for text, pattern, should_match in test_cases:
            match = re.search(pattern, text.lower())
            assert bool(match) == should_match, f"Pattern {pattern} vs '{text}'"
