"""Line-level parsing for ConversationFile directives."""

import re
from typing import Optional

from .types import Directive, DirectiveType, is_custom_directive


def parse_line(line: str, line_num: int) -> Optional[Directive]:
    """Parse a single line into a Directive.

    Args:
        line: The line text to parse
        line_num: The line number for error reporting

    Returns:
        A Directive if the line matches a known directive, None otherwise
    """
    # Match DIRECTIVE value pattern (value is optional for some directives)
    match = re.match(r"^([A-Z][A-Z0-9-]*)\s*(.*)$", line)
    if not match:
        return None

    directive_name = match.group(1)
    value = match.group(2).strip() if match.group(2) else ""

    # Try to match to DirectiveType enum (built-in directives)
    try:
        dtype = DirectiveType(directive_name)
        return Directive(type=dtype, value=value, line_number=line_num, raw_line=line)
    except ValueError:
        # Check if it's a registered custom directive (from plugins)
        if is_custom_directive(directive_name):
            return Directive(
                type=directive_name,  # String type for custom directives
                value=value,
                line_number=line_num,
                raw_line=line
            )
        # Unknown directive - ignore for forward compatibility
        return None


# Alias for backward compatibility
_parse_line = parse_line
