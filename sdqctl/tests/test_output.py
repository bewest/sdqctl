"""Tests for sdqctl output utilities."""

import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest


class TestTTYDetection:
    """Tests for TTY detection utilities."""
    
    def test_is_stdout_tty_exists(self):
        """Test is_stdout_tty function is available."""
        from sdqctl.utils.output import is_stdout_tty
        
        result = is_stdout_tty()
        assert isinstance(result, bool)
    
    def test_is_stderr_tty_exists(self):
        """Test is_stderr_tty function is available."""
        from sdqctl.utils.output import is_stderr_tty
        
        result = is_stderr_tty()
        assert isinstance(result, bool)


class TestPromptWriter:
    """Tests for PromptWriter class."""
    
    def test_prompt_writer_disabled_by_default(self):
        """Test PromptWriter is disabled by default."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter()
        assert writer.enabled is False
    
    def test_prompt_writer_enabled(self):
        """Test PromptWriter can be enabled."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=True)
        assert writer.enabled is True
    
    def test_prompt_writer_disabled_no_output(self):
        """Test disabled PromptWriter produces no output."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=False)
        # Mock the console to verify no calls
        writer.console = MagicMock()
        
        writer.write_prompt("Test prompt", cycle=1, total_cycles=1, 
                           prompt_idx=1, total_prompts=1, context_pct=50.0)
        
        # Should not have called print
        writer.console.print.assert_not_called()
    
    def test_prompt_writer_enabled_calls_console(self):
        """Test enabled PromptWriter calls console.print."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=True)
        # Mock the console to capture calls
        writer.console = MagicMock()
        
        writer.write_prompt("Test prompt content", cycle=1, total_cycles=1, 
                           prompt_idx=1, total_prompts=1, context_pct=25.0)
        
        # Should have called print multiple times
        assert writer.console.print.call_count >= 1
        
        # Check that the prompt content was included
        all_args = [str(call) for call in writer.console.print.call_args_list]
        combined = " ".join(all_args)
        assert "Test prompt content" in combined
    
    def test_prompt_writer_format_position_multicycle(self):
        """Test PromptWriter formats cycle info for multi-cycle."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=True)
        writer.console = MagicMock()
        
        writer.write_prompt("Multi-cycle prompt", cycle=2, total_cycles=3, 
                           prompt_idx=1, total_prompts=2, context_pct=30.0)
        
        # Check the call args contain cycle info
        all_args = [str(call) for call in writer.console.print.call_args_list]
        combined = " ".join(all_args)
        assert "Cycle 2/3" in combined
        assert "Prompt 1/2" in combined
    
    def test_prompt_writer_format_position_single_cycle(self):
        """Test PromptWriter omits cycle label for single-cycle."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=True)
        writer.console = MagicMock()
        
        writer.write_prompt("Single cycle prompt", cycle=1, total_cycles=1, 
                           prompt_idx=1, total_prompts=1, context_pct=10.0)
        
        # Check that "Cycle" is NOT in output for single-cycle
        all_args = [str(call) for call in writer.console.print.call_args_list]
        combined = " ".join(all_args)
        assert "Cycle" not in combined
        assert "Prompt 1/1" in combined
    
    def test_prompt_writer_shows_context_percent(self):
        """Test PromptWriter shows context percentage."""
        from sdqctl.utils.output import PromptWriter
        
        writer = PromptWriter(enabled=True)
        writer.console = MagicMock()
        
        writer.write_prompt("Prompt text", cycle=1, total_cycles=3, 
                           prompt_idx=2, total_prompts=4, context_pct=42.7)
        
        all_args = [str(call) for call in writer.console.print.call_args_list]
        combined = " ".join(all_args)
        assert "ctx: 43%" in combined  # Rounded


class TestConsoles:
    """Tests for console instances."""
    
    def test_console_exists(self):
        """Test main console is available."""
        from sdqctl.utils.output import console
        
        assert console is not None
    
    def test_stderr_console_exists(self):
        """Test stderr console is available."""
        from sdqctl.utils.output import stderr_console
        
        assert stderr_console is not None
        # stderr_console should write to stderr
        assert stderr_console.file is sys.stderr
