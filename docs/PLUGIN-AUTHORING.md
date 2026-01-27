# Plugin Authoring Guide

Create custom sdqctl plugins to extend verification and workflow capabilities for your project.

## Quick Start

### 1. Create the manifest

Create `.sdqctl/directives.yaml` in your project root:

```yaml
version: 1
directives:
  VERIFY:
    my-check:
      handler: python tools/verify_mycheck.py
      description: "My custom verification"
```

### 2. Create the handler script

Create `tools/verify_mycheck.py`:

```python
#!/usr/bin/env python3
"""Custom verification plugin."""
import sys

def main():
    # Your verification logic here
    print("Verification passed")
    sys.exit(0)  # 0 = pass, non-zero = fail

if __name__ == "__main__":
    main()
```

### 3. Use in workflows

```dockerfile
# my-workflow.conv
MODEL gpt-4
ADAPTER copilot

VERIFY my-check

PROMPT Analyze the verification results.
```

Or via CLI:

```bash
sdqctl verify plugin my-check
sdqctl verify plugin my-check -v  # verbose output
sdqctl verify plugin --list       # list available plugins
```

---

## Manifest Reference

### Location

Manifests are discovered in order (first wins):

1. **Workspace-local**: `.sdqctl/directives.yaml` (in project root)
2. **Parent directories**: Up to git root
3. **User-global**: `~/.sdqctl/directives.yaml`

### Schema

```yaml
version: 1                    # Required: schema version
directives:
  VERIFY:                     # Directive type
    my-verifier:              # Subcommand name
      handler: "command"      # Required: shell command to run
      description: "text"     # Required: help text
      timeout: 30             # Optional: seconds (default: 30)
      args:                   # Optional: argument specs
        - name: "arg-name"
          type: "string"      # string | path | number | boolean
          required: false
      requires:               # Optional: capability requirements
        - "shell"
```

### Supported Directive Types

| Type | Description | Use Case |
|------|-------------|----------|
| `VERIFY` | Verification commands | Static analysis, checks |
| `TRACE` | Traceability commands | Artifact linking |
| `CHECK` | Validation commands | Runtime checks |

---

## Handler Development

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success / verification passed |
| 1 | Failure / verification failed |
| 2+ | Error conditions |

### Output

- **stdout**: Captured and shown to user
- **stderr**: Captured as error message on failure

### Environment

Handlers run with:
- **CWD**: Workspace root (where `.sdqctl/` lives)
- **Timeout**: Configurable (default 30s)

### Placeholders

Use these in your handler command:

| Placeholder | Value |
|-------------|-------|
| `{root}` | Verification target path |
| `{workspace}` | Workspace root path |

Example:
```yaml
handler: python tools/verify.py --path {root}
```

---

## Examples

### Python Verifier

```yaml
# .sdqctl/directives.yaml
version: 1
directives:
  VERIFY:
    stpa-hazards:
      handler: python tools/verify_stpa.py
      description: "Verify STPA hazard traceability"
      timeout: 60
```

```python
# tools/verify_stpa.py
#!/usr/bin/env python3
"""Verify STPA hazard documentation."""
import sys
from pathlib import Path

def main():
    docs = Path("docs")
    hazards = list(docs.rglob("**/HAZ-*.md"))
    
    if not hazards:
        print("ERROR: No HAZ-* files found", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(hazards)} hazard documents")
    # Add your verification logic...
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Shell Script Verifier

```yaml
version: 1
directives:
  VERIFY:
    lint-docs:
      handler: ./scripts/lint-docs.sh
      description: "Lint markdown documentation"
      timeout: 120
```

```bash
#!/bin/bash
# scripts/lint-docs.sh
set -e

echo "Linting documentation..."
npx markdownlint docs/**/*.md

echo "Documentation lint passed"
exit 0
```

### Verifier with Arguments

```yaml
version: 1
directives:
  TRACE:
    uca:
      handler: python tools/trace_uca.py
      description: "Trace UCA to requirements"
      args:
        - name: uca-id
          type: string
          required: true
          description: "UCA identifier (e.g., UCA-001)"
```

---

## Testing Your Plugin

### Manual Testing

```bash
# Test the handler directly
python tools/verify_mycheck.py

# Test via sdqctl
sdqctl verify plugin my-check
sdqctl verify plugin my-check --verbose
```

### Verify Registration

```bash
# List discovered plugins
sdqctl verify plugin --list
```

### Debug Mode

```bash
# Run with verbose output
sdqctl verify plugin my-check -v

# Check for errors
sdqctl verify plugin my-check 2>&1 | head -20
```

---

## Best Practices

### Do

- ✅ Use descriptive names (`ecosystem-gaps` not `check1`)
- ✅ Provide clear descriptions for `--help`
- ✅ Exit 0 on success, non-zero on failure
- ✅ Print actionable error messages to stderr
- ✅ Set reasonable timeouts (longer for network ops)
- ✅ Use relative paths in handlers

### Don't

- ❌ Hardcode absolute paths
- ❌ Assume specific Python version
- ❌ Write to stdout on failure (use stderr)
- ❌ Block indefinitely (set timeouts)
- ❌ Modify files without user consent

---

## Troubleshooting

### Plugin Not Found

```
Error: Unknown verifier 'my-check'
```

**Causes:**
1. Manifest not in `.sdqctl/directives.yaml`
2. YAML syntax error
3. Missing `version` or `directives` key

**Fix:** Validate YAML:
```bash
python -c "import yaml; yaml.safe_load(open('.sdqctl/directives.yaml'))"
```

### Handler Not Found

```
Plugin 'my-check' handler not found
```

**Causes:**
1. Script path is wrong
2. Script not executable
3. Python/interpreter not in PATH

**Fix:** Test handler directly:
```bash
python tools/verify_mycheck.py
```

### Timeout

```
Plugin 'my-check' timed out after 30s
```

**Fix:** Increase timeout in manifest:
```yaml
timeout: 120  # 2 minutes
```

---

## References

- [Manifest Schema](directives-schema.json) - JSON Schema for validation
- [Plugin System Proposal](../proposals/PLUGIN-SYSTEM.md) - Design document
- [Architecture](ARCHITECTURE.md) - Extension points
