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

from ..verifiers import VERIFIERS
from .verify_output import add_fix_suggestions, apply_strict_mode, output_result

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
@click.option("--strict", is_flag=True,
              help="Treat warnings as errors")
def verify_refs(
    json_output: bool,
    verbose: bool,
    path: str,
    suggest_fixes: bool,
    exclude: tuple[str, ...],
    no_default_excludes: bool,
    strict: bool,
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
        result = add_fix_suggestions(result, Path(path))

    if strict:
        result = apply_strict_mode(result)

    output_result(result, json_output, verbose, "refs")


@verify.command("all")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--strict", is_flag=True,
              help="Treat warnings as errors for all verifiers")
def verify_all(json_output: bool, verbose: bool, path: str, strict: bool):
    """Run all verifications."""
    results = {}
    all_passed = True

    for name, verifier_cls in VERIFIERS.items():
        verifier = verifier_cls()
        result = verifier.verify(Path(path))

        if strict:
            result = apply_strict_mode(result)

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
                    msg = f"  [yellow]WARN[/yellow] {warn.file}:{warn.line}: {warn.message}"
                    console.print(msg)

        # Summary
        console.print()
        if all_passed:
            console.print("[green]All verifications passed[/green]")
        else:
            console.print("[red]Some verifications failed[/red]")

    # Exit code
    raise SystemExit(0 if all_passed else 1)


@verify.command("links")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--strict", is_flag=True,
              help="Treat warnings as errors")
def verify_links(json_output: bool, verbose: bool, path: str, strict: bool):
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

    if strict:
        result = apply_strict_mode(result)

    output_result(result, json_output, verbose, "links")


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

    if strict:
        result = apply_strict_mode(result)

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


@verify.command("trace")
@click.argument("link", required=True)
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show details")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
def verify_trace(link: str, json_output: bool, verbose: bool, path: str):
    """Verify a specific trace link between artifacts.

    Check if a trace relationship exists between two artifacts.
    The link format is: FROM_ID -> TO_ID

    \b
    Examples:
      sdqctl verify trace "UCA-001 -> SC-001"        # Check UCA → SC link
      sdqctl verify trace "UCA-BOLUS-003 -> REQ-020" # Check specific link
      sdqctl verify trace "SC-001 -> REQ-001"        # Check SC → REQ link
    """
    import re

    # Parse the link argument
    link_pattern = r'^([A-Z]+-[A-Z0-9-]+[a-z]?)\s*(?:->|→)\s*([A-Z]+-[A-Z0-9-]+[a-z]?)$'
    match = re.match(link_pattern, link.strip())
    if not match:
        console.print(f"[red]Invalid link format:[/red] {link}")
        console.print("Expected format: FROM_ID -> TO_ID (e.g., UCA-001 -> SC-001)")
        raise SystemExit(1)

    from_id = match.group(1)
    to_id = match.group(2)

    verifier = VERIFIERS["traceability"]()
    result = verifier.verify_trace(from_id, to_id, Path(path))

    if json_output:
        import json
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ LINKED[/green]" if result.passed else "[red]✗ NOT LINKED[/red]"
        console.print(f"{status}: {result.summary}")

        if verbose or not result.passed:
            for err in result.errors:
                console.print(f"  [red]ERROR[/red] {err.message}")
                if err.fix_hint:
                    console.print(f"        [dim]{err.fix_hint}[/dim]")

    raise SystemExit(0 if result.passed else 1)


@verify.command("coverage")
@click.argument("check", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show details")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
def verify_coverage(check: Optional[str], json_output: bool, verbose: bool, path: str):
    """Verify traceability coverage metrics.

    Without arguments, shows a coverage report. With a CHECK argument,
    verifies that the specified metric meets the threshold.

    \b
    CHECK format: METRIC OP THRESHOLD
    Example: "uca_to_sc >= 80" or "overall >= 50"

    \b
    Available metrics:
      loss_to_haz   - LOSS artifacts linked to HAZ
      haz_to_uca    - HAZ artifacts linked to UCA
      uca_to_sc     - UCA artifacts linked to SC
      req_to_spec   - REQ artifacts linked to SPEC
      spec_to_test  - SPEC artifacts linked to TEST
      overall       - Average of all metrics

    \b
    Examples:
      sdqctl verify coverage                # Show coverage report
      sdqctl verify coverage "uca_to_sc >= 80"    # Check UCA→SC coverage
      sdqctl verify coverage "overall >= 50"      # Check overall coverage
    """
    from ..verifiers.traceability import TraceabilityVerifier

    verifier = TraceabilityVerifier()

    if check:
        # Parse the check expression: metric op threshold
        import re
        match = re.match(r'^(\w+)\s*(>=|<=|>|<|==)\s*(\d+(?:\.\d+)?)%?$', check.strip())
        if not match:
            console.print(f"[red]Invalid check format: {check}[/red]")
            console.print("Expected: METRIC OP THRESHOLD (e.g., 'uca_to_sc >= 80')")
            raise SystemExit(1)

        metric = match.group(1)
        op = match.group(2)
        threshold = float(match.group(3))

        result = verifier.verify_coverage(Path(path), metric=metric, op=op, threshold=threshold)
    else:
        result = verifier.verify_coverage(Path(path))

    if json_output:
        import json
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
        console.print(f"{status}: {result.summary}")

        if verbose and result.details.get("coverage"):
            coverage = result.details["coverage"]
            console.print("\n[bold]Coverage Metrics:[/bold]")
            for key, value in sorted(coverage.items()):
                if "_to_" in key:
                    console.print(f"  {key}: {value:.1f}%")

        if not result.passed:
            for err in result.errors:
                console.print(f"  [red]ERROR[/red] {err.message}")
                if err.fix_hint:
                    console.print(f"        [dim]{err.fix_hint}[/dim]")

    raise SystemExit(0 if result.passed else 1)


@verify.command("terminology")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--glossary", "-g", type=click.Path(), default=None,
              help="Path to glossary file (default: auto-detect docs/GLOSSARY.md)")
@click.option("--strict", is_flag=True,
              help="Treat capitalization warnings as errors")
def verify_terminology(
    json_output: bool,
    verbose: bool,
    path: str,
    glossary: Optional[str],
    strict: bool,
):
    """Verify terminology consistency against glossary.

    Scans markdown files for deprecated terms and inconsistent
    capitalization. Uses docs/GLOSSARY.md as the authoritative
    source for terminology.

    \b
    Checks:
      Deprecated terms       "quine" → "synthesis cycle"
      Capitalization         "nightscout" → "Nightscout"
      Acronyms               "stpa" → "STPA"

    \b
    Examples:
      sdqctl verify terminology                # Verify current directory
      sdqctl verify terminology -p docs/       # Verify specific directory
      sdqctl verify terminology --glossary custom.md  # Use custom glossary
      sdqctl verify terminology --strict       # Fail on capitalization issues
      sdqctl verify terminology --json         # JSON output for CI
    """
    verifier = VERIFIERS["terminology"]()
    result = verifier.verify(Path(path), glossary=glossary)

    if strict:
        result = apply_strict_mode(result)

    output_result(result, json_output, verbose, "terminology")


@verify.command("assertions")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--require-message", is_flag=True,
              help="Error if assertions lack messages (default: warn)")
@click.option("--require-trace", is_flag=True,
              help="Error if assertions lack trace IDs (REQ-NNN, SC-NNN)")
def verify_assertions(
    json_output: bool,
    verbose: bool,
    path: str,
    require_message: bool,
    require_trace: bool,
):
    """Verify that assertions are documented and traced.

    Scans source files for assertion statements and checks whether
    they have meaningful messages and traceability IDs.

    \b
    Supported Languages:
      Python      assert condition, "message"
      Swift       assert(), precondition(), fatalError()
      Kotlin      assert(), require(), check()
      TypeScript  console.assert(), assert()

    \b
    Trace IDs in messages or comments:
      assert x > 0, "REQ-001: value must be positive"
      # SC-010a: validate input range
      assert input_valid

    \b
    Examples:
      sdqctl verify assertions                   # Scan current directory
      sdqctl verify assertions -p src/           # Scan specific directory
      sdqctl verify assertions --require-message # Error on missing messages
      sdqctl verify assertions --require-trace   # Error on missing trace IDs
      sdqctl verify assertions --json            # JSON output for CI
    """
    verifier = VERIFIERS["assertions"]()
    result = verifier.verify(
        Path(path),
        require_message=require_message,
        require_trace=require_trace,
    )

    if json_output:
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ PASSED[/green]" if result.passed else "[red]✗ FAILED[/red]"
        console.print(f"{status}: {result.summary}")

        # Show language breakdown if verbose
        if verbose and result.details.get("by_language"):
            langs = result.details["by_language"]
            if langs:
                console.print()
                console.print("[bold]Assertions by Language[/bold]")
                for lang, count in sorted(langs.items()):
                    console.print(f"  {lang}: {count}")

        # Show errors and warnings
        if verbose or not result.passed:
            if result.errors:
                console.print()
            for err in result.errors:
                loc = f"{err.file}:{err.line}" if err.line else err.file
                console.print(f"  [red]ERROR[/red] {loc}: {err.message}")
                if err.fix_hint and verbose:
                    console.print(f"        [dim]{err.fix_hint}[/dim]")

            if verbose:
                for warn in result.warnings:
                    loc = f"{warn.file}:{warn.line}" if warn.line else warn.file
                    console.print(f"  [yellow]WARN[/yellow] {loc}: {warn.message}")

    raise SystemExit(0 if result.passed else 1)


@verify.command("plugin")
@click.argument("name", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show details")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
@click.option("--list", "list_plugins", is_flag=True, help="List available plugins")
def verify_plugin(
    name: Optional[str],
    json_output: bool,
    verbose: bool,
    path: str,
    list_plugins: bool,
):
    """Run a plugin verifier.

    Plugin verifiers are defined in .sdqctl/directives.yaml manifests.
    Use --list to see available plugins.

    \b
    Examples:
      sdqctl verify plugin --list                # List available plugins
      sdqctl verify plugin hello-world           # Run hello-world plugin
      sdqctl verify plugin ecosystem-gaps -v     # Run with verbose output
    """
    from ..plugins import load_plugin_verifiers

    plugins = load_plugin_verifiers(Path(path))

    if list_plugins or name is None:
        if not plugins:
            console.print("[yellow]No plugin verifiers found[/yellow]")
            console.print("Create .sdqctl/directives.yaml to define plugins")
            console.print("See: sdqctl help plugin-authoring")
        else:
            console.print("[bold]Available Plugin Verifiers[/bold]")
            for pname, pv in sorted(plugins.items()):
                console.print(f"  {pname}: {pv.description}")
        raise SystemExit(0)

    if name not in plugins:
        console.print(f"[red]Unknown plugin verifier:[/red] {name}")
        if plugins:
            console.print(f"Available: {', '.join(sorted(plugins.keys()))}")
        else:
            console.print("No plugins found. Create .sdqctl/directives.yaml")
        raise SystemExit(1)

    plugin = plugins[name]
    result = plugin.verify(Path(path))

    if json_output:
        console.print_json(json.dumps(result.to_json()))
    else:
        status = "[green]✓ PASSED[/green]" if result.passed else "[red]✗ FAILED[/red]"
        console.print(f"{status}: {result.summary}")

        if verbose and result.details:
            if result.details.get("stdout"):
                console.print()
                console.print("[bold]Output:[/bold]")
                console.print(result.details["stdout"])

        if not result.passed:
            for err in result.errors:
                console.print(f"  [red]ERROR[/red] {err.message}")
                if err.fix_hint and verbose:
                    console.print(f"        [dim]{err.fix_hint}[/dim]")

    raise SystemExit(0 if result.passed else 1)
