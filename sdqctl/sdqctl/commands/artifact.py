"""
sdqctl artifact - Artifact ID management utilities.

Generate next artifact ID, validate IDs, and manage artifact registries.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

# Reuse patterns from traceability verifier
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

# File extensions to scan
SCAN_EXTENSIONS = {'.md', '.markdown', '.yaml', '.yml', '.txt', '.conv'}

# Types that support categories
CATEGORY_TYPES = {"UCA", "SC", "REQ", "SPEC", "TEST", "GAP"}

console = Console()


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
                groups = match.groups()
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
        console.print(f"[yellow]Warning: {art_type} does not support categories, ignoring '{category}'[/yellow]")
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
                art_type: [{"id": id_, "number": num} for id_, num in sorted(ids, key=lambda x: x[1])]
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
                "artifacts": [{"id": id_, "number": num} for id_, num in sorted(found, key=lambda x: x[1])],
            }
            console.print(json.dumps(result))
        else:
            if not found:
                console.print(f"[dim]No {type_spec} artifacts found[/dim]")
                return
            
            # Sort by number and display
            for id_, num in sorted(found, key=lambda x: x[1]):
                console.print(id_)
