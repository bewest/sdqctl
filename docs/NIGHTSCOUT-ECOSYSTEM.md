# Nightscout Ecosystem Conventions

**Status:** Reference  
**Created:** 2026-01-24  
**Audience:** sdqctl users working with Nightscout AID ecosystem projects

---

## Overview

This document defines conventions for using sdqctl with the Nightscout ecosystem of Automated Insulin Delivery (AID) projects:

| Project | Alias | Description |
|---------|-------|-------------|
| **Loop** | `loop` | iOS AID system |
| **AndroidAPS** | `aaps` | Android AID system |
| **Trio** | `trio` | Swift-based iOS AID |
| **xDrip+** | `xdrip` | Android CGM app |
| **Nightscout** | `ns`, `crm` | cgm-remote-monitor server |

---

## Workspace Configuration

### workspace.lock.json

sdqctl reads project aliases from `workspace.lock.json`, enabling cross-repository references:

```json
{
  "externals_dir": "externals",
  "repos": [
    {"alias": "loop", "name": "LoopWorkspace"},
    {"alias": "aaps", "name": "AndroidAPS"},
    {"alias": "trio", "name": "Trio"},
    {"alias": "xdrip", "name": "xDrip"},
    {"alias": "crm", "aliases": ["ns"], "name": "cgm-remote-monitor"}
  ]
}
```

### Directory Structure

Standard layout for ecosystem analysis:

```
workspace/
├── workspace.lock.json     # Alias configuration
├── externals/              # Cloned repositories
│   ├── LoopWorkspace/
│   ├── AndroidAPS/
│   ├── Trio/
│   ├── xDrip/
│   └── cgm-remote-monitor/
├── traceability/           # Cross-project analysis
│   ├── requirements.md
│   ├── gaps.md
│   └── mapping/
└── workflows/              # sdqctl workflows
    └── ecosystem-analysis.conv
```

---

## Cross-Project References

### REFCAT Syntax

Use REFCAT for precise code references across projects:

```dockerfile
# Reference Loop algorithm
REFCAT loop:LoopKit/LoopAlgorithm/Sources/LoopAlgorithm.swift#L100-L150

# Reference AAPS implementation
REFCAT aaps:app/src/main/java/info/nightscout/androidaps/MainActivity.kt#L50-L100

# Reference Trio code
REFCAT trio:Trio/Sources/APS/FreeAPS.swift#L200-L250

# Reference Nightscout API
REFCAT crm:lib/server/treatments.js#L1-L50
```

### Inline References

In documentation, use alias:path format:

```markdown
The bolus calculation in `loop:LoopKit/LoopKit/InsulinModel.swift#L100-L150`
differs from `aaps:core/main/src/main/java/info/nightscout/core/iob/iobCobCalculator/IobCobCalculatorPlugin.kt#L200-L300`.
```

---

## Artifact ID Conventions

### ID Ranges by Project

To avoid collisions in cross-project traceability:

| Project | REQ Range | GAP Range | UCA Range |
|---------|-----------|-----------|-----------|
| loop | REQ-001 to REQ-199 | GAP-LOOP-NNN | UCA-LOOP-NNN |
| aaps | REQ-200 to REQ-399 | GAP-AAPS-NNN | UCA-AAPS-NNN |
| trio | REQ-400 to REQ-599 | GAP-TRIO-NNN | UCA-TRIO-NNN |
| xdrip | REQ-600 to REQ-799 | GAP-XDRIP-NNN | UCA-XDRIP-NNN |
| ns | REQ-800 to REQ-999 | GAP-NS-NNN | UCA-NS-NNN |

### Cross-Project Gaps

When a gap spans multiple projects, use the `SYNC` domain:

```markdown
### GAP-SYNC-001: Inconsistent override duration handling
**Projects:** loop, aaps, trio
**Impact:** Override behavior differs across platforms
**Related:** REQ-010, REQ-210, REQ-410
```

### STPA Artifacts

For safety analysis across the ecosystem:

```markdown
### LOSS-001: Patient Harm
Serious harm due to incorrect insulin dosing.

### HAZ-001: Insulin Overdose  
Excessive insulin delivery leading to severe hypoglycemia.
**Leads to:** LOSS-001

### UCA-BOLUS-003: Bolus not cancelled on rapid CGM drop
**Control Action:** Cancel bolus
**Context:** CGM drops >3 mg/dL/min during delivery
**Type:** Type 1 (not providing)
**Applies to:** loop, aaps, trio
```

---

## Verification Commands

### Check Cross-Project References

```bash
# Verify all refs resolve (requires externals cloned)
sdqctl verify refs -p traceability/

# Check traceability links
sdqctl verify traceability -p traceability/ --coverage

# Verify terminology consistency
sdqctl verify terminology -p traceability/
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `Unknown alias 'loop'` | workspace.lock.json missing | Create lockfile or clone repos |
| `Broken alias reference` | File moved in external repo | Update ref path or re-clone |
| `Orphan UCA` | Missing safety constraint | Add SC-xxx for the UCA |

---

## Workflow Patterns

### Ecosystem Gap Analysis

```dockerfile
# ecosystem-gap-analysis.conv
MODEL gpt-4
ADAPTER copilot
MODE analysis
MAX-CYCLES 5

CONTEXT traceability/**/*.md
CONTEXT-OPTIONAL mapping/**/*.md

PROLOGUE """
You are analyzing gaps across the Nightscout AID ecosystem.
Projects: Loop (iOS), AAPS (Android), Trio (iOS), xDrip+ (CGM), Nightscout (server).
"""

VERIFY traceability
VERIFY-OUTPUT always

PROMPT ## Cross-Project Gap Discovery

Review the current traceability artifacts and identify:

1. **Gaps that apply to multiple projects** (GAP-SYNC-xxx)
2. **Missing safety constraints** for UCAs
3. **Inconsistent behavior** across platforms

For each finding, specify which projects are affected.

OUTPUT-FILE reports/ecosystem-gaps-{{DATE}}.md
```

### Code Comparison

```dockerfile
# compare-implementations.conv
MODEL gpt-4
ADAPTER copilot
MODE analysis

REFCAT loop:LoopKit/LoopAlgorithm/Sources/LoopAlgorithm.swift#L100-L200
REFCAT aaps:core/main/src/main/java/info/nightscout/core/iob/iobCobCalculator/IobCobCalculatorPlugin.kt#L150-L250

PROMPT ## Implementation Comparison

Compare the insulin calculation logic between Loop and AAPS:

1. **Algorithm differences** - Key calculation variations
2. **Edge cases** - How each handles boundary conditions  
3. **Safety checks** - What validations are performed

Identify any gaps or concerns.
```

---

## Terminology

Consistent terminology across ecosystem documentation:

| Term | Definition | 
|------|------------|
| **AID** | Automated Insulin Delivery |
| **CGM** | Continuous Glucose Monitor |
| **IOB** | Insulin On Board |
| **COB** | Carbohydrates On Board |
| **Basal** | Background insulin delivery rate |
| **Bolus** | Discrete insulin dose for meals/corrections |
| **Override** | Temporary adjustment to algorithm settings |
| **SMB** | Super Micro Bolus (AAPS/OpenAPS feature) |
| **Loop** | The iOS AID app (capitalize when referring to the project) |

---

## See Also

- [REFCAT-DESIGN.md](../proposals/REFCAT-DESIGN.md) — Reference syntax specification
- [ARTIFACT-TAXONOMY.md](../proposals/ARTIFACT-TAXONOMY.md) — Artifact ID conventions
- [TRACEABILITY-WORKFLOW.md](TRACEABILITY-WORKFLOW.md) — Traceability methodology
- [STPA-INTEGRATION.md](../proposals/STPA-INTEGRATION.md) — Safety analysis integration
