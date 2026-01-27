"""
Artifact ID utilities for scanning and generating artifact identifiers.

This module is separate from commands/artifact.py to:
1. Allow core modules to access ID patterns without importing commands
2. Enable reuse by verifiers/traceability.py
3. Reduce artifact.py to focused CLI handlers
"""

import re
from pathlib import Path
from typing import Optional

# Artifact ID patterns for various documentation types
ID_PATTERNS = {
    # STPA safety artifacts
    "LOSS": re.compile(r'\b(LOSS-(\d{3}))\b'),
    "HAZ": re.compile(r'\b(HAZ-(\d{3}))\b'),
    "UCA": re.compile(r'\b(UCA-([A-Z0-9]+)-(\d{3})|UCA-(\d{3}))\b'),
    "SC": re.compile(r'\b(SC-([A-Z0-9]+)-(\d{3})([a-z])?|SC-(\d{3})([a-z])?)\b'),
    # Requirements/specifications
    "REQ": re.compile(r'\b(REQ-([A-Z0-9]+)-(\d{3})|REQ-(\d{3}))\b'),
    "SPEC": re.compile(r'\b(SPEC-([A-Z0-9]+)-(\d{3})|SPEC-(\d{3}))\b'),
    "TEST": re.compile(r'\b(TEST-([A-Z0-9]+)-(\d{3})|TEST-(\d{3}))\b'),
    "GAP": re.compile(r'\b(GAP-([A-Z0-9]+)-(\d{3})|GAP-(\d{3}))\b'),
    # Development artifacts
    "BUG": re.compile(r'\b(BUG-(\d{3}))\b'),
    "PROP": re.compile(r'\b(PROP-(\d{3}))\b'),
    "Q": re.compile(r'\b(Q-(\d{3}))\b'),
    "IQ": re.compile(r'\b(IQ-(\d+))\b'),
}

# File extensions to scan for artifact IDs
SCAN_EXTENSIONS = {'.md', '.markdown', '.yaml', '.yml', '.txt', '.conv'}

# Types that support category prefixes (e.g., REQ-CGM-001)
CATEGORY_TYPES = {"UCA", "SC", "REQ", "SPEC", "TEST", "GAP"}


def parse_type_and_category(type_spec: str) -> tuple[str, Optional[str]]:
    """Parse type specification like 'REQ' or 'REQ-CGM' into (type, category)."""
    parts = type_spec.upper().split("-", 1)
    art_type = parts[0]
    category = parts[1] if len(parts) > 1 else None
    return art_type, category


def scan_existing_ids(
    root: Path,
    art_type: str,
    category: Optional[str] = None,
    recursive: bool = True,
) -> list[tuple[str, int]]:
    """Scan files for existing artifact IDs of a given type.

    Returns list of (full_id, number) tuples.
    """
    if art_type not in ID_PATTERNS:
        return []

    pattern = ID_PATTERNS[art_type]
    found_ids: list[tuple[str, int]] = []

    # Find files to scan
    if recursive:
        files = [f for f in root.rglob('*') if f.suffix in SCAN_EXTENSIONS and f.is_file()]
    else:
        files = [f for f in root.glob('*') if f.suffix in SCAN_EXTENSIONS and f.is_file()]

    for filepath in files:
        try:
            content = filepath.read_text(errors='replace')
        except Exception:
            continue

        for match in pattern.finditer(content):
            full_id = match.group(1)

            # Extract the numeric portion
            # Handle both simple (REQ-001) and category (REQ-CGM-001) formats
            if art_type in CATEGORY_TYPES:
                # Category types have complex patterns
                if category:
                    # Only include IDs with matching category
                    if f"-{category}-" in full_id.upper():
                        # Extract number from the category pattern
                        num_match = re.search(rf'-{category}-(\d+)', full_id, re.IGNORECASE)
                        if num_match:
                            found_ids.append((full_id, int(num_match.group(1))))
                else:
                    # Include all IDs of this type (simple format)
                    num_match = re.search(r'-(\d+)$', full_id)
                    if num_match:
                        found_ids.append((full_id, int(num_match.group(1))))
            else:
                # Simple types: LOSS-001, BUG-001, etc.
                num_match = re.search(r'-(\d+)$', full_id)
                if num_match:
                    found_ids.append((full_id, int(num_match.group(1))))

    return found_ids


def get_next_id(
    art_type: str,
    category: Optional[str],
    existing_ids: list[tuple[str, int]],
) -> str:
    """Generate the next available artifact ID."""
    if existing_ids:
        max_num = max(num for _, num in existing_ids)
        next_num = max_num + 1
    else:
        next_num = 1

    # Format the ID
    if category and art_type in CATEGORY_TYPES:
        return f"{art_type}-{category}-{next_num:03d}"
    else:
        return f"{art_type}-{next_num:03d}"


def find_all_references(
    root: Path,
    artifact_id: str,
    recursive: bool = True,
) -> list[tuple[Path, int, str]]:
    """Find all references to an artifact ID in files.

    Returns list of (filepath, line_number, line_content) tuples.
    """
    references: list[tuple[Path, int, str]] = []

    # Build a pattern that matches the exact ID with word boundaries
    pattern = re.compile(rf'\b{re.escape(artifact_id)}\b')

    # Find files to scan
    if recursive:
        files = [f for f in root.rglob('*') if f.suffix in SCAN_EXTENSIONS and f.is_file()]
    else:
        files = [f for f in root.glob('*') if f.suffix in SCAN_EXTENSIONS and f.is_file()]

    for filepath in files:
        try:
            lines = filepath.read_text(errors='replace').splitlines()
        except Exception:
            continue

        for line_num, line in enumerate(lines, start=1):
            if pattern.search(line):
                references.append((filepath, line_num, line))

    return references


def replace_in_file(filepath: Path, old_id: str, new_id: str) -> int:
    """Replace all occurrences of old_id with new_id in a file.

    Returns the number of replacements made.
    """
    pattern = re.compile(rf'\b{re.escape(old_id)}\b')

    try:
        content = filepath.read_text(errors='replace')
    except Exception:
        return 0

    new_content, count = pattern.subn(new_id, content)

    if count > 0:
        filepath.write_text(new_content)

    return count


def find_definition_heading(filepath: Path, artifact_id: str) -> Optional[tuple[int, str]]:
    """Find the definition heading for an artifact ID.

    Looks for patterns like:
      ### REQ-001: Some Title
      ## UCA-BOLUS-003: Description

    Returns (line_number, full_heading_text) or None if not found.
    """
    pattern = re.compile(rf'^(#+\s+{re.escape(artifact_id)}[:\s].*)$', re.MULTILINE)

    try:
        content = filepath.read_text(errors='replace')
    except Exception:
        return None

    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        if pattern.match(line):
            return (line_num, line)

    return None


def mark_heading_retired(heading: str) -> str:
    """Add [RETIRED] suffix to a heading if not already present."""
    if "[RETIRED]" in heading:
        return heading  # Already marked

    # Insert [RETIRED] after the artifact ID
    # Pattern: ### REQ-001: Title -> ### REQ-001: [RETIRED] Title
    #          ### REQ-001 -> ### REQ-001 [RETIRED]
    parts = heading.split(":", 1)
    if len(parts) == 2:
        return f"{parts[0]}: [RETIRED]{parts[1]}"
    else:
        return f"{heading} [RETIRED]"
