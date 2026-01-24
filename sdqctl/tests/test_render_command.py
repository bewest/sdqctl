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
            total_prompts=1,
            base_path=None,
            variables={},
        )
        
        assert result.index == 1
        assert result.raw == "Hello world"
        assert result.resolved == "Hello world"
        assert result.prologues == []
        assert result.epilogues == []
    
    def test_renders_with_prologues(self):
        """Prompts with prologues should include them on first prompt."""
        result = render_prompt(
            prompt="Main prompt",
            prologues=["Before:"],
            epilogues=[],
            index=1,
            total_prompts=1,
            base_path=None,
            variables={},
        )
        
        assert "Before:" in result.resolved
        assert "Main prompt" in result.resolved
        assert result.prologues == ["Before:"]
    
    def test_renders_with_epilogues(self):
        """Prompts with epilogues should include them on last prompt."""
        result = render_prompt(
            prompt="Main prompt",
            prologues=[],
            epilogues=["After."],
            index=1,
            total_prompts=1,
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
            total_prompts=1,
            base_path=None,
            variables={"DATE": "2026-01-22"},
        )
        
        assert "2026-01-22" in result.resolved
        assert result.prologues == ["Today: 2026-01-22"]
    
    def test_prologues_only_on_first_prompt(self):
        """Prologues should only be included on the first prompt."""
        # First prompt (index=1) should have prologues
        result_first = render_prompt(
            prompt="First prompt",
            prologues=["Prologue content"],
            epilogues=[],
            index=1,
            total_prompts=3,
            base_path=None,
            variables={},
        )
        assert "Prologue content" in result_first.resolved
        assert result_first.prologues == ["Prologue content"]
        
        # Second prompt (index=2) should NOT have prologues
        result_second = render_prompt(
            prompt="Second prompt",
            prologues=["Prologue content"],
            epilogues=[],
            index=2,
            total_prompts=3,
            base_path=None,
            variables={},
        )
        assert "Prologue content" not in result_second.resolved
        assert result_second.prologues == []
    
    def test_epilogues_only_on_last_prompt(self):
        """Epilogues should only be included on the last prompt."""
        # First prompt (not last) should NOT have epilogues
        result_first = render_prompt(
            prompt="First prompt",
            prologues=[],
            epilogues=["Epilogue content"],
            index=1,
            total_prompts=3,
            base_path=None,
            variables={},
        )
        assert "Epilogue content" not in result_first.resolved
        assert result_first.epilogues == []
        
        # Last prompt (index=3, total=3) should have epilogues
        result_last = render_prompt(
            prompt="Last prompt",
            prologues=[],
            epilogues=["Epilogue content"],
            index=3,
            total_prompts=3,
            base_path=None,
            variables={},
        )
        assert "Epilogue content" in result_last.resolved
        assert result_last.epilogues == ["Epilogue content"]


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


class TestRenderWithRefcat:
    """Tests for rendering with REFCAT refs."""
    
    def test_refcat_content_included(self, tmp_path):
        """REFCAT refs should be extracted and included in render."""
        # Create a test file
        test_file = tmp_path / "sample.py"
        test_file.write_text(dedent("""\
            line 1
            line 2
            line 3
            line 4
            line 5
        """).strip())
        
        conv = ConversationFile()
        conv.prompts = ["Analyze"]
        conv.refcat_refs = [f"@{test_file}#L2-L4"]
        conv.source_path = tmp_path / "test.conv"
        
        result = render_workflow(conv, include_context=True)
        
        assert result.cycles[0].refcat_content != ""
        assert "line 2" in result.cycles[0].refcat_content
        assert "line 3" in result.cycles[0].refcat_content
        assert "line 4" in result.cycles[0].refcat_content
        assert "## From:" in result.cycles[0].refcat_content
    
    def test_refcat_error_handled_gracefully(self, tmp_path):
        """Missing REFCAT refs should produce error comments, not crash."""
        conv = ConversationFile()
        conv.prompts = ["Analyze"]
        conv.refcat_refs = ["@nonexistent.py#L1-L10"]
        conv.source_path = tmp_path / "test.conv"
        
        result = render_workflow(conv, include_context=True)
        
        # Should have an error comment in refcat_content
        assert "<!-- REFCAT error" in result.cycles[0].refcat_content
    
    def test_refcat_in_markdown_output(self, tmp_path):
        """REFCAT content should appear in markdown output."""
        test_file = tmp_path / "sample.py"
        test_file.write_text("def foo():\n    pass")
        
        conv = ConversationFile()
        conv.prompts = ["Analyze"]
        conv.refcat_refs = [f"@{test_file}#L1-L2"]
        conv.source_path = tmp_path / "test.conv"
        
        result = render_workflow(conv, include_context=True)
        md = format_rendered_markdown(result)
        
        assert "### REFCAT Excerpts" in md
        assert "def foo():" in md
    
    def test_refcat_in_json_output(self, tmp_path):
        """REFCAT content should appear in JSON output."""
        test_file = tmp_path / "sample.py"
        test_file.write_text("def bar():\n    return 42")
        
        conv = ConversationFile()
        conv.prompts = ["Analyze"]
        conv.refcat_refs = [f"@{test_file}#L1-L2"]
        conv.source_path = tmp_path / "test.conv"
        
        result = render_workflow(conv, include_context=True)
        data = format_rendered_json(result)
        
        assert data["cycles"][0]["refcat_content"] is not None
        assert "def bar():" in data["cycles"][0]["refcat_content"]


class TestRenderWithHelp:
    """Tests for HELP directive injection during rendering."""

    def test_help_topics_injected_into_prologues(self):
        """HELP topics should be injected as prologues during rendering."""
        content = """MODEL gpt-4
HELP directives
PROMPT Analyze the workflow.
"""
        conv = ConversationFile.parse(content)
        
        # Create minimal context manager
        from sdqctl.core.context import ContextManager
        ctx = ContextManager()
        
        # Render cycle
        result = render_cycle(
            conv=conv,
            cycle_number=1,
            max_cycles=1,
            context_manager=ctx,
            base_variables={},
            include_context=True,
        )
        
        # The first prompt should have help content injected via prologues
        assert len(result.prompts) == 1
        # Check that "Directives" from the help topic is in the resolved prompt
        assert "Directive" in result.prompts[0].resolved

    def test_help_multiple_topics_injected(self):
        """Multiple HELP topics should all be injected."""
        content = """MODEL gpt-4
HELP directives adapters
PROMPT Analyze the workflow.
"""
        conv = ConversationFile.parse(content)
        
        from sdqctl.core.context import ContextManager
        ctx = ContextManager()
        
        result = render_cycle(
            conv=conv,
            cycle_number=1,
            max_cycles=1,
            context_manager=ctx,
            base_variables={},
            include_context=True,
        )
        
        # Should include content from both topics
        resolved = result.prompts[0].resolved
        assert "Directive" in resolved  # From directives topic
        assert "Adapter" in resolved    # From adapters topic

    def test_help_with_existing_prologues(self):
        """HELP topics should be added alongside existing prologues."""
        content = """MODEL gpt-4
PROLOGUE My custom prologue text
HELP directives
PROMPT Analyze the workflow.
"""
        conv = ConversationFile.parse(content)
        
        from sdqctl.core.context import ContextManager
        ctx = ContextManager()
        
        result = render_cycle(
            conv=conv,
            cycle_number=1,
            max_cycles=1,
            context_manager=ctx,
            base_variables={},
            include_context=True,
        )
        
        resolved = result.prompts[0].resolved
        # Should include both the custom prologue and help content
        assert "My custom prologue text" in resolved
        assert "Directive" in resolved
