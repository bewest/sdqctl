"""
sdqctl drift - Drift detection for alignment monitoring.

Usage:
    sdqctl drift status                      # Show drift summary
    sdqctl drift --since 2026-01-01          # Changes since date
    sdqctl drift --report docs/drift.md      # Generate report
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group("drift")
def drift():
    """Drift detection for alignment monitoring.

    Detect changes in external repositories that may affect alignment.
    Identifies breaking changes and surfaces alignment opportunities.

    \b
    Examples:
      sdqctl drift status                    # Show drift summary
      sdqctl drift detect --since 2026-01-01 # Detect changes
      sdqctl drift --report docs/drift.md    # Generate report
    """
    pass


@drift.command("status")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def drift_status(json_output: bool):
    """Show drift detection status.

    Displays available repositories and last check time.
    """
    from sdqctl.monitoring import GitChangeDetector

    # Find externals directory
    externals = Path("externals")
    if not externals.exists():
        externals = Path("../externals")

    repos = list(externals.glob("*/.git/..")) if externals.exists() else []

    if json_output:
        import json

        data = {
            "externals_path": str(externals) if externals.exists() else None,
            "repos": [str(r.resolve()) for r in repos],
            "repo_count": len(repos),
        }
        console.print_json(json.dumps(data))
        return

    table = Table(title="Drift Detection Status")
    table.add_column("Repository", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")

    if not repos:
        console.print("[yellow]No external repositories found[/yellow]")
        console.print(f"Looking in: {externals.resolve()}")
        return

    for repo in repos:
        detector = GitChangeDetector(repo)
        # Quick check: can we read git log?
        changes = detector.detect_changes(since="2026-01-27")
        status = f"{len(changes)} recent changes" if changes else "No recent changes"
        table.add_row(repo.name, str(repo), status)

    console.print(table)


@drift.command("detect")
@click.option("--since", "-s", default=None, help="Only changes after this date (YYYY-MM-DD)")
@click.option("--paths", "-p", multiple=True, help="Filter by path patterns")
@click.option("--repo", "-r", multiple=True, help="Specific repositories to check")
@click.option("--report", type=click.Path(), default=None, help="Write markdown report to file")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def drift_detect(
    since: Optional[str],
    paths: tuple[str, ...],
    repo: tuple[str, ...],
    report: Optional[str],
    json_output: bool,
):
    """Detect drift in external repositories.

    \b
    Examples:
      sdqctl drift detect --since 2026-01-01
      sdqctl drift detect --paths "*/treatments/*" --paths "*/models/*"
      sdqctl drift detect --repo Loop --repo AAPS
      sdqctl drift detect --report docs/drift-report.md
    """
    from sdqctl.monitoring import DriftReport, GitChangeDetector

    # Find repositories
    externals = Path("externals")
    if not externals.exists():
        externals = Path("../externals")

    if repo:
        # Specific repos requested
        repos = [externals / r for r in repo if (externals / r).exists()]
    else:
        # All repos in externals
        repos = [
            p for p in externals.iterdir()
            if p.is_dir() and (p / ".git").exists()
        ] if externals.exists() else []

    if not repos:
        console.print("[yellow]No repositories found[/yellow]")
        return

    # Collect changes
    all_changes = []
    path_list = list(paths) if paths else None

    for repo_path in repos:
        detector = GitChangeDetector(repo_path)
        changes = detector.detect_changes(since=since, paths=path_list)
        all_changes.extend(changes)

    # Build report
    drift_report = DriftReport(
        generated_at=datetime.now(),
        since=datetime.fromisoformat(since) if since else None,
        repos_checked=repos,
        changes=all_changes,
    )

    if json_output:
        import json

        data = {
            "generated_at": drift_report.generated_at.isoformat(),
            "since": since,
            "repos_checked": [str(r) for r in repos],
            "total_changes": len(all_changes),
            "critical": drift_report.critical_count,
            "high": drift_report.high_count,
            "changes": [
                {
                    "repo": str(c.repo.name),
                    "file": str(c.file_path),
                    "commit": c.commit_hash[:8],
                    "date": c.commit_date.isoformat(),
                    "message": c.message,
                    "impact": c.impact.value,
                }
                for c in all_changes[:50]  # Limit for JSON output
            ],
        }
        console.print_json(json.dumps(data))
        return

    # Write report file if requested
    if report:
        report_path = Path(report)
        report_path.write_text(drift_report.to_markdown())
        console.print(f"[green]Report written to {report_path}[/green]")

    # Display summary
    table = Table(title="Drift Detection Results")
    table.add_column("Impact", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("[red]Critical[/red]", str(drift_report.critical_count))
    table.add_row("[yellow]High[/yellow]", str(drift_report.high_count))
    table.add_row(
        "Medium",
        str(sum(1 for c in all_changes if c.impact.value == "medium")),
    )
    table.add_row(
        "[dim]Low[/dim]",
        str(sum(1 for c in all_changes if c.impact.value == "low")),
    )

    console.print(table)
    console.print()
    console.print(f"[dim]Checked {len(repos)} repositories, found {len(all_changes)} changes[/dim]")

    if drift_report.has_significant_drift:
        console.print()
        console.print("[yellow]⚠ Significant drift detected - review recommended[/yellow]")
