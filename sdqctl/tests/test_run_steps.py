"""Tests for run_steps module."""

import subprocess
import pytest
from unittest.mock import Mock, patch, AsyncMock

from sdqctl.commands.run_steps import (
    execute_run_step,
    execute_run_async_step,
    execute_run_wait_step,
)
from sdqctl.core.conversation import ConversationFile
from sdqctl.core.session import Session


class TestExecuteRunWaitStep:
    """Tests for RUN-WAIT step execution."""

    def test_run_wait_step(self):
        """Verify RUN-WAIT calls sleep with parsed duration."""
        step = Mock()
        step.content = "100ms"
        progress_fn = Mock()

        with patch("sdqctl.commands.run_steps.time") as mock_time:
            execute_run_wait_step(step, progress_fn)
            mock_time.sleep.assert_called_once_with(0.1)

        assert progress_fn.called


class TestExecuteRunAsyncStep:
    """Tests for RUN-ASYNC step execution."""

    def test_run_async_step_starts_background_process(self, tmp_path):
        """Verify RUN-ASYNC starts process and tracks it."""
        step = Mock()
        step.content = "echo test"

        conv = Mock(spec=ConversationFile)
        conv.run_cwd = None
        conv.cwd = str(tmp_path)
        conv.source_path = None
        conv.run_env = None
        conv.allow_shell = True
        conv.async_processes = []

        session = Mock(spec=Session)
        progress_fn = Mock()

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = Mock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc

            execute_run_async_step(step, conv, session, progress_fn)

            mock_popen.assert_called_once()
            assert len(conv.async_processes) == 1
            assert conv.async_processes[0] == ("echo test", mock_proc)
            session.add_message.assert_called_once()


class TestExecuteRunStep:
    """Tests for RUN step execution."""

    @pytest.mark.asyncio
    async def test_run_step_success(self, tmp_path):
        """Verify successful RUN step returns None (continue)."""
        step = Mock()
        step.content = "echo hello"
        step.retry_count = 0
        step.retry_prompt = ""
        step.on_failure = None
        step.on_success = None

        conv = Mock(spec=ConversationFile)
        conv.run_cwd = None
        conv.cwd = str(tmp_path)
        conv.source_path = None
        conv.run_env = None
        conv.allow_shell = True
        conv.run_output = "on-error"
        conv.run_output_limit = 10000

        session = Mock(spec=Session)
        ai_adapter = Mock()
        adapter_session = Mock()
        console = Mock()
        progress_fn = Mock()
        first_prompt = True

        def mock_run_subprocess(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            result.stdout = "hello"
            result.stderr = ""
            return result

        result = await execute_run_step(
            step, conv, session, ai_adapter, adapter_session,
            console, progress_fn, first_prompt, mock_run_subprocess
        )

        # None means continue execution
        assert result is None

    @pytest.mark.asyncio
    async def test_run_step_failure_stop_on_error(self, tmp_path):
        """Verify failing RUN step with stop-on-error returns False."""
        step = Mock()
        step.content = "exit 1"
        step.retry_count = 0
        step.retry_prompt = ""
        step.on_failure = None
        step.on_success = None

        conv = Mock(spec=ConversationFile)
        conv.run_cwd = None
        conv.cwd = str(tmp_path)
        conv.source_path = None
        conv.run_env = None
        conv.allow_shell = True
        conv.run_output = "on-error"
        conv.run_output_limit = 10000
        conv.run_on_error = "stop"

        session = Mock(spec=Session)
        session.state = Mock()
        session.save_pause_checkpoint = Mock(return_value="/tmp/ckpt")

        ai_adapter = Mock()
        adapter_session = Mock()
        console = Mock()
        progress_fn = Mock()
        first_prompt = True

        def mock_run_subprocess(cmd, **kwargs):
            result = Mock()
            result.returncode = 1
            result.stdout = ""
            result.stderr = "error"
            return result

        result = await execute_run_step(
            step, conv, session, ai_adapter, adapter_session,
            console, progress_fn, first_prompt, mock_run_subprocess
        )

        # False means stop execution
        assert result is False
        assert session.state.status == "failed"
