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


class TestElideIntegration:
    """Integration tests verifying ELIDE turn counting in iterate.py."""

    def test_run_elide_prompt_elide_prompt_produces_one_turn(self):
        """Verifies: RUN + ELIDE + PROMPT + ELIDE + PROMPT = 1 AI turn.
        
        This is the documented behavior from CONVERSATION-LIFECYCLE.md.
        The pattern should merge into a single merged_prompt step.
        """
        steps = [
            ConversationStep(type="run", content="echo test"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Analyze this output"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Then suggest fixes"),
        ]
        result = process_elided_steps(steps)
        
        # All should merge into 1 step = 1 AI turn
        assert len(result) == 1, f"Expected 1 turn, got {len(result)}"
        assert result[0].type == "merged_prompt"
        
        # The merged content should contain all prompts
        assert "Analyze this output" in result[0].content
        assert "Then suggest fixes" in result[0].content
        
        # The RUN command should be attached for execution
        assert hasattr(result[0], 'run_commands')
        assert "echo test" in result[0].run_commands

    def test_multiple_runs_elided_into_single_turn(self):
        """Multiple RUN commands can be elided into a single turn."""
        steps = [
            ConversationStep(type="run", content="echo first"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="echo second"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Analyze both outputs"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].run_commands) == 2
        assert "echo first" in result[0].run_commands
        assert "echo second" in result[0].run_commands

    def test_without_elide_each_prompt_is_separate_turn(self):
        """Without ELIDE, each PROMPT is a separate turn (baseline)."""
        steps = [
            ConversationStep(type="prompt", content="First prompt"),
            ConversationStep(type="prompt", content="Second prompt"),
            ConversationStep(type="prompt", content="Third prompt"),
        ]
        result = process_elided_steps(steps)
        
        # Without ELIDE, all prompts remain separate = 3 turns
        assert len(result) == 3
        for step in result:
            assert step.type == "prompt"


class TestBacklogCyclePatterns:
    """Tests for patterns found in backlog-cycle.conv workflow.
    
    These tests verify that real-world workflow patterns produce
    the expected turn structure.
    """

    def test_phase0_pattern_prompt_elide_runs_elide_prompt(self):
        """Phase 0 pattern: PROMPT + ELIDE + (RUN + ELIDE)×3 + PROMPT = 1 turn.
        
        From backlog-cycle.conv lines 43-58:
        PROMPT ## Phase 0: State Check
        ELIDE
        RUN git status
        ELIDE
        RUN swift build
        ELIDE
        RUN swift test
        ELIDE
        PROMPT Review status:
        """
        steps = [
            ConversationStep(type="prompt", content="## Phase 0: State Check"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="git status"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="swift build"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="swift test"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Review status:"),
        ]
        result = process_elided_steps(steps)
        
        # All 9 steps merge into 1 turn
        assert len(result) == 1, f"Expected 1 turn, got {len(result)}"
        assert result[0].type == "merged_prompt"
        
        # Should have all 3 RUN commands
        assert len(result[0].run_commands) == 3
        assert "git status" in result[0].run_commands
        assert "swift build" in result[0].run_commands
        assert "swift test" in result[0].run_commands
        
        # Should have both prompts merged
        assert "Phase 0: State Check" in result[0].content
        assert "Review status:" in result[0].content

    def test_compact_breaks_elide_chain(self):
        """COMPACT between ELIDE chains creates separate turns.
        
        From backlog-cycle.conv line 95:
        Phase 1 chain ends, COMPACT, Phase 2 starts fresh.
        """
        steps = [
            # Phase 1 chain
            ConversationStep(type="prompt", content="Phase 1: Task Selection"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="head backlogs"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Select task"),
            # COMPACT breaks the chain
            ConversationStep(type="compact", content=""),
            # Phase 2 - separate turn
            ConversationStep(type="prompt", content="Phase 2: Execute"),
        ]
        result = process_elided_steps(steps)
        
        # Should produce: merged_prompt, compact, prompt = 3 steps
        assert len(result) == 3
        assert result[0].type == "merged_prompt"
        assert result[1].type == "compact"
        assert result[2].type == "prompt"

    def test_four_runs_elided_into_single_turn(self):
        """Four RUN commands in an ELIDE chain (from Phase 1 pattern).
        
        From backlog-cycle.conv lines 61-74:
        PROMPT + ELIDE + RUN + ELIDE + RUN + ELIDE + RUN + ELIDE + RUN + ELIDE + PROMPT
        """
        steps = [
            ConversationStep(type="prompt", content="## Phase 1: Task Selection"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="head LIVE-BACKLOG.md"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="head MASTER-BACKLOG.md"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="grep apps.md"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="grep cgm.md"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Task Selection Criteria:"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].run_commands) == 4

    def test_multiple_phases_with_standalone_prompts(self):
        """Multiple phases where some prompts are standalone (no ELIDE).
        
        Simulates Phase 2 (standalone) followed by Phase 3 (with ELIDE).
        """
        steps = [
            # Phase 2: standalone prompt (no RUNs)
            ConversationStep(type="prompt", content="## Phase 2: Execute Work"),
            # Phase 3: with ELIDE chain
            ConversationStep(type="prompt", content="## Phase 3: Verify"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="swift build"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="swift test"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Verification Checklist:"),
        ]
        result = process_elided_steps(steps)
        
        # Phase 2 prompt is standalone, Phase 3 merges
        assert len(result) == 2
        assert result[0].type == "prompt"
        assert result[0].content == "## Phase 2: Execute Work"
        assert result[1].type == "merged_prompt"
        assert len(result[1].run_commands) == 2


class TestBacklogCycleWorkflowParsing:
    """End-to-end parsing tests for backlog-cycle.conv style workflows."""

    def test_parse_workflow_with_frontmatter(self):
        """Workflow with YAML frontmatter parses correctly."""
        from sdqctl.core.conversation.file import ConversationFile
        
        content = """---
name: backlog-cycle
description: Full development cycle
version: 3.1.0
---

MODEL gpt-4
ADAPTER mock
RUN-TIMEOUT 120s

PROMPT Phase 0
ELIDE
RUN git status
ELIDE
PROMPT Review
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model == "gpt-4"
        assert conv.adapter == "mock"
        assert conv.run_timeout == 120
        assert len(conv.steps) == 5  # prompt, elide, run, elide, prompt

    def test_full_phase_pattern_produces_correct_turns(self):
        """Full multi-phase workflow produces expected turn count."""
        from sdqctl.core.conversation.file import ConversationFile
        
        content = """MODEL gpt-4
ADAPTER mock

# Phase 0: State Check (1 turn)
PROMPT ## Phase 0: State Check
ELIDE
RUN git status
ELIDE
RUN swift build
ELIDE
PROMPT Review status

# COMPACT breaks chain
COMPACT

# Phase 2: Execute (1 turn, standalone)
PROMPT ## Phase 2: Execute Work

# Phase 3: Verify (1 turn)
PROMPT ## Phase 3: Verify
ELIDE
RUN swift test
ELIDE
PROMPT Verification complete
"""
        conv = ConversationFile.parse(content)
        result = process_elided_steps(conv.steps)
        
        # Expected: merged(Phase0), compact, prompt(Phase2), merged(Phase3)
        assert len(result) == 4
        
        # Phase 0: merged with 2 RUN commands
        assert result[0].type == "merged_prompt"
        assert len(result[0].run_commands) == 2
        
        # COMPACT
        assert result[1].type == "compact"
        
        # Phase 2: standalone prompt
        assert result[2].type == "prompt"
        
        # Phase 3: merged with 1 RUN command
        assert result[3].type == "merged_prompt"
        assert len(result[3].run_commands) == 1


class TestVerifyElideIntegration:
    """Tests for VERIFY + ELIDE integration (backlog-cycle-v2 patterns)."""

    def test_verify_elide_prompt_produces_one_turn(self):
        """VERIFY + ELIDE + PROMPT = 1 turn with verify output merged."""
        steps = [
            ConversationStep(
                type="verify",
                content="",
                verify_type="refs",
                verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Review verification results"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert hasattr(result[0], 'verify_commands')
        assert len(result[0].verify_commands) == 1
        assert result[0].verify_commands[0][0] == "refs"
        assert "{{VERIFY:0:refs}}" in result[0].content
        assert "Review verification results" in result[0].content

    def test_run_verify_elide_prompt_all_merge(self):
        """RUN + ELIDE + VERIFY + ELIDE + PROMPT all merge into 1 turn.
        
        From backlog-cycle-v2.conv Phase 3 pattern:
        ELIDE
        VERIFY build-all
        ELIDE
        RUN swift test
        ELIDE
        PROMPT Verification Checklist
        """
        steps = [
            ConversationStep(type="prompt", content="## Phase 3: Verify"),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify",
                content="",
                verify_type="build-all",
                verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="swift test 2>&1 | tail -20"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Verification Checklist:"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        
        # Should have 1 RUN and 1 VERIFY
        assert len(result[0].run_commands) == 1
        assert len(result[0].verify_commands) == 1
        
        # Content should have placeholders
        assert "{{VERIFY:0:build-all}}" in result[0].content
        assert "{{RUN:0:swift test" in result[0].content
        assert "Phase 3: Verify" in result[0].content
        assert "Verification Checklist:" in result[0].content

    def test_multiple_verify_in_elide_chain(self):
        """Multiple VERIFY commands in an ELIDE chain."""
        steps = [
            ConversationStep(type="prompt", content="Run all verifications"),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify",
                content="",
                verify_type="refs",
                verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify",
                content="",
                verify_type="links",
                verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Review all results"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].verify_commands) == 2
        assert result[0].verify_commands[0][0] == "refs"
        assert result[0].verify_commands[1][0] == "links"
