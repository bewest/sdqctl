"""
Verification output and helper utilities.

This module is separate from commands/verify.py to:
1. Reduce verify.py to focused CLI handlers
2. Enable reuse of output formatting
3. Centralize strict mode logic
"""

import json
import subprocess
from pathlib import Path

from rich.console import Console

from ..verifiers.base import VerificationError, VerificationResult

console = Console()


def output_result(
    result: VerificationResult,
    json_output: bool,
    verbose: bool,
    name: str,
) -> None:
    """Output verification result in requested format.

    Note: Raises SystemExit with appropriate code.
    """
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


def apply_strict_mode(result: VerificationResult) -> VerificationResult:
    """Promote warnings to errors in strict mode.

    Returns a new VerificationResult with warnings converted to errors
    and passed=False if there were any warnings.
    """
    if not result.warnings:
        return result

    return VerificationResult(
        passed=False,
        errors=result.errors + result.warnings,
        warnings=[],
        summary=result.summary + " (strict mode)",
        details=result.details,
    )


def add_fix_suggestions(result: VerificationResult, root: Path) -> VerificationResult:
    """Add fix suggestions by searching for moved files in externals/."""
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
