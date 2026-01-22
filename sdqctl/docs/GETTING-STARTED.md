# Getting Started with sdqctl

**Software Defined Quality Control** - Orchestrate AI-assisted development workflows with reproducible, declarative definitions.

---

## What is sdqctl?

sdqctl is a CLI that lets you:
- Define AI workflows as code (`.conv` files)
- Run single prompts or multi-cycle iterations
- Apply workflows across multiple components
- Manage context and checkpoints

Think of it as "Dockerfile for AI conversations" — declarative, reproducible, vendor-agnostic.

---

## Installation

```bash
cd /path/to/sdqctl
pip install -e .

# Verify installation
sdqctl --version
sdqctl --help
```

---

## Your First Workflow

### 1. Run a Simple Prompt

```bash
# Inline prompt with mock adapter (no AI calls)
sdqctl run "Analyze this codebase for security issues" --adapter mock --dry-run

# With real AI
sdqctl run "Analyze this codebase" --adapter copilot
```

### 2. Create a ConversationFile

Create `my-audit.conv`:

```dockerfile
# my-audit.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Analyze the codebase structure.
PROMPT Identify potential improvements.

OUTPUT-FORMAT markdown
```

> **⚠️ Naming Matters:** Workflow filenames influence agent behavior! Use action verbs 
> (`fix-`, `implement-`, `audit-`) not passive nouns (`tracker`, `report`).
> See [QUIRKS.md](QUIRKS.md#q-001-workflow-filename-influences-agent-behavior) for details.

Run it:

```bash
# Preview what would happen
sdqctl run my-audit.conv --dry-run

# Execute with mock (for testing)
sdqctl run my-audit.conv --adapter mock -v

# Execute with real AI
sdqctl run my-audit.conv --adapter copilot
```

### 3. Render Without Executing

The `render` command shows fully-resolved prompts without calling AI:

```bash
sdqctl render my-audit.conv
```

This is useful for:
- Debugging template issues
- Reviewing prompts before expensive AI calls
- Using sdqctl as a prompt templating engine

---

## Core Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `run` | Execute single prompt or workflow | Testing, one-off tasks |
| `cycle` | Multi-cycle iteration with state | Iterative refinement, long tasks |
| `apply` | Apply workflow to multiple components | Batch processing |
| `render` | Preview prompts without AI calls | Debugging, validation |
| `status` | Show session/adapter status | Troubleshooting |

### run vs cycle vs apply

**`run`** — Single execution, good for:
- Testing a workflow design
- One-off prompts
- Priming before committing to cycles

**`cycle`** — Multiple iterations, good for:
- Tasks that need refinement
- Work that exceeds one context window
- Self-improving workflows

**`apply`** — Iterate over components, good for:
- Auditing multiple files
- Batch transformations
- Generating per-component reports

---

## ConversationFile Anatomy

```dockerfile
# comment
MODEL gpt-4                    # AI model
ADAPTER copilot                # Provider (copilot, mock, claude, openai)
MODE audit                     # Execution mode

CONTEXT @lib/auth/*.js         # Include files (use sparingly!)

PROMPT First prompt to send.   # Conversation turn
PROMPT Second prompt.          # Another turn

OUTPUT-FORMAT markdown         # Output formatting
OUTPUT-FILE report.md          # Save output
```

### Key Directives

| Directive | Purpose |
|-----------|---------|
| `PROMPT` | Send a message to the AI |
| `RUN` | Execute a shell command |
| `CONTEXT` | Include file(s) in context |
| `PROLOGUE` | Prepend to every prompt |
| `EPILOGUE` | Append to every prompt |
| `PAUSE` | Checkpoint for human review |

### Template Variables

Use `{{VAR}}` syntax in prompts and output paths:

```dockerfile
PROMPT Analyzing on {{DATE}} (branch: {{GIT_BRANCH}})
OUTPUT-FILE reports/audit-{{DATE}}.md
```

Available: `{{DATE}}`, `{{DATETIME}}`, `{{GIT_BRANCH}}`, `{{GIT_COMMIT}}`, `{{CWD}}`

> **Note:** `{{WORKFLOW_NAME}}` is available in OUTPUT-FILE paths but excluded from prompts
> by default. Use `{{__WORKFLOW_NAME__}}` for explicit opt-in in prompts.

---

## Context Management Best Practices

### Hint, Don't Inject

❌ **Over-priming** — Forces everything into context:
```dockerfile
CONTEXT @docs/**/*.md
CONTEXT @lib/**/*.py
PROLOGUE @reports/full-analysis.md
```

✅ **Hinting** — Let the agent explore on demand:
```dockerfile
PROMPT Analyze the authentication module.
  Key files are in lib/auth/.
  Previous findings are in reports/auth-audit.md if you need context.
```

### Why This Matters

- AI agents can read files when they need them
- Injecting too much upfront wastes context tokens
- Agents explore more effectively when not over-constrained

### When to Use CONTEXT

Use `CONTEXT` only for:
- Small, critical files the AI must see
- Configuration files that define behavior
- Template files being analyzed

---

## Example: Security Audit

```dockerfile
# security-audit.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Perform a security audit of this codebase.
  Focus on authentication, input validation, and data handling.
  Key areas to check: lib/auth/, lib/api/
  
PROMPT Generate a findings report with severity ratings.

OUTPUT-FORMAT markdown
OUTPUT-FILE security-report.md
```

```bash
# Test with mock first
sdqctl run security-audit.conv --adapter mock --dry-run

# Run for real
sdqctl run security-audit.conv --adapter copilot
```

---

## Next Steps

Once comfortable with `run`, explore:

1. **[Quine Workflows](QUINE-WORKFLOWS.md)** — Self-improving iteration patterns
2. **[Traceability Workflows](TRACEABILITY-WORKFLOW.md)** — Requirements → code → verification
3. **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Code → documentation
4. **[Known Quirks](QUIRKS.md)** — Surprising behaviors and workarounds

See `examples/workflows/` for ready-to-use templates.

---

## Quick Reference

```bash
# Run workflow
sdqctl run workflow.conv --adapter copilot

# Preview prompts
sdqctl render workflow.conv

# Multi-cycle
sdqctl cycle workflow.conv -n 3

# Batch apply
sdqctl apply workflow.conv --components "lib/*.py"

# Check status
sdqctl status --adapters
```
