# REFCAT Design Specification

**Status**: Implemented  
**Created**: 2026-01-23  
**Updated**: 2026-01-24  
**Author**: sdqctl development  

## Overview

REFCAT (Reference Catalog) provides precise file content extraction with line-level granularity for AI context injection. It extends the existing `@path` syntax with line ranges, pattern matching, and cross-repository alias support.

## 1. Ref Syntax Specification

### 1.1 Basic Line Ranges (P0)

```
@path/file.py#L10-L50          # Lines 10 to 50 (inclusive)
@path/file.py#L10              # Single line 10
@path/file.py#L10-             # Line 10 to end of file
@path/file.py#L-50             # Start of file to line 50
```

**Grammar**:
```
ref         := '@' path ('#' selector)?
path        := relative_path | absolute_path
selector    := line_range | relative_range | pattern_spec
line_range  := 'L' start ('-' end)?
start       := INTEGER
end         := INTEGER | ''  (empty = EOF)
```

### 1.2 Relative Ranges (P1)

For extracting context around a cursor position or match:

```
@path/file.py#L50:-5..+10      # 5 lines before line 50, 10 lines after
@path/file.py#L50:-10..        # 10 lines before line 50 to EOF
@path/file.py#L50:..+20        # Line 50 to 20 lines after
```

**Use case**: Showing context around a specific line without knowing exact bounds.

### 1.3 Pattern-Based Extraction (P2)

```
@path/file.py#/def my_func/           # Find pattern, extract to next blank line
@path/file.py#/class Foo/:+50         # Pattern + next 50 lines
@path/file.py#/def.*/:function        # Pattern + semantic extraction (function body)
```

**Semantic extractors** (future):
- `:function` - Extract complete function/method
- `:class` - Extract complete class
- `:block` - Extract complete block (indentation-based)

### 1.4 Ecosystem Aliases (P1)

For cross-repository references in the Nightscout ecosystem:

```
loop:LoopKit/LoopAlgorithm/Sources/LoopAlgorithm.swift#L10-L50
aaps:app/src/main/java/info/nightscout/androidaps/MainActivity.kt#L100
trio:Trio/Sources/APS/FreeAPS.swift#L50-L100
crm:lib/server/treatments.js#L1-L50
```

**Alias resolution order**:

1. **Explicit aliases dict** - Passed programmatically
2. **workspace.lock.json** - Auto-detected in current or parent directories
3. **~/.sdqctl/aliases.yaml** - Global user configuration

#### workspace.lock.json Support

REFCAT automatically reads aliases from `workspace.lock.json` files (used by the Nightscout ecosystem alignment workspace):

```json
{
  "externals_dir": "externals",
  "repos": [
    {"alias": "loop", "name": "LoopWorkspace"},
    {"alias": "crm", "aliases": ["ns"], "name": "cgm-remote-monitor"},
    {"alias": "aaps", "name": "AndroidAPS"}
  ]
}
```

This enables seamless integration with multi-repo workspaces without manual alias configuration.

#### Global Aliases (~/.sdqctl/aliases.yaml)

For repos not in a workspace.lock.json:

```yaml
# ~/.sdqctl/aliases.yaml
aliases:
  loop: /home/user/src/LoopKit
  aaps: /home/user/src/AndroidAPS
  trio: /home/user/src/Trio
```

## 2. Context Injection Format

### 2.1 Enhanced Output Format

When REFCAT extracts content, it MUST include metadata for agent disambiguation:

```markdown
## From: sdqctl/core/context.py:182-194 (relative to /home/bewest/src/copilot-do-proposal/sdqctl)
```python
182 |     def get_context_content(self) -> str:
183 |         """Get formatted context content for inclusion in prompts."""
184 |         if not self.files:
185 |             return ""
186 | 
187 |         parts = ["## Context Files\n"]
188 |         for ctx_file in self.files:
189 |             try:
190 |                 rel_path = ctx_file.path.relative_to(self.base_path) if self.base_path else ctx_file.path
191 |             except ValueError:
192 |                 # File is not in base_path subtree, use absolute or name
193 |                 rel_path = ctx_file.path
194 |             parts.append(f"### {rel_path}\n```\n{ctx_file.content}\n```\n")
```
```

### 2.2 Format Components

| Component | Required | Example |
|-----------|----------|---------|
| Path | Yes | `sdqctl/core/context.py` |
| Line range | If partial | `:182-194` |
| CWD reference | Yes | `(relative to /home/...)` |
| Language hint | Yes | ` ```python ` |
| Line numbers | If partial | `182 | ` prefix |

### 2.3 Configuration Options

```python
@dataclass
class RefcatConfig:
    show_line_numbers: bool = True      # Prefix lines with numbers
    show_cwd: bool = True               # Include CWD in header
    show_attribution: bool = True       # Show "## From:" header
    relative_paths: bool = True         # Use relative vs absolute paths
    language_detect: bool = True        # Auto-detect language for highlighting
    context_lines: int = 0              # Extra lines before/after range
```

### 2.4 Output Formats

REFCAT supports multiple output formats controlled by CLI flags:

| Flag | Description | Example Output |
|------|-------------|----------------|
| (default) | Full markdown with attribution | `## From: path:10-20` + fenced code |
| `--no-attribution` | Markdown without header | Fenced code block only |
| `--quiet` | Raw content only | Plain text, no fences |
| `--spec` | Normalized ref spec | `@path/file.py#L10-L20` |
| `--json` | JSON structure | `{"refs": [...], "errors": []}` |
| `--json --spec` | JSON with spec field | Includes `"spec": "@path#L10-L20"` |

### 2.5 Round-Trip Format

The `--spec` flag outputs the normalized ref spec string, useful for:
- Validating that refs can be parsed and re-serialized
- Extracting refs from context for reuse
- Generating refs from extracted content

```bash
# Full file outputs without line range
$ sdqctl refcat @file.py --spec
@file.py

# Partial extraction includes line range
$ sdqctl refcat @file.py#L10-L20 --spec
@file.py#L10-L20
```

## 3. Error Handling

### 3.1 Fail-Fast Semantics

REFCAT uses **fail-fast** validation - broken refs are caught early, not at runtime.

| Condition | Validate Phase | Runtime Phase |
|-----------|----------------|---------------|
| File not found | ❌ Fail validation | ❌ Quit session |
| Lines out of range | ⚠️ Warning (clamp) | ⚠️ Clamp + note |
| Pattern not found | N/A | ❌ Quit session |
| Alias unknown | ❌ Fail validation | ❌ Quit session |
| Permission denied | ❌ Fail validation | ❌ Quit session |

### 3.2 Error Messages

```bash
# File not found
$ sdqctl validate workflow.conv
Error: REFCAT ref not found: @missing/file.py#L10-L50
  Searched: /home/user/project/missing/file.py
  
# Lines out of range (warning, not error)
$ sdqctl validate workflow.conv
Warning: REFCAT line range exceeds file bounds: @file.py#L1-L500
  File has 200 lines, will clamp to L1-L200

# Unknown alias
$ sdqctl validate workflow.conv
Error: Unknown REFCAT alias: 'foo' in foo:path/file.py#L10
  Known aliases: loop, aaps, trio
  Define in ~/.sdqctl/aliases.yaml or use ALIAS directive
```

### 3.3 Validation Integration

```bash
# Standard validation checks REFCAT refs
sdqctl validate workflow.conv

# Skip REFCAT validation for cross-repo workflows
sdqctl validate workflow.conv --allow-missing

# Validate only REFCAT refs
sdqctl verify refs workflow.conv
```

## 4. Implementation Architecture

### 4.1 Core Module: `sdqctl/core/refcat.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re

@dataclass
class RefSpec:
    """Parsed reference specification."""
    path: Path
    alias: Optional[str] = None       # None for @path, "loop" for loop:path
    line_start: Optional[int] = None  # 1-based start line
    line_end: Optional[int] = None    # 1-based end line (None = EOF)
    pattern: Optional[str] = None     # Regex pattern for search
    relative_before: int = 0          # Lines before anchor
    relative_after: int = 0           # Lines after anchor

@dataclass  
class ExtractedContent:
    """Result of content extraction."""
    path: Path
    content: str
    line_start: int
    line_end: int
    total_lines: int
    cwd: Path

def parse_ref(ref: str) -> RefSpec:
    """Parse ref string into components.
    
    Examples:
        @path/file.py           -> RefSpec(path=Path("path/file.py"))
        @path/file.py#L10-L50   -> RefSpec(path=..., line_start=10, line_end=50)
        loop:path/file.py#L10   -> RefSpec(path=..., alias="loop", line_start=10)
    """
    ...

def resolve_alias(alias: str, config_path: Optional[Path] = None) -> Path:
    """Resolve alias to base path."""
    ...

def extract_content(spec: RefSpec, cwd: Path) -> ExtractedContent:
    """Extract content according to spec."""
    ...

def format_for_context(extracted: ExtractedContent, config: RefcatConfig) -> str:
    """Format extracted content for context injection."""
    ...
```

### 4.2 CLI Command: `sdqctl/commands/refcat.py`

```bash
# Basic usage
sdqctl refcat @sdqctl/core/context.py#L182-L194

# JSON output for scripting
sdqctl refcat @file.py#L10-L50 --json

# Without line numbers
sdqctl refcat @file.py#L10-L50 --no-line-numbers

# Custom CWD reference
sdqctl refcat @file.py#L10-L50 --relative-to /custom/path

# Multiple refs
sdqctl refcat @file1.py#L10 @file2.py#L20-L30
```

### 4.3 Directive Integration

New `REFCAT` directive in workflow files:

```dockerfile
# Single ref
REFCAT @sdqctl/core/context.py#L182-L194

# Multiple refs
REFCAT @context.py#L182-L194 @renderer.py#L1-L50

# With alias
REFCAT loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

Processed during `render_workflow()`, integrated into context injection.

### 4.4 Integration with Existing Context System

Extend `ContextFile` dataclass:

```python
@dataclass
class ContextFile:
    path: Path
    content: str
    tokens_estimate: int
    # New fields for REFCAT
    line_start: Optional[int] = None  # 1-based, None = line 1
    line_end: Optional[int] = None    # 1-based, None = EOF
    is_partial: bool = False          # True if extracted via REFCAT
```

Modify `get_context_content()` to use enhanced format when `is_partial=True`.

## 5. Testing Requirements

### 5.1 Unit Tests

```python
class TestRefcatParsing:
    def test_basic_path(self): ...
    def test_line_range(self): ...
    def test_single_line(self): ...
    def test_open_range(self): ...
    def test_alias_path(self): ...
    def test_pattern_spec(self): ...
    def test_relative_range(self): ...

class TestRefcatExtraction:
    def test_extract_full_file(self): ...
    def test_extract_line_range(self): ...
    def test_clamp_to_bounds(self): ...
    def test_file_not_found(self): ...
    def test_pattern_match(self): ...

class TestRefcatFormat:
    def test_format_with_line_numbers(self): ...
    def test_format_with_cwd(self): ...
    def test_language_detection(self): ...
```

### 5.2 Integration Tests

```python
class TestRefcatDirective:
    def test_workflow_with_refcat(self): ...
    def test_validation_catches_missing(self): ...
    def test_render_includes_metadata(self): ...
```

## 6. Migration Path

### 6.1 Backward Compatibility

- Existing `@path` syntax continues to work (full file)
- `CONTEXT @path` unchanged
- REFCAT is additive, not breaking

### 6.2 Deprecation (None)

No deprecations required.

## 7. Future Enhancements

1. **Semantic extraction** (`:function`, `:class`) using tree-sitter
2. **Multiple pattern matches** (`@file.py#/pattern/g` for all matches)
3. **Diff-aware extraction** (extract changed lines from git diff)
4. **Remote refs** (`github:owner/repo@ref:path#L10-L50`)

---

## Appendix A: Regex Patterns

```python
# Pattern for parsing refs
REF_PATTERN = re.compile(r'''
    ^
    (?:(?P<alias>[a-zA-Z][a-zA-Z0-9_-]*):)?  # Optional alias:
    @?(?P<path>[^#]+)                          # Path (@ optional)
    (?:\#
        (?:
            L(?P<start>\d+)(?:-(?P<end>\d+)?)?  # Line range
            |
            /(?P<pattern>[^/]+)/                # Pattern
        )
        (?::(?P<relative>[+-]?\d+\.\.[+-]?\d+))?  # Relative range
    )?
    $
''', re.VERBOSE)
```

## Appendix B: Language Detection

```python
EXTENSION_TO_LANGUAGE = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.java': 'java',
    '.rs': 'rust',
    '.go': 'go',
    '.rb': 'ruby',
    '.sh': 'bash',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.md': 'markdown',
    '.conv': 'dockerfile',
}
```
