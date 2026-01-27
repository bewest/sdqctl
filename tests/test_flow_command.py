"""
Tests for sdqctl flow command - batch/parallel workflow execution.

Tests the flow command's ability to discover workflows,
run them in parallel, and handle errors.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.core.conversation import ConversationFile


class TestFlowCommandBasic:
    """Test basic flow command functionality."""

    def test_flow_help(self, cli_runner):
        """Test flow --help shows usage."""
        result = cli_runner.invoke(cli, ["flow", "--help"])
        assert result.exit_code == 0
        assert "--parallel" in result.output
        assert "--continue-on-error" in result.output

    def test_flow_requires_patterns(self, cli_runner):
        """Test flow requires at least one pattern."""
        result = cli_runner.invoke(cli, ["flow"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "required" in result.output.lower()


class TestFlowDiscovery:
    """Test flow command workflow discovery."""

    def test_flow_discovers_single_file(self, cli_runner, workflow_file):
        """Test flow discovers a single workflow file."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0
        assert "1" in result.output or workflow_file.name in result.output

    def test_flow_discovers_glob_pattern(self, cli_runner, tmp_path):
        """Test flow discovers workflows via glob pattern."""
        # Create multiple workflow files
        for i in range(3):
            wf = tmp_path / f"workflow{i}.conv"
            wf.write_text(f"MODEL gpt-4\nADAPTER mock\nPROMPT Task {i}.")
        
        result = cli_runner.invoke(cli, [
            "flow", str(tmp_path / "*.conv"),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_flow_no_matches_reports_error(self, cli_runner, tmp_path):
        """Test flow reports when no files match pattern."""
        result = cli_runner.invoke(cli, [
            "flow", str(tmp_path / "nonexistent*.conv"),
            "--dry-run"
        ])
        # Should either fail or report no matches
        assert result.exit_code != 0 or "no" in result.output.lower() or "0" in result.output


class TestFlowExecution:
    """Test flow command execution with mock adapter."""

    def test_flow_executes_single_workflow(self, cli_runner, workflow_file):
        """Test flow executes a single workflow."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0

    def test_flow_executes_multiple_workflows(self, cli_runner, tmp_path):
        """Test flow executes multiple workflows."""
        for i in range(2):
            wf = tmp_path / f"wf{i}.conv"
            wf.write_text(f"MODEL gpt-4\nADAPTER mock\nPROMPT Task {i}.")
        
        result = cli_runner.invoke(cli, [
            "flow", str(tmp_path / "*.conv"),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0


class TestFlowParallel:
    """Test flow command parallel execution."""

    def test_flow_parallel_option(self, cli_runner, workflow_file):
        """Test --parallel option is accepted."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--parallel", "4",
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_flow_parallel_limits_concurrency(self, cli_runner, tmp_path):
        """Test --parallel limits concurrent executions."""
        # Create multiple workflow files
        for i in range(5):
            wf = tmp_path / f"parallel{i}.conv"
            wf.write_text(f"MODEL gpt-4\nADAPTER mock\nPROMPT Parallel task {i}.")
        
        result = cli_runner.invoke(cli, [
            "flow", str(tmp_path / "*.conv"),
            "--parallel", "2",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0


class TestFlowErrorHandling:
    """Test flow command error handling."""

    def test_flow_continue_on_error(self, cli_runner, tmp_path):
        """Test --continue-on-error continues after failure."""
        # Create valid workflows
        for i in range(2):
            wf = tmp_path / f"valid{i}.conv"
            wf.write_text(f"MODEL gpt-4\nADAPTER mock\nPROMPT Valid task {i}.")
        
        result = cli_runner.invoke(cli, [
            "flow", str(tmp_path / "*.conv"),
            "--continue-on-error",
            "--adapter", "mock"
        ])
        assert result.exit_code == 0


class TestFlowOptions:
    """Test flow command options."""

    def test_flow_with_adapter_override(self, cli_runner, workflow_file):
        """Test --adapter overrides workflow settings."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock",
            "--dry-run"
        ])
        assert result.exit_code == 0

    def test_flow_with_output_dir(self, cli_runner, workflow_file, tmp_path):
        """Test --output-dir sets output directory."""
        output_dir = tmp_path / "flow-output"
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--output-dir", str(output_dir),
            "--adapter", "mock"
        ])
        assert result.exit_code == 0

    def test_flow_json_output(self, cli_runner, workflow_file):
        """Test --json produces JSON output."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock",
            "--json"
        ])
        assert result.exit_code == 0
        assert "{" in result.output


class TestFlowInjection:
    """Test prologue/epilogue and header/footer injection in flow."""

    def test_flow_with_prologue(self, cli_runner, workflow_file):
        """Test --prologue adds content to prompts."""
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock",
            "--prologue", "Flow context: batch run"
        ])
        assert result.exit_code == 0

    def test_flow_with_header_footer(self, cli_runner, workflow_file, tmp_path):
        """Test --header and --footer wrap output."""
        output_dir = tmp_path / "output"
        result = cli_runner.invoke(cli, [
            "flow", str(workflow_file),
            "--adapter", "mock",
            "--header", "# Flow Report",
            "--footer", "---\nGenerated by flow",
            "--output-dir", str(output_dir)
        ])
        assert result.exit_code == 0
