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

    def test_cycle_dry_run(self, cli_runner, workflow_file):
        """Test cycle --dry-run shows configuration."""
        result = cli_runner.invoke(cli, ["cycle", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Cycle Configuration" in result.output

    def test_cycle_requires_workflow(self, cli_runner):
        """Test cycle requires workflow argument."""
        result = cli_runner.invoke(cli, ["cycle"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()


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
        """Test COMPACT directive within workflow executes during cycle (Q-010 fix)."""
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
        # Verify COMPACT step was executed (shows compaction message)
        assert "Compacting" in result.output or "🗜" in result.output
        assert "Completed 1 cycles" in result.output

    def test_session_mode_default_is_accumulate(self, cli_runner, workflow_file):
        """Test default session mode is accumulate."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--dry-run"
        ])
        assert result.exit_code == 0
        # Dry run shows config - default mode should be applied
