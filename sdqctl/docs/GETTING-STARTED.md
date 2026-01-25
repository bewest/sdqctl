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

## Initialize a Project

The `init` command sets up sdqctl in your project:

```bash
# Initialize in current directory
sdqctl init .

# Initialize in a specific directory
sdqctl init my-project

# Skip GitHub Copilot integration files
sdqctl init . --no-copilot

# Overwrite existing files
sdqctl init . --force
```

### What `init` Creates

| File/Directory | Purpose |
|----------------|---------|
| `.sdqctl.yaml` | Project configuration (defaults, context settings) |
| `workflows/` | Directory for your `.conv` workflow files |
| `workflows/example-audit.conv` | Example security audit workflow |
| `.github/copilot-instructions.md` | Instructions for GitHub Copilot |
| `.github/skills/sdqctl-verify.md` | Copilot skill for sdqctl verification |

### Configuration File (`.sdqctl.yaml`)

The generated config file includes:

```yaml
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
```

This sets project-wide defaults so you don't need to specify them in every workflow.

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
# Render for run command (single execution)
sdqctl render run my-audit.conv

# Render for cycle command (multi-cycle)
sdqctl render cycle my-audit.conv -n 3

# Quick overview: show @file references without expanding
sdqctl render run my-audit.conv --plan

# Output to file
sdqctl render run my-audit.conv -o rendered.md
```

This is useful for:
- Debugging template issues
- Reviewing prompts before expensive AI calls
- Using sdqctl as a prompt templating engine
- CI/CD validation of workflow content

---

## Core Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `run` | Execute single prompt or workflow | Testing, one-off tasks |
| `cycle` | Multi-cycle iteration with state | Iterative refinement, long tasks |
| `apply` | Apply workflow to multiple components | Batch processing |
| `render` | Preview prompts without AI calls | Debugging, validation |
| `verify` | Static verification suite | Pre-flight checks |
| `refcat` | Extract file content with line ranges | Precise context injection |
| `status` | Show session/adapter status | Troubleshooting |
| `sessions` | Manage conversation sessions | List, delete, cleanup sessions |

### run vs cycle vs apply

**`run`** — Single execution, good for:
- Testing a workflow design
- One-off prompts
- Priming before committing to cycles

> **⚠️ Note**: `run` does not process CHECKPOINT directives. If your workflow uses 
> CHECKPOINT for resumability, use `cycle` instead. The `run` command is lightweight 
> and stateless; `cycle` provides full checkpoint/resume support.

**`cycle`** — Multiple iterations, good for:
- Tasks that need refinement
- Work that exceeds one context window
- Self-improving workflows
- **Workflows with CHECKPOINT directives**

**Session modes** control context across cycles:
```bash
sdqctl cycle workflow.conv -n 5 --session-mode fresh      # New session each cycle
sdqctl cycle workflow.conv -n 5 --session-mode accumulate # Context grows (default)
sdqctl cycle workflow.conv -n 10 --session-mode compact   # Summarize between cycles
```

**`apply`** — Iterate over components, good for:
- Auditing multiple files
- Batch transformations
- Generating per-component reports

### Precise Context with refcat

The `refcat` command extracts file content with line-level precision:

```bash
# Extract specific lines (more efficient than full file injection)
sdqctl refcat @path/file.py#L10-L50

# Single line
sdqctl refcat @path/file.py#L42

# Pattern search (first match)
sdqctl refcat @path/file.py#/def my_func/

# Multiple refs
sdqctl refcat @file1.py#L10 @file2.py#L20-L30
```

**Output includes metadata** for agent disambiguation:

```markdown
## From: sdqctl/core/context.py:182-194 (relative to /home/user/project)
```python
182 |     def get_context_content(self) -> str:
183 |         """Get formatted context content..."""
...
```
```

**When to use refcat vs CONTEXT:**

| Scenario | Use | Why |
|----------|-----|-----|
| Small config file (<100 lines) | `CONTEXT @config.yaml` | Agent needs full file |
| Specific function in large file | `sdqctl refcat @lib/auth.py#L50-L80` | Save tokens |
| Cross-repo reference | `sdqctl refcat loop:LoopKit/Algorithm.swift#L100` | Alias support |

See [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md#precise-extraction-with-refcat) for more patterns.

---

## Verbosity & Debugging

### See What's Happening

Use `-v` flags to control output verbosity:

```bash
sdqctl run my-audit.conv              # Default: just results
sdqctl -v run my-audit.conv           # Progress with context %
sdqctl -vv run my-audit.conv          # Stream agent responses
sdqctl -vvv run my-audit.conv         # Full debug output
```

### See What Prompts Are Sent

Use `-P` (`--show-prompt`) to display expanded prompts on stderr:

```bash
# See prompts in terminal
sdqctl -P run my-audit.conv

# Capture prompts to file while running
sdqctl -P run my-audit.conv 2> prompts.log

# Full debugging: prompts + streaming
sdqctl -vv -P cycle my-audit.conv -n 3
```

Output shows cycle/prompt position and context usage:
```
[Cycle 2/3, Prompt 1/2] (ctx: 45%)
────────────────────────────────────────────────
Your prompt content here...
────────────────────────────────────────────────
```

### Quiet Mode

For scripts and CI/CD, use `-q` for errors only:

```bash
sdqctl -q run my-audit.conv --json > results.json
```

See [IO-ARCHITECTURE.md](IO-ARCHITECTURE.md) for full details.

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
| `ON-FAILURE` | Block executed if preceding RUN fails (non-zero exit) |
| `ON-SUCCESS` | Block executed if preceding RUN succeeds (zero exit) |
| `CONTEXT` | Include file(s) in context |
| `PROLOGUE` | Prepend to first prompt of cycle |
| `EPILOGUE` | Append to last prompt of cycle |
| `PAUSE` | Checkpoint for human review |
| `CONSULT` | Pause with proactive question presentation |
| `COMPACT` | Trigger context compaction |
| `ELIDE` | Merge adjacent elements into single prompt |
| `VERIFY` | Run static verification (refs, etc.) |
| `MODEL-REQUIRES` | Abstract model selection (e.g., `context:50k`) |
| `HELP` | Inject built-in help topics into prompts |

> **Efficiency Tip:** Use `ELIDE` to combine test output with fix instructions:
> ```dockerfile
> RUN pytest -v
> ELIDE
> PROMPT Fix any failing tests above.
> ```
> This sends one merged prompt instead of multiple agent turns.

### HELP Directive

Inject built-in help content directly into workflow prompts. Useful for giving AI agents reference material:

```dockerfile
# Single topic - inject directive reference
HELP directives

# Multiple topics on one line
HELP directives workflow

# Multiple HELP directives
HELP adapters
HELP variables
```

**Available topics:** `adapters`, `ai`, `context`, `directives`, `examples`, `validation`, `variables`, `workflow`

**How it works:** HELP topics are injected as prologues, prepended to the first prompt of each cycle. This gives the AI agent access to sdqctl reference documentation without you copying it manually.

**Example:** Create a workflow where the AI helps write workflows:

```dockerfile
# workflow-assistant.conv
MODEL gpt-4
ADAPTER copilot

HELP directives workflow
PROMPT I need a workflow to audit authentication code.
  Suggest a ConversationFile structure with appropriate directives.
```

> **Tip:** Use `sdqctl help --list` to see all available topics, or `sdqctl help <topic>` to preview content.

### Template Variables

Use `{{VAR}}` syntax in prompts and output paths:

```dockerfile
PROMPT Analyzing on {{DATE}} (branch: {{GIT_BRANCH}})
OUTPUT-FILE reports/audit-{{DATE}}.md
```

Available: `{{DATE}}`, `{{DATETIME}}`, `{{GIT_BRANCH}}`, `{{GIT_COMMIT}}`, `{{CWD}}`, `{{STOP_FILE}}`

> **Note:** `{{WORKFLOW_NAME}}` is available in OUTPUT-FILE paths but excluded from prompts
> by default. Use `{{__WORKFLOW_NAME__}}` for explicit opt-in in prompts.
>
> **Stop File:** The `{{STOP_FILE}}` variable provides the filename an agent can create to
> request human review. Stop file instructions are injected automatically by default.
> See [LOOP-STRESS-TEST.md](LOOP-STRESS-TEST.md#4-stop-file-detection) for details.

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

## Error Handling & Branching

When shell commands fail, you can adapt the workflow using `ON-FAILURE` and `ON-SUCCESS` blocks:

### Basic Pattern: Test → Fix → Retry

```dockerfile
# test-and-fix.conv
MODEL gpt-4
ADAPTER copilot

RUN npm test
ON-FAILURE
  PROMPT Analyze the test failures above and fix them.
  RUN npm test
ON-SUCCESS
  PROMPT Tests passed! Generate a coverage summary.

PROMPT Continue with remaining tasks...
```

**Behavior:**
- `ON-FAILURE` executes only if the preceding `RUN` exits non-zero
- `ON-SUCCESS` executes only if the preceding `RUN` exits zero
- After the block, workflow continues normally
- Both blocks are optional (use either, both, or neither)

### RUN-RETRY for Simple Retries

For commands that may need multiple attempts:

```dockerfile
# Retry up to 3 times with AI intervention
RUN-RETRY 3 npm test
ELIDE
PROMPT If tests failed, analyze and fix the issues.
```

### When to Use Each Pattern

| Scenario | Directive | Why |
|----------|-----------|-----|
| Flaky test, let AI fix | `RUN` + `ON-FAILURE` | Full control over recovery |
| Network request retry | `RUN-RETRY 3` | Simple retry, no AI intervention |
| Different actions for pass/fail | `ON-SUCCESS` + `ON-FAILURE` | Conditional branching |
| Lint + auto-fix | `RUN npm run lint` + `ON-FAILURE` | Pattern: check → fix → recheck |

### Important Constraints

**No nesting:** `ON-FAILURE` blocks cannot contain their own branching:

```dockerfile
# ❌ INVALID - parse error
RUN npm test
ON-FAILURE
  RUN npm run fix
  ON-FAILURE          # Nested branching not allowed
    PROMPT Cannot auto-fix
```

**No ELIDE in blocks:** ELIDE cannot span across branching constructs.

See [FEATURE-INTERACTIONS.md](FEATURE-INTERACTIONS.md) for complete interaction rules.

---

## Artifact ID Management

For traceability workflows (STPA, IEC 62304), use `artifact` to manage unique IDs:

```bash
# Get next available ID
sdqctl artifact next REQ           # → REQ-001
sdqctl artifact next UCA-BOLUS     # → UCA-BOLUS-001

# List existing artifacts by type
sdqctl artifact list REQ

# Rename and update all references
sdqctl artifact rename REQ-001 REQ-AUTH-001
```

**Supported categories:** `LOSS`, `HAZ`, `UCA`, `SC` (STPA), `REQ`, `SPEC`, `TEST`, `GAP` (Requirements), `BUG`, `PROP`, `Q` (Development)

See [TRACEABILITY-WORKFLOW.md](TRACEABILITY-WORKFLOW.md) for full traceability patterns.

---

## Next Steps

Once comfortable with `run`, explore:

1. **[Philosophy](PHILOSOPHY.md)** — Workflow design principles and patterns
2. **[Adapters](ADAPTERS.md)** — Configure AI providers (Copilot, Claude, OpenAI)
3. **[Context Management](CONTEXT-MANAGEMENT.md)** — Optimal context window strategies
4. **[Synthesis Cycles](SYNTHESIS-CYCLES.md)** — Self-improving iteration patterns
5. **[Traceability Workflows](TRACEABILITY-WORKFLOW.md)** — Requirements → code → verification
6. **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Code → documentation
7. **[Commands Reference](COMMANDS.md)** — Complete CLI command documentation
8. **[Known Quirks](QUIRKS.md)** — Surprising behaviors and workarounds

See `examples/workflows/` for ready-to-use templates, including:
- `examples/workflows/stpa/` — STPA safety analysis workflows

---

## Quick Reference

```bash
# Run workflow
sdqctl run workflow.conv --adapter copilot

# Preview prompts (use subcommand: run, cycle, or apply)
sdqctl render run workflow.conv
sdqctl render cycle workflow.conv -n 3

# Multi-cycle with session mode
sdqctl cycle workflow.conv -n 3
sdqctl cycle workflow.conv -n 5 --session-mode fresh  # New session each cycle

# Batch apply
sdqctl apply workflow.conv --components "lib/*.py"

# Static verification
sdqctl verify refs
sdqctl verify all --json

# Extract file content with line ranges
sdqctl refcat @file.py#L10-L50              # Lines 10-50
sdqctl refcat @file.py#/def main/           # Pattern search

# Check status
sdqctl status --adapters

# Session management
sdqctl sessions list                           # List all sessions
sdqctl sessions list --format json             # JSON output
sdqctl sessions list --filter "audit-*"        # Filter by pattern
sdqctl sessions delete SESSION_ID --force      # Delete a session
sdqctl sessions cleanup --older-than 7d        # Clean up old sessions
```
