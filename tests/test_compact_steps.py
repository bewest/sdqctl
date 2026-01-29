"""Tests for compact_steps module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from sdqctl.commands.compact_steps import (
    execute_compact_step,
    execute_checkpoint_step,
)


class TestExecuteCheckpointStep:
    """Tests for checkpoint step execution."""

    def test_checkpoint_with_name(self):
        """Verify checkpoint uses provided name."""
        step = Mock()
        step.content = "my-checkpoint"

        session = Mock()
        checkpoint = Mock()
        checkpoint.name = "my-checkpoint"
        session.create_checkpoint = Mock(return_value=checkpoint)

        console = Mock()
        progress = Mock()

        result = execute_checkpoint_step(step, session, 0, console, progress)

        session.create_checkpoint.assert_called_once_with("my-checkpoint")
        assert result == "my-checkpoint"

    def test_checkpoint_default_name(self):
        """Verify checkpoint generates default name from cycle."""
        step = Mock()
        step.content = ""

        session = Mock()
        checkpoint = Mock()
        checkpoint.name = "cycle-3-step"
        session.create_checkpoint = Mock(return_value=checkpoint)

        console = Mock()
        progress = Mock()

        result = execute_checkpoint_step(step, session, 3, console, progress)

        session.create_checkpoint.assert_called_once_with("cycle-3-step")
        assert result == "cycle-3-step"

    def test_checkpoint_outputs_to_console(self):
        """Verify checkpoint prints to console and progress."""
        step = Mock()
        step.content = "test"

        session = Mock()
        checkpoint = Mock()
        checkpoint.name = "test"
        session.create_checkpoint = Mock(return_value=checkpoint)

        console = Mock()
        progress = Mock()

        execute_checkpoint_step(step, session, 0, console, progress)

        console.print.assert_called_once()
        progress.assert_called_once()


class TestExecuteCompactStep:
    """Tests for compact step execution."""

    @pytest.mark.asyncio
    async def test_compact_skipped_below_threshold(self):
        """Verify compaction skipped when below threshold."""
        step = Mock()
        conv = Mock()
        session = Mock()
        session.needs_compaction = Mock(return_value=False)

        ai_adapter = AsyncMock()
        adapter_session = Mock()
        console = Mock()
        progress = Mock()

        result = await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress
        )

        assert result is False
        ai_adapter.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_compact_executed_above_threshold(self):
        """Verify compaction runs when above threshold."""
        step = Mock()
        step.preserve = []

        conv = Mock()
        conv.compact_preserve = []

        session = Mock()
        session.needs_compaction = Mock(return_value=True)
        session.get_compaction_prompt = Mock(return_value="Summarize the conversation")
        session.add_message = Mock()

        context = Mock()
        context.window = Mock()
        session.context = context

        ai_adapter = AsyncMock()
        ai_adapter.send = AsyncMock(return_value="Summary: Done")
        ai_adapter.get_context_usage = AsyncMock(return_value=(5000, 10000))

        adapter_session = Mock()
        console = Mock()
        progress = Mock()

        result = await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress
        )

        assert result is True
        ai_adapter.send.assert_called_once()
        session.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_compact_includes_preserve_items(self):
        """Verify preserve items are included in compact prompt."""
        step = Mock()
        step.preserve = ["errors"]

        conv = Mock()
        conv.compact_preserve = ["prompts"]

        session = Mock()
        session.needs_compaction = Mock(return_value=True)
        session.get_compaction_prompt = Mock(return_value="Summarize")
        session.add_message = Mock()

        context = Mock()
        context.window = Mock()
        session.context = context

        ai_adapter = AsyncMock()
        ai_adapter.send = AsyncMock(return_value="Summary")
        ai_adapter.get_context_usage = AsyncMock(return_value=(5000, 10000))

        adapter_session = Mock()
        console = Mock()
        progress = Mock()

        await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress
        )

        # Check that send was called with preserve items in prompt
        call_args = ai_adapter.send.call_args[0]
        prompt = call_args[1]
        assert "prompts" in prompt
        assert "errors" in prompt

    @pytest.mark.asyncio
    async def test_compact_syncs_token_count(self):
        """Verify token count synced after compaction."""
        step = Mock()
        step.preserve = []

        conv = Mock()
        conv.compact_preserve = []

        session = Mock()
        session.needs_compaction = Mock(return_value=True)
        session.get_compaction_prompt = Mock(return_value="Summarize")
        session.add_message = Mock()

        context = Mock()
        context.window = Mock()
        session.context = context

        ai_adapter = AsyncMock()
        ai_adapter.send = AsyncMock(return_value="Summary")
        ai_adapter.get_context_usage = AsyncMock(return_value=(3000, 10000))

        adapter_session = Mock()
        console = Mock()
        progress = Mock()

        await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress
        )

        # Verify token count was updated
        assert session.context.window.used_tokens == 3000


class TestExecuteCompactStepWithReset:
    """Tests for compact step execution with session reset."""

    @pytest.mark.asyncio
    async def test_compact_with_reset_calls_compact_with_session_reset(self):
        """Verify reset_session=True calls compact_with_session_reset."""
        from sdqctl.adapters.base import CompactionResult

        step = Mock()
        step.preserve = ["errors"]

        conv = Mock()
        conv.compact_preserve = ["prompts"]
        conv.compaction_prologue = None
        conv.compaction_epilogue = None

        session = Mock()
        session.needs_compaction = Mock(return_value=True)

        context = Mock()
        context.window = Mock()
        session.context = context

        new_adapter_session = Mock()
        compact_result = CompactionResult(
            preserved_content="Summary",
            summary="Summary",
            tokens_before=10000,
            tokens_after=2000,
        )

        ai_adapter = AsyncMock()
        ai_adapter.compact_with_session_reset = AsyncMock(
            return_value=(new_adapter_session, compact_result)
        )

        adapter_session = Mock()
        adapter_config = Mock()
        console = Mock()
        progress = Mock()

        result = await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress,
            reset_session=True,
            adapter_config=adapter_config,
        )

        # Verify compact_with_session_reset was called
        ai_adapter.compact_with_session_reset.assert_called_once()
        call_args = ai_adapter.compact_with_session_reset.call_args

        # Check preserve list includes both conv and step items
        preserve_arg = call_args[0][2]  # Third positional arg
        assert "prompts" in preserve_arg
        assert "errors" in preserve_arg

        # Verify returns tuple with new session
        assert isinstance(result, tuple)
        performed, returned_session = result
        assert performed is True
        assert returned_session is new_adapter_session

        # Verify token count synced
        assert session.context.window.used_tokens == 2000

    @pytest.mark.asyncio
    async def test_compact_with_reset_skipped_returns_tuple(self):
        """Verify skipped compaction returns (False, None) with reset_session."""
        step = Mock()
        conv = Mock()
        session = Mock()
        session.needs_compaction = Mock(return_value=False)

        ai_adapter = AsyncMock()
        adapter_session = Mock()
        adapter_config = Mock()
        console = Mock()
        progress = Mock()

        result = await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress,
            reset_session=True,
            adapter_config=adapter_config,
        )

        assert result == (False, None)

    @pytest.mark.asyncio
    async def test_compact_with_reset_fallback_without_method(self):
        """Verify fallback when adapter lacks compact_with_session_reset."""
        step = Mock()
        step.preserve = []

        conv = Mock()
        conv.compact_preserve = []

        session = Mock()
        session.needs_compaction = Mock(return_value=True)
        session.get_compaction_prompt = Mock(return_value="Summarize")
        session.add_message = Mock()

        context = Mock()
        context.window = Mock()
        session.context = context

        # Adapter without compact_with_session_reset
        ai_adapter = AsyncMock(spec=['send', 'get_context_usage'])
        ai_adapter.send = AsyncMock(return_value="Summary")
        ai_adapter.get_context_usage = AsyncMock(return_value=(3000, 10000))

        adapter_session = Mock()
        adapter_config = Mock()
        console = Mock()
        progress = Mock()

        result = await execute_compact_step(
            step, conv, session, ai_adapter, adapter_session,
            0.30, console, progress,
            reset_session=True,
            adapter_config=adapter_config,
        )

        # Falls back to standard compaction, returns (True, None)
        assert result == (True, None)
        ai_adapter.send.assert_called_once()
