"""
sdqctl artifact - Artifact ID management utilities.

Generate next artifact ID, validate IDs, and manage artifact registries.
"""

from collections import defaultdict
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..core.artifact_ids import (
    CATEGORY_TYPES,
    ID_PATTERNS,
    find_all_references,
    find_definition_heading,
    get_next_id,
    mark_heading_retired,
    parse_type_and_category,
    replace_in_file,
    scan_existing_ids,
)

console = Console()


@click.group()
def artifact() -> None:
    """Artifact ID management utilities.

    Generate next artifact IDs, scan for existing artifacts, and manage
    artifact registries for traceability documentation.

    \b
    Artifact Types:
      STPA:    LOSS, HAZ, UCA, SC
      Reqs:    REQ, SPEC, TEST, GAP
      Dev:     BUG, PROP, Q, IQ

    \b
    Examples:
      sdqctl artifact next REQ              # → REQ-001 (or next available)
      sdqctl artifact next REQ-CGM          # → REQ-CGM-001 (category-scoped)
      sdqctl artifact next UCA-BOLUS        # → UCA-BOLUS-001
      sdqctl artifact list REQ              # List all REQ artifacts
    """
    pass


@artifact.command("next")
@click.argument("type_spec")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to scan for existing IDs")
@click.option("--no-scan", is_flag=True,
              help="Don't scan files, just output TYPE-001")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON")
def next_id(type_spec: str, path: str, no_scan: bool, as_json: bool) -> None:
    """Generate the next available artifact ID.

    TYPE_SPEC can be:
      - Simple type: REQ, UCA, SPEC, TEST, BUG, etc.
      - Category-scoped: REQ-CGM, UCA-BOLUS, GAP-SYNC, etc.

    \b
    Examples:
      sdqctl artifact next REQ
      sdqctl artifact next REQ-CGM
      sdqctl artifact next UCA-BOLUS --path traceability/
    """
    art_type, category = parse_type_and_category(type_spec)

    if art_type not in ID_PATTERNS:
        console.print(f"[red]Unknown artifact type: {art_type}[/red]")
        console.print(f"[dim]Valid types: {', '.join(sorted(ID_PATTERNS.keys()))}[/dim]")
        raise SystemExit(1)

    if category and art_type not in CATEGORY_TYPES:
        console.print(
            f"[yellow]Warning: {art_type} does not support categories, "
            f"ignoring '{category}'[/yellow]"
        )
        category = None

    if no_scan:
        existing: list[tuple[str, int]] = []
    else:
        existing = scan_existing_ids(Path(path), art_type, category)

    next_artifact_id = get_next_id(art_type, category, existing)

    if as_json:
        import json
        result = {
            "type": art_type,
            "category": category,
            "next_id": next_artifact_id,
            "existing_count": len(existing),
            "max_number": max((num for _, num in existing), default=0),
        }
        console.print(json.dumps(result))
    else:
        console.print(next_artifact_id)


@artifact.command("list")
@click.argument("type_spec", required=False)
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to scan")
@click.option("--all", "show_all", is_flag=True,
              help="Show all artifact types")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON")
def list_artifacts(type_spec: Optional[str], path: str, show_all: bool, as_json: bool) -> None:
    """List existing artifact IDs.

    \b
    Examples:
      sdqctl artifact list REQ              # List all REQ artifacts
      sdqctl artifact list UCA-BOLUS        # List UCA-BOLUS-* artifacts
      sdqctl artifact list --all            # List all artifact types
    """
    root = Path(path)

    if show_all or not type_spec:
        # Scan for all types
        all_artifacts: dict[str, list[tuple[str, int]]] = {}
        for art_type in ID_PATTERNS:
            found = scan_existing_ids(root, art_type, None)
            if found:
                all_artifacts[art_type] = found

        if as_json:
            import json
            result = {
                art_type: [
                    {"id": id_, "number": num}
                    for id_, num in sorted(ids, key=lambda x: x[1])
                ]
                for art_type, ids in all_artifacts.items()
            }
            console.print(json.dumps(result))
        else:
            if not all_artifacts:
                console.print("[dim]No artifacts found[/dim]")
                return

            table = Table(title="Artifact Summary")
            table.add_column("Type", style="cyan")
            table.add_column("Count", justify="right")
            table.add_column("Range", style="dim")

            for art_type in sorted(all_artifacts.keys()):
                ids = all_artifacts[art_type]
                nums = [num for _, num in ids]
                range_str = f"{min(nums):03d}-{max(nums):03d}" if nums else "-"
                table.add_row(art_type, str(len(ids)), range_str)

            console.print(table)
    else:
        art_type, category = parse_type_and_category(type_spec)

        if art_type not in ID_PATTERNS:
            console.print(f"[red]Unknown artifact type: {art_type}[/red]")
            raise SystemExit(1)

        found = scan_existing_ids(root, art_type, category)

        if as_json:
            import json
            result = {
                "type": art_type,
                "category": category,
                "artifacts": [
                    {"id": id_, "number": num}
                    for id_, num in sorted(found, key=lambda x: x[1])
                ],
            }
            console.print(json.dumps(result))
        else:
            if not found:
                console.print(f"[dim]No {type_spec} artifacts found[/dim]")
                return

            # Sort by number and display
            for id_, num in sorted(found, key=lambda x: x[1]):
                console.print(id_)


@artifact.command("rename")
@click.argument("old_id")
@click.argument("new_id")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to search for references")
@click.option("--dry-run", is_flag=True,
              help="Show what would be changed without making changes")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON")
def rename_artifact(old_id: str, new_id: str, path: str, dry_run: bool, as_json: bool) -> None:
    """Rename an artifact ID and update all references.

    Searches for all occurrences of OLD_ID and replaces them with NEW_ID.
    Use --dry-run to preview changes before applying.

    \b
    Examples:
      sdqctl artifact rename REQ-001 REQ-OVERRIDE-001
      sdqctl artifact rename UCA-003 UCA-BOLUS-003 --dry-run
      sdqctl artifact rename GAP-001 GAP-SYNC-001 --path traceability/
    """
    root = Path(path)

    # Find all references to the old ID
    references = find_all_references(root, old_id)

    if not references:
        if as_json:
            import json
            result = {
                "old_id": old_id, "new_id": new_id,
                "files_changed": 0, "references": 0
            }
            console.print(json.dumps(result))
        else:
            console.print(f"[yellow]No references to {old_id} found[/yellow]")
        return

    # Group references by file
    files_with_refs: dict[Path, list[tuple[int, str]]] = defaultdict(list)
    for filepath, line_num, line in references:
        files_with_refs[filepath].append((line_num, line))

    if dry_run:
        if as_json:
            import json
            result = {
                "old_id": old_id,
                "new_id": new_id,
                "dry_run": True,
                "files_affected": len(files_with_refs),
                "total_references": len(references),
                "files": [
                    {
                        "path": str(fp.relative_to(root) if fp.is_relative_to(root) else fp),
                        "references": [{"line": ln, "content": content} for ln, content in refs],
                    }
                    for fp, refs in sorted(files_with_refs.items())
                ],
            }
            console.print(json.dumps(result, indent=2))
        else:
            console.print(
                f"[bold]Dry run:[/bold] Would rename "
                f"[cyan]{old_id}[/cyan] → [green]{new_id}[/green]"
            )
            console.print(
                f"[dim]Found {len(references)} reference(s) "
                f"in {len(files_with_refs)} file(s):[/dim]\n"
            )

            for filepath in sorted(files_with_refs.keys()):
                refs = files_with_refs[filepath]
                rel_path = filepath.relative_to(root) if filepath.is_relative_to(root) else filepath
                console.print(f"[bold]{rel_path}[/bold] ({len(refs)} reference(s))")
                for line_num, line in refs:
                    # Show a preview with the ID highlighted
                    preview = line.strip()[:80]
                    if len(line.strip()) > 80:
                        preview += "..."
                    console.print(f"  L{line_num}: {preview}")
                console.print()
        return

    # Perform the rename
    total_replacements = 0
    files_changed: list[Path] = []

    for filepath in files_with_refs.keys():
        count = replace_in_file(filepath, old_id, new_id)
        if count > 0:
            total_replacements += count
            files_changed.append(filepath)

    if as_json:
        import json
        result = {
            "old_id": old_id,
            "new_id": new_id,
            "files_changed": len(files_changed),
            "total_replacements": total_replacements,
            "files": [
                str(fp.relative_to(root) if fp.is_relative_to(root) else fp)
                for fp in sorted(files_changed)
            ],
        }
        console.print(json.dumps(result, indent=2))
    else:
        console.print(f"[green]✓[/green] Renamed [cyan]{old_id}[/cyan] → [green]{new_id}[/green]")
        console.print(f"  {total_replacements} replacement(s) in {len(files_changed)} file(s):")
        for filepath in sorted(files_changed):
            rel_path = filepath.relative_to(root) if filepath.is_relative_to(root) else filepath
            console.print(f"    {rel_path}")


@artifact.command("retire")
@click.argument("artifact_id")
@click.option("--reason", "-r", required=True,
              help="Reason for retirement (e.g., 'Superseded by REQ-010')")
@click.option("--successor", "-s",
              help="Successor artifact ID (if replaced by another)")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to search for the artifact")
@click.option("--dry-run", is_flag=True,
              help="Show what would be changed without making changes")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON")
def retire_artifact(
    artifact_id: str,
    reason: str,
    successor: Optional[str],
    path: str,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Mark an artifact as retired with reason and optional successor.

    Finds the artifact's definition heading and marks it as [RETIRED],
    adding status metadata. Use this when an artifact is superseded or
    no longer applicable.

    \b
    Examples:
      sdqctl artifact retire REQ-003 --reason "Superseded by REQ-010"
      sdqctl artifact retire GAP-001 --reason "Fixed in v2.0" --successor REQ-020
      sdqctl artifact retire UCA-005 --reason "Obsolete design" --dry-run
    """
    from datetime import date

    root = Path(path)
    today = date.today().isoformat()

    # Find all files containing this artifact
    references = find_all_references(root, artifact_id)

    if not references:
        if as_json:
            import json
            console.print(json.dumps({
                "artifact_id": artifact_id,
                "status": "not_found",
                "error": f"No references to {artifact_id} found",
            }))
        else:
            console.print(f"[red]Error:[/red] No references to {artifact_id} found")
        raise SystemExit(1)

    # Find the definition heading
    definition_file: Optional[Path] = None
    definition_line: Optional[int] = None
    definition_heading: Optional[str] = None

    # Check each file for a heading definition
    for filepath, _, _ in references:
        result = find_definition_heading(filepath, artifact_id)
        if result:
            definition_file = filepath
            definition_line, definition_heading = result
            break

    if not definition_file or not definition_heading:
        # No heading found - report all references for manual review
        if as_json:
            import json
            console.print(json.dumps({
                "artifact_id": artifact_id,
                "status": "no_definition",
                "warning": f"No definition heading found for {artifact_id}",
                "references_found": len(references),
            }))
        else:
            console.print(
                f"[yellow]Warning:[/yellow] No definition heading found for {artifact_id}"
            )
            console.print(
                f"Found {len(references)} reference(s) but no heading "
                f"like '### {artifact_id}: ...'"
            )
            console.print("[dim]Consider adding a definition section manually[/dim]")
        raise SystemExit(1)

    # Build the retirement block
    retired_heading = mark_heading_retired(definition_heading)
    status_block = f"\n**Status:** RETIRED ({today})\n**Reason:** {reason}"
    if successor:
        status_block += f"\n**Successor:** {successor}"

    if dry_run:
        if as_json:
            import json
            def_file_rel = (
                definition_file.relative_to(root)
                if definition_file.is_relative_to(root)
                else definition_file
            )
            result = {
                "artifact_id": artifact_id,
                "dry_run": True,
                "definition_file": str(def_file_rel),
                "definition_line": definition_line,
                "original_heading": definition_heading,
                "retired_heading": retired_heading,
                "status_block": status_block.strip(),
                "reason": reason,
                "successor": successor,
                "date": today,
            }
            # Use print() instead of console.print() to avoid Rich markup interpretation
            print(json.dumps(result, indent=2))
        else:
            rel_path = (
                definition_file.relative_to(root)
                if definition_file.is_relative_to(root)
                else definition_file
            )
            console.print(f"[bold]Dry run:[/bold] Would retire [cyan]{artifact_id}[/cyan]")
            console.print(f"\n[dim]File:[/dim] {rel_path}:{definition_line}")
            console.print("\n[dim]Original heading:[/dim]")
            console.print(f"  {definition_heading}")
            console.print("\n[dim]Retired heading:[/dim]")
            console.print(f"  {retired_heading}")
            console.print("\n[dim]Status block to insert:[/dim]")
            for line in status_block.strip().split("\n"):
                console.print(f"  {line}")
        return

    # Apply the retirement
    try:
        content = definition_file.read_text(errors='replace')
    except Exception as e:
        console.print(f"[red]Error reading {definition_file}:[/red] {e}")
        raise SystemExit(1)

    lines = content.splitlines()

    # Find and replace the heading, then insert status block after
    modified_lines = []
    heading_found = False

    for i, line in enumerate(lines):
        if not heading_found and line == definition_heading:
            modified_lines.append(retired_heading)
            # Insert status block after heading
            for status_line in status_block.strip().split("\n"):
                modified_lines.append(status_line)
            heading_found = True
        else:
            modified_lines.append(line)

    if not heading_found:
        console.print("[red]Error:[/red] Could not find heading to modify")
        raise SystemExit(1)

    # Write the modified content
    try:
        definition_file.write_text("\n".join(modified_lines))
    except Exception as e:
        console.print(f"[red]Error writing {definition_file}:[/red] {e}")
        raise SystemExit(1)

    if as_json:
        import json
        file_rel = (
            definition_file.relative_to(root)
            if definition_file.is_relative_to(root)
            else definition_file
        )
        result = {
            "artifact_id": artifact_id,
            "status": "retired",
            "file": str(file_rel),
            "line": definition_line,
            "reason": reason,
            "successor": successor,
            "date": today,
        }
        console.print(json.dumps(result, indent=2))
    else:
        rel_path = (
            definition_file.relative_to(root)
            if definition_file.is_relative_to(root)
            else definition_file
        )
        console.print(f"[green]✓[/green] Retired [cyan]{artifact_id}[/cyan]")
        console.print(f"  File: {rel_path}:{definition_line}")
        console.print(f"  Reason: {reason}")
        if successor:
            console.print(f"  Successor: {successor}")
