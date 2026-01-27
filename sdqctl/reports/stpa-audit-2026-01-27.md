# STPA Artifact Audit Report

> **Date**: 2026-01-27  
> **Workspace**: rag-nightscout-ecosystem-alignment  
> **Auditor**: sdqctl automation (WP-005 step 1)

---

## Summary

| Artifact Type | Count | Status |
|---------------|-------|--------|
| UCAs (Unsafe Control Actions) | 6 | Defined in framework |
| SCs (Safety Constraints) | 2 | Partially defined |
| HAZards | 0 | Not yet defined |
| GAPs (Coverage Gaps) | 122 | Extensive coverage |

---

## Detailed Findings

### UCAs (6 unique)

All UCAs found in `docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md`:

| ID | Description | Severity |
|----|-------------|----------|
| UCA-BOLUS-001 | Bolus not delivered when carbs entered | Hyperglycemia |
| UCA-BOLUS-002 | Bolus delivered when BG < 70 mg/dL | Severe hypoglycemia |
| UCA-BOLUS-003 | Double bolus due to sync failure | Severe hypoglycemia |
| UCA-BOLUS-004 | Bolus delayed > 15 min after carbs | Postprandial spike |
| UCA-BOLUS-005 | Bolus not fully delivered (partial) | Hyperglycemia |
| UCA-OVERRIDE-002 | Conflicting targets | Not specified |

### Safety Constraints (2 unique)

| ID | Requirement |
|----|-------------|
| SC-BOLUS-003a | System SHALL deduplicate boluses by syncIdentifier |
| SC-BOLUS-003b | System SHALL NOT accept bolus if identical ID exists within 5 minutes |

### HAZards

**None defined** - This is a gap. UCAs reference hazards but no HAZ-xxx artifacts exist.

### GAPs (122 unique by domain)

| Domain | Count | Example |
|--------|-------|---------|
| ALG (Algorithm) | 8 | GAP-ALG-001 through GAP-ALG-008 |
| API | 5 | GAP-API-001 through GAP-API-005 |
| AUTH | 4 | GAP-AUTH-001 through GAP-AUTH-004 |
| BATCH | 3 | GAP-BATCH-001 through GAP-BATCH-003 |
| BLE | 5 | GAP-BLE-001 through GAP-BLE-005 |
| CARB | 5 | GAP-CARB-001 through GAP-CARB-005 |
| CGM | 6 | GAP-CGM-001 through GAP-CGM-006 |
| DELEGATE | 5 | GAP-DELEGATE-001 through GAP-DELEGATE-005 |
| DS (Data Sync) | 4 | GAP-DS-001 through GAP-DS-004 |
| ENTRY | 5 | GAP-ENTRY-001 through GAP-ENTRY-005 |
| ERR | 3 | GAP-ERR-001 through GAP-ERR-003 |
| G7 | 4 | GAP-G7-001 through GAP-G7-004 |
| INS (Insulin) | 4 | GAP-INS-001 through GAP-INS-004 |
| LF (Loop Feature) | 9 | GAP-LF-001 through GAP-LF-009 |
| LIBRE | 6 | GAP-LIBRE-001 through GAP-LIBRE-006 |
| NC | 2 | GAP-NC-001, GAP-NC-002 |
| NRG | 2 | GAP-NRG-001, GAP-NRG-002 |
| OVERRIDE | 1 | GAP-OVERRIDE-001 |
| PRED | 1 | GAP-PRED-001 |
| PROFILE | 4 | GAP-PROFILE-001 through GAP-PROFILE-004 |
| PUMP | 9 | GAP-PUMP-001 through GAP-PUMP-009 |
| REMOTE | 7 | GAP-REMOTE-001 through GAP-REMOTE-007 |
| RG | 1 | GAP-RG-001 |
| SPEC | 7 | GAP-SPEC-001 through GAP-SPEC-007 |
| SYNC | 5 | GAP-SYNC-001 through GAP-SYNC-005 |
| TREAT | 8 | GAP-TREAT-001 through GAP-TREAT-012 |
| TZ | 3 | GAP-TZ-001 through GAP-TZ-003 |
| General | 5 | GAP-001 through GAP-005 |

---

## Coverage Analysis

### UCA → SC Traceability

| UCA | Safety Constraints | Coverage |
|-----|-------------------|----------|
| UCA-BOLUS-003 | SC-BOLUS-003a, SC-BOLUS-003b | ✅ Complete |
| UCA-BOLUS-001 | None defined | ❌ Missing |
| UCA-BOLUS-002 | None defined | ❌ Missing |
| UCA-BOLUS-004 | None defined | ❌ Missing |
| UCA-BOLUS-005 | None defined | ❌ Missing |
| UCA-OVERRIDE-002 | None defined | ❌ Missing |

**SC Coverage**: 1/6 UCAs (17%)

### GAP → UCA Traceability

| GAP | Linked UCA |
|-----|------------|
| GAP-003 | UCA-BOLUS-003 |
| GAP-001 | UCA-OVERRIDE-002 |
| GAP-TREAT-012 | UCA-BOLUS-003 |

**GAP→UCA Links**: 3 (of 122 GAPs, 2.5%)

---

## Recommendations

1. **Define HAZ artifacts** - Create hazard definitions that UCAs reference
2. **Expand SC coverage** - 5 UCAs lack safety constraints (83% missing)
3. **Link GAPs to UCAs** - 97.5% of GAPs have no UCA traceability
4. **Create UCA catalog** - Expand beyond BOLUS/OVERRIDE to other control actions

---

## Source Files

- `docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md` - Primary STPA definitions
- Various gap files across `docs/` directories

---

## Next Steps (WP-005)

- [ ] Step 2: Define custom severity scale with ISO 14971 mapping
- [ ] Step 3: Cross-project UCA pattern discovery
- [ ] Step 4: STPA usage guide for ecosystem team
