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
    COMPACT_PROLOGUE = "COMPACT-PROLOGUE"  # Content injected before compacted summary
    COMPACT_EPILOGUE = "COMPACT-EPILOGUE"  # Content injected after compacted summary
    NEW_CONVERSATION = "NEW-CONVERSATION"
    
    # Infinite sessions (SDK native compaction)
    INFINITE_SESSIONS = "INFINITE-SESSIONS"  # enabled|disabled
    COMPACTION_MIN = "COMPACTION-MIN"  # Minimum density % to trigger compaction (0-100)
    COMPACTION_THRESHOLD = "COMPACTION-THRESHOLD"  # SDK background compaction threshold % (0-100)
    
    # Elision (merge adjacent elements into single prompt)
    ELIDE = "ELIDE"  # Merge element above with element below

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
    RUN_RETRY = "RUN-RETRY"  # Retry with AI fix: RUN-RETRY N "prompt"

    # Verification
    VERIFY = "VERIFY"  # Run verification: VERIFY refs, VERIFY links, VERIFY all
    VERIFY_ON_ERROR = "VERIFY-ON-ERROR"  # Failure behavior: fail, continue, warn
    VERIFY_OUTPUT = "VERIFY-OUTPUT"  # Output injection: on-error, always, never
    VERIFY_LIMIT = "VERIFY-LIMIT"  # Max output size: 5K, 10K, 50K, none
    VERIFY_TRACE = "VERIFY-TRACE"  # Check trace link: VERIFY-TRACE UCA-001 -> REQ-020
    VERIFY_COVERAGE = "VERIFY-COVERAGE"  # Check coverage: VERIFY-COVERAGE uca_to_sc >= 80
    # Verification aliases (shortcuts for common VERIFY types)
    CHECK_REFS = "CHECK-REFS"  # Alias for VERIFY refs
    CHECK_LINKS = "CHECK-LINKS"  # Alias for VERIFY links
    CHECK_TRACEABILITY = "CHECK-TRACEABILITY"  # Alias for VERIFY traceability

    # REFCAT - Reference Catalog for precise file excerpts
    REFCAT = "REFCAT"  # Line-level file references: REFCAT @file.py#L10-L50

    # Flow control
    PAUSE = "PAUSE"
    
    # Branching on RUN result
    ON_FAILURE = "ON-FAILURE"  # Block executed if previous RUN fails
    ON_SUCCESS = "ON-SUCCESS"  # Block executed if previous RUN succeeds
    END = "END"  # End of ON-FAILURE/ON-SUCCESS block

    # Pre-flight checks
    REQUIRE = "REQUIRE"  # Require file/command exists: REQUIRE @file.py, REQUIRE cmd:git

    # Help injection
    HELP = "HELP"  # Inject help topic(s) into prologues: HELP directives workflow

    # File inclusion
    INCLUDE = "INCLUDE"  # Include another .conv file: INCLUDE common/setup.conv

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
    
    type: str  # "prompt", "compact", "new_conversation", "checkpoint", "run", "run_retry", "verify"
    content: str = ""  # Prompt text or checkpoint name
    preserve: list[str] = field(default_factory=list)  # For compact
    retry_count: int = 0  # For run_retry: max retries
    retry_prompt: str = ""  # For run_retry: prompt to send on failure
    verify_type: str = ""  # For verify: refs, links, traceability, all
    verify_options: dict = field(default_factory=dict)  # For verify: additional options
    # For RUN with ON-FAILURE/ON-SUCCESS blocks
    on_failure: list["ConversationStep"] = field(default_factory=list)  # Steps to run on failure
    on_success: list["ConversationStep"] = field(default_factory=list)  # Steps to run on success
    

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
    compact_prologue: Optional[str] = None  # Content before compacted summary
    compact_epilogue: Optional[str] = None  # Content after compacted summary
    
    # Infinite sessions (SDK native compaction)
    infinite_sessions: Optional[bool] = None  # None=use adapter default, True=enabled, False=disabled
    compaction_min: Optional[float] = None  # Minimum density to trigger (0.0-1.0), None=use default
    compaction_threshold: Optional[float] = None  # SDK background threshold (0.0-1.0), None=use default

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

    # Verification settings
    verify_on_error: str = "fail"  # fail, continue, warn
    verify_output: str = "on-error"  # on-error, always, never
    verify_limit: Optional[int] = None  # Max output chars (None = unlimited)
    verify_trace_links: list[tuple[str, str]] = field(default_factory=list)  # [(from_id, to_id), ...]
    verify_coverage_checks: list[tuple[str, str, float]] = field(default_factory=list)  # [(metric, op, threshold), ...]

    # REFCAT - Reference Catalog (line-level file excerpts)
    refcat_refs: list[str] = field(default_factory=list)  # @file.py#L10-L50

    # Help topics injected via HELP directive
    help_topics: list[str] = field(default_factory=list)  # Topics to inject into prologues

    # Pre-flight requirements (files/commands that must exist)
    requirements: list[str] = field(default_factory=list)  # @file.py, cmd:git

    # Included files (for INCLUDE directive tracking)
    included_files: list[Path] = field(default_factory=list)  # Paths of included .conv files

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
    def parse(cls, content: str, source_path: Optional[Path] = None, _include_stack: Optional[set] = None) -> "ConversationFile":
        """Parse a ConversationFile from string content.
        
        Args:
            content: The .conv file content to parse.
            source_path: Path to the source file (for relative INCLUDE resolution).
            _include_stack: Internal: Set of already-included files for cycle detection.
        """
        conv = cls(source_path=source_path)
        directives = []
        
        # Track already-included files to prevent cycles
        include_stack = _include_stack or set()
        if source_path:
            include_stack.add(source_path.resolve())

        # Track multiline prompts
        current_multiline: Optional[tuple[DirectiveType, list[str], int]] = None
        
        # Track block context for ON-FAILURE/ON-SUCCESS
        # block_context is None when not in a block, or ("on_failure"|"on_success", steps_list, run_step)
        block_context: Optional[tuple[str, list[ConversationStep], ConversationStep]] = None
        last_run_step: Optional[ConversationStep] = None

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
                    if block_context:
                        # Add to current block instead of main conv
                        _apply_directive_to_block(block_context[1], directive)
                    else:
                        _apply_directive(conv, directive)
                    current_multiline = None

            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Parse directive
            directive = _parse_line(stripped, line_num)
            if directive:
                # Check for block control directives
                if directive.type == DirectiveType.ON_FAILURE:
                    if last_run_step is None:
                        raise ValueError(f"Line {line_num}: ON-FAILURE without preceding RUN")
                    if block_context is not None:
                        raise ValueError(f"Line {line_num}: Nested ON-FAILURE/ON-SUCCESS blocks not allowed")
                    block_context = ("on_failure", [], last_run_step)
                    continue
                
                elif directive.type == DirectiveType.ON_SUCCESS:
                    if last_run_step is None:
                        raise ValueError(f"Line {line_num}: ON-SUCCESS without preceding RUN")
                    if block_context is not None:
                        raise ValueError(f"Line {line_num}: Nested ON-FAILURE/ON-SUCCESS blocks not allowed")
                    block_context = ("on_success", [], last_run_step)
                    continue
                
                elif directive.type == DirectiveType.END:
                    if block_context is None:
                        raise ValueError(f"Line {line_num}: END without matching ON-FAILURE/ON-SUCCESS")
                    block_type, block_steps, run_step = block_context
                    if block_type == "on_failure":
                        run_step.on_failure = block_steps
                    else:
                        run_step.on_success = block_steps
                    block_context = None
                    continue
                
                # Check if this starts a multiline
                if directive.type in (
                    DirectiveType.PROMPT,
                    DirectiveType.ON_CONTEXT_LIMIT_PROMPT,
                    DirectiveType.COMPACT_SUMMARY,
                ):
                    current_multiline = (directive.type, [directive.value], line_num)
                else:
                    directives.append(directive)
                    # Handle INCLUDE specially - needs to merge included file
                    if directive.type == DirectiveType.INCLUDE:
                        cls._process_include(conv, directive, include_stack)
                    elif block_context:
                        # Add to current block
                        _apply_directive_to_block(block_context[1], directive)
                        # Track if this is a RUN within the block (for potential nested blocks - not allowed)
                    else:
                        _apply_directive(conv, directive)
                        # Track RUN steps for ON-FAILURE/ON-SUCCESS attachment
                        if directive.type == DirectiveType.RUN:
                            # Get the last added step (it's a RUN)
                            if conv.steps and conv.steps[-1].type == "run":
                                last_run_step = conv.steps[-1]

        # Handle trailing multiline
        if current_multiline is not None:
            dtype, lines, start_line = current_multiline
            value = "\n".join(lines)
            directive = Directive(
                type=dtype, value=value, line_number=start_line, raw_line="<multiline>"
            )
            directives.append(directive)
            if block_context:
                _apply_directive_to_block(block_context[1], directive)
            else:
                _apply_directive(conv, directive)
        
        # Check for unclosed block
        if block_context is not None:
            block_name = "ON-FAILURE" if block_context[0] == "on_failure" else "ON-SUCCESS"
            raise ValueError(f"Unclosed {block_name} block (missing END)")

        conv.directives = directives
        return conv

    @classmethod
    def from_file(cls, path: Path | str, _include_stack: Optional[set] = None) -> "ConversationFile":
        """Load and parse a ConversationFile from disk."""
        path = Path(path)
        content = path.read_text()
        return cls.parse(content, source_path=path, _include_stack=_include_stack)

    @classmethod
    def _process_include(cls, conv: "ConversationFile", directive: Directive, include_stack: set) -> None:
        """Process INCLUDE directive by merging included file content.
        
        Args:
            conv: The conversation being built
            directive: The INCLUDE directive
            include_stack: Set of already-included file paths for cycle detection
        """
        include_path = directive.value.strip()
        
        # Resolve path relative to current file's directory
        if conv.source_path:
            base_dir = conv.source_path.parent
        else:
            base_dir = Path.cwd()
        
        resolved_path = (base_dir / include_path).resolve()
        
        # Check for include cycle
        if resolved_path in include_stack:
            cycle_files = [str(p) for p in include_stack]
            raise ValueError(
                f"INCLUDE cycle detected: {include_path} at line {directive.line_number}\n"
                f"Include stack: {' -> '.join(cycle_files)} -> {include_path}"
            )
        
        # Check file exists
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"INCLUDE file not found: {include_path} at line {directive.line_number}\n"
                f"Searched: {resolved_path}"
            )
        
        # Parse the included file with cycle detection
        included_conv = cls.from_file(resolved_path, _include_stack=include_stack.copy())
        
        # Track included file
        conv.included_files.append(resolved_path)
        
        # Merge content from included file (metadata is NOT merged - only steps/context)
        # This follows the principle that INCLUDE is for reusable workflow fragments
        conv.context_files.extend(included_conv.context_files)
        conv.context_files_optional.extend(included_conv.context_files_optional)
        conv.context_exclude.extend(included_conv.context_exclude)
        conv.prologues.extend(included_conv.prologues)
        conv.epilogues.extend(included_conv.epilogues)
        conv.prompts.extend(included_conv.prompts)
        conv.steps.extend(included_conv.steps)
        conv.refcat_refs.extend(included_conv.refcat_refs)
        conv.help_topics.extend(included_conv.help_topics)
        conv.requirements.extend(included_conv.requirements)
        conv.included_files.extend(included_conv.included_files)

    @classmethod
    def from_rendered_json(cls, data: dict) -> "ConversationFile":
        """Reconstruct ConversationFile from rendered JSON.
        
        Uses resolved prompts directly (no re-expansion needed).
        This enables external transformation pipelines:
        
            sdqctl render cycle foo.conv --json | transform.py | sdqctl cycle --from-json -
        
        Args:
            data: Dict from format_rendered_json output
            
        Returns:
            ConversationFile with prompts pre-resolved
        """
        # Validate schema version
        schema_version = data.get("schema_version", "1.0")
        major_version = int(schema_version.split(".")[0])
        if major_version > 1:
            raise ValueError(f"Unsupported schema version: {schema_version} (max supported: 1.x)")
        
        conv = cls()
        conv.adapter = data.get("adapter", "copilot")
        conv.model = data.get("model", "gpt-4")
        conv.max_cycles = data.get("max_cycles", 1)
        
        # Extract prompts from first cycle (for single-cycle execution)
        # Multi-cycle support would need additional handling
        cycles = data.get("cycles", [])
        if cycles:
            first_cycle = cycles[0]
            for prompt_data in first_cycle.get("prompts", []):
                # Use resolved (fully expanded) prompt if available
                resolved = prompt_data.get("resolved", prompt_data.get("raw", ""))
                conv.prompts.append(resolved)
                conv.steps.append(ConversationStep(type="prompt", content=resolved))
        
        # Store preloaded context for injection (content already expanded)
        conv._preloaded_context = []
        if cycles:
            for cf in cycles[0].get("context_files", []):
                if "content" in cf:
                    conv._preloaded_context.append({
                        "path": cf.get("path", ""),
                        "content": cf.get("content", ""),
                    })
        
        # Store template variables for reference
        conv._template_variables = data.get("template_variables", {})
        
        return conv

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
    
    def validate_refcat_refs(
        self,
        allow_missing: bool = False,
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Validate that all REFCAT file references exist.
        
        Args:
            allow_missing: If True, returns warnings instead of errors
        
        Returns:
            Tuple of (errors, warnings) where each is a list of (ref, error_message).
        """
        from .refcat import parse_ref, resolve_path, RefcatError
        
        errors = []
        warnings = []
        workflow_base = self.source_path.parent if self.source_path else Path.cwd()
        
        for ref in self.refcat_refs:
            try:
                spec = parse_ref(ref)
                resolve_path(spec, workflow_base)
            except RefcatError as e:
                if allow_missing:
                    warnings.append((ref, str(e)))
                else:
                    errors.append((ref, str(e)))
        
        return errors, warnings
    
    def validate_help_topics(self) -> list[tuple[str, str]]:
        """Validate that all HELP topics exist.
        
        Returns:
            List of (topic, error_message) for unknown topics.
        """
        from ..commands.help import TOPICS
        
        errors = []
        for topic in self.help_topics:
            if topic not in TOPICS:
                known = ", ".join(sorted(TOPICS.keys()))
                errors.append((topic, f"Unknown help topic: '{topic}'. Known topics: {known}"))
        
        return errors
    
    def validate_elide_chains(self) -> list[str]:
        """Validate that ELIDE chains don't contain incompatible constructs.
        
        ELIDE merges steps into a single AI turn. Branching constructs 
        (RUN-RETRY, ON-FAILURE, ON-SUCCESS) require multiple turns and are incompatible.
        
        Returns:
            List of error messages for invalid ELIDE chain usage.
        """
        errors = []
        in_elide_chain = False
        
        for i, step in enumerate(self.steps):
            if step.type == "elide":
                in_elide_chain = True
                continue
            
            # Check for RUN with retry inside ELIDE chain
            if in_elide_chain and step.type == "run" and getattr(step, 'retry_count', 0) > 0:
                errors.append(
                    f"RUN-RETRY at step {i+1} is inside ELIDE chain. "
                    "RUN-RETRY requires multiple AI turns and cannot be used with ELIDE. "
                    "Remove ELIDE or RUN-RETRY."
                )
            
            # Check for RUN with ON-FAILURE/ON-SUCCESS blocks inside ELIDE chain
            if in_elide_chain and step.type == "run":
                if step.on_failure:
                    errors.append(
                        f"ON-FAILURE block at step {i+1} is inside ELIDE chain. "
                        "ON-FAILURE requires separate AI turns and cannot be used with ELIDE. "
                        "Remove ELIDE or ON-FAILURE block."
                    )
                if step.on_success:
                    errors.append(
                        f"ON-SUCCESS block at step {i+1} is inside ELIDE chain. "
                        "ON-SUCCESS requires separate AI turns and cannot be used with ELIDE. "
                        "Remove ELIDE or ON-SUCCESS block."
                    )
            
            # Any non-elide step breaks the chain unless next is elide
            if i + 1 < len(self.steps) and self.steps[i + 1].type == "elide":
                in_elide_chain = True
            else:
                in_elide_chain = False
        
        return errors
    
    def validate_requirements(self, base_path: Optional[Path] = None) -> list[tuple[str, str]]:
        """Validate that all REQUIRE items exist.
        
        Requirements can be:
        - @file.py or @path/to/file - File must exist
        - cmd:git or cmd:npm - Command must be available in PATH
        
        Args:
            base_path: Base path for resolving file requirements.
                       Defaults to workflow directory or CWD.
        
        Returns:
            List of (requirement, error_message) for missing requirements.
        """
        import shutil
        
        errors = []
        
        # Determine base path for file resolution
        if base_path is None:
            if self.source_path:
                base_path = self.source_path.parent
            else:
                base_path = Path.cwd()
        
        for req in self.requirements:
            if req.startswith("cmd:"):
                # Command requirement: check if command exists in PATH
                cmd_name = req[4:]  # Strip "cmd:" prefix
                if not shutil.which(cmd_name):
                    errors.append((req, f"Required command not found: '{cmd_name}'"))
            elif req.startswith("@"):
                # File requirement: check if file/pattern exists
                file_pattern = req[1:]  # Strip "@" prefix
                resolved = base_path / file_pattern
                
                # Check for exact file or glob pattern
                if "*" in file_pattern or "?" in file_pattern:
                    # Glob pattern
                    import glob
                    matches = list(glob.glob(str(resolved)))
                    if not matches:
                        errors.append((req, f"Required file pattern not found: '{file_pattern}'"))
                else:
                    # Exact file
                    if not resolved.exists():
                        errors.append((req, f"Required file not found: '{file_pattern}'"))
            else:
                # Assume it's a file path without @ prefix
                resolved = base_path / req
                if not resolved.exists():
                    errors.append((req, f"Required file not found: '{req}'"))
        
        return errors
    
    def validate_verify_trace_links(self, base_path: Optional[Path] = None) -> list[tuple[str, str]]:
        """Validate VERIFY-TRACE links by checking if artifacts exist in documentation.
        
        This is a static validation that checks if the referenced artifact IDs
        can be found in markdown files under base_path. It does NOT verify the
        actual link relationship - that happens at runtime.
        
        Args:
            base_path: Base path for scanning documentation files.
                       Defaults to workflow directory or CWD.
        
        Returns:
            List of (trace_spec, error_message) for invalid trace links.
        """
        import re
        
        errors = []
        
        if not self.verify_trace_links:
            return errors
        
        # Determine base path
        if base_path is None:
            if self.source_path:
                base_path = self.source_path.parent
            else:
                base_path = Path.cwd()
        
        # Collect all artifact IDs from documentation files
        artifact_ids: set[str] = set()
        artifact_pattern = re.compile(r'\b([A-Z]+-[A-Z0-9-]+[a-z]?)\b')
        
        # Scan markdown files
        for ext in ['.md', '.markdown', '.txt', '.yaml', '.yml']:
            for filepath in base_path.rglob(f'*{ext}'):
                try:
                    content = filepath.read_text(errors='replace')
                    for match in artifact_pattern.finditer(content):
                        artifact_ids.add(match.group(1))
                except Exception:
                    pass
        
        # Check each trace link
        for from_id, to_id in self.verify_trace_links:
            trace_spec = f"{from_id} -> {to_id}"
            
            # Validate artifact ID format
            if not re.match(r'^[A-Z]+-[A-Z0-9-]+[a-z]?$', from_id):
                errors.append((trace_spec, f"Invalid artifact ID format: '{from_id}'"))
                continue
            if not re.match(r'^[A-Z]+-[A-Z0-9-]+[a-z]?$', to_id):
                errors.append((trace_spec, f"Invalid artifact ID format: '{to_id}'"))
                continue
            
            # Check if artifacts exist (warning if not found, not error)
            # The actual link verification happens at runtime
            if from_id not in artifact_ids:
                # This is just a warning - artifact might be defined elsewhere
                pass
            if to_id not in artifact_ids:
                # This is just a warning - artifact might be defined elsewhere
                pass
        
        return errors
    
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
        
        # REFCAT - line-level file excerpts
        for ref in self.refcat_refs:
            lines.append(f"REFCAT {ref}")

        if self.context_files or self.context_files_optional or self.context_exclude or self.refcat_refs:
            lines.append("")

        # Compaction
        if self.compact_preserve:
            lines.append(f"COMPACT-PRESERVE {', '.join(self.compact_preserve)}")
        if self.compact_summary:
            lines.append(f"COMPACT-SUMMARY {self.compact_summary}")
        
        # Infinite sessions
        if self.infinite_sessions is not None:
            lines.append(f"INFINITE-SESSIONS {'enabled' if self.infinite_sessions else 'disabled'}")
        if self.compaction_min is not None:
            lines.append(f"COMPACTION-MIN {int(self.compaction_min * 100)}")
        if self.compaction_threshold is not None:
            lines.append(f"COMPACTION-THRESHOLD {int(self.compaction_threshold * 100)}")

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
        
        # Help topic injection
        if self.help_topics:
            lines.append(f"HELP {' '.join(self.help_topics)}")
        
        if self.prologues or self.epilogues or self.help_topics:
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
        
        # REFCAT - line-level file excerpts
        case DirectiveType.REFCAT:
            # REFCAT can have multiple refs separated by spaces
            # REFCAT @file.py#L10-L50 @other.py#L1-L20
            refs = directive.value.split()
            conv.refcat_refs.extend(refs)
        
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
        
        # Help injection - inject help topics into prologues
        case DirectiveType.HELP:
            # HELP can have multiple topics: HELP directives workflow
            topics = directive.value.split()
            conv.help_topics.extend(topics)
        
        # Pre-flight requirements
        case DirectiveType.REQUIRE:
            # REQUIRE can have multiple items: REQUIRE @file.py cmd:git @other.md
            items = directive.value.split()
            conv.requirements.extend(items)
        
        # File inclusion (handled in parse loop, no-op here)
        case DirectiveType.INCLUDE:
            pass  # Processed inline during parsing
        
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
        case DirectiveType.COMPACT_PROLOGUE:
            conv.compact_prologue = directive.value
        case DirectiveType.COMPACT_EPILOGUE:
            conv.compact_epilogue = directive.value
        
        # Infinite sessions (SDK native compaction)
        case DirectiveType.INFINITE_SESSIONS:
            value_lower = directive.value.lower()
            if value_lower in ("enabled", "true", "yes", "on", "1"):
                conv.infinite_sessions = True
            elif value_lower in ("disabled", "false", "no", "off", "0"):
                conv.infinite_sessions = False
            else:
                raise ValueError(f"Invalid INFINITE-SESSIONS value: {directive.value} (expected enabled/disabled)")
        case DirectiveType.COMPACTION_MIN:
            # Parse "30" or "30%" -> 0.30
            value = directive.value.rstrip("%")
            conv.compaction_min = float(value) / 100
        case DirectiveType.COMPACTION_THRESHOLD:
            # Parse "80" or "80%" -> 0.80
            value = directive.value.rstrip("%")
            conv.compaction_threshold = float(value) / 100
        
        # Elision - merge adjacent elements
        case DirectiveType.ELIDE:
            conv.steps.append(ConversationStep(type="elide", content=directive.value))
        
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
        case DirectiveType.RUN_RETRY:
            # RUN-RETRY modifies the previous RUN step to enable retry-with-AI-fix
            # Format: N "prompt" or N 'prompt' where N is retry count
            # Examples: RUN-RETRY 3 "Fix the failing tests"
            #           RUN-RETRY 2 'Analyze and fix errors'
            value = directive.value.strip()
            import re
            match = re.match(r'^(\d+)\s+["\'](.+)["\']$', value, re.DOTALL)
            if match:
                retry_count = int(match.group(1))
                retry_prompt = match.group(2)
            else:
                # Fallback: first word is count, rest is prompt
                parts = value.split(None, 1)
                retry_count = int(parts[0]) if parts else 3
                retry_prompt = parts[1] if len(parts) > 1 else "Fix the error and try again"
            
            # Find the last RUN step and attach retry config to it
            for i in range(len(conv.steps) - 1, -1, -1):
                if conv.steps[i].type == "run":
                    conv.steps[i].retry_count = retry_count
                    conv.steps[i].retry_prompt = retry_prompt
                    break
            else:
                # No preceding RUN - create standalone (will fail at execution if no command)
                conv.steps.append(ConversationStep(
                    type="run",
                    content="",
                    retry_count=retry_count,
                    retry_prompt=retry_prompt
                ))
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
        
        # Verification directives
        case DirectiveType.VERIFY:
            # VERIFY <type> [options]
            # Examples: VERIFY refs, VERIFY links --external, VERIFY all
            parts = directive.value.strip().split(None, 1)
            verify_type = parts[0].lower() if parts else "all"
            options = {}
            if len(parts) > 1:
                # Parse --key=value or --key options
                import re
                for opt_match in re.finditer(r'--(\w+)(?:=(\S+))?', parts[1]):
                    key = opt_match.group(1)
                    value = opt_match.group(2) if opt_match.group(2) else "true"
                    options[key] = value
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type=verify_type,
                verify_options=options
            ))
        case DirectiveType.VERIFY_ON_ERROR:
            conv.verify_on_error = directive.value.strip().lower()
        case DirectiveType.VERIFY_OUTPUT:
            conv.verify_output = directive.value.strip().lower()
        case DirectiveType.VERIFY_LIMIT:
            # Parse limit: "5K", "10K", "50K", "none"
            value = directive.value.strip().lower()
            if value in ("none", "unlimited", ""):
                conv.verify_limit = None
            elif value.endswith("k"):
                conv.verify_limit = int(value[:-1]) * 1000
            elif value.endswith("m"):
                conv.verify_limit = int(value[:-1]) * 1000000
            else:
                conv.verify_limit = int(value)
        case DirectiveType.VERIFY_TRACE:
            # Parse trace link: "UCA-001 -> REQ-020" or "UCA-001 → REQ-020"
            import re
            value = directive.value.strip()
            # Support both -> and → as arrow
            match = re.match(r'^([A-Z]+-[A-Z0-9-]+[a-z]?)\s*(?:->|→)\s*([A-Z]+-[A-Z0-9-]+[a-z]?)$', value)
            if match:
                from_id = match.group(1)
                to_id = match.group(2)
                conv.verify_trace_links.append((from_id, to_id))
                # Also add as a verify step so it runs during execution
                conv.steps.append(ConversationStep(
                    type="verify_trace",
                    content=f"{from_id} -> {to_id}",
                    verify_type="trace",
                    verify_options={"from": from_id, "to": to_id}
                ))
            else:
                # Invalid format - will be caught during validation
                pass
        case DirectiveType.VERIFY_COVERAGE:
            # Parse coverage check: "metric >= threshold" or empty for report
            # Examples: "uca_to_sc >= 80", "overall >= 50", ""
            import re
            value = directive.value.strip()
            if value:
                # Parse metric comparison: metric op threshold
                match = re.match(r'^(\w+)\s*(>=|<=|>|<|==)\s*(\d+(?:\.\d+)?)%?$', value)
                if match:
                    metric = match.group(1)
                    op = match.group(2)
                    threshold = float(match.group(3))
                    conv.verify_coverage_checks.append((metric, op, threshold))
                    conv.steps.append(ConversationStep(
                        type="verify_coverage",
                        content=value,
                        verify_type="coverage",
                        verify_options={"metric": metric, "op": op, "threshold": threshold}
                    ))
                else:
                    # Invalid format - will be caught during validation
                    pass
            else:
                # Empty value = just run coverage report (no threshold check)
                conv.steps.append(ConversationStep(
                    type="verify_coverage",
                    content="coverage report",
                    verify_type="coverage",
                    verify_options={"report_only": True}
                ))
        
        # CHECK-* aliases for common VERIFY types
        case DirectiveType.CHECK_REFS:
            # Alias for VERIFY refs
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="refs",
                verify_options={}
            ))
        case DirectiveType.CHECK_LINKS:
            # Alias for VERIFY links
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="links",
                verify_options={}
            ))
        case DirectiveType.CHECK_TRACEABILITY:
            # Alias for VERIFY traceability
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="traceability",
                verify_options={}
            ))
        
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


def _apply_directive_to_block(steps: list[ConversationStep], directive: Directive) -> None:
    """Apply a directive inside an ON-FAILURE/ON-SUCCESS block.
    
    Only a subset of directives are allowed inside blocks:
    - PROMPT - send a prompt to the AI
    - RUN - execute a shell command (no nested RUN-RETRY or ON-FAILURE)
    - CHECKPOINT - save state
    - COMPACT - compress context
    
    Configuration directives (MODEL, ADAPTER, etc.) are not allowed in blocks.
    """
    match directive.type:
        case DirectiveType.PROMPT:
            steps.append(ConversationStep(type="prompt", content=directive.value))
        case DirectiveType.RUN:
            steps.append(ConversationStep(type="run", content=directive.value))
        case DirectiveType.CHECKPOINT:
            steps.append(ConversationStep(type="checkpoint", content=directive.value))
        case DirectiveType.COMPACT:
            steps.append(ConversationStep(type="compact", preserve=[]))
        case DirectiveType.COMPACT_PRESERVE:
            # Modify the last COMPACT step if present
            for i in range(len(steps) - 1, -1, -1):
                if steps[i].type == "compact":
                    steps[i].preserve.append(directive.value)
                    break
        case DirectiveType.PAUSE:
            steps.append(ConversationStep(type="pause"))
        case DirectiveType.NEW_CONVERSATION:
            steps.append(ConversationStep(type="new_conversation"))
        case _:
            # Silently ignore configuration directives in blocks
            # This allows blocks to contain only execution-oriented directives
            pass


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
    stop_file_nonce: Optional[str] = None,
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
        stop_file_nonce: Nonce for stop file naming. When provided, adds
            STOP_FILE variable for agent stop signaling (Q-002).
    
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
    
    # Add stop file variable if nonce provided (Q-002 agent stop signaling)
    if stop_file_nonce:
        variables["STOP_FILE"] = f"STOPAUTOMATION-{stop_file_nonce}.json"
    
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
                                 variables: Optional[dict[str, str]] = None,
                                 is_first_prompt: bool = False,
                                 is_last_prompt: bool = False) -> str:
    """Build a complete prompt with prologue/epilogue injection.
    
    Prologues are only injected on the first prompt of a conversation/cycle.
    Epilogues are only injected on the last prompt of a conversation/cycle.
    
    Args:
        prompt: The main prompt text
        prologues: List of prologue content (inline or @file references)
        epilogues: List of epilogue content (inline or @file references)
        base_path: Base path for resolving @file references
        variables: Template variables for substitution
        is_first_prompt: If True, prepend prologues to this prompt
        is_last_prompt: If True, append epilogues to this prompt
        
    Returns:
        Complete prompt with prologues prepended (if first) and epilogues appended (if last)
    """
    variables = variables or {}
    parts = []
    
    # Resolve and add prologues only on first prompt
    if is_first_prompt:
        for prologue in prologues:
            content = resolve_content_reference(prologue, base_path)
            content = substitute_template_variables(content, variables)
            parts.append(content)
    
    # Add main prompt
    parts.append(substitute_template_variables(prompt, variables))
    
    # Resolve and add epilogues only on last prompt
    if is_last_prompt:
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
