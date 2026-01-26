"""
Assertion verification - check that assert statements are traced to requirements.

Scans Python, Swift, Kotlin, and other code files for assertion statements
and verifies they have associated traceability IDs or documentation.

Assertion patterns detected:
- Python: assert <expr>, assert <expr>, <message>
- Swift: assert(), precondition(), fatalError()
- Kotlin: assert(), require(), check()
- TypeScript/JavaScript: console.assert(), assert()
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import (
    VerificationError,
    VerificationResult,
    scan_files,
)


@dataclass
class Assertion:
    """A single assertion found in code."""
    file: str
    line: int
    content: str
    language: str
    has_message: bool = False
    has_trace_id: bool = False
    trace_id: str | None = None


class AssertionsVerifier:
    """Verify that assertions are properly documented and traced.

    Scans source files for assertion statements and checks:
    1. Whether assertions have meaningful messages
    2. Whether assertions link to traceability IDs (REQ, SC, UCA)

    This helps ensure safety-critical assertions are properly documented
    for regulatory compliance (IEC 62304, ISO 14971).
    """

    name = "assertions"
    description = "Check that assertions are documented and traced"

    # Language-specific assertion patterns
    ASSERTION_PATTERNS = {
        "python": [
            # assert expr
            re.compile(r'^\s*assert\s+(.+?)(?:,\s*(.+))?$', re.MULTILINE),
        ],
        "swift": [
            # assert(condition), assert(condition, message)
            re.compile(r'\bassert\s*\(\s*(.+?)(?:,\s*(.+))?\s*\)', re.MULTILINE),
            # precondition(condition, message)
            re.compile(r'\bprecondition\s*\(\s*(.+?)(?:,\s*(.+))?\s*\)', re.MULTILINE),
            # fatalError(message)
            re.compile(r'\bfatalError\s*\(\s*(.+)\s*\)', re.MULTILINE),
        ],
        "kotlin": [
            # assert(condition)
            re.compile(r'\bassert\s*\(\s*(.+?)\s*\)', re.MULTILINE),
            # require(condition) { message }
            re.compile(r'\brequire\s*\(\s*(.+?)\s*\)(?:\s*\{(.+?)\})?', re.MULTILINE),
            # check(condition) { message }
            re.compile(r'\bcheck\s*\(\s*(.+?)\s*\)(?:\s*\{(.+?)\})?', re.MULTILINE),
        ],
        "typescript": [
            # console.assert(condition, message)
            re.compile(r'\bconsole\.assert\s*\(\s*(.+?)(?:,\s*(.+))?\s*\)', re.MULTILINE),
            # assert(condition, message) - common assertion libraries
            re.compile(r'\bassert\s*\(\s*(.+?)(?:,\s*(.+))?\s*\)', re.MULTILINE),
        ],
    }

    # File extensions by language
    EXTENSIONS_BY_LANGUAGE = {
        ".py": "python",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "typescript",  # Use same patterns
        ".jsx": "typescript",
    }

    # Traceability ID patterns (from traceability.py)
    TRACE_ID_PATTERN = re.compile(
        r'\b(REQ-[A-Z0-9]*-?\d{3}|SPEC-\d{3}|SC-[A-Z0-9]*-?\d{3}[a-z]?|'
        r'UCA-[A-Z0-9]*-?\d{3}|TEST-\d{3})\b'
    )

    def verify(
        self,
        root: Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
        exclude: set[str] | None = None,
        no_default_excludes: bool = False,
        require_message: bool = False,
        require_trace: bool = False,
        **options: Any
    ) -> VerificationResult:
        """Verify assertions in source files.

        Args:
            root: Directory to scan
            recursive: Whether to scan subdirectories
            extensions: File extensions to scan (default: all supported)
            exclude: Additional patterns to exclude
            no_default_excludes: If True, don't apply default exclusions
            require_message: If True, error if assertion lacks message
            require_trace: If True, error if assertion lacks trace ID

        Returns:
            VerificationResult with assertion coverage metrics
        """
        root = Path(root)
        scan_ext = extensions or set(self.EXTENSIONS_BY_LANGUAGE.keys())

        # Build exclusion patterns for scan_files
        extra_excludes: set[str] = set()
        if exclude:
            extra_excludes.update(exclude)

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # Stats
        files_scanned = 0
        assertions_found = 0
        assertions_with_message = 0
        assertions_with_trace = 0
        assertions_by_language: dict[str, int] = {}

        # Collect all assertions
        all_assertions: list[Assertion] = []

        # Find files to scan (scan_files handles exclusion)
        files = scan_files(
            root,
            scan_ext,
            recursive=recursive,
            exclude_patterns=extra_excludes,
            no_default_excludes=no_default_excludes,
        )

        for filepath in files:
            files_scanned += 1
            language = self.EXTENSIONS_BY_LANGUAGE.get(filepath.suffix)
            if not language:
                continue

            try:
                content = filepath.read_text(errors='replace')
            except Exception as e:
                warnings.append(VerificationError(
                    file=str(self._relative_path(filepath, root)),
                    line=None,
                    message=f"Could not read file: {e}",
                ))
                continue

            # Find assertions in file
            file_assertions = self._find_assertions(
                content,
                str(self._relative_path(filepath, root)),
                language
            )

            for assertion in file_assertions:
                assertions_found += 1
                assertions_by_language[language] = assertions_by_language.get(language, 0) + 1

                if assertion.has_message:
                    assertions_with_message += 1
                if assertion.has_trace_id:
                    assertions_with_trace += 1

                all_assertions.append(assertion)

                # Check requirements
                if require_message and not assertion.has_message:
                    errors.append(VerificationError(
                        file=assertion.file,
                        line=assertion.line,
                        message=f"Assertion lacks message: {assertion.content[:50]}...",
                        fix_hint="Add a descriptive message to the assertion",
                    ))
                elif not assertion.has_message:
                    warnings.append(VerificationError(
                        file=assertion.file,
                        line=assertion.line,
                        message=f"Assertion lacks message: {assertion.content[:50]}...",
                        fix_hint="Consider adding a descriptive message",
                    ))

                if require_trace and not assertion.has_trace_id:
                    errors.append(VerificationError(
                        file=assertion.file,
                        line=assertion.line,
                        message=f"Assertion lacks trace ID: {assertion.content[:50]}...",
                        fix_hint="Add REQ-NNN, SC-NNN, or UCA-NNN in message or comment",
                    ))

        # Calculate coverage
        message_coverage = (assertions_with_message / assertions_found * 100) if assertions_found > 0 else 0
        trace_coverage = (assertions_with_trace / assertions_found * 100) if assertions_found > 0 else 0

        # Build result
        passed = len(errors) == 0

        summary = (
            f"Scanned {files_scanned} file(s), found {assertions_found} assertion(s): "
            f"{assertions_with_message} with messages ({message_coverage:.0f}%), "
            f"{assertions_with_trace} with trace IDs ({trace_coverage:.0f}%)"
        )

        return VerificationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            summary=summary,
            details={
                "files_scanned": files_scanned,
                "assertions_found": assertions_found,
                "assertions_with_message": assertions_with_message,
                "assertions_with_trace": assertions_with_trace,
                "message_coverage": message_coverage,
                "trace_coverage": trace_coverage,
                "by_language": assertions_by_language,
            },
        )

    def _find_assertions(
        self,
        content: str,
        filepath: str,
        language: str,
    ) -> list[Assertion]:
        """Find all assertions in a file."""
        assertions: list[Assertion] = []
        patterns = self.ASSERTION_PATTERNS.get(language, [])

        if not patterns:
            return assertions

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    _condition = match.group(1) if match.lastindex >= 1 else ""  # noqa: F841
                    message = match.group(2) if match.lastindex >= 2 else None

                    # Check for trace ID in message or preceding comment
                    trace_id = None
                    has_trace = False

                    # Check message for trace ID
                    if message:
                        trace_match = self.TRACE_ID_PATTERN.search(message)
                        if trace_match:
                            trace_id = trace_match.group(1)
                            has_trace = True

                    # Check preceding comment (look at previous line)
                    if not has_trace and line_num > 1:
                        prev_line = lines[line_num - 2]  # 0-indexed
                        if self._is_comment(prev_line, language):
                            trace_match = self.TRACE_ID_PATTERN.search(prev_line)
                            if trace_match:
                                trace_id = trace_match.group(1)
                                has_trace = True

                    # Check same-line comment
                    if not has_trace:
                        comment_start = self._get_comment_marker(language)
                        if comment_start:
                            comment_idx = line.find(comment_start)
                            if comment_idx > match.end():
                                comment_text = line[comment_idx:]
                                trace_match = self.TRACE_ID_PATTERN.search(comment_text)
                                if trace_match:
                                    trace_id = trace_match.group(1)
                                    has_trace = True

                    assertions.append(Assertion(
                        file=filepath,
                        line=line_num,
                        content=line.strip(),
                        language=language,
                        has_message=bool(message and message.strip()),
                        has_trace_id=has_trace,
                        trace_id=trace_id,
                    ))

        return assertions

    def _is_comment(self, line: str, language: str) -> bool:
        """Check if a line is a comment."""
        stripped = line.strip()
        if language == "python":
            return stripped.startswith('#')
        elif language in ("swift", "kotlin", "typescript"):
            return stripped.startswith('//') or stripped.startswith('/*')
        return False

    def _get_comment_marker(self, language: str) -> str | None:
        """Get the inline comment marker for a language."""
        if language == "python":
            return '#'
        elif language in ("swift", "kotlin", "typescript"):
            return '//'
        return None

    def _relative_path(self, path: Path, root: Path) -> Path:
        """Get path relative to root, or absolute if not under root."""
        try:
            return path.relative_to(root)
        except ValueError:
            return path
