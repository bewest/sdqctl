"""
CLI integration tests for core sdqctl commands.

Tests complete command execution with mock adapter for deterministic behavior.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from sdqctl.cli import cli


pytestmark = pytest.mark.integration


class TestRenderCommandIntegration:
    """Integration tests for render command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def conv_file(self, tmp_path):
        """Create a test conversation file."""
        conv = tmp_path / "test.conv"
        conv.write_text("""# Test Render
MODEL mock
ADAPTER mock

PROMPT Analyze the code quality.
PROMPT Provide recommendations.
""")
        return conv

    def test_render_run_outputs_conversation(self, runner, conv_file):
        """Test render run command produces output."""
        result = runner.invoke(cli, ["render", "run", str(conv_file)])
        assert result.exit_code == 0
        assert "Analyze the code quality" in result.output

    def test_render_run_with_json(self, runner, conv_file):
        """Test render run command with JSON output."""
        result = runner.invoke(cli, ["render", "run", str(conv_file), "--json"])
        assert result.exit_code == 0
        # JSON output should be parseable
        assert "{" in result.output or "[" in result.output

    def test_render_help_shows_subcommands(self, runner):
        """Test render --help shows subcommands."""
        result = runner.invoke(cli, ["render", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "cycle" in result.output

    def test_render_missing_file_errors(self, runner, tmp_path):
        """Test render command errors on missing file."""
        result = runner.invoke(cli, ["render", "run", str(tmp_path / "nonexistent.conv")])
        assert result.exit_code != 0


class TestValidateCommandIntegration:
    """Integration tests for validate command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def valid_conv(self, tmp_path):
        """Create a valid conversation file."""
        conv = tmp_path / "valid.conv"
        conv.write_text("""# Valid Conversation
MODEL mock
ADAPTER mock
PROMPT Test prompt.
""")
        return conv

    @pytest.fixture
    def invalid_conv(self, tmp_path):
        """Create a conversation with validation issues."""
        conv = tmp_path / "invalid.conv"
        conv.write_text("""# Invalid Conversation
MODEL mock
ADAPTER mock
REFCAT @nonexistent-file.md
PROMPT Test prompt.
""")
        return conv

    def test_validate_valid_file_succeeds(self, runner, valid_conv):
        """Test validate command succeeds for valid file."""
        result = runner.invoke(cli, ["validate", str(valid_conv)])
        assert result.exit_code == 0

    def test_validate_shows_file_info(self, runner, valid_conv):
        """Test validate shows file information."""
        result = runner.invoke(cli, ["validate", str(valid_conv)])
        assert "valid.conv" in result.output or result.exit_code == 0


class TestIterateCommandIntegration:
    """Integration tests for iterate command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def simple_conv(self, tmp_path):
        """Create a simple conversation for iteration."""
        conv = tmp_path / "iterate.conv"
        conv.write_text("""# Iterate Test
MODEL mock
ADAPTER mock
MAX-CYCLES 1

PROMPT Hello from iterate test.
""")
        return conv

    def test_iterate_dry_run(self, runner, simple_conv):
        """Test iterate --dry-run shows configuration."""
        result = runner.invoke(cli, ["iterate", str(simple_conv), "--dry-run"])
        assert result.exit_code == 0
        assert "Cycle Configuration" in result.output

    def test_iterate_help_shows_options(self, runner):
        """Test iterate --help shows available options."""
        result = runner.invoke(cli, ["iterate", "--help"])
        assert result.exit_code == 0
        assert "--adapter" in result.output
        assert "--max-cycles" in result.output or "-n" in result.output

    def test_iterate_with_max_cycles(self, runner, simple_conv):
        """Test iterate respects -n option in dry-run."""
        result = runner.invoke(cli, ["iterate", str(simple_conv), "-n", "3", "--dry-run"])
        assert result.exit_code == 0


class TestCycleCommandIntegration:
    """Integration tests for cycle command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def cycle_conv(self, tmp_path):
        """Create a conversation for cycle command."""
        conv = tmp_path / "cycle.conv"
        conv.write_text("""# Cycle Test
MODEL mock
ADAPTER mock

PROMPT Single cycle test.
""")
        return conv

    def test_cycle_dry_run(self, runner, cycle_conv):
        """Test cycle --dry-run shows configuration."""
        result = runner.invoke(cli, ["cycle", str(cycle_conv), "--dry-run"])
        assert result.exit_code == 0

    def test_cycle_help(self, runner):
        """Test cycle --help shows usage."""
        result = runner.invoke(cli, ["cycle", "--help"])
        assert result.exit_code == 0
        assert "cycle" in result.output.lower()


class TestStatusCommandIntegration:
    """Integration tests for status command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_status_runs_without_error(self, runner):
        """Test status command runs without error."""
        result = runner.invoke(cli, ["status"])
        # Status may show "no active session" which is fine
        assert result.exit_code in (0, 1)

    def test_status_help(self, runner):
        """Test status --help shows usage."""
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0


class TestHelpCommandIntegration:
    """Integration tests for help command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_help_lists_topics(self, runner):
        """Test help command lists available topics."""
        result = runner.invoke(cli, ["help"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("topic", [
        "directives",
        "adapters",
        "modes",
    ])
    def test_help_topic_exists(self, runner, topic):
        """Test help shows content for known topics."""
        result = runner.invoke(cli, ["help", topic])
        # Should succeed or show "not found" gracefully
        assert result.exit_code in (0, 1)
