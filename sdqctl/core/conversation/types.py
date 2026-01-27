"""Directive types and dataclasses for ConversationFile parsing."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Patterns for detecting secret environment variable names
SECRET_KEY_PATTERNS = ('KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'AUTH', 'CREDENTIAL', 'API_')


def _mask_env_value(key: str, value: str) -> str:
    """Mask environment variable value if key suggests it's a secret.

    Args:
        key: Environment variable name
        value: Environment variable value

    Returns:
        Original value or masked version (first 3 chars + ***)
    """
    key_upper = key.upper()
    for pattern in SECRET_KEY_PATTERNS:
        if pattern in key_upper:
            if len(value) > 3:
                return value[:3] + '***'
            return '***'
    return value


class DirectiveType(Enum):
    """Types of directives in a ConversationFile."""

    # Metadata
    MODEL = "MODEL"
    ADAPTER = "ADAPTER"
    MODE = "MODE"
    MAX_CYCLES = "MAX-CYCLES"
    CWD = "CWD"
    SESSION_NAME = "SESSION-NAME"  # Named session for resumability

    # Model requirements (abstract model selection)
    MODEL_REQUIRES = "MODEL-REQUIRES"  # Capability requirement: MODEL-REQUIRES context:50k
    MODEL_PREFERS = "MODEL-PREFERS"    # Soft preference: MODEL-PREFERS vendor:anthropic
    MODEL_POLICY = "MODEL-POLICY"      # Resolution policy: MODEL-POLICY cheapest

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
    COMPACTION_MAX = "COMPACTION-MAX"  # SDK buffer exhaustion threshold % (0-100)

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
    CONSULT = "CONSULT"  # Pause with proactive question presentation on resume
    CONSULT_TIMEOUT = "CONSULT-TIMEOUT"  # Timeout for CONSULT: CONSULT-TIMEOUT 1h, 30m, 7d

    # Branching on RUN result
    ON_FAILURE = "ON-FAILURE"  # Block executed if previous RUN fails
    ON_SUCCESS = "ON-SUCCESS"  # Block executed if previous RUN succeeds
    END = "END"  # End of ON-FAILURE/ON-SUCCESS block

    # Pre-flight checks
    REQUIRE = "REQUIRE"  # Require file/command exists: REQUIRE @file.py, REQUIRE cmd:git

    # Help injection
    HELP = "HELP"  # Inject help topic(s) into prologues: HELP directives workflow
    HELP_INLINE = "HELP-INLINE"  # Inject help inline before next prompt: HELP-INLINE stpa

    # LSP - Language Server Protocol queries
    LSP = "LSP"  # Query type/symbol info: LSP type Treatment -p ./src

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

    # Step types: prompt, compact, new_conversation, checkpoint, run,
    # run_retry, verify, pause, consult, help_inline
    type: str
    content: str = ""  # Prompt text or checkpoint name
    preserve: list[str] = field(default_factory=list)  # For compact
    retry_count: int = 0  # For run_retry: max retries
    retry_prompt: str = ""  # For run_retry: prompt to send on failure
    verify_type: str = ""  # For verify: refs, links, traceability, all
    verify_options: dict = field(default_factory=dict)  # For verify: additional options
    merge_with_next: bool = False  # For help_inline: merge content with following step
    # For RUN with ON-FAILURE/ON-SUCCESS blocks
    on_failure: list["ConversationStep"] = field(default_factory=list)  # Steps to run on failure
    on_success: list["ConversationStep"] = field(default_factory=list)  # Steps to run on success
