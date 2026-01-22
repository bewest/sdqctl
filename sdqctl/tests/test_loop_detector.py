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
        # Response must be >= 100 chars to avoid minimal response detection (Q-002 thresholds)
        result = detector.check(
            "I'll analyze the code and provide recommendations",
            "Here's my analysis of the authentication module. The code follows best practices for security including proper hashing.",
            cycle_number=1
        )
        assert result is None

    def test_no_detection_on_empty_reasoning(self):
        """Empty reasoning doesn't trigger detection."""
        detector = LoopDetector()
        # Response must be >= 100 chars to not trigger minimal response detection (Q-002 thresholds)
        result = detector.check(None, "This is a normal response with enough content to pass the length check that is now 100 characters minimum.", cycle_number=1)
        assert result is None


class TestLoopDetectorIdenticalResponses:
    """Test identical response detection."""

    def test_detects_two_identical_responses(self):
        """Two identical responses trigger detection (Q-002: threshold=2)."""
        detector = LoopDetector()
        
        # Response must be >= 100 chars to not trigger minimal response detection
        response = "Same response every time with enough content to pass length check easily. This needs to be at least 100 characters long."
        
        # First response - no detection
        result = detector.check(None, response, cycle_number=0)
        assert result is None
        
        # Second identical response - detection (threshold=2)
        result = detector.check(None, response, cycle_number=1)
        assert result is not None
        assert result.reason == LoopReason.IDENTICAL_RESPONSES

    def test_no_detection_with_different_responses(self):
        """Different responses don't trigger detection."""
        detector = LoopDetector()
        
        # Responses must be >= 100 chars to not trigger minimal response detection (Q-002)
        responses = [
            "First unique response with enough content to pass the length check requirement. Adding extra text to reach 100 chars.",
            "Second different response with sufficient content to avoid minimal detection. Additional padding to reach threshold.",
            "Third varied response that has plenty of characters in it to be valid. More content to ensure we hit 100 chars easily.",
            "Fourth distinct response with adequate length to pass all detection checks. Extra text for the 100 char minimum requirement.",
        ]
        
        for i, response in enumerate(responses):
            result = detector.check(None, response, cycle_number=i)
            assert result is None

    def test_no_detection_with_one_then_different(self):
        """One identical then different response doesn't trigger."""
        detector = LoopDetector()
        
        # Responses must be >= 100 chars (Q-002)
        same = "Same response with enough content to pass the length check requirement. Adding more text to reach 100 characters easily."
        different = "Different response with sufficient length to avoid minimal detection. More content to ensure we hit 100 chars minimum."
        
        detector.check(None, same, cycle_number=0)
        result = detector.check(None, different, cycle_number=1)
        
        assert result is None

    def test_custom_identical_threshold(self):
        """Custom threshold for identical detection."""
        detector = LoopDetector(identical_threshold=3)  # Override to 3
        
        # Response >= 100 chars (Q-002)
        response = "Same response here with sufficient length to avoid minimal response detection. Extra padding to reach 100 character minimum."
        
        detector.check(None, response, cycle_number=0)
        result = detector.check(None, response, cycle_number=1)
        assert result is None  # Still below threshold of 3
        
        result = detector.check(None, response, cycle_number=2)
        assert result is not None
        assert result.reason == LoopReason.IDENTICAL_RESPONSES


class TestLoopDetectorMinimalResponse:
    """Test minimal response detection."""

    def test_detects_minimal_response_after_first_cycle(self):
        """Very short response after first cycle triggers detection."""
        detector = LoopDetector()
        
        # First cycle - use different response to avoid identical detection
        result = detector.check(None, "First response that is unique and long enough to pass the 100 char check on first cycle.", cycle_number=0)
        assert result is None
        
        # Second cycle - short response triggers minimal detection (Q-002: min=100)
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
        
        # First cycle - unique response >= 100 chars
        detector.check(None, "Normal response with enough content to pass the length check. Adding more text to reach 100 characters minimum.", cycle_number=0)
        
        # Second cycle with adequate length (>= 100 chars, Q-002)
        long_response = "This is a response with more than 100 characters of content. Adding extra text to ensure we pass the minimum threshold."
        result = detector.check(None, long_response, cycle_number=1)
        assert result is None

    def test_custom_min_response_length(self):
        """Custom minimum response length threshold."""
        detector = LoopDetector(min_response_length=200)  # Higher than default
        
        # First cycle - unique response
        detector.check(None, "Normal first response with enough content to be unique and avoid identical detection on subsequent cycles.", cycle_number=0)
        # Second cycle - 100 chars is now too short with min=200
        result = detector.check(None, "Short response that is under 200 characters but over the default 100 character minimum threshold.", cycle_number=1)
        
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
        
        # Use responses long enough to not trigger minimal detection (Q-002: min=100)
        response = "Same response with enough content to pass the length check requirement. Adding extra text to reach 100 characters minimum."
        
        # Build up state - with threshold=2, this would trigger on second
        detector.check(None, response, cycle_number=0)
        
        # Reset before second identical (which would trigger)
        detector.reset()
        
        # After reset, first response doesn't trigger
        result = detector.check(None, response, cycle_number=0)
        assert result is None
        
        # Second identical after reset triggers (threshold=2)
        result = detector.check(None, response, cycle_number=1)
        assert result is not None
        assert result.reason == LoopReason.IDENTICAL_RESPONSES


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


class TestLoopDetectorStopFile:
    """Test stop file detection (Q-002)."""

    def test_stop_file_name_with_session_id(self):
        """Stop file name includes session hash."""
        detector = LoopDetector(session_id="test-session-123")
        assert "STOPAUTOMATION-" in detector.stop_file_name
        assert ".json" in detector.stop_file_name
        # Hash should be deterministic
        detector2 = LoopDetector(session_id="test-session-123")
        assert detector.stop_file_name == detector2.stop_file_name

    def test_stop_file_name_without_session_id(self):
        """Stop file name without session ID is generic."""
        detector = LoopDetector()
        assert detector.stop_file_name == "STOPAUTOMATION.json"

    def test_stop_file_detection(self, tmp_path):
        """Detects stop file when present."""
        detector = LoopDetector(session_id="test", stop_file_dir=tmp_path)
        
        # No stop file - no detection
        response = "Normal response with sufficient length to pass all other detection thresholds. Extra padding for 100 chars."
        result = detector.check(None, response, cycle_number=0)
        assert result is None
        
        # Create stop file
        stop_file = tmp_path / detector.stop_file_name
        stop_file.write_text('{"reason": "User requested stop"}')
        
        # Now detection triggers
        result = detector.check(None, "Another unique response with sufficient length to pass all detection thresholds including 100 char min.", cycle_number=1)
        assert result is not None
        assert result.reason == LoopReason.STOP_FILE
        assert "User requested stop" in result.details

    def test_cleanup_stop_file(self, tmp_path):
        """Cleanup removes stop file."""
        detector = LoopDetector(session_id="test", stop_file_dir=tmp_path)
        
        # Create stop file
        stop_file = tmp_path / detector.stop_file_name
        stop_file.write_text('{}')
        assert stop_file.exists()
        
        # Cleanup
        result = detector.cleanup_stop_file()
        assert result is True
        assert not stop_file.exists()
        
        # Cleanup when no file
        result = detector.cleanup_stop_file()
        assert result is False
