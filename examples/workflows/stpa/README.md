# STPA Workflow Templates

Workflows for **Systems-Theoretic Process Analysis (STPA)** hazard analysis, supporting regulatory compliance with ISO 14971 and IEC 62304.

## Workflows

| Workflow | Purpose | Typical Use |
|----------|---------|-------------|
| `control-action-audit.conv` | Identify Unsafe Control Actions (UCAs) | Code review, new feature analysis |
| `trace-verification.conv` | Verify traceability chain completeness | Pre-release audit, compliance check |
| `gap-analysis.conv` | Close gaps iteratively | Sprint planning, remediation |

## Quick Start

```bash
# Single component UCA analysis
sdqctl run examples/workflows/stpa/control-action-audit.conv \
  --prologue "PROJECT: loop" \
  --prologue "CONTROL_ACTION: bolus"

# Verify traceability
sdqctl run examples/workflows/stpa/trace-verification.conv

# Iterative gap closure (synthesis cycles)
echo "## Progress\n\nNo gaps addressed yet." > progress.md
sdqctl iterate examples/workflows/stpa/gap-analysis.conv -n 5 --session-mode fresh
```

## Workflow Details

### control-action-audit.conv

Applies the STPA 4-question framework to identify UCAs:

1. **Not Provided** — Action not provided when needed
2. **Provided Incorrectly** — Action provided when not needed
3. **Wrong Timing** — Too early or too late
4. **Wrong Duration** — Too short, too long, wrong magnitude

**Output**: YAML-formatted UCA entries with severity classification.

### trace-verification.conv

Verifies the complete traceability chain:

```
UCA → Safety Constraint → Requirement → Specification → Test → Code
```

**Output**: Traceability matrix with gap identification.

### gap-analysis.conv

Uses **synthesis cycles** to iteratively close gaps:

1. Analyzes current gaps from `progress.md`
2. Prioritizes by severity (Class C > B > A)
3. Generates remediation artifacts
4. Updates progress for next cycle

**Requires**: `progress.md` file for state tracking.

## Severity Classification (IEC 62304)

| Class | Definition | Rigor Required |
|-------|------------|----------------|
| **C** | Death or serious injury possible | Full process |
| **B** | Non-serious injury possible | Documented process |
| **A** | No injury possible | Basic process |

## Directory Structure

Workflows expect this structure (create as needed):

```
project/
├── traceability/
│   └── stpa/
│       ├── control-structure.md    # Control hierarchy diagram
│       ├── unsafe-control-actions.md # UCA catalog
│       ├── safety-constraints.md   # Derived constraints
│       └── gaps.md                 # Open gaps tracking
├── requirements/
│   └── REQ-*.md
├── specs/
│   └── SPEC-*.md
├── tests/
├── reports/
│   └── stpa/                       # Generated reports
└── progress.md                     # Synthesis cycle state
```

## Integration with sdqctl apply

Analyze multiple components in batch:

```bash
# Audit all Swift files in Loop project
sdqctl apply examples/workflows/stpa/control-action-audit.conv \
  --components "externals/Loop/**/*.swift" \
  --output-dir reports/stpa/ \
  --progress stpa-progress.md
```

## References

- [STPA-INTEGRATION.md](../../../proposals/STPA-INTEGRATION.md) — Design proposal
- [ISO 14971:2019](https://www.iso.org/standard/72704.html) — Risk management
- [IEC 62304:2006+AMD1:2015](https://www.iec.ch/homepage) — Software lifecycle
- [STPA Handbook](https://psas.scripts.mit.edu/home/get_file.php?name=STPA_handbook.pdf) — MIT methodology
