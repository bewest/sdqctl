"""
Reference verification - check that @-references and alias:refs resolve to files.

Scans markdown and code files for reference patterns and verifies
that the referenced files exist. Uses the refcat module for resolution
to support workspace.lock.json aliases.

Supported reference formats:
- @path/to/file.ext       (standard @-reference)
- @./relative/path.md     (relative @-reference)
- alias:path/file.ext     (workspace alias reference, e.g., loop:Loop/README.md)
- alias:path#L10-L50      (with line range - line range is ignored for validation)
"""

import re
from pathlib import Path
from typing import Any, Optional

from .base import VerificationError, VerificationResult


class RefsVerifier:
    """Verify that @-references and alias:refs resolve to actual paths.
    
    Uses the refcat module for path resolution, supporting:
    - Standard @-references relative to containing file
    - Workspace aliases from workspace.lock.json
    """
    
    name = "refs"
    description = "Check that @-references and alias:refs resolve to files"
    
    # Pattern to match @-references: @path/to/file.ext or @./relative/path
    # Excludes common false positives like @param, @returns, email addresses
    AT_REF_PATTERN = re.compile(
        r'@(\.?[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',
        re.MULTILINE
    )
    
    # Pattern to match alias:path references (e.g., loop:Loop/README.md)
    # Supports optional line range suffix (#L10 or #L10-L50)
    ALIAS_REF_PATTERN = re.compile(
        r'\b([a-zA-Z][a-zA-Z0-9_-]*):([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)(?:#[^\s]*)?',
        re.MULTILINE
    )
    
    # File extensions to scan for references
    SCAN_EXTENSIONS = {'.md', '.conv', '.txt', '.yaml', '.yml'}
    
    # Patterns that look like refs but aren't (JSDoc, decorators, etc.)
    FALSE_POSITIVE_PATTERNS = {
        # JSDoc annotations
        '@param', '@returns', '@return', '@throws', '@type', '@typedef',
        '@property', '@example', '@see', '@since', '@deprecated',
        '@author', '@license', '@copyright', '@version',
        # Python/Click decorators
        '@click', '@app', '@pytest', '@fixture', '@override',
        '@staticmethod', '@classmethod', '@abstractmethod',
        '@dataclass', '@property', '@cached',
        # Other common patterns
        '@verify', '@test', '@before', '@after',
    }
    
    # Patterns that match version pins like @v4.4.3 or @2.4.0
    VERSION_PATTERN = re.compile(r'^v?\d+(\.\d+)*$')
    
    # Common prefixes that look like alias:path but aren't
    ALIAS_FALSE_POSITIVES = {
        'http', 'https', 'ftp', 'mailto', 'file', 'data',  # URLs
        'ref', 'refs', 'see', 'type', 'class', 'enum',      # Common prose
        'caregiver',  # App-specific URL schemes
    }
    
    def verify(
        self, 
        root: Path, 
        recursive: bool = True,
        extensions: set[str] | None = None,
        **options: Any
    ) -> VerificationResult:
        """Verify @-references and alias:refs in files under root.
        
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
        alias_refs_found = 0
        alias_refs_valid = 0
        alias_refs_broken = 0
        
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
            
            # Process each line
            for line_num, line in enumerate(content.split('\n'), 1):
                # Check @-references
                at_errors, at_valid, at_total = self._check_at_refs(
                    line, line_num, filepath, root
                )
                errors.extend(at_errors)
                refs_found += at_total
                refs_valid += at_valid
                refs_broken += (at_total - at_valid)
                
                # Check alias:path references
                alias_errors, alias_valid, alias_total = self._check_alias_refs(
                    line, line_num, filepath, root
                )
                errors.extend(alias_errors)
                alias_refs_found += alias_total
                alias_refs_valid += alias_valid
                alias_refs_broken += (alias_total - alias_valid)
        
        # Build result
        total_refs = refs_found + alias_refs_found
        total_valid = refs_valid + alias_refs_valid
        total_broken = refs_broken + alias_refs_broken
        passed = total_broken == 0
        
        summary = (
            f"Scanned {files_scanned} file(s), found {total_refs} reference(s): "
            f"{total_valid} valid, {total_broken} broken"
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
                "alias_refs_found": alias_refs_found,
                "alias_refs_valid": alias_refs_valid,
                "alias_refs_broken": alias_refs_broken,
            },
        )
    
    def _check_at_refs(
        self, 
        line: str, 
        line_num: int, 
        filepath: Path, 
        root: Path
    ) -> tuple[list[VerificationError], int, int]:
        """Check @-references in a line.
        
        Resolution order:
        1. Explicit relative (./path) - resolve from file's directory
        2. Explicit absolute (/path) - resolve from root
        3. Try workspace root first, then fall back to file-relative
        
        Returns:
            Tuple of (errors, valid_count, total_count)
        """
        errors: list[VerificationError] = []
        valid_count = 0
        total_count = 0
        
        for match in self.AT_REF_PATTERN.finditer(line):
            ref_path = match.group(1)
            
            # Skip false positives (decorators, JSDoc, etc.)
            full_match = f"@{ref_path}"
            if any(full_match.startswith(fp) for fp in self.FALSE_POSITIVE_PATTERNS):
                continue
            
            # Skip version pins like @v4.4.3 or @2.4.0
            if self.VERSION_PATTERN.match(ref_path):
                continue
            
            # Skip if looks like email (text before @ looks like email local part)
            if '@' in line[:match.start()] and '.' in ref_path:
                before = line[:match.start()]
                if re.search(r'[a-zA-Z0-9._%+-]+$', before):
                    continue
            
            # Skip if looks like domain name (common TLDs at end)
            if re.match(r'^[a-zA-Z0-9.-]+\.(com|org|net|io|de|be|co|uk)$', ref_path):
                continue
            
            total_count += 1
            
            # Resolve reference path with fallback strategy
            resolved = None
            if ref_path.startswith('./'):
                # Explicit relative - resolve from file's directory
                resolved = filepath.parent / ref_path[2:]
            elif ref_path.startswith('/'):
                # Explicit absolute - resolve from root
                resolved = root / ref_path[1:]
            else:
                # Try workspace root first (common convention for project refs)
                root_resolved = root / ref_path
                if root_resolved.exists():
                    resolved = root_resolved
                else:
                    # Fall back to file-relative
                    resolved = filepath.parent / ref_path
            
            # Check if file exists
            if resolved.exists():
                valid_count += 1
            else:
                errors.append(VerificationError(
                    file=str(filepath.relative_to(root) if filepath.is_relative_to(root) else filepath),
                    line=line_num,
                    message=f"Broken reference: @{ref_path}",
                    fix_hint=f"Create {resolved} or fix the reference",
                ))
        
        return errors, valid_count, total_count
    
    def _check_alias_refs(
        self,
        line: str,
        line_num: int,
        filepath: Path,
        root: Path
    ) -> tuple[list[VerificationError], int, int]:
        """Check alias:path references in a line.
        
        Uses refcat module for alias resolution from workspace.lock.json.
        
        Returns:
            Tuple of (errors, valid_count, total_count)
        """
        errors: list[VerificationError] = []
        valid_count = 0
        total_count = 0
        
        for match in self.ALIAS_REF_PATTERN.finditer(line):
            alias = match.group(1)
            ref_path = match.group(2)
            full_ref = f"{alias}:{ref_path}"
            
            # Skip URL schemes and common false positives
            if alias.lower() in self.ALIAS_FALSE_POSITIVES:
                continue
            
            # Skip ellipsis paths (display shorthand like Sources/.../File.swift)
            if '...' in ref_path or '…' in ref_path:
                continue
            
            total_count += 1
            
            # Use refcat for resolution
            resolved = self._resolve_alias_ref(alias, ref_path, root)
            
            if resolved and resolved.exists():
                valid_count += 1
            else:
                # Provide helpful error message
                if resolved:
                    hint = f"Expected at {resolved}"
                else:
                    hint = f"Unknown alias '{alias}' - check workspace.lock.json"
                
                errors.append(VerificationError(
                    file=str(filepath.relative_to(root) if filepath.is_relative_to(root) else filepath),
                    line=line_num,
                    message=f"Broken alias reference: {full_ref}",
                    fix_hint=hint,
                ))
        
        return errors, valid_count, total_count
    
    def _resolve_alias_ref(
        self,
        alias: str,
        ref_path: str,
        root: Path
    ) -> Optional[Path]:
        """Resolve alias:path using refcat module.
        
        Falls back to None if alias cannot be resolved.
        """
        try:
            from ..core.refcat import RefSpec, resolve_path
            
            spec = RefSpec(path=Path(ref_path), alias=alias)
            return resolve_path(spec, root)
        except Exception:
            # Alias not found or other error
            return None
