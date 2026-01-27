"""
init command - Initialize sdqctl in a project.

Creates configuration files and example workflows.
"""

from pathlib import Path

import click
from rich.console import Console


@click.command()
@click.argument("name", default=".")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-copilot", is_flag=True, help="Skip GitHub Copilot integration files")
def init(name: str, force: bool, no_copilot: bool) -> None:
    """Initialize sdqctl in a project.

    Creates:
    - .sdqctl.yaml config file
    - workflows/ directory with examples
    - .github/copilot-instructions.md (unless --no-copilot)
    - .github/skills/sdqctl-verify.md (unless --no-copilot)
    """
    console = Console()
    target_dir = Path(name).resolve()

    if not target_dir.exists():
        target_dir.mkdir(parents=True)

    config_file = target_dir / ".sdqctl.yaml"
    workflows_dir = target_dir / "workflows"

    # Create config
    if config_file.exists() and not force:
        console.print(f"[yellow]Config already exists: {config_file}[/yellow]")
    else:
        config_content = """\
# sdqctl configuration
# See: https://github.com/bewest/copilot-do-proposal

project:
  name: my-project

defaults:
  adapter: copilot
  model: gpt-4

context:
  limit: 80%
  on_limit: compact

checkpoints:
  enabled: true
  directory: .sdqctl/checkpoints
"""
        config_file.write_text(config_content)
        console.print(f"[green]Created: {config_file}[/green]")

    # Create workflows directory
    if not workflows_dir.exists():
        workflows_dir.mkdir()
        console.print(f"[green]Created: {workflows_dir}/[/green]")

    # Create example workflow
    example_workflow = workflows_dir / "example-audit.conv"
    if example_workflow.exists() and not force:
        console.print(f"[yellow]Example already exists: {example_workflow}[/yellow]")
    else:
        example_content = """\
# Example security audit workflow
# Run with: sdqctl run workflows/example-audit.conv

MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 1

# Context files to include
# CONTEXT @lib/auth/*.js
# CONTEXT @tests/auth.test.js

# Context window settings
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

PROMPT Analyze the codebase for security vulnerabilities.
PROMPT Focus on authentication, input validation, and data handling.
PROMPT Generate a security report with severity ratings.

OUTPUT-FORMAT markdown
OUTPUT-FILE security-audit.md
"""
        example_workflow.write_text(example_content)
        console.print(f"[green]Created: {example_workflow}[/green]")

    # Create GitHub Copilot integration files
    if not no_copilot:
        _create_copilot_files(target_dir, force, console)

    console.print("\n[bold]sdqctl initialized![/bold]")
    console.print("\nNext steps:")
    console.print("  1. Edit .sdqctl.yaml to configure your project")
    console.print("  2. Create workflows in the workflows/ directory")
    console.print("  3. Run: sdqctl run workflows/example-audit.conv --dry-run")
    if not no_copilot:
        console.print("  4. Copilot can now use sdqctl commands for verification")


def _create_copilot_files(target_dir: Path, force: bool, console: Console) -> None:
    """Create GitHub Copilot integration files."""
    github_dir = target_dir / ".github"
    skills_dir = github_dir / "skills"

    # Create directories
    github_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)

    # Create copilot-instructions.md
    instructions_file = github_dir / "copilot-instructions.md"
    if instructions_file.exists() and not force:
        console.print(
            f"[yellow]Copilot instructions already exist: {instructions_file}[/yellow]"
        )
    else:
        instructions_content = """\
# sdqctl Project Instructions

This project uses **sdqctl** (Software Defined Quality Control) for declarative AI workflows.

## Workflow Files

Workflow files use the `.conv` extension and a Dockerfile-like syntax:
- `MODEL` - AI model to use
- `ADAPTER` - AI provider (copilot, claude, openai, mock)
- `CONTEXT @pattern` - Include files matching pattern
- `PROMPT` - Instructions for the AI
- `OUTPUT-FILE` - Where to write results

## Validation Commands (No LLM Required)

Before committing `.conv` workflow files, validate them:

```bash
# Check syntax of all workflows
sdqctl validate workflows/*.conv

# Inspect parsed structure
sdqctl show <file.conv>

# Preview execution without running
sdqctl run <file.conv> --dry-run
```

## Testing Workflows

Use the mock adapter to test workflow mechanics without LLM calls:

```bash
sdqctl run <file.conv> --adapter mock --verbose
```

## Status Commands

```bash
# Check system configuration
sdqctl status

# List available adapters
sdqctl status --adapters

# View active sessions
sdqctl status --sessions
```

## CI/CD Integration

These commands are safe for CI/CD pipelines (no LLM calls):
- `sdqctl validate` - Syntax validation
- `sdqctl show` - Structure inspection
- `sdqctl run --dry-run` - Execution preview
- `sdqctl run --adapter mock` - Mock execution
- `sdqctl status` - Configuration check
"""
        instructions_file.write_text(instructions_content)
        console.print(f"[green]Created: {instructions_file}[/green]")

    # Create sdqctl-verify skill
    skill_file = skills_dir / "sdqctl-verify.md"
    if skill_file.exists() and not force:
        console.print(f"[yellow]Skill already exists: {skill_file}[/yellow]")
    else:
        skill_content = """\
---
name: sdqctl-verify
description: Validate and inspect sdqctl workflow files without LLM calls
tools:
  - bash
---

# sdqctl Verification Skill

Use this skill to validate, inspect, and dry-run sdqctl workflows.
All commands in this skill run **without LLM calls** and are safe for CI/CD.

## Validate Workflow Syntax

Check that a `.conv` file has valid syntax:

```bash
sdqctl validate <workflow.conv>
```

Returns validation status and any syntax errors.

## Show Parsed Structure

Display the internal representation of a workflow:

```bash
sdqctl show <workflow.conv>
```

Shows: model, adapter, mode, prompts, context patterns, output config.

## Preview Execution (Dry Run)

See what would happen without actually running:

```bash
sdqctl run <workflow.conv> --dry-run
```

Shows configuration and prompts that would be sent.

## Test with Mock Adapter

Run the full workflow mechanics without LLM calls:

```bash
sdqctl run <workflow.conv> --adapter mock --verbose
```

Uses canned responses to test workflow flow, checkpoints, and output.

## Check System Status

```bash
# Overview
sdqctl status

# Available adapters
sdqctl status --adapters

# Active sessions
sdqctl status --sessions
```

## Validate All Workflows

```bash
for f in workflows/*.conv; do
  sdqctl validate "$f" || echo "FAILED: $f"
done
```

## When to Use This Skill

- **Before committing**: Validate new/modified `.conv` files
- **In CI/CD**: Verify workflow definitions are valid
- **During review**: Inspect what a workflow will do
- **Debugging**: Test workflow mechanics with mock adapter
"""
        skill_file.write_text(skill_content)
        console.print(f"[green]Created: {skill_file}[/green]")
