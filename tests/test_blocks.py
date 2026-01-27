"""Tests for blocks module - ON-FAILURE/ON-SUCCESS step execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sdqctl.commands.blocks import execute_block_steps
from sdqctl.core.conversation import ConversationStep


class TestExecuteBlockSteps:
    """Tests for execute_block_steps function."""

    @pytest.fixture
    def mock_context(self):
        """Create mock execution context."""
        conv = MagicMock()
        conv.cwd = None
        conv.allow_shell = False
        conv.run_timeout = 30
        conv.run_output_limit = 10000

        session = MagicMock()
        ai_adapter = AsyncMock()
        ai_adapter.send.return_value = "AI response"
        adapter_session = MagicMock()
        console = MagicMock()
        progress_fn = MagicMock()

        return {
            "conv": conv,
            "session": session,
            "ai_adapter": ai_adapter,
            "adapter_session": adapter_session,
            "console": console,
            "progress_fn": progress_fn,
            "first_prompt": True,
        }

    @pytest.mark.asyncio
    async def test_empty_steps_does_nothing(self, mock_context):
        await execute_block_steps([], **mock_context)
        mock_context["ai_adapter"].send.assert_not_called()

    @pytest.mark.asyncio
    async def test_prompt_step_sends_to_ai(self, mock_context):
        steps = [ConversationStep(type="prompt", content="Test prompt")]
        await execute_block_steps(steps, **mock_context)
        
        mock_context["ai_adapter"].send.assert_called_once()
        mock_context["session"].add_message.assert_called_with("assistant", "AI response")

    @pytest.mark.asyncio
    async def test_checkpoint_step_saves(self, mock_context):
        steps = [ConversationStep(type="checkpoint", content="test-checkpoint")]
        await execute_block_steps(steps, **mock_context)
        
        mock_context["session"].save_pause_checkpoint.assert_called_with("test-checkpoint")

    @pytest.mark.asyncio
    async def test_checkpoint_default_name(self, mock_context):
        steps = [ConversationStep(type="checkpoint", content="")]
        await execute_block_steps(steps, **mock_context)
        
        mock_context["session"].save_pause_checkpoint.assert_called_with("block-checkpoint")

    @pytest.mark.asyncio
    async def test_compact_step_summarizes(self, mock_context):
        steps = [ConversationStep(type="compact", content="")]
        await execute_block_steps(steps, **mock_context)
        
        mock_context["ai_adapter"].send.assert_called_once()
        # Check that compaction summary was added
        call_args = mock_context["session"].add_message.call_args
        assert "Compaction summary" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_run_step_executes_command(self, mock_context):
        steps = [ConversationStep(type="run", content="echo test")]
        
        with patch("sdqctl.commands.blocks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr=""
            )
            await execute_block_steps(steps, **mock_context)
            
            mock_run.assert_called_once()
            mock_context["progress_fn"].assert_called()

    @pytest.mark.asyncio
    async def test_run_step_handles_failure(self, mock_context):
        steps = [ConversationStep(type="run", content="false")]
        
        with patch("sdqctl.commands.blocks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error"
            )
            await execute_block_steps(steps, **mock_context)
            
            # Should still complete without raising
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_steps_execute_in_order(self, mock_context):
        steps = [
            ConversationStep(type="prompt", content="First"),
            ConversationStep(type="checkpoint", content="mid-point"),
            ConversationStep(type="prompt", content="Second"),
        ]
        await execute_block_steps(steps, **mock_context)
        
        assert mock_context["ai_adapter"].send.call_count == 2
        mock_context["session"].save_pause_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_step_prints_message(self, mock_context):
        steps = [ConversationStep(type="pause", content="")]
        
        with patch("builtins.input", return_value=""):
            await execute_block_steps(steps, **mock_context)
            
            mock_context["console"].print.assert_called()

    @pytest.mark.asyncio
    async def test_consult_step_prints_topic(self, mock_context):
        steps = [ConversationStep(type="consult", content="Review needed")]
        
        with patch("builtins.input", return_value=""):
            await execute_block_steps(steps, **mock_context)
            
            # Should print CONSULT message
            calls = [str(c) for c in mock_context["console"].print.call_args_list]
            assert any("CONSULT" in c for c in calls)
