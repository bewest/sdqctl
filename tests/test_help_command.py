"""Tests for sdqctl help command."""

import pytest
from click.testing import CliRunner

from sdqctl.cli import cli
from sdqctl.commands.help import (
    TOPICS,
    COMMAND_HELP,
    get_overview,
    _list_topics,
)


@pytest.fixture
def cli_runner():
    """Click test runner."""
    return CliRunner()


class TestHelpCommand:
    """Test help command main entry."""
    
    def test_help_no_args(self, cli_runner):
        """Test sdqctl help with no arguments shows overview."""
        result = cli_runner.invoke(cli, ["help"])
        
        assert result.exit_code == 0
        assert "sdqctl" in result.output
        assert "Quick Start" in result.output
        assert "Commands" in result.output
        assert "Topics" in result.output
    
    def test_help_list_flag(self, cli_runner):
        """Test sdqctl help --list."""
        result = cli_runner.invoke(cli, ["help", "--list"])
        
        assert result.exit_code == 0
        assert "Commands" in result.output
        assert "Topics" in result.output
        assert "run" in result.output
        assert "directives" in result.output
    
    def test_help_unknown_topic(self, cli_runner):
        """Test sdqctl help with unknown topic."""
        result = cli_runner.invoke(cli, ["help", "nonexistent"])
        
        assert result.exit_code == 0
        assert "Unknown topic" in result.output
        # Should show available topics
        assert "Commands" in result.output
        assert "Topics" in result.output


class TestHelpCommands:
    """Test help for each command."""
    
    def test_help_run(self, cli_runner):
        """Test sdqctl help run."""
        result = cli_runner.invoke(cli, ["help", "run"])
        
        assert result.exit_code == 0
        assert "sdqctl run" in result.output
        assert "Usage" in result.output
        assert "--adapter" in result.output
    
    def test_help_cycle(self, cli_runner):
        """Test sdqctl help cycle."""
        result = cli_runner.invoke(cli, ["help", "cycle"])
        
        assert result.exit_code == 0
        assert "sdqctl cycle" in result.output
        assert "--max-cycles" in result.output or "max-cycles" in result.output.lower()
    
    def test_help_flow(self, cli_runner):
        """Test sdqctl help flow."""
        result = cli_runner.invoke(cli, ["help", "flow"])
        
        assert result.exit_code == 0
        assert "sdqctl flow" in result.output
        assert "--parallel" in result.output
    
    def test_help_apply(self, cli_runner):
        """Test sdqctl help apply."""
        result = cli_runner.invoke(cli, ["help", "apply"])
        
        assert result.exit_code == 0
        assert "sdqctl apply" in result.output
        assert "--components" in result.output
    
    def test_help_render(self, cli_runner):
        """Test sdqctl help render."""
        result = cli_runner.invoke(cli, ["help", "render"])
        
        assert result.exit_code == 0
        assert "sdqctl render" in result.output
    
    def test_help_verify(self, cli_runner):
        """Test sdqctl help verify."""
        result = cli_runner.invoke(cli, ["help", "verify"])
        
        assert result.exit_code == 0
        assert "sdqctl verify" in result.output
        assert "refs" in result.output
    
    def test_help_status(self, cli_runner):
        """Test sdqctl help status."""
        result = cli_runner.invoke(cli, ["help", "status"])
        
        assert result.exit_code == 0
        assert "sdqctl status" in result.output
        assert "--adapters" in result.output
    
    def test_help_validate(self, cli_runner):
        """Test sdqctl help validate."""
        result = cli_runner.invoke(cli, ["help", "validate"])
        
        assert result.exit_code == 0
        assert "sdqctl validate" in result.output
    
    def test_help_init(self, cli_runner):
        """Test sdqctl help init."""
        result = cli_runner.invoke(cli, ["help", "init"])
        
        assert result.exit_code == 0
        assert "sdqctl init" in result.output
    
    def test_help_resume(self, cli_runner):
        """Test sdqctl help resume."""
        result = cli_runner.invoke(cli, ["help", "resume"])
        
        assert result.exit_code == 0
        assert "sdqctl resume" in result.output
        assert "--list" in result.output
    
    def test_help_show(self, cli_runner):
        """Test sdqctl help show."""
        result = cli_runner.invoke(cli, ["help", "show"])
        
        assert result.exit_code == 0
        assert "sdqctl show" in result.output


class TestHelpTopics:
    """Test help for each topic."""
    
    def test_help_directives(self, cli_runner):
        """Test sdqctl help directives."""
        result = cli_runner.invoke(cli, ["help", "directives"])
        
        assert result.exit_code == 0
        assert "Directives" in result.output
        assert "MODEL" in result.output
        assert "PROMPT" in result.output
        assert "CONTEXT" in result.output
    
    def test_help_adapters(self, cli_runner):
        """Test sdqctl help adapters."""
        result = cli_runner.invoke(cli, ["help", "adapters"])
        
        assert result.exit_code == 0
        assert "Adapters" in result.output
        assert "mock" in result.output
        assert "copilot" in result.output
    
    def test_help_workflow(self, cli_runner):
        """Test sdqctl help workflow."""
        result = cli_runner.invoke(cli, ["help", "workflow"])
        
        assert result.exit_code == 0
        assert "ConversationFile" in result.output
        assert "MODEL" in result.output
    
    def test_help_variables(self, cli_runner):
        """Test sdqctl help variables."""
        result = cli_runner.invoke(cli, ["help", "variables"])
        
        assert result.exit_code == 0
        assert "Template Variables" in result.output
        assert "{{DATE}}" in result.output
        assert "{{CYCLE_NUMBER}}" in result.output
    
    def test_help_context(self, cli_runner):
        """Test sdqctl help context."""
        result = cli_runner.invoke(cli, ["help", "context"])
        
        assert result.exit_code == 0
        assert "Context" in result.output
        assert "CONTEXT-LIMIT" in result.output
    
    def test_help_examples(self, cli_runner):
        """Test sdqctl help examples."""
        result = cli_runner.invoke(cli, ["help", "examples"])
        
        assert result.exit_code == 0
        assert "Examples" in result.output
        assert "MODEL" in result.output


class TestHelpCaseInsensitive:
    """Test case insensitivity."""
    
    def test_help_uppercase_command(self, cli_runner):
        """Test sdqctl help RUN works."""
        result = cli_runner.invoke(cli, ["help", "RUN"])
        
        assert result.exit_code == 0
        assert "sdqctl run" in result.output
    
    def test_help_mixed_case_topic(self, cli_runner):
        """Test sdqctl help Directives works."""
        result = cli_runner.invoke(cli, ["help", "Directives"])
        
        assert result.exit_code == 0
        assert "Directives" in result.output


class TestHelpDataStructures:
    """Test internal data structures."""
    
    def test_all_commands_have_help(self):
        """Verify all expected commands have help entries."""
        expected_commands = [
            "run", "cycle", "flow", "apply", "render",
            "verify", "status", "validate", "init", "resume", "show"
        ]
        for cmd in expected_commands:
            assert cmd in COMMAND_HELP, f"Missing help for command: {cmd}"
    
    def test_all_topics_have_content(self):
        """Verify all topics have content."""
        expected_topics = [
            "directives", "adapters", "workflow",
            "variables", "context", "examples"
        ]
        for topic in expected_topics:
            assert topic in TOPICS, f"Missing topic: {topic}"
            assert len(TOPICS[topic]) > 100, f"Topic {topic} seems too short"
    
    def test_overview_contains_all_commands(self):
        """Verify overview mentions all commands."""
        overview = get_overview()
        commands = [
            "run", "cycle", "flow", "apply", "render", "verify",
            "validate", "status", "init", "resume", "show"
        ]
        for cmd in commands:
            assert cmd in overview, f"Overview missing command: {cmd}"
    
    def test_overview_contains_all_topics(self):
        """Verify overview mentions all topics."""
        overview = get_overview()
        for topic in TOPICS.keys():
            assert topic in overview, f"Overview missing topic: {topic}"


class TestHelpCommandHelp:
    """Test that help command itself has proper Click help."""
    
    def test_help_command_has_help(self, cli_runner):
        """Test sdqctl help --help works."""
        result = cli_runner.invoke(cli, ["help", "--help"])
        
        assert result.exit_code == 0
        assert "Show help for commands and topics" in result.output


class TestInteractiveHelp:
    """Tests for interactive help mode."""
    
    def test_interactive_flag_in_help(self, cli_runner):
        """Test --interactive flag appears in help."""
        result = cli_runner.invoke(cli, ["help", "--help"])
        
        assert result.exit_code == 0
        assert "--interactive" in result.output or "-i" in result.output
    
    def test_interactive_quit(self, cli_runner):
        """Test interactive mode exits on quit."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="q\n")
        
        assert result.exit_code == 0
        assert "Help Browser" in result.output
        assert "Exiting help browser" in result.output
    
    def test_interactive_list(self, cli_runner):
        """Test list command in interactive mode."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="list\nq\n")
        
        assert result.exit_code == 0
        assert "Commands" in result.output
        assert "Topics" in result.output
    
    def test_interactive_topic_lookup(self, cli_runner):
        """Test looking up a topic in interactive mode."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="run\nq\n")
        
        assert result.exit_code == 0
        assert "sdqctl run" in result.output
    
    def test_interactive_prefix_match(self, cli_runner):
        """Test prefix matching in interactive mode."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="dir\nq\n")
        
        assert result.exit_code == 0
        # Should match "directives"
        assert "Directives" in result.output or "directives" in result.output
    
    def test_interactive_unknown_topic(self, cli_runner):
        """Test unknown topic message in interactive mode."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="xyznonexistent\nq\n")
        
        assert result.exit_code == 0
        assert "Unknown" in result.output
    
    def test_interactive_overview(self, cli_runner):
        """Test overview command in interactive mode."""
        result = cli_runner.invoke(cli, ["help", "-i"], input="home\nq\n")
        
        assert result.exit_code == 0
        assert "sdqctl" in result.output
