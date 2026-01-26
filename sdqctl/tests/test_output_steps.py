"""Tests for output_steps module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestWriteCycleOutput:
    """Tests for write_cycle_output function."""

    def test_returns_none_when_no_output_file(self):
        """Test returns None when no output file configured."""
        from sdqctl.commands.output_steps import write_cycle_output

        mock_conv = MagicMock()
        mock_conv.output_file = None

        result = write_cycle_output(
            all_responses=[],
            conv=mock_conv,
            output_vars={},
            console=MagicMock(),
            progress=MagicMock(),
        )

        assert result is None

    def test_writes_output_file(self, tmp_path):
        """Test writes output to file."""
        from sdqctl.commands.output_steps import write_cycle_output

        output_file = tmp_path / "output.md"

        mock_conv = MagicMock()
        mock_conv.output_file = str(output_file)
        mock_conv.headers = []
        mock_conv.footers = []
        mock_conv.source_path = None

        mock_console = MagicMock()
        mock_progress = MagicMock()

        all_responses = [
            {"cycle": 1, "prompt": 1, "response": "First response"},
            {"cycle": 1, "prompt": 2, "response": "Second response"},
        ]

        result = write_cycle_output(
            all_responses=all_responses,
            conv=mock_conv,
            output_vars={},
            console=mock_console,
            progress=mock_progress,
        )

        assert result == str(output_file)
        assert output_file.exists()
        content = output_file.read_text()
        assert "First response" in content
        assert "Second response" in content


class TestDisplayCompletion:
    """Tests for display_completion function."""

    def test_non_json_output_prints_completion(self):
        """Test non-JSON output prints completion message."""
        from sdqctl.commands.output_steps import display_completion

        mock_conv = MagicMock()
        mock_conv.max_cycles = 2
        mock_conv.output_file = None

        mock_session = MagicMock()
        mock_session.state.messages = ["msg1", "msg2"]

        mock_console = MagicMock()
        mock_progress = MagicMock()

        display_completion(
            conv=mock_conv,
            session=mock_session,
            cycle_elapsed=5.0,
            all_responses=[],
            output_vars={},
            json_output=False,
            console=mock_console,
            progress=mock_progress,
            ai_adapter=MagicMock(),
            adapter_session=MagicMock(),
        )

        # Should print completion message
        assert mock_console.print.called
        # Should call progress with elapsed time
        mock_progress.assert_called()


class TestHandleLoopError:
    """Tests for handle_loop_error function."""

    def test_saves_checkpoint_and_exits(self):
        """Test saves checkpoint and exits."""
        from sdqctl.commands.output_steps import handle_loop_error
        from sdqctl.core.exceptions import LoopDetected, LoopReason

        mock_error = LoopDetected(LoopReason.IDENTICAL_RESPONSES, "Repetitive content")

        mock_session = MagicMock()
        mock_session.save_pause_checkpoint.return_value = "/path/to/checkpoint"

        mock_console = MagicMock()

        with pytest.raises(SystemExit):
            handle_loop_error(
                error=mock_error,
                session=mock_session,
                workflow_path="test.conv",
                json_errors=False,
                console=mock_console,
            )

        assert mock_session.state.status == "failed"
        mock_session.save_pause_checkpoint.assert_called_once()


class TestHandleMissingContextError:
    """Tests for handle_missing_context_error function."""

    def test_saves_checkpoint_and_exits(self):
        """Test saves checkpoint and exits."""
        from sdqctl.commands.output_steps import handle_missing_context_error
        from sdqctl.core.exceptions import MissingContextFiles

        mock_error = MissingContextFiles(["file1.md", "file2.md"])

        mock_session = MagicMock()
        mock_session.save_pause_checkpoint.return_value = "/path/to/checkpoint"

        mock_console = MagicMock()

        with pytest.raises(SystemExit):
            handle_missing_context_error(
                error=mock_error,
                session=mock_session,
                workflow_path="test.conv",
                json_errors=False,
                console=mock_console,
            )

        assert mock_session.state.status == "failed"


class TestHandleGenericError:
    """Tests for handle_generic_error function."""

    def test_json_mode_exits(self):
        """Test JSON mode exits cleanly."""
        from sdqctl.commands.output_steps import handle_generic_error

        mock_error = ValueError("Test error")

        mock_session = MagicMock()
        mock_session.save_pause_checkpoint.return_value = "/path/to/checkpoint"

        mock_console = MagicMock()

        with pytest.raises(SystemExit):
            handle_generic_error(
                error=mock_error,
                session=mock_session,
                workflow_path="test.conv",
                json_errors=True,  # JSON mode
                console=mock_console,
            )

        assert mock_session.state.status == "failed"

    def test_non_json_mode_sets_failed_status(self):
        """Test non-JSON mode sets failed status and prints error."""
        from sdqctl.commands.output_steps import handle_generic_error

        mock_error = ValueError("Test error")

        mock_session = MagicMock()
        mock_session.save_pause_checkpoint.return_value = "/path/to/checkpoint"

        mock_console = MagicMock()

        # The function re-raises, so catch it
        with pytest.raises(ValueError):
            handle_generic_error(
                error=mock_error,
                session=mock_session,
                workflow_path="test.conv",
                json_errors=False,  # Non-JSON mode
                console=mock_console,
            )

        assert mock_session.state.status == "failed"
        assert mock_console.print.called
