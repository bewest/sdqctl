"""Tests for sdqctl renderer core classes."""

import pytest

from sdqctl.core.renderer import (
    RenderedCycle,
    RenderedPrompt,
    RenderedWorkflow,
)
from sdqctl.core.context import ContextFile

pytestmark = pytest.mark.unit


class TestRenderedPrompt:
    """Test RenderedPrompt dataclass."""

    def test_basic_creation(self):
        """Create RenderedPrompt with all fields."""
        rp = RenderedPrompt(
            index=1,
            raw="Hello, world!",
            prologues=["Prologue 1"],
            epilogues=["Epilogue 1"],
            resolved="Prologue 1\n\nHello, world!\n\nEpilogue 1"
        )
        assert rp.index == 1
        assert rp.raw == "Hello, world!"
        assert rp.prologues == ["Prologue 1"]
        assert rp.epilogues == ["Epilogue 1"]
        assert "Prologue 1" in rp.resolved

    def test_empty_prologues_and_epilogues(self):
        """Create RenderedPrompt with no prologues/epilogues."""
        rp = RenderedPrompt(
            index=2,
            raw="Middle prompt",
            prologues=[],
            epilogues=[],
            resolved="Middle prompt"
        )
        assert rp.prologues == []
        assert rp.epilogues == []
        assert rp.resolved == "Middle prompt"

    def test_multiple_prologues(self):
        """Multiple prologues stored correctly."""
        rp = RenderedPrompt(
            index=1,
            raw="Prompt",
            prologues=["First", "Second", "Third"],
            epilogues=[],
            resolved="First\n\nSecond\n\nThird\n\nPrompt"
        )
        assert len(rp.prologues) == 3
        assert rp.prologues[0] == "First"

    def test_index_is_one_based(self):
        """Index should be 1-based per convention."""
        rp = RenderedPrompt(
            index=1,
            raw="First",
            prologues=[],
            epilogues=[],
            resolved="First"
        )
        assert rp.index == 1  # Not 0


class TestRenderedCycle:
    """Test RenderedCycle dataclass."""

    def test_basic_creation(self):
        """Create RenderedCycle with minimal fields."""
        rc = RenderedCycle(
            number=1,
            context_files=[],
            context_content=""
        )
        assert rc.number == 1
        assert rc.context_files == []
        assert rc.context_content == ""
        assert rc.refcat_content == ""
        assert rc.prompts == []
        assert rc.variables == {}

    def test_with_context_files(self):
        """Create RenderedCycle with context files."""
        from pathlib import Path
        cf = ContextFile(path=Path("test.py"), content="print('hi')", tokens_estimate=10)
        rc = RenderedCycle(
            number=1,
            context_files=[cf],
            context_content="# test.py\nprint('hi')"
        )
        assert len(rc.context_files) == 1
        assert rc.context_files[0].path == Path("test.py")
        assert "print('hi')" in rc.context_content

    def test_with_prompts(self):
        """Create RenderedCycle with prompts."""
        rp = RenderedPrompt(
            index=1,
            raw="Test",
            prologues=[],
            epilogues=[],
            resolved="Test"
        )
        rc = RenderedCycle(
            number=2,
            context_files=[],
            context_content="",
            prompts=[rp]
        )
        assert len(rc.prompts) == 1
        assert rc.prompts[0].raw == "Test"

    def test_with_refcat_content(self):
        """Create RenderedCycle with REFCAT content."""
        rc = RenderedCycle(
            number=1,
            context_files=[],
            context_content="",
            refcat_content="# src/main.py\ndef main():\n    pass"
        )
        assert "main.py" in rc.refcat_content

    def test_with_variables(self):
        """Create RenderedCycle with template variables."""
        rc = RenderedCycle(
            number=3,
            context_files=[],
            context_content="",
            variables={
                "CYCLE_NUMBER": "3",
                "MAX_CYCLES": "10",
                "WORKFLOW_NAME": "test.conv"
            }
        )
        assert rc.variables["CYCLE_NUMBER"] == "3"
        assert rc.variables["MAX_CYCLES"] == "10"

    def test_number_is_one_based(self):
        """Cycle number should be 1-based."""
        rc = RenderedCycle(
            number=1,
            context_files=[],
            context_content=""
        )
        assert rc.number == 1  # Not 0


class TestRenderedWorkflow:
    """Test RenderedWorkflow dataclass."""

    def test_basic_creation(self):
        """Create RenderedWorkflow with minimal fields."""
        rw = RenderedWorkflow(
            workflow_path=None,
            workflow_name="inline",
            session_mode="fresh",
            adapter="copilot",
            model="gpt-4o",
            max_cycles=5,
            cycles=[],
            base_variables={}
        )
        assert rw.workflow_path is None
        assert rw.workflow_name == "inline"
        assert rw.session_mode == "fresh"
        assert rw.adapter == "copilot"
        assert rw.model == "gpt-4o"
        assert rw.max_cycles == 5
        assert rw.cycles == []

    def test_with_path(self):
        """Create RenderedWorkflow with workflow path."""
        from pathlib import Path
        rw = RenderedWorkflow(
            workflow_path=Path("/workflows/test.conv"),
            workflow_name="test.conv",
            session_mode="accumulate",
            adapter="copilot",
            model="claude-3",
            max_cycles=10,
            cycles=[],
            base_variables={"PROJECT": "sdqctl"}
        )
        assert rw.workflow_path == Path("/workflows/test.conv")
        assert rw.workflow_name == "test.conv"
        assert rw.base_variables["PROJECT"] == "sdqctl"

    def test_with_cycles(self):
        """Create RenderedWorkflow with cycles."""
        cycle = RenderedCycle(
            number=1,
            context_files=[],
            context_content=""
        )
        rw = RenderedWorkflow(
            workflow_path=None,
            workflow_name="test",
            session_mode="fresh",
            adapter="copilot",
            model="gpt-4o",
            max_cycles=1,
            cycles=[cycle],
            base_variables={}
        )
        assert len(rw.cycles) == 1
        assert rw.cycles[0].number == 1

    def test_multiple_cycles(self):
        """Create RenderedWorkflow with multiple cycles."""
        cycles = [
            RenderedCycle(number=i, context_files=[], context_content="")
            for i in range(1, 6)
        ]
        rw = RenderedWorkflow(
            workflow_path=None,
            workflow_name="multi",
            session_mode="compact",
            adapter="copilot",
            model="gpt-4o",
            max_cycles=5,
            cycles=cycles,
            base_variables={}
        )
        assert len(rw.cycles) == 5
        assert rw.cycles[0].number == 1
        assert rw.cycles[4].number == 5


class TestRenderedPromptEquality:
    """Test RenderedPrompt comparison behavior."""

    def test_equal_prompts(self):
        """Two prompts with same values are equal."""
        rp1 = RenderedPrompt(
            index=1,
            raw="Hello",
            prologues=["P1"],
            epilogues=["E1"],
            resolved="P1\n\nHello\n\nE1"
        )
        rp2 = RenderedPrompt(
            index=1,
            raw="Hello",
            prologues=["P1"],
            epilogues=["E1"],
            resolved="P1\n\nHello\n\nE1"
        )
        assert rp1 == rp2

    def test_different_prompts(self):
        """Two prompts with different values are not equal."""
        rp1 = RenderedPrompt(
            index=1,
            raw="Hello",
            prologues=[],
            epilogues=[],
            resolved="Hello"
        )
        rp2 = RenderedPrompt(
            index=2,
            raw="World",
            prologues=[],
            epilogues=[],
            resolved="World"
        )
        assert rp1 != rp2


class TestRenderedCycleEquality:
    """Test RenderedCycle comparison behavior."""

    def test_equal_cycles(self):
        """Two cycles with same values are equal."""
        rc1 = RenderedCycle(number=1, context_files=[], context_content="ctx")
        rc2 = RenderedCycle(number=1, context_files=[], context_content="ctx")
        assert rc1 == rc2

    def test_different_cycles(self):
        """Two cycles with different values are not equal."""
        rc1 = RenderedCycle(number=1, context_files=[], context_content="")
        rc2 = RenderedCycle(number=2, context_files=[], context_content="")
        assert rc1 != rc2


class TestElideInRenderer:
    """Tests for ELIDE directive processing in renderer.
    
    Regression tests ensuring that ELIDE directives are properly processed
    when rendering workflows, merging adjacent steps with RUN placeholders.
    """

    def test_render_elide_merges_prompt_and_run(self):
        """ELIDE should merge PROMPT with following RUN into single prompt."""
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.renderer import render_workflow

        content = """MODEL gpt-4
ADAPTER mock
PROMPT Check the status.
ELIDE
RUN git status
ELIDE
PROMPT Fix any issues.
"""
        conv = ConversationFile.parse(content)
        rendered = render_workflow(conv, include_context=False)
        
        # Should have 1 merged prompt instead of 2 separate ones
        assert len(rendered.cycles) == 1
        cycle = rendered.cycles[0]
        assert len(cycle.prompts) == 1
        
        # Merged prompt should contain both text and RUN placeholder
        merged = cycle.prompts[0].resolved
        assert "Check the status." in merged
        assert "{{RUN:0:git status}}" in merged
        assert "Fix any issues." in merged

    def test_render_elide_multiple_runs(self):
        """ELIDE should merge multiple RUN commands with placeholders."""
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.renderer import render_workflow

        content = """MODEL gpt-4
ADAPTER mock
PROMPT Review build and tests.
ELIDE
RUN make build
ELIDE
RUN make test
ELIDE
PROMPT Summarize results.
"""
        conv = ConversationFile.parse(content)
        rendered = render_workflow(conv, include_context=False)
        
        cycle = rendered.cycles[0]
        assert len(cycle.prompts) == 1
        
        merged = cycle.prompts[0].resolved
        assert "Review build and tests." in merged
        assert "{{RUN:0:make build}}" in merged
        assert "{{RUN:1:make test}}" in merged
        assert "Summarize results." in merged

    def test_render_no_elide_separate_prompts(self):
        """Without ELIDE, prompts should remain separate."""
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.renderer import render_workflow

        content = """MODEL gpt-4
ADAPTER mock
PROMPT First prompt.
RUN git status
PROMPT Second prompt.
"""
        conv = ConversationFile.parse(content)
        rendered = render_workflow(conv, include_context=False)
        
        cycle = rendered.cycles[0]
        # RUN step is not a prompt type, so we should have 2 prompts
        assert len(cycle.prompts) == 2
        assert "First prompt." in cycle.prompts[0].resolved
        assert "Second prompt." in cycle.prompts[1].resolved

    def test_render_elide_preserves_multiline_prompt(self):
        """ELIDE should work correctly with multi-line PROMPT content."""
        from sdqctl.core.conversation import ConversationFile
        from sdqctl.core.renderer import render_workflow

        content = """MODEL gpt-4
ADAPTER mock
PROMPT ## Phase 1
Review the code below.
Check for errors.
ELIDE
RUN cat src/main.py
ELIDE
PROMPT ## Phase 2
Fix any issues found.
"""
        conv = ConversationFile.parse(content)
        rendered = render_workflow(conv, include_context=False)
        
        cycle = rendered.cycles[0]
        assert len(cycle.prompts) == 1
        
        merged = cycle.prompts[0].resolved
        # Multi-line content preserved
        assert "## Phase 1" in merged
        assert "Review the code below." in merged
        assert "Check for errors." in merged
        # RUN placeholder included
        assert "{{RUN:0:cat src/main.py}}" in merged
        # Second multi-line prompt included
        assert "## Phase 2" in merged
        assert "Fix any issues found." in merged
