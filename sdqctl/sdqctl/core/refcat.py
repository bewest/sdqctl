"""
REFCAT - Reference Catalog for precise file content extraction.

Provides line-level granularity for AI context injection with:
- Line ranges: @path/file.py#L10-L50
- Single lines: @path/file.py#L10
- Alias resolution: loop:path/file.swift#L10-L50
- Pattern search: @path/file.py#/regex/ (future)

See proposals/REFCAT-DESIGN.md for full specification.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Extension to language mapping for syntax highlighting
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".swift": "swift",
    ".kt": "kotlin",
    ".java": "java",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".sh": "bash",
    ".bash": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".conv": "dockerfile",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".xml": "xml",
    ".toml": "toml",
}


@dataclass
class RefSpec:
    """Parsed reference specification."""

    path: Path
    alias: Optional[str] = None  # None for @path, "loop" for loop:path
    line_start: Optional[int] = None  # 1-based start line
    line_end: Optional[int] = None  # 1-based end line (None = EOF or same as start)
    pattern: Optional[str] = None  # Regex pattern for search
    relative_before: int = 0  # Lines before anchor
    relative_after: int = 0  # Lines after anchor
    raw: str = ""  # Original ref string


@dataclass
class ExtractedContent:
    """Result of content extraction."""

    path: Path
    content: str
    lines: list[str]  # Individual lines
    line_start: int  # 1-based
    line_end: int  # 1-based
    total_lines: int  # Total lines in file
    cwd: Path
    was_clamped: bool = False  # True if range was clamped to file bounds


@dataclass
class RefcatConfig:
    """Configuration for REFCAT output formatting."""

    show_line_numbers: bool = True
    show_cwd: bool = True
    show_attribution: bool = True  # Show "## From:" header
    relative_paths: bool = True
    language_detect: bool = True
    line_number_width: int = 0  # 0 = auto-detect


class RefcatError(Exception):
    """Base exception for REFCAT errors."""

    pass


class FileNotFoundError(RefcatError):
    """Referenced file does not exist."""

    pass


class InvalidRefError(RefcatError):
    """Reference string could not be parsed."""

    pass


class PatternNotFoundError(RefcatError):
    """Pattern did not match any content."""

    pass


class AliasNotFoundError(RefcatError):
    """Alias is not defined."""

    pass


# Regex pattern for parsing refs
# Matches: [alias:][@]path[#Lstart[-end]] or [alias:][@]path[#/pattern/]
REF_PATTERN = re.compile(
    r"""
    ^
    (?:(?P<alias>[a-zA-Z][a-zA-Z0-9_-]*):)?  # Optional alias:
    @?(?P<path>[^#\s]+)                       # Path (@ optional)
    (?:\#
        (?:
            L(?P<start>\d+)(?:-(?:L?(?P<end>\d+))?)?  # Line range: L10, L10-L50, L10-
            |
            /(?P<pattern>[^/]+)/                      # Pattern: /regex/
        )
        (?::(?P<rel_before>[+-]?\d+)\.\.(?P<rel_after>[+-]?\d+))?  # Relative: :-5..+10
    )?
    $
""",
    re.VERBOSE,
)


def parse_ref(ref: str) -> RefSpec:
    """Parse ref string into components.

    Args:
        ref: Reference string like "@path/file.py#L10-L50"

    Returns:
        RefSpec with parsed components

    Raises:
        InvalidRefError: If ref cannot be parsed

    Examples:
        >>> parse_ref("@path/file.py")
        RefSpec(path=Path("path/file.py"))

        >>> parse_ref("@path/file.py#L10-L50")
        RefSpec(path=Path("path/file.py"), line_start=10, line_end=50)

        >>> parse_ref("loop:path/file.swift#L10")
        RefSpec(path=Path("path/file.swift"), alias="loop", line_start=10)
    """
    ref = ref.strip()
    match = REF_PATTERN.match(ref)

    if not match:
        raise InvalidRefError(f"Cannot parse ref: {ref}")

    groups = match.groupdict()

    # Parse line numbers
    line_start = int(groups["start"]) if groups.get("start") else None
    line_end = int(groups["end"]) if groups.get("end") else None

    # If only start specified (e.g., L10), end = start (single line)
    # If range specified with no end (e.g., L10-), end = None (to EOF)
    if line_start is not None and line_end is None:
        # Check if it was L10- (open range) or just L10 (single line)
        if "#L" in ref and "-" in ref.split("#")[1]:
            line_end = None  # Open range to EOF
        else:
            line_end = line_start  # Single line

    # Parse relative range
    rel_before = int(groups["rel_before"]) if groups.get("rel_before") else 0
    rel_after = int(groups["rel_after"]) if groups.get("rel_after") else 0

    return RefSpec(
        path=Path(groups["path"]),
        alias=groups.get("alias"),
        line_start=line_start,
        line_end=line_end,
        pattern=groups.get("pattern"),
        relative_before=abs(rel_before),  # Normalize to positive
        relative_after=abs(rel_after),
        raw=ref,
    )


def is_glob_pattern(ref: str) -> bool:
    """Check if a ref contains glob wildcards.
    
    Args:
        ref: Reference string like "@path/**/*.py"
        
    Returns:
        True if ref contains glob wildcards (* or ?)
    """
    # Strip @ prefix
    clean = ref[1:] if ref.startswith("@") else ref
    
    # Check for wildcards, but not in line ranges or aliases
    has_glob = "*" in clean or "?" in clean
    has_line_ref = "#" in clean
    has_alias = ":" in clean and not clean.startswith("/")
    
    return has_glob and not has_line_ref and not has_alias


def expand_glob_refs(refs: list[str], cwd: Path) -> list[str]:
    """Expand glob patterns in refs to individual file refs.
    
    Takes refs like "@src/**/*.py" and expands them to individual file refs.
    Non-glob refs are passed through unchanged.
    
    Args:
        refs: List of reference strings
        cwd: Base directory for glob expansion
        
    Returns:
        List of expanded refs (glob patterns replaced with matched files)
        
    Example:
        >>> expand_glob_refs(["@src/**/*.py"], Path("/project"))
        ["@src/main.py", "@src/utils/helper.py"]
    """
    import glob as glob_module
    
    expanded: list[str] = []
    
    for ref in refs:
        if not is_glob_pattern(ref):
            # Not a glob, keep as-is
            expanded.append(ref)
            continue
            
        # Strip @ prefix for globbing
        clean_ref = ref[1:] if ref.startswith("@") else ref
        pattern_path = cwd / clean_ref
        
        # Use recursive glob for ** patterns
        if "**" in str(pattern_path):
            matches = glob_module.glob(str(pattern_path), recursive=True)
        else:
            matches = glob_module.glob(str(pattern_path))
        
        # Add each match as a ref
        for match in sorted(matches):  # Sort for deterministic order
            match_path = Path(match)
            if match_path.is_file():
                # Make relative to cwd if possible
                try:
                    rel_path = match_path.relative_to(cwd)
                    expanded.append(f"@{rel_path}")
                except ValueError:
                    # Not relative to cwd, use absolute
                    expanded.append(f"@{match_path}")
        
        # If no matches, keep original to generate a meaningful error later
        if not any(Path(m).is_file() for m in matches):
            expanded.append(ref)
    
    return expanded


def resolve_alias(
    alias: str,
    aliases: Optional[dict[str, Path]] = None,
    cwd: Optional[Path] = None
) -> Path:
    """Resolve alias to base path.

    Args:
        alias: Alias name (e.g., "loop", "aaps")
        aliases: Dictionary mapping aliases to paths
        cwd: Current working directory for workspace.lock.json lookup

    Returns:
        Base path for the alias

    Raises:
        AliasNotFoundError: If alias is not defined

    Resolution order:
        1. Explicit aliases dict passed in
        2. workspace.lock.json in cwd or parent directories
        3. ~/.sdqctl/aliases.yaml global config
    """
    if aliases and alias in aliases:
        return aliases[alias]

    # Try workspace.lock.json (supports Nightscout ecosystem format)
    workspace_alias = _resolve_workspace_alias(alias, cwd or Path.cwd())
    if workspace_alias:
        return workspace_alias

    # Try loading from ~/.sdqctl/aliases.yaml
    config_path = Path.home() / ".sdqctl" / "aliases.yaml"
    if config_path.exists():
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config and "aliases" in config and alias in config["aliases"]:
                    return Path(config["aliases"][alias])
        except Exception:
            pass

    raise AliasNotFoundError(
        f"Unknown alias: '{alias}'. Define in workspace.lock.json or ~/.sdqctl/aliases.yaml"
    )


def _resolve_workspace_alias(alias: str, start_dir: Path) -> Optional[Path]:
    """Try to resolve alias from workspace.lock.json.

    Searches for workspace.lock.json in start_dir and parent directories.
    Supports the Nightscout ecosystem format:

    {
        "externals_dir": "externals",
        "repos": [
            {"alias": "loop", "name": "LoopWorkspace", ...},
            {"alias": "crm", "aliases": ["ns"], "name": "cgm-remote-monitor", ...}
        ]
    }
    """
    import json

    # Walk up directory tree looking for workspace.lock.json
    current = start_dir.resolve()
    for _ in range(10):  # Max 10 levels up
        lockfile = current / "workspace.lock.json"
        if lockfile.exists():
            try:
                with open(lockfile) as f:
                    data = json.load(f)

                externals_dir = data.get("externals_dir", "externals")

                for repo in data.get("repos", []):
                    # Check primary alias
                    if repo.get("alias") == alias:
                        return current / externals_dir / repo["name"]
                    # Check additional aliases
                    if alias in repo.get("aliases", []):
                        return current / externals_dir / repo["name"]
                    # Check repo name as fallback
                    if repo.get("name") == alias:
                        return current / externals_dir / repo["name"]

                # Found lockfile but alias not in it
                return None

            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def resolve_path(spec: RefSpec, cwd: Path, aliases: Optional[dict[str, Path]] = None) -> Path:
    """Resolve RefSpec path to absolute path.

    Resolution order:
    1. If alias, resolve alias then join path
    2. If absolute, use directly
    3. Try CWD first
    4. Fall back to cwd parameter

    Args:
        spec: Parsed RefSpec
        cwd: Current working directory
        aliases: Optional alias mappings

    Returns:
        Resolved absolute path

    Raises:
        FileNotFoundError: If file cannot be found
    """
    path = spec.path

    # Handle alias
    if spec.alias:
        base = resolve_alias(spec.alias, aliases, cwd)
        full_path = base / path
        if full_path.exists():
            return full_path.resolve()
        raise FileNotFoundError(f"File not found: {spec.raw} (resolved to {full_path})")

    # Absolute path
    if path.is_absolute():
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"File not found: {path}")

    # Try CWD first
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path.resolve()

    # Try provided cwd
    base_path = cwd / path
    if base_path.exists():
        return base_path.resolve()

    raise FileNotFoundError(
        f"File not found: {spec.raw}\n  Tried: {cwd_path}\n  Tried: {base_path}"
    )


def extract_content(
    spec: RefSpec,
    cwd: Path,
    aliases: Optional[dict[str, Path]] = None,
) -> ExtractedContent:
    """Extract content according to spec.

    Args:
        spec: Parsed RefSpec
        cwd: Current working directory for resolution
        aliases: Optional alias mappings

    Returns:
        ExtractedContent with extracted lines

    Raises:
        FileNotFoundError: If file not found
        PatternNotFoundError: If pattern doesn't match
    """
    # Resolve path
    resolved_path = resolve_path(spec, cwd, aliases)

    # Read file
    content = resolved_path.read_text()
    all_lines = content.splitlines()
    total_lines = len(all_lines)

    # Default: entire file
    line_start = 1
    line_end = total_lines
    was_clamped = False

    # Handle pattern search
    if spec.pattern:
        pattern = re.compile(spec.pattern)
        for i, line in enumerate(all_lines, 1):
            if pattern.search(line):
                line_start = i
                line_end = i  # Default: just the matching line
                break
        else:
            raise PatternNotFoundError(
                f"Pattern /{spec.pattern}/ not found in {resolved_path}"
            )

    # Handle line range
    elif spec.line_start is not None:
        line_start = spec.line_start
        line_end = spec.line_end if spec.line_end is not None else total_lines

    # Apply relative range adjustments
    if spec.relative_before or spec.relative_after:
        line_start = max(1, line_start - spec.relative_before)
        line_end = min(total_lines, line_end + spec.relative_after)

    # Clamp to file bounds
    if line_start < 1:
        line_start = 1
        was_clamped = True
    if line_end > total_lines:
        line_end = total_lines
        was_clamped = True
    if line_start > total_lines:
        line_start = total_lines
        was_clamped = True

    # Extract lines (convert to 0-based indexing)
    extracted_lines = all_lines[line_start - 1 : line_end]
    extracted_content = "\n".join(extracted_lines)

    return ExtractedContent(
        path=resolved_path,
        content=extracted_content,
        lines=extracted_lines,
        line_start=line_start,
        line_end=line_end,
        total_lines=total_lines,
        cwd=cwd,
        was_clamped=was_clamped,
    )


def detect_language(path: Path) -> str:
    """Detect language from file extension for syntax highlighting."""
    suffix = path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix, suffix.lstrip(".") or "text")


def format_for_context(
    extracted: ExtractedContent,
    config: Optional[RefcatConfig] = None,
) -> str:
    """Format extracted content for context injection.

    Produces output like:
    ```
    ## From: path/file.py:10-50 (relative to /home/user/project)
    ```python
    10 | def example():
    11 |     ...
    ```
    ```

    Args:
        extracted: Extracted content
        config: Formatting configuration

    Returns:
        Formatted markdown string
    """
    if config is None:
        config = RefcatConfig()

    # Determine path display
    try:
        if config.relative_paths:
            display_path = extracted.path.relative_to(extracted.cwd)
        else:
            display_path = extracted.path
    except ValueError:
        display_path = extracted.path

    # Build header
    is_partial = extracted.line_start != 1 or extracted.line_end != extracted.total_lines
    if is_partial:
        header = f"## From: {display_path}:{extracted.line_start}-{extracted.line_end}"
    else:
        header = f"## From: {display_path}"

    if config.show_cwd:
        header += f" (relative to {extracted.cwd})"

    # Detect language
    lang = detect_language(extracted.path) if config.language_detect else ""

    # Format content with line numbers
    if config.show_line_numbers and is_partial:
        # Calculate line number width
        width = config.line_number_width
        if width == 0:
            width = len(str(extracted.line_end))

        numbered_lines = []
        for i, line in enumerate(extracted.lines, extracted.line_start):
            numbered_lines.append(f"{i:>{width}} | {line}")
        content = "\n".join(numbered_lines)
    else:
        content = extracted.content

    # Build output
    if config.show_attribution:
        return f"{header}\n```{lang}\n{content}\n```"
    else:
        return f"```{lang}\n{content}\n```"


def format_as_spec(extracted: ExtractedContent, config: Optional[RefcatConfig] = None) -> str:
    """Format extracted content as a normalized ref spec string.

    Produces output like:
        @path/file.py#L10-L50

    Args:
        extracted: Extracted content
        config: Formatting configuration

    Returns:
        Normalized ref spec string
    """
    if config is None:
        config = RefcatConfig()

    # Determine path display
    try:
        if config.relative_paths:
            display_path = extracted.path.relative_to(extracted.cwd)
        else:
            display_path = extracted.path
    except ValueError:
        display_path = extracted.path

    # Build spec string
    is_full_file = extracted.line_start == 1 and extracted.line_end == extracted.total_lines
    if is_full_file:
        return f"@{display_path}"
    else:
        return f"@{display_path}#L{extracted.line_start}-L{extracted.line_end}"


def format_for_json(extracted: ExtractedContent, include_spec: bool = False) -> dict:
    """Format extracted content as JSON-serializable dict."""
    result = {
        "path": str(extracted.path),
        "line_start": extracted.line_start,
        "line_end": extracted.line_end,
        "total_lines": extracted.total_lines,
        "cwd": str(extracted.cwd),
        "was_clamped": extracted.was_clamped,
        "content": extracted.content,
        "lines": extracted.lines,
    }
    if include_spec:
        result["spec"] = format_as_spec(extracted)
    return result


def extract_ref(
    ref: str,
    cwd: Optional[Path] = None,
    aliases: Optional[dict[str, Path]] = None,
    config: Optional[RefcatConfig] = None,
) -> str:
    """High-level API: parse, extract, and format a ref.

    Args:
        ref: Reference string like "@path/file.py#L10-L50"
        cwd: Current working directory (default: Path.cwd())
        aliases: Optional alias mappings
        config: Formatting configuration

    Returns:
        Formatted markdown string

    Example:
        >>> print(extract_ref("@sdqctl/core/context.py#L182-L194"))
        ## From: sdqctl/core/context.py:182-194 (relative to /home/...)
        ```python
        182 |     def get_context_content(self) -> str:
        ...
        ```
    """
    if cwd is None:
        cwd = Path.cwd()

    spec = parse_ref(ref)
    extracted = extract_content(spec, cwd, aliases)
    return format_for_context(extracted, config)
