# Subproject Tooling Guide

Guide for external projects using sdqctl's verification and directive system.

> **Audience**: Projects in `externals/` or any codebase integrating sdqctl  
> **Prerequisites**: [GETTING-STARTED.md](GETTING-STARTED.md), [PLUGIN-AUTHORING.md](PLUGIN-AUTHORING.md)

---

## Quick Setup

### 1. Initialize Configuration

Create `.sdqctl.yaml` in your project root:

```yaml
# .sdqctl.yaml
project:
  name: my-subproject
  
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

### 2. Create Plugin Manifest

Create `.sdqctl/directives.yaml` for custom verifiers:

```yaml
# .sdqctl/directives.yaml
version: 1
directives:
  VERIFY:
    my-check:
      handler: python tools/verify_mycheck.py
      description: "My custom verification"
      timeout: 30
```

### 3. Activate Parent sdqctl

If using sdqctl from a parent project:

```bash
# From subproject root
source ../path-to-sdqctl/activate-sdqctl.sh

# Or add to your shell profile
export PATH="/path/to/sdqctl:$PATH"
```

---

## Directive Types

### VERIFY - Validation Commands

For static analysis and checks that validate project state.

```yaml
directives:
  VERIFY:
    gaps:
      handler: python tools/verify_gaps.py
      description: "Verify GAP coverage"
      timeout: 60
```

**Usage in .conv**:
```dockerfile
VERIFY gaps
PROMPT Analyze the verification results.
```

**Usage via CLI**:
```bash
sdqctl verify plugin gaps
sdqctl verify plugin gaps -v  # verbose
```

### HYGIENE - Workflow Maintenance

For backlog, queue, and documentation maintenance tasks.

```yaml
directives:
  HYGIENE:
    queue-stats:
      handler: python tools/queue_stats.py --json
      description: "Quick queue status"
      timeout: 10
```

**Usage in .conv**:
```dockerfile
HYGIENE queue-stats
PROMPT Review the queue status and suggest improvements.
```

### TRACE - Traceability Commands

For artifact linking and dependency tracking.

```yaml
directives:
  TRACE:
    requirements:
      handler: python tools/trace_reqs.py {value}
      description: "Trace requirement coverage"
      timeout: 60
      args:
        - name: req-id
          type: string
          required: true
```

---

## Handler Development

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Failure (verification failed) |
| 2+ | Error (script error) |

### Output Format

Handlers should output JSON for structured results:

```python
#!/usr/bin/env python3
import json
import sys

def main():
    results = {
        "status": "pass",
        "checks": 5,
        "passed": 5,
        "issues": []
    }
    
    print(json.dumps(results, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Placeholders

Use in handler commands:

| Placeholder | Value |
|-------------|-------|
| `{root}` | Verification target path |
| `{workspace}` | Workspace root path |
| `{value}` | Directive value from .conv |
| `{directive}` | Directive type name |

---

## Workflow Integration

### Basic Workflow

```dockerfile
# workflows/validate.conv
MODEL gpt-4
ADAPTER copilot

# Run custom verification
VERIFY gaps
VERIFY terminology

PROMPT Based on the verification results above, identify the top 3 issues.
```

### With Context

```dockerfile
# workflows/analyze.conv
MODEL gpt-4

REFCAT @docs/ARCHITECTURE.md
REFCAT @traceability/gaps.md

VERIFY gaps

PROMPT Analyze gaps in context of the architecture.
```

### Multi-Cycle with Hygiene

```dockerfile
# workflows/maintenance.conv
MODEL gpt-4
MAX-CYCLES 3

HYGIENE queue-stats
PROMPT Review queue status.

COMPACT
COMPACT-PRESERVE queues, metrics

HYGIENE check-sizes
PROMPT Identify files needing chunking.
```

---

## Project Structure

Recommended layout for subprojects:

```
my-subproject/
├── .sdqctl/
│   ├── directives.yaml    # Plugin manifest
│   └── checkpoints/       # Session checkpoints
├── .sdqctl.yaml           # Project config
├── tools/
│   ├── verify_gaps.py     # VERIFY handlers
│   ├── verify_refs.py
│   └── queue_stats.py     # HYGIENE handlers
├── workflows/
│   ├── validate.conv      # Validation workflow
│   ├── analyze.conv       # Analysis workflow
│   └── maintenance.conv   # Hygiene workflow
├── docs/
│   └── ...
└── README.md
```

---

## Testing Plugins

### Manual Testing

```bash
# Test handler directly
python tools/verify_gaps.py

# Test via sdqctl
sdqctl verify plugin gaps
sdqctl verify plugin gaps -v

# List available plugins
sdqctl verify plugin --list
```

### Verify Registration

```bash
# Check VERIFY plugin discovery
sdqctl plugin list
sdqctl plugin list --json

# List ALL handlers (VERIFY, HYGIENE, TRACE, etc.)
sdqctl plugin handlers
sdqctl plugin handlers --type HYGIENE

# Run a handler directly
sdqctl plugin run HYGIENE queue-stats --json
```

### Debug Mode

```bash
# Run workflow with debug output
sdqctl iterate workflows/validate.conv --debug session,tool
```

---

## Best Practices

### 1. JSON Output

Return JSON for structured, parseable results:

```python
print(json.dumps({"status": "pass", "count": 5}))
```

### 2. Meaningful Exit Codes

- `0` = success/pass
- `1` = failure/failed checks  
- `2` = error/exception

### 3. Timeout Configuration

Set appropriate timeouts based on operation:

| Operation | Typical Timeout |
|-----------|----------------|
| Quick status | 10s |
| File analysis | 30s |
| Full verification | 60s |
| Large scans | 120s |

### 4. Idempotent Handlers

Handlers should be safe to run multiple times without side effects.

### 5. Clear Descriptions

Write descriptions that explain what the handler does:

```yaml
# Good
description: "Verify GAP coverage across all project files"

# Bad
description: "Run gaps"
```

---

## Troubleshooting

### Plugin Not Found

```
Error: Plugin 'my-check' not found
```

**Solution**: Check `.sdqctl/directives.yaml` exists and has correct syntax.

### Handler Timeout

```
Error: Handler timed out after 30s
```

**Solution**: Increase timeout in manifest or optimize handler.

### Permission Denied

```
Error: Permission denied: tools/verify.py
```

**Solution**: Make handler executable: `chmod +x tools/verify.py`

---

## Example: Nightscout Ecosystem

See `externals/rag-nightscout-ecosystem-alignment/` for a complete example:

```yaml
# .sdqctl/directives.yaml
version: 1
directives:
  VERIFY:
    ecosystem-gaps:
      handler: python tools/verify_coverage.py
      description: "Verify GAP coverage across projects"
      timeout: 60

    terminology-matrix:
      handler: python tools/verify_terminology.py
      description: "Verify terminology matrix coverage"
      timeout: 60

  HYGIENE:
    queue-stats:
      handler: python tools/queue_stats.py --json
      description: "Quick queue and file size status"
      timeout: 10
```

---

## See Also

- [PLUGIN-AUTHORING.md](PLUGIN-AUTHORING.md) - Detailed plugin development
- [DIRECTIVE-REFERENCE.md](DIRECTIVE-REFERENCE.md) - Built-in directive catalog
- [WORKFLOW-DESIGN.md](WORKFLOW-DESIGN.md) - Workflow patterns
- [GETTING-STARTED.md](GETTING-STARTED.md) - sdqctl fundamentals
