"""Tests for custom directive parser integration (DIR-001).

These tests verify that custom directives from plugins are recognized
by the parser and correctly processed through the pipeline.
"""

import pytest

from sdqctl.core.conversation.parser import parse_line
from sdqctl.core.conversation.applicator import apply_directive
from sdqctl.core.conversation.file import ConversationFile
from sdqctl.core.conversation.types import (
    Directive,
    DirectiveType,
    ConversationStep,
    register_custom_directive,
    clear_custom_directives,
    is_custom_directive,
)


@pytest.fixture(autouse=True)
def cleanup_custom_directives():
    """Clean up custom directive registry after each test."""
    yield
    clear_custom_directives()


class TestParserCustomDirectives:
    """Test parser recognition of custom directives."""

    def test_builtin_directive_still_works(self):
        """Built-in directives should continue to work."""
        result = parse_line("MODEL gpt-4", 1)
        assert result is not None
        assert result.type == DirectiveType.MODEL
        assert result.value == "gpt-4"

    def test_unregistered_custom_directive_returns_none(self):
        """Unregistered custom directives should be ignored."""
        result = parse_line("HYGIENE queue-stats", 1)
        assert result is None

    def test_registered_custom_directive_is_parsed(self):
        """Registered custom directives should be parsed."""
        register_custom_directive("HYGIENE", {"description": "Run hygiene checks"})
        
        result = parse_line("HYGIENE queue-stats", 1)
        
        assert result is not None
        assert result.type == "HYGIENE"  # String, not enum
        assert result.value == "queue-stats"
        assert result.line_number == 1
        assert result.is_custom is True

    def test_custom_directive_with_no_value(self):
        """Custom directives without values should work."""
        register_custom_directive("TRACE")
        
        result = parse_line("TRACE", 1)
        
        assert result is not None
        assert result.type == "TRACE"
        assert result.value == ""

    def test_custom_directive_case_normalization(self):
        """Directive names should be case-insensitive for registration."""
        register_custom_directive("hygiene")  # lowercase registration
        
        result = parse_line("HYGIENE check", 1)
        
        assert result is not None
        assert result.type == "HYGIENE"

    def test_builtin_and_custom_coexist(self):
        """Built-in and custom directives should coexist."""
        register_custom_directive("CUSTOM")
        
        builtin = parse_line("PROMPT Hello", 1)
        custom = parse_line("CUSTOM value", 2)
        
        assert builtin is not None
        assert builtin.type == DirectiveType.PROMPT
        assert custom is not None
        assert custom.type == "CUSTOM"


class TestApplicatorCustomDirectives:
    """Test applicator handling of custom directives."""

    def test_custom_directive_creates_step(self):
        """Custom directives should create custom_directive steps."""
        register_custom_directive("HYGIENE")
        
        directive = Directive(
            type="HYGIENE",
            value="queue-stats",
            line_number=10,
            raw_line="HYGIENE queue-stats",
        )
        
        # Create a mock ConversationFile
        conv = ConversationFile()
        apply_directive(conv, directive)
        
        assert len(conv.steps) == 1
        step = conv.steps[0]
        assert step.type == "custom_directive"
        assert step.directive_name == "HYGIENE"
        assert step.content == "queue-stats"
        assert step.line_number == 10

    def test_builtin_directive_no_step(self):
        """Built-in config directives shouldn't create steps."""
        directive = Directive(
            type=DirectiveType.MODEL,
            value="gpt-4",
            line_number=1,
            raw_line="MODEL gpt-4",
        )
        
        conv = ConversationFile()
        apply_directive(conv, directive)
        
        assert len(conv.steps) == 0
        assert conv.model == "gpt-4"


class TestConversationFileParsing:
    """Test full ConversationFile parsing with custom directives."""

    def test_parse_file_with_custom_directive(self):
        """ConversationFile.parse should recognize custom directives."""
        register_custom_directive("HYGIENE", {"handler": "hygiene.sh"})
        
        content = """\
MODEL gpt-4
HYGIENE queue-stats
PROMPT Check the results
"""
        
        conv = ConversationFile.parse(content)
        
        assert conv.model == "gpt-4"
        assert len(conv.steps) == 2
        
        # First step is custom directive
        assert conv.steps[0].type == "custom_directive"
        assert conv.steps[0].directive_name == "HYGIENE"
        assert conv.steps[0].content == "queue-stats"
        
        # Second step is prompt
        assert conv.steps[1].type == "prompt"
        assert conv.steps[1].content == "Check the results"

    def test_parse_multiple_custom_directives(self):
        """Multiple custom directives should all be processed."""
        register_custom_directive("HYGIENE")
        register_custom_directive("TRACE")
        
        content = """\
HYGIENE check-1
TRACE enable
HYGIENE check-2
"""
        
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 3
        assert conv.steps[0].directive_name == "HYGIENE"
        assert conv.steps[0].content == "check-1"
        assert conv.steps[1].directive_name == "TRACE"
        assert conv.steps[2].directive_name == "HYGIENE"
        assert conv.steps[2].content == "check-2"

    def test_mixed_builtin_and_custom_order(self):
        """Order should be preserved with mixed directive types."""
        register_custom_directive("CUSTOM")
        
        content = """\
PROMPT First
CUSTOM middle
PROMPT Second
"""
        
        conv = ConversationFile.parse(content)
        
        assert len(conv.steps) == 3
        assert conv.steps[0].type == "prompt"
        assert conv.steps[0].content == "First"
        assert conv.steps[1].type == "custom_directive"
        assert conv.steps[1].directive_name == "CUSTOM"
        assert conv.steps[2].type == "prompt"
        assert conv.steps[2].content == "Second"


class TestConversationStepAttributes:
    """Test new ConversationStep attributes for custom directives."""

    def test_directive_name_attribute(self):
        """ConversationStep should have directive_name for custom directives."""
        step = ConversationStep(
            type="custom_directive",
            content="value",
            directive_name="HYGIENE",
            line_number=5,
        )
        
        assert step.directive_name == "HYGIENE"
        assert step.line_number == 5

    def test_regular_step_empty_directive_name(self):
        """Regular steps should have empty directive_name."""
        step = ConversationStep(type="prompt", content="Hello")
        
        assert step.directive_name == ""
        assert step.line_number == 0
