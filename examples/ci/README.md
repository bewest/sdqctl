# CI/CD Integration Examples

Examples for integrating sdqctl into CI/CD pipelines.

---

## Available Examples

| File | Description | Platform |
|------|-------------|----------|
| `validate-workflows.yml` | Validate .conv files on PR | GitHub Actions |
| `verify-refs.yml` | Run static verification suite | GitHub Actions |

---

## GitHub Actions

### Validate Workflows on Pull Request

Copy `validate-workflows.yml` to `.github/workflows/` to validate all workflow files on every PR:

```yaml
# See validate-workflows.yml for full example
```

**What it does:**
- Runs `sdqctl validate` on all `.conv` files
- Runs `sdqctl verify all` for static checks
- Fails PR if any validation errors

### Verify References

Copy `verify-refs.yml` to `.github/workflows/` for comprehensive verification:

```yaml
# See verify-refs.yml for full example
```

**What it does:**
- Verifies `@file` references resolve
- Checks markdown link validity
- Validates traceability chains (if using STPA)

---

## Usage Tips

### No AI Calls Required

All validation commands run **without AI**:

```bash
sdqctl validate workflow.conv    # Syntax check
sdqctl verify refs               # Reference check
sdqctl verify links              # Link check
sdqctl render run workflow.conv  # Preview prompts
```

These are safe for CI/CD - no tokens, no costs, no auth required.

### Strict Mode for CI

Use `--strict` to fail on any issue:

```bash
sdqctl validate workflow.conv --strict
```

### JSON Output for Parsing

Use `--json` for machine-readable output:

```bash
sdqctl verify all --json > verification-report.json
```

---

## See Also

- [GETTING-STARTED.md §Validation & CI/CD](../../docs/GETTING-STARTED.md#validation--cicd)
- [VALIDATION-WORKFLOW.md](../../docs/VALIDATION-WORKFLOW.md)
