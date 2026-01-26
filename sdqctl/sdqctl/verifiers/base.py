"""
Base classes and types for verification.

The verification system provides a unified interface for checking
various aspects of the codebase: references, links, terminology,
traceability, and assertions.
"""

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

# Default directories to exclude from verification scans
DEFAULT_EXCLUDES = {
    ".venv",
    "venv",
    ".env",
    "node_modules",
    "__pycache__",
    ".git",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
    "lib",  # Common virtualenv symlink
    "lib64",  # Common virtualenv symlink
}


def load_sdqctlignore(root: Path) -> set[str]:
    """Load exclusion patterns from .sdqctlignore file.

    Format is similar to .gitignore:
    - One pattern per line
    - Lines starting with # are comments
    - Empty lines are ignored
    - Patterns use glob syntax

    Args:
        root: Directory to search for .sdqctlignore

    Returns:
        Set of exclusion patterns
    """
    ignore_file = root / ".sdqctlignore"
    patterns: set[str] = set()

    if ignore_file.exists():
        try:
            for line in ignore_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)
        except Exception:
            pass

    return patterns


def should_exclude(path: Path, root: Path, exclude_patterns: set[str]) -> bool:
    """Check if a path should be excluded from verification.

    Args:
        path: Path to check
        root: Root directory for relative path calculation
        exclude_patterns: Set of glob patterns to exclude

    Returns:
        True if path should be excluded
    """
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        rel_path = path

    rel_str = str(rel_path)

    for pattern in exclude_patterns:
        # Check each part of the path against the pattern
        for part in rel_path.parts:
            if fnmatch.fnmatch(part, pattern):
                return True
        # Also check the full relative path
        if fnmatch.fnmatch(rel_str, pattern):
            return True
        # Check with ** prefix for deep matches
        if fnmatch.fnmatch(rel_str, f"**/{pattern}"):
            return True

    return False


def scan_files(
    root: Path,
    extensions: set[str],
    recursive: bool = True,
    exclude_patterns: set[str] | None = None,
    no_default_excludes: bool = False,
) -> list[Path]:
    """Scan directory for files with specified extensions.

    Consolidates the common file scanning pattern used across verifiers.
    Respects DEFAULT_EXCLUDES and .sdqctlignore patterns.

    Args:
        root: Root directory to scan
        extensions: Set of file extensions to include (e.g., {".py", ".md"})
        recursive: Whether to scan subdirectories (default: True)
        exclude_patterns: Additional patterns to exclude (merged with defaults)
        no_default_excludes: If True, skip DEFAULT_EXCLUDES (default: False)

    Returns:
        List of Path objects matching the criteria

    Example:
        files = scan_files(Path("docs"), {".md", ".rst"}, recursive=True)
    """
    # Build exclusion patterns
    excludes: set[str] = set()
    if not no_default_excludes:
        excludes.update(DEFAULT_EXCLUDES)
    excludes.update(load_sdqctlignore(root))
    if exclude_patterns:
        excludes.update(exclude_patterns)

    # Scan files
    if recursive:
        candidates = root.rglob('*')
    else:
        candidates = root.glob('*')

    files = [
        f for f in candidates
        if f.is_file()
        and f.suffix in extensions
        and not should_exclude(f, root, excludes)
    ]

    return files


@dataclass
class VerificationError:
    """A single verification error or warning."""

    file: str
    line: int | None
    message: str
    fix_hint: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fix_hint": self.fix_hint,
        }


@dataclass
class VerificationResult:
    """Result of a verification run."""

    passed: bool
    errors: list[VerificationError] = field(default_factory=list)
    warnings: list[VerificationError] = field(default_factory=list)
    summary: str = ""
    details: dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Format results as markdown for context injection."""
        lines = []

        # Status header
        status = "✅ Passed" if self.passed else "❌ Failed"
        lines.append(f"## Verification Result: {status}")
        lines.append("")

        # Summary
        if self.summary:
            lines.append(self.summary)
            lines.append("")

        # Errors
        if self.errors:
            lines.append(f"### Errors ({len(self.errors)})")
            lines.append("")
            for err in self.errors:
                loc = f"{err.file}"
                if err.line:
                    loc += f":{err.line}"
                lines.append(f"- **{loc}**: {err.message}")
                if err.fix_hint:
                    lines.append(f"  - Fix: {err.fix_hint}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append(f"### Warnings ({len(self.warnings)})")
            lines.append("")
            for warn in self.warnings:
                loc = f"{warn.file}"
                if warn.line:
                    loc += f":{warn.line}"
                lines.append(f"- **{loc}**: {warn.message}")
            lines.append("")

        # Details
        if self.details:
            lines.append("### Details")
            lines.append("")
            for key, value in self.details.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """Format results as JSON for CLI output."""
        return {
            "passed": self.passed,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "summary": self.summary,
            "details": self.details,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class Verifier(Protocol):
    """Protocol for verification implementations."""

    name: str
    description: str

    def verify(self, root: Path, **options: Any) -> VerificationResult:
        """Run verification and return results.

        Args:
            root: Root directory to verify
            **options: Verifier-specific options

        Returns:
            VerificationResult with pass/fail status and details
        """
        ...
