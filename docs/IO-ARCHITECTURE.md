# IO Architecture

This document describes the input/output architecture for sdqctl, including stream separation, verbosity controls, and TTY detection.

## Stream Separation

sdqctl follows Unix conventions for output streams:

| Output Type | Stream | Purpose |
|-------------|--------|---------|
| Progress messages | stdout | User-facing workflow progress |
| Agent responses | stdout | AI-generated content (pipeable) |
| Prompts (with `-P`) | stderr | Expanded templates for debugging/logging |
| Logs (DEBUG/TRACE) | stderr | Diagnostic information |
| Errors | stderr | Error messages and warnings |

This separation allows:
```bash
# Pipe agent output while seeing prompts
sdqctl -P run workflow.conv > output.md 2> prompts.log

# CI/CD: capture results, log prompts
sdqctl -P iterate workflow.conv > results.json 2>> debug.log
```

## Verbosity Flags

### Agent Output Verbosity (`-v`)

The `-v` flag controls agent output detail level. Stacking increases verbosity:

| Level | Flag | What's Shown |
|-------|------|--------------|
| Default | (none) | Final result only |
| INFO | `-v` | Progress with context %, prompt previews |
| DEBUG | `-vv` | Streaming agent responses |
| TRACE | `-vvv` | Tool calls, reasoning, raw events |

### Prompt Display (`-P` / `--show-prompt`)

The `-P` flag enables prompt display on stderr:

```bash
# Show what prompts are being sent
sdqctl -P run workflow.conv

# Capture prompts to file for review
sdqctl -P run workflow.conv 2> prompts.txt

# Combine with verbosity for full debugging
sdqctl -vv -P iterate workflow.conv
```

When enabled, prompts are displayed with context:
```
[Cycle 2/5, Prompt 3/4] (ctx: 45%)
────────────────────────────────────────────────────────────
You are analyzing a codebase for security issues.

Context files loaded: 12 files, 23KB
...
────────────────────────────────────────────────────────────
```

### Quiet Mode (`-q`)

Suppresses all output except errors:
```bash
sdqctl -q run workflow.conv  # Errors only
```

### Verbosity Quick Reference

What you'll see at each level:

| Level | Errors | Warnings | Progress | Tools | Reasoning | Raw Events |
|-------|--------|----------|----------|-------|-----------|------------|
| `-q` (quiet) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| (default) | ✅ | ✅ | Final only | ❌ | ❌ | ❌ |
| `-v` (INFO) | ✅ | ✅ | Cycle/prompt | Summary | ❌ | ❌ |
| `-vv` (DEBUG) | ✅ | ✅ | Detailed | Names + timing | Summaries | ❌ |
| `-vvv` (TRACE) | ✅ | ✅ | All | Full args/output | Full text | ✅ |

**Example output at each level:**

```
# -q (quiet): Nothing unless error
(no output)

# (default): Just the final result
Analysis complete. 3 issues found.

# -v (INFO): Progress + context
[Cycle 1/3] Prompt 1/4 (ctx: 23%): Sending...
[Cycle 1/3] Prompt 1/4 (ctx: 31%): Complete (3.2s)
🔧 Tool: view
✓ view (0.8s)

# -vv (DEBUG): Streaming + tool details
[Cycle 1/3] Prompt 1/4 (ctx: 23%): "Analyze authentication..."
Agent: I'll examine the authentication module...
🔧 Tool: view → path="/lib/auth.py"
✓ view (0.8s) → 2,341 chars

# -vvv (TRACE): Everything including raw SDK events
[SDK] turn.started: turn_id=abc123
[SDK] tool.execution_started: tool=view, id=xyz789
[SDK] tool.execution_complete: duration=0.8s
Agent reasoning: The authentication module uses...
```

**When to use each:**

| Use Case | Recommended |
|----------|-------------|
| CI/CD pipelines | `-q` or default |
| Normal development | `-v` |
| Debugging workflows | `-vv` |
| SDK troubleshooting | `-vvv` |

## Progress Indicators

Progress messages show cycle, prompt, and context usage:

```
Running workflow.conv...
  [Cycle 1/3] Prompt 1/4 (ctx: 23%): Sending...
  [Cycle 1/3] Prompt 1/4 (ctx: 31%): Complete (3.2s)
  [Cycle 1/3] Prompt 2/4 (ctx: 31%): Sending...
```

At `-v` level, includes prompt preview:
```
  [Cycle 1/3] Prompt 2/4 (ctx: 31%): "Analyze authentication..."
```

## TTY Detection (git-style)

Like git, sdqctl detects when output is redirected and adjusts formatting:

| Condition | Behavior |
|-----------|----------|
| stdout is TTY | Rich formatting, colors, progress overwrites |
| stdout redirected | Plain text, no colors, no progress overwrites |
| stderr is TTY | Rich prompt display with formatting |
| stderr redirected | Plain prompt text for logging |

This means:
```bash
# Interactive terminal: colors and formatting
sdqctl -v run workflow.conv

# Piped to file: clean output
sdqctl run workflow.conv > output.md

# Piped to less: clean output
sdqctl run workflow.conv | less
```

## Implementation Details

### Core Modules

- **`sdqctl/utils/output.py`**: TTY detection, PromptWriter, console instances
- **`sdqctl/utils/decorators.py`**: Error handling decorators for CLI commands
- **`sdqctl/core/progress.py`**: Progress functions, WorkflowProgress class
- **`sdqctl/core/logging.py`**: Verbosity levels, stderr logging

### Key Classes

#### `PromptWriter`

Writes expanded prompts to stderr with cycle/step context:

```python
from sdqctl.utils.output import PromptWriter

writer = PromptWriter(enabled=ctx.obj.get("show_prompt", False))
writer.write_prompt(
    prompt=full_prompt,
    cycle=1,
    total_cycles=3,
    prompt_idx=2,
    total_prompts=4,
    context_pct=45.5,
)
```

#### `WorkflowProgress`

Enhanced progress tracking with context %:

```python
from sdqctl.core.progress import WorkflowProgress

wp = WorkflowProgress("workflow.conv", total_cycles=3, total_prompts=4, verbosity=1)
wp.start()
wp.prompt_sending(cycle=1, prompt=1, context_pct=23.5, preview="Analyze...")
wp.prompt_complete(cycle=1, prompt=1, duration=3.2, context_pct=31.0)
wp.done()
```

#### `handle_io_errors` Decorator

Wraps CLI commands with consistent I/O error handling:

```python
from sdqctl.utils import handle_io_errors, handle_io_errors_async

@click.command()
@handle_io_errors()
def my_command():
    """FileNotFoundError, PermissionError, OSError caught automatically."""
    content = Path("file.txt").read_text()
    ...

# With JSON error output
@click.command()
@handle_io_errors(json_errors=True, exit_code=2)
def json_command():
    ...

# Async variant
@click.command()
@handle_io_errors_async()
async def async_command():
    ...
```

#### `WorkflowContext` and `WorkflowLoggerAdapter`

Enhanced logging with workflow context for better observability:

```python
from sdqctl.core.logging import WorkflowContext, WorkflowLoggerAdapter, get_workflow_logger

# Create a workflow-aware logger
logger = get_workflow_logger(
    "sdqctl.adapters.copilot",
    workflow_name="fix-quirks",
    cycle=1,
    total_cycles=3
)

# Log messages include workflow context
logger.info("Turn started")  # Logs: [fix-quirks:1/3] Turn started

# Update context as workflow progresses
logger.update_context(prompt=2, total_prompts=4)
logger.info("Sending prompt")  # Logs: [fix-quirks:1/3:P2/4] Sending prompt
```

The workflow context is also available globally for formatters:

```python
from sdqctl.core.logging import set_workflow_context, WorkflowContext

# Set global context (used by WorkflowContextFormatter)
ctx = WorkflowContext(workflow_name="proposal-dev", cycle=2, total_cycles=5)
set_workflow_context(ctx)

# All sdqctl loggers will include the prefix at DEBUG/TRACE levels
```

### TTY Detection

```python
from sdqctl.utils.output import is_stdout_tty, is_stderr_tty

if is_stdout_tty():
    # Use rich formatting
else:
    # Use plain text
```

## Flag Summary

| Flag | Short | Purpose | Stacks |
|------|-------|---------|--------|
| `--verbose` | `-v` | Increase agent output verbosity | Yes |
| `--quiet` | `-q` | Suppress non-error output | No |
| `--show-prompt` | `-P` | Show prompts on stderr | No |

## Examples

```bash
# Basic run
sdqctl run workflow.conv

# Show progress with context %
sdqctl -v run workflow.conv

# Debug: see streaming output
sdqctl -vv run workflow.conv

# Full debug: prompts + streaming + tool calls
sdqctl -vvv -P run workflow.conv

# Capture prompts separately from output
sdqctl -P run workflow.conv > results.md 2> prompts.log

# CI/CD: quiet mode, JSON output
sdqctl -q run workflow.conv --json > results.json

# Pipe agent output, see progress
sdqctl -v run workflow.conv | tee output.md
```
