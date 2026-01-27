"""Tests for sdqctl custom exceptions and JSON serialization."""

import json

import pytest

from sdqctl.core.exceptions import (
    AgentAborted,
    ExitCode,
    LoopDetected,
    LoopReason,
    MissingContextFiles,
    RunCommandFailed,
    exception_to_json,
    format_json_error,
)

pytestmark = pytest.mark.unit


class TestExitCodes:
    """Test exit code constants."""

    def test_exit_codes_are_distinct(self):
        """All exit codes should be unique."""
        codes = [
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.MISSING_FILES,
            ExitCode.LOOP_DETECTED,
            ExitCode.AGENT_ABORTED,
            ExitCode.RUN_FAILED,
            ExitCode.VALIDATION_FAILED,
            ExitCode.VERIFY_FAILED,
        ]
        assert len(codes) == len(set(codes))

    def test_success_is_zero(self):
        """SUCCESS should be 0 per Unix convention."""
        assert ExitCode.SUCCESS == 0

    def test_errors_are_nonzero(self):
        """All error codes should be non-zero."""
        assert ExitCode.GENERAL_ERROR != 0
        assert ExitCode.MISSING_FILES != 0
        assert ExitCode.LOOP_DETECTED != 0
        assert ExitCode.AGENT_ABORTED != 0
        assert ExitCode.RUN_FAILED != 0


class TestLoopDetected:
    """Test LoopDetected exception."""

    def test_basic_creation(self):
        """Create LoopDetected with required fields."""
        exc = LoopDetected(
            reason=LoopReason.IDENTICAL_RESPONSES,
            details="3 identical responses detected"
        )
        assert exc.reason == LoopReason.IDENTICAL_RESPONSES
        assert "3 identical" in exc.details

    def test_str_representation(self):
        """String representation includes details."""
        exc = LoopDetected(
            reason=LoopReason.REASONING_PATTERN,
            details="AI mentioned being stuck"
        )
        assert "Loop detected" in str(exc)
        assert "stuck" in str(exc)

    def test_str_with_cycle_number(self):
        """String includes cycle number when provided."""
        exc = LoopDetected(
            reason=LoopReason.MINIMAL_RESPONSE,
            details="Response too short",
            cycle_number=5
        )
        assert "cycle 5" in str(exc)

    def test_exit_code(self):
        """Exit code matches LOOP_DETECTED constant."""
        exc = LoopDetected(
            reason=LoopReason.STOP_FILE,
            details="Stop file created"
        )
        assert exc.exit_code == ExitCode.LOOP_DETECTED

    def test_all_loop_reasons(self):
        """All LoopReason values create valid exceptions."""
        for reason in LoopReason:
            exc = LoopDetected(reason=reason, details="test")
            assert exc.reason == reason


class TestMissingContextFiles:
    """Test MissingContextFiles exception."""

    def test_single_file(self):
        """Single missing file message."""
        exc = MissingContextFiles(files=["config.yaml"])
        assert "config.yaml" in str(exc)
        assert "Missing mandatory context file" in str(exc)

    def test_multiple_files(self):
        """Multiple missing files message."""
        exc = MissingContextFiles(files=["a.txt", "b.txt", "c.txt"])
        assert "Missing 3 mandatory context files" in str(exc)

    def test_exit_code(self):
        """Exit code matches MISSING_FILES constant."""
        exc = MissingContextFiles(files=["test.py"])
        assert exc.exit_code == ExitCode.MISSING_FILES

    def test_with_resolved_paths(self):
        """Resolved paths stored correctly."""
        exc = MissingContextFiles(
            files=["*.py"],
            resolved_paths={"*.py": "/path/to/file.py"}
        )
        assert exc.resolved_paths == {"*.py": "/path/to/file.py"}


class TestAgentAborted:
    """Test AgentAborted exception."""

    def test_basic_creation(self):
        """Create with default values."""
        exc = AgentAborted()
        assert exc.reason == "unknown"
        assert exc.details is None

    def test_with_reason_and_details(self):
        """Create with specific reason and details."""
        exc = AgentAborted(
            reason="repeated_request",
            details="Same question asked 3 times"
        )
        assert "repeated_request" in str(exc)
        assert "Same question" in str(exc)

    def test_with_turn_number(self):
        """Turn number included in string."""
        exc = AgentAborted(
            reason="circular_workflow",
            turn_number=10
        )
        assert "turn 10" in str(exc)

    def test_exit_code(self):
        """Exit code matches AGENT_ABORTED constant."""
        exc = AgentAborted()
        assert exc.exit_code == ExitCode.AGENT_ABORTED


class TestRunCommandFailed:
    """Test RunCommandFailed exception."""

    def test_basic_creation(self):
        """Create with command and exit code."""
        exc = RunCommandFailed(command="npm test", exit_code_val=1)
        assert "npm test" in str(exc)
        assert "exit code 1" in str(exc)

    def test_timeout(self):
        """Timeout message differs from exit code."""
        exc = RunCommandFailed(
            command="sleep 100",
            exit_code_val=-1,
            timeout=True
        )
        assert "timed out" in str(exc)
        assert "exit code" not in str(exc)

    def test_with_stderr(self):
        """Stderr stored correctly."""
        exc = RunCommandFailed(
            command="bad-command",
            exit_code_val=127,
            stderr="command not found"
        )
        assert exc.stderr == "command not found"

    def test_exit_code(self):
        """Exit code matches RUN_FAILED constant."""
        exc = RunCommandFailed(command="test", exit_code_val=1)
        assert exc.exit_code == ExitCode.RUN_FAILED


class TestExceptionToJson:
    """Test exception_to_json function."""

    def test_loop_detected_json(self):
        """LoopDetected serializes correctly."""
        exc = LoopDetected(
            reason=LoopReason.IDENTICAL_RESPONSES,
            details="3 identical",
            cycle_number=5
        )
        result = exception_to_json(exc)

        assert result["error"]["type"] == "LoopDetected"
        assert result["error"]["exit_code"] == ExitCode.LOOP_DETECTED
        assert result["error"]["reason"] == "identical_responses"
        assert result["error"]["cycle_number"] == 5

    def test_missing_context_files_json(self):
        """MissingContextFiles serializes correctly."""
        exc = MissingContextFiles(
            files=["a.txt", "b.txt"],
            resolved_paths={"a.txt": "/full/a.txt"}
        )
        result = exception_to_json(exc)

        assert result["error"]["type"] == "MissingContextFiles"
        assert result["error"]["files"] == ["a.txt", "b.txt"]
        assert "resolved_paths" in result["error"]

    def test_agent_aborted_json(self):
        """AgentAborted serializes correctly."""
        exc = AgentAborted(
            reason="test_reason",
            details="test_details",
            turn_number=7
        )
        result = exception_to_json(exc)

        assert result["error"]["type"] == "AgentAborted"
        assert result["error"]["reason"] == "test_reason"
        assert result["error"]["turn_number"] == 7

    def test_run_command_failed_json(self):
        """RunCommandFailed serializes correctly."""
        exc = RunCommandFailed(
            command="npm test",
            exit_code_val=1,
            stderr="test failed",
            stdout="output",
            timeout=False
        )
        result = exception_to_json(exc)

        assert result["error"]["type"] == "RunCommandFailed"
        assert result["error"]["command"] == "npm test"
        assert result["error"]["command_exit_code"] == 1
        assert result["error"]["stderr"] == "test failed"
        assert result["error"]["timeout"] is False

    def test_generic_exception_json(self):
        """Generic exception gets GENERAL_ERROR exit code."""
        exc = ValueError("something wrong")
        result = exception_to_json(exc)

        assert result["error"]["type"] == "ValueError"
        assert result["error"]["exit_code"] == ExitCode.GENERAL_ERROR
        assert "something wrong" in result["error"]["message"]

    def test_with_context(self):
        """Context dict included in output."""
        exc = LoopDetected(
            reason=LoopReason.STOP_FILE,
            details="test"
        )
        result = exception_to_json(exc, context={"workflow": "test.conv"})

        assert result["error"]["context"]["workflow"] == "test.conv"

    def test_stderr_truncation(self):
        """Long stderr/stdout truncated to 2000 chars."""
        long_output = "x" * 5000
        exc = RunCommandFailed(
            command="test",
            exit_code_val=1,
            stderr=long_output
        )
        result = exception_to_json(exc)

        assert len(result["error"]["stderr"]) == 2000


class TestFormatJsonError:
    """Test format_json_error function."""

    def test_returns_valid_json(self):
        """Output is valid JSON string."""
        exc = LoopDetected(
            reason=LoopReason.REASONING_PATTERN,
            details="test"
        )
        result = format_json_error(exc)

        # Should parse without error
        parsed = json.loads(result)
        assert "error" in parsed

    def test_is_formatted(self):
        """Output is indented for readability."""
        exc = AgentAborted(reason="test")
        result = format_json_error(exc)

        # Indented JSON has newlines
        assert "\n" in result

    def test_with_context(self):
        """Context included in formatted output."""
        exc = MissingContextFiles(files=["test.py"])
        result = format_json_error(exc, context={"cycle": 3})

        parsed = json.loads(result)
        assert parsed["error"]["context"]["cycle"] == 3
