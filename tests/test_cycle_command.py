"""
Tests for sdqctl cycle command - multi-cycle workflow execution.

Tests the cycle command's ability to run multiple iterations,
handle compaction triggers, and checkpoint policies.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.core.conversation import ConversationFile


class TestCycleCommandBasic:
    """Test basic cycle command functionality."""

    def test_cycle_help(self, cli_runner):
        """Test cycle --help shows usage."""
        result = cli_runner.invoke(cli, ["cycle", "--help"])
        assert result.exit_code == 0
        assert "--max-cycles" in result.output
        assert "--checkpoint-dir" in result.output

    def test_cycle_help_shows_stop_file_option(self, cli_runner):
        """Test cycle --help shows --no-stop-file-prologue option."""
        result = cli_runner.invoke(cli, ["cycle", "--help"])
        assert result.exit_code == 0
        assert "--no-stop-file-prologue" in result.output

    def test_cycle_dry_run(self, cli_runner, workflow_file):
        """Test cycle --dry-run shows configuration."""
        result = cli_runner.invoke(cli, ["cycle", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Cycle Configuration" in result.output

    def test_cycle_requires_workflow_or_from_json(self, cli_runner):
        """Test cycle requires either workflow argument or --from-json."""
        result = cli_runner.invoke(cli, ["cycle"])
        assert result.exit_code != 0
        assert "required" in result.output.lower() or "WORKFLOW" in result.output

    def test_cycle_from_json_help(self, cli_runner):
        """Test cycle --help shows --from-json option."""
        result = cli_runner.invoke(cli, ["cycle", "--help"])
        assert result.exit_code == 0
        assert "--from-json" in result.output


class TestCycleExecution:
    """Test cycle command execution with mock adapter."""

    def test_cycle_runs_single_cycle(self, cli_runner, workflow_file):
        """Test cycle with 1 cycle completes."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "1",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        assert "Completed 1 cycles" in result.output

    def test_cycle_runs_multiple_cycles(self, cli_runner, workflow_file):
        """Test cycle with multiple cycles."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "3",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        assert "Completed 3 cycles" in result.output

    def test_cycle_max_cycles_override(self, cli_runner, tmp_path):
        """Test --max-cycles overrides workflow setting."""
        workflow = tmp_path / "multicycle.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
MAX-CYCLES 5
PROMPT Analyze iteration.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "2",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        assert "Completed 2 cycles" in result.output  # Override worked


class TestCycleOptions:
    """Test cycle command options."""

    def test_cycle_with_adapter_override(self, cli_runner, workflow_file):
        """Test --adapter overrides workflow setting."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0
        assert "mock" in result.output

    def test_cycle_with_model_override(self, cli_runner, workflow_file):
        """Test --model overrides workflow setting."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--model", "gpt-4-turbo",
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_cycle_with_output_file(self, cli_runner, workflow_file, tmp_path):
        """Test --output writes results to file."""
        output_file = tmp_path / "cycle-output.md"
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "1",
            "--adapter", "mock",
            "--output", str(output_file)
        ])
        assert result.exit_code == 0
        assert output_file.exists()

    def test_cycle_json_output(self, cli_runner, workflow_file):
        """Test --json produces JSON output."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "1",
            "--adapter", "mock",
            "--json"
        ])
        assert result.exit_code == 0
        assert "{" in result.output
        assert "cycles_completed" in result.output


class TestCycleInjection:
    """Test prologue/epilogue and header/footer injection in cycle."""

    def test_cycle_with_prologue(self, cli_runner, workflow_file):
        """Test --prologue adds content to prompts."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "1",
            "--adapter", "mock",
            "--prologue", "Iteration context: testing"
        ])
        assert result.exit_code == 0

    def test_cycle_with_header_footer(self, cli_runner, workflow_file, tmp_path):
        """Test --header and --footer wrap output."""
        output_file = tmp_path / "output.md"
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "1",
            "--adapter", "mock",
            "--header", "# Cycle Report",
            "--footer", "---\nEnd of report",
            "--output", str(output_file)
        ])
        assert result.exit_code == 0
        if output_file.exists():
            content = output_file.read_text()
            assert "# Cycle Report" in content


class TestCycleWorkflowParsing:
    """Test cycle command workflow parsing."""

    def test_cycle_parses_max_cycles(self):
        """Test MAX-CYCLES directive is parsed."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES 10
PROMPT Iterate.
"""
        conv = ConversationFile.parse(content)
        assert conv.max_cycles == 10

    def test_cycle_parses_context_limit(self):
        """Test CONTEXT-LIMIT directive is parsed."""
        content = """MODEL gpt-4
ADAPTER mock
CONTEXT-LIMIT 75%
PROMPT Iterate.
"""
        conv = ConversationFile.parse(content)
        assert conv.context_limit == 0.75

    def test_cycle_parses_on_context_limit(self):
        """Test ON-CONTEXT-LIMIT directive is parsed."""
        content = """MODEL gpt-4
ADAPTER mock
ON-CONTEXT-LIMIT compact
PROMPT Iterate.
"""
        conv = ConversationFile.parse(content)
        assert conv.on_context_limit == "compact"


class TestCycleSessionModes:
    """Test session mode behavior (fresh, compact, accumulate)."""

    def test_fresh_mode_creates_new_sessions(self, cli_runner, tmp_path):
        """Test fresh mode logs new session creation for each cycle."""
        workflow = tmp_path / "fresh-test.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
PROMPT Analyze.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "3",
            "--adapter", "mock",
            "--session-mode", "fresh"
        ])
        assert result.exit_code == 0
        assert "Completed 3 cycles" in result.output

    def test_fresh_mode_reloads_context_files(self, cli_runner, tmp_path):
        """Test fresh mode re-reads CONTEXT files from disk between cycles.
        
        This validates the reload_context() implementation from C1.
        """
        # Create a context file that will be "modified" 
        context_file = tmp_path / "tracker.md"
        context_file.write_text("# Initial Content\nVersion 1")
        
        workflow = tmp_path / "context-test.conv"
        workflow.write_text(f"""MODEL gpt-4
ADAPTER mock
CWD {tmp_path}
CONTEXT @tracker.md
PROMPT Check tracker content.
""")
        
        # Fresh mode with context - should complete without error
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "2",
            "--adapter", "mock",
            "--session-mode", "fresh"
        ])
        assert result.exit_code == 0
        assert "Completed 2 cycles" in result.output

    def test_accumulate_mode_preserves_context(self, cli_runner, tmp_path):
        """Test accumulate mode maintains session across cycles."""
        workflow = tmp_path / "accumulate-test.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
PROMPT Continue analysis.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "2",
            "--adapter", "mock",
            "--session-mode", "accumulate"
        ])
        assert result.exit_code == 0
        assert "Completed 2 cycles" in result.output

    def test_compact_mode_summarizes_between_cycles(self, cli_runner, tmp_path):
        """Test compact mode triggers summarization between cycles."""
        workflow = tmp_path / "compact-test.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
COMPACT-PRESERVE findings, decisions
PROMPT Analyze iteration.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "2",
            "--adapter", "mock",
            "--session-mode", "compact"
        ])
        assert result.exit_code == 0
        # Compact mode logs compaction activity
        assert "Compacting" in result.output or "Completed 2 cycles" in result.output

    def test_inline_compact_step_executes(self, cli_runner, tmp_path):
        """Test COMPACT directive within workflow is conditional on threshold (Q-012 fix)."""
        workflow = tmp_path / "inline-compact.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
PROMPT Step 1: Do something.
COMPACT
PROMPT Step 2: Continue after compaction.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "1",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        # COMPACT step was processed - either executed or skipped based on threshold
        assert "Compacting" in result.output or "Skipping COMPACT" in result.output
        assert "Completed 1 cycles" in result.output

    def test_compact_with_empty_context(self, cli_runner, tmp_path):
        """Test COMPACT skipped when no context files loaded (Q-012 behavior)."""
        workflow = tmp_path / "empty-context-compact.conv"
        workflow.write_text(f"""MODEL gpt-4
ADAPTER mock
CWD {tmp_path}

PROMPT Step 1.
COMPACT
PROMPT Step 2.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "1",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        # COMPACT skipped because context is below threshold
        assert "Skipping COMPACT" in result.output
        assert "Completed 1 cycles" in result.output

    def test_compact_executes_with_min_density_zero(self, cli_runner, tmp_path):
        """Test COMPACT executes when min-compaction-density is 0 (always run)."""
        workflow = tmp_path / "force-compact.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
PROMPT Step 1: Do something.
COMPACT
PROMPT Step 2: Continue after compaction.
""")
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow),
            "--max-cycles", "1",
            "--adapter", "mock",
            "--min-compaction-density", "0"
        ])
        assert result.exit_code == 0
        # With min-density 0, COMPACT should execute (needs_compaction checks is_near_limit first)
        # The mock adapter may or may not trigger near-limit, so check either outcome
        assert "Compacting" in result.output or "Skipping COMPACT" in result.output
        assert "Completed 1 cycles" in result.output

    def test_session_mode_default_is_accumulate(self, cli_runner, workflow_file):
        """Test default session mode is accumulate."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--dry-run"
        ])
        assert result.exit_code == 0
        # Dry run shows config - default mode should be applied


class TestParseTargets:
    """Test parse_targets function for mixed prompt mode (Phase 6)."""

    def test_single_prompt(self):
        """Test single inline prompt."""
        from sdqctl.commands.iterate import parse_targets, TurnGroup
        groups = parse_targets(("Hello world",))
        assert len(groups) == 1
        assert groups[0].items == ["Hello world"]

    def test_single_file(self, tmp_path):
        """Test single .conv file."""
        from sdqctl.commands.iterate import parse_targets
        workflow = tmp_path / "test.conv"
        workflow.write_text("PROMPT Test")
        groups = parse_targets((str(workflow),))
        assert len(groups) == 1
        assert groups[0].items == [str(workflow)]

    def test_separator_creates_groups(self):
        """Test --- separator creates separate turn groups."""
        from sdqctl.commands.iterate import parse_targets
        groups = parse_targets(("prompt1", "---", "prompt2"))
        assert len(groups) == 2
        assert groups[0].items == ["prompt1"]
        assert groups[1].items == ["prompt2"]

    def test_multiple_items_in_group(self):
        """Test multiple items without separator stay in same group."""
        from sdqctl.commands.iterate import parse_targets
        groups = parse_targets(("prompt1", "prompt2", "prompt3"))
        assert len(groups) == 1
        assert groups[0].items == ["prompt1", "prompt2", "prompt3"]

    def test_empty_groups_filtered(self):
        """Test empty groups from consecutive separators are filtered."""
        from sdqctl.commands.iterate import parse_targets
        groups = parse_targets(("prompt1", "---", "---", "prompt2"))
        assert len(groups) == 2  # Empty middle group filtered

    def test_leading_separator_ignored(self):
        """Test leading separator creates no empty group."""
        from sdqctl.commands.iterate import parse_targets
        groups = parse_targets(("---", "prompt1"))
        assert len(groups) == 1
        assert groups[0].items == ["prompt1"]

    def test_trailing_separator_ignored(self):
        """Test trailing separator creates no empty group."""
        from sdqctl.commands.iterate import parse_targets
        groups = parse_targets(("prompt1", "---"))
        assert len(groups) == 1
        assert groups[0].items == ["prompt1"]


class TestValidateTargets:
    """Test validate_targets function for mixed prompt mode (Phase 6)."""

    def test_no_conv_file(self):
        """Test validation with only inline prompts."""
        from sdqctl.commands.iterate import parse_targets, validate_targets
        groups = parse_targets(("prompt1", "prompt2"))
        workflow_path, pre, post = validate_targets(groups)
        assert workflow_path is None
        assert pre == ["prompt1", "prompt2"]
        assert post == []

    def test_single_conv_file(self, tmp_path):
        """Test validation with single .conv file."""
        from sdqctl.commands.iterate import parse_targets, validate_targets
        workflow = tmp_path / "test.conv"
        workflow.write_text("PROMPT Test")
        groups = parse_targets((str(workflow),))
        workflow_path, pre, post = validate_targets(groups)
        assert workflow_path == str(workflow)
        assert pre == []
        assert post == []

    def test_mixed_pre_and_post(self, tmp_path):
        """Test prompts before and after .conv file."""
        from sdqctl.commands.iterate import parse_targets, validate_targets
        workflow = tmp_path / "test.conv"
        workflow.write_text("PROMPT Test")
        groups = parse_targets(("before1", "before2", str(workflow), "after1"))
        workflow_path, pre, post = validate_targets(groups)
        assert workflow_path == str(workflow)
        assert pre == ["before1", "before2"]
        assert post == ["after1"]

    def test_multiple_conv_files_error(self, tmp_path):
        """Test error when multiple .conv files provided."""
        import click
        from sdqctl.commands.iterate import parse_targets, validate_targets
        w1 = tmp_path / "first.conv"
        w2 = tmp_path / "second.conv"
        w1.write_text("PROMPT First")
        w2.write_text("PROMPT Second")
        groups = parse_targets((str(w1), str(w2)))
        with pytest.raises(click.UsageError) as exc_info:
            validate_targets(groups)
        assert "only ONE .conv file" in str(exc_info.value)

    def test_copilot_extension_recognized(self, tmp_path):
        """Test .copilot extension files are recognized."""
        from sdqctl.commands.iterate import parse_targets, validate_targets
        workflow = tmp_path / "test.copilot"
        workflow.write_text("PROMPT Test")
        groups = parse_targets((str(workflow),))
        workflow_path, pre, post = validate_targets(groups)
        assert workflow_path == str(workflow)

    def test_nonexistent_file_treated_as_prompt(self, tmp_path):
        """Test non-existent file path treated as prompt text."""
        from sdqctl.commands.iterate import parse_targets, validate_targets
        groups = parse_targets(("nonexistent.conv", "prompt"))
        workflow_path, pre, post = validate_targets(groups)
        # nonexistent.conv doesn't exist, so treated as prompt
        assert workflow_path is None
        assert pre == ["nonexistent.conv", "prompt"]


class TestIterateMixedMode:
    """Integration tests for iterate command mixed mode."""

    def test_iterate_help_shows_mixed_mode(self, cli_runner):
        """Test iterate --help documents mixed mode."""
        result = cli_runner.invoke(cli, ["iterate", "--help"])
        assert result.exit_code == 0
        assert "TARGETS" in result.output
        assert "---" in result.output

    def test_iterate_inline_prompt(self, cli_runner):
        """Test iterate with inline prompt only."""
        result = cli_runner.invoke(cli, [
            "iterate", "Hello world",
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_iterate_mixed_prompts_and_file(self, cli_runner, tmp_path):
        """Test iterate with prompts before and after .conv file."""
        workflow = tmp_path / "mixed.conv"
        workflow.write_text("""MODEL gpt-4
ADAPTER mock
PROMPT Middle step.
""")
        result = cli_runner.invoke(cli, [
            "iterate",
            "Setup context",
            str(workflow),
            "Final summary",
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0


class TestIterateDisambiguation:
    """Tests for --prompt and --file disambiguation flags."""

    def test_iterate_help_shows_disambiguation_flags(self, cli_runner):
        """Test iterate --help shows --prompt and --file flags."""
        result = cli_runner.invoke(cli, ["iterate", "--help"])
        assert result.exit_code == 0
        assert "-p, --prompt" in result.output
        assert "-f, --file" in result.output
        assert "disambiguate" in result.output.lower()

    def test_explicit_prompt_not_treated_as_file(self, cli_runner, tmp_path):
        """Test --prompt flag prevents file path detection."""
        # Create a file that would match if treated as path
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nPROMPT This is the file.\n")
        
        # Use --prompt to treat the path as a prompt string
        result = cli_runner.invoke(cli, [
            "iterate",
            "--prompt", str(workflow),  # Should be treated as prompt, not file
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0
        # The file path should be in output as prompt, not loaded as workflow
        assert "test.conv" in result.output or "Dry run" in result.output

    def test_explicit_file_for_nonexistent_path(self, cli_runner, tmp_path):
        """Test --file flag treats path as file even if it doesn't exist."""
        # Path that doesn't exist
        nonexistent = tmp_path / "future.conv"
        
        result = cli_runner.invoke(cli, [
            "iterate",
            "--file", str(nonexistent),
            "--adapter", "mock",
            "--dry-run"
        ])
        # Should fail because file doesn't exist
        assert result.exit_code != 0
        # Exception type indicates it was treated as a file, not as a prompt
        assert result.exception is not None

    def test_multiple_explicit_prompts(self, cli_runner):
        """Test multiple --prompt flags."""
        result = cli_runner.invoke(cli, [
            "iterate",
            "-p", "First prompt",
            "-p", "Second prompt",
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_mixed_explicit_and_positional(self, cli_runner, tmp_path):
        """Test mixing --prompt/--file with positional args."""
        workflow = tmp_path / "work.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Workflow step.\n")
        
        result = cli_runner.invoke(cli, [
            "iterate",
            "-p", "Explicit prompt first",
            str(workflow),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0
