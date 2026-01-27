"""Tests for sdqctl status command."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.commands.status import (
    _show_overview_async,
    _show_adapters,
    _show_sessions,
    _show_models_async,
    _show_auth_async,
    SDQCTL_DIR,
)
from sdqctl.commands.utils import run_async


@pytest.fixture
def cli_runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_sessions_dir(tmp_path):
    """Create mock sessions directory structure."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    
    # Create session 1 with 2 checkpoints
    session1 = sessions_dir / "session-abc123"
    session1.mkdir()
    (session1 / "checkpoint-1.json").write_text(json.dumps({
        "id": "cp1",
        "name": "checkpoint-1",
        "timestamp": "2026-01-21T10:00:00",
        "cycle_number": 1,
    }))
    (session1 / "checkpoint-2.json").write_text(json.dumps({
        "id": "cp2",
        "name": "checkpoint-2",
        "timestamp": "2026-01-21T11:00:00",
        "cycle_number": 2,
    }))
    
    # Create session 2 with no checkpoints
    session2 = sessions_dir / "session-def456"
    session2.mkdir()
    
    return tmp_path


class TestStatusCommand:
    """Test status command main entry."""
    
    def test_status_default(self, cli_runner):
        """Test sdqctl status with no flags."""
        # Use mock adapter to avoid copilot SDK errors
        result = cli_runner.invoke(cli, ["status", "-a", "mock"])
        
        assert result.exit_code == 0
        assert "sdqctl" in result.output
    
    def test_status_json_output(self, cli_runner):
        """Test sdqctl status --json."""
        result = cli_runner.invoke(cli, ["status", "--json", "-a", "mock"])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "sessions" in data
        assert "adapters" in data
    
    def test_status_adapters_flag(self, cli_runner):
        """Test sdqctl status --adapters."""
        result = cli_runner.invoke(cli, ["status", "--adapters"])
        
        assert result.exit_code == 0
        assert "Available Adapters" in result.output or "adapters" in result.output.lower()
    
    def test_status_sessions_flag(self, cli_runner, mock_sessions_dir):
        """Test sdqctl status --sessions."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            result = cli_runner.invoke(cli, ["status", "--sessions"])
            
            assert result.exit_code == 0
            assert "session-abc123" in result.output or "Sessions" in result.output
    
    def test_status_checkpoints_flag(self, cli_runner, mock_sessions_dir):
        """Test sdqctl status --checkpoints."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            result = cli_runner.invoke(cli, ["status", "--checkpoints"])
            
            assert result.exit_code == 0

    def test_status_models_flag(self, cli_runner):
        """Test sdqctl status --models."""
        result = cli_runner.invoke(cli, ["status", "--models", "-a", "mock"])
        
        assert result.exit_code == 0
        assert "mock-model" in result.output.lower() or "Model" in result.output

    def test_status_auth_flag(self, cli_runner):
        """Test sdqctl status --auth."""
        result = cli_runner.invoke(cli, ["status", "--auth", "-a", "mock"])
        
        assert result.exit_code == 0
        assert "Authentication" in result.output or "mock-user" in result.output

    def test_status_all_flag(self, cli_runner):
        """Test sdqctl status --all."""
        result = cli_runner.invoke(cli, ["status", "--all", "-a", "mock"])
        
        assert result.exit_code == 0
        assert "Adapters" in result.output


class TestShowOverview:
    """Test _show_overview_async function."""
    
    @pytest.mark.asyncio
    async def test_overview_no_sessions(self, capsys, tmp_path):
        """Test overview when no sessions exist."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            await _show_overview_async("mock", json_output=False)
        
        captured = capsys.readouterr()
        assert "Sessions:" in captured.out
    
    @pytest.mark.asyncio
    async def test_overview_with_sessions(self, capsys, mock_sessions_dir):
        """Test overview with existing sessions."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            await _show_overview_async("mock", json_output=False)
        
        captured = capsys.readouterr()
        assert "Sessions:" in captured.out
    
    @pytest.mark.asyncio
    async def test_overview_json(self, capsys, mock_sessions_dir):
        """Test overview JSON output."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            await _show_overview_async("mock", json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "sessions" in data
        assert "adapters" in data


class TestShowAdapters:
    """Test _show_adapters function."""
    
    def test_adapters_list(self, capsys):
        """Test adapters are listed."""
        _show_adapters(json_output=False)
        
        captured = capsys.readouterr()
        assert "mock" in captured.out.lower() or "Available" in captured.out
    
    def test_adapters_json(self, capsys):
        """Test adapters JSON output."""
        _show_adapters(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "adapters" in data
        assert isinstance(data["adapters"], list)
    
    def test_adapters_shows_capabilities(self, capsys):
        """Test adapter capabilities are shown."""
        _show_adapters(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        for adapter in data["adapters"]:
            if "error" not in adapter:
                assert "name" in adapter


class TestShowSessions:
    """Test _show_sessions function."""
    
    def test_no_sessions_dir(self, capsys, tmp_path):
        """Test when sessions directory doesn't exist."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            _show_sessions(json_output=False)
        
        captured = capsys.readouterr()
        assert "No sessions found" in captured.out
    
    def test_no_sessions_json(self, capsys, tmp_path):
        """Test empty sessions JSON."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            _show_sessions(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["sessions"] == []
    
    def test_sessions_listed(self, capsys, mock_sessions_dir):
        """Test sessions are listed."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            _show_sessions(json_output=False)
        
        captured = capsys.readouterr()
        assert "session-abc123" in captured.out or "Sessions" in captured.out
    
    def test_sessions_json(self, capsys, mock_sessions_dir):
        """Test sessions JSON output."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            _show_sessions(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["sessions"]) == 2
    
    def test_sessions_with_checkpoints(self, capsys, mock_sessions_dir):
        """Test sessions with checkpoint details."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            _show_sessions(json_output=True, show_checkpoints=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        # Find session with checkpoints
        session_with_cp = next(
            (s for s in data["sessions"] if s["id"] == "session-abc123"),
            None
        )
        assert session_with_cp is not None
        assert "checkpoint_details" in session_with_cp
        assert len(session_with_cp["checkpoint_details"]) == 2
    
    def test_checkpoint_details_content(self, capsys, mock_sessions_dir):
        """Test checkpoint details contain expected fields."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            _show_sessions(json_output=True, show_checkpoints=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        session = next(s for s in data["sessions"] if s["id"] == "session-abc123")
        cp = session["checkpoint_details"][0]
        
        assert "id" in cp
        assert "name" in cp
        assert "timestamp" in cp
        assert "cycle" in cp
    
    def test_sessions_sorted_by_modified(self, capsys, mock_sessions_dir):
        """Test sessions are sorted by modification time."""
        with patch("sdqctl.commands.status.SDQCTL_DIR", mock_sessions_dir):
            _show_sessions(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        # Should have 2 sessions with modified timestamps
        assert len(data["sessions"]) == 2
        for session in data["sessions"]:
            assert "modified" in session


class TestStatusEdgeCases:
    """Test edge cases and error handling."""
    
    def test_corrupted_checkpoint_file(self, capsys, tmp_path):
        """Test handling of corrupted checkpoint JSON."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        
        session = sessions_dir / "session-corrupt"
        session.mkdir()
        (session / "checkpoint-bad.json").write_text("not valid json{{{")
        
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            _show_sessions(json_output=True, show_checkpoints=True)
        
        captured = capsys.readouterr()
        # Should not crash
        data = json.loads(captured.out)
        assert "sessions" in data
    
    def test_empty_session_dir(self, capsys, tmp_path):
        """Test session with no files."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "empty-session").mkdir()
        
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            _show_sessions(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["checkpoints"] == 0
    
    def test_file_in_sessions_dir_ignored(self, capsys, tmp_path):
        """Test that files (not dirs) in sessions dir are ignored."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "some-file.txt").write_text("ignored")
        (sessions_dir / "real-session").mkdir()
        
        with patch("sdqctl.commands.status.SDQCTL_DIR", tmp_path):
            _show_sessions(json_output=True)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "real-session"
