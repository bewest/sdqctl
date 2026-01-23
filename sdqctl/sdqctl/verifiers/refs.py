"""
Reference verification - check that @-references resolve to files.

Scans markdown and code files for @-reference patterns and verifies
that the referenced files exist.
"""

import re
from pathlib import Path
from typing import Any

from .base import VerificationError, VerificationResult


class RefsVerifier:
    """Verify that @-references in files resolve to actual paths."""
    
    name = "refs"
    description = "Check that @-references resolve to files"
    
    # Pattern to match @-references: @path/to/file.ext or @./relative/path
    # Excludes common false positives like @param, @returns, email addresses
    REF_PATTERN = re.compile(
        r'@(\.?[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',
        re.MULTILINE
    )
    
    # File extensions to scan for references
    SCAN_EXTENSIONS = {'.md', '.conv', '.txt', '.yaml', '.yml'}
    
    # Patterns that look like refs but aren't
    FALSE_POSITIVE_PATTERNS = {
        '@param', '@returns', '@return', '@throws', '@type', '@typedef',
        '@property', '@example', '@see', '@since', '@deprecated',
        '@author', '@license', '@copyright', '@version',
    }
    
    def verify(
        self, 
        root: Path, 
        recursive: bool = True,
        extensions: set[str] | None = None,
        **options: Any
    ) -> VerificationResult:
        """Verify @-references in files under root.
        
        Args:
            root: Directory to scan
            recursive: Whether to scan subdirectories
            extensions: File extensions to scan (default: .md, .conv, .txt)
            
        Returns:
            VerificationResult with broken reference errors
        """
        root = Path(root)
        scan_ext = extensions or self.SCAN_EXTENSIONS
        
        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []
        
        # Stats
        files_scanned = 0
        refs_found = 0
        refs_valid = 0
        refs_broken = 0
        
        # Find files to scan
        if recursive:
            files = [f for f in root.rglob('*') if f.suffix in scan_ext and f.is_file()]
        else:
            files = [f for f in root.glob('*') if f.suffix in scan_ext and f.is_file()]
        
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
            
            # Find all @-references
            for line_num, line in enumerate(content.split('\n'), 1):
                for match in self.REF_PATTERN.finditer(line):
                    ref_path = match.group(1)
                    refs_found += 1
                    
                    # Skip false positives
                    full_match = f"@{ref_path}"
                    if any(full_match.startswith(fp) for fp in self.FALSE_POSITIVE_PATTERNS):
                        continue
                    
                    # Skip if looks like email
                    if '@' in line[:match.start()] and '.' in ref_path:
                        # Likely part of email - crude check
                        before = line[:match.start()]
                        if re.search(r'[a-zA-Z0-9._%+-]+$', before):
                            continue
                    
                    # Resolve reference path
                    # References are relative to the file containing them
                    if ref_path.startswith('./'):
                        resolved = filepath.parent / ref_path[2:]
                    elif ref_path.startswith('/'):
                        resolved = root / ref_path[1:]
                    else:
                        resolved = filepath.parent / ref_path
                    
                    # Check if file exists
                    if resolved.exists():
                        refs_valid += 1
                    else:
                        refs_broken += 1
                        errors.append(VerificationError(
                            file=str(filepath.relative_to(root) if filepath.is_relative_to(root) else filepath),
                            line=line_num,
                            message=f"Broken reference: @{ref_path}",
                            fix_hint=f"Create {resolved} or fix the reference",
                        ))
        
        # Build result
        passed = len(errors) == 0
        summary = (
            f"Scanned {files_scanned} file(s), found {refs_found} reference(s): "
            f"{refs_valid} valid, {refs_broken} broken"
        )
        
        return VerificationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            summary=summary,
            details={
                "files_scanned": files_scanned,
                "refs_found": refs_found,
                "refs_valid": refs_valid,
                "refs_broken": refs_broken,
            },
        )
