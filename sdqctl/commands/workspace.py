#!/usr/bin/env python3
"""
sdqctl workspace - Multi-repository workspace management.

Commands for working with external repositories in the ecosystem alignment workspace.
"""

import subprocess
from pathlib import Path

import click


def find_workspace_root() -> Path | None:
    """Find the workspace root by looking for .sdqctl.yaml or externals/ dir."""
    cwd = Path.cwd()
    # Walk up looking for indicators
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".sdqctl.yaml").exists():
            return parent
        if (parent / "externals").is_dir():
            return parent
    return None


def get_externals(root: Path) -> list[Path]:
    """Get all external repository directories."""
    externals_dir = root / "externals"
    if not externals_dir.exists():
        return []

    repos = []
    for item in sorted(externals_dir.iterdir()):
        if item.is_dir() and (item / ".git").exists():
            repos.append(item)
    return repos


def get_git_status(repo: Path) -> dict:
    """Get git status for a repository."""
    try:
        # Get current branch
        branch = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        branch_name = branch.stdout.strip() if branch.returncode == 0 else "unknown"

        # Check for uncommitted changes
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        has_changes = bool(status.stdout.strip()) if status.returncode == 0 else False

        # Get last commit date
        log = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%cr"],
            capture_output=True, text=True, timeout=5
        )
        last_commit = log.stdout.strip() if log.returncode == 0 else "unknown"

        return {
            "branch": branch_name,
            "has_changes": has_changes,
            "last_commit": last_commit,
        }
    except Exception as e:
        return {"error": str(e)}


@click.group("workspace")
def workspace():
    """Multi-repository workspace management.

    Commands for working with external repositories in an ecosystem
    alignment workspace (e.g., rag-nightscout-ecosystem-alignment).

    \b
    Examples:
      sdqctl workspace status          # Show all externals/ status
      sdqctl workspace search "bolus"  # Search across all repos
    """
    pass


@workspace.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show status of all external repositories.

    Displays branch, uncommitted changes, and last commit for each repo
    in the externals/ directory.
    """
    root = find_workspace_root()
    if not root:
        click.echo("Error: Not in a workspace (no externals/ or .sdqctl.yaml found)", err=True)
        raise SystemExit(1)

    repos = get_externals(root)
    if not repos:
        click.echo("No external repositories found in externals/")
        return

    if as_json:
        import json
        result = {}
        for repo in repos:
            result[repo.name] = get_git_status(repo)
        click.echo(json.dumps(result, indent=2))
        return

    # Table output
    click.echo(f"Workspace: {root}")
    click.echo(f"External repositories: {len(repos)}")
    click.echo()

    # Header
    click.echo(f"{'Repository':<35} {'Branch':<20} {'Changes':<10} {'Last Commit':<20}")
    click.echo("-" * 85)

    for repo in repos:
        status_info = get_git_status(repo)
        if "error" in status_info:
            click.echo(f"{repo.name:<35} Error: {status_info['error']}")
            continue

        changes = "✗ dirty" if status_info["has_changes"] else "✓ clean"
        line = (
            f"{repo.name:<35} {status_info['branch']:<20} "
            f"{changes:<10} {status_info['last_commit']:<20}"
        )
        click.echo(line)


@workspace.command("search")
@click.argument("pattern")
@click.option("-i", "--ignore-case", is_flag=True, help="Case insensitive search")
@click.option("-t", "--type", "file_type", help="File type filter (e.g., swift, java, kt)")
@click.option("--context", "-C", type=int, default=0, help="Lines of context")
@click.option("--files-only", "-l", is_flag=True, help="Only show file names")
def search(pattern: str, ignore_case: bool, file_type: str | None, context: int, files_only: bool):
    """Search across all external repositories.

    Uses ripgrep if available, falls back to grep.

    \b
    Examples:
      sdqctl workspace search "bolus"
      sdqctl workspace search "Treatment" -t swift
      sdqctl workspace search "glucose" -i -C 2
    """
    root = find_workspace_root()
    if not root:
        click.echo("Error: Not in a workspace", err=True)
        raise SystemExit(1)

    externals_dir = root / "externals"
    if not externals_dir.exists():
        click.echo("Error: No externals/ directory found", err=True)
        raise SystemExit(1)

    # Try ripgrep first, fall back to grep
    use_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0

    if use_rg:
        cmd = ["rg"]
        if ignore_case:
            cmd.append("-i")
        if file_type:
            cmd.extend(["-t", file_type])
        if context > 0:
            cmd.extend(["-C", str(context)])
        if files_only:
            cmd.append("-l")
        else:
            cmd.append("-n")
        cmd.append(pattern)
        cmd.append(str(externals_dir))
    else:
        # Fallback to grep
        cmd = ["grep", "-r"]
        if ignore_case:
            cmd.append("-i")
        if files_only:
            cmd.append("-l")
        else:
            cmd.append("-n")
        if context > 0:
            cmd.extend(["-C", str(context)])
        if file_type:
            cmd.extend(["--include", f"*.{file_type}"])
        cmd.append(pattern)
        cmd.append(str(externals_dir))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            # Make paths relative to workspace root for readability
            output = result.stdout.replace(str(root) + "/", "")
            click.echo(output, nl=False)
        if result.returncode == 1 and not result.stdout:
            click.echo("No matches found")
        elif result.returncode > 1:
            click.echo(f"Error: {result.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: grep not found", err=True)
        raise SystemExit(1)


@workspace.command("diff")
@click.argument("pattern")
@click.option("-t", "--type", "file_type", help="File type filter (e.g., swift, java)")
def diff(pattern: str, file_type: str | None):
    """Compare implementations matching a pattern across repos.

    Finds files matching the pattern and shows a summary of implementations
    across different external repositories.

    \b
    Examples:
      sdqctl workspace diff "Treatment"
      sdqctl workspace diff "bolus" -t swift
    """
    root = find_workspace_root()
    if not root:
        click.echo("Error: Not in a workspace", err=True)
        raise SystemExit(1)

    repos = get_externals(root)
    if not repos:
        click.echo("No external repositories found")
        return

    click.echo(f"Searching for '{pattern}' across {len(repos)} repositories...")
    click.echo()

    for repo in repos:
        # Find matching files
        cmd = ["rg", "-l"]
        if file_type:
            cmd.extend(["-t", file_type])
        cmd.append(pattern)
        cmd.append(str(repo))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.stdout:
                files = result.stdout.strip().split("\n")
                click.echo(f"### {repo.name} ({len(files)} files)")
                for f in files[:10]:  # Limit to first 10
                    rel_path = Path(f).relative_to(root)
                    click.echo(f"  - {rel_path}")
                if len(files) > 10:
                    click.echo(f"  ... and {len(files) - 10} more")
                click.echo()
        except FileNotFoundError:
            click.echo("Error: ripgrep (rg) not found", err=True)
            raise SystemExit(1)
        except subprocess.TimeoutExpired:
            click.echo(f"  (timeout searching {repo.name})")
