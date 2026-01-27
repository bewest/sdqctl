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

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .applicator import apply_directive, apply_directive_to_block
from .parser import parse_line
from .types import (
    ConversationStep,
    Directive,
    DirectiveType,
    FileRestrictions,
    _mask_env_value,
)

if TYPE_CHECKING:
    from ..models import ModelRequirements


def _get_default_model() -> str:
    """Get default model from config (lazy import to avoid circular deps)."""
    try:
        from ..config import get_default_model
        return get_default_model()
    except ImportError:
        return "gpt-4"


def _get_default_adapter() -> str:
    """Get default adapter from config (lazy import to avoid circular deps)."""
    try:
        from ..config import get_default_adapter
        return get_default_adapter()
    except ImportError:
        return "copilot"


def _get_default_context_limit() -> float:
    """Get default context limit from config (lazy import to avoid circular deps)."""
    try:
        from ..config import get_context_limit
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
    session_name: Optional[str] = None  # Named session for resumability

    # Model requirements (abstract model selection)
    # Lazy import to avoid circular dependency
    model_requirements: Optional["ModelRequirements"] = None

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
    # None=use adapter default, True=enabled, False=disabled
    infinite_sessions: Optional[bool] = None
    # Minimum density to trigger (0.0-1.0), None=use default
    compaction_min: Optional[float] = None
    # SDK background threshold (0.0-1.0), None=use default
    compaction_threshold: Optional[float] = None
    # SDK buffer exhaustion threshold (0.0-1.0), None=use default
    compaction_max: Optional[float] = None

    # Checkpointing
    checkpoint_after: Optional[str] = None  # each-cycle, each-prompt, never
    checkpoint_name: Optional[str] = None

    # CONSULT timeout (e.g., "1h", "30m", "7d", None=no timeout)
    consult_timeout: Optional[str] = None

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
    # [(from_id, to_id), ...]
    verify_trace_links: list[tuple[str, str]] = field(default_factory=list)
    # [(metric, op, threshold), ...]
    verify_coverage_checks: list[tuple[str, str, float]] = field(default_factory=list)

    # REFCAT - Reference Catalog (line-level file excerpts)
    refcat_refs: list[str] = field(default_factory=list)  # @file.py#L10-L50

    # Help topics injected via HELP directive
    help_topics: list[str] = field(default_factory=list)  # Topics to inject into prologues

    # Pre-flight requirements (files/commands that must exist)
    requirements: list[str] = field(default_factory=list)  # @file.py, cmd:git

    # Included files (for INCLUDE directive tracking)
    included_files: list[Path] = field(default_factory=list)  # Paths of included .conv files

    # Flow control
    # (after_prompt_index, message)
    pause_points: list[tuple[int, str]] = field(default_factory=list)
    # (after_prompt_index, topic)
    consult_points: list[tuple[int, str]] = field(default_factory=list)

    # Debug configuration
    debug_categories: list[str] = field(default_factory=list)  # session, tool, intent, event, all
    debug_intents: bool = False  # Enable verbose intent tracking
    event_log: Optional[str] = None  # Path for event export (supports template vars)

    # Source
    source_path: Optional[Path] = None
    directives: list[Directive] = field(default_factory=list)

    @classmethod
    def parse(
        cls,
        content: str,
        source_path: Optional[Path] = None,
        _include_stack: Optional[set] = None
    ) -> "ConversationFile":
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
        # block_context: None or ("on_failure"|"on_success", steps_list, run_step)
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
                        apply_directive_to_block(block_context[1], directive)
                    else:
                        apply_directive(conv, directive)
                    current_multiline = None

            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Parse directive
            directive = parse_line(stripped, line_num)
            if directive:
                # Check for block control directives
                if directive.type == DirectiveType.ON_FAILURE:
                    if last_run_step is None:
                        raise ValueError(
                            f"Line {line_num}: ON-FAILURE without preceding RUN"
                        )
                    if block_context is not None:
                        raise ValueError(
                            f"Line {line_num}: Nested ON-FAILURE/ON-SUCCESS not allowed"
                        )
                    block_context = ("on_failure", [], last_run_step)
                    continue

                elif directive.type == DirectiveType.ON_SUCCESS:
                    if last_run_step is None:
                        raise ValueError(
                            f"Line {line_num}: ON-SUCCESS without preceding RUN"
                        )
                    if block_context is not None:
                        raise ValueError(
                            f"Line {line_num}: Nested ON-FAILURE/ON-SUCCESS not allowed"
                        )
                    block_context = ("on_success", [], last_run_step)
                    continue

                elif directive.type == DirectiveType.END:
                    if block_context is None:
                        raise ValueError(
                            f"Line {line_num}: END without matching ON-FAILURE/ON-SUCCESS"
                        )
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
                        apply_directive_to_block(block_context[1], directive)
                        # Track RUN within block (nested blocks not allowed)
                    else:
                        apply_directive(conv, directive)
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
                apply_directive_to_block(block_context[1], directive)
            else:
                apply_directive(conv, directive)

        # Check for unclosed block
        if block_context is not None:
            block_name = "ON-FAILURE" if block_context[0] == "on_failure" else "ON-SUCCESS"
            raise ValueError(f"Unclosed {block_name} block (missing END)")

        conv.directives = directives
        return conv

    @classmethod
    def from_file(
        cls, path: Path | str, _include_stack: Optional[set] = None
    ) -> "ConversationFile":
        """Load and parse a ConversationFile from disk."""
        path = Path(path)
        content = path.read_text()
        return cls.parse(content, source_path=path, _include_stack=_include_stack)

    @classmethod
    def _process_include(
        cls, conv: "ConversationFile", directive: Directive, include_stack: set
    ) -> None:
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
        
        Expands glob patterns before validation, storing expanded refs
        back to self.refcat_refs for use in rendering.

        Args:
            allow_missing: If True, returns warnings instead of errors

        Returns:
            Tuple of (errors, warnings) where each is a list of (ref, error_message).
        """
        from ..refcat import RefcatError, expand_glob_refs, parse_ref, resolve_path

        errors = []
        warnings = []
        workflow_base = self.source_path.parent if self.source_path else Path.cwd()

        # Expand glob patterns first (e.g., @src/**/*.py -> [@src/a.py, @src/b.py])
        expanded_refs = expand_glob_refs(self.refcat_refs, workflow_base)
        
        # Store expanded refs back for rendering
        self.refcat_refs = expanded_refs

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
        from ..help_topics import TOPICS

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

    def validate_verify_trace_links(
        self, base_path: Optional[Path] = None
    ) -> list[tuple[str, str]]:
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

        has_context = (
            self.context_files or self.context_files_optional
            or self.context_exclude or self.refcat_refs
        )
        if has_context:
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
        if self.compaction_max is not None:
            lines.append(f"COMPACTION-MAX {int(self.compaction_max * 100)}")

        # Checkpointing
        if self.checkpoint_after:
            lines.append(f"CHECKPOINT-AFTER {self.checkpoint_after}")
        if self.checkpoint_name:
            lines.append(f"CHECKPOINT-NAME {self.checkpoint_name}")

        if self.compact_preserve or self.checkpoint_after:
            lines.append("")

        # RUN command settings
        if self.allow_shell:
            lines.append("ALLOW-SHELL true")
        if self.run_cwd:
            lines.append(f"RUN-CWD {self.run_cwd}")
        if self.run_timeout != 60:
            lines.append(f"RUN-TIMEOUT {self.run_timeout}")
        # RUN-ENV with secret masking for serialization
        for key, value in self.run_env.items():
            masked_value = _mask_env_value(key, value)
            lines.append(f"RUN-ENV {key}={masked_value}")

        if self.allow_shell or self.run_cwd or self.run_timeout != 60 or self.run_env:
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
