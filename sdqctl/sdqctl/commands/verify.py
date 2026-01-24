"""
sdqctl verify - Static verification commands.

Usage:
    sdqctl verify refs [--json] [--verbose]
    sdqctl verify all [--json]
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ..verifiers import VERIFIERS, VerificationResult

console = Console()


@click.group("verify")
def verify():
    """Static verification suite."""
    pass


@verify.command("refs")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", 
              help="Directory to verify")
@click.option("--suggest-fixes", is_flag=True, 
              help="Search for correct paths for broken refs")
def verify_refs(json_output: bool, verbose: bool, path: str, suggest_fixes: bool):
    """Verify that @-references and alias:refs resolve to files.
    
    Scans markdown and workflow files for references and validates
    that the referenced files exist.
    
    \b
    Supported reference formats:
      @path/to/file.md         Standard @-reference
      alias:path/file.swift    Workspace alias (from workspace.lock.json)
      loop:Loop/README.md      Example alias reference
    
    \b
    Examples:
      sdqctl verify refs                    # Verify current directory
      sdqctl verify refs -p docs/           # Verify specific directory
      sdqctl verify refs --json             # JSON output for CI
      sdqctl verify refs --suggest-fixes    # Search for correct paths
    """
    verifier = VERIFIERS["refs"]()
    result = verifier.verify(Path(path))
    
    if suggest_fixes and result.errors:
        result = _add_fix_suggestions(result, Path(path))
    
    _output_result(result, json_output, verbose, "refs")


@verify.command("all")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
def verify_all(json_output: bool, verbose: bool, path: str):
    """Run all verifications."""
    results = {}
    all_passed = True
    
    for name, verifier_cls in VERIFIERS.items():
        verifier = verifier_cls()
        result = verifier.verify(Path(path))
        results[name] = result
        if not result.passed:
            all_passed = False
    
    if json_output:
        output = {
            "passed": all_passed,
            "verifications": {name: r.to_json() for name, r in results.items()},
        }
        console.print_json(json.dumps(output))
    else:
        for name, result in results.items():
            status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
            console.print(f"{status} {name}: {result.summary}")
            
            if verbose and (result.errors or result.warnings):
                for err in result.errors:
                    console.print(f"  [red]ERROR[/red] {err.file}:{err.line}: {err.message}")
                for warn in result.warnings:
                    console.print(f"  [yellow]WARN[/yellow] {warn.file}:{warn.line}: {warn.message}")
        
        # Summary
        console.print()
        if all_passed:
            console.print("[green]All verifications passed[/green]")
        else:
            console.print("[red]Some verifications failed[/red]")
    
    # Exit code
    raise SystemExit(0 if all_passed else 1)


def _output_result(result: VerificationResult, json_output: bool, verbose: bool, name: str):
    """Output verification result in requested format."""
    if json_output:
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ PASSED[/green]" if result.passed else "[red]✗ FAILED[/red]"
        console.print(f"{status}: {result.summary}")
        
        if verbose or not result.passed:
            for err in result.errors:
                loc = f"{err.file}:{err.line}" if err.line else err.file
                console.print(f"  [red]ERROR[/red] {loc}: {err.message}")
                if err.fix_hint and verbose:
                    console.print(f"        [dim]{err.fix_hint}[/dim]")
            
            for warn in result.warnings:
                loc = f"{warn.file}:{warn.line}" if warn.line else warn.file
                console.print(f"  [yellow]WARN[/yellow] {loc}: {warn.message}")
    
    raise SystemExit(0 if result.passed else 1)


def _add_fix_suggestions(result: VerificationResult, root: Path) -> VerificationResult:
    """Add fix suggestions by searching for moved files."""
    import subprocess
    from ..verifiers.base import VerificationError
    
    externals_dir = root / "externals"
    if not externals_dir.exists():
        return result
    
    new_errors = []
    for err in result.errors:
        if 'Expected at' in (err.fix_hint or ''):
            # Extract filename from expected path
            expected_path = err.fix_hint.replace('Expected at', '').strip()
            filename = Path(expected_path).name
            
            # Search for file in externals
            try:
                proc = subprocess.run(
                    ['find', str(externals_dir), '-name', filename, '-type', 'f'],
                    capture_output=True, text=True, timeout=5
                )
                found = [p for p in proc.stdout.strip().split('\n') if p]
                
                if found:
                    # Create suggestion
                    suggestion = f"Found: {found[0]}"
                    if len(found) > 1:
                        suggestion += f" (+{len(found)-1} more)"
                    new_hint = f"{err.fix_hint}\n        Suggestion: {suggestion}"
                    new_errors.append(VerificationError(
                        file=err.file,
                        line=err.line,
                        message=err.message,
                        fix_hint=new_hint,
                    ))
                    continue
            except (subprocess.TimeoutExpired, Exception):
                pass
        
        new_errors.append(err)
    
    return VerificationResult(
        passed=result.passed,
        errors=new_errors,
        warnings=result.warnings,
        summary=result.summary,
        details=result.details,
    )
