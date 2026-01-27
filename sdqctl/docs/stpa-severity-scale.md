# STPA Severity Scale

> **Version**: 1.0  
> **Created**: 2026-01-27  
> **Work Package**: WP-005 step 2  
> **Standard Reference**: ISO 14971:2019

---

## Custom Severity Scale

A 4-level scale optimized for diabetes management systems, with ISO 14971 mappings.

| Level | Name | Description | ISO 14971 Mapping |
|-------|------|-------------|-------------------|
| **S4** | Critical | Death or life-threatening injury (e.g., severe hypoglycemia causing unconsciousness) | Catastrophic |
| **S3** | Serious | Serious injury or medical intervention required (e.g., hypoglycemia requiring glucagon) | Critical |
| **S2** | Moderate | Minor injury or temporary impairment (e.g., extended hyperglycemia >250 mg/dL) | Serious |
| **S1** | Minor | Inconvenience or no injury (e.g., incorrect trend display, UI glitch) | Minor/Negligible |

---

## Domain-Specific Examples

### Insulin Delivery

| Severity | Example Scenario |
|----------|------------------|
| S4 | Undetected double bolus causing BG < 40 mg/dL |
| S3 | Bolus delivered when BG < 70 mg/dL |
| S2 | Bolus timing delayed >30 minutes |
| S1 | Bolus history display error |

### CGM Data

| Severity | Example Scenario |
|----------|------------------|
| S4 | CGM data dropout during active insulin delivery |
| S3 | Incorrect calibration causing 40% reading error |
| S2 | 15-minute data lag during rapid BG change |
| S1 | Minor display rounding discrepancy |

### Closed Loop Control

| Severity | Example Scenario |
|----------|------------------|
| S4 | Algorithm override failure during hypoglycemia |
| S3 | Basal suspension not triggered at threshold |
| S2 | Suboptimal temp basal calculation |
| S1 | Loop status icon delay |

---

## UCA Severity Assignments

Based on audit findings from `reports/stpa-audit-2026-01-27.md`:

| UCA ID | Description | Severity |
|--------|-------------|----------|
| UCA-BOLUS-001 | Bolus not delivered when carbs entered | S2 (Moderate) |
| UCA-BOLUS-002 | Bolus delivered when BG < 70 mg/dL | S3 (Serious) |
| UCA-BOLUS-003 | Double bolus due to sync failure | S4 (Critical) |
| UCA-BOLUS-004 | Bolus delivered too late (>30 min delay) | S2 (Moderate) |
| UCA-BOLUS-005 | Bolus continues after user cancel | S3 (Serious) |
| UCA-OVERRIDE-002 | Override accepted when loop suspended | S3 (Serious) |

---

## ISO 14971 Probability Matrix

For risk assessment, combine severity with probability:

| Probability | S1 (Minor) | S2 (Moderate) | S3 (Serious) | S4 (Critical) |
|-------------|------------|---------------|--------------|---------------|
| Frequent | Medium | High | Unacceptable | Unacceptable |
| Probable | Low | Medium | High | Unacceptable |
| Occasional | Low | Medium | High | Unacceptable |
| Remote | Negligible | Low | Medium | High |
| Improbable | Negligible | Negligible | Low | Medium |

---

## Usage Guidelines

1. **Assign severity at UCA definition time** - Each UCA must have a severity level
2. **Safety Constraints inherit severity** - SC derives severity from parent UCA
3. **Review quarterly** - Reassess assignments as system understanding evolves
4. **Document rationale** - Non-obvious assignments require justification

---

## References

- ISO 14971:2019 Medical devices — Application of risk management
- IEC 62304:2006 Medical device software — Software life cycle processes
- STPA Handbook (Leveson & Thomas, 2018)
