"""
End-to-end workflow integration tests.

Tests complete conversation workflows using mock adapters for
deterministic behavior without requiring live API access.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.core.conversation import ConversationFile, ConversationStep


class TestConversationWorkflow:
    """Test complete conversation file workflows."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace with test files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a simple conversation file
        conv_file = workspace / "test.conv"
        conv_file.write_text("""# Test Conversation
MODEL mock
ADAPTER mock

PROMPT Hello, this is a test prompt.
""")

        # Create a multi-step conversation
        multi_conv = workspace / "multi-step.conv"
        multi_conv.write_text("""# Multi-Step Test
MODEL mock
ADAPTER mock

PROMPT First step: analyze the situation.

PROMPT Second step: provide recommendations.

CHECKPOINT mid-point

PROMPT Third step: summarize findings.
""")

        return workspace

    def test_parse_simple_conversation(self, temp_workspace):
        """Test parsing a simple conversation file."""
        conv_path = temp_workspace / "test.conv"
        conv = ConversationFile.from_file(conv_path)

        assert conv.model == "mock"
        assert conv.adapter == "mock"
        assert len(conv.steps) >= 1

    def test_parse_multi_step_conversation(self, temp_workspace):
        """Test parsing multi-step conversation with checkpoint."""
        conv_path = temp_workspace / "multi-step.conv"
        conv = ConversationFile.from_file(conv_path)

        assert len(conv.steps) == 4  # 3 prompts + 1 checkpoint
        
        step_types = [s.type for s in conv.steps]
        assert step_types.count("prompt") == 3
        assert "checkpoint" in step_types

    def test_conversation_step_content(self, temp_workspace):
        """Test conversation step content extraction."""
        conv_path = temp_workspace / "multi-step.conv"
        conv = ConversationFile.from_file(conv_path)

        prompts = [s for s in conv.steps if s.type == "prompt"]
        assert "First step" in prompts[0].content
        assert "Second step" in prompts[1].content
        assert "Third step" in prompts[2].content


class TestDirectiveWorkflow:
    """Test directive processing workflows."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with directive test files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Context file
        (workspace / "context.md").write_text("# Context\nThis is context.")

        # Conversation with context
        conv_file = workspace / "with-context.conv"
        conv_file.write_text(f"""# Context Test
MODEL mock
ADAPTER mock
CWD {workspace}

REFCAT @context.md

PROMPT Analyze the context file.
""")

        return workspace

    def test_refcat_directive_loads_context(self, temp_workspace):
        """Test REFCAT directive creates refcat refs."""
        conv_path = temp_workspace / "with-context.conv"
        conv = ConversationFile.from_file(conv_path)

        # REFCAT stores refs for lazy loading
        assert len(conv.refcat_refs) > 0
        assert "@context.md" in conv.refcat_refs

    def test_cwd_directive_sets_working_dir(self, temp_workspace):
        """Test CWD directive sets working directory."""
        conv_path = temp_workspace / "with-context.conv"
        conv = ConversationFile.from_file(conv_path)

        assert conv.cwd is not None
        assert Path(conv.cwd).exists()


class TestRunCommandWorkflow:
    """Test run command step execution."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with RUN step test files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Conversation with RUN step
        conv_file = workspace / "with-run.conv"
        conv_file.write_text(f"""# Run Test
MODEL mock
ADAPTER mock
CWD {workspace}

PROMPT Prepare to run a command.

RUN echo "Hello from RUN step"

PROMPT Report on the command output.
""")

        return workspace

    def test_parse_run_steps(self, temp_workspace):
        """Test parsing RUN steps in conversation."""
        conv_path = temp_workspace / "with-run.conv"
        conv = ConversationFile.from_file(conv_path)

        run_steps = [s for s in conv.steps if s.type == "run"]
        assert len(run_steps) == 1
        assert "echo" in run_steps[0].content


class TestElideWorkflow:
    """Test ELIDE directive workflow."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create workspace with ELIDE test files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        conv_file = workspace / "with-elide.conv"
        conv_file.write_text("""# Elide Test
MODEL mock
ADAPTER mock

PROMPT First part of merged prompt.

ELIDE

PROMPT Second part of merged prompt.
""")

        return workspace

    def test_parse_elide_steps(self, temp_workspace):
        """Test parsing ELIDE directive."""
        conv_path = temp_workspace / "with-elide.conv"
        conv = ConversationFile.from_file(conv_path)

        elide_steps = [s for s in conv.steps if s.type == "elide"]
        assert len(elide_steps) == 1

    def test_elide_between_prompts(self, temp_workspace):
        """Test ELIDE is positioned between prompts."""
        conv_path = temp_workspace / "with-elide.conv"
        conv = ConversationFile.from_file(conv_path)

        step_types = [s.type for s in conv.steps]
        elide_idx = step_types.index("elide")

        # Should have prompt before and after
        assert step_types[elide_idx - 1] == "prompt"
        assert step_types[elide_idx + 1] == "prompt"
