"""
Tests for stop file existence check behavior.

When a stop file exists from a previous run, commands should refuse to
proceed until the user reviews and removes it.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from sdqctl.commands.iterate import iterate
from sdqctl.commands.run import run
from sdqctl.commands.apply import apply


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workflow(tmp_path):
    """Create a minimal workflow file."""
    workflow = tmp_path / "test.conv"
    workflow.write_text("""MODEL gpt-4
ADAPTER mock

---

Test prompt
""")
    return workflow


@pytest.fixture
def stop_file_content():
    """Standard stop file JSON content."""
    return {
        "reason": "Test stop - agent requested review",
        "needs_review": True,
        "test_id": "unit-test"
    }


class TestCycleStopFileCheck:
    """Test that iterate command checks for existing stop file."""

    def test_cycle_refuses_when_stop_file_exists(
        self, runner, temp_workflow, stop_file_content, tmp_path
    ):
        """Cycle should refuse to run when stop file exists."""
        nonce = "testcheck123"
        stop_file = tmp_path / f"STOPAUTOMATION-{nonce}.json"
        stop_file.write_text(json.dumps(stop_file_content))
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy workflow to isolated fs
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            # Create stop file in cwd
            stop_file_cwd = Path(f"STOPAUTOMATION-{nonce}.json")
            stop_file_cwd.write_text(json.dumps(stop_file_content))
            
            result = runner.invoke(iterate, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
            ])
            
            # Should show review required message
            assert "Review Required" in result.output or "Stop file exists" in result.output
            assert "STOPAUTOMATION-testcheck123.json" in result.output
            assert "Test stop - agent requested review" in result.output

    def test_cycle_proceeds_without_stop_file(self, runner, temp_workflow, tmp_path):
        """Cycle should proceed normally when no stop file exists."""
        nonce = "nofile12345"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            # No stop file - should proceed (will fail on adapter but that's ok)
            result = runner.invoke(iterate, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
                "--dry-run",
            ])
            
            # Should NOT show review required
            assert "Review Required" not in result.output
            assert "Stop file exists" not in result.output


class TestRunStopFileCheck:
    """Test that run command checks for existing stop file."""

    def test_run_refuses_when_stop_file_exists(
        self, runner, temp_workflow, stop_file_content, tmp_path
    ):
        """Run should refuse when stop file exists."""
        nonce = "runcheck1234"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            stop_file_cwd = Path(f"STOPAUTOMATION-{nonce}.json")
            stop_file_cwd.write_text(json.dumps(stop_file_content))
            
            result = runner.invoke(run, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
            ])
            
            assert "Review Required" in result.output or "Stop file exists" in result.output
            assert nonce in result.output

    def test_run_proceeds_without_stop_file(self, runner, temp_workflow, tmp_path):
        """Run should proceed normally when no stop file exists."""
        nonce = "runnofile12"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            result = runner.invoke(run, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
                "--dry-run",
            ])
            
            assert "Review Required" not in result.output


class TestApplyStopFileCheck:
    """Test that apply command checks for existing stop file."""

    def test_apply_refuses_when_stop_file_exists(
        self, runner, temp_workflow, stop_file_content, tmp_path
    ):
        """Apply should refuse when stop file exists."""
        nonce = "applycheck1"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            # Create a component to apply to
            component = Path("component.py")
            component.write_text("# test component")
            
            stop_file_cwd = Path(f"STOPAUTOMATION-{nonce}.json")
            stop_file_cwd.write_text(json.dumps(stop_file_content))
            
            result = runner.invoke(apply, [
                str(workflow_path),
                "--components", "*.py",
                f"--stop-file-nonce={nonce}",
            ])
            
            assert "Review Required" in result.output or "Stop file exists" in result.output

    def test_apply_proceeds_without_stop_file(self, runner, temp_workflow, tmp_path):
        """Apply should proceed normally when no stop file exists."""
        nonce = "applynofile"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            component = Path("component.py")
            component.write_text("# test component")
            
            result = runner.invoke(apply, [
                str(workflow_path),
                "--components", "*.py",
                f"--stop-file-nonce={nonce}",
                "--dry-run",
            ])
            
            assert "Review Required" not in result.output


class TestStopFileContentParsing:
    """Test that stop file content is correctly parsed and displayed."""

    def test_displays_reason_from_json(self, runner, temp_workflow, tmp_path):
        """Should display the reason field from stop file JSON."""
        nonce = "reasontest1"
        custom_reason = "Custom stop reason for testing display"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            stop_file = Path(f"STOPAUTOMATION-{nonce}.json")
            stop_file.write_text(json.dumps({
                "reason": custom_reason,
                "needs_review": True
            }))
            
            result = runner.invoke(iterate, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
            ])
            
            assert custom_reason in result.output

    def test_handles_invalid_json(self, runner, temp_workflow, tmp_path):
        """Should handle stop files with invalid JSON gracefully."""
        nonce = "badjsontest"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            workflow_path = Path("test.conv")
            workflow_path.write_text(temp_workflow.read_text())
            
            stop_file = Path(f"STOPAUTOMATION-{nonce}.json")
            stop_file.write_text("not valid json {{{")
            
            result = runner.invoke(iterate, [
                str(workflow_path),
                f"--stop-file-nonce={nonce}",
            ])
            
            # Should still detect and block, just can't show reason
            assert "Review Required" in result.output or "Stop file exists" in result.output
            assert "Could not read" in result.output or "Unknown" in result.output
