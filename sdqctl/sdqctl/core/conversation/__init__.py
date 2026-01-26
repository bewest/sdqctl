"""
ConversationFile parser - Dockerfile-like format for AI workflows.

This package provides the ConversationFile parser and related utilities.
All public APIs are re-exported here for backward compatibility.
"""

# Types and dataclasses
from .applicator import (
    _apply_directive,
    _apply_directive_to_block,
    apply_directive,
    apply_directive_to_block,
)

# Main ConversationFile class
from .file import ConversationFile

# Parser and applicator (mostly internal, but exported for compatibility)
from .parser import _parse_line, parse_line

# Template utilities
from .templates import (
    get_standard_variables,
    substitute_template_variables,
)
from .types import (
    SECRET_KEY_PATTERNS,
    ConversationStep,
    Directive,
    DirectiveType,
    FileRestrictions,
    _mask_env_value,
)

# Content utilities
from .utilities import (
    apply_iteration_context,
    build_output_with_injection,
    build_prompt_with_injection,
    parse_timeout_duration,
    resolve_content_reference,
)

__all__ = [
    # Primary exports
    "ConversationFile",
    "ConversationStep",
    "Directive",
    "DirectiveType",
    "FileRestrictions",
    # Template functions
    "substitute_template_variables",
    "get_standard_variables",
    # Content utilities
    "apply_iteration_context",
    "build_prompt_with_injection",
    "build_output_with_injection",
    "resolve_content_reference",
    "parse_timeout_duration",
    # Parser internals (for backward compatibility)
    "parse_line",
    "_parse_line",
    "apply_directive",
    "apply_directive_to_block",
    "_apply_directive",
    "_apply_directive_to_block",
    # Constants
    "SECRET_KEY_PATTERNS",
    "_mask_env_value",
]
