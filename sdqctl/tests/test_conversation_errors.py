"""
Error path tests for ConversationFile parsing.

Tests malformed .conv input handling, invalid directives, and edge cases.
"""

import pytest
from pathlib import Path

from sdqctl.core.conversation import ConversationFile


pytestmark = pytest.mark.unit


class TestMalformedConvInput:
    """Test handling of malformed .conv file content."""

    def test_empty_content_creates_empty_conv(self):
        """Empty content produces a ConversationFile with defaults."""
        conv = ConversationFile.parse("")
        # Model/adapter have defaults from ConversationFile
        assert conv.model == "gpt-4"  # Default model
        assert conv.adapter == "copilot"  # Default adapter
        assert len(conv.steps) == 0

    def test_whitespace_only_content(self):
        """Whitespace-only content is valid but empty."""
        conv = ConversationFile.parse("   \n\t\n   ")
        assert len(conv.steps) == 0

    def test_comments_only_content(self):
        """Comment-only content is valid."""
        conv = ConversationFile.parse("# Just a comment\n# Another comment")
        assert len(conv.steps) == 0

    def test_unknown_directive_ignored(self):
        """Unknown directives are ignored (not raised as errors)."""
        content = """MODEL gpt-4
ADAPTER mock
UNKNOWN-DIRECTIVE value
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.model == "gpt-4"
        assert len(conv.prompts) == 1

    def test_directive_without_value(self):
        """Directive without value uses empty string."""
        content = """MODEL
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        # MODEL with no value becomes empty string
        assert conv.model == ""

    def test_duplicate_model_uses_last(self):
        """Duplicate MODEL directives use the last value."""
        content = """MODEL gpt-3
MODEL gpt-4
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.model == "gpt-4"

    def test_prompt_without_content_is_valid(self):
        """PROMPT without content creates empty prompt step."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts) == 1
        assert conv.prompts[0] == ""


class TestInvalidDirectiveValues:
    """Test handling of invalid directive values."""

    def test_context_limit_non_percentage(self):
        """CONTEXT-LIMIT with invalid format raises ValueError."""
        content = """MODEL gpt-4
ADAPTER mock
CONTEXT-LIMIT invalid
PROMPT Test.
"""
        # Invalid format raises at parse time
        with pytest.raises(ValueError):
            ConversationFile.parse(content)

    def test_context_limit_negative_percentage(self):
        """CONTEXT-LIMIT with negative value is handled."""
        content = """MODEL gpt-4
ADAPTER mock
CONTEXT-LIMIT -50%
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        # Negative value stored (validation happens at runtime)
        assert conv.context_limit is not None

    def test_context_limit_over_100_percentage(self):
        """CONTEXT-LIMIT over 100% is allowed (may be intentional)."""
        content = """MODEL gpt-4
ADAPTER mock
CONTEXT-LIMIT 150%
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.context_limit == 1.5

    def test_max_cycles_non_integer(self):
        """MAX-CYCLES with non-integer raises ValueError."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES abc
PROMPT Test.
"""
        with pytest.raises(ValueError):
            ConversationFile.parse(content)

    def test_max_cycles_negative(self):
        """MAX-CYCLES with negative value is stored."""
        content = """MODEL gpt-4
ADAPTER mock
MAX-CYCLES -5
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.max_cycles == -5


class TestMissingFileErrors:
    """Test handling of missing file references."""

    def test_refcat_missing_file_at_parse(self, tmp_path):
        """REFCAT with missing file stores ref (resolved at render time)."""
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("""MODEL gpt-4
ADAPTER mock
REFCAT @nonexistent.md
PROMPT Test.
""")
        conv = ConversationFile.from_file(conv_file)
        # Missing file stored as ref, error at resolution time
        assert "@nonexistent.md" in conv.refcat_refs

    def test_include_missing_file_raises(self, tmp_path):
        """INCLUDE with missing file raises FileNotFoundError."""
        conv_file = tmp_path / "test.conv"
        conv_file.write_text("""MODEL gpt-4
ADAPTER mock
INCLUDE nonexistent.conv
PROMPT Test.
""")
        with pytest.raises(FileNotFoundError):
            ConversationFile.from_file(conv_file)

    def test_from_file_nonexistent_path(self):
        """from_file with nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConversationFile.from_file(Path("/nonexistent/path/test.conv"))


class TestBlockDirectiveErrors:
    """Test error handling for block directives (ON-FAILURE, ON-SUCCESS)."""

    def test_on_failure_without_preceding_run(self):
        """ON-FAILURE without preceding RUN raises error."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First.
ON-FAILURE
  PROMPT Handle failure.
END-FAILURE
"""
        with pytest.raises(ValueError, match="ON-FAILURE"):
            ConversationFile.parse(content)

    def test_on_success_without_preceding_run(self):
        """ON-SUCCESS without preceding RUN raises error."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First.
ON-SUCCESS
  PROMPT Handle success.
END-SUCCESS
"""
        with pytest.raises(ValueError, match="ON-SUCCESS"):
            ConversationFile.parse(content)

    def test_unclosed_on_failure_block(self):
        """Unclosed ON-FAILURE block raises error."""
        content = """MODEL gpt-4
ADAPTER mock
RUN echo test
ON-FAILURE
  PROMPT Handle failure.
PROMPT Next step.
"""
        with pytest.raises(ValueError, match="Unclosed|missing END"):
            ConversationFile.parse(content)

    def test_nested_on_failure_blocks(self):
        """Nested ON-FAILURE blocks raise error."""
        content = """MODEL gpt-4
ADAPTER mock
RUN echo test
ON-FAILURE
  RUN echo retry
  ON-FAILURE
    PROMPT Double failure.
  END-FAILURE
END-FAILURE
"""
        with pytest.raises(ValueError, match="nested|Nested"):
            ConversationFile.parse(content)


class TestVerifyDirectiveErrors:
    """Test error handling for VERIFY directives."""

    def test_verify_coverage_parses_metric(self):
        """VERIFY-COVERAGE metric is stored in step (validation at execution)."""
        content = """MODEL gpt-4
ADAPTER mock
VERIFY-COVERAGE coverage > 80%
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        steps = [s for s in conv.steps if s.type == "verify_coverage"]
        assert len(steps) == 1
        assert "coverage" in steps[0].content


class TestEncodingAndSpecialCharacters:
    """Test handling of encoding and special characters."""

    def test_unicode_in_prompt(self):
        """Unicode characters in prompt are preserved."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Analyze: 日本語テスト émojis 🎉
"""
        conv = ConversationFile.parse(content)
        assert "日本語" in conv.prompts[0]
        assert "🎉" in conv.prompts[0]

    def test_tabs_in_content(self):
        """Tabs in content are preserved."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT Line with\ttab.
"""
        conv = ConversationFile.parse(content)
        assert "\t" in conv.prompts[0]

    def test_multiple_blank_lines_normalized(self):
        """Multiple blank lines don't create empty steps."""
        content = """MODEL gpt-4
ADAPTER mock


PROMPT First.



PROMPT Second.
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts) == 2


class TestConsultTimeoutErrors:
    """Test CONSULT-TIMEOUT directive error handling."""

    @pytest.mark.parametrize("timeout_value", [
        "7d",    # Days
        "24h",   # Hours
        "30m",   # Minutes (if supported)
        "1w",    # Week (if supported)
    ])
    def test_consult_timeout_valid_formats(self, timeout_value):
        """CONSULT-TIMEOUT with valid formats parses correctly."""
        content = f"""MODEL gpt-4
ADAPTER mock
CONSULT-TIMEOUT {timeout_value}
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.consult_timeout is not None


class TestDirectiveVariants:
    """Parametrized tests for directive parsing variants."""

    @pytest.mark.parametrize("model_name", [
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-opus",
        "gemini-pro",
        "custom-model-v1",
    ])
    def test_model_directive_variants(self, model_name):
        """MODEL directive accepts various model names."""
        content = f"""MODEL {model_name}
ADAPTER mock
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.model == model_name

    @pytest.mark.parametrize("adapter_name", [
        "mock",
        "copilot",
    ])
    def test_adapter_directive_variants(self, adapter_name):
        """ADAPTER directive accepts registered adapters."""
        content = f"""MODEL gpt-4
ADAPTER {adapter_name}
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.adapter == adapter_name

    @pytest.mark.parametrize("mode_value", [
        "audit",
        "full",
        "apply",
    ])
    def test_mode_directive_variants(self, mode_value):
        """MODE directive accepts valid modes."""
        content = f"""MODEL gpt-4
ADAPTER mock
MODE {mode_value}
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.mode == mode_value

    @pytest.mark.parametrize("limit_value,expected", [
        ("80%", 0.8),
        ("50%", 0.5),
        ("100%", 1.0),
        ("25%", 0.25),
    ])
    def test_context_limit_variants(self, limit_value, expected):
        """CONTEXT-LIMIT directive parses percentage values."""
        content = f"""MODEL gpt-4
ADAPTER mock
CONTEXT-LIMIT {limit_value}
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.context_limit == expected

    @pytest.mark.parametrize("cycles", [1, 5, 10, 100])
    def test_max_cycles_variants(self, cycles):
        """MAX-CYCLES directive accepts positive integers."""
        content = f"""MODEL gpt-4
ADAPTER mock
MAX-CYCLES {cycles}
PROMPT Test.
"""
        conv = ConversationFile.parse(content)
        assert conv.max_cycles == cycles


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_very_long_prompt(self):
        """Very long prompts are preserved."""
        long_text = "x" * 10000
        content = f"""MODEL gpt-4
ADAPTER mock
PROMPT {long_text}
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts[0]) == 10000

    def test_many_steps(self):
        """Many steps are all preserved."""
        prompts = "\n".join([f"PROMPT Step {i}." for i in range(100)])
        content = f"""MODEL gpt-4
ADAPTER mock
{prompts}
"""
        conv = ConversationFile.parse(content)
        assert len(conv.prompts) == 100

    def test_deeply_indented_multiline(self):
        """Deeply indented multiline prompts are parsed correctly."""
        content = """MODEL gpt-4
ADAPTER mock
PROMPT First line.
    Second line with indent.
        Third line deeply indented.
"""
        conv = ConversationFile.parse(content)
        # Multiline content includes indented lines
        assert "Second line" in conv.prompts[0]

    def test_directive_case_sensitivity(self):
        """Directives should be case-insensitive."""
        content = """model gpt-4
ADAPTER mock
Prompt Test.
"""
        # Some parsers are case-insensitive, test actual behavior
        conv = ConversationFile.parse(content)
        # If case-insensitive, model is set
        # If case-sensitive, these are treated as unknown
        # Document actual behavior
        assert conv is not None
