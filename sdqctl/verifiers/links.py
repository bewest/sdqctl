"""
Link verification - check that URLs and file links are reachable.

Scans markdown files for link patterns and verifies that file links
resolve to existing files.
"""

import re
from pathlib import Path
from typing import Any

from .base import VerificationError, VerificationResult, scan_files


class LinksVerifier:
    """Verify that markdown links resolve to existing files."""

    name = "links"
    description = "Check that markdown links resolve to files"

    # Pattern to match markdown links: [text](url)
    LINK_PATTERN = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

    # Pattern to match reference-style links: [text][ref] with [ref]: url
    REF_LINK_DEF = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)', re.MULTILINE)

    # Pattern to match code blocks start/end
    CODE_BLOCK_PATTERN = re.compile(r'^```')

    # Pattern to strip inline code from a line before checking links
    INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')

    # File extensions to scan
    SCAN_EXTENSIONS = {'.md', '.markdown', '.txt'}

    def verify(
        self,
        root: Path,
        recursive: bool = True,
        check_urls: bool = False,
        extensions: set[str] | None = None,
        **options: Any
    ) -> VerificationResult:
        """Verify links in markdown files.

        Args:
            root: Directory to scan
            recursive: Whether to scan subdirectories
            check_urls: Whether to verify external URLs (not implemented)
            extensions: File extensions to scan

        Returns:
            VerificationResult with broken link errors
        """
        root = Path(root)
        scan_ext = extensions or self.SCAN_EXTENSIONS

        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []

        # Stats
        files_scanned = 0
        links_found = 0
        links_valid = 0
        links_broken = 0
        links_external = 0

        # Find files to scan
        files = scan_files(root, scan_ext, recursive=recursive)

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

            # Build reference link definitions map
            ref_defs = {}
            for match in self.REF_LINK_DEF.finditer(content):
                ref_name = match.group(1).lower()
                ref_url = match.group(2)
                ref_defs[ref_name] = ref_url

            # Find all inline links, tracking code block state
            in_code_block = False
            for line_num, line in enumerate(content.split('\n'), 1):
                # Track code block state
                if self.CODE_BLOCK_PATTERN.match(line):
                    in_code_block = not in_code_block
                    continue

                # Skip lines inside code blocks
                if in_code_block:
                    continue

                # Strip inline code before checking for links
                line_stripped = self.INLINE_CODE_PATTERN.sub('', line)

                for match in self.LINK_PATTERN.finditer(line_stripped):
                    text, url = match.groups()
                    links_found += 1

                    # Handle reference-style links [text][ref]
                    if url.startswith('[') and url.endswith(']'):
                        ref_name = url[1:-1].lower() or text.lower()
                        url = ref_defs.get(ref_name, url)

                    # Skip external URLs
                    if url.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
                        links_external += 1
                        if check_urls:
                            warnings.append(VerificationError(
                                file=str(self._relative_path(filepath, root)),
                                line=line_num,
                                message=f"External URL not verified: {url}",
                            ))
                        continue

                    # Skip anchors-only links
                    if url.startswith('#'):
                        links_valid += 1
                        continue

                    # Skip data: URIs
                    if url.startswith('data:'):
                        links_valid += 1
                        continue

                    # Extract path (remove anchor and query)
                    path_part = url.split('#')[0].split('?')[0]

                    # Skip empty paths (anchor links to same file)
                    if not path_part:
                        links_valid += 1
                        continue

                    # Resolve path
                    if path_part.startswith('/'):
                        # Absolute from root
                        resolved = root / path_part[1:]
                    else:
                        # Relative to file
                        resolved = filepath.parent / path_part

                    # Normalize path
                    try:
                        resolved = resolved.resolve()
                    except Exception:
                        pass  # Keep as-is if resolve fails

                    # Check if file exists
                    if resolved.exists():
                        links_valid += 1
                    else:
                        links_broken += 1
                        errors.append(VerificationError(
                            file=str(self._relative_path(filepath, root)),
                            line=line_num,
                            message=f"Broken link: [{text}]({url})",
                            fix_hint=f"Create {path_part} or update link",
                        ))

        # Build result
        passed = len(errors) == 0
        summary = (
            f"Scanned {files_scanned} file(s), found {links_found} link(s): "
            f"{links_valid} valid, {links_broken} broken, {links_external} external"
        )

        return VerificationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            summary=summary,
            details={
                "files_scanned": files_scanned,
                "links_found": links_found,
                "links_valid": links_valid,
                "links_broken": links_broken,
                "links_external": links_external,
            },
        )

    def _relative_path(self, path: Path, root: Path) -> Path:
        """Get path relative to root, or absolute if not under root."""
        try:
            return path.relative_to(root)
        except ValueError:
            return path
