# Proposal: STPA Integration for Workflow-Driven Safety Analysis

> **Status**: Partial Implementation ✅  
> **Date**: 2026-01-23  
> **Updated**: 2026-01-24  
> **Author**: sdqctl development  
> **Scope**: STPA hazard analysis automation, regulatory traceability support  
> **Related**: [rag-nightscout STPA-TRACEABILITY-FRAMEWORK.md](https://github.com/bewest/rag-nightscout-ecosystem-alignment/docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md)

---

## Implementation Status

| Feature | Status | Location |
|---------|--------|----------|
| STPA workflow templates | ✅ Complete | `examples/workflows/stpa/` |
| Traceability verifier | ✅ Complete | `sdqctl/verifiers/traceability.py` |
| LOSS/HAZ/UCA/SC patterns | ✅ Complete | Traceability verifier patterns |
| Coverage reporting | ✅ Complete | `sdqctl verify traceability --coverage` |
| STPA template variables | ❌ Future work | Not implemented |
| VERIFY-TRACE directive | ❌ Future work | Not implemented |
| VERIFY-COVERAGE directive | ❌ Future work | Not implemented |
| VERIFY-IMPLEMENTED directive | ❌ Future work | Not implemented |
| CI JSON output format | ❌ Future work | Not implemented |

---

## Summary

This proposal extends sdqctl's capabilities to support STPA (Systems-Theoretic Process Analysis) workflows for regulatory-compatible hazard analysis and traceability. It defines how sdqctl can automate UCA (Unsafe Control Action) cataloging, trace verification, and safety constraint validation.

---

## Regulatory Standards Context

Medical device software typically must satisfy **multiple regulatory frameworks simultaneously**. The two foundational international standards are:

### ISO 14971 — Risk Management

Governs the **risk management process** for medical devices:
- Hazard identification and risk analysis
- Risk evaluation and control
- Residual risk acceptability
- Risk-benefit analysis

**sdqctl relevance**: STPA workflows produce hazard analysis artifacts that feed into ISO 14971 risk management files.

### IEC 62304 — Software Lifecycle

Governs **software development processes** for medical devices:
- Software safety classification (Class A, B, C)
- Software development planning
- Requirements analysis and traceability
- Verification and validation

**sdqctl relevance**: Traceability pipelines (REQ → SPEC → TEST → CODE → VERIFY) directly support IEC 62304 documentation requirements. Software classification (Class A/B/C) determines the rigor required.

### Multi-Jurisdiction Applicability

| Jurisdiction | Primary Regulation | Recognizes ISO 14971 | Recognizes IEC 62304 |
|--------------|-------------------|---------------------|---------------------|
| **USA (FDA)** | 21 CFR 820, 21 CFR Part 11 | Yes (consensus std) | Yes (consensus std) |
| **EU** | MDR 2017/745 | Yes (harmonized) | Yes (harmonized) |
| **Canada** | CMDR, SOR/98-282 | Yes | Yes |
| **Japan** | MHLW Ordinance 169 | Yes | Yes |

**Key insight**: Building sdqctl workflows around ISO 14971 + IEC 62304 provides a foundation that satisfies regulators globally, not just FDA.

### How the Standards Work Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Medical Device Development                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ISO 14971 (Risk)              IEC 62304 (Lifecycle)                   │
│   ┌─────────────────┐           ┌─────────────────────────┐             │
│   │ Hazard Analysis │ ────────▶ │ Software Classification │             │
│   │ (STPA/UCAs)     │           │ (Class A/B/C)           │             │
│   └────────┬────────┘           └───────────┬─────────────┘             │
│            │                                │                           │
│            │ informs rigor                  │ determines process        │
│            ▼                                ▼                           │
│   ┌─────────────────┐           ┌─────────────────────────┐             │
│   │ Risk Controls   │ ◀──────── │ REQ → SPEC → TEST → CODE│             │
│   │ (mitigations)   │           │ (traceability pipeline) │             │
│   └─────────────────┘           └─────────────────────────┘             │
│                                                                         │
│   sdqctl automates:                                                     │
│   • UCA discovery (STPA workflows)                                      │
│   • Traceability validation (VERIFY directives)                         │
│   • Documentation synthesis (trace synthesis cycles)                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Motivation

The rag-nightscout-ecosystem-alignment workspace is developing an STPA-based traceability framework for the AID (Automated Insulin Delivery) ecosystem. sdqctl is already integrated for workflow automation. This proposal bridges the two:

- **STPA provides**: Systematic hazard identification methodology
- **sdqctl provides**: Repeatable, AI-assisted workflow execution

Together, they enable:
1. Automated UCA discovery in source code
2. Trace validation between UCAs → Requirements → Tests
3. CI-compatible safety verification

---

## Proposed Features

### 1. STPA Template Variables

New template variables for STPA-aware workflows:

```dockerfile
# Available in STPA workflows
{{PROJECT}}           # e.g., "loop", "aaps"
{{CONTROL_ACTION}}    # e.g., "bolus", "basal", "override"
{{SEVERITY_TIER}}     # e.g., "tier1", "tier2"
{{UCA_PREFIX}}        # e.g., "UCA-BOLUS"
```

### 2. STPA Workflow Conventions

Standardized workflow patterns for STPA analysis:

```dockerfile
# stpa-control-action-audit.conv
MODEL claude-sonnet-4.5
MAX-CYCLES 2

# Load STPA context
@traceability/stpa/control-structure.md
@traceability/stpa/unsafe-control-actions.md

# Load target module
@externals/{{PROJECT}}/{{MODULE}}

PROMPT Analyze this code for {{CONTROL_ACTION}} control actions.
       Apply the STPA 4-question framework:
       1. Could the action NOT be provided when needed?
       2. Could the action be provided when NOT needed?
       3. Could the timing be wrong (too early/late)?
       4. Could the duration be wrong (too short/long)?
       
       For each potential UCA:
       - Assign ID: {{UCA_PREFIX}}-NNN
       - Rate severity: Class A/B/C (IEC 62304)
       - Link to existing GAPs if applicable
       
       Output: YAML format for unsafe-control-actions.md

RUN python tools/validate_uca_format.py --stdin
ELIDE
PROMPT Review validation results. Fix any format issues.
```

### 3. VERIFY Extensions for STPA

Building on the VERIFICATION-DIRECTIVES proposal:

```dockerfile
# Verify UCA → REQ tracing
VERIFY-TRACE UCA-BOLUS-003 -> REQ-020
  EXPECT linked
  ON-FAIL warn "UCA not linked to requirement"

# Verify all Tier 1 UCAs have tests
VERIFY-COVERAGE traceability/stpa/unsafe-control-actions.md
  FILTER severity:Class-C
  EXPECT test-linked >= 100%
  ON-FAIL fail "Critical UCA lacks test coverage"

# Verify safety constraints implemented
VERIFY-IMPLEMENTED SC-BOLUS-003a
  IN externals/Loop/LoopCore/
  PATTERN "func.*validateGlucose\|guard.*glucose.*<"
  EXPECT found
  ON-FAIL warn "Safety constraint not found in code"
```

### 4. STPA Analysis Report Format

Standardized JSON output for CI integration:

```json
{
  "analysis_type": "stpa",
  "project": "loop",
  "control_action": "bolus",
  "ucas_found": [
    {
      "id": "UCA-BOLUS-006",
      "type": "provided_incorrectly",
      "description": "Bolus delivered based on stale CGM data (>10 min old)",
      "severity": "Class-C",
      "hazard": "Hypoglycemia from incorrect correction",
      "causal_factors": ["CF-CGM-003: CGM data age not validated"],
      "related_gaps": ["GAP-CGM-005"],
      "status": "new"
    }
  ],
  "trace_coverage": {
    "uca_to_req": 0.85,
    "req_to_test": 0.72,
    "gaps_linked": 0.90
  },
  "recommendations": [
    "Create REQ-XXX for CGM data age validation",
    "Add test for stale CGM rejection"
  ]
}
```

---

## Integration with Existing Proposals

### RUN-BRANCHING

STPA workflows may need conditional branching:

```dockerfile
RUN python tools/check_uca_exists.py {{UCA_ID}}
ON-SUCCESS
  PROMPT Update existing UCA entry with new findings.
ON-FAILURE
  PROMPT Create new UCA entry using template.
```

### PIPELINE-ARCHITECTURE

External transformation for STPA scope selection:

```bash
# Select only Tier 1 projects for rigorous analysis
sdqctl render cycle stpa-audit.conv --json \
  | jq '.template_variables.SEVERITY_TIER = "tier1"' \
  | sdqctl cycle --from-json -
```

### VERIFICATION-DIRECTIVES

STPA-specific verification patterns become a standard set:

```dockerfile
INCLUDE verification/stpa-checks.conv
# Imports standard VERIFY-TRACE, VERIFY-COVERAGE, etc.
```

---

## Implementation Plan

### Phase 1: Template Variables (Week 1)
- Add STPA-related template variables
- Document conventions for STPA workflows

### Phase 2: Workflow Library (Week 2-3)
- Create `workflows/stpa/` in rag-nightscout
- Implement: control-action-audit.conv, trace-verification.conv
- Test with Loop bolus analysis

### Phase 3: VERIFY Extensions (Week 4-5)
- Extend VERIFY directive for trace checking
- Implement VERIFY-COVERAGE for STPA artifacts
- Add CI integration examples

### Phase 4: Reporting (Week 6)
- Standardize JSON output format
- Create summary report generator
- Integration with rag-nightscout tooling

---

## Success Criteria

1. **Automation**: UCA discovery can be triggered by sdqctl workflow
2. **Validation**: Trace completeness checked automatically
3. **CI-ready**: JSON output parseable by CI systems
4. **Reusable**: Same patterns work for all 16 external projects
5. **Multi-jurisdiction**: Artifacts satisfy ISO 14971 + IEC 62304 (recognized globally)

---

## Future Work

- **Batch analysis**: Analyze all Tier 1 projects in parallel
- **Delta detection**: Identify UCAs affected by code changes
- **Severity propagation**: Update downstream artifacts when UCA severity changes
- **Cross-project UCAs**: UCAs that span multiple projects (e.g., Nightscout ↔ Loop sync)

---

## References

### sdqctl Proposals
- [STPA-TRACEABILITY-FRAMEWORK.md](../../rag-nightscout-ecosystem-alignment/docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md) - Main STPA proposal
- [VERIFICATION-DIRECTIVES.md](./VERIFICATION-DIRECTIVES.md) - Verification directive proposal
- [RUN-BRANCHING.md](./RUN-BRANCHING.md) - Conditional branching proposal
- [PIPELINE-ARCHITECTURE.md](./PIPELINE-ARCHITECTURE.md) - External transformation proposal

### Regulatory Standards
- **ISO 14971:2019** — Medical devices — Application of risk management to medical devices
- **IEC 62304:2006+AMD1:2015** — Medical device software — Software life cycle processes
- **FDA 21 CFR 820** — Quality System Regulation
- **EU MDR 2017/745** — Regulation on medical devices
