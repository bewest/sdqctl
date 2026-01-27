"""Tests for json_pipeline module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExecuteJsonPipeline:
    """Tests for execute_json_pipeline function."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_early(self):
        """Test dry run mode returns without executing."""
        from sdqctl.commands.json_pipeline import execute_json_pipeline

        json_data = {
            "workflow_name": "test-workflow",
            "prompts": ["Test prompt"],
            "adapter": "mock",
            "model": "test-model",
        }

        with patch('sdqctl.commands.json_pipeline.console') as mock_console:
            await execute_json_pipeline(
                json_data=json_data,
                max_cycles_override=1,
                session_mode="accumulate",
                adapter_name=None,
                model=None,
                checkpoint_dir=None,
                cli_prologues=(),
                cli_epilogues=(),
                cli_headers=(),
                cli_footers=(),
                output_file=None,
                event_log_path=None,
                json_output=False,
                dry_run=True,  # dry run
            )

            # Should print dry run info
            assert mock_console.print.called

    @pytest.mark.asyncio
    async def test_applies_cli_overrides(self):
        """Test CLI options override JSON data."""
        from sdqctl.commands.json_pipeline import execute_json_pipeline
        from sdqctl.core.conversation import ConversationFile

        json_data = {
            "workflow_name": "test",
            "prompts": ["Prompt"],
            "adapter": "original",
            "model": "original-model",
        }

        with patch.object(ConversationFile, 'from_rendered_json') as mock_from_json:
            mock_conv = MagicMock()
            mock_conv.adapter = "original"
            mock_conv.model = "original-model"
            mock_conv.prompts = ["Prompt"]
            mock_conv.prologues = []
            mock_conv.epilogues = []
            mock_conv.headers = []
            mock_conv.footers = []
            mock_conv.max_cycles = 1
            mock_from_json.return_value = mock_conv

            with patch('sdqctl.commands.json_pipeline.console'):
                await execute_json_pipeline(
                    json_data=json_data,
                    max_cycles_override=None,
                    session_mode="accumulate",
                    adapter_name="override-adapter",  # CLI override
                    model="override-model",  # CLI override
                    checkpoint_dir=None,
                    cli_prologues=(),
                    cli_epilogues=(),
                    cli_headers=(),
                    cli_footers=(),
                    output_file=None,
                    event_log_path=None,
                    json_output=False,
                    dry_run=True,
                )

                # Verify overrides applied
                assert mock_conv.adapter == "override-adapter"
                assert mock_conv.model == "override-model"

    @pytest.mark.asyncio
    async def test_applies_cli_prologues(self):
        """Test CLI prologues are prepended."""
        from sdqctl.commands.json_pipeline import execute_json_pipeline
        from sdqctl.core.conversation import ConversationFile

        json_data = {
            "workflow_name": "test",
            "prompts": ["Prompt"],
        }

        with patch.object(ConversationFile, 'from_rendered_json') as mock_from_json:
            mock_conv = MagicMock()
            mock_conv.adapter = "mock"
            mock_conv.model = "test"
            mock_conv.prompts = ["Prompt"]
            mock_conv.prologues = ["file-prologue"]
            mock_conv.epilogues = []
            mock_conv.headers = []
            mock_conv.footers = []
            mock_conv.max_cycles = 1
            mock_from_json.return_value = mock_conv

            with patch('sdqctl.commands.json_pipeline.console'):
                await execute_json_pipeline(
                    json_data=json_data,
                    max_cycles_override=None,
                    session_mode="accumulate",
                    adapter_name=None,
                    model=None,
                    checkpoint_dir=None,
                    cli_prologues=("cli-prologue",),  # CLI prologue
                    cli_epilogues=(),
                    cli_headers=(),
                    cli_footers=(),
                    output_file=None,
                    event_log_path=None,
                    json_output=False,
                    dry_run=True,
                )

                # CLI prologues prepend to file prologues
                assert mock_conv.prologues == ["cli-prologue", "file-prologue"]

    @pytest.mark.asyncio
    async def test_adapter_error_handled(self):
        """Test adapter errors are handled gracefully."""
        from sdqctl.commands.json_pipeline import execute_json_pipeline

        json_data = {
            "workflow_name": "test",
            "prompts": ["Prompt"],
            "adapter": "nonexistent",
            "model": "test",
        }

        with patch('sdqctl.commands.json_pipeline.get_adapter') as mock_get_adapter:
            mock_get_adapter.side_effect = ValueError("Unknown adapter")

            with patch('sdqctl.commands.json_pipeline.console') as mock_console:
                await execute_json_pipeline(
                    json_data=json_data,
                    max_cycles_override=1,
                    session_mode="accumulate",
                    adapter_name=None,
                    model=None,
                    checkpoint_dir=None,
                    cli_prologues=(),
                    cli_epilogues=(),
                    cli_headers=(),
                    cli_footers=(),
                    output_file=None,
                    event_log_path=None,
                    json_output=False,
                    dry_run=False,  # Not dry run, should hit adapter
                )

                # Should print error
                error_calls = [c for c in mock_console.print.call_args_list
                              if 'red' in str(c)]
                assert len(error_calls) > 0
