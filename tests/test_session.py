"""
Tests for Session management - sdqctl/core/session.py

P0 Critical - Session lifecycle tests.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sdqctl.core.session import Session, SessionState, Message, Checkpoint, ExecutionContext
from sdqctl.core.conversation import ConversationFile


class TestSessionInitialization:
    """Session creation and state tests."""

    def test_session_initialization(self, sample_conv_content):
        """Test session ID generation and state initialization."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        # ID should be generated (8 chars)
        assert len(session.id) == 8
        
        # State should be initialized
        assert session.state.status == "pending"
        assert session.state.cycle_number == 0
        assert session.state.prompt_index == 0
        assert len(session.state.messages) == 0
        
        # Conversation should be stored
        assert session.conversation.model == "gpt-4"

    def test_session_with_custom_dir(self, tmp_path, sample_conv_content):
        """Test session with custom session directory."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path / "my-session")
        
        assert session.session_dir == tmp_path / "my-session"

    def test_session_context_loaded(self, temp_workspace, sample_conv_content):
        """Test context files are loaded during initialization."""
        content = f"""MODEL gpt-4
ADAPTER mock
CWD {temp_workspace}
CONTEXT @lib/*.js
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Context files should be loaded
        assert len(session.context.files) >= 2  # auth.js, utils.js, secret.js


class TestMessageManagement:
    """Tests for adding messages and tracking tokens."""

    def test_add_message(self, sample_conv_content):
        """Test adding messages to session."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        msg = session.add_message("user", "Hello, world!")
        
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert len(session.state.messages) == 1

    def test_add_message_tracks_tokens(self, sample_conv_content):
        """Test that adding messages updates token count."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        initial_tokens = session.context.conversation_tokens
        session.add_message("user", "A" * 400)  # ~100 tokens
        
        assert session.context.conversation_tokens > initial_tokens

    def test_add_message_with_metadata(self, sample_conv_content):
        """Test adding messages with metadata."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        msg = session.add_message("assistant", "Response", prompt_index=0)
        
        assert msg.metadata.get("prompt_index") == 0


class TestPromptNavigation:
    """Tests for prompt/cycle advancement."""

    def test_get_current_prompt(self):
        """Test getting current prompt."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First prompt.
PROMPT Second prompt.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        assert session.get_current_prompt() == "First prompt."

    def test_get_current_prompt_none_when_done(self):
        """Test None returned when all prompts exhausted."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Only prompt.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        session.state.prompt_index = 1  # Past end
        assert session.get_current_prompt() is None

    def test_advance_prompt(self):
        """Test advancing to next prompt."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First.
PROMPT Second.
PROMPT Third.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        assert session.state.prompt_index == 0
        
        has_more = session.advance_prompt()
        assert has_more is True
        assert session.state.prompt_index == 1
        
        has_more = session.advance_prompt()
        assert has_more is True
        assert session.state.prompt_index == 2
        
        has_more = session.advance_prompt()
        assert has_more is False
        assert session.state.prompt_index == 3

    def test_advance_cycle(self):
        """Test advancing to next cycle."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES 3
PROMPT Prompt.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Complete first prompt
        session.state.prompt_index = 1
        
        has_more = session.advance_cycle()
        assert has_more is True
        assert session.state.cycle_number == 1
        assert session.state.prompt_index == 0  # Reset
        
        session.advance_cycle()
        has_more = session.advance_cycle()
        assert has_more is False  # At max


class TestCheckpointPolicy:
    """Tests for checkpoint triggering policy."""

    def test_should_checkpoint_each_cycle(self):
        """Test each-cycle checkpoint policy."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES 2
CHECKPOINT-AFTER each-cycle
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Should not checkpoint at start of first cycle
        assert session.should_checkpoint() is False
        
        # Advance to second cycle
        session.state.cycle_number = 1
        session.state.prompt_index = 0
        assert session.should_checkpoint() is True
        
        # Should not checkpoint mid-cycle
        session.state.prompt_index = 1
        assert session.should_checkpoint() is False

    def test_should_checkpoint_each_prompt(self):
        """Test each-prompt checkpoint policy."""
        content = """MODEL gpt-4
ADAPTER mock
CHECKPOINT-AFTER each-prompt
PROMPT First.
PROMPT Second.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Should always checkpoint when policy is each-prompt
        assert session.should_checkpoint() is True
        session.advance_prompt()
        assert session.should_checkpoint() is True

    def test_should_checkpoint_never(self):
        """Test never checkpoint policy."""
        content = """MODEL gpt-4
ADAPTER mock
CHECKPOINT-AFTER never
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        assert session.should_checkpoint() is False

    def test_should_checkpoint_no_policy(self):
        """Test default behavior when no policy specified."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # No policy = no checkpoint
        assert session.should_checkpoint() is False


class TestCheckpointCreation:
    """Tests for checkpoint creation and saving."""

    def test_create_checkpoint(self, tmp_path, sample_conv_content):
        """Test checkpoint creation with correct data."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path)
        
        # Add some messages
        session.add_message("user", "First message")
        session.add_message("assistant", "Response")
        
        checkpoint = session.create_checkpoint("test-checkpoint")
        
        assert checkpoint.name == "test-checkpoint"
        assert len(checkpoint.messages) == 2
        assert checkpoint.cycle_number == 0
        assert len(session.state.checkpoints) == 1

    def test_checkpoint_saved_to_disk(self, tmp_path, sample_conv_content):
        """Test checkpoint is saved to disk."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path)
        
        checkpoint = session.create_checkpoint("disk-test")
        
        # Check file exists
        checkpoint_files = list(tmp_path.glob("checkpoint-*.json"))
        assert len(checkpoint_files) == 1
        
        # Verify content
        data = json.loads(checkpoint_files[0].read_text())
        assert data["name"] == "disk-test"

    def test_checkpoint_uses_conversation_name(self, tmp_path, sample_conv_content):
        """Test checkpoint uses CHECKPOINT-NAME if set."""
        content = """MODEL gpt-4
ADAPTER mock
CHECKPOINT-NAME my-workflow
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv, session_dir=tmp_path)
        
        checkpoint = session.create_checkpoint()
        assert checkpoint.name == "my-workflow"


class TestPauseCheckpoint:
    """Tests for PAUSE checkpoint save/load."""

    def test_save_pause_checkpoint(self, tmp_path, sample_conv_content):
        """Test pause checkpoint saved to disk."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path)
        
        # Add message and set state
        session.add_message("user", "Question")
        session.state.prompt_index = 1
        
        pause_file = session.save_pause_checkpoint("Please review before continuing")
        
        assert pause_file.exists()
        assert pause_file.name == "pause.json"
        
        data = json.loads(pause_file.read_text())
        assert data["type"] == "pause"
        assert data["message"] == "Please review before continuing"
        assert len(data["messages"]) == 1

    def test_load_from_pause(self, tmp_path, sample_conv_content):
        """Test session restored from pause checkpoint."""
        # Create and save original session
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path)
        session.add_message("user", "Question")
        session.add_message("assistant", "Answer")
        session.state.cycle_number = 1
        session.state.prompt_index = 2
        
        pause_file = session.save_pause_checkpoint("Review time")
        
        # Load from checkpoint
        restored = Session.load_from_pause(pause_file)
        
        assert restored.id == session.id
        assert restored.state.cycle_number == 1
        assert restored.state.prompt_index == 2
        assert restored.state.status == "resumed"
        assert len(restored.state.messages) == 2

    def test_load_from_pause_with_inline_conv(self, tmp_path):
        """Test loading when conversation was inline (no source file)."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Inline prompt.
"""
        conv = ConversationFile.parse(content)  # No source_path
        session = Session(conv, session_dir=tmp_path)
        
        pause_file = session.save_pause_checkpoint("Paused")
        
        # Should include inline content
        data = json.loads(pause_file.read_text())
        assert data["conversation_inline"] is not None
        
        # Load should work
        restored = Session.load_from_pause(pause_file)
        assert restored.conversation.model == "gpt-4"

    def test_load_from_pause_preserves_consulting_status(self, tmp_path, sample_conv_content):
        """Test that 'consulting' status is preserved through checkpoint."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv, session_dir=tmp_path)
        session.state.status = "consulting"  # Set consulting status (as CONSULT does)
        
        pause_file = session.save_pause_checkpoint("CONSULT: Design Decisions")
        
        # Verify checkpoint contains status
        data = json.loads(pause_file.read_text())
        assert data["status"] == "consulting"
        
        # Load should preserve consulting status
        restored = Session.load_from_pause(pause_file)
        assert restored.state.status == "consulting"


class TestReloadContext:
    """Tests for CONTEXT file reloading (fresh mode support)."""

    def test_reload_context_clears_and_reloads(self, temp_workspace):
        """Test reload_context clears files and re-reads from disk."""
        content = f"""MODEL gpt-4
ADAPTER mock
CWD {temp_workspace}
CONTEXT @lib/auth.js
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Initial load should have the file
        assert len(session.context.files) == 1
        assert "function login()" in session.context.files[0].content
        
        # Modify the file on disk
        (temp_workspace / "lib" / "auth.js").write_text("function newAuth() { return 'changed'; }")
        
        # Reload should pick up the change
        session.reload_context()
        
        assert len(session.context.files) == 1
        assert "function newAuth" in session.context.files[0].content
        assert "changed" in session.context.files[0].content

    def test_reload_context_preserves_conversation_tokens(self, temp_workspace):
        """Test reload_context doesn't reset conversation token count."""
        content = f"""MODEL gpt-4
ADAPTER mock
CWD {temp_workspace}
CONTEXT @lib/auth.js
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Simulate conversation activity
        session.add_message("user", "Hello world")
        session.add_message("assistant", "Hi there, how can I help?")
        conv_tokens_before = session.context.conversation_tokens
        
        # Reload context
        session.reload_context()
        
        # Conversation tokens should be preserved
        assert session.context.conversation_tokens == conv_tokens_before


class TestCompaction:
    """Tests for compaction triggers and prompts."""

    def test_needs_compaction(self, sample_conv_content):
        """Test compaction trigger check."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        # Initially should not need compaction
        assert session.needs_compaction() is False
        
        # Simulate high token usage
        session.context.window.used_tokens = int(session.context.window.max_tokens * 0.85)
        assert session.needs_compaction() is True

    def test_needs_compaction_min_density(self, sample_conv_content):
        """Test min_density parameter skips compaction when below threshold."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        # Simulate 50% usage - above default threshold (80%)
        session.context.window.used_tokens = int(session.context.window.max_tokens * 0.50)
        
        # Without min_density, no compaction needed (below 80%)
        assert session.needs_compaction() is False
        
        # Now simulate 85% usage - above threshold
        session.context.window.used_tokens = int(session.context.window.max_tokens * 0.85)
        
        # Without min_density, needs compaction
        assert session.needs_compaction() is True
        
        # With min_density=90, skip because usage (85%) < min (90%)
        assert session.needs_compaction(min_density=90) is False
        
        # With min_density=80, compact because usage (85%) >= min (80%)
        assert session.needs_compaction(min_density=80) is True
        
        # With min_density=50, compact because usage (85%) >= min (50%)
        assert session.needs_compaction(min_density=50) is True

    def test_get_compaction_prompt_default(self, sample_conv_content):
        """Test compaction prompt generation with defaults."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        prompt = session.get_compaction_prompt()
        
        assert "Compact" in prompt or "compact" in prompt
        assert "PRESERVE" in prompt

    def test_get_compaction_prompt_with_preserve(self):
        """Test compaction prompt includes preserve items."""
        content = """MODEL gpt-4
ADAPTER mock
COMPACT-PRESERVE findings, recommendations, action items
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        prompt = session.get_compaction_prompt()
        
        assert "findings" in prompt
        assert "recommendations" in prompt
        assert "action items" in prompt

    def test_get_compaction_prompt_with_summary(self):
        """Test compaction prompt uses custom summary instruction."""
        content = """MODEL gpt-4
ADAPTER mock
COMPACT-SUMMARY Focus on security findings only.
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        prompt = session.get_compaction_prompt()
        
        assert "security findings" in prompt


class TestSessionStatus:
    """Tests for session status reporting."""

    def test_get_status(self, sample_conv_content):
        """Test status dictionary generation."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        status = session.get_status()
        
        assert status["id"] == session.id
        assert status["status"] == "pending"
        assert "cycle" in status
        assert "prompt" in status
        assert "context" in status
        assert status["adapter"] == "mock"
        assert status["model"] == "gpt-4"

    def test_to_dict(self, sample_conv_content):
        """Test full session serialization."""
        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        
        data = session.to_dict()
        
        assert data["id"] == session.id
        assert "state" in data
        assert "context" in data
        assert "checkpoints" in data


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_execution_context_creation(self, sample_conv_content):
        """Test ExecutionContext can be created with required fields."""
        from rich.console import Console
        from sdqctl.adapters.base import AdapterConfig

        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)

        # Create mock adapter and session
        mock_adapter = MagicMock()
        mock_adapter_session = MagicMock()
        mock_adapter_session.sdk_session_id = "test-session-id"

        adapter_config = AdapterConfig(model="gpt-4")

        ctx = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
            verbosity=1,
            console=Console(),
        )

        assert ctx.adapter == mock_adapter
        assert ctx.conv == conv
        assert ctx.verbosity == 1
        assert ctx.is_verbose is True
        assert ctx.is_debug is False

    def test_execution_context_verbosity_properties(self, sample_conv_content):
        """Test is_verbose and is_debug properties."""
        from rich.console import Console
        from sdqctl.adapters.base import AdapterConfig

        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        mock_adapter = MagicMock()
        mock_adapter_session = MagicMock()
        adapter_config = AdapterConfig(model="gpt-4")

        # Verbosity 0: quiet
        ctx0 = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
            verbosity=0,
        )
        assert ctx0.is_verbose is False
        assert ctx0.is_debug is False

        # Verbosity 1: verbose
        ctx1 = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
            verbosity=1,
        )
        assert ctx1.is_verbose is True
        assert ctx1.is_debug is False

        # Verbosity 2: debug
        ctx2 = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
            verbosity=2,
        )
        assert ctx2.is_verbose is True
        assert ctx2.is_debug is True

    def test_execution_context_default_console(self, sample_conv_content):
        """Test ExecutionContext creates default Console if not provided."""
        from rich.console import Console
        from sdqctl.adapters.base import AdapterConfig

        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        mock_adapter = MagicMock()
        mock_adapter_session = MagicMock()
        adapter_config = AdapterConfig(model="gpt-4")

        ctx = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
        )

        assert isinstance(ctx.console, Console)

    def test_execution_context_json_errors_flag(self, sample_conv_content):
        """Test json_errors flag is stored correctly."""
        from sdqctl.adapters.base import AdapterConfig

        conv = ConversationFile.parse(sample_conv_content)
        session = Session(conv)
        mock_adapter = MagicMock()
        mock_adapter_session = MagicMock()
        adapter_config = AdapterConfig(model="gpt-4")

        ctx = ExecutionContext(
            adapter=mock_adapter,
            adapter_config=adapter_config,
            adapter_session=mock_adapter_session,
            session=session,
            conv=conv,
            json_errors=True,
        )

        assert ctx.json_errors is True
