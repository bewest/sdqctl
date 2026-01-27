"""
Context management for AI workflows.

Handles:
- File inclusion via @path syntax
- Glob pattern expansion
- Context window tracking
- Compaction triggers

Token Estimation Note:
    Token counts are estimated using a simple heuristic of ~4 characters per token.
    This is a rough approximation that works reasonably well for English text and code.
    Actual token counts vary by model and content type:
    - GPT models: use tiktoken for accurate counts
    - Claude models: typically ~3.5 chars/token for code

    For precise token budgeting, consider integrating tiktoken or model-specific
    tokenizers. The current heuristic prioritizes simplicity and zero dependencies.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def estimate_tokens(content: str) -> int:
    """Estimate token count for content.

    Uses ~4 characters per token heuristic. This is approximate;
    see module docstring for accuracy considerations.
    """
    return len(content) // 4


@dataclass
class ContextFile:
    """A file included in the context."""

    path: Path
    content: str
    tokens_estimate: int  # Approximate; see estimate_tokens()


@dataclass
class ContextWindow:
    """Tracks context window usage."""

    used_tokens: int = 0
    max_tokens: int = 128000  # Default for modern models
    limit_threshold: float = 0.8  # Trigger compaction at 80%

    @property
    def usage_percent(self) -> float:
        """Get context usage as percentage."""
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 0

    @property
    def is_near_limit(self) -> bool:
        """Check if context is approaching the configured limit."""
        return self.usage_percent >= self.limit_threshold

    @property
    def available_tokens(self) -> int:
        """Get remaining available tokens before limit."""
        limit_tokens = int(self.max_tokens * self.limit_threshold)
        return max(0, limit_tokens - self.used_tokens)


class ContextManager:
    """Manages context files and window tracking."""

    def __init__(
        self,
        base_path: Optional[Path] = None,
        max_tokens: int = 128000,
        limit_threshold: float = 0.8,
        path_filter: Optional[callable] = None,
    ):
        self.base_path = base_path or Path.cwd()
        self.window = ContextWindow(max_tokens=max_tokens, limit_threshold=limit_threshold)
        self.files: list[ContextFile] = []
        self.conversation_tokens: int = 0
        self.path_filter = path_filter  # Optional filter: (path: str) -> bool

    def resolve_pattern(self, pattern: str) -> list[Path]:
        """Resolve a context pattern to file paths.

        Patterns:
          @lib/auth.js        -> Single file
          @lib/auth/*.js      -> Glob pattern
          @lib/**/*.js        -> Recursive glob

        Resolution order for relative paths:
          1. CWD (current working directory) - intuitive for users
          2. base_path (workflow file directory) - for self-contained workflows
        """
        # Strip @ prefix if present
        if pattern.startswith("@"):
            pattern = pattern[1:]

        # Absolute paths resolve directly
        if Path(pattern).is_absolute():
            return self._resolve_pattern_from_base(Path(pattern).parent, Path(pattern).name)

        # Try CWD first, then base_path
        cwd = Path.cwd()
        cwd_results = self._resolve_pattern_from_base(cwd, pattern)
        if cwd_results:
            return cwd_results

        # Fall back to base_path (workflow directory)
        return self._resolve_pattern_from_base(self.base_path, pattern)

    def _resolve_pattern_from_base(self, base: Path, pattern: str) -> list[Path]:
        """Resolve a pattern relative to a specific base path."""
        full_pattern = base / pattern

        # Check if it's a glob pattern
        if "*" in pattern or "?" in pattern or "[" in pattern:
            # Use Python's glob module for proper pattern matching
            import glob as glob_module

            pattern_str = str(full_pattern)

            # Handle ** recursive patterns
            if "**" in pattern:
                matches = list(glob_module.glob(pattern_str, recursive=True))
            else:
                # For patterns like mapping/*/README.md, use glob directly
                matches = list(glob_module.glob(pattern_str))

            return [Path(m) for m in matches if Path(m).is_file()]
        else:
            # Single file
            if full_pattern.exists() and full_pattern.is_file():
                return [full_pattern]
            return []

    def add_file(self, path: Path) -> Optional[ContextFile]:
        """Add a file to the context.

        Respects path_filter if configured (e.g., for DENY-FILES restrictions).
        """
        if not path.exists():
            return None

        # Apply path filter if configured
        if self.path_filter is not None:
            if not self.path_filter(str(path)):
                return None  # Filtered out by restrictions

        try:
            content = path.read_text()
        except Exception:
            return None

        tokens = estimate_tokens(content)

        ctx_file = ContextFile(path=path, content=content, tokens_estimate=tokens)
        self.files.append(ctx_file)
        self.window.used_tokens += tokens

        return ctx_file

    def add_pattern(self, pattern: str) -> list[ContextFile]:
        """Add files matching a pattern to the context."""
        paths = self.resolve_pattern(pattern)
        added = []
        for path in paths:
            ctx_file = self.add_file(path)
            if ctx_file:
                added.append(ctx_file)
        return added

    def add_conversation_turn(self, content: str) -> None:
        """Track tokens from a conversation turn."""
        tokens = len(content) // 4
        self.conversation_tokens += tokens
        self.window.used_tokens += tokens

    def get_context_content(self) -> str:
        """Get formatted context content for inclusion in prompts."""
        if not self.files:
            return ""

        parts = ["## Context Files\n"]
        for ctx_file in self.files:
            try:
                if self.base_path:
                    rel_path = ctx_file.path.relative_to(self.base_path)
                else:
                    rel_path = ctx_file.path
            except ValueError:
                # File is not in base_path subtree, use absolute or name
                rel_path = ctx_file.path
            parts.append(f"### {rel_path}\n```\n{ctx_file.content}\n```\n")

        return "\n".join(parts)

    def clear_files(self) -> None:
        """Clear loaded files (for compaction)."""
        file_tokens = sum(f.tokens_estimate for f in self.files)
        self.window.used_tokens -= file_tokens
        self.files = []

    def get_status(self) -> dict:
        """Get context status for reporting."""
        return {
            "files_loaded": len(self.files),
            "file_tokens": sum(f.tokens_estimate for f in self.files),
            "conversation_tokens": self.conversation_tokens,
            "total_tokens": self.window.used_tokens,
            "max_tokens": self.window.max_tokens,
            "usage_percent": round(self.window.usage_percent * 100, 1),
            "near_limit": self.window.is_near_limit,
            "available_tokens": self.window.available_tokens,
        }
