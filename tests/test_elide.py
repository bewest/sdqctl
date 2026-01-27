"""Tests for elide module - ELIDE directive processing."""

import pytest
from sdqctl.commands.elide import (
    process_elided_steps,
    get_step_type,
    get_step_content,
)
from sdqctl.core.conversation import ConversationStep


class TestGetStepHelpers:
    """Tests for helper functions."""

    def test_get_step_type_from_object(self):
        step = ConversationStep(type="prompt", content="hello")
        assert get_step_type(step) == "prompt"

    def test_get_step_type_from_dict(self):
        step = {"type": "run", "content": "echo test"}
        assert get_step_type(step) == "run"

    def test_get_step_type_from_empty_dict(self):
        step = {}
        assert get_step_type(step) == ""

    def test_get_step_content_from_object(self):
        step = ConversationStep(type="prompt", content="hello world")
        assert get_step_content(step) == "hello world"

    def test_get_step_content_from_dict(self):
        step = {"type": "run", "content": "echo test"}
        assert get_step_content(step) == "echo test"


class TestProcessElidedSteps:
    """Tests for process_elided_steps function."""

    def test_empty_list_returns_empty(self):
        result = process_elided_steps([])
        assert result == []

    def test_single_step_unchanged(self):
        steps = [ConversationStep(type="prompt", content="hello")]
        result = process_elided_steps(steps)
        assert len(result) == 1
        assert result[0].content == "hello"

    def test_no_elide_steps_unchanged(self):
        steps = [
            ConversationStep(type="prompt", content="first"),
            ConversationStep(type="prompt", content="second"),
        ]
        result = process_elided_steps(steps)
        assert len(result) == 2
        assert result[0].content == "first"
        assert result[1].content == "second"

    def test_elide_merges_two_prompts(self):
        steps = [
            ConversationStep(type="prompt", content="Analyze this"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix the issues"),
        ]
        result = process_elided_steps(steps)
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert "Analyze this" in result[0].content
        assert "Fix the issues" in result[0].content

    def test_elide_with_run_step(self):
        steps = [
            ConversationStep(type="prompt", content="Look at tests"),
            ConversationStep(type="run", content="pytest -v"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix failures"),
        ]
        result = process_elided_steps(steps)
        # Should have merged_prompt with run command placeholder
        merged = [s for s in result if get_step_type(s) == "merged_prompt"]
        assert len(merged) >= 1

    def test_multiple_elide_groups(self):
        steps = [
            ConversationStep(type="prompt", content="Group 1 start"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Group 1 end"),
            ConversationStep(type="prompt", content="Standalone"),
            ConversationStep(type="prompt", content="Group 2 start"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Group 2 end"),
        ]
        result = process_elided_steps(steps)
        # Should have: merged(1+1), standalone, merged(2+2)
        assert len(result) == 3

    def test_consecutive_elides(self):
        steps = [
            ConversationStep(type="prompt", content="First"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Second"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Third"),
        ]
        result = process_elided_steps(steps)
        # All three should merge into one
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert "First" in result[0].content
        assert "Second" in result[0].content
        assert "Third" in result[0].content

    def test_dict_steps_supported(self):
        steps = [
            {"type": "prompt", "content": "Dict step 1"},
            {"type": "elide", "content": ""},
            {"type": "prompt", "content": "Dict step 2"},
        ]
        result = process_elided_steps(steps)
        assert len(result) == 1
