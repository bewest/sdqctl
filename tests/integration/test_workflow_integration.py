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


class TestEndToEndWorkflows:
    """End-to-end workflow tests with mock adapter execution."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def complete_workflow(self, tmp_path):
        """Create a complete workflow with multiple step types."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create context file
        (workspace / "context.md").write_text("# Project Context\nThis is the context.")

        # Create complete workflow
        conv = workspace / "complete.conv"
        conv.write_text(f"""# Complete Workflow Test
MODEL mock
ADAPTER mock
CWD {workspace}
MAX-CYCLES 1

REFCAT @context.md

PROMPT Analyze the context and provide findings.

CHECKPOINT analysis-complete

PROMPT Summarize the analysis.
""")
        return conv

    def test_complete_workflow_dry_run(self, runner, complete_workflow):
        """Test complete workflow parses correctly in dry-run."""
        result = runner.invoke(cli, ["iterate", str(complete_workflow), "--dry-run"])
        assert result.exit_code == 0
        assert "mock" in result.output

    def test_workflow_with_checkpoint_parses(self, complete_workflow):
        """Test workflow with checkpoint parses correctly."""
        conv = ConversationFile.from_file(complete_workflow)

        assert conv.model == "mock"
        assert conv.adapter == "mock"
        assert len(conv.steps) >= 3  # 2 prompts + 1 checkpoint
        
        step_types = [s.type for s in conv.steps]
        assert "checkpoint" in step_types
        assert step_types.count("prompt") == 2


class TestErrorHandlingWorkflows:
    """Test workflow error handling scenarios."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def workflow_with_missing_context(self, tmp_path):
        """Create workflow referencing missing file."""
        conv = tmp_path / "missing-context.conv"
        conv.write_text("""# Missing Context Test
MODEL mock
ADAPTER mock

REFCAT @nonexistent-file.md

PROMPT This should fail due to missing context.
""")
        return conv

    def test_missing_context_detected(self, runner, workflow_with_missing_context):
        """Test that missing context files are detected."""
        result = runner.invoke(cli, ["validate", str(workflow_with_missing_context)])
        # Should report validation issue
        assert result.exit_code != 0 or "missing" in result.output.lower() or "not found" in result.output.lower() or "warning" in result.output.lower()


class TestVerifyWorkflows:
    """Test VERIFY directive workflows."""

    @pytest.fixture
    def verify_workflow(self, tmp_path):
        """Create workflow with VERIFY steps."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a requirements file for verification
        (workspace / "requirements.md").write_text("""# Requirements
## REQ-001: User Authentication
Users must authenticate before accessing the system.

## REQ-002: Data Validation
All input data must be validated.
""")

        conv = workspace / "verify.conv"
        conv.write_text(f"""# Verify Workflow Test
MODEL mock
ADAPTER mock
CWD {workspace}

PROMPT Analyze requirements.

VERIFY-TRACE REQ-001 -> TEST-001
""")
        return conv

    def test_verify_workflow_parses(self, verify_workflow):
        """Test VERIFY workflow parses correctly."""
        conv = ConversationFile.from_file(verify_workflow)

        step_types = [s.type for s in conv.steps]
        assert "verify_trace" in step_types


class TestCompactWorkflows:
    """Test COMPACT directive workflows."""

    @pytest.fixture
    def compact_workflow(self, tmp_path):
        """Create workflow with COMPACT directive."""
        conv = tmp_path / "compact.conv"
        conv.write_text("""# Compact Workflow Test
MODEL mock
ADAPTER mock
MAX-CYCLES 1

PROMPT First analysis phase.

COMPACT

PROMPT Second phase after compaction.
""")
        return conv

    def test_compact_workflow_parses(self, compact_workflow):
        """Test COMPACT workflow parses correctly."""
        conv = ConversationFile.from_file(compact_workflow)

        step_types = [s.type for s in conv.steps]
        assert "compact" in step_types
        assert step_types.count("prompt") == 2


class TestConsultWorkflows:
    """Test CONSULT directive workflow integration."""

    @pytest.fixture
    def consult_workflow(self, tmp_path):
        """Create workflow with CONSULT directive."""
        conv = tmp_path / "consult.conv"
        conv.write_text("""# Consult Workflow Test
MODEL mock
ADAPTER mock
SESSION-NAME design-review

PROMPT Analyze this proposal and identify open questions.

CONSULT Design Decisions

PROMPT Implement the resolved design based on answers.
""")
        return conv

    @pytest.fixture
    def consult_with_timeout(self, tmp_path):
        """Create workflow with CONSULT-TIMEOUT directive."""
        conv = tmp_path / "consult-timeout.conv"
        conv.write_text("""# Consult with Timeout
MODEL mock
ADAPTER mock

CONSULT-TIMEOUT 7d

PROMPT Analyze and identify questions.

CONSULT Architecture Review

PROMPT Continue after consultation.
""")
        return conv

    @pytest.fixture
    def multi_consult_workflow(self, tmp_path):
        """Create workflow with multiple CONSULT steps."""
        conv = tmp_path / "multi-consult.conv"
        conv.write_text("""# Multi-Consult Workflow
MODEL mock
ADAPTER mock
SESSION-NAME multi-review

PROMPT Initial analysis phase.

CONSULT Technical Review

PROMPT Implement technical changes.

CONSULT Security Review

PROMPT Apply security recommendations.
""")
        return conv

    def test_consult_workflow_parses(self, consult_workflow):
        """Test CONSULT workflow parses correctly."""
        conv = ConversationFile.from_file(consult_workflow)

        # CONSULT stored in consult_points, not steps
        assert len(conv.consult_points) > 0
        assert len(conv.steps) >= 2  # At least 2 prompts

    def test_consult_point_has_topic(self, consult_workflow):
        """Test CONSULT point captures topic."""
        conv = ConversationFile.from_file(consult_workflow)

        assert len(conv.consult_points) == 1
        step_idx, topic = conv.consult_points[0]
        assert "Design Decisions" in topic

    def test_consult_timeout_parses(self, consult_with_timeout):
        """Test CONSULT-TIMEOUT directive is parsed."""
        conv = ConversationFile.from_file(consult_with_timeout)

        # CONSULT-TIMEOUT should set a timeout value
        assert conv.consult_timeout is not None

    def test_multi_consult_workflow_parses(self, multi_consult_workflow):
        """Test multiple CONSULT points parse correctly."""
        conv = ConversationFile.from_file(multi_consult_workflow)

        assert len(conv.consult_points) == 2
        topics = [topic for _, topic in conv.consult_points]
        assert "Technical Review" in topics[0]
        assert "Security Review" in topics[1]

    def test_consult_with_session_name(self, consult_workflow):
        """Test CONSULT workflow with SESSION-NAME directive."""
        conv = ConversationFile.from_file(consult_workflow)

        assert conv.session_name == "design-review"

    def test_consult_point_step_index(self, consult_workflow):
        """Test CONSULT point references correct step index."""
        conv = ConversationFile.from_file(consult_workflow)

        # consult_points contains (step_index, topic) tuples
        assert len(conv.consult_points) == 1
        step_idx, _ = conv.consult_points[0]
        assert isinstance(step_idx, int)
        assert step_idx >= 0


class TestPauseWorkflows:
    """Test PAUSE directive workflow integration."""

    @pytest.fixture
    def pause_workflow(self, tmp_path):
        """Create workflow with PAUSE directive."""
        conv = tmp_path / "pause.conv"
        conv.write_text("""# Pause Workflow Test
MODEL mock
ADAPTER mock

PROMPT Analyze the code for issues.

PAUSE Review findings before proceeding

PROMPT Apply recommended fixes.
""")
        return conv

    def test_pause_workflow_parses(self, pause_workflow):
        """Test PAUSE workflow parses correctly."""
        conv = ConversationFile.from_file(pause_workflow)

        # PAUSE stored in pause_points, not steps
        assert len(conv.pause_points) > 0
        assert len(conv.steps) >= 2  # At least 2 prompts

    def test_pause_point_has_message(self, pause_workflow):
        """Test PAUSE point captures message."""
        conv = ConversationFile.from_file(pause_workflow)

        assert len(conv.pause_points) == 1
        step_idx, message = conv.pause_points[0]
        assert "Review findings" in message

    def test_pause_point_step_index(self, pause_workflow):
        """Test PAUSE point references correct step index."""
        conv = ConversationFile.from_file(pause_workflow)

        # pause_points contains (step_index, message) tuples
        assert len(conv.pause_points) == 1
        step_idx, _ = conv.pause_points[0]
        assert isinstance(step_idx, int)
        assert step_idx >= 0
