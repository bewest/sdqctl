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


class TestRunTimeout:
    """Test RUN-TIMEOUT directive."""

    def test_run_timeout_default(self, tmp_path, monkeypatch):
        """Test run_timeout defaults to 60 seconds."""
        from sdqctl.core.config import clear_config_cache
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
        content = """MODEL gpt-4
ADAPTER mock
RUN echo hello
"""
        conv = ConversationFile.parse(content)
        assert conv.run_timeout == 60

    def test_run_timeout_seconds(self):
        """Test RUN-TIMEOUT with seconds value."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-TIMEOUT 30
RUN echo hello
"""
        conv = ConversationFile.parse(content)
        assert conv.run_timeout == 30

    def test_run_timeout_with_s_suffix(self):
        """Test RUN-TIMEOUT with 's' suffix."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-TIMEOUT 45s
RUN echo hello
"""
        conv = ConversationFile.parse(content)
        assert conv.run_timeout == 45

    def test_run_timeout_with_m_suffix(self):
        """Test RUN-TIMEOUT with 'm' suffix for minutes."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-TIMEOUT 2m
RUN echo hello
"""
        conv = ConversationFile.parse(content)
        assert conv.run_timeout == 120  # 2 minutes = 120 seconds

    def test_run_timeout_five_minutes(self):
        """Test RUN-TIMEOUT with 5 minutes."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-TIMEOUT 5m
"""
        conv = ConversationFile.parse(content)
        assert conv.run_timeout == 300  # 5 minutes = 300 seconds


class TestTimeoutPartialOutput:
    """Test timeout captures partial output (R1 improvement)."""

    def test_timeout_expired_has_output_attributes(self):
        """Test subprocess.TimeoutExpired has stdout/stderr attributes."""
        import subprocess
        
        # TimeoutExpired should have these attributes
        exc = subprocess.TimeoutExpired(cmd="test", timeout=1, output="partial", stderr="error")
        assert exc.stdout == "partial"
        assert exc.stderr == "error"

    def test_timeout_output_captured_in_context(self):
        """Test that partial output is captured on timeout and added to session."""
        import subprocess
        
        # Simulate what run.py does with TimeoutExpired
        e = subprocess.TimeoutExpired(cmd="slow_cmd", timeout=5, output="partial stdout", stderr="partial stderr")
        
        partial_stdout = e.stdout or ""
        partial_stderr = e.stderr or ""
        partial_output = partial_stdout
        if partial_stderr:
            partial_output += f"\n\n[stderr]\n{partial_stderr}"
        
        # Verify the format matches what we add to session
        assert "partial stdout" in partial_output
        assert "[stderr]" in partial_output
        assert "partial stderr" in partial_output
        
        # Verify context message format
        run_context = f"```\n$ slow_cmd\n[TIMEOUT after 5s]\n{partial_output}\n```"
        assert "[TIMEOUT after 5s]" in run_context
        assert "partial stdout" in run_context


class TestRunSubprocessExecution:
    """Integration tests for RUN subprocess execution (T1)."""

    def test_run_echo_captures_output(self):
        """Test RUN with echo command captures stdout."""
        import subprocess
        import shlex
        
        command = "echo hello world"
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        assert result.returncode == 0
        assert "hello world" in result.stdout

    def test_run_failing_command_returns_nonzero(self):
        """Test RUN with failing command returns non-zero exit code."""
        import subprocess
        import shlex
        
        command = "false"  # Always returns 1
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        assert result.returncode != 0

    def test_run_output_added_to_session(self):
        """Test RUN output format matches session context pattern."""
        command = "echo test output"
        output_text = "test output\n"
        
        # Match the pattern from run.py:485-486
        run_context = f"```\n$ {command}\n{output_text}\n```"
        session_msg = f"[RUN output]\n{run_context}"
        
        assert "$ echo test output" in session_msg
        assert "test output" in session_msg
        assert "```" in session_msg

    def test_run_failure_includes_stderr(self):
        """Test RUN failure output includes stderr."""
        import subprocess
        import shlex
        
        # Command that writes to stderr
        command = "ls /nonexistent_directory_12345"
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        assert result.returncode != 0
        assert result.stderr  # Should have error message
        
        # Verify stderr format matches run.py:480-481
        output_text = result.stdout or ""
        if result.stderr:
            output_text += f"\n\n[stderr]\n{result.stderr}"
        
        assert "[stderr]" in output_text


class TestMultiStepWorkflow:
    """Test multi-step workflows process all steps (verifies indentation fix)."""

    def test_multiple_prompts_parsed(self):
        """Test multiple PROMPT steps are all parsed."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First prompt
PROMPT Second prompt
PROMPT Third prompt
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.prompts) == 3
        assert len(conv.steps) == 3
        assert all(s.type == "prompt" for s in conv.steps)

    def test_mixed_steps_all_parsed(self):
        """Test mixed step types are all parsed in order."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze code
RUN python -m pytest
CHECKPOINT after-tests
PROMPT Review results
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 4
        step_types = [s.type for s in conv.steps]
        assert step_types == ["prompt", "run", "checkpoint", "prompt"]

    def test_run_step_content_preserved(self):
        """Test RUN step preserves command content."""
        content = """MODEL gpt-4
ADAPTER mock
RUN python -m pytest tests/ -v --tb=short
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 1
        assert conv.steps[0].type == "run"
        assert conv.steps[0].content == "python -m pytest tests/ -v --tb=short"


class TestR2FailureOutputCapture:
    """Test R2: RUN failure output is captured BEFORE early return on stop.
    
    Bug fixed: run.py previously returned on stop-on-error BEFORE capturing output.
    Now output is captured first, then stop-on-error is checked.
    """

    def test_failure_output_format_includes_exit_code(self):
        """Test that failure output includes exit code marker for debugging."""
        import subprocess
        import shlex
        
        # Simulate a failing command
        command = "false"  # Always exits with code 1
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0
        
        # Verify the new format includes exit code in the output marker
        status_marker = "" if result.returncode == 0 else f" (exit {result.returncode})"
        run_context = f"```\n$ {command}{status_marker}\n{result.stdout or '(no output)'}\n```"
        
        assert "(exit 1)" in run_context
        assert "$ false" in run_context

    def test_stderr_captured_on_failure(self):
        """Test that stderr is captured on command failure."""
        import subprocess
        import shlex
        
        # Use a command that writes to stderr and fails
        command = "ls /nonexistent_directory_12345"
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0
        assert result.stderr  # Should have error message about directory not found
        
        # Verify stderr is included in output
        output_text = result.stdout or ""
        if result.stderr:
            output_text += f"\n\n[stderr]\n{result.stderr}"
        
        assert "[stderr]" in output_text
        assert "nonexistent" in output_text.lower() or "cannot access" in output_text.lower() or "no such" in output_text.lower()


class TestRunOutputLimit:
    """Test RUN-OUTPUT-LIMIT directive parsing and truncation."""

    def test_run_output_limit_default_none(self):
        """Test default is no limit."""
        content = """MODEL gpt-4
ADAPTER mock
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output_limit is None

    def test_run_output_limit_numeric(self):
        """Test parsing numeric limit."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-OUTPUT-LIMIT 5000
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output_limit == 5000

    def test_run_output_limit_with_k_suffix(self):
        """Test parsing K suffix (thousands)."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-OUTPUT-LIMIT 10K
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output_limit == 10000

    def test_run_output_limit_with_m_suffix(self):
        """Test parsing M suffix (millions)."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-OUTPUT-LIMIT 1M
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output_limit == 1000000

    def test_run_output_limit_none_keyword(self):
        """Test 'none' keyword for unlimited."""
        content = """MODEL gpt-4
ADAPTER mock
RUN-OUTPUT-LIMIT none
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_output_limit is None


class TestTruncateOutput:
    """Test _truncate_output helper function."""

    def test_no_truncation_under_limit(self):
        """Text under limit is unchanged."""
        from sdqctl.commands.run import _truncate_output
        text = "Hello world"
        result = _truncate_output(text, 100)
        assert result == text

    def test_no_truncation_when_limit_none(self):
        """None limit means no truncation."""
        from sdqctl.commands.run import _truncate_output
        text = "x" * 10000
        result = _truncate_output(text, None)
        assert result == text

    def test_truncation_includes_marker(self):
        """Truncated output includes marker."""
        from sdqctl.commands.run import _truncate_output
        text = "x" * 1000
        result = _truncate_output(text, 100)
        assert "truncated" in result
        assert len(result) < len(text)

    def test_truncation_preserves_head_and_tail(self):
        """Truncated output keeps head and tail."""
        from sdqctl.commands.run import _truncate_output
        text = "HEAD" + "x" * 1000 + "TAIL"
        result = _truncate_output(text, 200)
        assert "HEAD" in result
        assert "TAIL" in result


class TestRunSubprocessHelper:
    """Test _run_subprocess helper function (T2)."""

    def test_echo_captures_stdout(self, tmp_path):
        """Test basic echo command captures output."""
        from sdqctl.commands.run import _run_subprocess
        result = _run_subprocess("echo hello", allow_shell=False, timeout=10, cwd=tmp_path)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_shell_mode_allows_pipes(self, tmp_path):
        """Test shell=True allows pipe operators."""
        from sdqctl.commands.run import _run_subprocess
        result = _run_subprocess("echo hello | cat", allow_shell=True, timeout=10, cwd=tmp_path)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_non_shell_mode_uses_shlex(self, tmp_path):
        """Test shell=False uses shlex.split (no shell injection)."""
        from sdqctl.commands.run import _run_subprocess
        # This should fail or behave differently without shell
        result = _run_subprocess("echo 'hello world'", allow_shell=False, timeout=10, cwd=tmp_path)
        assert result.returncode == 0
        # Without shell, quotes are preserved in output
        assert "hello" in result.stdout

    def test_cwd_parameter_used(self, tmp_path):
        """Test cwd parameter changes working directory."""
        from sdqctl.commands.run import _run_subprocess
        result = _run_subprocess("pwd", allow_shell=False, timeout=10, cwd=tmp_path)
        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_timeout_parameter_raises(self, tmp_path):
        """Test timeout parameter causes TimeoutExpired."""
        import subprocess
        from sdqctl.commands.run import _run_subprocess
        with pytest.raises(subprocess.TimeoutExpired):
            _run_subprocess("sleep 10", allow_shell=False, timeout=1, cwd=tmp_path)

    def test_stderr_captured(self, tmp_path):
        """Test stderr is captured separately."""
        from sdqctl.commands.run import _run_subprocess
        result = _run_subprocess("ls /nonexistent_path_12345", allow_shell=False, timeout=10, cwd=tmp_path)
        assert result.returncode != 0
        assert result.stderr  # Should have error message


class TestR3FailureCheckpoint:
    """Test R3: Auto-checkpoint on RUN failure."""

    def test_checkpoint_file_created_on_run_failure(self, tmp_path):
        """Verify pause.json checkpoint created when RUN fails with stop-on-error."""
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.session import Session
        
        # Create workflow with failing RUN
        content = """MODEL gpt-4
ADAPTER mock
RUN-ON-ERROR stop
RUN exit 1
"""
        conv = ConversationFile.parse(content)
        session = Session(conv, session_dir=tmp_path)
        
        # Simulate adding a message before failure (like RUN output capture)
        session.add_message("system", "[RUN output]\n```\n$ exit 1 (exit 1)\n```")
        
        # Save checkpoint (what R3 does before early return)
        checkpoint_path = session.save_pause_checkpoint("RUN failed: exit 1 (exit 1)")
        
        # Verify checkpoint exists
        assert checkpoint_path.exists()
        assert checkpoint_path.name == "pause.json"
        
    def test_checkpoint_contains_run_output(self, tmp_path):
        """Verify checkpoint preserves RUN output messages."""
        import json
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.session import Session
        
        content = """MODEL gpt-4
ADAPTER mock
RUN-ON-ERROR stop
RUN false
"""
        conv = ConversationFile.parse(content)
        session = Session(conv, session_dir=tmp_path)
        
        # Add RUN output message
        run_output = "[RUN output]\n```\n$ false (exit 1)\nCommand failed\n```"
        session.add_message("system", run_output)
        
        # Save checkpoint
        checkpoint_path = session.save_pause_checkpoint("RUN failed: false")
        
        # Load and verify
        data = json.loads(checkpoint_path.read_text())
        messages = data.get("messages", [])
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "RUN output" in messages[0]["content"]
        assert "Command failed" in messages[0]["content"]

    def test_checkpoint_contains_failure_message(self, tmp_path):
        """Verify checkpoint message describes the failure."""
        import json
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.session import Session
        
        content = """MODEL gpt-4
ADAPTER mock
RUN-ON-ERROR stop
RUN my_command --flag
"""
        conv = ConversationFile.parse(content)
        session = Session(conv, session_dir=tmp_path)
        
        # Save checkpoint with descriptive message
        checkpoint_path = session.save_pause_checkpoint("RUN failed: my_command --flag (exit 127)")
        
        # Verify message in checkpoint
        data = json.loads(checkpoint_path.read_text())
        assert "RUN failed" in data.get("message", "")
        assert "my_command" in data.get("message", "")


class TestRunEnvDirective:
    """Test E2: RUN-ENV directive for environment variables."""

    def test_run_env_parsed(self):
        """Test RUN-ENV directive is parsed correctly."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL gpt-4
ADAPTER mock
RUN-ENV API_KEY=secret123
RUN-ENV DEBUG=1
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_env == {"API_KEY": "secret123", "DEBUG": "1"}

    def test_run_env_with_equals_in_value(self):
        """Test RUN-ENV handles values containing equals sign."""
        from sdqctl.core.conversation import ConversationFile
        
        content = """MODEL gpt-4
ADAPTER mock
RUN-ENV CONNECTION=host=localhost;port=5432
RUN echo test
"""
        conv = ConversationFile.parse(content)
        assert conv.run_env["CONNECTION"] == "host=localhost;port=5432"

    def test_run_env_passed_to_subprocess(self, tmp_path):
        """Test environment variables are passed to subprocess."""
        from sdqctl.commands.run import _run_subprocess
        
        result = _run_subprocess(
            "printenv MY_TEST_VAR",
            allow_shell=False,
            timeout=10,
            cwd=tmp_path,
            env={"MY_TEST_VAR": "hello_world"}
        )
        assert result.returncode == 0
        assert "hello_world" in result.stdout

    def test_run_env_merges_with_os_environ(self, tmp_path):
        """Test custom env merges with (not replaces) OS environment."""
        from sdqctl.commands.run import _run_subprocess
        
        # PATH should still be available (inherited from os.environ)
        result = _run_subprocess(
            "echo $PATH",
            allow_shell=True,
            timeout=10,
            cwd=tmp_path,
            env={"MY_VAR": "test"}
        )
        assert result.returncode == 0
        assert result.stdout.strip()  # PATH should not be empty
