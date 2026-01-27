# sdqctl

**Software Defined Quality Control** - Vendor-agnostic CLI for orchestrating AI-assisted development workflows.

## Motivation

Interactive AI coding assistants like GitHub Copilot CLI excel at **focused, single-spike work**—you enter plan mode, iterate through plan/do cycles, and emerge with a working feature. But real projects require **sustained multi-cycle work**: auditing 15 components, migrating 40 files, or iterating on a complex feature over 5-10 cycles.

Manual orchestration means:

- **20+ sessions** with repetitive setup
- **Manual context management** (when to compact? when to start fresh?)
- **No repeatability** (can't re-run the same workflow reliably)
- **No mid-run steering** (can't inject new priorities without stopping)

**sdqctl bridges this gap** with the `iterate` command—the primary workflow for AI-assisted development:

```bash
# Primary workflow: iterate with context injection
sdqctl iterate backlog.conv -n 8 \
  --session-mode accumulate \
  --introduction "Focus on P0-P2 Ready Queue items" \
  --prologue proposals/LIVE-BACKLOG.md
```

**Key patterns**:
- `--introduction` — First-cycle-only warmup (goals, focus areas)
- `--prologue` — Re-read before every cycle (live priorities, status updates)
- `LIVE-BACKLOG.md` — Edit during spot checks to steer longer runs

**Session modes** control context lifecycle:
- `accumulate` — Context grows; compact only at limit (iterative refinement, 70% of use)
- `compact` — Summarize after each cycle (long workflows, token economy)  
- `fresh` — New session each cycle, reload files (autonomous editing)

## Features

### Core Capabilities
- 🔄 **Declarative workflows** - ConversationFile format (.conv) for reproducible AI interactions
- 🔌 **Vendor agnostic** - Swap AI providers without changing workflows
- 📊 **Context management** - Automatic tracking, compaction, and token optimization
- ✅ **Checkpointing** - Save/resume long-running workflows
- ⚡ **Batch execution** - Parallel workflow execution across components

### Commands

**Primary command:**

| Command | Purpose | Documentation |
|---------|---------|---------------|
| `iterate` | Multi-cycle workflow execution (primary) | [COMMANDS.md](docs/COMMANDS.md#iterate) |

**Advanced commands:**

| Command | Purpose | Documentation |
|---------|---------|---------------|
| `run` | Single execution (deprecated, alias for `iterate -n 1`) | [COMMANDS.md](docs/COMMANDS.md#run) |
| `flow` | Batch/parallel workflows | [COMMANDS.md](docs/COMMANDS.md#flow) |
| `apply` | Apply workflow to multiple components | [COMMANDS.md](docs/COMMANDS.md#apply) |
| `render` | Preview prompts without AI execution | [COMMANDS.md](docs/COMMANDS.md#render) |
| `verify` | Static verification (refs, links, traceability) | [COMMANDS.md](docs/COMMANDS.md#verify) |
| `refcat` | Extract file content with line precision | [COMMANDS.md](docs/COMMANDS.md#refcat) |
| `sessions` | Session management (list, resume, cleanup) | [COMMANDS.md](docs/COMMANDS.md#sessions) |
| `status` | System and adapter status | [COMMANDS.md](docs/COMMANDS.md#status) |
| `validate` | Syntax validation for .conv files | [COMMANDS.md](docs/COMMANDS.md#validate) |
| `init` | Initialize sdqctl in a project | [COMMANDS.md](docs/COMMANDS.md#init) |
| `help` | Built-in help system | [COMMANDS.md](docs/COMMANDS.md#help) |

### Directives

ConversationFiles support 40+ directives for workflow control. See [DIRECTIVE-REFERENCE.md](docs/DIRECTIVE-REFERENCE.md) for complete documentation.

Key directive categories:
- **Context**: `CONTEXT`, `REFCAT`, `LSP` - inject file content and type definitions
- **Flow Control**: `PROMPT`, `CHECKPOINT`, `COMPACT`, `VERIFY` - structure workflow execution
- **Session**: `SESSION-NAME`, `SESSION-MODE`, `CONSULT` - manage AI sessions
- **Output**: `OUTPUT-FILE`, `OUTPUT-FORMAT`, `ALLOW-SHELL` - control results

### Documentation

| Document | Purpose |
|----------|---------|
| [GETTING-STARTED.md](docs/GETTING-STARTED.md) | Installation and first workflow |
| [COMMANDS.md](docs/COMMANDS.md) | Complete CLI reference |
| [DIRECTIVE-REFERENCE.md](docs/DIRECTIVE-REFERENCE.md) | All .conv directives |
| [PHILOSOPHY.md](docs/PHILOSOPHY.md) | Design principles, terminology |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure, extension points |
| [CONTEXT-MANAGEMENT.md](docs/CONTEXT-MANAGEMENT.md) | Token optimization strategies |
| [ADAPTERS.md](docs/ADAPTERS.md) | AI provider configuration |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [COLOPHON.md](docs/COLOPHON.md) | How sdqctl was built (dogfooding story) |

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

# Basic iteration (single cycle)
sdqctl iterate "Audit authentication module for security issues"

# Multi-cycle with context injection (primary workflow)
sdqctl iterate backlog.conv -n 5 \
  --introduction "Focus on high-priority items" \
  --prologue LIVE-BACKLOG.md

# Check status
sdqctl status
```

### Mid-Run Steering

During longer runs (`-n 5-10`), edit `LIVE-BACKLOG.md` to inject new priorities:

```markdown
<!-- LIVE-BACKLOG.md - edit while iterate runs -->
## Hot Items
- [ ] **URGENT**: Fix token leak spotted in cycle 3
- [ ] Refocus on error handling

## Skip Until Next Run
- Documentation updates
```

The `--prologue` file is re-read before each cycle, enabling real-time course correction.

## Verbosity & Output Control

sdqctl provides fine-grained control over output:

### Verbosity Levels (`-v`)

```bash
sdqctl iterate workflow.conv     # Default: final result only
sdqctl -v iterate workflow.conv  # Progress with context %
sdqctl -vv iterate workflow.conv # Streaming agent responses
sdqctl -vvv iterate workflow.conv # Full debug (tool calls, reasoning)
sdqctl -q iterate workflow.conv  # Quiet mode (errors only)
```

### Show Prompts (`-P` / `--show-prompt`)

See the exact prompts being sent to the AI (on stderr):

```bash
# Show prompts in terminal
sdqctl -P iterate workflow.conv

# Capture prompts to file while running
sdqctl -P iterate workflow.conv 2> prompts.log

# Full debugging: prompts + streaming response
sdqctl -vv -P iterate workflow.conv
```

Prompts are displayed with context:
```
[Cycle 2/5, Prompt 3/4] (ctx: 45%)
────────────────────────────────────────────────
You are analyzing a codebase for security issues.
...
────────────────────────────────────────────────
```

### Stream Separation

Output follows Unix conventions for pipeable workflows:
- **stdout**: Progress, agent responses (pipeable)
- **stderr**: Prompts (with `-P`), logs, errors

```bash
# Pipe agent output, see prompts on terminal
sdqctl -P iterate workflow.conv > results.md

# Capture both separately
sdqctl -P iterate workflow.conv > results.md 2> prompts.log
```

See [docs/IO-ARCHITECTURE.md](docs/IO-ARCHITECTURE.md) for full details.

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
| `PROLOGUE` | Prepend to first prompt of cycle (inline or @file) |
| `EPILOGUE` | Append to last prompt of cycle (inline or @file) |
| `HELP` | Inject help topics into prologues: `HELP directives workflow` |
| `REQUIRE` | Pre-flight checks: `REQUIRE @file.py cmd:git` |
| `PROMPT` | Prompt to send (runs LLM conversation cycle) |
| `RUN` | Execute shell command |
| `RUN-RETRY` | Retry with AI fix: `RUN-RETRY N "prompt"` |
| `RUN-ON-ERROR` | Behavior on command failure (stop, continue) |
| `ON-FAILURE` | Block executed if preceding RUN fails (non-zero exit) |
| `ON-SUCCESS` | Block executed if preceding RUN succeeds (zero exit) |
| `RUN-OUTPUT` | When to include output (always, on-error, never) |
| `RUN-OUTPUT-LIMIT` | Max output chars (10K, 50K, 1M, none) |
| `RUN-ENV` | Set environment variable (KEY=value) |
| `RUN-TIMEOUT` | Command timeout (30, 30s, 2m) |
| `RUN-CWD` | Working directory for RUN commands |
| `ALLOW-SHELL` | Enable shell features like pipes (true/false) |
| `PAUSE` | Checkpoint and exit for human review |
| `CONSULT` | Pause with proactive question presentation on resume |
| `SESSION-NAME` | Named session for easier resume: `SESSION-NAME my-feature` |
| `CHECKPOINT-AFTER` | When to checkpoint (each-cycle, each-prompt) |
| `COMPACT` | Trigger compaction (with optional preserve list) |
| `COMPACT-PRESERVE` | What to preserve during compaction |
| `COMPACT-PROLOGUE` | Content before compacted summary |
| `COMPACT-EPILOGUE` | Content after compacted summary |
| `INFINITE-SESSIONS` | Enable SDK native compaction (enabled/disabled) |
| `COMPACTION-MIN` | Min context % to trigger compaction (default: 30%) |
| `COMPACTION-THRESHOLD` | Background compaction threshold (default: 80%) |
| `COMPACTION-MAX` | Buffer exhaustion threshold (default: 95%) |
| `ELIDE` | Merge adjacent elements into single prompt |
| `VERIFY` | Run static verification (refs, traceability) |
| `VERIFY-ON-ERROR` | Behavior on verification failure (stop, continue) |
| `VERIFY-OUTPUT` | When to include output (always, on-error, never) |
| `VERIFY-LIMIT` | Max verification output chars |
| `HEADER` | Prepend to output (inline or @file) |
| `FOOTER` | Append to output (inline or @file) |
| `OUTPUT-FORMAT` | Output format (markdown, json) |
| `OUTPUT-FILE` | Output destination |
| `DEBUG` | Enable debug output |
| `DEBUG-INTENTS` | Log agent intents |
| `EVENT-LOG` | Log all SDK events to file |

### Template Variables

Available in PROLOGUE, EPILOGUE, HEADER, FOOTER, PROMPT, and OUTPUT paths:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{DATE}}` | ISO date | 2026-01-21 |
| `{{DATETIME}}` | ISO datetime | 2026-01-21T12:00:00 |
| `{{WORKFLOW_NAME}}` | Workflow filename (output paths only) | security-audit |
| `{{WORKFLOW_PATH}}` | Full path (output paths only) | /path/to/security-audit.conv |
| `{{__WORKFLOW_NAME__}}` | Workflow filename (explicit opt-in) | security-audit |
| `{{__WORKFLOW_PATH__}}` | Full path (explicit opt-in) | /path/to/security-audit.conv |
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
| `{{STOP_FILE}}` | Stop signal filename (for agent) | STOPAUTOMATION-a1b2c3.json |

> **Note:** `WORKFLOW_NAME` and `WORKFLOW_PATH` are excluded from prompts by default
> to avoid influencing agent behavior. Use `__WORKFLOW_NAME__` for explicit opt-in.
> See [SDK-LEARNINGS.md](docs/SDK-LEARNINGS.md#1-filename-semantics-influence-agent-role-q-001) for details.
>
> **Stop File (Enabled by Default):** Stop file instructions are automatically injected
> on the first prompt. The agent can create `{{STOP_FILE}}` to request human review.
> Use `--no-stop-file-prologue` to disable, or `--stop-file-nonce=VALUE` to override
> the random nonce. See [docs/LOOP-STRESS-TEST.md](docs/LOOP-STRESS-TEST.md#4-stop-file-detection).

### Prompt/Output Injection

Inject consistent content into prompts or output:

```dockerfile
# Prepend date context to every prompt
PROLOGUE Current date: {{DATE}}
PROLOGUE @templates/5-facet-context.md

# Append reminder to every prompt
EPILOGUE Remember to update progress.md

# Add headers/footers to output (WORKFLOW_NAME works here)
HEADER # Analysis Report
HEADER Generated: {{DATETIME}}
FOOTER ---\nGenerated by sdqctl
```

CLI options:
```bash
sdqctl iterate workflow.conv \
  --introduction "First-cycle warmup context" \
  --prologue LIVE-BACKLOG.md \
  --epilogue @templates/footer.md
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

#### RUN-RETRY (AI-Assisted Retry)

Enable automatic retry with AI fix when commands fail:

```dockerfile
RUN npm test
RUN-RETRY 3 "Fix the failing tests based on error output"
```

**Behavior**:
1. Run the command
2. If it fails, send error output + retry prompt to AI
3. AI analyzes errors and makes fixes
4. Run the command again
5. Repeat up to N times
6. If still failing after all retries, use `RUN-ON-ERROR` behavior

**Use cases**:
- Test-fix-retry loops
- Lint-fix cycles
- Build error recovery

```dockerfile
# Retry with custom prompt
RUN pytest tests/
RUN-RETRY 2 "Analyze the test failures and fix the code"

# Works with other RUN options
RUN-TIMEOUT 5m
RUN npm run build
RUN-RETRY 3 "Fix build errors"
```

**Note**: RUN-RETRY modifies the immediately preceding RUN directive. Each retry sends the error to the AI for analysis, consuming additional tokens.

### ELIDE Directive (Merge Adjacent Elements)

The `ELIDE` directive merges the element above with the element below into a single prompt, eliminating the agent turn between them. This is useful for:

- **Combining test output with fix instructions** - Agent sees test failures and instructions in one turn
- **Reducing token waste** - No meaningless intermediate "I see the output" responses
- **Faster workflows** - Skip unnecessary agent reasoning cycles

```dockerfile
# Without ELIDE: 3 agent turns (wasteful)
PROMPT Analyze test results.
RUN pytest -v
PROMPT Fix any failing tests.

# With ELIDE: 1 agent turn (efficient)
PROMPT Analyze test results.
RUN pytest -v
ELIDE
PROMPT Fix any failing tests.

# The agent receives a single merged prompt:
#   Analyze test results.
#   [test output from RUN]
#   Fix any failing tests.
```

Chained ELIDEs merge multiple elements:

```dockerfile
PROMPT Review the build output.
ELIDE
RUN npm run build
ELIDE
RUN npm test
ELIDE
PROMPT Fix any errors in the build or tests.
# All merged into a single prompt with both outputs
```

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

### `sdqctl iterate` (Primary Command)

The iterate command is the primary way to use sdqctl. It runs multi-cycle workflows with context injection and mid-run steering:

```bash
# Basic usage
sdqctl iterate workflow.conv -n 5

# Full workflow with context injection (recommended pattern)
sdqctl iterate backlog.conv -n 8 \
  --session-mode accumulate \
  --introduction "Focus on P0-P2 items from the Ready Queue" \
  --prologue LIVE-BACKLOG.md

# Preview without AI calls
sdqctl iterate workflow.conv -n 3 --render-only
```

**Key options:**

| Option | Purpose |
|--------|---------|
| `-n, --max-cycles` | Number of cycles to run |
| `--session-mode` | Context management: accumulate, compact, fresh |
| `--introduction` | First-cycle-only context (warmup, goals) |
| `--prologue` | Re-read before every cycle (live priorities) |
| `--epilogue` | Appended after each cycle |
| `--dry-run` | Validate without execution |
| `--render-only` | Preview prompts, no AI calls |

#### Session Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `accumulate` | Context grows, compact only at limit | Iterative refinement (70% of use) |
| `compact` | Summarize after each cycle | Long-running workflows |
| `fresh` | New session each cycle, reload files | Autonomous file editing |

```bash
# Accumulate mode (default): context builds across cycles
sdqctl iterate workflow.conv -n 5 --session-mode accumulate

# Fresh mode: each cycle sees file changes from previous cycles
sdqctl iterate workflow.conv -n 5 --session-mode fresh
```

#### Pipeline Input (`--from-json`)

Execute workflow from pre-rendered JSON, enabling external transformation:

```bash
# Round-trip: render, transform, execute
sdqctl render iterate workflow.conv --json \
  | jq '.cycles[0].prompts[0].resolved += " (modified)"' \
  | sdqctl iterate --from-json -
```

### `sdqctl run` (Deprecated)

> **Note:** `sdqctl run` is deprecated. It forwards to `sdqctl iterate -n 1`.

```bash
# These are equivalent:
sdqctl run workflow.conv
sdqctl iterate workflow.conv -n 1
```

### Advanced Commands

The following commands are available for specialized use cases.

#### `sdqctl render`

Render workflow prompts without executing (no AI calls). Now with subcommands:

```bash
# Render for run command (single cycle)
sdqctl render run workflow.conv
sdqctl render run workflow.conv --plan    # Show @file refs only
sdqctl render run workflow.conv --json    # JSON output

# Render for cycle command (multi-cycle)
sdqctl render iterate workflow.conv --max-cycles 5
sdqctl render iterate workflow.conv -n 3 -s fresh -o rendered/

# Render for apply command
sdqctl render apply workflow.conv --components "lib/*.js"

# Legacy (backwards compat)
sdqctl render file workflow.conv

# Common options
sdqctl render run workflow.conv -o rendered.md      # Output to file
sdqctl render run workflow.conv --cycle 2           # Specific cycle
sdqctl render run workflow.conv --prompt 1          # Specific prompt
sdqctl render run workflow.conv --prologue "Date: 2026-01-22"
```

**Modes:**
- `--plan` - Show `@file` references without expanding content (faster, overview)
- `--full` - Fully expand all content (default)

The render command produces fully-resolved prompts with all context files, 
template variables (`{{DATE}}`, `{{CYCLE_NUMBER}}`, etc.), prologues, and 
epilogues expanded. Useful for:
- Debugging template issues before running expensive AI calls
- Using sdqctl as a prompt templating engine
- CI/CD validation of workflow content

> **Note:** `--render-only` flag on `run` and `iterate` commands is deprecated.
> Use `sdqctl render run` or `sdqctl render iterate` instead.

#### `sdqctl flow`

Batch/parallel execution:

```bash
sdqctl flow workflows/*.conv --parallel 4
sdqctl flow workflows/*.conv --continue-on-error
```

#### `sdqctl apply`

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

#### `sdqctl verify`

Static verification suite for workflows and references. These commands run **without AI calls** and are safe for CI/CD pipelines.

> **📖 See Also**: [docs/VALIDATION-WORKFLOW.md](docs/VALIDATION-WORKFLOW.md) for comprehensive guidance on the validation pipeline (`validate` → `verify` → `render` → `run`).

```bash
# Verify @-references resolve to files
sdqctl verify refs

# Verify markdown links
sdqctl verify links

# Verify STPA traceability (UCA→SC→REQ→SPEC→TEST)
sdqctl verify traceability

# Verify terminology consistency (deprecated terms, capitalization)
sdqctl verify terminology

# Verify assertions have messages and trace IDs
sdqctl verify assertions

# Run all verifications
sdqctl verify all

# JSON output for scripting
sdqctl verify refs --json

# Verify specific directory
sdqctl verify refs -p examples/workflows/
```

#### VERIFY Directive (In-Workflow Verification)

Run verifications during workflow execution:

```dockerfile
# Verify all @-references before proceeding
VERIFY refs

# Verify markdown links
VERIFY links

# Verify STPA traceability chain
VERIFY traceability

# Verify terminology consistency
VERIFY terminology

# Verify assertions are documented
VERIFY assertions

# Control error handling
VERIFY-ON-ERROR continue
VERIFY refs

# Only include output on failure
VERIFY-OUTPUT on-error
VERIFY refs

# Combine with ELIDE to fix issues
VERIFY traceability
ELIDE
PROMPT Fix any traceability gaps found above.
```

#### `sdqctl refcat`

Extract file content with line-level precision for context injection:

```bash
# Extract specific lines
sdqctl refcat @path/file.py#L10-L50

# Single line
sdqctl refcat @path/file.py#L42

# Line to end of file
sdqctl refcat @path/file.py#L100-

# Pattern search (first match)
sdqctl refcat @path/file.py#/def my_func/

# Multiple refs
sdqctl refcat @file1.py#L10 @file2.py#L20-L30

# JSON output for scripting
sdqctl refcat @file.py#L10-L50 --json

# Validate refs without output
sdqctl refcat @file.py#L10-L50 --validate-only

# Without line numbers
sdqctl refcat @file.py#L10-L50 --no-line-numbers
```

Output format includes file origin and line numbers:

```markdown
## From: sdqctl/core/context.py:182-194 (relative to /home/user/project)
```python
182 |     def get_context_content(self) -> str:
183 |         """Get formatted context content..."""
...
```
```

For cross-repository workflows, use aliases:

```bash
# With alias (defined in ~/.sdqctl/aliases.yaml)
sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

**Cross-Repo Usage Patterns:**

```bash
# Compare implementations across projects
sdqctl refcat loop:Algorithm.swift#L50-100 aaps:DetermineBasalAdapter.kt#L30-80

# In .conv files - reference external code for analysis
REFCAT loop:LoopKit/Sources/Loop/Models/BolusEntry.swift#L1-50
REFCAT aaps:app/src/main/java/info/nightscout/androidaps/plugins/aps/loop/LoopPlugin.kt#L100-150
PROMPT Compare these bolus handling implementations.

# Using workspace.lock.json for project aliases
# Create workspace.lock.json in project root:
# {
#   "aliases": {
#     "loop": "/path/to/LoopKit",
#     "aaps": "/path/to/AndroidAPS"
#   }
# }
```

See `proposals/REFCAT-DESIGN.md` for full specification.

#### `sdqctl status`

Show session and system status:

```bash
sdqctl status
sdqctl status --adapters
sdqctl status --sessions
sdqctl status --models
sdqctl status --auth
```

#### `sdqctl sessions`

Manage conversation sessions:

```bash
# List all sessions
sdqctl sessions list
sdqctl sessions list --format json
sdqctl sessions list --filter "audit-*"

# Delete a session
sdqctl sessions delete SESSION_ID
sdqctl sessions delete SESSION_ID --force

# Clean up old sessions
sdqctl sessions cleanup --older-than 7d --dry-run
sdqctl sessions cleanup --older-than 30d
```

#### `sdqctl help`

Comprehensive help system:

```bash
sdqctl help                  # Overview
sdqctl help iterate          # Command help
sdqctl help directives       # Topic help
sdqctl help --list           # List all commands and topics
```

Available topics: `directives`, `adapters`, `workflow`, `variables`, `context`, `examples`

## Adapters

| Adapter | Package | Description |
|---------|---------|-------------|
| `mock` | Built-in | Testing adapter |
| `copilot` | `github-copilot-sdk` | GitHub Copilot CLI |
| `claude` | `anthropic` | Anthropic Claude |
| `openai` | `openai` | OpenAI GPT |

> **📖 Configuration**: See [docs/ADAPTERS.md](docs/ADAPTERS.md) for authentication, environment variables, and provider-specific options.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with markers
pytest -m integration       # Integration tests only (15 tests)
pytest -m "not slow"        # Skip slow tests (~1s faster)
pytest -m "not integration" # Unit tests only

# Lint
ruff check sdqctl/
```

## Roadmap

### Recently Completed

- ✅ **ON-FAILURE/ON-SUCCESS Blocks** - Conditional execution after RUN commands
- ✅ **All Quirks Resolved** - Q-013 tool name fix completes quirk backlog
- ✅ **REFCAT Command** - Extract file content with line ranges (`@file.py#L10-L50`) for precise context injection
- ✅ **VERIFY Directive** - Static verification during workflows ([docs](#verify-directive-in-workflow-verification))
- ✅ **STPA Workflow Templates** - Safety analysis workflows (`examples/workflows/stpa/`)
- ✅ **RUN-RETRY Directive** - AI-assisted retry on command failure ([docs](#run-retry-ai-assisted-retry))
- ✅ **INCLUDE Directive** - Compose workflows from reusable fragments
- ✅ **REQUIRE Directive** - Pre-flight checks for files and commands

### Waiting on SDK

- 🔜 **Infinite Sessions** - Native SDK compaction (requires SDK v2 protocol)
- 🔜 **Session Persistence** - Resume/list/delete sessions (requires SDK v2 protocol)
- 🔜 **SDK ABORT Event Handling** - Code ready to handle abort signals, but SDK does not currently emit them ([details](./COPILOT-SDK-INTEGRATION.md#gap-sdk-abort-event-not-observed))

### Planned Features

#### P2: VERIFY-IMPLEMENTED Directive

Pattern search in code to verify safety constraints are implemented:

```dockerfile
# Check that safety constraint is implemented in code
VERIFY-IMPLEMENTED SC-BOLUS-003a
```

See [proposals/STPA-INTEGRATION.md](./proposals/STPA-INTEGRATION.md) for design details.

#### P2: Tight Validation Tool Integration

Integrate sdqctl with verification tools (like `verify_refs.py`) as first-class gates:

```dockerfile
# Proposed: require tool success before continuing
REQUIRE-TOOL verify_refs --check refs.yaml
GATE @reports/verification.json exists

# Dynamic context from tool output
CONTEXT-FROM-TOOL verify_refs --output-format json
```

#### P3: Permission Handler

Implement SDK permission handler for safe unattended automation:

```dockerfile
ALLOW-SHELL echo,ls,cat,grep
DENY-SHELL rm,sudo,chmod
PERMISSION-MODE strict
```

#### P3: Hook/Skill Integration

Explore integration with Copilot hooks and skills for:
- Pre/post prompt hooks for validation
- Domain-specific skills injection
- Custom tool registration

See [COPILOT-SDK-INTEGRATION.md](./COPILOT-SDK-INTEGRATION.md) for full SDK integration plans.

## License

MIT
