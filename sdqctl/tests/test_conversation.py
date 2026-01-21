"""
Tests for ConversationFile parsing - sdqctl/core/conversation.py

P0 Critical - Core parser tests.
"""

import pytest
from pathlib import Path

from sdqctl.core.conversation import (
    ConversationFile,
    FileRestrictions,
    ConversationStep,
    DirectiveType,
    substitute_template_variables,
    get_standard_variables,
)


class TestConversationFileParsing:
    """Core parsing tests for ConversationFile.parse()"""

    def test_parse_basic_directives(self, sample_conv_content):
        """Test parsing MODEL, ADAPTER, MODE directives."""
        conv = ConversationFile.parse(sample_conv_content)
        
        assert conv.model == "gpt-4"
        assert conv.adapter == "mock"
        assert conv.mode == "audit"
        assert len(conv.prompts) == 1
        assert conv.prompts[0] == "Analyze the code."

    def test_parse_max_cycles(self):
        """Test parsing MAX-CYCLES directive."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES 5
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.max_cycles == 5

    def test_parse_cwd(self):
        """Test parsing CWD directive."""
        content = """MODEL gpt-4
ADAPTER mock
CWD /home/user/project
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.cwd == "/home/user/project"

    def test_parse_context_directives(self):
        """Test parsing CONTEXT, CONTEXT-LIMIT, ON-CONTEXT-LIMIT."""
        content = """MODEL gpt-4
ADAPTER mock
CONTEXT @lib/*.js
CONTEXT @src/**/*.py
CONTEXT-LIMIT 75%
ON-CONTEXT-LIMIT stop
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.context_files) == 2
        assert "@lib/*.js" in conv.context_files
        assert "@src/**/*.py" in conv.context_files
        assert conv.context_limit == 0.75
        assert conv.on_context_limit == "stop"

    def test_parse_file_restrictions(self, file_restrictions_conv_content):
        """Test parsing ALLOW-FILES, DENY-FILES, ALLOW-DIR, DENY-DIR."""
        conv = ConversationFile.parse(file_restrictions_conv_content)
        
        assert "lib/*.js" in conv.file_restrictions.allow_patterns
        assert "src/*.py" in conv.file_restrictions.allow_patterns
        assert "lib/secret.js" in conv.file_restrictions.deny_patterns
        assert "**/test_*.py" in conv.file_restrictions.deny_patterns
        assert "lib" in conv.file_restrictions.allow_dirs
        assert "node_modules" in conv.file_restrictions.deny_dirs

    def test_parse_prompt_injection(self, complex_conv_content):
        """Test parsing PROLOGUE, EPILOGUE."""
        conv = ConversationFile.parse(complex_conv_content)
        
        assert len(conv.prologues) == 1
        assert "Analysis date: 2026-01-20" in conv.prologues
        assert len(conv.epilogues) == 1
        assert "cite line numbers" in conv.epilogues[0]

    def test_parse_prompts(self):
        """Test parsing multiple PROMPT directives."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First prompt.
PROMPT Second prompt.
PROMPT Third prompt.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.prompts) == 3
        assert conv.prompts[0] == "First prompt."
        assert conv.prompts[1] == "Second prompt."
        assert conv.prompts[2] == "Third prompt."

    def test_parse_steps_from_prompts(self, steps_conv_content):
        """Test that steps list is populated when PROMPT is parsed."""
        conv = ConversationFile.parse(steps_conv_content)
        
        # Count prompt steps
        prompt_steps = [s for s in conv.steps if s.type == "prompt"]
        assert len(prompt_steps) == 3
        
        # Verify all step types present
        step_types = [s.type for s in conv.steps]
        assert "prompt" in step_types
        assert "checkpoint" in step_types
        assert "compact" in step_types
        assert "run" in step_types

    def test_parse_control_directives(self, steps_conv_content):
        """Test parsing COMPACT, NEW-CONVERSATION, CHECKPOINT."""
        conv = ConversationFile.parse(steps_conv_content)
        
        # Find checkpoint step
        checkpoint_steps = [s for s in conv.steps if s.type == "checkpoint"]
        assert len(checkpoint_steps) == 1
        assert checkpoint_steps[0].content == "after-analysis"
        
        # Find compact step
        compact_steps = [s for s in conv.steps if s.type == "compact"]
        assert len(compact_steps) == 1
        assert "findings" in compact_steps[0].preserve

    def test_parse_new_conversation(self):
        """Test parsing NEW-CONVERSATION directive."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Initial analysis.
NEW-CONVERSATION
PROMPT Fresh context analysis.
"""
        conv = ConversationFile.parse(content)
        
        new_conv_steps = [s for s in conv.steps if s.type == "new_conversation"]
        assert len(new_conv_steps) == 1

    def test_parse_output_directives(self, complex_conv_content):
        """Test parsing OUTPUT, OUTPUT-FORMAT, OUTPUT-FILE, OUTPUT-DIR."""
        conv = ConversationFile.parse(complex_conv_content)
        
        assert conv.output_format == "markdown"
        assert conv.output_file == "reports/quality-2026-01-20.md"

    def test_parse_header_footer(self, complex_conv_content):
        """Test parsing HEADER, FOOTER."""
        conv = ConversationFile.parse(complex_conv_content)
        
        assert len(conv.headers) == 1
        assert "# Quality Report" in conv.headers
        assert len(conv.footers) == 2
        assert "---" in conv.footers
        assert "Generated by sdqctl" in conv.footers

    def test_parse_run_directives(self):
        """Test parsing RUN, RUN-ON-ERROR, RUN-OUTPUT."""
        content = """MODEL gpt-4
ADAPTER mock
RUN npm run test
RUN-ON-ERROR continue
RUN-OUTPUT on-error
PROMPT Check results.
"""
        conv = ConversationFile.parse(content)
        
        run_steps = [s for s in conv.steps if s.type == "run"]
        assert len(run_steps) == 1
        assert run_steps[0].content == "npm run test"
        assert conv.run_on_error == "continue"
        assert conv.run_output == "on-error"

    def test_parse_pause(self, pause_conv_content):
        """Test parsing PAUSE directive with message."""
        conv = ConversationFile.parse(pause_conv_content)
        
        assert len(conv.pause_points) == 1
        pause_index, message = conv.pause_points[0]
        assert pause_index == 0  # After first prompt
        assert "Review findings" in message

    def test_multiline_prompt(self, multiline_conv_content):
        """Test multiline prompt parsing with indentation continuation."""
        conv = ConversationFile.parse(multiline_conv_content)
        
        assert len(conv.prompts) == 2
        # First prompt should have multiline content
        first_prompt = conv.prompts[0]
        assert "Analyze the code structure" in first_prompt
        assert "Authentication flow" in first_prompt
        assert "Error handling" in first_prompt
        assert "Performance concerns" in first_prompt

    def test_unknown_directive_ignored(self):
        """Test that unknown directives are ignored for forward compatibility."""
        content = """MODEL gpt-4
ADAPTER mock
FUTURE-DIRECTIVE some-value
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model == "gpt-4"
        assert len(conv.prompts) == 1
        # Should not raise error

    def test_comments_ignored(self):
        """Test that comment lines are ignored."""
        content = """# This is a comment
MODEL gpt-4
# Another comment
ADAPTER mock
PROMPT Test.
# Trailing comment
"""
        conv = ConversationFile.parse(content)
        
        assert conv.model == "gpt-4"
        assert conv.adapter == "mock"
        assert len(conv.prompts) == 1

    def test_empty_lines_ignored(self):
        """Test that empty lines are handled correctly."""
        content = """MODEL gpt-4

ADAPTER mock


PROMPT Test.

"""
        conv = ConversationFile.parse(content)
        
        assert conv.model == "gpt-4"
        assert conv.adapter == "mock"


class TestFileRestrictions:
    """Tests for FileRestrictions logic."""

    def test_deny_wins_over_allow(self):
        """Test that deny patterns take precedence over allow."""
        restrictions = FileRestrictions(
            allow_patterns=["lib/*.js"],
            deny_patterns=["lib/secret.js"],
        )
        
        assert restrictions.is_path_allowed("lib/auth.js") is True
        assert restrictions.is_path_allowed("lib/secret.js") is False

    def test_allow_patterns_filter(self):
        """Test that only allowed patterns pass when specified."""
        restrictions = FileRestrictions(
            allow_patterns=["lib/*.js"],
        )
        
        assert restrictions.is_path_allowed("lib/auth.js") is True
        assert restrictions.is_path_allowed("src/main.py") is False

    def test_allow_dirs_filter(self):
        """Test directory-based allow filtering."""
        restrictions = FileRestrictions(
            allow_dirs=["lib", "src"],
        )
        
        assert restrictions.is_path_allowed("lib/auth.js") is True
        assert restrictions.is_path_allowed("src/main.py") is True
        # Note: is_path_allowed uses relative_to which requires proper paths
        # This is a simplified test

    def test_deny_dirs_filter(self):
        """Test directory-based deny filtering."""
        restrictions = FileRestrictions(
            deny_dirs=["node_modules"],
        )
        
        # Paths not under node_modules should pass
        assert restrictions.is_path_allowed("lib/auth.js") is True

    def test_merge_with_cli(self):
        """Test CLI restrictions merge behavior."""
        file_restrictions = FileRestrictions(
            allow_patterns=["*.js"],
            deny_patterns=["*.test.js"],
        )
        
        merged = file_restrictions.merge_with_cli(
            cli_allow=["*.py"],  # CLI overrides allow
            cli_deny=["*.min.js"],  # CLI adds to deny
        )
        
        # CLI allow replaces file allow
        assert merged.allow_patterns == ["*.py"]
        # CLI deny adds to file deny
        assert "*.min.js" in merged.deny_patterns
        assert "*.test.js" in merged.deny_patterns

    def test_no_restrictions_allows_all(self):
        """Test that empty restrictions allow all paths."""
        restrictions = FileRestrictions()
        
        assert restrictions.is_path_allowed("any/path/file.txt") is True
        assert restrictions.is_path_allowed("lib/secret.js") is True


class TestTemplateVariables:
    """Tests for template variable substitution."""

    def test_substitute_date_variables(self):
        """Test DATE, DATETIME substitution."""
        text = "Report for {{DATE}}"
        variables = {"DATE": "2026-01-20"}
        
        result = substitute_template_variables(text, variables)
        assert result == "Report for 2026-01-20"

    def test_substitute_workflow_variables(self):
        """Test WORKFLOW_NAME, WORKFLOW_PATH substitution."""
        text = "Running {{WORKFLOW_NAME}} from {{WORKFLOW_PATH}}"
        variables = {
            "WORKFLOW_NAME": "security-audit",
            "WORKFLOW_PATH": "/home/user/workflows/security-audit.conv",
        }
        
        result = substitute_template_variables(text, variables)
        assert "security-audit" in result
        assert "/home/user/workflows" in result

    def test_substitute_component_variables(self):
        """Test COMPONENT_PATH, COMPONENT_NAME, etc."""
        text = "Analyzing {{COMPONENT_NAME}} in {{COMPONENT_DIR}}"
        variables = {
            "COMPONENT_NAME": "auth.js",
            "COMPONENT_DIR": "lib",
        }
        
        result = substitute_template_variables(text, variables)
        assert result == "Analyzing auth.js in lib"

    def test_substitute_multiple_same_variable(self):
        """Test same variable appearing multiple times."""
        text = "{{DATE}} report. Date: {{DATE}}"
        variables = {"DATE": "2026-01-20"}
        
        result = substitute_template_variables(text, variables)
        assert result == "2026-01-20 report. Date: 2026-01-20"

    def test_get_standard_variables(self):
        """Test standard variables are populated."""
        variables = get_standard_variables()
        
        assert "DATE" in variables
        assert "DATETIME" in variables
        assert "CWD" in variables

    def test_get_standard_variables_with_workflow_path(self, tmp_path):
        """Test variables with workflow path."""
        workflow_file = tmp_path / "test.conv"
        workflow_file.write_text("MODEL gpt-4")
        
        variables = get_standard_variables(workflow_file)
        
        assert variables["WORKFLOW_NAME"] == "test"
        assert "test.conv" in variables["WORKFLOW_PATH"]


class TestConversationFileToString:
    """Tests for serialization back to .conv format."""

    def test_to_string_basic(self, sample_conv_content):
        """Test basic round-trip serialization."""
        conv = ConversationFile.parse(sample_conv_content)
        output = conv.to_string()
        
        assert "MODEL gpt-4" in output
        assert "ADAPTER mock" in output
        assert "MODE audit" in output
        assert "PROMPT Analyze the code." in output

    def test_to_string_preserves_restrictions(self, file_restrictions_conv_content):
        """Test file restrictions are serialized."""
        conv = ConversationFile.parse(file_restrictions_conv_content)
        output = conv.to_string()
        
        assert "ALLOW-FILES lib/*.js" in output
        assert "DENY-FILES lib/secret.js" in output
        assert "ALLOW-DIR lib" in output
        assert "DENY-DIR node_modules" in output

    def test_to_string_preserves_injection(self, complex_conv_content):
        """Test prologue/epilogue/header/footer serialized."""
        conv = ConversationFile.parse(complex_conv_content)
        output = conv.to_string()
        
        assert "PROLOGUE Analysis date" in output
        assert "EPILOGUE Remember to cite" in output
        assert "HEADER # Quality Report" in output
        assert "FOOTER ---" in output

    def test_to_string_multiline_prompt(self, multiline_conv_content):
        """Test multiline prompts are serialized with indentation."""
        conv = ConversationFile.parse(multiline_conv_content)
        output = conv.to_string()
        
        assert "PROMPT Analyze the code structure" in output
        # Continuation lines should have indentation
        lines = output.split("\n")
        continuation_found = any(line.startswith("  ") for line in lines)
        assert continuation_found


class TestConversationFileFromFile:
    """Tests for loading from file."""

    def test_from_file(self, tmp_path, sample_conv_content):
        """Test loading conversation from file."""
        conv_file = tmp_path / "test.conv"
        conv_file.write_text(sample_conv_content)
        
        conv = ConversationFile.from_file(conv_file)
        
        assert conv.model == "gpt-4"
        assert conv.source_path == conv_file

    def test_from_file_str_path(self, tmp_path, sample_conv_content):
        """Test loading with string path."""
        conv_file = tmp_path / "test.conv"
        conv_file.write_text(sample_conv_content)
        
        conv = ConversationFile.from_file(str(conv_file))
        
        assert conv.model == "gpt-4"


class TestConversationDefaults:
    """Test default values when directives not specified."""

    def test_defaults(self):
        """Test all defaults are set correctly."""
        conv = ConversationFile()
        
        assert conv.model == "gpt-4"
        assert conv.adapter == "copilot"
        assert conv.mode == "full"
        assert conv.max_cycles == 1
        assert conv.context_limit == 0.8
        assert conv.on_context_limit == "compact"
        assert conv.output_format == "markdown"
        assert conv.run_on_error == "stop"
        assert conv.run_output == "always"
