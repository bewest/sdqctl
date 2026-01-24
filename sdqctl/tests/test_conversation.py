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
from sdqctl.commands.run import process_elided_steps


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

    def test_parse_compact_prologue_epilogue(self):
        """Test parsing COMPACT-PROLOGUE and COMPACT-EPILOGUE directives."""
        content = """MODEL gpt-4
ADAPTER mock
COMPACT-PROLOGUE This conversation has been compacted. Previous context:
COMPACT-EPILOGUE Continue from the summary above.
PROMPT Analyze the code.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.compact_prologue == "This conversation has been compacted. Previous context:"
        assert conv.compact_epilogue == "Continue from the summary above."

    def test_parse_elide_directive(self):
        """Test parsing ELIDE directive creates elide step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze test results.
ELIDE
PROMPT Fix any errors found.
"""
        conv = ConversationFile.parse(content)
        
        elide_steps = [s for s in conv.steps if s.type == "elide"]
        assert len(elide_steps) == 1
        
        # Should have 2 prompts and 1 elide
        assert len(conv.prompts) == 2
        step_types = [s.type for s in conv.steps]
        assert step_types == ["prompt", "elide", "prompt"]

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

    def test_parse_run_retry(self):
        """Test parsing RUN-RETRY directive."""
        content = """MODEL gpt-4
ADAPTER mock
RUN npm test
RUN-RETRY 3 "Fix the failing tests based on error output"
PROMPT Verify all tests pass.
"""
        conv = ConversationFile.parse(content)
        
        run_steps = [s for s in conv.steps if s.type == "run"]
        assert len(run_steps) == 1
        assert run_steps[0].content == "npm test"
        assert run_steps[0].retry_count == 3
        assert run_steps[0].retry_prompt == "Fix the failing tests based on error output"

    def test_parse_run_retry_single_quotes(self):
        """Test parsing RUN-RETRY with single quotes."""
        content = """RUN pytest
RUN-RETRY 2 'Analyze and fix errors'
"""
        conv = ConversationFile.parse(content)
        
        run_steps = [s for s in conv.steps if s.type == "run"]
        assert len(run_steps) == 1
        assert run_steps[0].retry_count == 2
        assert run_steps[0].retry_prompt == "Analyze and fix errors"

    def test_parse_run_retry_fallback_format(self):
        """Test parsing RUN-RETRY with fallback format (no quotes)."""
        content = """RUN make build
RUN-RETRY 1 Fix build errors
"""
        conv = ConversationFile.parse(content)
        
        run_steps = [s for s in conv.steps if s.type == "run"]
        assert len(run_steps) == 1
        assert run_steps[0].retry_count == 1
        assert run_steps[0].retry_prompt == "Fix build errors"

    def test_parse_pause(self, pause_conv_content):
        """Test parsing PAUSE directive with message."""
        conv = ConversationFile.parse(pause_conv_content)
        
        assert len(conv.pause_points) == 1
        pause_index, message = conv.pause_points[0]
        assert pause_index == 0  # After first prompt
        assert "Review findings" in message

    def test_parse_debug_directives(self):
        """Test parsing DEBUG, DEBUG-INTENTS, and EVENT-LOG directives."""
        content = """MODEL gpt-4
ADAPTER copilot
DEBUG session, tool, intent
DEBUG-INTENTS true
EVENT-LOG ./logs/events-{{DATETIME}}.jsonl
PROMPT Test workflow.
"""
        conv = ConversationFile.parse(content)
        
        assert conv.debug_categories == ["session", "tool", "intent"]
        assert conv.debug_intents is True
        assert conv.event_log == "./logs/events-{{DATETIME}}.jsonl"

    def test_parse_debug_intents_false(self):
        """Test DEBUG-INTENTS false parsing."""
        content = """MODEL gpt-4
DEBUG-INTENTS false
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.debug_intents is False

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
        """Test variables with workflow path.
        
        Note: WORKFLOW_NAME is excluded by default to avoid Q-001.
        Use include_workflow_vars=True for output paths.
        """
        workflow_file = tmp_path / "test.conv"
        workflow_file.write_text("MODEL gpt-4")
        
        # Default: WORKFLOW_NAME excluded (Q-001 fix)
        variables = get_standard_variables(workflow_file)
        assert "WORKFLOW_NAME" not in variables
        assert "WORKFLOW_PATH" not in variables
        # But explicit opt-in is always available
        assert variables["__WORKFLOW_NAME__"] == "test"
        assert "test.conv" in variables["__WORKFLOW_PATH__"]
        
        # With include_workflow_vars=True: for output paths
        output_vars = get_standard_variables(workflow_file, include_workflow_vars=True)
        assert output_vars["WORKFLOW_NAME"] == "test"
        assert "test.conv" in output_vars["WORKFLOW_PATH"]

    def test_get_standard_variables_with_stop_file_nonce(self):
        """Test STOP_FILE variable with nonce (Q-002).
        
        When stop_file_nonce is provided, STOP_FILE includes the nonce
        for agent stop signaling.
        """
        # Without nonce: no stop file variable
        variables = get_standard_variables()
        assert "STOP_FILE" not in variables
        
        # With nonce: stop file variable included
        variables = get_standard_variables(stop_file_nonce="abc123def456")
        assert variables["STOP_FILE"] == "STOPAUTOMATION-abc123def456.json"
        
        # Same nonce produces same stop file name
        variables2 = get_standard_variables(stop_file_nonce="abc123def456")
        assert variables["STOP_FILE"] == variables2["STOP_FILE"]
        
        # Different nonce produces different stop file name
        variables3 = get_standard_variables(stop_file_nonce="different123")
        assert variables["STOP_FILE"] != variables3["STOP_FILE"]


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


class TestConversationFileFromRenderedJson:
    """Tests for loading from rendered JSON."""

    def test_from_rendered_json_basic(self):
        """Test basic JSON loading."""
        json_data = {
            "schema_version": "1.0",
            "workflow": "test.conv",
            "workflow_name": "test",
            "mode": "full",
            "session_mode": "accumulate",
            "adapter": "mock",
            "model": "gpt-4-turbo",
            "max_cycles": 3,
            "template_variables": {"DATE": "2026-01-23"},
            "cycles": [{
                "number": 1,
                "variables": {"CYCLE_NUMBER": "1"},
                "context_files": [],
                "prompts": [{
                    "index": 1,
                    "raw": "Analyze the code",
                    "prologues": [],
                    "epilogues": [],
                    "resolved": "Full prompt text here",
                }],
            }],
        }
        
        conv = ConversationFile.from_rendered_json(json_data)
        
        assert conv.adapter == "mock"
        assert conv.model == "gpt-4-turbo"
        assert conv.max_cycles == 3
        assert len(conv.prompts) == 1
        assert conv.prompts[0] == "Full prompt text here"

    def test_from_rendered_json_with_context(self):
        """Test JSON with context files."""
        json_data = {
            "schema_version": "1.0",
            "adapter": "copilot",
            "model": "gpt-4",
            "max_cycles": 1,
            "cycles": [{
                "number": 1,
                "context_files": [
                    {"path": "lib/auth.js", "content": "// auth code", "tokens_estimate": 100},
                    {"path": "test.js", "content": "// test code", "tokens_estimate": 50},
                ],
                "prompts": [
                    {"resolved": "Analyze this code", "raw": "Analyze"},
                ],
            }],
        }
        
        conv = ConversationFile.from_rendered_json(json_data)
        
        assert len(conv._preloaded_context) == 2
        assert conv._preloaded_context[0]["path"] == "lib/auth.js"

    def test_from_rendered_json_schema_version_check(self):
        """Test schema version validation."""
        json_data = {
            "schema_version": "2.0",  # Unsupported major version
            "adapter": "mock",
        }
        
        with pytest.raises(ValueError, match="Unsupported schema version"):
            ConversationFile.from_rendered_json(json_data)

    def test_from_rendered_json_defaults(self):
        """Test defaults when fields missing."""
        json_data = {"cycles": []}
        
        conv = ConversationFile.from_rendered_json(json_data)
        
        assert conv.adapter == "copilot"
        assert conv.model == "gpt-4"
        assert conv.max_cycles == 1


class TestConversationDefaults:
    """Test default values when directives not specified."""

    def test_defaults(self, tmp_path, monkeypatch):
        """Test all defaults are set correctly (with no config file)."""
        # Ensure no config file affects defaults
        from sdqctl.core.config import clear_config_cache
        monkeypatch.chdir(tmp_path)
        clear_config_cache()
        
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


class TestElisionProcessing:
    """Tests for process_elided_steps() function."""

    def test_no_elision_returns_unchanged(self):
        """Steps without ELIDE are returned unchanged."""
        steps = [
            ConversationStep(type="prompt", content="First prompt"),
            ConversationStep(type="prompt", content="Second prompt"),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 2
        assert result[0].type == "prompt"
        assert result[1].type == "prompt"

    def test_elide_merges_two_prompts(self):
        """ELIDE between two prompts merges them into a merged_prompt."""
        steps = [
            ConversationStep(type="prompt", content="Analyze this."),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix any errors."),
        ]
        result = process_elided_steps(steps)
        
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert "Analyze this." in result[0].content
        assert "Fix any errors." in result[0].content

    def test_elide_merges_prompt_run_prompt(self):
        """ELIDE merges RUN above with PROMPT below, first prompt is separate."""
        steps = [
            ConversationStep(type="prompt", content="Check tests."),
            ConversationStep(type="run", content="pytest -v"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Fix failures."),
        ]
        result = process_elided_steps(steps)
        
        # First prompt is standalone, RUN and second prompt are merged
        assert len(result) == 2
        assert result[0].type == "prompt"
        assert result[0].content == "Check tests."
        assert result[1].type == "merged_prompt"
        assert "{{RUN:0:pytest -v}}" in result[1].content
        assert "Fix failures." in result[1].content
        # The merged step has run_commands attached
        assert hasattr(result[1], 'run_commands')
        assert result[1].run_commands == ["pytest -v"]

    def test_multiple_elide_groups(self):
        """Multiple ELIDE groups are processed independently."""
        steps = [
            ConversationStep(type="prompt", content="First."),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Second."),
            ConversationStep(type="prompt", content="Third standalone."),
        ]
        result = process_elided_steps(steps)
        
        # First two should be merged, third standalone
        assert len(result) == 2
        assert result[0].type == "merged_prompt"
        assert "First." in result[0].content
        assert "Second." in result[0].content
        assert result[1].type == "prompt"
        assert result[1].content == "Third standalone."

    def test_empty_steps_returns_empty(self):
        """Empty steps list returns empty list."""
        result = process_elided_steps([])
        assert result == []

    def test_elide_with_checkpoint_warns(self):
        """Control steps like checkpoint in ELIDE group should warn."""
        steps = [
            ConversationStep(type="prompt", content="Before."),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="checkpoint", content="cp1"),
        ]
        # Should still process without error
        result = process_elided_steps(steps)
        assert len(result) >= 1

    def test_chained_elides_merge_all(self):
        """Multiple consecutive ELIDEs chain together to merge multiple elements."""
        steps = [
            ConversationStep(type="prompt", content="First."),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="run", content="echo test"),
            ConversationStep(type="elide", content=""),
            ConversationStep(type="prompt", content="Last."),
        ]
        result = process_elided_steps(steps)
        
        # All elements should be merged into one
        assert len(result) == 1
        assert result[0].type == "merged_prompt"
        assert "First." in result[0].content
        assert "{{RUN:0:echo test}}" in result[0].content
        assert "Last." in result[0].content


class TestVerifyDirectiveParsing:
    """Tests for VERIFY directive parsing."""

    def test_parse_verify_simple(self):
        """Test parsing basic VERIFY directive."""
        content = """MODEL gpt-4
VERIFY refs
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 1
        assert verify_steps[0].verify_type == "refs"
        assert verify_steps[0].verify_options == {}

    def test_parse_verify_with_options(self):
        """Test parsing VERIFY with --option flags."""
        content = """MODEL gpt-4
VERIFY links --external --timeout=30
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 1
        assert verify_steps[0].verify_type == "links"
        assert verify_steps[0].verify_options == {"external": "true", "timeout": "30"}

    def test_parse_verify_all(self):
        """Test parsing VERIFY all."""
        content = """MODEL gpt-4
VERIFY all
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 1
        assert verify_steps[0].verify_type == "all"

    def test_parse_verify_on_error(self):
        """Test parsing VERIFY-ON-ERROR directive."""
        content = """MODEL gpt-4
VERIFY-ON-ERROR continue
VERIFY refs
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        assert conv.verify_on_error == "continue"

    def test_parse_verify_output(self):
        """Test parsing VERIFY-OUTPUT directive."""
        content = """MODEL gpt-4
VERIFY-OUTPUT always
VERIFY refs
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        assert conv.verify_output == "always"

    def test_parse_verify_limit(self):
        """Test parsing VERIFY-LIMIT directive."""
        content = """MODEL gpt-4
VERIFY-LIMIT 10K
VERIFY refs
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        assert conv.verify_limit == 10000

    def test_parse_verify_limit_megabytes(self):
        """Test parsing VERIFY-LIMIT with M suffix."""
        content = """MODEL gpt-4
VERIFY-LIMIT 1M
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        assert conv.verify_limit == 1000000

    def test_parse_multiple_verify_steps(self):
        """Test parsing multiple VERIFY directives."""
        content = """MODEL gpt-4
VERIFY refs
VERIFY links
VERIFY traceability
PROMPT Analyze all results.
"""
        conv = ConversationFile.parse(content)
        
        verify_steps = [s for s in conv.steps if s.type == "verify"]
        assert len(verify_steps) == 3
        assert verify_steps[0].verify_type == "refs"
        assert verify_steps[1].verify_type == "links"
        assert verify_steps[2].verify_type == "traceability"


class TestRefcatDirectiveParsing:
    """Tests for REFCAT directive parsing."""

    def test_parse_refcat_single_ref(self):
        """Test parsing single REFCAT ref."""
        content = """MODEL gpt-4
REFCAT @sdqctl/core/context.py#L10-L50
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.refcat_refs) == 1
        assert conv.refcat_refs[0] == "@sdqctl/core/context.py#L10-L50"

    def test_parse_refcat_multiple_refs_one_line(self):
        """Test parsing multiple REFCAT refs on one line."""
        content = """MODEL gpt-4
REFCAT @file1.py#L1-L10 @file2.py#L20-L30
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.refcat_refs) == 2
        assert "@file1.py#L1-L10" in conv.refcat_refs
        assert "@file2.py#L20-L30" in conv.refcat_refs

    def test_parse_refcat_multiple_directives(self):
        """Test parsing multiple REFCAT directives."""
        content = """MODEL gpt-4
REFCAT @context.py#L10-L50
REFCAT @renderer.py#L1-L20
REFCAT loop:LoopKit/Sources/Algorithm.swift#L100
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.refcat_refs) == 3
        assert "@context.py#L10-L50" in conv.refcat_refs
        assert "@renderer.py#L1-L20" in conv.refcat_refs
        assert "loop:LoopKit/Sources/Algorithm.swift#L100" in conv.refcat_refs

    def test_parse_refcat_with_alias(self):
        """Test parsing REFCAT with alias prefix."""
        content = """MODEL gpt-4
REFCAT loop:LoopKit/Sources/Algorithm.swift#L100-L200
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.refcat_refs) == 1
        assert conv.refcat_refs[0] == "loop:LoopKit/Sources/Algorithm.swift#L100-L200"

    def test_parse_refcat_single_line(self):
        """Test parsing REFCAT with single line ref."""
        content = """MODEL gpt-4
REFCAT @file.py#L10
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.refcat_refs) == 1
        assert conv.refcat_refs[0] == "@file.py#L10"

    def test_to_string_includes_refcat(self):
        """Test that to_string() serializes REFCAT refs."""
        content = """MODEL gpt-4
REFCAT @file.py#L10-L50
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        output = conv.to_string()
        
        assert "REFCAT @file.py#L10-L50" in output


class TestRefcatValidation:
    """Tests for REFCAT ref validation."""

    def test_validate_refcat_existing_file(self, tmp_path):
        """Validate REFCAT refs to existing files succeed."""
        # Create test file
        test_file = tmp_path / "sample.py"
        test_file.write_text("line 1\nline 2\nline 3")
        
        content = f"""MODEL gpt-4
REFCAT @{test_file}#L1-L2
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content, source_path=tmp_path / "test.conv")
        errors, warnings = conv.validate_refcat_refs()
        
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_refcat_missing_file(self, tmp_path):
        """Validate REFCAT refs to missing files fail."""
        content = """MODEL gpt-4
REFCAT @nonexistent.py#L1-L10
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content, source_path=tmp_path / "test.conv")
        errors, warnings = conv.validate_refcat_refs()
        
        assert len(errors) == 1
        assert "nonexistent.py" in errors[0][0]

    def test_validate_refcat_allow_missing(self, tmp_path):
        """Validate REFCAT refs with allow_missing returns warnings."""
        content = """MODEL gpt-4
REFCAT @nonexistent.py#L1-L10
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content, source_path=tmp_path / "test.conv")
        errors, warnings = conv.validate_refcat_refs(allow_missing=True)
        
        assert len(errors) == 0
        assert len(warnings) == 1

    def test_validate_refcat_invalid_syntax(self, tmp_path):
        """Validate REFCAT refs with invalid syntax fail."""
        content = """MODEL gpt-4
REFCAT invalid#syntax
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content, source_path=tmp_path / "test.conv")
        errors, warnings = conv.validate_refcat_refs()
        
        # Should have an error (either parse or file not found)
        assert len(errors) == 1


class TestHelpDirectiveParsing:
    """Tests for HELP directive parsing."""

    def test_parse_help_single_topic(self):
        """Test parsing single HELP topic."""
        content = """MODEL gpt-4
HELP directives
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.help_topics) == 1
        assert "directives" in conv.help_topics

    def test_parse_help_multiple_topics(self):
        """Test parsing multiple HELP topics on one line."""
        content = """MODEL gpt-4
HELP directives workflow variables
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.help_topics) == 3
        assert "directives" in conv.help_topics
        assert "workflow" in conv.help_topics
        assert "variables" in conv.help_topics

    def test_parse_help_multiple_directives(self):
        """Test parsing multiple HELP directives."""
        content = """MODEL gpt-4
HELP directives
HELP workflow
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.help_topics) == 2
        assert "directives" in conv.help_topics
        assert "workflow" in conv.help_topics

    def test_help_to_string(self):
        """Test that to_string() serializes HELP topics."""
        content = """MODEL gpt-4
HELP directives workflow
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        output = conv.to_string()
        
        assert "HELP directives workflow" in output


class TestHelpDirectiveValidation:
    """Tests for HELP topic validation."""

    def test_validate_help_known_topics(self):
        """Validate known HELP topics succeed."""
        content = """MODEL gpt-4
HELP directives adapters workflow
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_help_topics()
        
        assert len(errors) == 0

    def test_validate_help_unknown_topic(self):
        """Validate unknown HELP topics fail."""
        content = """MODEL gpt-4
HELP nonexistent_topic
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_help_topics()
        
        assert len(errors) == 1
        assert "nonexistent_topic" in errors[0][0]
        assert "Unknown help topic" in errors[0][1]

    def test_validate_help_mixed_known_unknown(self):
        """Validate mixed known/unknown topics returns errors for unknown only."""
        content = """MODEL gpt-4
HELP directives invalid_topic workflow
PROMPT Analyze.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_help_topics()
        
        assert len(errors) == 1
        assert "invalid_topic" in errors[0][0]


class TestElideChainValidation:
    """Tests for ELIDE chain validation (RUN-RETRY incompatibility)."""

    def test_run_retry_without_elide_is_valid(self):
        """RUN-RETRY without ELIDE should be valid."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
RUN-RETRY 3 "Fix tests"
PROMPT Summarize.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) == 0

    def test_run_retry_inside_elide_chain_is_invalid(self):
        """RUN-RETRY inside ELIDE chain should be rejected."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze.
ELIDE
RUN pytest
RUN-RETRY 3 "Fix tests"
ELIDE
PROMPT Summarize.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) == 1
        assert "RUN-RETRY" in errors[0]
        assert "ELIDE" in errors[0]

    def test_run_inside_elide_chain_without_retry_is_valid(self):
        """RUN without retry inside ELIDE chain should be valid."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze.
ELIDE
RUN pytest -v
ELIDE
PROMPT Summarize the results.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) == 0

    def test_elide_after_run_retry_is_valid(self):
        """ELIDE after RUN-RETRY (not inside chain) should be valid."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
RUN-RETRY 3 "Fix tests"
PROMPT Review.
ELIDE
PROMPT Summarize.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) == 0


class TestRequireDirectiveParsing:
    """Tests for REQUIRE directive parsing."""

    def test_parse_single_file_requirement(self):
        """Test parsing REQUIRE with a single file."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @pyproject.toml
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.requirements) == 1
        assert "@pyproject.toml" in conv.requirements

    def test_parse_single_command_requirement(self):
        """Test parsing REQUIRE with a command."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE cmd:git
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.requirements) == 1
        assert "cmd:git" in conv.requirements

    def test_parse_multiple_requirements_one_line(self):
        """Test parsing REQUIRE with multiple items on one line."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @README.md cmd:python @pyproject.toml
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.requirements) == 3
        assert "@README.md" in conv.requirements
        assert "cmd:python" in conv.requirements
        assert "@pyproject.toml" in conv.requirements

    def test_parse_multiple_require_directives(self):
        """Test parsing multiple REQUIRE directives."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @README.md
REQUIRE cmd:git
REQUIRE @pyproject.toml
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.requirements) == 3


class TestRequireDirectiveValidation:
    """Tests for REQUIRE directive validation."""

    def test_validate_existing_file_passes(self, tmp_path):
        """Test that requiring an existing file passes validation."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")
        
        content = f"""MODEL gpt-4
ADAPTER mock
REQUIRE @test.md
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements(base_path=tmp_path)
        
        assert len(errors) == 0

    def test_validate_missing_file_fails(self, tmp_path):
        """Test that requiring a missing file fails validation."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @nonexistent-file-12345.md
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements(base_path=tmp_path)
        
        assert len(errors) == 1
        assert "not found" in errors[0][1]
        assert "nonexistent-file-12345.md" in errors[0][1]

    def test_validate_existing_command_passes(self):
        """Test that requiring an existing command passes validation."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE cmd:python
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements()
        
        # python should exist in most environments
        assert len(errors) == 0

    def test_validate_missing_command_fails(self):
        """Test that requiring a missing command fails validation."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE cmd:nonexistent-command-12345
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements()
        
        assert len(errors) == 1
        assert "not found" in errors[0][1]
        assert "nonexistent-command-12345" in errors[0][1]

    def test_validate_glob_pattern_with_matches(self, tmp_path):
        """Test that requiring a glob pattern that matches passes."""
        # Create test files
        (tmp_path / "test1.py").write_text("# test")
        (tmp_path / "test2.py").write_text("# test")
        
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @*.py
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements(base_path=tmp_path)
        
        assert len(errors) == 0

    def test_validate_glob_pattern_without_matches_fails(self, tmp_path):
        """Test that requiring a glob pattern with no matches fails."""
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @*.nonexistent
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements(base_path=tmp_path)
        
        assert len(errors) == 1
        assert "not found" in errors[0][1]

    def test_validate_mixed_requirements(self, tmp_path):
        """Test validation with mixed file and command requirements."""
        # Create one test file
        (tmp_path / "exists.md").write_text("# exists")
        
        content = """MODEL gpt-4
ADAPTER mock
REQUIRE @exists.md cmd:python @missing.md cmd:nonexistent-cmd-12345
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_requirements(base_path=tmp_path)
        
        # Should have 2 errors: missing file and missing command
        assert len(errors) == 2
        error_messages = [e[1] for e in errors]
        assert any("missing.md" in msg for msg in error_messages)
        assert any("nonexistent-cmd-12345" in msg for msg in error_messages)



class TestOnFailureDirectiveParsing:
    """Tests for ON-FAILURE/ON-SUCCESS block parsing."""

    def test_parse_on_failure_block(self):
        """Test parsing a basic ON-FAILURE block."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-FAILURE
  PROMPT Fix the failing tests.
END
PROMPT Continue.
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 2
        assert conv.steps[0].type == "run"
        assert conv.steps[0].content == "pytest"
        assert len(conv.steps[0].on_failure) == 1
        assert conv.steps[0].on_failure[0].type == "prompt"
        assert conv.steps[0].on_failure[0].content == "Fix the failing tests."
        assert conv.steps[1].type == "prompt"

    def test_parse_on_success_block(self):
        """Test parsing a basic ON-SUCCESS block."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-SUCCESS
  PROMPT All tests passed!
END
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 1
        assert conv.steps[0].type == "run"
        assert len(conv.steps[0].on_success) == 1
        assert conv.steps[0].on_success[0].type == "prompt"

    def test_parse_both_blocks(self):
        """Test parsing both ON-FAILURE and ON-SUCCESS blocks."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-FAILURE
  PROMPT Fix the tests.
END
ON-SUCCESS
  PROMPT Deploy now.
END
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps[0].on_failure) == 1
        assert len(conv.steps[0].on_success) == 1

    def test_parse_multiple_steps_in_block(self):
        """Test parsing a block with multiple steps.
        
        Note: Block content should NOT be indented, as indented lines
        are treated as multiline continuation of the previous directive.
        """
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-FAILURE
PROMPT Analyze failures.
RUN git diff
PROMPT Fix based on diff.
END
"""
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps[0].on_failure) == 3
        assert conv.steps[0].on_failure[0].type == "prompt"
        assert conv.steps[0].on_failure[1].type == "run"
        assert conv.steps[0].on_failure[2].type == "prompt"

    def test_parse_on_failure_without_run_raises_error(self):
        """Test that ON-FAILURE without preceding RUN raises ValueError."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Something
ON-FAILURE
  PROMPT Fix it
END
"""
        with pytest.raises(ValueError) as excinfo:
            ConversationFile.parse(content)
        assert "ON-FAILURE without preceding RUN" in str(excinfo.value)

    def test_parse_unclosed_block_raises_error(self):
        """Test that unclosed ON-FAILURE block raises ValueError."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-FAILURE
  PROMPT Fix it
"""
        with pytest.raises(ValueError) as excinfo:
            ConversationFile.parse(content)
        assert "Unclosed ON-FAILURE block" in str(excinfo.value)

    def test_parse_nested_blocks_raises_error(self):
        """Test that nested ON-FAILURE blocks raise ValueError."""
        content = """MODEL gpt-4
ADAPTER mock
RUN pytest
ON-FAILURE
  ON-SUCCESS
    PROMPT Oops
  END
END
"""
        with pytest.raises(ValueError) as excinfo:
            ConversationFile.parse(content)
        assert "Nested" in str(excinfo.value)

    def test_elide_chain_with_on_failure_invalid(self):
        """Test that ELIDE chain with ON-FAILURE blocks is invalid."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze
ELIDE
RUN pytest
ON-FAILURE
  PROMPT Fix
END
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) > 0
        assert "ON-FAILURE" in errors[0]
        assert "ELIDE" in errors[0]

    def test_elide_chain_with_on_success_invalid(self):
        """Test that ELIDE chain with ON-SUCCESS blocks is invalid."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze
ELIDE
RUN pytest
ON-SUCCESS
  PROMPT Deploy
END
"""
        conv = ConversationFile.parse(content)
        errors = conv.validate_elide_chains()
        
        assert len(errors) > 0
        assert "ON-SUCCESS" in errors[0]
        assert "ELIDE" in errors[0]
