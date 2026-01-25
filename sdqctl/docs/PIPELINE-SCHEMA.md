# Pipeline JSON Schema

> **Version**: 1.0  
> **Status**: Stable  
> **See Also**: [PIPELINE-ARCHITECTURE.md](../proposals/PIPELINE-ARCHITECTURE.md) (proposal)

---

## Overview

sdqctl supports **round-trip JSON workflows** for external transformation pipelines. This enables:

- **Conditional workflow selection** - Choose prompts based on external state
- **Dynamic context injection** - Add/remove context files based on analysis  
- **Workflow templating** - Generate variations of a base workflow
- **CI/CD integration** - Modify workflows based on pipeline variables

```bash
# Render workflow as JSON, transform it, execute
sdqctl render iterate workflow.conv --json \
  | jq '.cycles[0].prompts[0].resolved += " (modified)"' \
  | sdqctl iterate --from-json -
```

---

## Schema Version

The JSON schema includes a `schema_version` field for compatibility:

```json
{
  "schema_version": "1.0",
  ...
}
```

**Versioning policy:**
- **Major version** (2.0): Breaking changes to stable fields
- **Minor version** (1.1): New fields, no breaking changes
- CLI validates version and warns/errors on unsupported major versions

---

## JSON Schema (v1.0)

### Top-Level Structure

```json
{
  "schema_version": "1.0",
  "workflow": "/path/to/workflow.conv",
  "workflow_name": "workflow",
  "mode": "full",
  "session_mode": "accumulate",
  "adapter": "copilot",
  "model": "gpt-4",
  "max_cycles": 3,
  "template_variables": {},
  "cycles": []
}
```

| Field | Type | Required | Stability | Description |
|-------|------|----------|-----------|-------------|
| `schema_version` | string | Yes | **Stable** | Schema version (e.g., "1.0") |
| `workflow` | string \| null | No | Stable | Source workflow file path |
| `workflow_name` | string | No | Stable | Workflow name (from filename) |
| `mode` | string | No | Stable | Render mode: "full" or "plan" |
| `session_mode` | string | Yes | **Stable** | "fresh", "compact", or "accumulate" |
| `adapter` | string | Yes | **Stable** | AI adapter: "copilot", "claude", "openai", "mock" |
| `model` | string | No | Stable | Model identifier |
| `max_cycles` | integer | Yes | **Stable** | Total number of cycles |
| `template_variables` | object | No | Stable | Base template variables (without cycle-specific) |
| `cycles` | array | Yes | **Stable** | Array of cycle objects |

### Cycle Object

```json
{
  "number": 1,
  "variables": {
    "CYCLE_NUMBER": "1",
    "CYCLE_TOTAL": "3"
  },
  "context_files": [],
  "prompts": []
}
```

| Field | Type | Required | Stability | Description |
|-------|------|----------|-----------|-------------|
| `number` | integer | Yes | **Stable** | 1-based cycle number |
| `variables` | object | No | Stable | Cycle-specific template variables |
| `context_files` | array | No | **Stable** | Array of context file objects |
| `prompts` | array | Yes | **Stable** | Array of prompt objects |

### Context File Object

```json
{
  "path": "/absolute/path/to/file.js",
  "content": "// file contents...",
  "tokens_estimate": 500
}
```

| Field | Type | Required | Stability | Description |
|-------|------|----------|-----------|-------------|
| `path` | string | Yes | **Stable** | Absolute path to source file |
| `content` | string | Full mode | **Stable** | File contents (omitted in plan mode) |
| `tokens_estimate` | integer | No | Unstable | Estimated token count |

### Prompt Object

```json
{
  "index": 1,
  "raw": "Original prompt text",
  "prologues": ["Prologue content"],
  "epilogues": ["Epilogue content"],
  "resolved": "Full assembled prompt with prologues and epilogues"
}
```

| Field | Type | Required | Stability | Description |
|-------|------|----------|-----------|-------------|
| `index` | integer | Yes | **Stable** | 1-based prompt index within cycle |
| `raw` | string | Yes | **Stable** | Original prompt before expansion |
| `prologues` | array | Full mode | Stable | Resolved prologue strings |
| `epilogues` | array | Full mode | Stable | Resolved epilogue strings |
| `resolved` | string | Full mode | **Stable** | Fully assembled prompt for execution |

**Plan mode differences:**
- `content` is omitted from context files
- `prologues`, `epilogues`, `resolved` are omitted from prompts
- Adds `prologues_count` and `epilogues_count` instead

---

## Stability Guarantee

Fields marked as **Stable** are guaranteed to maintain their semantics across minor version updates. Consumers should:

1. Check `schema_version` before processing
2. Only rely on Stable fields for production pipelines
3. Ignore unknown fields (forward compatibility)

**Breaking changes** (major version bump) will be announced in release notes.

---

## Usage Examples

### Render to JSON

```bash
# Single cycle (run command equivalent)
sdqctl render run workflow.conv --json > workflow.json

# Multi-cycle
sdqctl render iterate workflow.conv -n 3 --json > workflow.json

# Plan mode (references only, faster)
sdqctl render run workflow.conv --plan --json
```

### Execute from JSON

```bash
# From file
sdqctl iterate --from-json workflow.json

# From stdin
cat workflow.json | sdqctl iterate --from-json -

# With dry run
sdqctl iterate --from-json workflow.json --dry-run
```

### Transform Pipeline

```bash
# Add prefix to all prompts
sdqctl render iterate audit.conv --json \
  | jq '.cycles[].prompts[].resolved = "IMPORTANT: " + .resolved' \
  | sdqctl iterate --from-json -

# Modify specific cycle
sdqctl render iterate workflow.conv -n 5 --json \
  | jq '.cycles[2].prompts[0].resolved += "\n\nFocus on security issues."' \
  | sdqctl iterate --from-json -
```

### Environment-Specific Workflows (with jq)

```bash
ENV="production"
sdqctl render iterate deploy.conv --json \
  | jq --arg env "$ENV" '.cycles[0].prompts[0].resolved = "Environment: " + $env + "\n\n" + .resolved' \
  | sdqctl iterate --from-json -
```

### Merge Multiple Workflows

```bash
# Render both workflows
sdqctl render iterate audit.conv --json > /tmp/audit.json
sdqctl render iterate fix.conv --json > /tmp/fix.json

# Merge cycles from both (jq example)
jq -s '.[0] + {cycles: (.[0].cycles + .[1].cycles)}' \
  /tmp/audit.json /tmp/fix.json \
  | sdqctl iterate --from-json -
```

---

## Validation

The `--from-json` flag performs these validations:

1. **Schema version check** - Errors on unsupported major version
2. **Required fields** - Validates presence of `cycles`, `session_mode`, `adapter`
3. **Prompt structure** - Each cycle must have at least one prompt

```bash
# Validate without executing
sdqctl iterate --from-json workflow.json --dry-run
```

---

## Content Resolution

When executing from JSON:

- **`resolved` prompt is used directly** - No re-expansion of templates
- **Context `content` is used as-is** - No re-reading from files
- This enables **synthetic context injection** for testing

If `resolved` is missing, `raw` is used as fallback.

---

## Security Considerations

When accepting JSON from untrusted sources:

1. **Path traversal** - `context_files[].path` could reference sensitive files
2. **Command injection** - Prompts may instruct AI to run commands
3. **Size limits** - Very large inputs could exhaust memory

**Best practices:**
- Validate JSON before piping to sdqctl
- Use `--dry-run` first to inspect what would execute
- Set appropriate `MODE` restrictions in the workflow

---

## Full Example

```json
{
  "schema_version": "1.0",
  "workflow": "/home/user/project/security-audit.conv",
  "workflow_name": "security-audit",
  "mode": "full",
  "session_mode": "fresh",
  "adapter": "copilot",
  "model": "gpt-4",
  "max_cycles": 2,
  "template_variables": {
    "DATE": "2026-01-23",
    "DATETIME": "2026-01-23T12:00:00",
    "GIT_BRANCH": "main",
    "GIT_COMMIT": "abc1234",
    "CWD": "/home/user/project"
  },
  "cycles": [
    {
      "number": 1,
      "variables": {
        "DATE": "2026-01-23",
        "CYCLE_NUMBER": "1",
        "CYCLE_TOTAL": "2"
      },
      "context_files": [
        {
          "path": "/home/user/project/lib/auth.js",
          "content": "export function authenticate(user, pass) {\n  // ...\n}",
          "tokens_estimate": 150
        }
      ],
      "prompts": [
        {
          "index": 1,
          "raw": "Audit the authentication module for security issues.",
          "prologues": ["You are a security expert. Date: 2026-01-23"],
          "epilogues": ["Output findings in markdown format."],
          "resolved": "You are a security expert. Date: 2026-01-23\n\nAudit the authentication module for security issues.\n\nOutput findings in markdown format."
        }
      ]
    },
    {
      "number": 2,
      "variables": {
        "DATE": "2026-01-23",
        "CYCLE_NUMBER": "2",
        "CYCLE_TOTAL": "2"
      },
      "context_files": [
        {
          "path": "/home/user/project/lib/auth.js",
          "content": "export function authenticate(user, pass) {\n  // ...\n}",
          "tokens_estimate": 150
        }
      ],
      "prompts": [
        {
          "index": 1,
          "raw": "Propose fixes for the identified vulnerabilities.",
          "prologues": ["You are a security expert. Date: 2026-01-23"],
          "epilogues": ["Include code samples."],
          "resolved": "You are a security expert. Date: 2026-01-23\n\nPropose fixes for the identified vulnerabilities.\n\nInclude code samples."
        }
      ]
    }
  ]
}
```

---

## Related Documentation

- [IO-ARCHITECTURE.md](./IO-ARCHITECTURE.md) - Stream separation patterns
- [SYNTHESIS-CYCLES.md](./SYNTHESIS-CYCLES.md) - Iterative workflow patterns
- [../proposals/PIPELINE-ARCHITECTURE.md](../proposals/PIPELINE-ARCHITECTURE.md) - Original proposal
