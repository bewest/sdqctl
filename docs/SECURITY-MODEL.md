# Security Model

> **Added**: 2026-01-25 | **Source**: BACKLOG.md §Security Concerns, QUIRKS.md Code Quality Review

This document describes the security model for sdqctl, a developer tool for orchestrating AI-assisted workflows.

---

## Threat Model

### What sdqctl Is

sdqctl is a **developer tool** designed for use in trusted environments:

- Local development workstations
- CI/CD pipelines under operator control
- Automated testing environments

### What sdqctl Is NOT

sdqctl is **not designed for**:

- Multi-tenant environments
- Processing untrusted workflow files
- Production servers handling external input

### Trust Boundaries

| Component | Trust Level | Rationale |
|-----------|-------------|-----------|
| Workflow files (`.conv`) | **Fully trusted** | Author controls all directives |
| User running sdqctl | **Fully trusted** | Has shell access anyway |
| AI model responses | **Partially trusted** | Tool use is sandboxed by SDK |
| Environment variables | **Trusted** | Operator controls environment |

---

## Directive Security

### ALLOW-SHELL

**Severity**: HIGH  
**Location**: `run.py` subprocess handling

The `ALLOW-SHELL` directive enables shell command execution in prompts.

```dockerfile
# Enables shell execution - use with caution
ALLOW-SHELL true
```

#### Risks

1. **Arbitrary command execution**: Any command the user can run
2. **No sandboxing**: Commands run with user's full permissions
3. **Environment inheritance**: Child processes inherit environment

#### Mitigations

| Mitigation | Status | Notes |
|------------|--------|-------|
| Explicit opt-in | ✅ Implemented | `ALLOW-SHELL` must be declared |
| Default disabled | ✅ Implemented | Shell commands fail without directive |
| Logged execution | ✅ Implemented | All shell commands logged at INFO |

#### Safe Usage Patterns

```dockerfile
# ✅ Good: Explicit, specific commands
ALLOW-SHELL true
RUN-PROMPT Run `pytest tests/unit/` and report failures

# ❌ Avoid: Open-ended shell access
ALLOW-SHELL true
RUN-PROMPT Do whatever you need to fix the build
```

#### CI/CD Recommendations

```yaml
# GitHub Actions - limit permissions
jobs:
  sdqctl:
    permissions:
      contents: read  # No write access
    steps:
      - run: sdqctl run workflow.conv --dry-run  # Preview first
```

---

### RUN_ENV

**Severity**: MEDIUM  
**Location**: `conversation.py` environment handling

The `RUN_ENV` directive injects environment variables into subprocess execution.

```dockerfile
RUN_ENV PATH=/custom/bin:$PATH
RUN_ENV DEBUG=1
```

#### Risks

1. **LD_PRELOAD injection**: Could load malicious libraries
2. **PATH manipulation**: Could execute unintended binaries
3. **Credential exposure**: Secrets in env vars visible to subprocesses

#### Dangerous Variables

| Variable | Risk | Notes |
|----------|------|-------|
| `LD_PRELOAD` | HIGH | Loads arbitrary shared libraries |
| `LD_LIBRARY_PATH` | HIGH | Library search path manipulation |
| `PYTHONPATH` | MEDIUM | Python module injection |
| `PATH` | MEDIUM | Binary resolution order |

#### Safe Usage Patterns

```dockerfile
# ✅ Good: Application-specific config
RUN_ENV NODE_ENV=test
RUN_ENV PYTEST_CURRENT_TEST=1

# ❌ Avoid: System-level manipulation
RUN_ENV LD_PRELOAD=/path/to/hook.so
RUN_ENV PATH=/tmp/bin:$PATH
```

#### Secret Masking

When workflows are serialized (e.g., in checkpoints), environment variables with sensitive-looking names are automatically masked:

| Key Pattern | Example | Serialized As |
|-------------|---------|---------------|
| `*KEY*` | `API_KEY=sk-123456` | `API_KEY=sk-***` |
| `*SECRET*` | `MY_SECRET=abc` | `MY_SECRET=abc***` |
| `*TOKEN*` | `AUTH_TOKEN=xyz` | `AUTH_TOKEN=xyz***` |
| `*PASSWORD*` | `DB_PASSWORD=pass` | `DB_PASSWORD=pas***` |
| `*AUTH*` | `GITHUB_AUTH=ghp_...` | `GITHUB_AUTH=ghp***` |
| `*CREDENTIAL*` | `CRED_ID=cred123` | `CRED_ID=cre***` |

Non-sensitive variables (e.g., `DEBUG=1`, `NODE_ENV=test`) are serialized as-is.

#### Hardening (Future)

Consider implementing an environment variable allowlist:

```python
# Proposed: sdqctl/core/security.py
SAFE_ENV_VARS = {
    "NODE_ENV", "PYTEST_*", "DEBUG", "LOG_LEVEL",
    "CI", "GITHUB_*", "GITLAB_*"
}
```

---

### OUTPUT-FILE / OUTPUT-DIR

**Severity**: LOW  
**Location**: `run.py` file output handling

Output directives write AI-generated content to files.

```dockerfile
OUTPUT-FILE reports/{{DATE}}-analysis.md
OUTPUT-DIR artifacts/
```

#### Risks

1. **Path traversal**: `../../../etc/passwd` style attacks
2. **Symlink following**: Writing through symlinks
3. **Overwrite protection**: Replacing important files

#### Current Protections

| Protection | Status | Notes |
|------------|--------|-------|
| Relative path enforcement | ⚠️ Partial | Paths relative to workflow location |
| Symlink resolution | ❌ Not implemented | `.resolve()` not called |
| Overwrite prompts | ❌ Not implemented | Silent overwrite |

#### Safe Usage Patterns

```dockerfile
# ✅ Good: Explicit subdirectory
OUTPUT-DIR ./reports/
OUTPUT-FILE ./artifacts/{{WORKFLOW_NAME}}.md

# ❌ Avoid: Parent traversal
OUTPUT-FILE ../../../tmp/output.md
OUTPUT-DIR /tmp/
```

#### Recommended Hardening

```bash
# Run from dedicated workspace
cd /workspace/project
sdqctl run workflow.conv

# Use --dry-run to preview outputs
sdqctl run workflow.conv --dry-run
```

---

### Path Handling

**Severity**: MEDIUM  
**Location**: `conversation.py` path resolution

Workflow files reference external files via `INCLUDE`, `COMPONENT`, and `CONTEXT-FILE`.

```dockerfile
INCLUDE ./shared/prologue.conv
COMPONENT-FILE ./components/analyzer.md
CONTEXT-FILE ./data/input.json
```

#### Current Behavior

1. Paths resolved relative to workflow file location
2. No canonicalization before access checks
3. Symlinks followed without validation

#### Risks

| Scenario | Risk | Example |
|----------|------|---------|
| Symlink escape | MEDIUM | `components/link` → `/etc/passwd` |
| Relative escape | LOW | `../../sensitive/data.json` |
| Absolute paths | LOW | `/home/user/.ssh/id_rsa` |

#### Recommended Patterns

```dockerfile
# ✅ Good: Explicit relative paths
INCLUDE ./includes/header.conv
COMPONENT-FILE ./components/analyzer.md

# ❌ Avoid: Absolute paths
INCLUDE /home/shared/workflow.conv

# ❌ Avoid: Parent traversal
INCLUDE ../../other-project/secrets.conv
```

---

## CI/CD Integration

### Principle of Least Privilege

```yaml
# GitHub Actions example
jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read      # Read-only checkout
      pull-requests: write # Comment on PRs only
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate workflow
        run: sdqctl validate workflow.conv
        
      - name: Dry run
        run: sdqctl run workflow.conv --dry-run
        
      - name: Execute (if needed)
        run: sdqctl run workflow.conv
        env:
          ALLOW_SHELL: "false"  # Extra safety
```

### Pre-commit Validation

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: sdqctl-validate
        name: Validate .conv files
        entry: sdqctl validate
        language: system
        files: \.conv$
```

### Secrets Management

```bash
# ❌ Don't: Embed secrets in workflows
RUN_ENV API_KEY=sk-secret-key

# ✅ Do: Reference from environment
RUN_ENV API_KEY=$API_KEY  # Inherited from CI secrets
```

---

## Logging and Auditing

### What Gets Logged

| Event | Level | Details |
|-------|-------|---------|
| Shell command execution | INFO | Command, duration, exit code |
| File writes | INFO | Path, size |
| Tool invocations | INFO | Tool name, arguments (summarized) |
| Environment setup | DEBUG | Variable names (not values) |

### Enabling Audit Logging

```bash
# Full verbose logging
sdqctl -vvv run workflow.conv 2>&1 | tee audit.log

# Structured JSON output
sdqctl run workflow.conv --json-errors 2>&1 | jq
```

---

## Summary

| Directive | Severity | Key Mitigation |
|-----------|----------|----------------|
| `ALLOW-SHELL` | HIGH | Explicit opt-in, specific commands |
| `RUN_ENV` | MEDIUM | Avoid system-level variables |
| `OUTPUT-FILE` | LOW | Use relative paths, `--dry-run` |
| Path handling | MEDIUM | Avoid traversal, validate inputs |

**Core principle**: sdqctl trusts the workflow author. Security controls exist to prevent accidents, not malicious workflows.

---

## See Also

- [GETTING-STARTED.md](GETTING-STARTED.md) - Safe usage patterns
- [WORKFLOW-DESIGN.md](WORKFLOW-DESIGN.md) - Directive reference
- [COMMANDS.md](COMMANDS.md) - CLI options (`--dry-run`, `-v`)
- [BACKLOG.md §Security Concerns](../proposals/BACKLOG.md) - Known issues
