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
    CONTEXT_OPTIONAL = "CONTEXT-OPTIONAL"  # Optional context (warn if missing, don't fail)
    CONTEXT_EXCLUDE = "CONTEXT-EXCLUDE"  # Patterns to exclude from validation
    CONTEXT_LIMIT = "CONTEXT-LIMIT"
    ON_CONTEXT_LIMIT = "ON-CONTEXT-LIMIT"
    
    # Validation mode
    VALIDATION_MODE = "VALIDATION-MODE"  # strict, lenient, exploratory

    # File control (allow/deny patterns)
    ALLOW_FILES = "ALLOW-FILES"
    DENY_FILES = "DENY-FILES"
    ALLOW_DIR = "ALLOW-DIR"
    DENY_DIR = "DENY-DIR"

    # Prompt injection (prepend/append to prompts)
    PROLOGUE = "PROLOGUE"
    EPILOGUE = "EPILOGUE"

    # Prompts
    PROMPT = "PROMPT"
    ON_CONTEXT_LIMIT_PROMPT = "ON-CONTEXT-LIMIT-PROMPT"

    # Compaction & conversation control
    COMPACT = "COMPACT"
    COMPACT_PRESERVE = "COMPACT-PRESERVE"
    COMPACT_SUMMARY = "COMPACT-SUMMARY"
    NEW_CONVERSATION = "NEW-CONVERSATION"

    # Checkpointing
    CHECKPOINT = "CHECKPOINT"
    CHECKPOINT_AFTER = "CHECKPOINT-AFTER"
    CHECKPOINT_NAME = "CHECKPOINT-NAME"

    # Output injection (prepend/append to output)
    HEADER = "HEADER"
    FOOTER = "FOOTER"

    # Output
    OUTPUT = "OUTPUT"
    OUTPUT_FORMAT = "OUTPUT-FORMAT"
    OUTPUT_FILE = "OUTPUT-FILE"
    OUTPUT_DIR = "OUTPUT-DIR"

    # Command execution
    RUN = "RUN"
    RUN_ON_ERROR = "RUN-ON-ERROR"
    RUN_OUTPUT = "RUN-OUTPUT"
    RUN_OUTPUT_LIMIT = "RUN-OUTPUT-LIMIT"  # Max chars to capture (e.g., 10K, 50K, none)
    RUN_ENV = "RUN-ENV"  # Environment variables for RUN commands (KEY=value)
    RUN_CWD = "RUN-CWD"  # Working directory for RUN commands
    ALLOW_SHELL = "ALLOW-SHELL"  # Enable shell=True for RUN (security opt-in)
    RUN_TIMEOUT = "RUN-TIMEOUT"  # Timeout in seconds for RUN commands
    RUN_ASYNC = "RUN-ASYNC"  # Run command in background, don't wait
    RUN_WAIT = "RUN-WAIT"  # Wait/sleep (e.g., 5s, 1m)

    # Flow control
    PAUSE = "PAUSE"

    # Debug directives
    DEBUG = "DEBUG"  # Comma-separated debug categories (session,tool,intent,event)
    DEBUG_INTENTS = "DEBUG-INTENTS"  # true/false - enable intent tracking output
    EVENT_LOG = "EVENT-LOG"  # Path for event log (supports {{DATETIME}} template)


@dataclass
class Directive:
    """A single directive from a ConversationFile."""

    type: DirectiveType
    value: str
    line_number: int
    raw_line: str


@dataclass
class FileRestrictions:
    """File access restrictions for workflows."""
    
    allow_patterns: list[str] = field(default_factory=list)  # Glob patterns to include
    deny_patterns: list[str] = field(default_factory=list)   # Glob patterns to exclude
    allow_dirs: list[str] = field(default_factory=list)      # Directories to allow
    deny_dirs: list[str] = field(default_factory=list)       # Directories to deny
    
    def merge_with_cli(self, cli_allow: list[str], cli_deny: list[str]) -> "FileRestrictions":
        """Merge with CLI overrides (CLI takes precedence)."""
        return FileRestrictions(
            allow_patterns=list(cli_allow) if cli_allow else self.allow_patterns.copy(),
            deny_patterns=list(cli_deny) + self.deny_patterns,  # CLI deny adds to file deny
            allow_dirs=self.allow_dirs.copy(),
            deny_dirs=self.deny_dirs.copy(),
        )
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed by the restrictions.
        
        Logic:
        - If deny patterns match, deny (deny wins)
        - If allow patterns are specified and none match, deny
        - Otherwise allow
        """
        import fnmatch
        from pathlib import Path
        
        path_obj = Path(path)
        
        # Check deny patterns first (deny wins)
        for pattern in self.deny_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(str(path_obj), pattern):
                return False
        
        # Check deny dirs
        for deny_dir in self.deny_dirs:
            deny_path = Path(deny_dir)
            try:
                path_obj.relative_to(deny_path)
                return False  # Path is under denied directory
            except ValueError:
                pass  # Not under this directory
        
        # If allow patterns specified, path must match at least one
        if self.allow_patterns:
            for pattern in self.allow_patterns:
                if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(str(path_obj), pattern):
                    return True
            return False  # No allow pattern matched
        
        # If allow dirs specified, path must be under at least one
        if self.allow_dirs:
            for allow_dir in self.allow_dirs:
                allow_path = Path(allow_dir)
                try:
                    path_obj.relative_to(allow_path)
                    return True  # Path is under allowed directory
                except ValueError:
                    pass
            return False  # Not under any allowed directory
        
        # No restrictions, allow by default
        return True


@dataclass
class ConversationStep:
    """A step in the conversation flow (PROMPT, COMPACT, NEW-CONVERSATION, etc.)."""
    
    type: str  # "prompt", "compact", "new_conversation", "checkpoint"
    content: str = ""  # Prompt text or checkpoint name
    preserve: list[str] = field(default_factory=list)  # For compact
    

def _get_default_model() -> str:
    """Get default model from config (lazy import to avoid circular deps)."""
    try:
        from .config import get_default_model
        return get_default_model()
    except ImportError:
        return "gpt-4"


def _get_default_adapter() -> str:
    """Get default adapter from config (lazy import to avoid circular deps)."""
    try:
        from .config import get_default_adapter
        return get_default_adapter()
    except ImportError:
        return "copilot"


def _get_default_context_limit() -> float:
    """Get default context limit from config (lazy import to avoid circular deps)."""
    try:
        from .config import get_context_limit
        return get_context_limit()
    except ImportError:
        return 0.8


@dataclass
class ConversationFile:
    """Parsed representation of a .conv file."""

    # Metadata - defaults loaded from .sdqctl.yaml config if available
    model: str = field(default_factory=_get_default_model)
    adapter: str = field(default_factory=_get_default_adapter)
    mode: str = "full"
    max_cycles: int = 1
    cwd: Optional[str] = None

    # Context - context_limit default loaded from config
    context_files: list[str] = field(default_factory=list)
    context_files_optional: list[str] = field(default_factory=list)  # Optional context patterns
    context_exclude: list[str] = field(default_factory=list)  # Patterns to exclude from validation
    context_limit: float = field(default_factory=_get_default_context_limit)
    on_context_limit: str = "compact"  # compact, stop, continue
    
    # Validation mode (strict, lenient, exploratory)
    validation_mode: str = "strict"  # strict=fail on missing, lenient=warn only

    # File restrictions
    file_restrictions: FileRestrictions = field(default_factory=FileRestrictions)

    # Prompt injection (prepend/append to each prompt)
    prologues: list[str] = field(default_factory=list)  # Content prepended to each prompt
    epilogues: list[str] = field(default_factory=list)  # Content appended to each prompt

    # Prompts (legacy - flat list for backward compatibility)
    prompts: list[str] = field(default_factory=list)
    on_context_limit_prompt: Optional[str] = None

    # Conversation steps (new - ordered sequence including control directives)
    steps: list[ConversationStep] = field(default_factory=list)

    # Compaction
    compact_preserve: list[str] = field(default_factory=list)
    compact_summary: Optional[str] = None

    # Checkpointing
    checkpoint_after: Optional[str] = None  # each-cycle, each-prompt, never
    checkpoint_name: Optional[str] = None

    # Output (supports template variables)
    output_format: str = "markdown"
    output_file: Optional[str] = None
    output_dir: Optional[str] = None

    # Output injection (prepend/append to output)
    headers: list[str] = field(default_factory=list)  # Content prepended to output
    footers: list[str] = field(default_factory=list)  # Content appended to output

    # Command execution settings
    run_on_error: str = "stop"  # stop, continue
    run_output: str = "always"  # always, on-error, never
    run_output_limit: Optional[int] = None  # Max chars to capture (None = unlimited)
    run_env: dict[str, str] = field(default_factory=dict)  # Environment variables for RUN
    run_cwd: Optional[str] = None  # Working directory for RUN commands (relative to workflow dir)
    allow_shell: bool = False  # Security: must opt-in to shell=True for RUN
    run_timeout: int = 60  # Timeout in seconds for RUN commands
    async_processes: list = field(default_factory=list)  # Background processes from RUN-ASYNC

    # Flow control
    pause_points: list[tuple[int, str]] = field(default_factory=list)  # (after_prompt_index, message)

    # Debug configuration
    debug_categories: list[str] = field(default_factory=list)  # session, tool, intent, event, all
    debug_intents: bool = False  # Enable verbose intent tracking
    event_log: Optional[str] = None  # Path for event export (supports template vars)

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

    def validate_context_files(
        self, 
        exclude_patterns: list[str] | None = None,
        allow_missing: bool = False,
    ) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
        """Validate that all CONTEXT file references exist.
        
        Resolution order for relative paths:
        1. CWD (current working directory) - intuitive for users
        2. Workflow file directory - for self-contained workflows
        
        Args:
            exclude_patterns: Additional patterns to exclude from validation
            allow_missing: If True, returns warnings instead of errors
        
        Returns:
            Tuple of (errors, warnings) where each is a list of (pattern, resolved_path).
            Errors are required patterns that are missing.
            Warnings are optional patterns that are missing or excluded patterns.
        """
        import fnmatch as fnmatch_module
        import glob as glob_module
        
        errors = []
        warnings = []
        workflow_base = self.source_path.parent if self.source_path else Path.cwd()
        cwd = Path.cwd()
        
        # Combine file-level and CLI exclusions
        all_exclusions = list(self.context_exclude)
        if exclude_patterns:
            all_exclusions.extend(exclude_patterns)
        
        def is_excluded(pattern: str) -> bool:
            """Check if pattern matches any exclusion."""
            for excl in all_exclusions:
                if fnmatch_module.fnmatch(pattern, excl):
                    return True
                # Also check without @ prefix
                if pattern.startswith("@") and fnmatch_module.fnmatch(pattern[1:], excl):
                    return True
            return False
        
        def validate_pattern(context_ref: str, is_optional: bool = False) -> None:
            """Validate a single context pattern."""
            # Only check @file references (not inline content)
            if not context_ref.startswith("@"):
                return
            
            pattern = context_ref[1:]  # Remove @ prefix
            
            # Check exclusions
            if is_excluded(context_ref) or is_excluded(pattern):
                warnings.append((context_ref, Path(pattern)))
                return
            
            # Absolute paths resolve directly
            if Path(pattern).is_absolute():
                resolved_pattern = Path(pattern)
                found = self._check_pattern_exists(resolved_pattern, glob_module)
                if not found:
                    if is_optional or allow_missing:
                        warnings.append((context_ref, resolved_pattern))
                    else:
                        errors.append((context_ref, resolved_pattern))
                return
            
            # Try CWD first, then workflow directory
            cwd_resolved = cwd / pattern
            workflow_resolved = workflow_base / pattern
            
            cwd_found = self._check_pattern_exists(cwd_resolved, glob_module)
            workflow_found = self._check_pattern_exists(workflow_resolved, glob_module)
            
            if not cwd_found and not workflow_found:
                # Report CWD path since that's what users expect
                if is_optional or allow_missing:
                    warnings.append((context_ref, cwd_resolved))
                else:
                    errors.append((context_ref, cwd_resolved))
        
        # Validate required context files
        for context_ref in self.context_files:
            validate_pattern(context_ref, is_optional=False)
        
        # Validate optional context files (always warnings, never errors)
        for context_ref in self.context_files_optional:
            validate_pattern(context_ref, is_optional=True)
        
        return errors, warnings
    
    def _check_pattern_exists(self, resolved_pattern: Path, glob_module) -> bool:
        """Check if a pattern (file or glob) resolves to existing files."""
        pattern_str = str(resolved_pattern)
        if "*" in pattern_str or "?" in pattern_str or "[" in pattern_str:
            return bool(list(glob_module.glob(pattern_str, recursive=True)))
        else:
            return resolved_pattern.exists()

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

        # File restrictions
        for pattern in self.file_restrictions.allow_patterns:
            lines.append(f"ALLOW-FILES {pattern}")
        for pattern in self.file_restrictions.deny_patterns:
            lines.append(f"DENY-FILES {pattern}")
        for dir_path in self.file_restrictions.allow_dirs:
            lines.append(f"ALLOW-DIR {dir_path}")
        for dir_path in self.file_restrictions.deny_dirs:
            lines.append(f"DENY-DIR {dir_path}")
        
        if (self.file_restrictions.allow_patterns or self.file_restrictions.deny_patterns or
            self.file_restrictions.allow_dirs or self.file_restrictions.deny_dirs):
            lines.append("")

        # Context
        if self.validation_mode != "strict":
            lines.append(f"VALIDATION-MODE {self.validation_mode}")
        if self.context_limit != 0.8:
            lines.append(f"CONTEXT-LIMIT {int(self.context_limit * 100)}%")
        if self.on_context_limit != "compact":
            lines.append(f"ON-CONTEXT-LIMIT {self.on_context_limit}")

        for ctx in self.context_files:
            lines.append(f"CONTEXT {ctx}")
        for ctx in self.context_files_optional:
            lines.append(f"CONTEXT-OPTIONAL {ctx}")
        for pattern in self.context_exclude:
            lines.append(f"CONTEXT-EXCLUDE {pattern}")

        if self.context_files or self.context_files_optional or self.context_exclude:
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

        # Prompt injection (prologues/epilogues)
        for prologue in self.prologues:
            lines.append(f"PROLOGUE {prologue}")
        for epilogue in self.epilogues:
            lines.append(f"EPILOGUE {epilogue}")
        
        if self.prologues or self.epilogues:
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

        # Output injection (headers/footers)
        for header in self.headers:
            lines.append(f"HEADER {header}")
        for footer in self.footers:
            lines.append(f"FOOTER {footer}")
        
        if self.headers or self.footers:
            lines.append("")

        # Output
        if self.output_format != "markdown":
            lines.append(f"OUTPUT-FORMAT {self.output_format}")
        if self.output_file:
            lines.append(f"OUTPUT-FILE {self.output_file}")
        
        # RUN settings (only if non-default)
        if self.run_on_error != "stop":
            lines.append(f"RUN-ON-ERROR {self.run_on_error}")
        if self.run_output != "always":
            lines.append(f"RUN-OUTPUT {self.run_output}")

        return "\n".join(lines)


def _parse_line(line: str, line_num: int) -> Optional[Directive]:
    """Parse a single line into a Directive."""
    # Match DIRECTIVE value pattern (value is optional for some directives)
    match = re.match(r"^([A-Z][A-Z0-9-]*)\s*(.*)$", line)
    if not match:
        return None

    directive_name = match.group(1)
    value = match.group(2).strip() if match.group(2) else ""

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
        case DirectiveType.CONTEXT_OPTIONAL:
            conv.context_files_optional.append(directive.value)
        case DirectiveType.CONTEXT_EXCLUDE:
            conv.context_exclude.append(directive.value)
        case DirectiveType.CONTEXT_LIMIT:
            # Parse "80%" -> 0.8
            value = directive.value.rstrip("%")
            conv.context_limit = float(value) / 100
        case DirectiveType.ON_CONTEXT_LIMIT:
            conv.on_context_limit = directive.value
        case DirectiveType.VALIDATION_MODE:
            conv.validation_mode = directive.value.lower()
        
        # File restrictions
        case DirectiveType.ALLOW_FILES:
            conv.file_restrictions.allow_patterns.append(directive.value)
        case DirectiveType.DENY_FILES:
            conv.file_restrictions.deny_patterns.append(directive.value)
        case DirectiveType.ALLOW_DIR:
            conv.file_restrictions.allow_dirs.append(directive.value)
        case DirectiveType.DENY_DIR:
            conv.file_restrictions.deny_dirs.append(directive.value)
        
        # Prompt injection (prepend/append to each prompt)
        case DirectiveType.PROLOGUE:
            conv.prologues.append(directive.value)
        case DirectiveType.EPILOGUE:
            conv.epilogues.append(directive.value)
        
        # Prompts - add to both flat list and steps
        case DirectiveType.PROMPT:
            conv.prompts.append(directive.value)
            conv.steps.append(ConversationStep(type="prompt", content=directive.value))
        case DirectiveType.ON_CONTEXT_LIMIT_PROMPT:
            conv.on_context_limit_prompt = directive.value
        
        # Conversation control directives
        case DirectiveType.COMPACT:
            # COMPACT with optional preserve list
            preserve = [x.strip() for x in directive.value.split(",")] if directive.value else []
            conv.steps.append(ConversationStep(type="compact", preserve=preserve))
        case DirectiveType.NEW_CONVERSATION:
            conv.steps.append(ConversationStep(type="new_conversation"))
        case DirectiveType.CHECKPOINT:
            conv.steps.append(ConversationStep(type="checkpoint", content=directive.value))
        
        # Legacy compaction settings
        case DirectiveType.COMPACT_PRESERVE:
            # Parse "findings, recommendations" -> ["findings", "recommendations"]
            conv.compact_preserve = [x.strip() for x in directive.value.split(",")]
        case DirectiveType.COMPACT_SUMMARY:
            conv.compact_summary = directive.value
        
        case DirectiveType.CHECKPOINT_AFTER:
            conv.checkpoint_after = directive.value
        case DirectiveType.CHECKPOINT_NAME:
            conv.checkpoint_name = directive.value
        
        # Output (with template variable support)
        case DirectiveType.OUTPUT:
            conv.output_file = directive.value
        case DirectiveType.OUTPUT_FORMAT:
            conv.output_format = directive.value
        case DirectiveType.OUTPUT_FILE:
            conv.output_file = directive.value
        case DirectiveType.OUTPUT_DIR:
            conv.output_dir = directive.value
        
        # Output injection (prepend/append to output)
        case DirectiveType.HEADER:
            conv.headers.append(directive.value)
        case DirectiveType.FOOTER:
            conv.footers.append(directive.value)
        
        # Command execution settings
        case DirectiveType.RUN:
            conv.steps.append(ConversationStep(type="run", content=directive.value))
        case DirectiveType.RUN_ASYNC:
            conv.steps.append(ConversationStep(type="run_async", content=directive.value))
        case DirectiveType.RUN_WAIT:
            conv.steps.append(ConversationStep(type="run_wait", content=directive.value))
        case DirectiveType.RUN_ON_ERROR:
            conv.run_on_error = directive.value.lower()
        case DirectiveType.RUN_OUTPUT:
            conv.run_output = directive.value.lower()
        case DirectiveType.RUN_OUTPUT_LIMIT:
            # Parse limit: "10K", "50K", "100000", "none"
            value = directive.value.strip().lower()
            if value in ("none", "unlimited", ""):
                conv.run_output_limit = None
            elif value.endswith("k"):
                conv.run_output_limit = int(value[:-1]) * 1000
            elif value.endswith("m"):
                conv.run_output_limit = int(value[:-1]) * 1000000
            else:
                conv.run_output_limit = int(value)
        case DirectiveType.ALLOW_SHELL:
            # Parse "true", "yes", "1" as True, anything else as False
            conv.allow_shell = directive.value.lower() in ("true", "yes", "1", "")
        case DirectiveType.RUN_ENV:
            # Parse "KEY=value" format
            if "=" in directive.value:
                key, value = directive.value.split("=", 1)
                conv.run_env[key.strip()] = value.strip()
        case DirectiveType.RUN_CWD:
            # Set working directory for RUN commands
            conv.run_cwd = directive.value.strip()
        case DirectiveType.RUN_TIMEOUT:
            # Parse timeout in seconds (supports "30", "30s", "2m")
            value = directive.value.strip().lower()
            if value.endswith("m"):
                conv.run_timeout = int(value[:-1]) * 60
            elif value.endswith("s"):
                conv.run_timeout = int(value[:-1])
            else:
                conv.run_timeout = int(value)
        
        case DirectiveType.PAUSE:
            # PAUSE after the last prompt added so far
            pause_index = len(conv.prompts) - 1 if conv.prompts else 0
            conv.pause_points.append((pause_index, directive.value))
        
        # Debug directives
        case DirectiveType.DEBUG:
            # Comma-separated debug categories
            categories = [c.strip().lower() for c in directive.value.split(",")]
            conv.debug_categories.extend(categories)
        case DirectiveType.DEBUG_INTENTS:
            # Boolean flag for intent tracking
            conv.debug_intents = directive.value.strip().lower() in ("true", "1", "yes", "on")
        case DirectiveType.EVENT_LOG:
            # Path for event log (supports template variables)
            conv.event_log = directive.value.strip()


def substitute_template_variables(text: str, variables: dict[str, str]) -> str:
    """Substitute {{VARIABLE}} placeholders with values.
    
    Supported variables:
    - DATE: ISO date (YYYY-MM-DD)
    - DATETIME: ISO datetime
    - __WORKFLOW_NAME__: Workflow filename (explicit opt-in, Q-001 safe)
    - __WORKFLOW_PATH__: Full path to workflow (explicit opt-in, Q-001 safe)
    - WORKFLOW_NAME: Workflow filename (only in output paths, not prompts)
    - WORKFLOW_PATH: Full path to workflow (only in output paths, not prompts)
    - COMPONENT_PATH: Full path to current component
    - COMPONENT_NAME: Base name of component (without extension)
    - COMPONENT_DIR: Parent directory of component
    - COMPONENT_TYPE: Type from discovery (plugin, api, etc.)
    - ITERATION_INDEX: Current iteration number (1-based)
    - ITERATION_TOTAL: Total number of components
    - GIT_BRANCH: Current git branch (if available)
    - GIT_COMMIT: Short commit SHA (if available)
    - CWD: Current working directory
    
    Note: WORKFLOW_NAME/WORKFLOW_PATH are excluded from prompts by default to
    avoid influencing agent behavior. Use __WORKFLOW_NAME__ for explicit opt-in.
    See Q-001 in docs/QUIRKS.md.
    """
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def get_standard_variables(
    workflow_path: Optional[Path] = None,
    include_workflow_vars: bool = False,
) -> dict[str, str]:
    """Get standard template variables available in all contexts.
    
    Returns dict with DATE, DATETIME, GIT_BRANCH, GIT_COMMIT, CWD.
    
    Workflow path variables are NOT included by default to avoid influencing
    agent behavior (see Q-001 in docs/QUIRKS.md). Use include_workflow_vars=True
    for output paths only, or use the explicit opt-in __WORKFLOW_NAME__ variable.
    
    Args:
        workflow_path: Path to the workflow file
        include_workflow_vars: If True, include WORKFLOW_NAME and WORKFLOW_PATH
            (use only for output paths, not agent-visible prompts)
    
    Returns:
        Dict with template variables. Always includes __WORKFLOW_NAME__ and
        __WORKFLOW_PATH__ for explicit opt-in regardless of include_workflow_vars.
    """
    import subprocess
    from datetime import datetime
    
    now = datetime.now()
    variables = {
        "DATE": now.strftime("%Y-%m-%d"),
        "DATETIME": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "CWD": str(Path.cwd()),
    }
    
    if workflow_path:
        # Always provide explicit opt-in variables (underscore prefix = explicit)
        variables["__WORKFLOW_NAME__"] = workflow_path.stem
        variables["__WORKFLOW_PATH__"] = str(workflow_path)
        
        # Only include unprefixed versions if explicitly requested (for output paths)
        if include_workflow_vars:
            variables["WORKFLOW_NAME"] = workflow_path.stem
            variables["WORKFLOW_PATH"] = str(workflow_path)
    
    # Try to get git info (fail silently if not in a git repo)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            variables["GIT_BRANCH"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            variables["GIT_COMMIT"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return variables


def resolve_content_reference(value: str, base_path: Optional[Path] = None) -> str:
    """Resolve @file references to file content.
    
    Args:
        value: Either inline text or @path/to/file reference
        base_path: Base path for relative file references (workflow directory)
        
    Returns:
        The resolved content (file contents or original value)
        
    Note:
        Resolution order for relative paths:
        1. CWD (current working directory) - intuitive for CLI users
        2. base_path (workflow file directory) - for self-contained workflows
        
        Logs a warning if file reference cannot be resolved.
    """
    import logging
    logger = logging.getLogger("sdqctl.core.conversation")
    
    if value.startswith("@"):
        file_path = value[1:]  # Remove @ prefix
        
        # Absolute paths resolve directly
        if Path(file_path).is_absolute():
            full_path = Path(file_path)
            if full_path.exists():
                return full_path.read_text()
            else:
                logger.warning(f"File reference not found: {value} (resolved to {full_path})")
                return value
        
        # Try CWD first (intuitive for CLI users)
        cwd_path = Path.cwd() / file_path
        if cwd_path.exists():
            return cwd_path.read_text()
        
        # Fall back to base_path (workflow directory)
        if base_path:
            full_path = base_path / file_path
            if full_path.exists():
                return full_path.read_text()
        
        # Neither worked - log warning with both attempted paths
        if base_path:
            logger.warning(f"File reference not found: {value} (tried {cwd_path} and {base_path / file_path})")
        else:
            logger.warning(f"File reference not found: {value} (resolved to {cwd_path})")
        return value
    return value


def apply_iteration_context(conv: ConversationFile, component_path: str, 
                            iteration_index: int = 1, iteration_total: int = 1,
                            component_type: str = "unknown") -> ConversationFile:
    """Create a copy of ConversationFile with template variables substituted.
    
    Args:
        conv: The original ConversationFile
        component_path: Path to the current component
        iteration_index: Current iteration number (1-based)
        iteration_total: Total number of iterations
        component_type: Type of component from discovery
        
    Returns:
        A new ConversationFile with substituted values
    """
    from copy import deepcopy
    
    path_obj = Path(component_path)
    
    # Combine standard variables with component-specific ones
    # Exclude WORKFLOW_NAME from prompts to avoid Q-001 (agent behavior influenced by filename)
    variables = get_standard_variables(conv.source_path)
    variables.update({
        "COMPONENT_PATH": str(component_path),
        "COMPONENT_NAME": path_obj.stem,
        "COMPONENT_DIR": str(path_obj.parent),
        "COMPONENT_TYPE": component_type,
        "ITERATION_INDEX": str(iteration_index),
        "ITERATION_TOTAL": str(iteration_total),
    })
    
    # Get output-specific variables (includes WORKFLOW_NAME for output paths)
    output_variables = get_standard_variables(conv.source_path, include_workflow_vars=True)
    output_variables.update(variables)
    
    # Deep copy to avoid modifying original
    new_conv = deepcopy(conv)
    
    # Substitute in prompts (no WORKFLOW_NAME - Q-001 fix)
    new_conv.prompts = [substitute_template_variables(p, variables) for p in new_conv.prompts]
    
    # Substitute in prologues and epilogues (no WORKFLOW_NAME - Q-001 fix)
    new_conv.prologues = [substitute_template_variables(p, variables) for p in new_conv.prologues]
    new_conv.epilogues = [substitute_template_variables(e, variables) for e in new_conv.epilogues]
    
    # Substitute in headers and footers (output context, includes WORKFLOW_NAME)
    new_conv.headers = [substitute_template_variables(h, output_variables) for h in new_conv.headers]
    new_conv.footers = [substitute_template_variables(f, output_variables) for f in new_conv.footers]
    
    # Substitute in steps (no WORKFLOW_NAME - Q-001 fix)
    for step in new_conv.steps:
        step.content = substitute_template_variables(step.content, variables)
    
    # Substitute in output paths (includes WORKFLOW_NAME)
    if new_conv.output_file:
        new_conv.output_file = substitute_template_variables(new_conv.output_file, output_variables)
    if new_conv.output_dir:
        new_conv.output_dir = substitute_template_variables(new_conv.output_dir, output_variables)
    
    return new_conv


def build_prompt_with_injection(prompt: str, prologues: list[str], epilogues: list[str],
                                 base_path: Optional[Path] = None,
                                 variables: Optional[dict[str, str]] = None) -> str:
    """Build a complete prompt with prologue/epilogue injection.
    
    Args:
        prompt: The main prompt text
        prologues: List of prologue content (inline or @file references)
        epilogues: List of epilogue content (inline or @file references)
        base_path: Base path for resolving @file references
        variables: Template variables for substitution
        
    Returns:
        Complete prompt with prologues prepended and epilogues appended
    """
    variables = variables or {}
    parts = []
    
    # Resolve and add prologues
    for prologue in prologues:
        content = resolve_content_reference(prologue, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)
    
    # Add main prompt
    parts.append(substitute_template_variables(prompt, variables))
    
    # Resolve and add epilogues
    for epilogue in epilogues:
        content = resolve_content_reference(epilogue, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)
    
    return "\n\n".join(parts)


def build_output_with_injection(output: str, headers: list[str], footers: list[str],
                                 base_path: Optional[Path] = None,
                                 variables: Optional[dict[str, str]] = None) -> str:
    """Build complete output with header/footer injection.
    
    Args:
        output: The main output content
        headers: List of header content (inline or @file references)
        footers: List of footer content (inline or @file references)
        base_path: Base path for resolving @file references
        variables: Template variables for substitution
        
    Returns:
        Complete output with headers prepended and footers appended
    """
    variables = variables or {}
    parts = []
    
    # Resolve and add headers
    for header in headers:
        content = resolve_content_reference(header, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)
    
    # Add main output
    parts.append(output)
    
    # Resolve and add footers
    for footer in footers:
        content = resolve_content_reference(footer, base_path)
        content = substitute_template_variables(content, variables)
        parts.append(content)
    
    return "\n\n".join(parts)
