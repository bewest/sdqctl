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
@click.option("--exclude", "-e", multiple=True,
              help="Exclude pattern (glob syntax, can be repeated)")
@click.option("--no-default-excludes", is_flag=True,
              help="Don't apply default exclusions (.venv, node_modules, etc.)")
def verify_refs(
    json_output: bool, 
    verbose: bool, 
    path: str, 
    suggest_fixes: bool,
    exclude: tuple[str, ...],
    no_default_excludes: bool,
):
    """Verify that @-references and alias:refs resolve to files.
    
    Scans markdown and workflow files for references and validates
    that the referenced files exist.
    
    \b
    Supported reference formats:
      @path/to/file.md         Standard @-reference
      alias:path/file.swift    Workspace alias (from workspace.lock.json)
      loop:Loop/README.md      Example alias reference
    
    \b
    Default exclusions:
      .venv, venv, node_modules, __pycache__, .git, lib, lib64, etc.
      Additional patterns can be added via .sdqctlignore file.
    
    \b
    Examples:
      sdqctl verify refs                    # Verify current directory
      sdqctl verify refs -p docs/           # Verify specific directory
      sdqctl verify refs --json             # JSON output for CI
      sdqctl verify refs --suggest-fixes    # Search for correct paths
      sdqctl verify refs -e "examples/**"   # Exclude examples directory
    """
    verifier = VERIFIERS["refs"]()
    result = verifier.verify(
        Path(path),
        exclude=set(exclude) if exclude else None,
        no_default_excludes=no_default_excludes,
    )
    
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


@verify.command("links")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
def verify_links(json_output: bool, verbose: bool, path: str):
    """Verify that URLs and file links are valid.
    
    Scans markdown files for internal and external links and validates
    that they resolve correctly.
    
    \b
    Examples:
      sdqctl verify links                     # Verify current directory
      sdqctl verify links -p docs/            # Verify specific directory
      sdqctl verify links --json              # JSON output for CI
    """
    verifier = VERIFIERS["links"]()
    result = verifier.verify(Path(path))
    _output_result(result, json_output, verbose, "links")


@verify.command("traceability")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--coverage", is_flag=True, 
              help="Show detailed coverage metrics")
@click.option("--strict", is_flag=True,
              help="Treat warnings as errors")
def verify_traceability(
    json_output: bool, 
    verbose: bool, 
    path: str, 
    coverage: bool,
    strict: bool,
):
    """Verify STPA/IEC 62304 traceability links.
    
    Scans markdown files for traceability artifacts (REQ, SPEC, TEST,
    UCA, SC, GAP, etc.) and verifies proper linking.
    
    \b
    Artifact Types:
      LOSS-NNN, HAZ-NNN           STPA losses and hazards
      UCA-NNN, UCA-DOMAIN-NNN     Unsafe Control Actions
      SC-NNN, SC-DOMAIN-NNNx      Safety Constraints
      REQ-NNN, REQ-DOMAIN-NNN     Requirements
      SPEC-NNN, TEST-NNN          Specifications and tests
      GAP-DOMAIN-NNN              Implementation gaps
      Q-NNN, BUG-NNN, PROP-NNN    Development artifacts
    
    \b
    Examples:
      sdqctl verify traceability              # Basic verification
      sdqctl verify traceability --coverage   # Show coverage metrics
      sdqctl verify traceability --strict     # Fail on warnings
      sdqctl verify traceability --json       # JSON output for CI
    """
    verifier = VERIFIERS["traceability"]()
    result = verifier.verify(Path(path))
    
    # In strict mode, promote warnings to errors
    if strict and result.warnings:
        from ..verifiers.base import VerificationError
        result = VerificationResult(
            passed=False,
            errors=result.errors + result.warnings,
            warnings=[],
            summary=result.summary + " (strict mode)",
            details=result.details,
        )
    
    if json_output:
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ PASSED[/green]" if result.passed else "[red]✗ FAILED[/red]"
        console.print(f"{status}: {result.summary}")
        
        # Show coverage metrics if requested
        if coverage and result.details and "coverage" in result.details:
            cov = result.details["coverage"]
            console.print()
            console.print("[bold]Artifact Coverage Report[/bold]")
            console.print("=" * 40)
            
            # STPA chain
            if cov.get("total_losses", 0) > 0:
                pct = cov.get("loss_to_haz", 0)
                console.print(f"LOSS: {cov['total_losses']} found, {pct:.0f}% linked to HAZ")
            if cov.get("total_hazards", 0) > 0:
                pct = cov.get("haz_to_uca", 0)
                console.print(f"HAZ: {cov['total_hazards']} found, {pct:.0f}% linked to UCA")
            if cov.get("total_ucas", 0) > 0:
                pct = cov.get("uca_to_sc", 0)
                console.print(f"UCA: {cov['total_ucas']} found, {pct:.0f}% have SC")
            if cov.get("total_scs", 0) > 0:
                console.print(f"SC: {cov['total_scs']} found")
            
            # IEC 62304 chain
            if cov.get("total_reqs", 0) > 0:
                pct = cov.get("req_to_spec", 0)
                console.print(f"REQ: {cov['total_reqs']} found, {pct:.0f}% have SPEC")
            if cov.get("total_specs", 0) > 0:
                pct = cov.get("spec_to_test", 0)
                console.print(f"SPEC: {cov['total_specs']} found, {pct:.0f}% have TEST")
            if cov.get("total_tests", 0) > 0:
                console.print(f"TEST: {cov['total_tests']} found")
            
            # Development artifacts
            dev_arts = []
            if cov.get("total_bugs", 0) > 0:
                dev_arts.append(f"BUG: {cov['total_bugs']}")
            if cov.get("total_props", 0) > 0:
                dev_arts.append(f"PROP: {cov['total_props']}")
            if cov.get("total_quirks", 0) > 0:
                dev_arts.append(f"Q: {cov['total_quirks']}")
            if dev_arts:
                console.print(f"Development: {', '.join(dev_arts)}")
            
            # Overall
            overall = cov.get("overall", 0)
            console.print()
            console.print(f"[bold]Overall trace coverage: {overall:.0f}%[/bold]")
        
        # Show errors and warnings
        if verbose or not result.passed:
            if result.errors:
                console.print()
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
