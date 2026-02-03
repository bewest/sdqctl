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


class TestExtendedDirectivesElide:
    """Tests for ELIDE with additional context-generating directives."""

    def test_refcat_elide_produces_placeholder(self):
        """REFCAT + ELIDE should produce merged_prompt with refcat_commands."""
        steps = [
            ConversationStep(type="prompt", content="Review the following code:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="refcat", content="@src/main.py#L10-L50"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Suggest improvements."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].refcat_commands) == 1
        assert result[0].refcat_commands[0] == "@src/main.py#L10-L50"
        assert "{{REFCAT:0:@src/main.py#L10-L50}}" in result[0].content

    def test_lsp_elide_produces_placeholder(self):
        """LSP + ELIDE should produce merged_prompt with lsp_commands."""
        step = ConversationStep(type="lsp", content="type Treatment -p ./src")
        step.lsp_query = "type Treatment -p ./src"
        step.lsp_options = {}
        
        steps = [
            ConversationStep(type="prompt", content="Analyze this type:"),
            ConversationStep(type="elide", content=""),
            step,
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Explain the design."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].lsp_commands) == 1
        assert result[0].lsp_commands[0][0] == "type Treatment -p ./src"
        assert "{{LSP:0:type Treatment -p ./src}}" in result[0].content

    def test_help_inline_elide_produces_placeholder(self):
        """HELP-INLINE + ELIDE should produce merged_prompt with help_inline_commands."""
        steps = [
            ConversationStep(type="prompt", content="Follow these guidelines:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="help_inline", content="directives workflow"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Create a new workflow."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].help_inline_commands) == 1
        assert result[0].help_inline_commands[0] == "directives workflow"
        assert "{{HELP:0:directives workflow}}" in result[0].content

    def test_custom_directive_elide_produces_placeholder(self):
        """Custom directive + ELIDE should produce merged_prompt with custom_directives."""
        step = ConversationStep(type="custom_directive", content="check-queues --verbose")
        step.directive_name = "HYGIENE"
        
        steps = [
            ConversationStep(type="prompt", content="Review hygiene status:"),
            ConversationStep(type="elide", content=""),
            step,
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Address any issues."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].custom_directives) == 1
        assert result[0].custom_directives[0][0] == "HYGIENE"
        assert result[0].custom_directives[0][1] == "check-queues --verbose"
        assert "{{CUSTOM:0:HYGIENE}}" in result[0].content

    def test_consult_elide_produces_placeholder(self):
        """CONSULT + ELIDE should produce merged_prompt with consult_commands."""
        steps = [
            ConversationStep(type="prompt", content="Based on this advice:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="consult", content="What are best practices for error handling in Python?"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Implement error handling."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].consult_commands) == 1
        assert "best practices for error handling" in result[0].consult_commands[0]
        # Placeholder includes truncated content (first 50 chars)
        assert "{{CONSULT:0:" in result[0].content

    def test_mixed_directives_all_merge(self):
        """Multiple different directive types should all merge properly."""
        refcat_step = ConversationStep(type="refcat", content="@lib/utils.py#L1-L20")
        lsp_step = ConversationStep(type="lsp", content="type Utils")
        lsp_step.lsp_query = "type Utils"
        lsp_step.lsp_options = {}
        
        steps = [
            ConversationStep(type="prompt", content="Analyze this codebase:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="git status"),
            ConversationStep(type="elide", content=""),
            refcat_step,
            ConversationStep(type="elide", content=""),
            lsp_step,
            ConversationStep(type="elide", content=""),
            ConversationStep(type="verify", content="", verify_type="refs", verify_options={}),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Provide summary."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].run_commands) == 1
        assert len(result[0].refcat_commands) == 1
        assert len(result[0].lsp_commands) == 1
        assert len(result[0].verify_commands) == 1
        # All placeholders present
        assert "{{RUN:0:" in result[0].content
        assert "{{REFCAT:0:" in result[0].content
        assert "{{LSP:0:" in result[0].content
        assert "{{VERIFY:0:" in result[0].content

    def test_pause_breaks_elide_chain(self):
        """PAUSE is a control directive and should break ELIDE chain."""
        import logging
        
        steps = [
            ConversationStep(type="prompt", content="Start"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="pause", content=""),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Continue"),
        ]
        
        # Should log a warning about pause breaking the chain
        result = process_elided_steps(steps)
        
        # pause should have been emitted separately
        # The chain is broken, but we still process what we can
        assert any(step.type == "pause" for step in result if hasattr(step, 'type'))

    def test_unknown_step_type_warns_and_includes_content(self):
        """Unknown step types should warn and include content as-is."""
        steps = [
            ConversationStep(type="prompt", content="Start"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="future_directive", content="some future content"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Continue"),
        ]
        result = process_elided_steps(steps)
        
        # Should merge and include content with type label
        assert len(result) == 1
        assert "[FUTURE_DIRECTIVE]" in result[0].content
        assert "some future content" in result[0].content


class TestElideWithPluginVerifiers:
    """Tests for ELIDE behavior with plugin VERIFY handlers."""

    def test_verify_elide_stores_verify_type_for_plugin(self):
        """VERIFY with plugin name is stored correctly for ELIDE execution."""
        # Simulates VERIFY build-all from t1pal workspace
        steps = [
            ConversationStep(type="prompt", content="Check the build:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify",
                content="",
                verify_type="build-all",  # Plugin verifier name
                verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix any issues."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert len(result[0].verify_commands) == 1
        assert result[0].verify_commands[0][0] == "build-all"
        assert "{{VERIFY:0:build-all}}" in result[0].content

    def test_verify_elide_multiple_plugin_verifiers(self):
        """Multiple plugin verifiers in ELIDE chain."""
        steps = [
            ConversationStep(type="prompt", content="Run all checks:"),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify", content="",
                verify_type="build-linux", verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify", content="",
                verify_type="build-ios", verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(
                type="verify", content="",
                verify_type="test-linux", verify_options={}
            ),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Address all failures."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert len(result[0].verify_commands) == 3
        verify_types = [v[0] for v in result[0].verify_commands]
        assert verify_types == ["build-linux", "build-ios", "test-linux"]


class TestElideCustomDirectivePreservesMetadata:
    """Tests that custom directive metadata is preserved for execution."""

    def test_custom_directive_preserves_directive_name(self):
        """Custom directive step preserves directive_name attribute."""
        step = ConversationStep(type="custom_directive", content="arg1 arg2")
        step.directive_name = "HYGIENE"
        step.line_number = 42
        
        steps = [
            ConversationStep(type="prompt", content="Check hygiene:"),
            ConversationStep(type="elide", content=""),
            step,
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix issues."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert len(result[0].custom_directives) == 1
        directive_name, content, orig_step = result[0].custom_directives[0]
        assert directive_name == "HYGIENE"
        assert content == "arg1 arg2"
        # Original step preserved for line_number access
        assert orig_step.line_number == 42

    def test_lsp_preserves_options(self):
        """LSP step preserves query options."""
        step = ConversationStep(type="lsp", content="type Treatment -p ./src")
        step.lsp_query = "type Treatment -p ./src"
        step.lsp_options = {"project_path": "./src", "language": "swift"}
        
        steps = [
            ConversationStep(type="prompt", content="Analyze:"),
            ConversationStep(type="elide", content=""),
            step,
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Explain."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert len(result[0].lsp_commands) == 1
        query, options = result[0].lsp_commands[0]
        assert query == "type Treatment -p ./src"
        assert options == {"project_path": "./src", "language": "swift"}
