"""Tests for resume command and checkpoint functionality.

Tests the integration between:
- Session.save_pause_checkpoint() (session.py:184-211)
- Session.load_from_pause() (session.py:213-250)
- Resume command (cli.py:454-560)
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sdqctl.core.conversation import ConversationFile
from sdqctl.core.session import Session, Message


class TestSavePauseCheckpoint:
    """Test Session.save_pause_checkpoint() creates valid checkpoint files."""
    
    def test_checkpoint_file_created(self, tmp_path):
        """Checkpoint file is created in session directory."""
        conv = ConversationFile(prompts=["Test prompt"])
        session = Session(conv, session_dir=tmp_path)
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        assert checkpoint_path.exists()
        assert checkpoint_path.name == "pause.json"
        assert checkpoint_path.parent == tmp_path
    
    def test_checkpoint_contains_message(self, tmp_path):
        """Checkpoint stores the pause message."""
        conv = ConversationFile(prompts=["Test prompt"])
        session = Session(conv, session_dir=tmp_path)
        
        checkpoint_path = session.save_pause_checkpoint("RUN failed: exit 1")
        data = json.loads(checkpoint_path.read_text())
        
        assert data["type"] == "pause"
        assert data["message"] == "RUN failed: exit 1"
    
    def test_checkpoint_contains_session_messages(self, tmp_path):
        """Checkpoint includes all session messages (including RUN output)."""
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2"])
        session = Session(conv, session_dir=tmp_path)
        
        # Simulate workflow execution with RUN output
        session.add_message("user", "Prompt 1")
        session.add_message("assistant", "Response 1")
        session.add_message("system", "[RUN output]\n```\n$ echo hello\nhello\n```")
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        data = json.loads(checkpoint_path.read_text())
        
        assert len(data["messages"]) == 3
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][2]["role"] == "system"
        assert "[RUN output]" in data["messages"][2]["content"]
    
    def test_checkpoint_contains_prompt_index(self, tmp_path):
        """Checkpoint stores prompt_index for resuming."""
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2", "Prompt 3"])
        session = Session(conv, session_dir=tmp_path)
        session.state.prompt_index = 2  # Failed after prompt 2
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        data = json.loads(checkpoint_path.read_text())
        
        assert data["prompt_index"] == 2
    
    def test_checkpoint_contains_cycle_number(self, tmp_path):
        """Checkpoint stores cycle_number for multi-cycle workflows."""
        conv = ConversationFile(prompts=["Prompt 1"], max_cycles=5)
        session = Session(conv, session_dir=tmp_path)
        session.state.cycle_number = 3
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        data = json.loads(checkpoint_path.read_text())
        
        assert data["cycle_number"] == 3


class TestLoadFromPause:
    """Test Session.load_from_pause() restores session state."""
    
    def test_load_restores_messages(self, tmp_path):
        """load_from_pause restores all messages from checkpoint."""
        # Create and save a session
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1\nPROMPT Prompt 2")
        
        session = Session(conv, session_dir=tmp_path)
        session.add_message("user", "Prompt 1")
        session.add_message("assistant", "Response 1")
        session.add_message("system", "[RUN output]\ntest output")
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        # Load the session
        restored = Session.load_from_pause(checkpoint_path)
        
        assert len(restored.state.messages) == 3
        assert restored.state.messages[0].content == "Prompt 1"
        assert restored.state.messages[1].content == "Response 1"
        assert "[RUN output]" in restored.state.messages[2].content
    
    def test_load_restores_prompt_index(self, tmp_path):
        """load_from_pause restores prompt_index for correct resume point."""
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2", "Prompt 3"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1\nPROMPT Prompt 2\nPROMPT Prompt 3")
        
        session = Session(conv, session_dir=tmp_path)
        session.state.prompt_index = 2
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        restored = Session.load_from_pause(checkpoint_path)
        
        assert restored.state.prompt_index == 2
    
    def test_load_restores_cycle_number(self, tmp_path):
        """load_from_pause restores cycle_number."""
        conv = ConversationFile(prompts=["Prompt 1"], max_cycles=5)
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1\nMAX-CYCLES 5")
        
        session = Session(conv, session_dir=tmp_path)
        session.state.cycle_number = 3
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        restored = Session.load_from_pause(checkpoint_path)
        
        assert restored.state.cycle_number == 3
    
    def test_load_sets_status_resumed(self, tmp_path):
        """load_from_pause sets status to 'resumed'."""
        conv = ConversationFile(prompts=["Prompt 1"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1")
        
        session = Session(conv, session_dir=tmp_path)
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        restored = Session.load_from_pause(checkpoint_path)
        
        assert restored.state.status == "resumed"
    
    def test_load_restores_session_id(self, tmp_path):
        """load_from_pause restores the original session ID."""
        conv = ConversationFile(prompts=["Prompt 1"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1")
        
        session = Session(conv, session_dir=tmp_path)
        original_id = session.id
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        restored = Session.load_from_pause(checkpoint_path)
        
        assert restored.id == original_id


class TestCheckpointRoundTrip:
    """Test full save/load cycle preserves RUN failure context."""
    
    def test_run_failure_output_preserved(self, tmp_path):
        """RUN failure output survives checkpoint round-trip."""
        conv = ConversationFile(prompts=["Analyze", "Fix"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Analyze\nPROMPT Fix")
        
        session = Session(conv, session_dir=tmp_path)
        
        # Simulate: prompt 1 completed, RUN failed before prompt 2
        session.add_message("user", "Analyze")
        session.add_message("assistant", "I found issues...")
        session.add_message(
            "system",
            "[RUN output]\n```\n$ pytest (exit 1)\nFailed: test_auth.py::test_login\n```"
        )
        session.state.prompt_index = 1  # Resume from prompt 2
        
        checkpoint_path = session.save_pause_checkpoint("RUN failed: pytest (exit 1)")
        
        # Load and verify
        restored = Session.load_from_pause(checkpoint_path)
        
        assert len(restored.state.messages) == 3
        assert "test_auth.py::test_login" in restored.state.messages[2].content
        assert restored.state.prompt_index == 1
        assert len(restored.conversation.prompts) == 2
        # Resume would start from prompts[1] = "Fix"
    
    def test_inline_conversation_preserved(self, tmp_path):
        """Inline conversation (no source file) is preserved."""
        conv = ConversationFile(prompts=["Test prompt"])
        # No source_path - inline conversation
        
        session = Session(conv, session_dir=tmp_path)
        session.add_message("user", "Test prompt")
        
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        # The checkpoint should contain conversation_inline
        data = json.loads(checkpoint_path.read_text())
        assert data["conversation_inline"] is not None
        assert "PROMPT Test prompt" in data["conversation_inline"]


class TestResumeListFlag:
    """Test resume --list flag functionality."""
    
    def test_list_checkpoints_empty_sessions_dir(self, tmp_path, monkeypatch):
        """--list handles missing sessions directory gracefully."""
        from sdqctl.commands.resume import _list_checkpoints
        from unittest.mock import MagicMock
        
        monkeypatch.chdir(tmp_path)  # No .sdqctl/sessions here
        console = MagicMock()
        
        _list_checkpoints(console, json_output=False)
        
        # Should print "No sessions directory found"
        console.print.assert_called()
    
    def test_list_checkpoints_json_empty(self, tmp_path, monkeypatch):
        """--list --json returns empty array for no checkpoints."""
        from sdqctl.commands.resume import _list_checkpoints
        from unittest.mock import MagicMock
        
        monkeypatch.chdir(tmp_path)
        console = MagicMock()
        
        _list_checkpoints(console, json_output=True)
        
        console.print_json.assert_called_with('{"checkpoints": []}')


class TestResumeDryRunFlag:
    """Test resume --dry-run flag functionality."""
    
    def test_dry_run_loads_checkpoint(self, tmp_path):
        """--dry-run loads and displays checkpoint without executing."""
        from sdqctl.commands.resume import _dry_run_resume
        from unittest.mock import MagicMock
        
        # Create a checkpoint
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1\nPROMPT Prompt 2")
        
        session = Session(conv, session_dir=tmp_path)
        session.state.prompt_index = 1
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        console = MagicMock()
        _dry_run_resume(str(checkpoint_path), console, json_output=False)
        
        # Should have printed a Panel
        console.print.assert_called()
    
    def test_dry_run_json_output(self, tmp_path):
        """--dry-run --json returns structured data."""
        import json as json_module
        from sdqctl.commands.resume import _dry_run_resume
        from unittest.mock import MagicMock
        
        # Create a checkpoint
        conv = ConversationFile(prompts=["Prompt 1", "Prompt 2"])
        conv.source_path = tmp_path / "test.conv"
        conv.source_path.write_text("PROMPT Prompt 1\nPROMPT Prompt 2")
        
        session = Session(conv, session_dir=tmp_path)
        session.state.prompt_index = 1
        checkpoint_path = session.save_pause_checkpoint("Test pause")
        
        console = MagicMock()
        _dry_run_resume(str(checkpoint_path), console, json_output=True)
        
        # Should have called print_json
        console.print_json.assert_called_once()
        call_args = console.print_json.call_args[0][0]
        result = json_module.loads(call_args)
        
        assert result["dry_run"] is True
        assert result["resume_from_prompt"] == 2
        assert result["total_prompts"] == 2
