"""
Tests for loop detection in AI workflow cycles.
"""

import pytest
from sdqctl.core.loop_detector import (
    LoopDetector, 
    LOOP_REASONING_PATTERNS,
    generate_nonce,
    get_stop_file_name,
)
from sdqctl.core.exceptions import LoopDetected, LoopReason


class TestGenerateNonce:
    """Test nonce generation utilities."""

    def test_generate_nonce_default_length(self):
        """Generate nonce with default 12 char length."""
        nonce = generate_nonce()
        assert len(nonce) == 12
        assert nonce.isalnum()  # hex chars are alphanumeric

    def test_generate_nonce_custom_length(self):
        """Generate nonce with custom length."""
        nonce = generate_nonce(length=6)
        assert len(nonce) == 6

    def test_generate_nonce_uniqueness(self):
        """Each nonce should be unique."""
        nonces = [generate_nonce() for _ in range(100)]
        assert len(set(nonces)) == 100

    def test_get_stop_file_name_with_nonce(self):
        """Stop file name with explicit nonce."""
        name = get_stop_file_name("abc123")
        assert name == "STOPAUTOMATION-abc123.json"

    def test_get_stop_file_name_without_nonce(self):
        """Stop file name generates random nonce."""
        name = get_stop_file_name()
        assert name.startswith("STOPAUTOMATION-")
        assert name.endswith(".json")


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
        # Response must be >= 100 chars to avoid minimal response detection (Q-002)
        long_response = (
            "Here's my analysis of the authentication module. "
            "The code follows best practices for security including proper hashing."
        )
        result = detector.check(
            "I'll analyze the code and provide recommendations",
            long_response,
            cycle_number=1
        )
        assert result is None

    def test_no_detection_on_empty_reasoning(self):
        """Empty reasoning doesn't trigger detection."""
        detector = LoopDetector()
        # Response must be >= 100 chars to not trigger minimal response detection
        long_response = (
            "This is a normal response with enough content to pass the length "
            "check that is now 100 characters minimum."
        )
        result = detector.check(None, long_response, cycle_number=1)
        assert result is None


class TestLoopDetectorIdenticalResponses:
    """Test identical response detection."""

    def test_detects_two_identical_responses(self):
        """Two identical responses trigger detection (Q-002: threshold=2)."""
        detector = LoopDetector()
        
        # Response must be >= 100 chars to not trigger minimal response detection
        response = (
            "Same response every time with enough content to pass length check. "
            "This needs to be at least 100 characters long."
        )
        
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
        
        # Responses must be >= 100 chars to not trigger minimal response detection
        responses = [
            (
                "First unique response with enough content to pass the length "
                "check requirement. Adding extra text to reach 100 chars."
            ),
            (
                "Second different response with sufficient content to avoid "
                "minimal detection. Additional padding to reach threshold."
            ),
            (
                "Third varied response that has plenty of characters in it to "
                "be valid. More content to ensure we hit 100 chars easily."
            ),
            (
                "Fourth distinct response with adequate length to pass all "
                "detection checks. Extra text for the 100 char minimum."
            ),
        ]
        
        for i, response in enumerate(responses):
            result = detector.check(None, response, cycle_number=i)
            assert result is None

    def test_no_detection_with_one_then_different(self):
        """One identical then different response doesn't trigger."""
        detector = LoopDetector()
        
        # Responses must be >= 100 chars (Q-002)
        same = (
            "Same response with enough content to pass the length check. "
            "Adding more text to reach 100 characters easily."
        )
        different = (
            "Different response with sufficient length to avoid minimal. "
            "More content to ensure we hit 100 chars minimum."
        )
        
        detector.check(None, same, cycle_number=0)
        result = detector.check(None, different, cycle_number=1)
        
        assert result is None

    def test_custom_identical_threshold(self):
        """Custom threshold for identical detection."""
        detector = LoopDetector(identical_threshold=3)  # Override to 3
        
        # Response >= 100 chars (Q-002)
        response = (
            "Same response here with sufficient length to avoid minimal. "
            "Extra padding to reach 100 character minimum."
        )
        
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
        first = (
            "First response that is unique and long enough to pass the "
            "100 char check on first cycle."
        )
        result = detector.check(None, first, cycle_number=0)
        assert result is None
        
        # Second cycle - short response triggers minimal detection
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
        first = (
            "Normal response with enough content to pass the length check. "
            "Adding more text to reach 100 characters minimum."
        )
        detector.check(None, first, cycle_number=0)
        
        # Second cycle with adequate length (>= 100 chars, Q-002)
        long_response = (
            "This is a response with more than 100 characters of content. "
            "Adding extra text to ensure we pass the minimum threshold."
        )
        result = detector.check(None, long_response, cycle_number=1)
        assert result is None

    def test_custom_min_response_length(self):
        """Custom minimum response length threshold."""
        detector = LoopDetector(min_response_length=200)  # Higher than default
        
        # First cycle - unique response
        first = (
            "Normal first response with enough content to be unique and "
            "avoid identical detection on subsequent cycles."
        )
        detector.check(None, first, cycle_number=0)
        # Second cycle - 100 chars is now too short with min=200
        short = (
            "Short response that is under 200 characters but over the "
            "default 100 character minimum threshold."
        )
        result = detector.check(None, short, cycle_number=1)
        
        assert result is not None
        assert result.reason == LoopReason.MINIMAL_RESPONSE

    def test_no_detection_when_tools_called(self):
        """Short response with tool calls doesn't trigger detection.
        
        When the agent called tools, a short acknowledgment is normal.
        This prevents false positives on Phase 6 commit confirmations.
        """
        detector = LoopDetector()
        
        # First cycle - unique long response
        detector.check(
            None,
            "First response that is unique and long enough to pass the 100 char check.",
            cycle_number=0
        )
        
        # Second cycle - short response BUT tools were called
        result = detector.check(
            None, "Done.", cycle_number=1, tools_called=3
        )
        assert result is None  # No detection because tools_called > 0

    def test_detection_when_no_tools_short_response(self):
        """Short response without tool calls still triggers detection."""
        detector = LoopDetector()
        
        # First cycle
        detector.check(
            None,
            "First response that is unique and long enough to pass length check on first.",
            cycle_number=0
        )
        
        # Second cycle - short response, no tools
        result = detector.check(
            None, "OK", cycle_number=1, tools_called=0
        )
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
        response = (
            "Same response with enough content to pass the length check. "
            "Adding extra text to reach 100 characters minimum."
        )
        
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
        
        # (text, pattern, should_match)
        prompt_pattern = r"\bsame (?:workflow )?prompt (?:being )?repeated\b"
        confirmed_pattern = (
            r"\balready (?:confirmed|answered|responded).*"
            r"(?:multiple|several) times\b"
        )
        minimal_pattern = r"\bkeep(?:ing)? (?:my )?response minimal\b"
        
        test_cases = [
            ("in a loop", r"\bin a loop\b", True),
            ("inalooptest", r"\bin a loop\b", False),  # word boundaries
            ("same prompt being repeated", prompt_pattern, True),
            ("same workflow prompt repeated", prompt_pattern, True),
            ("already confirmed multiple times", confirmed_pattern, True),
            ("keep my response minimal", minimal_pattern, True),
            ("keeping response minimal", minimal_pattern, True),
        ]
        
        for text, pattern, should_match in test_cases:
            match = re.search(pattern, text.lower())
            assert bool(match) == should_match, f"Pattern {pattern} vs '{text}'"


class TestLoopDetectorStopFile:
    """Test stop file detection (Q-002)."""

    def test_stop_file_name_with_nonce(self):
        """Stop file name includes nonce."""
        detector = LoopDetector(nonce="abc123def456")
        assert detector.stop_file_name == "STOPAUTOMATION-abc123def456.json"
        # Same nonce gives same name
        detector2 = LoopDetector(nonce="abc123def456")
        assert detector.stop_file_name == detector2.stop_file_name

    def test_stop_file_name_without_nonce(self):
        """Stop file name generates random nonce if none provided."""
        detector = LoopDetector()
        assert detector.stop_file_name.startswith("STOPAUTOMATION-")
        assert detector.stop_file_name.endswith(".json")
        # Should have a 12-char nonce
        nonce_part = detector.stop_file_name.replace("STOPAUTOMATION-", "").replace(".json", "")
        assert len(nonce_part) == 12

    def test_stop_file_detection(self, tmp_path):
        """Detects stop file when present."""
        detector = LoopDetector(nonce="testnonc1234", stop_file_dir=tmp_path)
        
        # No stop file - no detection
        response = (
            "Normal response with sufficient length to pass all other "
            "detection thresholds. Extra padding for 100 chars."
        )
        result = detector.check(None, response, cycle_number=0)
        assert result is None
        
        # Create stop file
        stop_file = tmp_path / detector.stop_file_name
        stop_file.write_text('{"reason": "User requested stop"}')
        
        # Now detection triggers
        response2 = (
            "Another unique response with sufficient length to pass all "
            "detection thresholds including 100 char min."
        )
        result = detector.check(None, response2, cycle_number=1)
        assert result is not None
        assert result.reason == LoopReason.STOP_FILE
        assert "User requested stop" in result.details

    def test_cleanup_stop_file(self, tmp_path):
        """Cleanup removes stop file."""
        detector = LoopDetector(nonce="testnonc1234", stop_file_dir=tmp_path)
        
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


class TestStopFileInstruction:
    """Test stop file instruction template (Q-002)."""

    def test_get_stop_file_instruction(self):
        """get_stop_file_instruction substitutes filename correctly."""
        from sdqctl.core.loop_detector import get_stop_file_instruction, STOP_FILE_INSTRUCTION
        
        result = get_stop_file_instruction("STOPAUTOMATION-abc123.json")
        
        assert "STOPAUTOMATION-abc123.json" in result
        assert "${STOP_FILE}" not in result
        assert "Automation Control" in result
        assert "needs_review" in result

    def test_stop_file_instruction_template_has_variable(self):
        """STOP_FILE_INSTRUCTION template contains ${STOP_FILE} placeholder."""
        from sdqctl.core.loop_detector import STOP_FILE_INSTRUCTION
        
        assert "${STOP_FILE}" in STOP_FILE_INSTRUCTION
