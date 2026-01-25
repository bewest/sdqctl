# sdqctl Command Reference

Complete reference for all sdqctl CLI commands.

---

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `run` | Execute single workflow | `sdqctl run workflow.conv` |
| `iterate` | Multi-cycle iteration | `sdqctl iterate workflow.conv -n 5` |
| `apply` | Apply to multiple components | `sdqctl apply workflow.conv -c "lib/*.js"` |
| `flow` | Batch/parallel execution | `sdqctl flow workflows/*.conv --parallel 4` |
| `render` | Preview prompts (no AI) | `sdqctl render run workflow.conv` |
| `verify` | Static verification | `sdqctl verify refs` |
| `refcat` | Extract file content | `sdqctl refcat @file.py#L10-L50` |
| `sessions` | Session management | `sdqctl sessions list` |
| `resume` | Resume paused workflow | `sdqctl resume checkpoint.json` |
| `status` | System/adapter status | `sdqctl status --adapters` |
| `artifact` | Artifact ID utilities | `sdqctl artifact next REQ` |
| `validate` | Syntax validation | `sdqctl validate workflow.conv` |
| `show` | Display parsed workflow | `sdqctl show workflow.conv` |
| `init` | Initialize project | `sdqctl init` |
| `help` | Built-in help | `sdqctl help directives` |

---

## Global Options

```bash
sdqctl [OPTIONS] COMMAND [ARGS]...
```

| Option | Description |
|--------|-------------|
| `-v` | INFO level (progress with context %) |
| `-vv` | DEBUG level (streaming responses) |
| `-vvv` | TRACE level (tool calls, reasoning) |
| `-q` | Quiet mode (errors only) |
| `-P` | Show expanded prompts on stderr |
| `--json-errors` | Output errors as JSON (for CI) |
| `--version` | Show version |
| `--help` | Show help |

---

## run

Execute a single prompt or ConversationFile.

```bash
sdqctl run TARGET [OPTIONS]
```

**Examples:**
```bash
# Inline prompt
sdqctl run "Audit authentication module"

# Workflow file
sdqctl run workflow.conv --adapter copilot

# With context injection
sdqctl run workflow.conv --prologue "Date: 2026-01-21" --epilogue @footer.md

# Preview only (no AI calls)
sdqctl run workflow.conv --render-only

# File access control
sdqctl run "Analyze code" --allow-files "./lib/*" --deny-files "./lib/special"
```

**Key Options:**
| Option | Description |
|--------|-------------|
| `-a, --adapter` | AI adapter (copilot, claude, openai, mock) |
| `-m, --model` | Model override |
| `--prologue` | Prepend to prompts (inline or @file) |
| `--epilogue` | Append to prompts (inline or @file) |
| `--header` | Prepend to output |
| `--footer` | Append to output |
| `--render-only` | Preview prompts without AI calls |
| `--dry-run` | Show what would happen |
| `--allow-files` | Restrict file access |
| `--deny-files` | Exclude files from access |

---

## iterate

Run multi-cycle workflow with compaction and checkpointing.

```bash
sdqctl iterate [WORKFLOW] [OPTIONS]
```

**Examples:**
```bash
# 5 cycles with default settings
sdqctl iterate workflow.conv -n 5

# Fresh session each cycle (for file editing workflows)
sdqctl iterate workflow.conv -n 3 --session-mode fresh

# Compact between cycles (token management)
sdqctl iterate workflow.conv -n 10 --session-mode compact

# From pre-rendered JSON
sdqctl iterate --from-json rendered.json

# Pipeline mode
sdqctl render iterate workflow.conv --json | jq '...' | sdqctl iterate --from-json -
```

**Key Options:**
| Option | Description |
|--------|-------------|
| `-n, --max-cycles` | Number of cycles |
| `-s, --session-mode` | `accumulate`, `compact`, or `fresh` |
| `--from-json` | Execute from rendered JSON |
| `--checkpoint-dir` | Checkpoint directory |
| `--event-log` | Export SDK events to JSONL |
| `--infinite-sessions` | Enable SDK native compaction |
| `--compaction-threshold` | Background compaction threshold (%) |

**Session Modes:**
| Mode | Behavior |
|------|----------|
| `accumulate` | Context grows until limit (default) |
| `compact` | Summarize after each cycle |
| `fresh` | New session each cycle |

---

## apply

Apply a workflow to multiple components with variable substitution.

```bash
sdqctl apply WORKFLOW [OPTIONS]
```

**Examples:**
```bash
# Apply to all plugins
sdqctl apply audit.conv --components "lib/plugins/*.js"

# With progress tracking
sdqctl apply audit.conv -c "lib/*.js" --progress progress.md

# Parallel execution
sdqctl apply audit.conv -c "lib/**/*.js" --parallel 4 --output-dir reports/

# From discovery file
sdqctl apply audit.conv --from-discovery components.json
```

**Template Variables:**
| Variable | Description |
|----------|-------------|
| `{{COMPONENT_PATH}}` | Full path to component |
| `{{COMPONENT_NAME}}` | Filename without extension |
| `{{COMPONENT_DIR}}` | Parent directory |
| `{{ITERATION_INDEX}}` | Current iteration (1-based) |
| `{{ITERATION_TOTAL}}` | Total iterations |

---

## flow

Execute batch/parallel workflows across multiple files.

```bash
sdqctl flow PATTERNS... [OPTIONS]
```

**Use Cases:**
- Run the same workflow on many components in parallel
- Batch-process multiple workflow files
- CI/CD integration for automated analysis

**Key Options:**
| Option | Description |
|--------|-------------|
| `-p, --parallel N` | Run up to N workflows concurrently |
| `--continue-on-error` | Don't stop if a workflow fails |
| `--dry-run` | Show what would run without executing |
| `-o, --output-dir PATH` | Collect all outputs in a directory |

**Examples:**
```bash
# Run all workflows in directory
sdqctl flow workflows/*.conv

# Parallel execution (4 at a time)
sdqctl flow workflows/*.conv --parallel 4

# Continue on error (useful for CI)
sdqctl flow workflows/*.conv --continue-on-error

# Output to directory with JSON summary
sdqctl flow workflows/*.conv -o reports/ --json

# Preview what would run
sdqctl flow workflows/*.conv --dry-run

# With shared prologue/epilogue
sdqctl flow audits/*.conv --prologue @context.md --parallel 2
```

> **Tip:** Use `flow` for batch operations. Use `apply` when iterating
> the same workflow across components with variable expansion.

---

## render

Render workflow prompts without executing (no AI calls).

```bash
sdqctl render SUBCOMMAND [OPTIONS]
```

**Subcommands:**
| Subcommand | Purpose |
|------------|---------|
| `render run` | Single-cycle render |
| `render iterate` | Multi-cycle render |
| `render apply` | Per-component render |

**Examples:**
```bash
# Render single cycle
sdqctl render run workflow.conv

# Show file refs only (faster)
sdqctl render run workflow.conv --plan

# JSON output for pipeline
sdqctl render iterate workflow.conv -n 3 --json

# Render specific prompt
sdqctl render run workflow.conv --prompt 2
```

---

## verify

Static verification suite for workflows and documentation.

```bash
sdqctl verify SUBCOMMAND [OPTIONS]
```

**Subcommands:**
| Subcommand | Purpose |
|------------|---------|
| `refs` | Verify @-references resolve |
| `links` | Verify markdown links |
| `traceability` | STPA/IEC 62304 traces |
| `terminology` | Glossary consistency |
| `assertions` | Assertion documentation |
| `trace` | Single trace link |
| `coverage` | Traceability coverage |
| `all` | Run all verifications |

**Examples:**
```bash
# Check @-references
sdqctl verify refs

# All verifications with JSON output
sdqctl verify all --json

# Specific directory
sdqctl verify refs -p examples/workflows/

# Suggest fixes for broken refs
sdqctl verify refs --suggest-fixes
```

---

## refcat

Extract file content with line-level precision for context injection.

```bash
sdqctl refcat [REFS]... [OPTIONS]
```

**Reference Formats:**
| Format | Description |
|--------|-------------|
| `@path/file.py` | Entire file |
| `@path/file.py#L10` | Single line |
| `@path/file.py#L10-L50` | Line range |
| `@path/file.py#L10-` | Line to end |
| `@path/file.py#/pattern/` | Pattern search |
| `alias:path/file.py#L10` | With alias |
| `@docs/**/*.md` | Glob pattern |

**Examples:**
```bash
# Extract specific lines
sdqctl refcat @sdqctl/core/context.py#L182-L194

# Multiple refs
sdqctl refcat @file1.py#L10 @file2.py#L20-L30

# With alias (from workspace.lock.json)
sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200

# JSON output
sdqctl refcat @file.py#L10-L50 --json

# Validate without output
sdqctl refcat @file.py#L10-L50 --validate-only
```

---

## sessions

Manage conversation sessions (server-side session state).

```bash
sdqctl sessions SUBCOMMAND [OPTIONS]
```

**Subcommands:**
| Subcommand | Purpose |
|------------|---------|
| `list` | List all sessions |
| `delete` | Delete a session |
| `cleanup` | Remove old sessions |
| `resume` | Resume a session |

**Examples:**
```bash
# List all sessions
sdqctl sessions list

# JSON format
sdqctl sessions list --format json

# Filter by pattern
sdqctl sessions list --filter "audit-*"

# Delete session
sdqctl sessions delete SESSION_ID --force

# Clean up old sessions
sdqctl sessions cleanup --older-than 7d --dry-run
sdqctl sessions cleanup --older-than 30d

# Resume session
sdqctl sessions resume my-session
```

> **Note:** `sessions resume` restores **SDK conversation history** (server-side).
> For resuming from a local **PAUSE checkpoint file**, see [`resume`](#resume).

---

## resume

Resume a paused workflow from a local checkpoint file.

```bash
sdqctl resume [CHECKPOINT] [OPTIONS]
```

> **Difference from `sessions resume`:**
> - `resume` loads a **local checkpoint file** created by the `PAUSE` directive
> - `sessions resume` restores **SDK session history** by session ID
> 
> Use `resume` for: workflow pauses, human-in-loop breaks, CONSULT responses  
> Use `sessions resume` for: continuing previous SDK conversations

**Examples:**
```bash
# Resume from checkpoint file
sdqctl resume ~/.sdqctl/sessions/abc123/pause.json

# List available checkpoints
sdqctl resume --list

# Preview what would resume
sdqctl resume checkpoint.json --dry-run
```

---

## status

Show session and system status.

```bash
sdqctl status [OPTIONS]
```

**Examples:**
```bash
# Basic status
sdqctl status

# Show available adapters
sdqctl status --adapters

# Show available models
sdqctl status --models

# Check authentication
sdqctl status --auth

# All details
sdqctl status --all

# JSON output
sdqctl status --all --json
```

---

## artifact

Artifact ID management for traceability documentation.

```bash
sdqctl artifact SUBCOMMAND [OPTIONS]
```

**Artifact Types:**
| Category | Types |
|----------|-------|
| STPA | `LOSS`, `HAZ`, `UCA`, `SC` |
| Requirements | `REQ`, `SPEC`, `TEST`, `GAP` |
| Development | `BUG`, `PROP`, `Q`, `IQ` |

**Examples:**
```bash
# Get next available ID
sdqctl artifact next REQ           # → REQ-001

# With category scope
sdqctl artifact next REQ-CGM       # → REQ-CGM-001
sdqctl artifact next UCA-BOLUS     # → UCA-BOLUS-001

# List existing artifacts
sdqctl artifact list REQ

# Rename and update references
sdqctl artifact rename REQ-001 REQ-AUTH-001
```

---

## validate

Validate ConversationFile syntax and references.

```bash
sdqctl validate WORKFLOW [OPTIONS]
```

**Examples:**
```bash
# Basic validation
sdqctl validate workflow.conv

# Allow missing context files
sdqctl validate workflow.conv --allow-missing

# Exclude patterns
sdqctl validate workflow.conv --exclude "*.yaml"

# Strict mode
sdqctl validate workflow.conv --strict

# Check MODEL-REQUIRES resolution (see ADAPTERS.md §Model Selection Guide)
sdqctl validate workflow.conv --check-model

# JSON output
sdqctl validate workflow.conv --json
```

---

## show

Display a parsed ConversationFile structure.

```bash
sdqctl show WORKFLOW
```

**Example:**
```bash
sdqctl show workflow.conv
```

---

## init

Initialize sdqctl in a project.

```bash
sdqctl init [NAME] [OPTIONS]
```

**Creates:**
- `.sdqctl.yaml` config file
- `workflows/` directory with examples
- `.github/copilot-instructions.md`
- `.github/skills/sdqctl-verify.md`

**Examples:**
```bash
# Initialize in current directory
sdqctl init

# With project name
sdqctl init my-project

# Skip GitHub Copilot files
sdqctl init --no-copilot

# Overwrite existing
sdqctl init --force
```

---

## help

Built-in help system.

```bash
sdqctl help [TOPIC]
```

**Examples:**
```bash
# Overview
sdqctl help

# Command help
sdqctl help run
sdqctl help iterate

# Topic help
sdqctl help directives
sdqctl help workflow
sdqctl help variables

# List all topics
sdqctl help --list
```

**Available Topics:**
- `directives` - ConversationFile directive reference
- `adapters` - AI provider configuration
- `workflow` - Workflow design patterns
- `variables` - Template variable reference
- `context` - Context management strategies
- `examples` - Example workflows

---

## See Also

- [GETTING-STARTED.md](GETTING-STARTED.md) - Quick start guide
- [ADAPTERS.md](ADAPTERS.md) - Adapter configuration and authentication
- [SECURITY-MODEL.md](SECURITY-MODEL.md) - Shell execution, path handling, CI/CD hardening
- [PHILOSOPHY.md](PHILOSOPHY.md) - Workflow design principles
- [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md) - Context strategies
- [IO-ARCHITECTURE.md](IO-ARCHITECTURE.md) - Stream handling
