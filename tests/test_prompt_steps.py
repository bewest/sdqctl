"""Tests for prompt_steps module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sdqctl.commands.prompt_steps import (
    PromptContext,
    PromptBuildResult,
    LoopCheckResult,
    build_full_prompt,
    check_response_loop,
    emit_prompt_progress,
    format_loop_output,
)
from sdqctl.core.exceptions import LoopReason


class TestPromptContext:
    """Tests for PromptContext dataclass."""

    def test_prompt_context_creation(self):
        """Test PromptContext can be created with required fields."""
        ctx = PromptContext(
            prompt="Test prompt",
            prompt_idx=0,
            total_prompts=3,
            cycle_num=0,
            max_cycles=5,
            session_mode="accumulate",
            context_content="Some context",
            template_vars={"KEY": "value"},
        )
        assert ctx.prompt == "Test prompt"
        assert ctx.prompt_idx == 0
        assert ctx.session_mode == "accumulate"
        assert ctx.no_stop_file_prologue is False  # default
        assert ctx.verbosity == 0  # default

    def test_prompt_context_with_options(self):
        """Test PromptContext with optional fields."""
        ctx = PromptContext(
            prompt="Test",
            prompt_idx=1,
            total_prompts=2,
            cycle_num=1,
            max_cycles=3,
            session_mode="fresh",
            context_content="",
            template_vars={},
            no_stop_file_prologue=True,
            verbosity=2,
        )
        assert ctx.no_stop_file_prologue is True
        assert ctx.verbosity == 2


class TestPromptBuildResult:
    """Tests for PromptBuildResult dataclass."""

    def test_build_result_creation(self):
        """Test PromptBuildResult can be created."""
        result = PromptBuildResult(
            full_prompt="Full prompt text",
            context_pct=45.5,
            is_first=True,
            is_last=False,
        )
        assert result.full_prompt == "Full prompt text"
        assert result.context_pct == 45.5
        assert result.is_first is True
        assert result.is_last is False


class TestBuildFullPrompt:
    """Tests for build_full_prompt function."""

    def test_build_basic_prompt(self):
        """Test building a basic prompt without injections."""
        ctx = PromptContext(
            prompt="Hello world",
            prompt_idx=0,
            total_prompts=1,
            cycle_num=0,
            max_cycles=1,
            session_mode="accumulate",
            context_content="",
            template_vars={},
            no_stop_file_prologue=True,  # disable for simpler test
        )

        mock_conv = MagicMock()
        mock_conv.prologues = []
        mock_conv.epilogues = []
        mock_conv.source_path = None
        mock_conv.on_context_limit_prompt = None

        mock_session = MagicMock()
        mock_session.context.get_status.return_value = {"usage_percent": 25}

        mock_loop_detector = MagicMock()

        result = build_full_prompt(ctx, mock_conv, mock_session, mock_loop_detector)

        assert "Hello world" in result.full_prompt
        assert result.context_pct == 25
        assert result.is_first is True
        assert result.is_last is True  # single prompt

    def test_build_prompt_with_context(self):
        """Test building a prompt with context injection."""
        ctx = PromptContext(
            prompt="Do the thing",
            prompt_idx=0,
            total_prompts=2,
            cycle_num=0,
            max_cycles=1,
            session_mode="accumulate",
            context_content="## Context\nSome important info",
            template_vars={},
            no_stop_file_prologue=True,
        )

        mock_conv = MagicMock()
        mock_conv.prologues = []
        mock_conv.epilogues = []
        mock_conv.source_path = None
        mock_conv.on_context_limit_prompt = None

        mock_session = MagicMock()
        mock_session.context.get_status.return_value = {"usage_percent": 10}

        mock_loop_detector = MagicMock()

        result = build_full_prompt(ctx, mock_conv, mock_session, mock_loop_detector)

        assert "## Context" in result.full_prompt
        assert "Some important info" in result.full_prompt
        assert "Do the thing" in result.full_prompt
        assert result.is_first is True
        assert result.is_last is False  # not last of 2

    def test_build_prompt_stop_file_injection(self):
        """Test stop file instructions are injected on first prompt."""
        ctx = PromptContext(
            prompt="Work on this",
            prompt_idx=0,
            total_prompts=1,
            cycle_num=0,
            max_cycles=1,
            session_mode="accumulate",
            context_content="",
            template_vars={},
            no_stop_file_prologue=False,  # enable stop file
        )

        mock_conv = MagicMock()
        mock_conv.prologues = []
        mock_conv.epilogues = []
        mock_conv.source_path = None
        mock_conv.on_context_limit_prompt = None

        mock_session = MagicMock()
        mock_session.context.get_status.return_value = {"usage_percent": 5}

        mock_loop_detector = MagicMock()
        mock_loop_detector.stop_file_name = "STOP-abc123.json"

        result = build_full_prompt(ctx, mock_conv, mock_session, mock_loop_detector)

        assert "STOP-abc123.json" in result.full_prompt

    def test_build_prompt_continuation_context(self):
        """Test continuation context on cycle > 0 in accumulate mode."""
        ctx = PromptContext(
            prompt="Continue work",
            prompt_idx=0,
            total_prompts=1,
            cycle_num=1,  # second cycle
            max_cycles=3,
            session_mode="accumulate",
            context_content="",
            template_vars={},
            no_stop_file_prologue=True,
        )

        mock_conv = MagicMock()
        mock_conv.prologues = []
        mock_conv.epilogues = []
        mock_conv.source_path = None
        mock_conv.on_context_limit_prompt = "Continue from where you left off."

        mock_session = MagicMock()
        mock_session.context.get_status.return_value = {"usage_percent": 50}

        mock_loop_detector = MagicMock()

        result = build_full_prompt(ctx, mock_conv, mock_session, mock_loop_detector)

        assert "Continue from where you left off" in result.full_prompt


class TestLoopCheckResult:
    """Tests for LoopCheckResult dataclass."""

    def test_loop_not_detected(self):
        """Test LoopCheckResult when no loop detected."""
        result = LoopCheckResult(detected=False)
        assert result.detected is False
        assert result.loop_result is None

    def test_loop_detected(self):
        """Test LoopCheckResult when loop is detected."""
        mock_loop = MagicMock()
        result = LoopCheckResult(detected=True, loop_result=mock_loop)
        assert result.detected is True
        assert result.loop_result == mock_loop


class TestCheckResponseLoop:
    """Tests for check_response_loop function."""

    def test_no_loop_detected(self):
        """Test when no loop is detected."""
        mock_adapter = MagicMock()
        mock_adapter.get_session_stats.return_value = None

        mock_session = MagicMock()

        mock_loop_detector = MagicMock()
        mock_loop_detector.check.return_value = None

        result = check_response_loop(
            response="Good response with content",
            reasoning=["Thinking about the problem"],
            cycle_num=0,
            ai_adapter=mock_adapter,
            adapter_session=mock_session,
            loop_detector=mock_loop_detector,
        )

        assert result.detected is False
        assert result.loop_result is None

    def test_loop_detected(self):
        """Test when a loop is detected."""
        mock_adapter = MagicMock()
        mock_adapter.get_session_stats.return_value = None

        mock_session = MagicMock()

        mock_loop_result = MagicMock()
        mock_loop_detector = MagicMock()
        mock_loop_detector.check.return_value = mock_loop_result

        result = check_response_loop(
            response="Short",
            reasoning=[],
            cycle_num=1,
            ai_adapter=mock_adapter,
            adapter_session=mock_session,
            loop_detector=mock_loop_detector,
        )

        assert result.detected is True
        assert result.loop_result == mock_loop_result

    def test_tool_aware_loop_detection(self):
        """Test that tool calls are passed to loop detector."""
        mock_stats = MagicMock()
        mock_stats._send_turn_stats = MagicMock()
        mock_stats._send_turn_stats.tool_calls = 5

        mock_adapter = MagicMock()
        mock_adapter.get_session_stats.return_value = mock_stats

        mock_session = MagicMock()

        mock_loop_detector = MagicMock()
        mock_loop_detector.check.return_value = None

        check_response_loop(
            response="Short but productive",
            reasoning=["Did work"],
            cycle_num=0,
            ai_adapter=mock_adapter,
            adapter_session=mock_session,
            loop_detector=mock_loop_detector,
        )

        # Verify tool count was passed
        mock_loop_detector.check.assert_called_once()
        call_args = mock_loop_detector.check.call_args
        assert call_args[0][3] == 5  # 4th positional arg is turn_tools


class TestFormatLoopOutput:
    """Tests for format_loop_output function."""

    def test_format_stop_file_output(self):
        """Test formatting output for agent-initiated stop."""
        mock_loop_result = MagicMock()
        mock_loop_result.reason = LoopReason.STOP_FILE
        mock_loop_result.details = "Work complete, needs review"

        mock_loop_detector = MagicMock()
        mock_loop_detector.stop_file_name = "STOP-abc.json"

        mock_session = MagicMock()
        mock_session.id = "session-123"

        mock_console = MagicMock()
        mock_progress = MagicMock()

        format_loop_output(
            mock_loop_result,
            mock_loop_detector,
            mock_session,
            cycle_num=2,
            max_cycles=5,
            console=mock_console,
            progress=mock_progress,
        )

        # Check console.print was called with stop file info
        assert mock_console.print.called
        # Check progress was called
        mock_progress.assert_called_once()
        assert "Agent stop" in mock_progress.call_args[0][0]

    def test_format_other_loop_output(self):
        """Test formatting output for other loop types."""
        mock_loop_result = MagicMock()
        mock_loop_result.reason = MagicMock()
        mock_loop_result.reason.value = "repetition"

        mock_loop_detector = MagicMock()
        mock_session = MagicMock()
        mock_console = MagicMock()
        mock_progress = MagicMock()

        format_loop_output(
            mock_loop_result,
            mock_loop_detector,
            mock_session,
            cycle_num=1,
            max_cycles=3,
            console=mock_console,
            progress=mock_progress,
        )

        # Check progress was called with loop message
        mock_progress.assert_called_once()
        assert "Loop detected" in mock_progress.call_args[0][0]


class TestEmitPromptProgress:
    """Tests for emit_prompt_progress function."""

    def test_emit_progress(self):
        """Test emitting progress notifications."""
        ctx = PromptContext(
            prompt="Test prompt text",
            prompt_idx=0,
            total_prompts=2,
            cycle_num=0,
            max_cycles=3,
            session_mode="accumulate",
            context_content="",
            template_vars={},
            verbosity=1,
        )

        mock_workflow_progress = MagicMock()
        mock_prompt_writer = MagicMock()

        emit_prompt_progress(
            ctx,
            context_pct=35.5,
            workflow_progress=mock_workflow_progress,
            prompt_writer=mock_prompt_writer,
            full_prompt="Full prompt content here",
        )

        # Verify workflow progress was called
        mock_workflow_progress.prompt_sending.assert_called_once_with(
            cycle=1,
            prompt=1,
            context_pct=35.5,
            preview="Test prompt text"[:50],
        )

        # Verify prompt writer was called
        mock_prompt_writer.write_prompt.assert_called_once()
