"""
sdqctl refcat - Extract file content with line-level precision.

Usage:
    sdqctl refcat @path/file.py#L10-L50
    sdqctl refcat @path/file.py#L10-L50 --json
    sdqctl refcat @path/file.py#L10 --no-line-numbers
    sdqctl refcat loop:path/file.swift#L100-L200

See proposals/REFCAT-DESIGN.md for full specification.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ..core.logging import get_logger
from ..core.refcat import (
    AliasNotFoundError,
    FileNotFoundError,
    InvalidRefError,
    PatternNotFoundError,
    RefcatConfig,
    RefcatError,
    extract_content,
    format_as_spec,
    format_for_context,
    format_for_json,
    parse_ref,
)

logger = get_logger(__name__)
console = Console()


def _load_workflow_context_patterns(workflow_path: Path) -> list[str]:
    """Load CONTEXT patterns from a workflow file."""
    patterns = []
    try:
        content = workflow_path.read_text()
        for line in content.split('\n'):
            line = line.strip()
            # Match CONTEXT and CONTEXT-OPTIONAL directives
            if line.startswith('CONTEXT ') or line.startswith('CONTEXT-OPTIONAL '):
                # Extract the pattern after the directive
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    patterns.append(parts[1])
    except Exception as e:
        logger.warning(f"Could not read workflow {workflow_path}: {e}")
    return patterns


def _expand_glob_patterns(refs: list[str], cwd: Path) -> list[str | Path]:
    """Expand glob patterns in refs to file paths.

    Returns a mix of:
    - Path objects for expanded glob matches
    - Original strings for refs with line numbers or aliases
    """
    import glob as glob_module

    expanded: list[str | Path] = []

    for ref in refs:
        # Strip @ prefix for processing
        clean_ref = ref[1:] if ref.startswith('@') else ref

        # Check if it's a glob pattern (contains * or ?)
        # But not if it has line numbers or alias prefix
        has_glob = '*' in clean_ref or '?' in clean_ref
        has_line_ref = '#' in clean_ref
        has_alias = ':' in clean_ref and not clean_ref.startswith('/')

        if has_glob and not has_line_ref and not has_alias:
            # Expand glob pattern
            pattern_path = cwd / clean_ref
            if '**' in str(pattern_path):
                matches = glob_module.glob(str(pattern_path), recursive=True)
            else:
                matches = glob_module.glob(str(pattern_path))

            for match in matches:
                match_path = Path(match)
                if match_path.is_file():
                    expanded.append(match_path)

            if not matches:
                # Keep original ref to generate error message
                expanded.append(ref)
        else:
            # Keep as-is (will be parsed by parse_ref)
            expanded.append(ref)

    return expanded


@click.command("refcat")
@click.argument("refs", nargs=-1, required=False)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output as JSON",
)
@click.option(
    "--no-line-numbers",
    is_flag=True,
    help="Don't prefix lines with line numbers",
)
@click.option(
    "--no-cwd",
    is_flag=True,
    help="Don't include CWD in header",
)
@click.option(
    "--absolute",
    is_flag=True,
    help="Show absolute paths instead of relative",
)
@click.option(
    "--relative-to",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Base directory for relative paths (default: CWD)",
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    help="Only output content, no headers or formatting",
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate refs exist, don't output content",
)
@click.option(
    "--from-workflow",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Extract refs from a workflow's CONTEXT patterns",
)
@click.option(
    "--list-files",
    is_flag=True,
    help="Only list matching files (for glob patterns)",
)
@click.option(
    "--no-attribution",
    is_flag=True,
    help="Don't show '## From:' header (keeps code fences)",
)
@click.option(
    "--spec",
    "spec_output",
    is_flag=True,
    help="Output normalized ref spec strings for round-tripping",
)
def refcat(
    refs: tuple[str, ...],
    json_output: bool,
    no_line_numbers: bool,
    no_cwd: bool,
    absolute: bool,
    relative_to: Optional[Path],
    quiet: bool,
    validate_only: bool,
    from_workflow: Optional[Path],
    list_files: bool,
    no_attribution: bool,
    spec_output: bool,
) -> None:
    """Extract file content with line-level precision.

    REFS are file references with optional line ranges, or glob patterns:

    \b
      @path/file.py              Entire file
      @path/file.py#L10          Single line 10
      @path/file.py#L10-L50      Lines 10 to 50
      @path/file.py#L10-         Line 10 to end of file
      @path/file.py#/pattern/    Find pattern (first match)
      alias:path/file.py#L10     With alias prefix
      @docs/**/*.md              Glob pattern (expands to matching files)

    Examples:

    \b
      # Extract specific lines
      sdqctl refcat @sdqctl/core/context.py#L182-L194

      # Multiple refs
      sdqctl refcat @file1.py#L10 @file2.py#L20-L30

      # Glob pattern - extract all matching files
      sdqctl refcat "@docs/*.md" --list-files

      # Extract all context from a workflow
      sdqctl refcat --from-workflow workflows/verify-refs.conv --list-files

      # JSON output for scripting
      sdqctl refcat @file.py#L10-L50 --json

      # Validate refs without output
      sdqctl refcat @file.py#L10-L50 --validate-only
    """
    cwd = relative_to or Path.cwd()

    # Build config
    config = RefcatConfig(
        show_line_numbers=not no_line_numbers,
        show_cwd=not no_cwd,
        show_attribution=not no_attribution,
        relative_paths=not absolute,
    )

    # Collect refs from various sources
    all_refs: list[str] = list(refs) if refs else []

    # Load refs from workflow if specified
    if from_workflow:
        workflow_refs = _load_workflow_context_patterns(from_workflow)
        all_refs.extend(workflow_refs)

    if not all_refs:
        console.print("[yellow]No refs provided. Use --from-workflow or provide REFS.[/yellow]")
        return

    # Expand glob patterns
    expanded_refs = _expand_glob_patterns(all_refs, cwd)

    # List files mode - just show what would be processed
    if list_files:
        if json_output:
            console.print_json(json.dumps({"files": [str(p) for p in expanded_refs]}))
        else:
            console.print(f"[bold]Files matching patterns ({len(expanded_refs)}):[/bold]")
            for item in expanded_refs:
                if isinstance(item, Path):
                    try:
                        rel_path = item.relative_to(cwd)
                    except ValueError:
                        rel_path = item
                    console.print(f"  {rel_path}")
                else:
                    console.print(f"  {item}")
        return

    # Process each ref
    results: list[dict] = []
    errors: list[str] = []

    for ref in expanded_refs:
        # Handle both Path objects (from glob) and strings (original refs)
        ref_str = f"@{ref}" if isinstance(ref, Path) else ref
        try:
            spec = parse_ref(ref_str)
            extracted = extract_content(spec, cwd)

            if validate_only:
                # Just validate, collect info
                results.append({
                    "ref": ref_str,
                    "valid": True,
                    "path": str(extracted.path),
                    "lines": f"{extracted.line_start}-{extracted.line_end}",
                })
            else:
                results.append({
                    "ref": ref_str,
                    "extracted": extracted,
                    "formatted": format_for_context(extracted, config),
                    "spec": format_as_spec(extracted, config),
                })

        except FileNotFoundError as e:
            errors.append(f"Error: {e}")
            if json_output:
                results.append({"ref": ref_str, "valid": False, "error": str(e)})
        except InvalidRefError as e:
            errors.append(f"Error: {e}")
            if json_output:
                results.append({"ref": ref_str, "valid": False, "error": str(e)})
        except PatternNotFoundError as e:
            errors.append(f"Error: {e}")
            if json_output:
                results.append({"ref": ref_str, "valid": False, "error": str(e)})
        except AliasNotFoundError as e:
            errors.append(f"Error: {e}")
            if json_output:
                results.append({"ref": ref_str, "valid": False, "error": str(e)})
        except RefcatError as e:
            errors.append(f"Error: {e}")
            if json_output:
                results.append({"ref": ref_str, "valid": False, "error": str(e)})

    # Output
    if json_output:
        if validate_only:
            output = {
                "refs": results,
                "valid": len(errors) == 0,
                "errors": errors,
            }
        else:
            output = {
                "refs": [
                    format_for_json(r["extracted"], include_spec=spec_output)
                    if "extracted" in r else r
                    for r in results
                ],
                "errors": errors,
            }
        console.print_json(json.dumps(output, indent=2))

    elif spec_output:
        # Spec mode: output normalized ref spec strings
        for r in results:
            if "spec" in r:
                print(r["spec"])

    elif validate_only:
        # Validation mode output
        for r in results:
            if r.get("valid"):
                console.print(f"[green]✓[/green] {r['ref']} → {r['path']} ({r['lines']})")
            else:
                console.print(f"[red]✗[/red] {r['ref']}: {r.get('error', 'unknown error')}")

        if errors:
            sys.exit(1)
        else:
            console.print(f"\n[green]All {len(results)} ref(s) valid[/green]")

    elif quiet:
        # Quiet mode: just content
        for r in results:
            if "extracted" in r:
                print(r["extracted"].content)

    else:
        # Normal mode: formatted markdown
        for i, r in enumerate(results):
            if "formatted" in r:
                if i > 0:
                    print()  # Separator between refs
                print(r["formatted"])

    # Print errors to stderr
    if errors and not json_output:
        err_console = Console(stderr=True)
        for e in errors:
            err_console.print(f"[red]{e}[/red]")
        sys.exit(1)


# Alias for CLI registration
command = refcat
