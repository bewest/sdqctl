# Artifact Templates

This directory contains markdown templates for traceability artifacts as defined in the [ARTIFACT-TAXONOMY proposal](../../../proposals/ARTIFACT-TAXONOMY.md).

## Available Templates

### Core Traceability Artifacts

| Template | Purpose | Pattern |
|----------|---------|---------|
| [REQ-template.md](REQ-template.md) | Requirement | `REQ-{DOMAIN}-NNN` |
| [SPEC-template.md](SPEC-template.md) | Specification | `SPEC-NNN` |
| [TEST-template.md](TEST-template.md) | Test Case | `TEST-NNN` |
| [GAP-template.md](GAP-template.md) | Implementation Gap | `GAP-{DOMAIN}-NNN` |

### STPA Safety Artifacts

| Template | Purpose | Pattern |
|----------|---------|---------|
| [LOSS-template.md](LOSS-template.md) | System-level Loss | `LOSS-NNN` |
| [HAZ-template.md](HAZ-template.md) | Hazard | `HAZ-NNN` |
| [UCA-template.md](UCA-template.md) | Unsafe Control Action | `UCA-{DOMAIN}-NNN` |
| [SC-template.md](SC-template.md) | Safety Constraint | `SC-{DOMAIN}-NNNx` |

### Development Artifacts

| Template | Purpose | Pattern |
|----------|---------|---------|
| [Q-template.md](Q-template.md) | Quirk (known behavior) | `Q-NNN` |
| [BUG-template.md](BUG-template.md) | Bug Report | `BUG-NNN` |
| [PROP-template.md](PROP-template.md) | Proposal | `PROP-NNN` |

## Usage

### Create New Artifact

1. Copy the appropriate template
2. Replace placeholders: `{DOMAIN}`, `{NNN}`, `{Title}`, `YYYY-MM-DD`
3. Fill in required sections
4. Link to related artifacts

### Example: New Requirement

```bash
cp examples/templates/artifacts/REQ-template.md docs/requirements/REQ-CGM-010.md
```

Then edit to fill in:
- `REQ-{DOMAIN}-NNN` → `REQ-CGM-010`
- `{Title}` → `CGM Data Freshness`
- `YYYY-MM-DD` → `2026-01-24`

### Example: New UCA

```bash
cp examples/templates/artifacts/UCA-template.md traceability/stpa/UCA-BOLUS-003.md
```

## Relationship Hierarchy

```
LOSS
  └── HAZ (leads_to)
        └── UCA (causes)
              └── SC (mitigates)
                    └── REQ (implemented_by)
                          └── SPEC (specified_by)
                                └── TEST (verified_by)
                                      └── CODE (implemented_in)
```

## Validation

Use `sdqctl verify traceability` to check:
- All artifacts follow ID patterns
- Required relationships exist
- No orphaned artifacts

```bash
sdqctl verify traceability docs/ --strict
```

## See Also

- [ARTIFACT-TAXONOMY.md](../../../proposals/ARTIFACT-TAXONOMY.md) - Full taxonomy specification
- [TRACEABILITY-WORKFLOW.md](../../../docs/TRACEABILITY-WORKFLOW.md) - Workflow guidance
- [STPA-INTEGRATION.md](../../../proposals/STPA-INTEGRATION.md) - STPA integration details
