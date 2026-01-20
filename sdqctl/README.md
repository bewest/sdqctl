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
| `PROMPT` | Prompt to send (runs LLM conversation cycle) |
| `PAUSE` | Checkpoint and exit for human review |
| `CHECKPOINT-AFTER` | When to checkpoint (each-cycle, each-prompt) |
| `COMPACT-PRESERVE` | What to preserve during compaction |
| `OUTPUT-FORMAT` | Output format (markdown, json) |
| `OUTPUT-FILE` | Output destination |

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
```

## Commands

### `sdqctl run`

Execute a single prompt or workflow:

```bash
sdqctl run "Analyze this codebase"
sdqctl run workflow.conv --adapter copilot
sdqctl run workflow.conv --dry-run
```

### `sdqctl cycle`

Multi-cycle execution with compaction:

```bash
sdqctl cycle workflow.conv --max-cycles 5
sdqctl cycle workflow.conv --checkpoint-dir ./checkpoints
```

### `sdqctl flow`

Batch/parallel execution:

```bash
sdqctl flow workflows/*.conv --parallel 4
sdqctl flow workflows/*.conv --continue-on-error
```

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
