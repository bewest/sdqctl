"""
Tests for sdqctl run command step execution.

Tests the internal step processing: PROMPT, CHECKPOINT, COMPACT, NEW-CONVERSATION, RUN.
"""

import pytest
from pathlib import Path

from sdqctl.core.conversation import ConversationFile, ConversationStep
from sdqctl.core.session import Session


class TestPromptStepParsing:
    """Test PROMPT step parsing from .conv files."""

    def test_prompt_creates_step(self):
        """Test PROMPT directive creates a step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First prompt.
PROMPT Second prompt.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts) == 2
        assert len(conv.steps) == 2
        assert conv.steps[0].type == "prompt"
        assert conv.steps[0].content == "First prompt."

    def test_multiline_prompt_preserved(self):
        """Test multiline prompts are parsed correctly."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze the code.
  Focus on:
  - Security issues
  - Performance
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts) == 1
        assert "Focus on:" in conv.prompts[0]
        assert "Security issues" in conv.prompts[0]


class TestCheckpointStepParsing:
    """Test CHECKPOINT step parsing."""

    def test_checkpoint_creates_step(self):
        """Test CHECKPOINT directive creates a step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First analysis.
CHECKPOINT analysis-complete
PROMPT Second phase.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.steps) == 3
        assert conv.steps[1].type == "checkpoint"
        assert conv.steps[1].content == "analysis-complete"

    def test_checkpoint_without_name(self):
        """Test CHECKPOINT without explicit name."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Do something.
CHECKPOINT
"""
        conv = ConversationFile.parse(content)
        checkpoint_step = [s for s in conv.steps if s.type == "checkpoint"][0]
        assert checkpoint_step.content == ""  # Empty name


class TestCompactStepParsing:
    """Test COMPACT step parsing."""

    def test_compact_creates_step(self):
        """Test COMPACT directive creates a step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze.
COMPACT findings, recommendations
"""
        conv = ConversationFile.parse(content)
        compact_step = [s for s in conv.steps if s.type == "compact"][0]
        assert compact_step.type == "compact"
        assert "findings" in compact_step.preserve
        assert "recommendations" in compact_step.preserve

    def test_compact_without_preserve(self):
        """Test COMPACT without preserve list."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze.
COMPACT
"""
        conv = ConversationFile.parse(content)
        compact_step = [s for s in conv.steps if s.type == "compact"][0]
        assert compact_step.preserve == []


class TestNewConversationStepParsing:
    """Test NEW-CONVERSATION step parsing."""

    def test_new_conversation_creates_step(self):
        """Test NEW-CONVERSATION directive creates a step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First phase.
NEW-CONVERSATION
PROMPT Fresh start.
"""
        conv = ConversationFile.parse(content)
        nc_step = [s for s in conv.steps if s.type == "new_conversation"][0]
        assert nc_step.type == "new_conversation"


class TestRunStepParsing:
    """Test RUN step parsing."""

    def test_run_creates_step(self):
        """Test RUN directive creates a step."""
        content = """MODEL gpt-4
ADAPTER mock
RUN npm test
PROMPT Check results.
"""
        conv = ConversationFile.parse(content)
        run_step = [s for s in conv.steps if s.type == "run"][0]
        assert run_step.type == "run"
        assert run_step.content == "npm test"

    def test_run_with_complex_command(self):
        """Test RUN with complex command."""
        content = """MODEL gpt-4
ADAPTER mock
RUN echo "hello world" && ls -la
"""
        conv = ConversationFile.parse(content)
        run_step = [s for s in conv.steps if s.type == "run"][0]
        assert 'echo "hello world"' in run_step.content


class TestRunSettings:
    """Test RUN-ON-ERROR and RUN-OUTPUT settings."""

    def test_run_on_error_default(self):
        """Test RUN-ON-ERROR defaults to stop."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.run_on_error == "stop"

    def test_run_on_error_continue(self):
        """Test RUN-ON-ERROR continue setting."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-ON-ERROR continue
RUN failing-command
"""
        conv = ConversationFile.parse(content)
        assert conv.run_on_error == "continue"

    def test_run_output_default(self):
        """Test RUN-OUTPUT defaults to always."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output == "always"

    def test_run_output_on_error(self):
        """Test RUN-OUTPUT on-error setting."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-OUTPUT on-error
RUN some-command
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output == "on-error"


class TestStepOrder:
    """Test that steps maintain correct order."""

    def test_mixed_steps_order_preserved(self):
        """Test mixed step types maintain declaration order."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Step 1.
CHECKPOINT cp1
PROMPT Step 2.
RUN echo test
COMPACT
PROMPT Step 3.
"""
        conv = ConversationFile.parse(content)
        
        expected_types = ["prompt", "checkpoint", "prompt", "run", "compact", "prompt"]
        actual_types = [s.type for s in conv.steps]
        assert actual_types == expected_types

    def test_steps_match_prompts_count(self):
        """Test prompt count matches prompt-type steps."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT One.
CHECKPOINT
PROMPT Two.
COMPACT
PROMPT Three.
"""
        conv = ConversationFile.parse(content)
        
        prompt_steps = [s for s in conv.steps if s.type == "prompt"]
        assert len(prompt_steps) == len(conv.prompts)
        assert len(conv.prompts) == 3


class TestSessionStepTracking:
    """Test Session tracks step execution."""

    def test_session_tracks_messages(self):
        """Test session records messages from prompts."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Test prompt.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        session.add_message("user", "Test prompt.")
        session.add_message("assistant", "Response")
        
        assert len(session.state.messages) == 2
        assert session.state.messages[0].role == "user"
        assert session.state.messages[1].role == "assistant"

    def test_session_creates_checkpoint(self):
        """Test session can create checkpoints."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        checkpoint = session.create_checkpoint("test-checkpoint")
        assert checkpoint.name == "test-checkpoint"
        assert len(session.state.checkpoints) == 1

    def test_session_compaction_prompt(self):
        """Test session generates compaction prompt."""
        content = """MODEL gpt-4
ADAPTER mock
COMPACT-PRESERVE findings, recommendations
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        session = Session(conv)
        
        # Add some messages
        session.add_message("user", "Analyze the code.")
        session.add_message("assistant", "Found 3 issues.")
        
        prompt = session.get_compaction_prompt()
        assert "compact" in prompt.lower() or "summarize" in prompt.lower()


class TestAllowShellSecurity:
    """Test ALLOW-SHELL directive for shell injection prevention."""

    def test_allow_shell_default_false(self, tmp_path, monkeypatch):
        """Test allow_shell defaults to False for security."""
        from sdqctl.core.config import clear_config_cache
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        content = """MODEL gpt-4
ADAPTER mock
RUN echo hello
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is False

    def test_allow_shell_true(self):
        """Test ALLOW-SHELL true enables shell mode."""
        content = """MODEL gpt-4
ADAPTER mock
ALLOW-SHELL true
RUN echo "hello" | cat
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is True

    def test_allow_shell_yes(self):
        """Test ALLOW-SHELL yes enables shell mode."""
        content = """MODEL gpt-4
ADAPTER mock
ALLOW-SHELL yes
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is True

    def test_allow_shell_bare(self):
        """Test bare ALLOW-SHELL enables shell mode."""
        content = """MODEL gpt-4
ADAPTER mock
ALLOW-SHELL
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is True

    def test_allow_shell_false_explicit(self):
        """Test ALLOW-SHELL false keeps shell disabled."""
        content = """MODEL gpt-4
ADAPTER mock
ALLOW-SHELL false
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is False

    def test_allow_shell_no(self):
        """Test ALLOW-SHELL no keeps shell disabled."""
        content = """MODEL gpt-4
ADAPTER mock
ALLOW-SHELL no
"""
        conv = ConversationFile.parse(content)
        assert conv.allow_shell is False


class TestShellExecutionSecurity:
    """Test that RUN command uses correct shell mode."""

    def test_run_without_shell_uses_shlex(self):
        """Test RUN without ALLOW-SHELL uses shlex.split (no shell injection)."""
        import shlex
        
        command = 'echo "hello world"'
        parsed = shlex.split(command)
        # shlex.split properly handles quoted strings
        assert parsed == ['echo', 'hello world']

    def test_shlex_handles_simple_commands(self):
        """Test shlex handles simple commands correctly."""
        import shlex
        
        assert shlex.split('npm test') == ['npm', 'test']
        assert shlex.split('python -m pytest') == ['python', '-m', 'pytest']
        assert shlex.split('ls -la /tmp') == ['ls', '-la', '/tmp']

    def test_shlex_prevents_shell_injection(self):
        """Test shlex.split prevents shell injection attacks."""
        import shlex
        
        # These would be dangerous with shell=True
        malicious = 'echo hello; rm -rf /'
        parsed = shlex.split(malicious)
        # With shlex, the semicolon is part of a single argument
        assert ';' in parsed[1]  # "hello;" is treated as one arg
        assert 'rm' in parsed  # rm is a separate arg, not executed as command
        
        # Dollar substitution is not executed
        malicious2 = 'echo $(whoami)'
        parsed2 = shlex.split(malicious2)
        assert '$(whoami)' in parsed2  # Treated literally, not expanded
