"""Tests for verify_steps module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sdqctl.commands.verify_steps import (
    execute_verify_step,
    execute_verify_trace_step,
    execute_verify_coverage_step,
)


class TestExecuteVerifyStep:
    """Tests for execute_verify_step function."""

    def test_verify_step_calls_verifier(self, tmp_path):
        """Test that verify step invokes the verifier registry."""
        # Create mock step
        step = MagicMock()
        step.verify_type = "refs"
        step.verify_options = {}
        step.get = MagicMock(return_value="refs")

        # Create mock conv
        conv = MagicMock()
        conv.source_path = tmp_path / "test.conv"
        conv.verify_output = "never"
        conv.verify_limit = None
        conv.verify_on_error = "continue"

        # Create mock session
        session = MagicMock()

        # Mock progress
        progress = MagicMock()

        # Mock the verifier
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.errors = []
        mock_result.summary = "All refs valid"

        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = mock_result

        with patch("sdqctl.verifiers.VERIFIERS", {"refs": lambda: mock_verifier}):
            execute_verify_step(step, conv, session, progress)

        mock_verifier.verify.assert_called_once()
        progress.assert_called()

    def test_verify_step_raises_on_fail(self, tmp_path):
        """Test that verify step raises RuntimeError when verify_on_error is fail."""
        step = MagicMock()
        step.verify_type = "refs"
        step.verify_options = {}
        step.get = MagicMock(return_value="refs")

        conv = MagicMock()
        conv.source_path = tmp_path / "test.conv"
        conv.verify_output = "never"
        conv.verify_limit = None
        conv.verify_on_error = "fail"

        session = MagicMock()
        progress = MagicMock()

        mock_result = MagicMock()
        mock_result.passed = False
        mock_result.errors = [MagicMock(file="test.py", line=1, message="Error")]
        mock_result.summary = "1 error"

        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = mock_result

        with patch("sdqctl.verifiers.VERIFIERS", {"refs": lambda: mock_verifier}):
            with pytest.raises(RuntimeError, match="Verification failed"):
                execute_verify_step(step, conv, session, progress)


class TestExecuteVerifyTraceStep:
    """Tests for execute_verify_trace_step function."""

    def test_verify_trace_step_calls_verifier(self, tmp_path):
        """Test that verify_trace step invokes TraceabilityVerifier."""
        step = MagicMock()
        step.verify_options = {"from": "REQ-001", "to": "TEST-001"}
        step.get = MagicMock(return_value={"from": "REQ-001", "to": "TEST-001"})

        conv = MagicMock()
        conv.source_path = tmp_path / "test.conv"
        conv.verify_on_error = "continue"

        progress = MagicMock()

        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.summary = "Trace verified"

        with patch(
            "sdqctl.verifiers.traceability.TraceabilityVerifier"
        ) as MockVerifier:
            mock_instance = MockVerifier.return_value
            mock_instance.verify_trace.return_value = mock_result

            execute_verify_trace_step(step, conv, progress)

            mock_instance.verify_trace.assert_called_once_with(
                "REQ-001", "TEST-001", tmp_path
            )


class TestExecuteVerifyCoverageStep:
    """Tests for execute_verify_coverage_step function."""

    def test_verify_coverage_report_only(self, tmp_path):
        """Test verify_coverage in report-only mode."""
        step = MagicMock()
        step.verify_options = {"report_only": True}
        step.get = MagicMock(return_value={"report_only": True})

        conv = MagicMock()
        conv.source_path = tmp_path / "test.conv"
        conv.verify_on_error = "continue"

        progress = MagicMock()

        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.summary = "Coverage: 85%"

        with patch(
            "sdqctl.verifiers.traceability.TraceabilityVerifier"
        ) as MockVerifier:
            mock_instance = MockVerifier.return_value
            mock_instance.verify_coverage.return_value = mock_result

            execute_verify_coverage_step(step, conv, progress)

            mock_instance.verify_coverage.assert_called_once_with(tmp_path)

    def test_verify_coverage_with_threshold(self, tmp_path):
        """Test verify_coverage with threshold check."""
        step = MagicMock()
        step.verify_options = {
            "report_only": False,
            "metric": "requirements",
            "op": ">=",
            "threshold": 80,
        }
        step.get = MagicMock(return_value=step.verify_options)

        conv = MagicMock()
        conv.source_path = tmp_path / "test.conv"
        conv.verify_on_error = "continue"

        progress = MagicMock()

        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.summary = "Coverage: 85%"

        with patch(
            "sdqctl.verifiers.traceability.TraceabilityVerifier"
        ) as MockVerifier:
            mock_instance = MockVerifier.return_value
            mock_instance.verify_coverage.return_value = mock_result

            execute_verify_coverage_step(step, conv, progress)

            mock_instance.verify_coverage.assert_called_once_with(
                tmp_path, metric="requirements", op=">=", threshold=80
            )
