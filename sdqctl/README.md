# sdqctl

**Software Defined Quality Control** - Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

## Features

- 🔄 **Declarative workflows** - ConversationFile format (.conv) for reproducible AI interactions
- 🔌 **Vendor agnostic** - Swap AI providers without changing workflows
- 📊 **Context management** - Automatic tracking and compaction
- ✅ **Checkpointing** - Save/resume long-running workflows
- ⚡ **Batch execution** - Parallel workflow execution

## Installation

```bash
# Basic installation
pip install -e .

# With Copilot SDK support
pip install -e ".[copilot]"

# With all AI providers
pip install -e ".[all]"
```

## Quick Start

```bash
# Initialize in your project
sdqctl init

# Run a simple prompt
sdqctl run "Audit authentication module for security issues"

# Run a workflow file
sdqctl run workflows/security-audit.conv

# Multi-cycle workflow with compaction
sdqctl cycle workflows/migration.conv --max-cycles 5

# Batch execution
sdqctl flow workflows/*.conv --parallel 4

# Check status
sdqctl status
```

## ConversationFile Format

ConversationFiles (`.conv`) are declarative workflow definitions:

```dockerfile
# security-audit.conv
MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 1

CONTEXT @lib/auth/*.js
CONTEXT @tests/auth.test.js

CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

PROMPT Analyze authentication for security vulnerabilities.
PROMPT Generate a report with severity ratings.

OUTPUT-FORMAT markdown
OUTPUT-FILE security-report.md
```

### Directives

| Directive | Purpose |
|-----------|---------|
| `MODEL` | AI model to use |
| `ADAPTER` | AI provider (copilot, claude, openai, mock) |
| `MODE` | Execution mode (audit, read-only, full) |
| `MAX-CYCLES` | Maximum iteration cycles |
| `CONTEXT` | Include file/pattern |
| `CONTEXT-LIMIT` | Context window threshold |
| `ON-CONTEXT-LIMIT` | Action when limit reached (compact, stop) |
| `PROLOGUE` | Prepend to each prompt (inline or @file) |
| `EPILOGUE` | Append to each prompt (inline or @file) |
| `PROMPT` | Prompt to send (runs LLM conversation cycle) |
| `RUN` | Execute shell command |
| `RUN-ON-ERROR` | Behavior on command failure (stop, continue) |
| `RUN-OUTPUT` | When to include output (always, on-error, never) |
| `RUN-OUTPUT-LIMIT` | Max output chars (10K, 50K, 1M, none) |
| `RUN-ENV` | Set environment variable (KEY=value) |
| `RUN-TIMEOUT` | Command timeout (30, 30s, 2m) |
| `RUN-CWD` | Working directory for RUN commands |
| `ALLOW-SHELL` | Enable shell features like pipes (true/false) |
| `PAUSE` | Checkpoint and exit for human review |
| `CHECKPOINT-AFTER` | When to checkpoint (each-cycle, each-prompt) |
| `COMPACT-PRESERVE` | What to preserve during compaction |
| `HEADER` | Prepend to output (inline or @file) |
| `FOOTER` | Append to output (inline or @file) |
| `OUTPUT-FORMAT` | Output format (markdown, json) |
| `OUTPUT-FILE` | Output destination |

### Template Variables

Available in PROLOGUE, EPILOGUE, HEADER, FOOTER, PROMPT, and OUTPUT paths:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{DATE}}` | ISO date | 2026-01-21 |
| `{{DATETIME}}` | ISO datetime | 2026-01-21T12:00:00 |
| `{{WORKFLOW_NAME}}` | Workflow filename (stem) | security-audit |
| `{{WORKFLOW_PATH}}` | Full path to workflow | /path/to/security-audit.conv |
| `{{COMPONENT_NAME}}` | Component name (without extension) | auth |
| `{{COMPONENT_PATH}}` | Full path to component | /path/to/auth.py |
| `{{COMPONENT_DIR}}` | Parent directory of component | /path/to |
| `{{COMPONENT_TYPE}}` | Type from discovery | plugin, api |
| `{{ITERATION_INDEX}}` | Current iteration (1-based) | 3 |
| `{{ITERATION_TOTAL}}` | Total iterations | 15 |
| `{{CYCLE_NUMBER}}` | Current cycle (cycle command) | 2 |
| `{{CYCLE_TOTAL}}` | Total cycles (cycle command) | 5 |
| `{{GIT_BRANCH}}` | Current git branch | main |
| `{{GIT_COMMIT}}` | Short commit SHA | abc1234 |
| `{{CWD}}` | Current working directory | /home/user/project |

### Prompt/Output Injection

Inject consistent content into prompts or output:

```dockerfile
# Prepend date context to every prompt
PROLOGUE Current date: {{DATE}}
PROLOGUE @templates/5-facet-context.md

# Append reminder to every prompt
EPILOGUE Remember to update progress.md

# Add headers/footers to output
HEADER # Analysis Report - {{WORKFLOW_NAME}}
FOOTER ---\nGenerated: {{DATETIME}} by sdqctl
```

CLI options:
```bash
sdqctl run workflow.conv \
  --prologue "Date: 2026-01-21" \
  --epilogue @templates/footer.md \
  --header "# Report" \
  --footer @templates/disclaimer.md
```

### RUN Directive (Command Execution)

Execute shell commands during workflow:

```dockerfile
# Run verification tool, output goes to AI context
RUN python tools/verify_refs.py --json
PROMPT Analyze the verification results above

# Control error handling
RUN-ON-ERROR continue
RUN make test

# Only include output on failure
RUN-OUTPUT on-error
RUN npm run lint
```

#### Security: Shell Mode

By default, RUN commands are executed **without a shell** for security (no shell injection):

```dockerfile
# Safe: parsed as ["echo", "hello", "world"]
RUN echo hello world

# To enable shell features (pipes, redirects, variables):
ALLOW-SHELL true
RUN cat data.json | jq '.items[]' > output.txt
```

#### Environment Variables

Set environment variables for RUN commands:

```dockerfile
RUN-ENV API_KEY=secret123
RUN-ENV DEBUG=1
RUN ./deploy.sh
```

#### Output Limits

Limit captured output to prevent context bloat:

```dockerfile
RUN-OUTPUT-LIMIT 10K    # Max 10,000 characters
RUN python long_test.py
```

Supported formats: `10K`, `50K`, `1M`, `100000`, `none` (unlimited).

#### Timeout

Set command timeout (default: 60 seconds):

```dockerfile
RUN-TIMEOUT 2m          # 2 minutes
RUN npm run build
```

#### Working Directory

Set working directory for RUN commands (paths relative to workflow file):

```dockerfile
RUN-CWD ./backend       # Relative to workflow location
RUN npm test            # Runs in ./backend directory
```

#### Auto-Checkpoint on Failure

When a RUN command fails with `RUN-ON-ERROR stop` (default), sdqctl automatically saves a checkpoint containing all captured output. This preserves debugging context even on failure.

### Human-in-the-Loop with PAUSE

The `PAUSE` directive creates a checkpoint and exits, allowing human review before continuing:

```dockerfile
# Phase 1: AI analysis
PROMPT Analyze codebase for security issues.
PROMPT Generate findings report.

# Human reviews findings
PAUSE "Review findings before generating remediation plan"

# Phase 2: Runs after human resumes
PROMPT Generate remediation plan based on findings.
```

Resume with:
```bash
sdqctl resume ~/.sdqctl/sessions/<session-id>/pause.json

# List available checkpoints
sdqctl resume --list

# Preview what would be resumed (dry run)
sdqctl resume pause.json --dry-run

# JSON output for scripting
sdqctl resume --list --json
sdqctl resume pause.json --dry-run --json
```

## Commands

### `sdqctl run`

Execute a single prompt or workflow:

```bash
sdqctl run "Analyze this codebase"
sdqctl run workflow.conv --adapter copilot
sdqctl run workflow.conv --dry-run
sdqctl run workflow.conv --render-only  # Preview prompts, no AI calls
```

### `sdqctl cycle`

Multi-cycle execution with compaction:

```bash
sdqctl cycle workflow.conv --max-cycles 5
sdqctl cycle workflow.conv --checkpoint-dir ./checkpoints
sdqctl cycle workflow.conv -n 3 --render-only  # Preview all cycles
```

### `sdqctl render`

Render workflow prompts without executing (no AI calls):

```bash
# Basic render to stdout
sdqctl render workflow.conv

# Render with multiple cycles
sdqctl render workflow.conv -n 3

# JSON output for tooling
sdqctl render workflow.conv --json

# Render to file
sdqctl render workflow.conv -o rendered.md

# Fresh mode with separate files per cycle
sdqctl render workflow.conv -s fresh -n 3 -o rendered/

# Render specific cycle or prompt
sdqctl render workflow.conv --cycle 2
sdqctl render workflow.conv --prompt 1

# Add extra prologues/epilogues
sdqctl render workflow.conv --prologue "Date: 2026-01-22"
```

The render command produces fully-resolved prompts with all context files, 
template variables (`{{DATE}}`, `{{CYCLE_NUMBER}}`, etc.), prologues, and 
epilogues expanded. Useful for:
- Debugging template issues before running expensive AI calls
- Using sdqctl as a prompt templating engine
- CI/CD validation of workflow content

### `sdqctl flow`

Batch/parallel execution:

```bash
sdqctl flow workflows/*.conv --parallel 4
sdqctl flow workflows/*.conv --continue-on-error
```

### `sdqctl apply`

Apply a workflow to multiple components with progress tracking:

```bash
# Apply workflow to all plugins
sdqctl apply workflow.conv --components "lib/plugins/*.js"

# With progress file
sdqctl apply workflow.conv --components "src/**/*.ts" --progress progress.md

# Parallel execution
sdqctl apply workflow.conv --components "lib/*.js" --parallel 4 --output-dir reports/
```

#### Progress File Format

The `--progress` option writes a markdown file tracking iteration status:

```markdown
## Iteration Progress

Started: 2026-01-21T09:30:00

| Component | Status | Output | Duration |
|-----------|--------|--------|----------|
| module1.js | ✅ Done | reports/module1.md | 12.3s |
| module2.js | 🔄 Running | - | - |
| module3.js | ⏳ Pending | - | - |
| module4.js | ❌ Failed | - | 5.2s |

**Summary:** 1/4 complete, 1 running, 1 pending, 1 failed
```

Status indicators:
- ✅ Done - Component processed successfully
- 🔄 Running - Currently being processed
- ⏳ Pending - Waiting to be processed
- ❌ Failed - Processing failed

### `sdqctl status`

Show session and system status:

```bash
sdqctl status
sdqctl status --adapters
sdqctl status --sessions
```

## Adapters

| Adapter | Package | Description |
|---------|---------|-------------|
| `mock` | Built-in | Testing adapter |
| `copilot` | `github-copilot-sdk` | GitHub Copilot CLI |
| `claude` | `anthropic` | Anthropic Claude |
| `openai` | `openai` | OpenAI GPT |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check sdqctl/
```

## License

MIT
