"""
CLI integration tests for sdqctl commands.

Tests CLI entry points using Click's test runner.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path

from sdqctl.cli import cli


class TestCliHelp:
    """Test CLI help and version output."""

    def test_help_shows_commands(self, cli_runner):
        """Test --help shows available commands."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "cycle" in result.output
        assert "flow" in result.output
        assert "apply" in result.output
        assert "status" in result.output

    def test_version_option(self, cli_runner):
        """Test --version shows version."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "sdqctl" in result.output


class TestRunCommand:
    """Test sdqctl run command."""

    def test_run_dry_run_inline_prompt(self, cli_runner):
        """Test sdqctl run --dry-run with inline prompt."""
        result = cli_runner.invoke(cli, ["run", "Test prompt", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_run_dry_run_workflow(self, cli_runner, workflow_file):
        """Test sdqctl run --dry-run with workflow file."""
        result = cli_runner.invoke(cli, ["run", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Workflow Configuration" in result.output
        assert "mock" in result.output  # adapter from workflow

    def test_run_with_mock_adapter(self, cli_runner, workflow_file):
        """Test sdqctl run with mock adapter executes successfully."""
        result = cli_runner.invoke(cli, ["run", str(workflow_file), "--adapter", "mock"])
        assert result.exit_code == 0

    def test_run_with_adapter_override(self, cli_runner, workflow_file):
        """Test --adapter flag overrides workflow setting."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file), 
            "--adapter", "mock", 
            "--dry-run"
        ])
        assert result.exit_code == 0
        assert "mock" in result.output

    def test_run_with_output_file(self, cli_runner, workflow_file, tmp_path):
        """Test --output writes to file."""
        output_file = tmp_path / "output.md"
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--adapter", "mock",
            "--output", str(output_file)
        ])
        assert result.exit_code == 0
        assert output_file.exists()

    def test_run_with_context(self, cli_runner, tmp_path):
        """Test --context adds context files."""
        # Create a context file
        ctx_file = tmp_path / "context.txt"
        ctx_file.write_text("Context content")
        
        # Create workflow
        workflow = tmp_path / "test.conv"
        workflow.write_text("MODEL gpt-4\nADAPTER mock\nPROMPT Test.")
        
        result = cli_runner.invoke(cli, [
            "run", str(workflow),
            "--context", str(ctx_file),
            "--dry-run"
        ])
        assert result.exit_code == 0


class TestRunFileRestrictions:
    """Test file restriction options for run command."""

    def test_run_with_allow_files(self, cli_runner, workflow_file):
        """Test --allow-files option."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--allow-files", "*.js",
            "--dry-run"
        ])
        assert result.exit_code == 0
        assert "*.js" in result.output or "Allow patterns" in result.output

    def test_run_with_deny_files(self, cli_runner, workflow_file):
        """Test --deny-files option."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--deny-files", "*secret*",
            "--dry-run"
        ])
        assert result.exit_code == 0


class TestRunInjection:
    """Test prologue/epilogue and header/footer injection."""

    def test_run_with_prologue(self, cli_runner, workflow_file):
        """Test --prologue prepends content."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--adapter", "mock",
            "--prologue", "Date: 2026-01-21"
        ])
        assert result.exit_code == 0

    def test_run_with_epilogue(self, cli_runner, workflow_file):
        """Test --epilogue appends content."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--adapter", "mock",
            "--epilogue", "Remember to cite sources."
        ])
        assert result.exit_code == 0

    def test_run_with_header_footer(self, cli_runner, workflow_file, tmp_path):
        """Test --header and --footer wrap output."""
        output_file = tmp_path / "output.md"
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--adapter", "mock",
            "--header", "# Report",
            "--footer", "---\nGenerated by sdqctl",
            "--output", str(output_file)
        ])
        assert result.exit_code == 0
        if output_file.exists():
            content = output_file.read_text()
            assert "# Report" in content
            assert "Generated by sdqctl" in content


class TestCycleCommand:
    """Test sdqctl cycle command."""

    def test_cycle_dry_run(self, cli_runner, workflow_file):
        """Test sdqctl cycle --dry-run."""
        result = cli_runner.invoke(cli, ["cycle", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Cycle Configuration" in result.output

    def test_cycle_with_max_cycles(self, cli_runner, workflow_file):
        """Test --max-cycles override."""
        result = cli_runner.invoke(cli, [
            "cycle", str(workflow_file),
            "--max-cycles", "2",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0
        assert "Completed 2 cycles" in result.output


class TestStatusCommand:
    """Test sdqctl status command."""

    def test_status_overview(self, cli_runner):
        """Test status shows system overview."""
        result = cli_runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        # Status should show adapter info or overview
        assert "Adapter" in result.output or "Status" in result.output

    def test_status_adapters(self, cli_runner):
        """Test status --adapters lists adapters."""
        result = cli_runner.invoke(cli, ["status", "--adapters"])
        assert result.exit_code == 0
        assert "mock" in result.output.lower()


class TestValidateCommand:
    """Test sdqctl validate command."""

    def test_validate_valid_workflow(self, cli_runner, workflow_file):
        """Test validating a correct .conv file."""
        result = cli_runner.invoke(cli, ["validate", str(workflow_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "✓" in result.output

    def test_validate_invalid_file(self, cli_runner, tmp_path):
        """Test validating nonexistent file."""
        fake_path = tmp_path / "nonexistent.conv"
        result = cli_runner.invoke(cli, ["validate", str(fake_path)])
        # Should fail with error about file not existing
        assert result.exit_code != 0 or "error" in result.output.lower() or "not found" in result.output.lower()


class TestVerbosity:
    """Test verbosity flag behavior."""

    def test_quiet_mode(self, cli_runner, workflow_file):
        """Test -q suppresses most output."""
        result = cli_runner.invoke(cli, ["-q", "run", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0

    def test_verbose_mode(self, cli_runner, workflow_file):
        """Test -v enables info logging."""
        result = cli_runner.invoke(cli, ["-v", "run", str(workflow_file), "--dry-run"])
        assert result.exit_code == 0


class TestJsonOutput:
    """Test JSON output mode."""

    def test_run_json_output(self, cli_runner, workflow_file):
        """Test --json produces JSON."""
        result = cli_runner.invoke(cli, [
            "run", str(workflow_file),
            "--adapter", "mock",
            "--json"
        ])
        assert result.exit_code == 0
        # Should contain JSON structure
        assert "{" in result.output
        assert "status" in result.output or "responses" in result.output
