"""
Help content for sdqctl commands.

This module is separate from commands/help.py to:
1. Allow core modules to access command help without importing commands
2. Reduce help.py from 698 lines to a focused CLI handler
3. Follow the same pattern as help_topics.py
"""

# Command help (supplements Click's built-in help)
COMMAND_HELP = {
    "run": """
# sdqctl run

Execute a single prompt or ConversationFile workflow.

## Usage

```bash
sdqctl run "Audit authentication module"
sdqctl run workflow.conv
sdqctl run workflow.conv --adapter copilot --model gpt-4
```

## Key Options

| Option | Description |
|--------|-------------|
| `--adapter` | AI provider (copilot, claude, openai, mock) |
| `--model` | Model override |
| `--dry-run` | Preview without executing |
| `--allow-files` | File patterns AI can modify |
| `--deny-files` | File patterns AI cannot modify |

## Examples

```bash
# Simple prompt
sdqctl run "Analyze authentication for security issues"

# Workflow file
sdqctl run workflow.conv

# Dry run (no AI calls)
sdqctl run workflow.conv --dry-run

# Test with mock adapter
sdqctl run workflow.conv --adapter mock -v

# With file restrictions
sdqctl run workflow.conv --allow-files "lib/*" --deny-files "lib/core/*"
```

See also: `sdqctl help workflow`
""",

    "cycle": """
# sdqctl cycle

Run multi-cycle workflow with context management.

## Usage

```bash
sdqctl cycle workflow.conv --max-cycles 5
sdqctl cycle workflow.conv -n 3 --session-mode fresh
```

## Key Options

| Option | Description |
|--------|-------------|
| `--max-cycles, -n` | Maximum iterations |
| `--session-mode` | Context management (accumulate, compact, fresh) |
| `--checkpoint-dir` | Checkpoint storage location |
| `--from-json` | Execute from pre-rendered JSON |

## Session Modes

| Mode | Behavior |
|------|----------|
| `accumulate` | Context grows; compact only at limit |
| `compact` | Summarize after each cycle |
| `fresh` | New session each cycle (sees file changes) |

## Examples

```bash
# 5 cycles with checkpoints
sdqctl cycle workflow.conv -n 5

# Fresh mode for file editing
sdqctl cycle workflow.conv -n 3 --session-mode fresh

# From rendered JSON
sdqctl render cycle workflow.conv --json | sdqctl cycle --from-json -
```
""",

    "apply": """
# sdqctl apply

Apply a workflow to multiple components.

## Usage

```bash
sdqctl apply workflow.conv --components "lib/*.js"
sdqctl apply workflow.conv --components "src/**/*.ts" --progress progress.md
```

## Key Options

| Option | Description |
|--------|-------------|
| `--components` | Glob pattern for components |
| `--progress` | Progress tracking file |
| `--parallel` | Parallel execution count |
| `--output-dir` | Directory for output files |

## Template Variables

In your workflow, use:
- `{{COMPONENT_NAME}}` - Filename without extension
- `{{COMPONENT_PATH}}` - Full path
- `{{COMPONENT_DIR}}` - Parent directory
- `{{ITERATION_INDEX}}` - 1-based iteration number

## Examples

```bash
# Apply to all plugins
sdqctl apply audit.conv --components "lib/plugins/*.js"

# With progress tracking
sdqctl apply migrate.conv --components "src/*.ts" --progress status.md

# Parallel execution
sdqctl apply audit.conv --components "lib/*.js" --parallel 4
```
""",

    "render": """
# sdqctl render

Render workflow prompts without executing (no AI calls).

## Subcommands

```bash
sdqctl render run workflow.conv      # Single execution render
sdqctl render cycle workflow.conv    # Multi-cycle render
sdqctl render apply workflow.conv    # Apply command render
```

## Key Options

| Option | Description |
|--------|-------------|
| `--plan` | Show @file refs only (not content) |
| `--json` | JSON output format |
| `-o, --output` | Output to file |
| `--cycle` | Specific cycle number |
| `--prompt` | Specific prompt number |

## Use Cases

- Debug template expansion before expensive AI calls
- Use sdqctl as a prompt templating engine
- CI/CD validation of workflow content
- Pipeline composition with `--from-json`

## Examples

```bash
# Preview prompts
sdqctl render run workflow.conv

# JSON for pipeline
sdqctl render cycle workflow.conv --json > rendered.json

# Specific cycle/prompt
sdqctl render run workflow.conv --cycle 2 --prompt 1
```
""",

    "verify": """
# sdqctl verify

Static verification (no AI calls).

## Subcommands

```bash
sdqctl verify refs         # Verify @-references resolve
sdqctl verify links        # Verify markdown links
sdqctl verify traceability # Verify STPA traces
sdqctl verify terminology  # Verify term consistency
sdqctl verify assertions   # Verify assertion documentation
sdqctl verify all          # Run all verifications
```

## Key Options

| Option | Description |
|--------|-------------|
| `-p, --path` | Directory to verify |
| `--json` | JSON output format |
| `--verbose, -v` | Show all findings |

## Examples

```bash
# Check references
sdqctl verify refs

# Verify specific directory
sdqctl verify refs -p examples/workflows/

# JSON output for CI
sdqctl verify refs --json

# Check traceability with coverage report
sdqctl verify traceability --coverage

# Check assertions with strict mode
sdqctl verify assertions --require-trace
```

## In-Workflow Verification

Use VERIFY directive in ConversationFiles:

```dockerfile
VERIFY refs
VERIFY-ON-ERROR continue
VERIFY-OUTPUT on-error
```
""",

    "status": """
# sdqctl status

Show session and system status.

## Usage

```bash
sdqctl status              # Overview
sdqctl status --adapters   # Available AI adapters
sdqctl status --sessions   # Session details
sdqctl status --checkpoints  # Checkpoint details
```

## Key Options

| Option | Description |
|--------|-------------|
| `--adapters` | Show available adapters |
| `--sessions` | Show session details |
| `--checkpoints` | Show checkpoint details |
| `--json` | JSON output format |
""",

    "validate": """
# sdqctl validate

Validate a ConversationFile (no AI calls).

## Usage

```bash
sdqctl validate workflow.conv
sdqctl validate workflow.conv --allow-missing
sdqctl validate workflow.conv --strict
sdqctl validate workflow.conv --check-model
```

## Key Options

| Option | Description |
|--------|-------------|
| `--allow-missing` | Warn on missing context files |
| `--strict` | Fail on any issue |
| `--check-model` | Validate MODEL-REQUIRES can be resolved |
| `--exclude` | Patterns to exclude from validation |
| `--json` | JSON output format |

## Examples

```bash
# Basic validation
sdqctl validate workflow.conv

# Allow missing optional files
sdqctl validate workflow.conv --allow-missing

# Verify model requirements can be satisfied
sdqctl validate workflow.conv --check-model

# CI mode with JSON
sdqctl validate workflow.conv --json
```
""",

    "init": """
# sdqctl init

Initialize sdqctl in a project.

## Usage

```bash
sdqctl init
sdqctl init ./new-project
sdqctl init --no-copilot
```

## Creates

- `.sdqctl.yaml` - Configuration file
- `workflows/` - Example workflows directory
- `.github/copilot-instructions.md` - Copilot integration
- `.github/skills/sdqctl-verify.md` - Verification skill

## Key Options

| Option | Description |
|--------|-------------|
| `--force` | Overwrite existing files |
| `--no-copilot` | Skip GitHub Copilot files |
""",

    "resume": """
# sdqctl resume

Resume a paused workflow from checkpoint.

## Usage

```bash
sdqctl resume checkpoint.json
sdqctl resume --list
sdqctl resume checkpoint.json --dry-run
```

## Key Options

| Option | Description |
|--------|-------------|
| `--list` | List available checkpoints |
| `--dry-run` | Preview without executing |
| `--adapter` | Override adapter |
| `--json` | JSON output format |

## Workflow

1. Workflow pauses with `PAUSE` directive
2. Checkpoint saved to `.sdqctl/sessions/`
3. Human reviews
4. Resume with `sdqctl resume`

## Examples

```bash
# List checkpoints
sdqctl resume --list

# Preview resume
sdqctl resume ~/.sdqctl/sessions/abc123/pause.json --dry-run

# Resume execution
sdqctl resume ~/.sdqctl/sessions/abc123/pause.json
```
""",

    "sessions": """
# sdqctl sessions

Manage conversation sessions.

## Usage

```bash
sdqctl sessions list
sdqctl sessions list --format json
sdqctl sessions list --filter "audit-*"
sdqctl sessions delete SESSION_ID
sdqctl sessions cleanup --older-than 7d
sdqctl sessions resume SESSION_ID --prompt "Continue"
```

## Subcommands

| Command | Description |
|---------|-------------|
| `list` | List all available sessions |
| `delete` | Delete a session permanently |
| `cleanup` | Clean up old sessions |
| `resume` | Resume a previous conversation session |

## List Options

| Option | Description |
|--------|-------------|
| `--format` | Output format (table, json) |
| `--filter` | Filter by session name pattern (glob) |
| `--adapter` | Adapter to use (default: copilot) |

## Delete Options

| Option | Description |
|--------|-------------|
| `--force, -f` | Skip confirmation prompt |
| `--adapter` | Adapter to use (default: copilot) |

## Cleanup Options

| Option | Description |
|--------|-------------|
| `--older-than` | Delete sessions older than (e.g., 7d, 24h, 30m) |
| `--dry-run` | Show what would be deleted without deleting |
| `--adapter` | Adapter to use (default: copilot) |

## Resume Options

| Option | Description |
|--------|-------------|
| `--prompt, -p` | Send an immediate prompt after resuming |
| `--adapter` | Adapter to use (default: copilot) |
| `--model` | Model to use for resumed session |
| `--streaming/--no-streaming` | Enable/disable streaming output |

## Examples

```bash
# List all sessions in table format
sdqctl sessions list

# List sessions as JSON
sdqctl sessions list --format json

# Filter sessions by pattern
sdqctl sessions list --filter "security-*"

# Delete a session (with confirmation)
sdqctl sessions delete my-session-id

# Delete a session (skip confirmation)
sdqctl sessions delete my-session-id --force

# Preview cleanup (dry run)
sdqctl sessions cleanup --older-than 7d --dry-run

# Clean up sessions older than 30 days
sdqctl sessions cleanup --older-than 30d

# Resume a session
sdqctl sessions resume security-audit-2026-01

# Resume and send immediate prompt
sdqctl sessions resume my-session --prompt "Continue with auth module"
```

## Notes

- Remote sessions are automatically filtered from listings
- The `cleanup` command respects the dry-run flag
- Sessions older than 30 days trigger a cleanup tip in listings
- Use `SESSION-NAME` directive in workflows for named sessions
""",

    "flow": """
# sdqctl flow

Execute batch/parallel workflows.

## Usage

```bash
sdqctl flow workflows/*.conv
sdqctl flow workflows/*.conv --parallel 4
sdqctl flow workflows/*.conv --continue-on-error
```

## Key Options

| Option | Description |
|--------|-------------|
| `--parallel, -p` | Parallel execution limit |
| `--adapter` | AI adapter override |
| `--continue-on-error` | Continue if a workflow fails |
| `--output-dir` | Directory for output files |
| `--dry-run` | Preview without executing |
| `--json` | JSON output format |

## Examples

```bash
# Run all workflows sequentially
sdqctl flow workflows/*.conv

# Parallel execution (4 at a time)
sdqctl flow workflows/*.conv --parallel 4

# Continue on errors
sdqctl flow workflows/*.conv --continue-on-error

# Dry run
sdqctl flow workflows/*.conv --dry-run
```
""",

    "show": """
# sdqctl show

Display a parsed ConversationFile.

## Usage

```bash
sdqctl show workflow.conv
```

## Output

Shows:
- Original file content with syntax highlighting
- Parsed representation:
  - model, adapter, mode
  - max_cycles, validation_mode
  - context_files, context_limit
  - prompts (with previews)
  - output configuration

## Use Cases

- Debug workflow parsing issues
- Verify directive interpretation
- Inspect context patterns before execution

## Example

```bash
sdqctl show workflows/security-audit.conv
```

Output shows both the raw `.conv` file and its parsed structure.
"""
}
