"""
Terminology verification - check consistent usage of defined terms.

Scans markdown and code files for terminology usage and verifies
consistency against a glossary file. Detects:
- Deprecated terms (e.g., "quine" should be "synthesis cycle")
- Inconsistent capitalization (e.g., "Conversation file" vs "conversation file")
- Missing glossary entries for commonly used technical terms

Default glossary: docs/GLOSSARY.md (auto-detected)
Custom glossary: --glossary path/to/glossary.md
"""

import re
from pathlib import Path
from typing import Any

from .base import (
    VerificationError,
    VerificationResult,
    scan_files,
)


class TerminologyVerifier:
    """Verify terminology consistency against a glossary.

    Checks for deprecated terms, inconsistent capitalization, and
    ensures technical terms match glossary definitions.
    """

    name = "terminology"
    description = "Check terminology consistency against glossary"

    # File extensions to scan
    SCAN_EXTENSIONS = {'.md', '.conv', '.txt', '.rst'}

    # Deprecated terms → preferred replacements
    # These are checked regardless of glossary
    DEPRECATED_TERMS = {
        # Historical sdqctl terminology
        r'\bquine\b': 'synthesis cycle',
        r'\bquine-like\b': 'synthesis cycle',
        r'\bquine pattern\b': 'synthesis cycle pattern',
        # Common misusage
        r'\bself-replicat': 'synthesis (not self-replication)',
    }

    # Terms requiring specific capitalization
    # Format: lowercase term -> correct form
    CAPITALIZATION_RULES = {
        'sdqctl': 'sdqctl',  # Always lowercase
        'copilot': 'Copilot',  # Capitalize when referring to GitHub Copilot
        'nightscout': 'Nightscout',  # Project name capitalized
        'stpa': 'STPA',  # Acronym all caps
        'iec 62304': 'IEC 62304',
        'iso 14971': 'ISO 14971',
    }

    # Pattern to extract glossary terms from markdown
    GLOSSARY_TERM_PATTERN = re.compile(
        r'^###?\s+(?:"|\')?([^"\'\n]+?)(?:"|\')?(?:\s+\(deprecated\))?\s*$',
        re.MULTILINE
    )

    # Pattern for definition lists (term: definition)
    DEFINITION_PATTERN = re.compile(
        r'^\*\*([^*]+)\*\*\s*[-–—:]\s*',
        re.MULTILINE
    )

    def verify(
        self,
        root: Path,
        glossary: Path | str | None = None,
        recursive: bool = True,
        extensions: set[str] | None = None,
        exclude: set[str] | None = None,
        no_default_excludes: bool = False,
        check_deprecated: bool = True,
        check_capitalization: bool = True,
        **options: Any
    ) -> VerificationResult:
        """Verify terminology consistency in files under root.

        Args:
            root: Directory to scan
            glossary: Path to glossary file (default: auto-detect docs/GLOSSARY.md)
            recursive: Whether to scan subdirectories
            extensions: File extensions to scan (default: .md, .conv, .txt)
            exclude: Additional patterns to exclude
            no_default_excludes: If True, don't apply default exclusions
            check_deprecated: Check for deprecated terms
            check_capitalization: Check capitalization consistency

        Returns:
            VerificationResult with terminology issues
        """
        root = Path(root)
        scan_ext = extensions or self.SCAN_EXTENSIONS

        # Build exclusion patterns for scan_files
        extra_excludes: set[str] = set()
        if exclude:
            extra_excludes.update(exclude)

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # Stats
        files_scanned = 0
        deprecated_found = 0
        capitalization_issues = 0

        # Load glossary if available
        glossary_terms = self._load_glossary(root, glossary)
        glossary_path = self._find_glossary(root, glossary)

        # Find files to scan (scan_files handles exclusion)
        all_files = scan_files(
            root,
            scan_ext,
            recursive=recursive,
            exclude_patterns=extra_excludes,
            no_default_excludes=no_default_excludes,
        )

        # Exclude glossary file itself
        files = [f for f in all_files if not (glossary_path and f == glossary_path)]

        for filepath in files:
            files_scanned += 1
            try:
                content = filepath.read_text(errors='replace')
            except Exception as e:
                warnings.append(VerificationError(
                    file=str(filepath),
                    line=None,
                    message=f"Could not read file: {e}",
                ))
                continue

            # Check each line, tracking code block state
            in_code_block = False
            for line_num, line in enumerate(content.split('\n'), 1):
                # Track fenced code blocks
                stripped = line.strip()
                if stripped.startswith('```'):
                    in_code_block = not in_code_block
                    continue

                # Skip content inside code blocks or indented code (4+ spaces)
                if in_code_block or line.startswith('    '):
                    continue

                # Check deprecated terms
                if check_deprecated:
                    for pattern, replacement in self.DEPRECATED_TERMS.items():
                        matches = list(re.finditer(pattern, line, re.IGNORECASE))
                        for match in matches:
                            deprecated_found += 1
                            errors.append(VerificationError(
                                file=str(self._rel_path(filepath, root)),
                                line=line_num,
                                message=f"Deprecated term '{match.group()}' - use '{replacement}' instead",
                                fix_hint=f"Replace '{match.group()}' with '{replacement}'",
                            ))

                # Check capitalization
                if check_capitalization:
                    for term_lower, correct_form in self.CAPITALIZATION_RULES.items():
                        # Find all case-insensitive matches
                        pattern = re.compile(r'\b' + re.escape(term_lower) + r'\b', re.IGNORECASE)
                        for match in pattern.finditer(line):
                            found = match.group()
                            # Skip if already correct or if it's a different word
                            if found == correct_form:
                                continue
                            # Skip code references (backticks)
                            if '`' in line:
                                # Check if this match is inside backticks
                                before = line[:match.start()]
                                if before.count('`') % 2 == 1:
                                    continue
                            # Don't flag sdqctl in ALL CAPS context (like headers)
                            if term_lower == 'sdqctl' and found == 'SDQCTL':
                                continue
                            # Skip copilot in CLI context (--adapter copilot, ADAPTER copilot)
                            if term_lower == 'copilot':
                                context = line[max(0, match.start()-15):match.end()+5]
                                if re.search(r'(--adapter|ADAPTER|adapter)\s+copilot', context, re.IGNORECASE):
                                    continue
                                # Skip ALL CAPS in env vars or config names like COPILOT_SDK
                                if found == 'COPILOT' and re.search(r'\bCOPILOT[_A-Z]', line):
                                    continue

                            capitalization_issues += 1
                            warnings.append(VerificationError(
                                file=str(self._rel_path(filepath, root)),
                                line=line_num,
                                message=f"Capitalization: '{found}' should be '{correct_form}'",
                                fix_hint=f"Replace '{found}' with '{correct_form}'",
                            ))

        # Build result
        passed = deprecated_found == 0  # Only deprecated terms cause failure

        if glossary_terms:
            glossary_info = f"glossary: {len(glossary_terms)} terms"
        else:
            glossary_info = "no glossary found"

        summary = (
            f"Scanned {files_scanned} file(s) ({glossary_info}): "
            f"{deprecated_found} deprecated, {capitalization_issues} capitalization"
        )

        return VerificationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            summary=summary,
            details={
                "files_scanned": files_scanned,
                "deprecated_terms": deprecated_found,
                "capitalization_issues": capitalization_issues,
                "glossary_terms": len(glossary_terms) if glossary_terms else 0,
                "glossary_path": str(glossary_path) if glossary_path else None,
            },
        )

    def _rel_path(self, filepath: Path, root: Path) -> Path:
        """Get relative path if possible."""
        try:
            return filepath.relative_to(root)
        except ValueError:
            return filepath

    def _find_glossary(self, root: Path, glossary: Path | str | None) -> Path | None:
        """Find glossary file.

        Resolution order:
        1. Explicit glossary parameter
        2. docs/GLOSSARY.md in root
        3. GLOSSARY.md in root
        """
        if glossary:
            path = Path(glossary)
            if path.exists():
                return path
            # Try relative to root
            rel_path = root / path
            if rel_path.exists():
                return rel_path
            return None

        # Auto-detect
        candidates = [
            root / 'docs' / 'GLOSSARY.md',
            root / 'GLOSSARY.md',
            root / 'docs' / 'glossary.md',
            root / 'glossary.md',
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _load_glossary(self, root: Path, glossary: Path | str | None) -> dict[str, str]:
        """Load glossary terms from file.

        Returns:
            Dict mapping term (lowercase) to original form
        """
        glossary_path = self._find_glossary(root, glossary)
        if not glossary_path:
            return {}

        try:
            content = glossary_path.read_text(errors='replace')
        except Exception:
            return {}

        terms: dict[str, str] = {}

        # Extract terms from headers (### Term Name)
        for match in self.GLOSSARY_TERM_PATTERN.finditer(content):
            term = match.group(1).strip()
            # Skip if it looks like a section title
            if term.lower() in {'core concepts', 'historical terms', 'disambiguation',
                               'workflow patterns', 'directives', 'execution modes',
                               'see also', 'conceptual overview'}:
                continue
            terms[term.lower()] = term

        # Extract terms from definition lists (**Term**: definition)
        for match in self.DEFINITION_PATTERN.finditer(content):
            term = match.group(1).strip()
            terms[term.lower()] = term

        return terms
