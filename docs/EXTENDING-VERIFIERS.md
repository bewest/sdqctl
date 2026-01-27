# Extending sdqctl Verifiers

> **Status**: Stable  
> **Related**: [VERIFICATION-DIRECTIVES.md](../proposals/VERIFICATION-DIRECTIVES.md), [QUIRKS.md](./QUIRKS.md)

---

## Overview

sdqctl's verification system provides a plugin architecture for static checks. Verifiers can be invoked:

1. **Via CLI**: `sdqctl verify refs`
2. **In workflows**: `VERIFY refs` directive
3. **Programmatically**: `RefsVerifier().verify(path)`

This guide explains how to create new verifiers.

---

## Architecture

```
sdqctl/verifiers/
├── __init__.py      # VERIFIERS registry
├── base.py          # Protocol and result types
└── refs.py          # Reference checker (example)
```

**Key types:**

| Type | Purpose |
|------|---------|
| `Verifier` | Protocol (interface) for all verifiers |
| `VerificationResult` | Pass/fail status with errors, warnings, details |
| `VerificationError` | Single error with file, line, message, fix hint |
| `VERIFIERS` | Registry dict mapping name → class |
| `scan_files` | Utility for file discovery with exclusion handling |

---

## Utility: scan_files

The `scan_files()` utility consolidates common file scanning logic:

```python
from pathlib import Path
from sdqctl.verifiers.base import scan_files

# Basic usage
files = scan_files(Path("docs"), {".md", ".rst"}, recursive=True)

# With exclusion options
files = scan_files(
    root=Path("."),
    extensions={".py", ".md"},
    recursive=True,
    exclude_patterns={"examples"},    # Additional patterns
    no_default_excludes=False,        # Respect DEFAULT_EXCLUDES
)
```

**Default excludes:** `.venv`, `venv`, `node_modules`, `__pycache__`, `.git`, etc.

**Also respects:** `.sdqctlignore` file in root directory.

---

## Step 1: Create Verifier Class

Create `sdqctl/verifiers/links.py`:

```python
"""
Link verification - check that URLs and file links are reachable.
"""

from pathlib import Path
from typing import Any
import re

from .base import VerificationError, VerificationResult, scan_files


class LinksVerifier:
    """Verify that URLs and file links are valid."""
    
    name = "links"
    description = "Check that URLs and file links are reachable"
    
    # Pattern to match markdown links: [text](url)
    LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    
    SCAN_EXTENSIONS = {".md"}  # Define supported extensions
    
    def verify(
        self,
        root: Path,
        check_urls: bool = False,  # Optional: HTTP HEAD requests
        recursive: bool = True,
        **options: Any
    ) -> VerificationResult:
        """Verify links in markdown files.
        
        Args:
            root: Directory to scan
            check_urls: Whether to verify external URLs (slow)
            recursive: Scan subdirectories
            
        Returns:
            VerificationResult with broken link errors
        """
        root = Path(root)
        errors: list[VerificationError] = []
        warnings: list[VerificationError] = []
        
        files_scanned = 0
        links_found = 0
        links_broken = 0
        
        # Use scan_files for consistent exclusion handling
        for filepath in scan_files(root, self.SCAN_EXTENSIONS, recursive=recursive):
            files_scanned += 1
            content = filepath.read_text(errors='replace')
            
            for line_num, line in enumerate(content.split('\n'), 1):
                for match in self.LINK_PATTERN.finditer(line):
                    text, url = match.groups()
                    links_found += 1
                    
                    # Skip external URLs unless check_urls is True
                    if url.startswith(('http://', 'https://')):
                        if not check_urls:
                            continue
                        # TODO: Implement HTTP HEAD check
                        continue
                    
                    # Skip anchors
                    if url.startswith('#'):
                        continue
                    
                    # Resolve relative path
                    if url.startswith('/'):
                        resolved = root / url[1:]
                    else:
                        resolved = filepath.parent / url.split('#')[0]
                    
                    if not resolved.exists():
                        links_broken += 1
                        errors.append(VerificationError(
                            file=str(filepath.relative_to(root)),
                            line=line_num,
                            message=f"Broken link: [{text}]({url})",
                            fix_hint=f"Create {resolved} or update link",
                        ))
        
        return VerificationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            summary=f"Scanned {files_scanned} files, {links_found} links, {links_broken} broken",
            details={
                "files_scanned": files_scanned,
                "links_found": links_found,
                "links_broken": links_broken,
            },
        )
```

---

## Step 2: Register the Verifier

Edit `sdqctl/verifiers/__init__.py`:

```python
from .base import VerificationError, VerificationResult, Verifier
from .refs import RefsVerifier
from .links import LinksVerifier  # Add import

# Registry of available verifiers
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
    "links": LinksVerifier,  # Add to registry
}

__all__ = [
    "VerificationError",
    "VerificationResult",
    "Verifier",
    "RefsVerifier",
    "LinksVerifier",  # Add to exports
    "VERIFIERS",
]
```

That's it! The verifier is now available via CLI and `VERIFY` directive.

---

## Step 3: Add Tests

Create `tests/test_verifiers_links.py`:

```python
import pytest
from pathlib import Path

from sdqctl.verifiers.links import LinksVerifier


class TestLinksVerifier:
    """Tests for LinksVerifier."""
    
    def test_valid_link(self, tmp_path: Path):
        """Valid markdown links pass verification."""
        # Create target file
        (tmp_path / "target.md").write_text("# Target")
        
        # Create file with valid link
        (tmp_path / "doc.md").write_text(
            "Check out [the target](target.md)."
        )
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed
        assert len(result.errors) == 0
    
    def test_broken_link(self, tmp_path: Path):
        """Broken links are detected."""
        (tmp_path / "doc.md").write_text(
            "Check out [missing](nonexistent.md)."
        )
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert not result.passed
        assert len(result.errors) == 1
        assert "Broken link" in result.errors[0].message
    
    def test_external_urls_skipped_by_default(self, tmp_path: Path):
        """External URLs are not checked by default."""
        (tmp_path / "doc.md").write_text(
            "See [GitHub](https://github.com/example/nonexistent)."
        )
        
        verifier = LinksVerifier()
        result = verifier.verify(tmp_path)
        
        assert result.passed  # External URL not checked
```

---

## API Reference

### VerificationResult

```python
@dataclass
class VerificationResult:
    passed: bool                          # Overall pass/fail
    errors: list[VerificationError]       # Blocking issues
    warnings: list[VerificationError]     # Non-blocking issues
    summary: str                          # One-line summary
    details: dict                         # Arbitrary metadata
    
    def to_markdown(self) -> str: ...     # For VERIFY-OUTPUT
    def to_json(self) -> dict: ...        # For --json output
```

### VerificationError

```python
@dataclass
class VerificationError:
    file: str           # Relative file path
    line: int | None    # Line number (1-based) or None
    message: str        # Error description
    fix_hint: str | None  # Suggested fix (optional)
```

### Verifier Protocol

```python
class Verifier(Protocol):
    name: str           # CLI identifier (e.g., "refs", "links")
    description: str    # One-line description
    
    def verify(self, root: Path, **options: Any) -> VerificationResult:
        """Run verification from root directory."""
        ...
```

---

## Usage

### CLI

```bash
# Verify @-references and alias:refs
sdqctl verify refs

# With JSON output
sdqctl verify links --json

# Specific directory
sdqctl verify links -p examples/
```

### Reference Resolution

The `refs` verifier supports multiple reference types with intelligent resolution:

**@-References:**
- `@path/file.md` - Tries workspace root first, falls back to file-relative
- `@./relative/path.md` - Always resolves relative to containing file
- `@/absolute/path.md` - Always resolves from workspace root

**Alias References:**
- `loop:Loop/README.md` - Resolves using `workspace.lock.json` aliases
- `crm:lib/server.js#L10-L50` - Supports line ranges (file existence validated)

**False Positives Excluded:**
- Python decorators: `@click.option`, `@app.command`
- JSDoc annotations: `@param`, `@returns`, `@example`
- Version pins: `@v4.4.3`, `@2.4.0`
- Email domains: `@gmail.com`, `@example.org`, `@school.edu` (case-insensitive)
- URL schemes: `https://`, `mailto:`
- Ellipsis paths: `Sources/.../File.swift` (display-only shorthand)
- Placeholder aliases: `project:`, `extract:`, `alias:` (example refs in docs)
- Placeholder paths: `loop:path/to/file.swift` (example refs in templates)
- Connection strings: `localhost:port`, `mongo:`, `redis:` (database URIs)
- Unix socket paths: `sock:/var/run/docker.sock`, `unix:/tmp/mysql.sock`
- Timestamp formats: `mm:ss.SSS`, `HH:mm:ss` (date format patterns)

**How Path Detection Works:**

The verifier skips `alias:path` patterns when:
1. The alias is in `ALIAS_FALSE_POSITIVES` (e.g., `http`, `mongo`, `sock`, `mm`, `path`)
2. The path starts with `/` (absolute paths like Unix sockets)
3. The path contains `...` or `…` (ellipsis shorthand)
4. The path starts with `path/to/` (placeholder examples)

### Future: Custom `ref://` Scheme

For stricter validation, consider adopting a custom URL scheme:

```markdown
# Unambiguous reference that can't conflict with other URL schemes
See [implementation](ref://loop/Loop/Models/Override.swift#L10-L50)

# Or with sdq:// prefix
`sdq://trio:Trio/Sources/Network/API.swift`
```

**Benefits:**
- Zero false positives (custom scheme is unambiguous)
- Clickable in editors with custom URI handlers
- Clear intent - this IS a traceable reference

**Trade-offs:**
- Requires migration of existing refs
- More verbose than `alias:path`
- Editor support varies

This is documented as a future option; current implementation uses heuristic exclusions.

### Roadmap: Eliminating False Positives

The `verify refs` command has evolved through several iterations to reduce false positives:

| Version | Broken Refs | False Positives Eliminated |
|---------|-------------|----------------------------|
| Initial | 502 | - |
| +Root-first resolution | 297 | 205 (workspace @refs) |
| +TLD exclusions | 271 | 26 (emails, domains) |
| +Connection strings | 259 | 12 (localhost:, mongo:) |
| +Unix sockets | 258 | 1 (sock:, unix:) |
| +Timestamps & placeholders | 251 | 7 (mm:ss, path/to/) |
| +Doc path/to fixes | 249 | 2 (replaced antipattern) |

**Current state (2026-01-24):** 249 remaining broken refs are **real documentation issues** (short-form refs needing full paths).

**Remaining work for zero false positives:**

1. **Short-form resolution** (Feature Request)
   - Pattern: `trio:Preferences.swift` → `trio:**/Preferences.swift`
   - Status: Not implemented - requires fuzzy file search
   - Workaround: Use full paths in documentation

2. **Whitelist-only mode** (Future)
   - Only validate refs with aliases in `workspace.lock.json`
   - Eliminates unknown alias false positives
   - Trade-off: Won't catch refs to undefined aliases

3. **Custom `ref://` scheme** (Proposal)
   - Unambiguous: `ref://trio/Trio/Sources/Models/Preferences.swift`
   - Zero false positives by design
   - Trade-off: Migration effort, more verbose

**Current recommendation:** Use full paths from repo root:
```markdown
# ✅ Validates correctly
`trio:Trio/Sources/Models/Preferences.swift#L22`

# ❌ Won't validate (short-form)
`trio:Preferences.swift`
```

### Triage Workflow

When verifying a workspace with many broken refs, use `--suggest-fixes` to find correct paths:

```bash
# Verify and suggest fixes for moved files
sdqctl verify refs --suggest-fixes -v

# JSON output for scripting
sdqctl verify refs --suggest-fixes --json > refs-triage.json
```

**Error Classification:**

| Hint | Meaning | Action |
|------|---------|--------|
| `Expected at /path/...` | Alias known, file doesn't exist | File moved - check suggestion |
| `Unknown alias 'X'` | Alias not in workspace.lock.json | Add alias or fix typo |
| `Suggestion: Found: path` | Actual file location found | Update ref to use correct path |

### In Workflows

```dockerfile
# Check links during workflow
VERIFY links

# Control error handling
VERIFY-ON-ERROR continue
VERIFY links

# Only inject output on failure
VERIFY-OUTPUT on-error
VERIFY links

# Combine with ELIDE to fix issues
VERIFY links
ELIDE
PROMPT Fix any broken links found above.
```

### Programmatic

```python
from pathlib import Path
from sdqctl.verifiers import LinksVerifier

verifier = LinksVerifier()
result = verifier.verify(Path("."), check_urls=True)

if not result.passed:
    print(result.to_markdown())
```

---

## Best Practices

### 1. Use Relative Paths in Errors

```python
# Good: relative to root
VerificationError(
    file=str(filepath.relative_to(root)),
    ...
)

# Bad: absolute paths leak system info
VerificationError(
    file=str(filepath),  # /home/user/project/...
    ...
)
```

### 2. Provide Fix Hints

```python
VerificationError(
    message="Broken reference: @lib/missing.js",
    fix_hint="Create lib/missing.js or update the reference",
)
```

### 3. Separate Errors vs Warnings

- **Errors**: Cause `passed=False`, block workflow if `VERIFY-ON-ERROR stop`
- **Warnings**: Informational, don't block

### 4. Include Statistics in Details

```python
VerificationResult(
    details={
        "files_scanned": 42,
        "issues_found": 3,
        "check_duration_ms": 150,
    }
)
```

### 5. Handle Read Errors Gracefully

```python
try:
    content = filepath.read_text(errors='replace')
except Exception as e:
    warnings.append(VerificationError(
        file=str(filepath),
        line=None,
        message=f"Could not read file: {e}",
    ))
    continue
```

---

## Example Verifiers to Consider

| Verifier | Purpose | Use Case |
|----------|---------|----------|
| `traceability` | REQ→SPEC→TEST traces | STPA safety analysis |
| `terminology` | Consistent term usage | Documentation quality |
| `assertions` | Boolean condition checks | CI gates |
| `secrets` | Credential detection | Security audit |
| `dependencies` | Import/require validation | Build health |

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Verifier extension points and base classes
- [PLUGIN-AUTHORING.md](PLUGIN-AUTHORING.md) - External plugin development guide
- [proposals/VERIFICATION-DIRECTIVES.md](../proposals/VERIFICATION-DIRECTIVES.md) - Original proposal
- [proposals/STPA-INTEGRATION.md](../proposals/STPA-INTEGRATION.md) - Traceability use cases
- [README.md](../README.md#verify-directive-in-workflow-verification) - VERIFY directive usage
