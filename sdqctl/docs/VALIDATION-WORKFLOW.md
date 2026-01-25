# Validation and Verification Workflow Guide

> **Status**: Stable  
> **Audience**: Human and AI workflow authors  
> **Related**: [EXTENDING-VERIFIERS.md](./EXTENDING-VERIFIERS.md), [GETTING-STARTED.md](./GETTING-STARTED.md)

---

## Overview

sdqctl provides a suite of **static verification commands** that run without AI calls. These commands form a validation pipeline that catches errors before expensive LLM execution.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  validate   │ →  │   verify    │ →  │   render    │ →  │  run/cycle  │
│  (syntax)   │    │  (refs)     │    │  (preview)  │    │  (execute)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     No LLM             No LLM            No LLM             LLM
```

---

## Command Reference

### validate — Syntax Checking

**Purpose**: Verify that a `.conv` file parses correctly and required directives are present.

```bash
# Basic validation
sdqctl validate workflow.conv

# Allow missing optional context files
sdqctl validate workflow.conv --allow-missing

# Exclude patterns from validation
sdqctl validate workflow.conv -e "*.yaml" -e "external/**"

# Validate MODEL-REQUIRES can be resolved
sdqctl validate workflow.conv --check-model

# JSON output for CI/CD
sdqctl validate workflow.conv --json
```

**What it checks**:
- ✓ File parses as valid ConversationFile
- ✓ `MODEL` directive present
- ✓ At least one `PROMPT` directive exists
- ✓ `CONTEXT` patterns resolve to files (unless `--allow-missing`)
- ✓ `MODEL-REQUIRES` can be resolved (with `--check-model`)
- ✓ Directive syntax is correct

**When to use**:
- Before committing workflow changes
- In CI/CD pipelines to gate merges
- After editing `.conv` files

### verify — Static Verification Suite

**Purpose**: Run deeper verification checks on references, links, and traceability.

```bash
# Verify @-references resolve to files
sdqctl verify refs

# Verify markdown links
sdqctl verify links

# Verify STPA traceability chains
sdqctl verify traceability

# Run all verifiers
sdqctl verify all

# JSON output for CI
sdqctl verify refs --json

# Verify specific directory
sdqctl verify refs -p examples/workflows/

# Suggest fixes for broken refs
sdqctl verify refs --suggest-fixes -v
```

**Available verifiers**:

| Verifier | Purpose | Use Case |
|----------|---------|----------|
| `refs` | Check `@path` and `alias:path` references | Documentation integrity |
| `links` | Check markdown `[text](url)` links | Link rot detection |
| `traceability` | Check REQ→SPEC→TEST chains | STPA safety analysis |

**When to use**:
- Before documentation PRs
- After refactoring file paths
- In STPA/safety workflows

### show — Display Parsed Structure

**Purpose**: Inspect how sdqctl interprets a workflow file.

```bash
sdqctl show workflow.conv
```

**Output includes**:
- Original file with syntax highlighting
- Parsed values: model, adapter, mode, max_cycles
- Context patterns and their resolution status
- Prompt previews
- Output configuration

**When to use**:
- Debugging unexpected workflow behavior
- Verifying directive interpretation
- Learning ConversationFile syntax

### render — Preview Prompts

**Purpose**: See fully-expanded prompts without executing.

```bash
# Render for run command
sdqctl render run workflow.conv

# Render for cycle command
sdqctl render cycle workflow.conv -n 3

# Quick overview (show refs, don't expand content)
sdqctl render run workflow.conv --plan

# JSON output for pipeline composition
sdqctl render cycle workflow.conv --json
```

**What it expands**:
- Template variables (`{{DATE}}`, `{{CYCLE_NUMBER}}`, etc.)
- Context file content (`@path/to/file.md`)
- Prologue/epilogue injection
- Cycle-specific variations

**When to use**:
- Before expensive LLM calls
- Debugging template expansion
- Pipeline composition with `--from-json`

### refcat — Extract File Content

**Purpose**: Extract precise file content with line-level granularity.

```bash
# Extract line range
sdqctl refcat @path/file.py#L10-L50

# Single line
sdqctl refcat @path/file.py#L42

# Line to end of file
sdqctl refcat @path/file.py#L100-

# Multiple refs
sdqctl refcat @file1.py#L10 @file2.py#L20-L30

# Validate without output
sdqctl refcat @file.py#L10-L50 --validate-only

# JSON output
sdqctl refcat @file.py#L10-L50 --json

# Output without attribution header
sdqctl refcat @file.py#L10-L50 --no-attribution

# Output normalized ref spec for round-tripping
sdqctl refcat @file.py#L10-L50 --spec
```

**Reference syntax**:
```
@path/file.py              # Full file
@path/file.py#L10-L50      # Lines 10-50
@path/file.py#L10          # Single line
@path/file.py#L10-         # Line 10 to EOF
alias:path/file.py#L10     # Cross-repo with alias
```

**When to use**:
- Extracting specific code sections for context
- Cross-repository reference validation
- Building precise AI context

---

## Decision Tree: Which Command?

```
Need to check a .conv file?
├── Is it a syntax/parse issue?
│   └── YES → sdqctl validate workflow.conv
│
├── Are references broken?
│   └── YES → sdqctl verify refs
│
├── Want to see parsed structure?
│   └── YES → sdqctl show workflow.conv
│
├── Want to preview prompts?
│   └── YES → sdqctl render run workflow.conv
│
└── Need precise file extraction?
    └── YES → sdqctl refcat @file.py#L10-L50
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Validate Workflows

on:
  pull_request:
    paths:
      - 'workflows/**/*.conv'
      - 'docs/**/*.md'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install sdqctl
        run: pip install -e .
      
      - name: Validate workflow syntax
        run: |
          for f in workflows/*.conv; do
            sdqctl validate "$f" --json || exit 1
          done
      
      - name: Verify references
        run: sdqctl verify refs --json
      
      - name: Verify links
        run: sdqctl verify links --json
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate any staged .conv files
for file in $(git diff --cached --name-only --diff-filter=ACM | grep '\.conv$'); do
  if ! sdqctl validate "$file"; then
    echo "Validation failed: $file"
    exit 1
  fi
done

# Verify refs if docs changed
if git diff --cached --name-only | grep -q '\.md$'; then
  sdqctl verify refs || exit 1
fi
```

### Pipeline Composition

Use render + transform + execute for dynamic workflows:

```bash
# Render, transform with jq, execute
sdqctl render cycle workflow.conv --json \
  | jq '.cycles[0].prompts[0].resolved += " (transformed)"' \
  | sdqctl cycle --from-json -

# Conditional workflow based on verify results
if sdqctl verify refs --json | jq -e '.passed'; then
  sdqctl run workflow.conv
else
  sdqctl run fix-refs.conv
fi
```

---

## Interactive Development Patterns

### Pattern 1: Edit-Validate-Run Loop

```bash
# 1. Edit workflow
vim workflows/audit.conv

# 2. Validate syntax
sdqctl validate workflows/audit.conv

# 3. Preview prompts
sdqctl render run workflows/audit.conv

# 4. Test with mock
sdqctl run workflows/audit.conv --adapter mock -v

# 5. Run for real
sdqctl run workflows/audit.conv --adapter copilot
```

### Pattern 2: Debug Reference Issues

```bash
# 1. Check which refs are broken (excludes .venv, node_modules by default)
sdqctl verify refs -v

# 2. Exclude additional directories
sdqctl verify refs -e "examples" -e "tests"

# 3. Get fix suggestions
sdqctl verify refs --suggest-fixes

# 4. Validate specific file extraction
sdqctl refcat @path/to/file.py#L10-L50 --validate-only

# 5. See what would be included
sdqctl refcat @path/to/file.py#L10-L50
```

### Pattern 3: Understanding a Workflow

```bash
# 1. See the parsed structure
sdqctl show mystery-workflow.conv

# 2. See what prompts would be sent
sdqctl render run mystery-workflow.conv

# 3. See cycle-by-cycle breakdown
sdqctl render cycle mystery-workflow.conv -n 3
```

---

## Common Error Patterns

### "No PROMPT directives found"

```bash
$ sdqctl validate broken.conv
  ✗ No PROMPT directives found
```

**Fix**: Add at least one `PROMPT` directive:
```dockerfile
PROMPT Analyze the codebase.
```

### "Context pattern matches no files"

```bash
$ sdqctl validate workflow.conv
  ✗ Context pattern matches no files: @lib/missing/*.py
```

**Fixes**:
1. Correct the path: `CONTEXT @lib/existing/*.py`
2. Make optional: `CONTEXT-OPTIONAL @lib/missing/*.py`
3. Allow missing: `sdqctl validate --allow-missing`
4. Use lenient mode in file: `VALIDATION-MODE lenient`

### "Broken reference: @path/file.md"

```bash
$ sdqctl verify refs
  ✗ FAILED: 3 broken references
    ERROR docs/README.md:42: @lib/old-path.py
```

**Fixes**:
1. Update the reference to correct path
2. Use `--suggest-fixes` to find moved files
3. Exclude from verification: `-e "legacy/**"`

### "Unknown alias 'foo'"

```bash
$ sdqctl verify refs
  ERROR: Unknown alias 'foo' in foo:path/file.py
```

**Fixes**:
1. Add alias to `workspace.lock.json`
2. Add to `~/.sdqctl/aliases.yaml`
3. Use full path instead

---

## In-Workflow Verification

Use the `VERIFY` directive to run verification during workflow execution:

```dockerfile
# Verify refs before proceeding
VERIFY refs

# Continue on verification failure
VERIFY-ON-ERROR continue
VERIFY links

# Only inject output on failure
VERIFY-OUTPUT on-error
VERIFY traceability

# Combine with ELIDE for AI-assisted fixes
VERIFY refs
ELIDE
PROMPT Fix any broken references found above.
```

---

## Related Documentation

- [GETTING-STARTED.md](./GETTING-STARTED.md) — Basic sdqctl usage
- [EXTENDING-VERIFIERS.md](./EXTENDING-VERIFIERS.md) — Creating custom verifiers
- [PIPELINE-SCHEMA.md](./PIPELINE-SCHEMA.md) — JSON schema for `--from-json`
- [proposals/REFCAT-DESIGN.md](../proposals/REFCAT-DESIGN.md) — Full REFCAT specification
- [proposals/VERIFICATION-DIRECTIVES.md](../proposals/VERIFICATION-DIRECTIVES.md) — VERIFY directive design
