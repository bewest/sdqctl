"""Tests for sdqctl progress module."""

import sys
import time
from io import StringIO
from unittest.mock import patch

import pytest

from sdqctl.core.progress import (
    progress,
    progress_step,
    progress_file,
    progress_done,
    progress_timer,
    set_quiet,
    is_quiet,
    ProgressTracker,
)


@pytest.fixture(autouse=True)
def reset_quiet():
    """Reset quiet mode before and after each test."""
    set_quiet(False)
    yield
    set_quiet(False)


class TestQuietMode:
    """Test quiet mode functionality."""
    
    def test_default_not_quiet(self):
        """Test quiet mode is off by default."""
        assert is_quiet() is False
    
    def test_set_quiet_true(self):
        """Test setting quiet mode on."""
        set_quiet(True)
        assert is_quiet() is True
    
    def test_set_quiet_false(self):
        """Test setting quiet mode off."""
        set_quiet(True)
        set_quiet(False)
        assert is_quiet() is False
    
    def test_set_quiet_default_arg(self):
        """Test set_quiet() with default arg sets quiet."""
        set_quiet()  # Should default to True
        assert is_quiet() is True


class TestProgressFunction:
    """Test progress() function."""
    
    def test_progress_prints_to_stdout(self, capsys):
        """Test progress prints to stdout."""
        progress("Test message")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert captured.err == ""  # Nothing to stderr
    
    def test_progress_newline_default(self, capsys):
        """Test progress adds newline by default."""
        progress("Line 1")
        progress("Line 2")
        
        captured = capsys.readouterr()
        assert "Line 1\nLine 2\n" == captured.out
    
    def test_progress_custom_end(self, capsys):
        """Test progress with custom end character."""
        progress("No newline", end="")
        progress("With space", end=" ")
        
        captured = capsys.readouterr()
        assert "No newlineWith space " == captured.out
    
    def test_progress_quiet_mode_suppresses(self, capsys):
        """Test progress is suppressed in quiet mode."""
        set_quiet(True)
        progress("This should not appear")
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_progress_flush_default(self):
        """Test progress flushes by default."""
        with patch.object(sys, 'stdout', new_callable=StringIO) as mock_stdout:
            # Can't easily test flush, but ensure it doesn't error
            # Just verify it calls print with flush=True
            with patch('builtins.print') as mock_print:
                progress("Test")
                mock_print.assert_called_with(
                    "Test", end="\n", flush=True, file=sys.stdout
                )


class TestProgressHelpers:
    """Test progress helper functions."""
    
    def test_progress_step(self, capsys):
        """Test progress_step formatting."""
        progress_step(2, 5, "Sending prompt...")
        
        captured = capsys.readouterr()
        assert "Step 2/5: Sending prompt..." in captured.out
    
    def test_progress_file(self, capsys):
        """Test progress_file formatting."""
        progress_file("Writing to", "reports/output.md")
        
        captured = capsys.readouterr()
        assert "Writing to reports/output.md" in captured.out
    
    def test_progress_done(self, capsys):
        """Test progress_done formatting."""
        progress_done(4.123)
        
        captured = capsys.readouterr()
        assert "Done in 4.1s" in captured.out
    
    def test_progress_done_rounding(self, capsys):
        """Test progress_done rounds to 1 decimal."""
        progress_done(10.999)
        
        captured = capsys.readouterr()
        assert "Done in 11.0s" in captured.out


class TestProgressTimer:
    """Test progress_timer context manager."""
    
    def test_timer_tracks_elapsed(self):
        """Test timer tracks elapsed time."""
        with progress_timer() as timer:
            time.sleep(0.1)
        
        assert timer.elapsed >= 0.1
        assert timer.elapsed < 0.5  # Should be close to 0.1
    
    def test_timer_mark_method(self):
        """Test timer mark() updates and returns elapsed."""
        with progress_timer() as timer:
            time.sleep(0.05)
            mid = timer.mark()
            time.sleep(0.05)
        
        assert mid >= 0.05
        assert timer.elapsed >= 0.1
        assert timer.elapsed > mid  # Final should be greater than mid
    
    def test_timer_start_attribute(self):
        """Test timer has start time."""
        before = time.time()
        with progress_timer() as timer:
            pass
        after = time.time()
        
        assert timer.start >= before
        assert timer.start <= after


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_tracker_init(self):
        """Test tracker initialization."""
        tracker = ProgressTracker("test.conv", total_steps=5)
        
        assert tracker.name == "test.conv"
        assert tracker.total_steps == 5
        assert tracker.current_step == 0
        assert tracker.start_time is None
    
    def test_tracker_start(self, capsys):
        """Test tracker start message."""
        tracker = ProgressTracker("workflow.conv")
        tracker.start()
        
        captured = capsys.readouterr()
        assert "Running workflow.conv..." in captured.out
        assert tracker.start_time is not None
    
    def test_tracker_step_with_total(self, capsys):
        """Test step with total shows numbered step."""
        tracker = ProgressTracker("test", total_steps=3)
        tracker.step("First action")
        
        captured = capsys.readouterr()
        assert "Step 1/3: First action" in captured.out
        assert tracker.current_step == 1
    
    def test_tracker_step_without_total(self, capsys):
        """Test step without total shows just action."""
        tracker = ProgressTracker("test", total_steps=0)
        tracker.step("Some action")
        
        captured = capsys.readouterr()
        assert "Some action" in captured.out
        assert "Step" not in captured.out
    
    def test_tracker_multiple_steps(self, capsys):
        """Test multiple steps increment counter."""
        tracker = ProgressTracker("test", total_steps=3)
        tracker.step("First")
        tracker.step("Second")
        tracker.step("Third")
        
        captured = capsys.readouterr()
        assert "Step 1/3" in captured.out
        assert "Step 2/3" in captured.out
        assert "Step 3/3" in captured.out
        assert tracker.current_step == 3
    
    def test_tracker_step_done_with_result(self, capsys):
        """Test step_done with result message."""
        tracker = ProgressTracker("test")
        tracker.step("Processing")
        time.sleep(0.1)
        tracker.step_done("Success")
        
        captured = capsys.readouterr()
        assert "Success" in captured.out
        # Should include timing
        assert "0." in captured.out or "s)" in captured.out
    
    def test_tracker_step_done_without_result(self, capsys):
        """Test step_done without result (silent)."""
        tracker = ProgressTracker("test")
        tracker.step("Processing")
        tracker.step_done()  # No result
        
        captured = capsys.readouterr()
        # Should only have the step message
        assert "Processing" in captured.out
    
    def test_tracker_file_op(self, capsys):
        """Test file operation message."""
        tracker = ProgressTracker("test")
        tracker.file_op("Writing to", "output.md")
        
        captured = capsys.readouterr()
        assert "Writing to output.md" in captured.out
    
    def test_tracker_checkpoint(self, capsys):
        """Test checkpoint message."""
        tracker = ProgressTracker("test")
        tracker.checkpoint("cycle-1")
        
        captured = capsys.readouterr()
        assert "CHECKPOINT" in captured.out
        assert "cycle-1" in captured.out
        assert "📌" in captured.out
    
    def test_tracker_done(self, capsys):
        """Test done message with duration."""
        tracker = ProgressTracker("test")
        tracker.start()
        time.sleep(0.1)
        tracker.done()
        
        captured = capsys.readouterr()
        assert "Done in" in captured.out
        assert "0." in captured.out  # Should be ~0.1s


class TestProgressTrackerIntegration:
    """Integration tests for ProgressTracker."""
    
    def test_full_workflow(self, capsys):
        """Test complete workflow tracking."""
        tracker = ProgressTracker("workflow.conv", total_steps=3)
        
        tracker.start()
        
        tracker.step("Sending prompt 1")
        time.sleep(0.01)
        tracker.step_done()
        
        tracker.step("Sending prompt 2")
        tracker.file_op("Writing to", "reports/partial.md")
        tracker.step_done("Received response")
        
        tracker.step("Sending prompt 3")
        tracker.checkpoint("final")
        tracker.step_done()
        
        tracker.done()
        
        captured = capsys.readouterr()
        
        assert "Running workflow.conv..." in captured.out
        assert "Step 1/3" in captured.out
        assert "Step 2/3" in captured.out
        assert "Step 3/3" in captured.out
        assert "Writing to" in captured.out
        assert "CHECKPOINT" in captured.out
        assert "Done in" in captured.out
    
    def test_quiet_mode_suppresses_all(self, capsys):
        """Test quiet mode suppresses all tracker output."""
        set_quiet(True)
        
        tracker = ProgressTracker("test", total_steps=2)
        tracker.start()
        tracker.step("Action")
        tracker.step_done("Result")
        tracker.checkpoint("cp1")
        tracker.done()
        
        captured = capsys.readouterr()
        assert captured.out == ""


class TestWorkflowProgress:
    """Tests for the enhanced WorkflowProgress class."""
    
    def test_workflow_progress_init(self):
        """Test WorkflowProgress initialization."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=3, total_prompts=4, verbosity=1)
        assert wp.name == "test.conv"
        assert wp.total_cycles == 3
        assert wp.total_prompts == 4
        assert wp.verbosity == 1
    
    def test_workflow_progress_start(self, capsys):
        """Test WorkflowProgress start message."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("workflow.conv", total_cycles=2, total_prompts=3)
        wp.start()
        
        captured = capsys.readouterr()
        assert "Running workflow.conv..." in captured.out
    
    def test_workflow_progress_prompt_sending(self, capsys):
        """Test prompt sending progress with context %."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=2, total_prompts=3)
        wp.prompt_sending(cycle=1, prompt=2, context_pct=45.5)
        
        captured = capsys.readouterr()
        assert "Cycle 1/2" in captured.out
        assert "Prompt 2/3" in captured.out
        assert "ctx: 46%" in captured.out  # Rounded
    
    def test_workflow_progress_single_cycle_format(self, capsys):
        """Test single cycle mode omits cycle number."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=1, total_prompts=2)
        wp.prompt_sending(cycle=1, prompt=1, context_pct=10.0)
        
        captured = capsys.readouterr()
        # Should NOT show "Cycle 1/1" for single-cycle workflows
        assert "Cycle" not in captured.out
        assert "Prompt 1/2" in captured.out
    
    def test_workflow_progress_prompt_complete(self, capsys):
        """Test prompt completion with duration and context."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=1, total_prompts=2)
        wp.prompt_complete(cycle=1, prompt=1, duration=3.25, context_pct=35.0)
        
        captured = capsys.readouterr()
        assert "Complete" in captured.out
        assert "3.2s" in captured.out or "3.3s" in captured.out
        assert "ctx: 35%" in captured.out
    
    def test_workflow_progress_cycle_complete(self, capsys):
        """Test cycle completion message."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=3, total_prompts=2)
        wp.cycle_complete(cycle=2, compacted=True)
        
        captured = capsys.readouterr()
        assert "Cycle 2/3" in captured.out
        assert "Complete" in captured.out
        assert "compacted" in captured.out
    
    def test_workflow_progress_verbose_preview(self, capsys):
        """Test prompt preview shown at verbose level."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=1, total_prompts=1, verbosity=1)
        wp.prompt_sending(cycle=1, prompt=1, context_pct=20.0, preview="Analyze the code")
        
        captured = capsys.readouterr()
        assert "Analyze the code" in captured.out
    
    def test_workflow_progress_done(self, capsys):
        """Test workflow completion message."""
        from sdqctl.core.progress import WorkflowProgress
        
        wp = WorkflowProgress("test.conv", total_cycles=1, total_prompts=1)
        wp.start()
        time.sleep(0.05)
        wp.done()
        
        captured = capsys.readouterr()
        assert "Done in" in captured.out
    
    def test_workflow_progress_quiet_suppresses_all(self, capsys):
        """Test quiet mode suppresses WorkflowProgress output."""
        from sdqctl.core.progress import WorkflowProgress
        
        set_quiet(True)
        
        wp = WorkflowProgress("test.conv", total_cycles=2, total_prompts=3)
        wp.start()
        wp.prompt_sending(cycle=1, prompt=1, context_pct=10.0)
        wp.prompt_complete(cycle=1, prompt=1, duration=1.0, context_pct=20.0)
        wp.cycle_complete(cycle=1)
        wp.done()
        
        captured = capsys.readouterr()
        assert captured.out == ""


class TestTTYDetection:
    """Tests for TTY detection in progress module."""
    
    def test_is_tty_function_exists(self):
        """Test is_tty function is available."""
        from sdqctl.core.progress import is_tty
        
        # Should return a boolean
        result = is_tty()
        assert isinstance(result, bool)


class TestTimestamps:
    """Tests for timestamp functionality (Q-019A)."""

    def test_set_timestamps_function_exists(self):
        """Test set_timestamps function is available."""
        from sdqctl.core.progress import set_timestamps
        
        # Should not raise
        set_timestamps(True)
        set_timestamps(False)

    def test_progress_with_timestamps(self, capsys):
        """Test progress includes timestamp when enabled."""
        from sdqctl.core.progress import set_timestamps
        
        set_timestamps(True)
        progress("Test message")
        set_timestamps(False)  # Reset
        
        captured = capsys.readouterr()
        # Should have HH:MM:SS format timestamp
        import re
        assert re.match(r'\d{2}:\d{2}:\d{2} Test message', captured.out)

    def test_progress_without_timestamps(self, capsys):
        """Test progress has no timestamp when disabled (default)."""
        from sdqctl.core.progress import set_timestamps
        
        set_timestamps(False)
        progress("Test message")
        
        captured = capsys.readouterr()
        # Should NOT have timestamp prefix
        assert captured.out == "Test message\n"
        
    def test_timestamps_disabled_by_default(self, capsys):
        """Test timestamps are off by default."""
        # Just call progress without setting timestamps
        progress("Plain message")
        
        captured = capsys.readouterr()
        # Should not have timestamp
        assert captured.out == "Plain message\n"


class TestAgentResponse:
    """Tests for agent_response function."""

    def test_agent_response_prints_to_stdout(self, capsys):
        """agent_response should print response to stdout."""
        from sdqctl.core.progress import agent_response, set_quiet

        set_quiet(False)
        agent_response("Hello from agent", cycle=1, prompt=1)

        captured = capsys.readouterr()
        assert "Hello from agent" in captured.out
        assert "[Agent Cycle 1, Prompt 1]" in captured.out

    def test_agent_response_quiet_mode(self, capsys):
        """agent_response should not print in quiet mode."""
        from sdqctl.core.progress import agent_response, set_quiet

        set_quiet(True)
        agent_response("Should not appear")

        captured = capsys.readouterr()
        assert captured.out == ""

        # Reset quiet mode
        set_quiet(False)

    def test_agent_response_no_cycle(self, capsys):
        """agent_response with no cycle should show simple header."""
        from sdqctl.core.progress import agent_response, set_quiet

        set_quiet(False)
        agent_response("Simple response")

        captured = capsys.readouterr()
        assert "[Agent]" in captured.out
        assert "Simple response" in captured.out

    def test_agent_response_cycle_only(self, capsys):
        """agent_response with cycle but no prompt."""
        from sdqctl.core.progress import agent_response, set_quiet

        set_quiet(False)
        agent_response("Cycle response", cycle=2)

        captured = capsys.readouterr()
        assert "[Agent Cycle 2]" in captured.out
        assert "Cycle response" in captured.out


class TestWorkflowProgressLineNumber:
    """Tests for line number tracking in WorkflowProgress."""

    def test_format_position_with_line_number(self):
        """Line number should be included in position string."""
        from sdqctl.core.progress import WorkflowProgress

        wp = WorkflowProgress("test", total_cycles=1, total_prompts=5)
        pos = wp._format_position(cycle=1, prompt=2, line_number=42)
        
        assert "Prompt 2/5" in pos
        assert "(line 42)" in pos

    def test_format_position_with_line_and_context(self):
        """Line number and context % should both be shown."""
        from sdqctl.core.progress import WorkflowProgress

        wp = WorkflowProgress("test", total_cycles=2, total_prompts=10)
        pos = wp._format_position(cycle=1, prompt=3, context_pct=55.0, line_number=100)
        
        assert "[Cycle 1/2]" in pos
        assert "Prompt 3/10" in pos
        assert "(line 100)" in pos
        assert "(ctx: 55%)" in pos

    def test_format_position_no_line_number(self):
        """When line_number is None, it should not appear."""
        from sdqctl.core.progress import WorkflowProgress

        wp = WorkflowProgress("test", total_cycles=1, total_prompts=3)
        pos = wp._format_position(cycle=1, prompt=1, line_number=None)
        
        assert "Prompt 1/3" in pos
        assert "line" not in pos

    def test_format_position_zero_line_number(self):
        """When line_number is 0, it should not appear."""
        from sdqctl.core.progress import WorkflowProgress

        wp = WorkflowProgress("test", total_cycles=1, total_prompts=3)
        pos = wp._format_position(cycle=1, prompt=1, line_number=0)
        
        assert "Prompt 1/3" in pos
        assert "line" not in pos


class TestWorkflowProgressRunExecution:
    """Tests for RUN execution progress in WorkflowProgress."""

    def test_run_executing_shows_command(self, capsys):
        """run_executing should show the command being run."""
        from sdqctl.core.progress import WorkflowProgress, set_quiet

        set_quiet(False)
        wp = WorkflowProgress("test", total_cycles=1, total_prompts=5)
        wp.run_executing("git status", cmd_idx=0, total_cmds=3)
        
        # Force output by ending TTY mode
        wp._end_overwrite()
        captured = capsys.readouterr()
        assert "RUN 1/3" in captured.out
        assert "git status" in captured.out

    def test_run_executing_truncates_long_command(self, capsys):
        """Long commands should be truncated in display."""
        from sdqctl.core.progress import WorkflowProgress, set_quiet

        set_quiet(False)
        wp = WorkflowProgress("test", total_cycles=1, total_prompts=5)
        long_cmd = "grep -E 'some very long pattern that goes on and on' /path/to/some/very/long/filename.txt"
        wp.run_executing(long_cmd, cmd_idx=1, total_cmds=2)
        
        wp._end_overwrite()
        captured = capsys.readouterr()
        assert "RUN 2/2" in captured.out
        assert "..." in captured.out  # Should be truncated

    def test_run_complete_success(self, capsys):
        """run_complete should show success status."""
        from sdqctl.core.progress import WorkflowProgress, set_quiet

        set_quiet(False)
        wp = WorkflowProgress("test", total_cycles=1, total_prompts=5)
        wp.run_complete(cmd_idx=0, total_cmds=2, success=True, duration=1.5)
        
        wp._end_overwrite()
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "RUN 1/2" in captured.out
        assert "1.5s" in captured.out

    def test_run_complete_failure(self, capsys):
        """run_complete should show failure status."""
        from sdqctl.core.progress import WorkflowProgress, set_quiet

        set_quiet(False)
        wp = WorkflowProgress("test", total_cycles=1, total_prompts=5)
        wp.run_complete(cmd_idx=2, total_cmds=3, success=False, duration=0.3)
        
        wp._end_overwrite()
        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "RUN 3/3" in captured.out


class TestTotalPromptsAfterElide:
    """Tests for correct prompt counting after ELIDE processing."""

    def test_merged_prompts_counted_correctly(self):
        """After ELIDE, total_prompts should reflect merged count."""
        from sdqctl.core.conversation import ConversationFile, ConversationStep
        from sdqctl.commands.elide import process_elided_steps

        # Create steps that will be merged by ELIDE
        steps = [
            ConversationStep(type="prompt", content="First part"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="git status"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Second part"),
            ConversationStep(type="prompt", content="Separate prompt"),
        ]
        
        merged = process_elided_steps(steps)
        
        # Count prompts the same way iterate.py does
        total_prompts = sum(
            1 for s in merged
            if (s.type if hasattr(s, 'type') else s.get('type', ''))
            in ("prompt", "merged_prompt")
        )
        
        # Should be 2: one merged_prompt (from first 5 steps) and one prompt
        assert total_prompts == 2

    def test_no_elide_all_prompts_counted(self):
        """Without ELIDE, all prompts should be counted."""
        from sdqctl.core.conversation import ConversationStep
        from sdqctl.commands.elide import process_elided_steps

        steps = [
            ConversationStep(type="prompt", content="First"),
            ConversationStep(type="run", content="echo test"),
            ConversationStep(type="prompt", content="Second"),
            ConversationStep(type="prompt", content="Third"),
        ]
        
        merged = process_elided_steps(steps)
        
        total_prompts = sum(
            1 for s in merged
            if (s.type if hasattr(s, 'type') else s.get('type', ''))
            in ("prompt", "merged_prompt")
        )
        
        # Should be 3: all prompts remain separate (RUN without ELIDE doesn't merge)
        assert total_prompts == 3
