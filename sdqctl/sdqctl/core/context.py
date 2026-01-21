"""
Context management for AI workflows.

Handles:
- File inclusion via @path syntax
- Glob pattern expansion
- Context window tracking
- Compaction triggers
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ContextFile:
    """A file included in the context."""

    path: Path
    content: str
    tokens_estimate: int  # Rough estimate: chars / 4


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
        """
        # Strip @ prefix if present
        if pattern.startswith("@"):
            pattern = pattern[1:]

        # Resolve relative to base path
        full_pattern = self.base_path / pattern

        # Check if it's a glob pattern
        if "*" in pattern or "?" in pattern:
            # Use pathlib glob
            if "**" in pattern:
                # Recursive glob
                parts = pattern.split("**")
                if len(parts) == 2:
                    base = self.base_path / parts[0].rstrip("/")
                    sub_pattern = parts[1].lstrip("/")
                    return list(base.glob(f"**/{sub_pattern}"))
            else:
                parent = full_pattern.parent
                name_pattern = full_pattern.name
                if parent.exists():
                    return [p for p in parent.iterdir() if fnmatch.fnmatch(p.name, name_pattern)]
            return []
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

        # Estimate tokens (rough: 4 chars per token)
        tokens = len(content) // 4

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
            rel_path = ctx_file.path.relative_to(self.base_path) if self.base_path else ctx_file.path
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
