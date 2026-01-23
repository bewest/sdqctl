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
sdqctl -P cycle workflow.conv > results.json 2>> debug.log
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
sdqctl -vv -P cycle workflow.conv
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
