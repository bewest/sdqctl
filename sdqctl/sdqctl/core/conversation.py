"""
ConversationFile parser - Dockerfile-like format for AI workflows.

Example:
    MODEL claude-sonnet-4.5
    ADAPTER copilot
    MODE audit
    MAX-CYCLES 3
    
    CONTEXT @lib/auth/*.js
    
    PROMPT Analyze authentication for vulnerabilities.
    PROMPT Generate security report.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DirectiveType(Enum):
    """Types of directives in a ConversationFile."""

    # Metadata
    MODEL = "MODEL"
    ADAPTER = "ADAPTER"
    MODE = "MODE"
    MAX_CYCLES = "MAX-CYCLES"
    CWD = "CWD"

    # Context
    CONTEXT = "CONTEXT"
    CONTEXT_LIMIT = "CONTEXT-LIMIT"
    ON_CONTEXT_LIMIT = "ON-CONTEXT-LIMIT"

    # Prompts
    PROMPT = "PROMPT"
    ON_CONTEXT_LIMIT_PROMPT = "ON-CONTEXT-LIMIT-PROMPT"

    # Compaction
    COMPACT_PRESERVE = "COMPACT-PRESERVE"
    COMPACT_SUMMARY = "COMPACT-SUMMARY"

    # Checkpointing
    CHECKPOINT_AFTER = "CHECKPOINT-AFTER"
    CHECKPOINT_NAME = "CHECKPOINT-NAME"

    # Output
    OUTPUT_FORMAT = "OUTPUT-FORMAT"
    OUTPUT_FILE = "OUTPUT-FILE"

    # Flow control
    PAUSE = "PAUSE"


@dataclass
class Directive:
    """A single directive from a ConversationFile."""

    type: DirectiveType
    value: str
    line_number: int
    raw_line: str


@dataclass
class ConversationFile:
    """Parsed representation of a .conv file."""

    # Metadata
    model: str = "gpt-4"
    adapter: str = "copilot"
    mode: str = "full"
    max_cycles: int = 1
    cwd: Optional[str] = None

    # Context
    context_files: list[str] = field(default_factory=list)
    context_limit: float = 0.8  # 80% of context window
    on_context_limit: str = "compact"  # compact, stop, continue

    # Prompts
    prompts: list[str] = field(default_factory=list)
    on_context_limit_prompt: Optional[str] = None

    # Compaction
    compact_preserve: list[str] = field(default_factory=list)
    compact_summary: Optional[str] = None

    # Checkpointing
    checkpoint_after: Optional[str] = None  # each-cycle, each-prompt, never
    checkpoint_name: Optional[str] = None

    # Output
    output_format: str = "markdown"
    output_file: Optional[str] = None

    # Flow control
    pause_points: list[tuple[int, str]] = field(default_factory=list)  # (after_prompt_index, message)

    # Source
    source_path: Optional[Path] = None
    directives: list[Directive] = field(default_factory=list)

    @classmethod
    def parse(cls, content: str, source_path: Optional[Path] = None) -> "ConversationFile":
        """Parse a ConversationFile from string content."""
        conv = cls(source_path=source_path)
        directives = []

        # Track multiline prompts
        current_multiline: Optional[tuple[DirectiveType, list[str], int]] = None

        for line_num, line in enumerate(content.split("\n"), 1):
            # Handle multiline continuation
            if current_multiline is not None:
                if line.startswith("  ") or line.startswith("\t"):
                    # Continuation of multiline
                    current_multiline[1].append(line.strip())
                    continue
                else:
                    # End of multiline - process it
                    dtype, lines, start_line = current_multiline
                    value = "\n".join(lines)
                    directive = Directive(
                        type=dtype, value=value, line_number=start_line, raw_line="<multiline>"
                    )
                    directives.append(directive)
                    _apply_directive(conv, directive)
                    current_multiline = None

            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Parse directive
            directive = _parse_line(stripped, line_num)
            if directive:
                # Check if this starts a multiline
                if directive.type in (
                    DirectiveType.PROMPT,
                    DirectiveType.ON_CONTEXT_LIMIT_PROMPT,
                    DirectiveType.COMPACT_SUMMARY,
                ):
                    current_multiline = (directive.type, [directive.value], line_num)
                else:
                    directives.append(directive)
                    _apply_directive(conv, directive)

        # Handle trailing multiline
        if current_multiline is not None:
            dtype, lines, start_line = current_multiline
            value = "\n".join(lines)
            directive = Directive(
                type=dtype, value=value, line_number=start_line, raw_line="<multiline>"
            )
            directives.append(directive)
            _apply_directive(conv, directive)

        conv.directives = directives
        return conv

    @classmethod
    def from_file(cls, path: Path | str) -> "ConversationFile":
        """Load and parse a ConversationFile from disk."""
        path = Path(path)
        content = path.read_text()
        return cls.parse(content, source_path=path)

    def to_string(self) -> str:
        """Serialize back to ConversationFile format."""
        lines = []

        # Metadata
        lines.append(f"MODEL {self.model}")
        lines.append(f"ADAPTER {self.adapter}")
        lines.append(f"MODE {self.mode}")
        if self.max_cycles != 1:
            lines.append(f"MAX-CYCLES {self.max_cycles}")
        if self.cwd:
            lines.append(f"CWD {self.cwd}")

        lines.append("")

        # Context
        if self.context_limit != 0.8:
            lines.append(f"CONTEXT-LIMIT {int(self.context_limit * 100)}%")
        if self.on_context_limit != "compact":
            lines.append(f"ON-CONTEXT-LIMIT {self.on_context_limit}")

        for ctx in self.context_files:
            lines.append(f"CONTEXT {ctx}")

        if self.context_files:
            lines.append("")

        # Compaction
        if self.compact_preserve:
            lines.append(f"COMPACT-PRESERVE {', '.join(self.compact_preserve)}")
        if self.compact_summary:
            lines.append(f"COMPACT-SUMMARY {self.compact_summary}")

        # Checkpointing
        if self.checkpoint_after:
            lines.append(f"CHECKPOINT-AFTER {self.checkpoint_after}")
        if self.checkpoint_name:
            lines.append(f"CHECKPOINT-NAME {self.checkpoint_name}")

        if self.compact_preserve or self.checkpoint_after:
            lines.append("")

        # Prompts
        for prompt in self.prompts:
            if "\n" in prompt:
                lines.append(f"PROMPT {prompt.split(chr(10))[0]}")
                for sub_line in prompt.split("\n")[1:]:
                    lines.append(f"  {sub_line}")
            else:
                lines.append(f"PROMPT {prompt}")

        if self.on_context_limit_prompt:
            lines.append(f"ON-CONTEXT-LIMIT-PROMPT {self.on_context_limit_prompt}")

        lines.append("")

        # Output
        if self.output_format != "markdown":
            lines.append(f"OUTPUT-FORMAT {self.output_format}")
        if self.output_file:
            lines.append(f"OUTPUT-FILE {self.output_file}")

        return "\n".join(lines)


def _parse_line(line: str, line_num: int) -> Optional[Directive]:
    """Parse a single line into a Directive."""
    # Match DIRECTIVE value pattern
    match = re.match(r"^([A-Z][A-Z0-9-]*)\s+(.+)$", line)
    if not match:
        return None

    directive_name = match.group(1)
    value = match.group(2).strip()

    # Try to match to DirectiveType
    try:
        dtype = DirectiveType(directive_name)
        return Directive(type=dtype, value=value, line_number=line_num, raw_line=line)
    except ValueError:
        # Unknown directive - ignore for forward compatibility
        return None


def _apply_directive(conv: ConversationFile, directive: Directive) -> None:
    """Apply a parsed directive to the ConversationFile."""
    match directive.type:
        case DirectiveType.MODEL:
            conv.model = directive.value
        case DirectiveType.ADAPTER:
            conv.adapter = directive.value
        case DirectiveType.MODE:
            conv.mode = directive.value
        case DirectiveType.MAX_CYCLES:
            conv.max_cycles = int(directive.value)
        case DirectiveType.CWD:
            conv.cwd = directive.value
        case DirectiveType.CONTEXT:
            conv.context_files.append(directive.value)
        case DirectiveType.CONTEXT_LIMIT:
            # Parse "80%" -> 0.8
            value = directive.value.rstrip("%")
            conv.context_limit = float(value) / 100
        case DirectiveType.ON_CONTEXT_LIMIT:
            conv.on_context_limit = directive.value
        case DirectiveType.PROMPT:
            conv.prompts.append(directive.value)
        case DirectiveType.ON_CONTEXT_LIMIT_PROMPT:
            conv.on_context_limit_prompt = directive.value
        case DirectiveType.COMPACT_PRESERVE:
            # Parse "findings, recommendations" -> ["findings", "recommendations"]
            conv.compact_preserve = [x.strip() for x in directive.value.split(",")]
        case DirectiveType.COMPACT_SUMMARY:
            conv.compact_summary = directive.value
        case DirectiveType.CHECKPOINT_AFTER:
            conv.checkpoint_after = directive.value
        case DirectiveType.CHECKPOINT_NAME:
            conv.checkpoint_name = directive.value
        case DirectiveType.OUTPUT_FORMAT:
            conv.output_format = directive.value
        case DirectiveType.OUTPUT_FILE:
            conv.output_file = directive.value
        case DirectiveType.PAUSE:
            # PAUSE after the last prompt added so far
            pause_index = len(conv.prompts) - 1 if conv.prompts else 0
            conv.pause_points.append((pause_index, directive.value))
