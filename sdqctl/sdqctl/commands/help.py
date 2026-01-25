"""
sdqctl help - Comprehensive help system.

Usage:
    sdqctl help                    # Overview
    sdqctl help <command>          # Command help (run, cycle, flow, etc.)
    sdqctl help <topic>            # Topic help (directives, adapters, workflow)
"""

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()

# Topic documentation
TOPICS = {
    "directives": """
# ConversationFile Directives

Directives control workflow behavior in `.conv` files.

## Core Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `MODEL` | AI model to use | `MODEL gpt-4` |
| `ADAPTER` | AI provider | `ADAPTER copilot` |
| `MODE` | Execution mode | `MODE audit` |
| `MAX-CYCLES` | Maximum iterations | `MAX-CYCLES 5` |
| `SESSION-NAME` | Named session for resumability | `SESSION-NAME audit-2026-01` |
| `PROMPT` | Prompt to send | `PROMPT Analyze the code` |

## Model Requirements (Abstract Selection)

| Directive | Purpose | Example |
|-----------|---------|---------|
| `MODEL-REQUIRES` | Capability requirement | `MODEL-REQUIRES context:50k` |
| `MODEL-PREFERS` | Soft preference (hint) | `MODEL-PREFERS vendor:anthropic` |
| `MODEL-POLICY` | Resolution strategy | `MODEL-POLICY cheapest` |

Requirements: `context:Nk`, `tier:economy|standard|premium`, `speed:fast|standard|deliberate`, `capability:code|reasoning|general`

## Context Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `CONTEXT` | Include file/pattern | `CONTEXT @lib/*.js` |
| `CONTEXT-LIMIT` | Window threshold | `CONTEXT-LIMIT 80%` |
| `ON-CONTEXT-LIMIT` | Limit action | `ON-CONTEXT-LIMIT compact` |

## Injection Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `PROLOGUE` | Prepend to first prompt | `PROLOGUE Current date: {{DATE}}` |
| `EPILOGUE` | Append to last prompt | `EPILOGUE Update progress.md` |
| `HELP` | Inject help topics | `HELP directives workflow` |
| `HEADER` | Prepend to output | `HEADER # Report` |
| `FOOTER` | Append to output | `FOOTER ---` |

## RUN Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `RUN` | Execute shell command | `RUN pytest -v` |
| `RUN-RETRY` | Retry with AI fix | `RUN-RETRY 3 "Fix errors"` |
| `RUN-ON-ERROR` | Error behavior | `RUN-ON-ERROR continue` |
| `RUN-OUTPUT` | Output inclusion | `RUN-OUTPUT on-error` |
| `RUN-OUTPUT-LIMIT` | Max output chars | `RUN-OUTPUT-LIMIT 10K` |
| `RUN-TIMEOUT` | Command timeout | `RUN-TIMEOUT 2m` |
| `RUN-CWD` | Working directory | `RUN-CWD ./backend` |
| `RUN-ENV` | Environment variable | `RUN-ENV API_KEY=secret` |
| `ALLOW-SHELL` | Enable shell features | `ALLOW-SHELL true` |
| `ON-FAILURE` | Block on RUN failure | `ON-FAILURE` ... `END` |
| `ON-SUCCESS` | Block on RUN success | `ON-SUCCESS` ... `END` |

## Control Flow

| Directive | Purpose | Example |
|-----------|---------|---------|
| `PAUSE` | Checkpoint and exit | `PAUSE Review findings` |
| `CONSULT` | Pause for human consultation | `CONSULT Design Decisions` |
| `ELIDE` | Merge adjacent elements | `ELIDE` |
| `COMPACT` | Trigger compaction | `COMPACT` |
| `REQUIRE` | Pre-flight checks | `REQUIRE @file.py cmd:git` |
| `END` | End ON-FAILURE/ON-SUCCESS | `END` |

## Output Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `OUTPUT-FORMAT` | Output format | `OUTPUT-FORMAT markdown` |
| `OUTPUT-FILE` | Output destination | `OUTPUT-FILE report.md` |

See `sdqctl help workflow` for full ConversationFile examples.
""",

    "adapters": """
# AI Adapters

sdqctl supports multiple AI providers through adapters.

## Available Adapters

| Adapter | Package | Description |
|---------|---------|-------------|
| `mock` | Built-in | Testing adapter (no AI calls) |
| `copilot` | github-copilot-sdk | GitHub Copilot CLI |
| `claude` | anthropic | Anthropic Claude |
| `openai` | openai | OpenAI GPT models |

## Specifying Adapters

In ConversationFile:
```dockerfile
ADAPTER copilot
MODEL gpt-4
```

Via CLI:
```bash
sdqctl run workflow.conv --adapter copilot
```

## Checking Adapter Status

```bash
sdqctl status --adapters
```

## Mock Adapter

The `mock` adapter is useful for testing workflow mechanics without AI calls:

```bash
sdqctl run workflow.conv --adapter mock --verbose
```

Returns canned responses, allowing you to test:
- Workflow parsing and execution
- Checkpointing behavior
- Output file handling
""",

    "workflow": """
# ConversationFile Workflow Format

ConversationFiles (`.conv`) are declarative workflow definitions.

## Basic Structure

```dockerfile
# workflow.conv
MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 1

# Include context files
CONTEXT @lib/auth/*.js
CONTEXT @tests/auth.test.js

# Context management
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

# Prompts (run in sequence)
PROMPT Analyze authentication for security vulnerabilities.
PROMPT Generate a report with severity ratings.

# Output configuration
OUTPUT-FORMAT markdown
OUTPUT-FILE security-report.md
```

## Template Variables

Available in prompts and output paths:

| Variable | Example |
|----------|---------|
| `{{DATE}}` | 2026-01-21 |
| `{{DATETIME}}` | 2026-01-21T12:00:00 |
| `{{CYCLE_NUMBER}}` | 2 |
| `{{COMPONENT_NAME}}` | auth |
| `{{GIT_BRANCH}}` | main |

## Multi-Cycle Workflow

```dockerfile
MODEL gpt-4
MAX-CYCLES 3

PROLOGUE Iteration {{CYCLE_NUMBER}}/{{CYCLE_TOTAL}}
PROMPT Refine the implementation.
EPILOGUE Checkpoint progress.
```

## Human-in-the-Loop

```dockerfile
PROMPT Analyze security issues.
PAUSE "Review findings before remediation"
PROMPT Generate remediation plan.
```

Resume with: `sdqctl resume --list`

## Running Workflows

```bash
sdqctl run workflow.conv              # Single execution
sdqctl cycle workflow.conv -n 5       # Multi-cycle
sdqctl apply workflow.conv --components "lib/*.js"  # Apply to files
```
""",

    "variables": """
# Template Variables

Template variables are expanded in prompts, context, and output paths.

## Date/Time Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{DATE}}` | ISO date | 2026-01-21 |
| `{{DATETIME}}` | ISO datetime | 2026-01-21T12:00:00 |

## Workflow Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{WORKFLOW_NAME}}` | Workflow filename | security-audit |
| `{{WORKFLOW_PATH}}` | Full workflow path | /path/to/audit.conv |

## Component Variables (apply command)

| Variable | Description | Example |
|----------|-------------|---------|
| `{{COMPONENT_NAME}}` | Component name | auth |
| `{{COMPONENT_PATH}}` | Component path | /path/to/auth.py |
| `{{COMPONENT_DIR}}` | Parent directory | /path/to |
| `{{COMPONENT_TYPE}}` | Discovery type | plugin |

## Iteration Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ITERATION_INDEX}}` | Current iteration | 3 |
| `{{ITERATION_TOTAL}}` | Total iterations | 15 |
| `{{CYCLE_NUMBER}}` | Current cycle | 2 |
| `{{CYCLE_TOTAL}}` | Total cycles | 5 |

## Git Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{GIT_BRANCH}}` | Current branch | main |
| `{{GIT_COMMIT}}` | Short commit SHA | abc1234 |

## System Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{CWD}}` | Current directory | /home/user/project |
| `{{STOP_FILE}}` | Stop signal filename | STOPAUTOMATION-a1b2c3.json |
""",

    "context": """
# Context Management

sdqctl manages AI context windows automatically.

## Including Context Files

```dockerfile
# Single file
CONTEXT @lib/auth.js

# Glob pattern
CONTEXT @lib/**/*.js

# Optional (won't fail if missing)
CONTEXT-OPTIONAL @lib/legacy/*.js

# Exclude patterns
CONTEXT-EXCLUDE @node_modules/**
```

## Context Limits

```dockerfile
# Trigger action at 80% capacity
CONTEXT-LIMIT 80%

# Actions when limit reached
ON-CONTEXT-LIMIT compact    # Summarize and continue
ON-CONTEXT-LIMIT stop       # Stop and checkpoint
```

## Session Modes (cycle command)

```bash
sdqctl cycle workflow.conv --session-mode accumulate  # Grow context
sdqctl cycle workflow.conv --session-mode compact     # Summarize per cycle
sdqctl cycle workflow.conv --session-mode fresh       # Reset per cycle
```

## Compaction

```dockerfile
# Explicit compaction
COMPACT

# Preserve important content
COMPACT-PRESERVE @lib/core.js

# Add context before/after summary
COMPACT-PROLOGUE Previous context summary:
COMPACT-EPILOGUE Continue with the summarized context above.
```
""",

    "examples": """
# Workflow Examples

## Security Audit

```dockerfile
# security-audit.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

CONTEXT @lib/auth/*.js
CONTEXT @lib/crypto/*.js

PROMPT Analyze for security vulnerabilities.
PROMPT Focus on: authentication, input validation, encryption.
PROMPT Generate severity-rated findings.

OUTPUT-FILE security-report.md
```

## Test-Fix Loop

```dockerfile
# test-fix.conv
MODEL gpt-4
MAX-CYCLES 3

RUN pytest tests/
RUN-RETRY 2 "Analyze test failures and fix the code"

PROMPT Summarize fixes made this cycle.

CHECKPOINT-AFTER each-cycle
```

## Conditional Branching on RUN Result

```dockerfile
# deploy-with-fallback.conv
MODEL gpt-4

RUN npm test
ON-FAILURE
PROMPT Analyze test failures.
RUN git diff
PROMPT Fix the failing tests based on the diff.
END
ON-SUCCESS
PROMPT All tests passed! Deploy to staging.
RUN npm run deploy:staging
END

PROMPT Continue with next steps.
```

## Multi-Component Migration

```dockerfile
# migration.conv
MODEL gpt-4

PROLOGUE Component: {{COMPONENT_NAME}}
CONTEXT @{{COMPONENT_PATH}}

PROMPT Migrate this component to TypeScript.
PROMPT Update imports and add type annotations.

EPILOGUE Update progress.md with migration status.
OUTPUT-FILE reports/{{COMPONENT_NAME}}.md
```

Run with:
```bash
sdqctl apply migration.conv --components "lib/*.js" --progress progress.md
```

## Human Review Workflow

```dockerfile
# review-workflow.conv
MODEL gpt-4

PROMPT Analyze codebase for issues.
PAUSE "Review findings before proceeding"

PROMPT Generate remediation plan.
PAUSE "Approve remediation plan"

PROMPT Implement approved changes.
```

## Human Consultation Workflow

```dockerfile
# consultation-workflow.conv
MODEL gpt-4
SESSION-NAME feature-design

PROMPT Analyze this proposal and identify open questions.
  Add questions to the document's "## Open Questions" section.
CONSULT "Design Decisions"

PROMPT Now that the design decisions are resolved,
  update the proposal with the decisions and create tasks.
```

The CONSULT directive pauses like PAUSE, but when the human resumes
with `sdqctl sessions resume SESSION` (or `copilot --resume SESSION`),
the agent proactively presents open questions and guides the human
through answering them.
""",

    "validation": """
# Validation and Verification Workflow

sdqctl provides static verification commands that run **without AI calls**.

## Command Pipeline

```
validate → verify → render → run/cycle
(syntax)   (refs)   (preview)  (execute)
```

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `validate` | Check .conv syntax | `sdqctl validate workflow.conv` |
| `verify refs` | Check @-references | `sdqctl verify refs` |
| `verify links` | Check markdown links | `sdqctl verify links` |
| `verify traceability` | Check STPA traces | `sdqctl verify traceability` |
| `verify terminology` | Check term consistency | `sdqctl verify terminology` |
| `verify assertions` | Check assertion docs | `sdqctl verify assertions` |
| `verify all` | Run all verifiers | `sdqctl verify all --json` |
| `show` | Display parsed structure | `sdqctl show workflow.conv` |
| `render` | Preview prompts | `sdqctl render run workflow.conv` |
| `refcat` | Extract file content | `sdqctl refcat @file.py#L10-L50` |

## Decision Tree

- **Syntax/parse issues?** → `sdqctl validate`
- **Broken references?** → `sdqctl verify refs`
- **Broken links?** → `sdqctl verify links`
- **Missing traces?** → `sdqctl verify traceability`
- **Terminology issues?** → `sdqctl verify terminology`
- **Assertion docs?** → `sdqctl verify assertions`
- **See parsed structure?** → `sdqctl show`
- **Preview prompts?** → `sdqctl render run`
- **Extract file lines?** → `sdqctl refcat`

## VERIFY Directive

Run verification during workflow execution:

```dockerfile
VERIFY refs
VERIFY-ON-ERROR continue
VERIFY-OUTPUT on-error
```

## CI/CD Pattern

```bash
# Validate all workflows
for f in workflows/*.conv; do
  sdqctl validate "$f" --json || exit 1
done

# Verify references
sdqctl verify refs --json
```

## refcat Syntax

```
@path/file.py              # Full file
@path/file.py#L10-L50      # Lines 10-50
@path/file.py#L10          # Single line
@path/file.py#L10-         # Line 10 to EOF
alias:path/file.py#L10     # Cross-repo alias
```

See `docs/VALIDATION-WORKFLOW.md` for comprehensive guide.
""",

    "ai": """
# Guidance for AI Workflow Authors

When authoring sdqctl workflows, follow these principles.

## 1. Context Window Mental Model

Think of conversation files as **describing how context windows fit over workflow steps**,
not as containers for detailed specifications.

The .conv file orchestrates the *flow* of work. Documentation files hold the *details*.

❌ **Anti-pattern**: Embedding specifications in the .conv file
```dockerfile
PROMPT ## Phase 1: Implement Feature X
  The feature should:
  - Support format A with fields x, y, z
  - Handle error cases: E1, E2, E3
  - Follow pattern from lib/similar.py lines 45-120
  ... 50 more lines of spec ...
```

✅ **Pattern**: Reference documentation deliverables
```dockerfile
# Small, critical file - OK to inject
CONTEXT @proposals/FEATURE-X.md

# Let agent read details on demand
PROMPT Implement Feature X according to the design in proposals/FEATURE-X.md
```

## 2. Documentation Reading Order

**For workflow authoring:**
1. `sdqctl help workflow` - Basic structure
2. `sdqctl help directives` - All directives
3. `sdqctl help examples` - Common patterns

**For advanced patterns:**
- `docs/SYNTHESIS-CYCLES.md` - Iterative refinement workflows
- `docs/CONTEXT-MANAGEMENT.md` - Token efficiency strategies
- `docs/QUIRKS.md` - Surprising behaviors to avoid
- `docs/WORKFLOW-DESIGN.md` - Deep dive on conversation file design

## 3. Key Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Hint, don't inject** | Agent reads files on demand, saving tokens |
| **Name for action** | Filename influences agent role (use verbs) |
| **Specs in docs** | Put details in .md files, reference from .conv |
| **ELIDE for efficiency** | Merge RUN output with prompts in one turn |
| **Fresh mode for edits** | Agent sees file changes between cycles |
| **COMPACT between phases** | Free context before synthesis |

## 4. Workflow Structure Template

```dockerfile
# [action-verb]-[noun].conv - Brief description
MODEL gpt-4
ADAPTER copilot
MODE implement    # or: audit, read-only
MAX-CYCLES 3

# Role clarification (prevents passive interpretation)
PROLOGUE You are an implementation assistant. Edit files directly.
PROLOGUE Session: {{DATE}} | Branch: {{GIT_BRANCH}}

# Small critical context only
CONTEXT @proposals/DESIGN.md

# Cycle 1: Analyze
PROMPT Review the design and select one task to implement.

# Cycle 2: Implement
PROMPT Implement the selected task. Run tests to verify.

COMPACT

# Cycle 3: Document
PROMPT Summarize changes and update docs.

OUTPUT-FILE reports/{{DATE}}-progress.md
```

## 5. Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `CONTEXT @lib/**/*.py` | Hint at paths, let agent read |
| Naming file `tracker.conv` | Use `implement-fixes.conv` |
| 50-line PROMPT blocks | Move specs to .md files |
| No COMPACT in long workflows | Add between phases |
| Hardcoded commit messages | Let agent write them |

## 6. Getting Templates

```bash
# Show workflow examples
sdqctl help examples

# Render existing workflow as template
sdqctl render run examples/workflows/security-audit.conv

# Preview what would be sent to AI
sdqctl render cycle workflow.conv -n 3
```

See also: `sdqctl help workflow`, `docs/GETTING-STARTED.md`
"""
}

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


def get_overview() -> str:
    """Return overview help text."""
    return """
# sdqctl - Software Defined Quality Control

Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

## Quick Start

```bash
sdqctl init                          # Initialize in project
sdqctl run "Audit auth module"       # Run single prompt
sdqctl run workflow.conv             # Run workflow file
sdqctl cycle workflow.conv -n 5      # Multi-cycle execution
sdqctl status                        # Check status
```

## Commands

| Command | Description |
|---------|-------------|
| `run` | Execute single prompt or workflow |
| `cycle` | Multi-cycle workflow execution |
| `flow` | Batch/parallel workflows |
| `apply` | Apply workflow to multiple components |
| `render` | Preview prompts (no AI calls) |
| `verify` | Static verification |
| `validate` | Validate ConversationFile |
| `show` | Display parsed ConversationFile |
| `status` | Show session status |
| `sessions` | Manage conversation sessions |
| `init` | Initialize project |
| `resume` | Resume paused workflow |

## Topics

| Topic | Description |
|-------|-------------|
| `ai` | Workflow authoring guidance for AI agents |
| `directives` | ConversationFile directive reference |
| `adapters` | AI provider configuration |
| `workflow` | ConversationFile format guide |
| `variables` | Template variable reference |
| `context` | Context management guide |
| `examples` | Example workflows |
| `validation` | Static verification workflow guide |

## Getting Help

```bash
sdqctl help                  # This overview
sdqctl help run              # Command help
sdqctl help directives       # Topic help
sdqctl <command> --help      # Click's built-in help
```

## Documentation

- README: /home/bewest/src/copilot-do-proposal/sdqctl/README.md
- Docs: /home/bewest/src/copilot-do-proposal/sdqctl/docs/
"""


@click.command("help")
@click.argument("topic", required=False)
@click.option("--list", "-l", "list_topics", is_flag=True, help="List available topics")
def help_cmd(topic: str, list_topics: bool) -> None:
    """Show help for commands and topics.
    
    \b
    Examples:
      sdqctl help              # Overview
      sdqctl help run          # Command help
      sdqctl help directives   # Topic help
      sdqctl help --list       # List all topics
    """
    if list_topics:
        _list_topics()
        return
    
    if topic is None:
        # Show overview
        console.print(Markdown(get_overview()))
        return
    
    topic_lower = topic.lower()
    
    # Check if it's a command
    if topic_lower in COMMAND_HELP:
        console.print(Markdown(COMMAND_HELP[topic_lower]))
        return
    
    # Check if it's a topic
    if topic_lower in TOPICS:
        console.print(Markdown(TOPICS[topic_lower]))
        return
    
    # Unknown topic
    console.print(f"[yellow]Unknown topic: {topic}[/yellow]\n")
    _list_topics()


def _list_topics() -> None:
    """List available help topics."""
    console.print("\n[bold]Commands[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="dim")
    
    for cmd in sorted(COMMAND_HELP.keys()):
        desc = COMMAND_HELP[cmd].split("\n")[2].strip("# ")  # First heading
        table.add_row(cmd, desc)
    
    console.print(table)
    
    console.print("\n[bold]Topics[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="dim")
    
    topic_descriptions = {
        "directives": "ConversationFile directive reference",
        "adapters": "AI provider configuration",
        "workflow": "ConversationFile format guide",
        "variables": "Template variable reference",
        "context": "Context management guide",
        "examples": "Example workflows",
        "ai": "Workflow authoring guidance for AI agents",
        "validation": "Static verification workflow guide",
    }
    
    for topic in sorted(TOPICS.keys()):
        table.add_row(topic, topic_descriptions.get(topic, ""))
    
    console.print(table)
    console.print("\nUsage: sdqctl help <command|topic>")
