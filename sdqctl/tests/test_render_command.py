"""Tests for the render command and renderer module."""

import json
from pathlib import Path
from textwrap import dedent

import pytest

from sdqctl.core.conversation import ConversationFile
from sdqctl.core.renderer import (
    render_prompt,
    render_cycle,
    render_workflow,
    format_rendered_markdown,
    format_rendered_json,
)


class TestRenderPrompt:
    """Tests for render_prompt function."""
    
    def test_renders_simple_prompt(self):
        """Simple prompt should render unchanged."""
        result = render_prompt(
            prompt="Hello world",
            prologues=[],
            epilogues=[],
            index=1,
            base_path=None,
            variables={},
        )
        
        assert result.index == 1
        assert result.raw == "Hello world"
        assert result.resolved == "Hello world"
        assert result.prologues == []
        assert result.epilogues == []
    
    def test_renders_with_prologues(self):
        """Prompts with prologues should include them."""
        result = render_prompt(
            prompt="Main prompt",
            prologues=["Before:"],
            epilogues=[],
            index=1,
            base_path=None,
            variables={},
        )
        
        assert "Before:" in result.resolved
        assert "Main prompt" in result.resolved
        assert result.prologues == ["Before:"]
    
    def test_renders_with_epilogues(self):
        """Prompts with epilogues should include them."""
        result = render_prompt(
            prompt="Main prompt",
            prologues=[],
            epilogues=["After."],
            index=1,
            base_path=None,
            variables={},
        )
        
        assert "Main prompt" in result.resolved
        assert "After." in result.resolved
        assert result.epilogues == ["After."]
    
    def test_substitutes_template_variables(self):
        """Template variables should be substituted."""
        result = render_prompt(
            prompt="Date is {{DATE}}",
            prologues=["Today: {{DATE}}"],
            epilogues=[],
            index=1,
            base_path=None,
            variables={"DATE": "2026-01-22"},
        )
        
        assert "2026-01-22" in result.resolved
        assert result.prologues == ["Today: 2026-01-22"]


class TestRenderCycle:
    """Tests for render_cycle function."""
    
    def test_renders_single_cycle(self):
        """Should render a single cycle correctly."""
        conv = ConversationFile()
        conv.prompts = ["First prompt", "Second prompt"]
        
        from sdqctl.core.context import ContextManager
        ctx = ContextManager()
        
        result = render_cycle(
            conv=conv,
            cycle_number=1,
            max_cycles=1,
            context_manager=ctx,
            base_variables={"DATE": "2026-01-22"},
            include_context=False,
        )
        
        assert result.number == 1
        assert len(result.prompts) == 2
        assert result.prompts[0].raw == "First prompt"
        assert result.prompts[1].raw == "Second prompt"
        assert result.variables["CYCLE_NUMBER"] == "1"
        assert result.variables["CYCLE_TOTAL"] == "1"
    
    def test_cycle_variables_set(self):
        """Cycle-specific variables should be set."""
        conv = ConversationFile()
        conv.prompts = ["Test"]
        
        from sdqctl.core.context import ContextManager
        ctx = ContextManager()
        
        result = render_cycle(
            conv=conv,
            cycle_number=3,
            max_cycles=5,
            context_manager=ctx,
            base_variables={},
            include_context=False,
        )
        
        assert result.variables["CYCLE_NUMBER"] == "3"
        assert result.variables["CYCLE_TOTAL"] == "5"
        assert result.variables["MAX_CYCLES"] == "5"


class TestRenderWorkflow:
    """Tests for render_workflow function."""
    
    def test_renders_workflow(self):
        """Should render a complete workflow."""
        conv = ConversationFile()
        conv.prompts = ["Analyze code."]
        conv.adapter = "mock"
        conv.model = "test-model"
        conv.max_cycles = 2
        
        result = render_workflow(conv, session_mode="accumulate", include_context=False)
        
        assert result.workflow_name == "inline"
        assert result.session_mode == "accumulate"
        assert result.adapter == "mock"
        assert result.model == "test-model"
        assert result.max_cycles == 2
        assert len(result.cycles) == 2
    
    def test_max_cycles_override(self):
        """max_cycles parameter should override conv.max_cycles."""
        conv = ConversationFile()
        conv.prompts = ["Test"]
        conv.max_cycles = 10
        
        result = render_workflow(conv, max_cycles=3, include_context=False)
        
        assert result.max_cycles == 3
        assert len(result.cycles) == 3


class TestFormatRenderedMarkdown:
    """Tests for markdown formatting."""
    
    def test_includes_header(self):
        """Markdown should include workflow header."""
        conv = ConversationFile()
        conv.prompts = ["Test prompt"]
        
        result = render_workflow(conv, include_context=False)
        markdown = format_rendered_markdown(result)
        
        assert "# Rendered Workflow:" in markdown
        assert "**Session Mode:**" in markdown
        assert "**Cycles:**" in markdown
    
    def test_includes_prompts(self):
        """Markdown should include all prompts."""
        conv = ConversationFile()
        conv.prompts = ["First", "Second"]
        
        result = render_workflow(conv, include_context=False)
        markdown = format_rendered_markdown(result)
        
        assert "### Prompt 1 of 2" in markdown
        assert "### Prompt 2 of 2" in markdown
        assert "First" in markdown
        assert "Second" in markdown
    
    def test_includes_template_variables(self):
        """Markdown should list template variables."""
        conv = ConversationFile()
        conv.prompts = ["Test"]
        
        result = render_workflow(conv, include_context=False)
        markdown = format_rendered_markdown(result, show_sections=True)
        
        assert "## Template Variables" in markdown
        assert "{{DATE}}" in markdown


class TestFormatRenderedJson:
    """Tests for JSON formatting."""
    
    def test_json_structure(self):
        """JSON should have correct structure."""
        conv = ConversationFile()
        conv.prompts = ["Test"]
        conv.adapter = "mock"
        conv.model = "test"
        
        result = render_workflow(conv, include_context=False)
        data = format_rendered_json(result)
        
        assert "workflow_name" in data
        assert "session_mode" in data
        assert "adapter" in data
        assert "model" in data
        assert "cycles" in data
        assert "template_variables" in data
    
    def test_json_serializable(self):
        """JSON output should be serializable."""
        conv = ConversationFile()
        conv.prompts = ["Test"]
        
        result = render_workflow(conv, include_context=False)
        data = format_rendered_json(result)
        
        # Should not raise
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed["cycles"][0]["prompts"][0]["raw"] == "Test"


class TestRenderWithContext:
    """Tests for rendering with context files."""
    
    def test_context_files_included(self, tmp_path):
        """Context files should be included in render."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        conv = ConversationFile()
        conv.prompts = ["Analyze"]
        conv.context_files = [str(test_file)]
        conv.source_path = tmp_path / "test.conv"
        
        result = render_workflow(conv, include_context=True)
        
        assert len(result.cycles[0].context_files) == 1
        assert result.cycles[0].context_files[0].content == "print('hello')"
