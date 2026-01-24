# ARTIFACT-TAXONOMY: Comprehensive Traceability Artifact Enumeration

**Status:** PROPOSAL  
**Date:** 2026-01-24  
**Author:** sdqctl team  
**Priority:** P1

---

## Abstract

This proposal defines a comprehensive taxonomy of artifact types that sdqctl should recognize and trace. It establishes naming conventions, relationship patterns, and validation rules for traceability across requirements, specifications, tests, code, and safety analysis.

---

## Motivation

Effective traceability requires:
1. **Consistent artifact identification** - Unique, parseable IDs
2. **Clear relationships** - Known links between artifact types
3. **Automated validation** - Tools that verify completeness
4. **Author guidance** - Clear conventions for documentation

Currently, sdqctl recognizes several artifact patterns but lacks a unified taxonomy. This leads to:
- Inconsistent ID formats across projects
- Unclear relationship semantics
- Incomplete coverage verification
- Author confusion about conventions

---

## Artifact Type Taxonomy

### 1. Core Traceability Artifacts

| Type | Pattern | Description | Required Fields |
|------|---------|-------------|-----------------|
| **REQ** | `REQ-NNN` | Requirement | Statement, Rationale, Priority |
| **REQ** | `REQ-{DOMAIN}-NNN` | Scoped requirement | Same + Domain context |
| **SPEC** | `SPEC-NNN` | Specification | Acceptance criteria, Edge cases |
| **TEST** | `TEST-NNN` | Test case | Verifies, Expected outcome |
| **GAP** | `GAP-{DOMAIN}-NNN` | Implementation gap | Impact, Severity, Related REQ |

**Examples:**
```markdown
### REQ-001: Override Identity
**Statement:** Every override MUST have a unique, stable identifier.
**Rationale:** Required for supersession tracking.
**Priority:** P0

### REQ-CGM-010: CGM Data Freshness
**Statement:** CGM readings MUST be no older than 5 minutes.
**Domain:** CGM
**Priority:** P1

### SPEC-001: ConversationFile Parsing
**Requirement:** REQ-001
**Acceptance:** File parses without error, all directives extracted.
**Edge Cases:** Empty file, malformed directive, UTF-8 BOM.

### GAP-SYNC-004: Override supersession not tracked
**Impact:** Cannot query historical override state.
**Severity:** Medium
**Related:** REQ-001
```

### 2. STPA Safety Artifacts

| Type | Pattern | Description | Required Fields |
|------|---------|-------------|-----------------|
| **LOSS** | `LOSS-NNN` | System-level loss | Description |
| **HAZ** | `HAZ-NNN` | Hazard | Caused by LOSS, Severity |
| **UCA** | `UCA-NNN` | Unsafe Control Action | Control action, Context, Type |
| **UCA** | `UCA-{DOMAIN}-NNN` | Scoped UCA | Same + Domain |
| **SC** | `SC-NNN{x}` | Safety Constraint | Mitigates UCA |
| **SC** | `SC-{DOMAIN}-NNNx` | Scoped SC | Same + Domain |

**UCA Types:**
- Type 1: Not providing causes hazard
- Type 2: Providing causes hazard
- Type 3: Too early/late/out of order
- Type 4: Stopped too soon/applied too long

**Examples:**
```markdown
### LOSS-001: Patient Harm
Serious harm to patient due to incorrect insulin dosing.

### HAZ-001: Insulin Overdose
Excessive insulin delivery leading to severe hypoglycemia.
**Leads to:** LOSS-001
**Severity:** Catastrophic

### UCA-BOLUS-003: Bolus not cancelled when CGM drops rapidly
**Control Action:** Cancel bolus
**Context:** CGM reading drops >3 mg/dL/min during delivery
**Type:** Type 1 (not providing)
**Leads to:** HAZ-001

### SC-BOLUS-003a: Validate CGM trend before continuing bolus
**Mitigates:** UCA-BOLUS-003
**Implementation:** If CGM trend < -3, pause and alert user.
```

### 3. Development Artifacts

| Type | Pattern | Description | Required Fields |
|------|---------|-------------|-----------------|
| **Q** | `Q-NNN` | Quirk (known behavior) | Description, Priority, Status |
| **BUG** | `BUG-NNN` | Bug report | Symptoms, Reproduction, Severity |
| **PROP** | `PROP-NNN` | Proposal | Abstract, Motivation, Specification |
| **IQ** | `IQ-NNN` | Implementation quality issue | Location, Impact |

**Priority Levels:**
- P0: Critical - Blocks usage
- P1: High - Significant impact
- P2: Medium - Inconvenience
- P3: Low - Nice to have

**Status Values:**
- 🔴 OPEN - Not addressed
- 🟡 IN PROGRESS - Being worked
- 🟢 FIXED/RESOLVED - Complete
- 🔶 KNOWN - Documented, won't fix
- ⚪ WONTFIX - Intentional, not a bug

**Examples:**
```markdown
### Q-001: Workflow filename influences agent behavior
**Priority:** P0
**Status:** ✅ FIXED
**Description:** Agent behavior differs based on .conv filename.
**Root Cause:** Filename injected into prompt context.
**Fix:** Exclude WORKFLOW_NAME from prompts by default.

### BUG-001: Compaction fails on empty context
**Priority:** P1
**Status:** 🔴 OPEN
**Symptoms:** Crash when compacting session with no context files.
**Reproduction:** Run `sdqctl cycle` with empty CONTEXT directive.
**Severity:** High - Blocks compaction workflow.

### PROP-001: Custom ref:// URL scheme
**Status:** PROPOSAL
**Abstract:** Define unambiguous URL scheme for code references.
**Motivation:** Eliminate false positives in verify refs.
```

### 4. Documentation Artifacts (Proposed)

| Type | Pattern | Description | Required Fields |
|------|---------|-------------|-----------------|
| **DOC** | `DOC-NNN` | Documentation section | Title, Audience |
| **GUIDE** | `GUIDE-NNN` | User guide | Prerequisites, Steps |
| **API** | `API-NNN` | API documentation | Endpoint, Parameters |

**Note:** These are proposed for future standardization. Current practice is to reference documentation by file path.

### 5. Code References

| Type | Pattern | Description | Resolution |
|------|---------|-------------|------------|
| **@-ref** | `@path/to/file.md` | File reference | Workspace root |
| **alias-ref** | `alias:path/file#L1-50` | Code reference | workspace.lock.json |
| **anchor-ref** | `#section-name` | Section anchor | Same file |

**Examples:**
```markdown
# File references
See @traceability/requirements.md for the full list.
Context from @mapping/loop/README.md shows the implementation.

# Code references with line ranges
The algorithm is in `loop:LoopKit/LoopKit/InsulinModel.swift#L100-L150`.

# Anchors
See [Override Identity](#req-001-override-identity) above.
```

---

## Traceability Relationships

### Relationship Hierarchy

```
LOSS
  └── HAZ (leads_to)
        └── UCA (causes)
              └── SC (mitigates)
                    └── REQ (implemented_by)
                          └── SPEC (specified_by)
                                └── TEST (verified_by)
                                      └── CODE (implemented_in)

GAP ─── (blocks) ───→ REQ
Q ─── (escalates_to) ───→ BUG
BUG ─── (fixed_by) ───→ commit/PR
```

### Relationship Matrix

| From Type | To Type | Relationship | Arrow | Required? |
|-----------|---------|--------------|-------|-----------|
| LOSS | HAZ | leads_to | → | Yes |
| HAZ | UCA | causes | → | Yes |
| UCA | SC | mitigated_by | → | Yes |
| SC | REQ | implemented_by | → | Recommended |
| REQ | SPEC | specified_by | → | Recommended |
| SPEC | TEST | verified_by | → | Recommended |
| TEST | CODE | implemented_in | → | Optional |
| GAP | REQ | blocks | → | Yes |
| GAP | UCA | related_to | ↔ | Optional |
| Q | BUG | escalates_to | → | If escalated |
| PROP | REQ | proposes | → | If accepted |

### Relationship Syntax

```markdown
# Inline relationship
UCA-BOLUS-003 → SC-BOLUS-003a: Validate CGM trend

# Block relationship
### SC-BOLUS-003a
**Mitigates:** UCA-BOLUS-003
**Implements:** REQ-020

# Table relationship
| UCA | SC | REQ | SPEC | TEST | Status |
|-----|----|----|------|------|--------|
| UCA-001 | SC-001a | REQ-020 | SPEC-020 | TEST-020 | ✅ |
```

---

## Validation Rules

### Artifact ID Validation

```regex
# Core patterns
REQ-[0-9]{3}                    # REQ-001
REQ-[A-Z]+-[0-9]{3}             # REQ-CGM-010
SPEC-[0-9]{3}                   # SPEC-001
TEST-[0-9]{3}                   # TEST-001
GAP-[A-Z]+-[0-9]{3}             # GAP-SYNC-004

# STPA patterns
LOSS-[0-9]{3}                   # LOSS-001
HAZ-[0-9]{3}                    # HAZ-001
UCA-[0-9]{3}                    # UCA-001
UCA-[A-Z]+-[0-9]{3}             # UCA-BOLUS-003
SC-[0-9]{3}[a-z]?               # SC-001, SC-001a
SC-[A-Z]+-[0-9]{3}[a-z]?        # SC-BOLUS-003a

# Development patterns
Q-[0-9]{3}                      # Q-001
BUG-[0-9]{3}                    # BUG-001
PROP-[0-9]{3}                   # PROP-001
IQ-[0-9]+                       # IQ-1
```

### Coverage Rules

| Artifact Type | Must Have | Should Have | May Have |
|---------------|-----------|-------------|----------|
| REQ | Statement | Rationale, Priority | Code refs |
| SPEC | REQ reference | Acceptance criteria | Edge cases |
| TEST | SPEC reference | Expected outcome | Code refs |
| GAP | Impact | Related REQ | Severity |
| UCA | Control action, Type | Context | HAZ reference |
| SC | UCA reference | Implementation notes | REQ link |
| Q | Description, Priority | Status | Root cause |
| BUG | Symptoms | Reproduction steps | Severity |

### Orphan Detection

An artifact is orphaned if:
- **UCA** has no SC
- **SC** has no REQ (warning)
- **REQ** has no SPEC (warning)
- **SPEC** has no TEST (warning)
- **GAP** has no related REQ

### Coverage Metrics

```
Requirement Coverage = (REQs with SPEC) / (Total REQs)
Specification Coverage = (SPECs with TEST) / (Total SPECs)
Test Coverage = (TESTs implemented) / (Total TESTs)
Safety Coverage = (UCAs with SC) / (Total UCAs)
Gap Resolution = (GAPs closed) / (Total GAPs)
```

---

## Implementation

### Phase 1: Pattern Recognition

Update `sdqctl/verifiers/traceability.py`:

```python
ARTIFACT_PATTERNS = {
    'REQ': r'REQ-(?:[A-Z]+-)?[0-9]{3}',
    'SPEC': r'SPEC-[0-9]{3}',
    'TEST': r'TEST-[0-9]{3}',
    'GAP': r'GAP-[A-Z]+-[0-9]{3}',
    'LOSS': r'LOSS-[0-9]{3}',
    'HAZ': r'HAZ-[0-9]{3}',
    'UCA': r'UCA-(?:[A-Z]+-)?[0-9]{3}',
    'SC': r'SC-(?:[A-Z]+-)?[0-9]{3}[a-z]?',
    'Q': r'Q-[0-9]{3}',
    'BUG': r'BUG-[0-9]{3}',
    'PROP': r'PROP-[0-9]{3}',
}
```

### Phase 2: Relationship Extraction

Parse relationship syntax:
```python
RELATIONSHIP_PATTERNS = {
    'arrow': r'([A-Z]+-[A-Z]*-?[0-9]+[a-z]?)\s*→\s*([A-Z]+-[A-Z]*-?[0-9]+[a-z]?)',
    'field': r'\*\*(Mitigates|Implements|Verifies|Blocks):\*\*\s*([A-Z]+-[A-Z]*-?[0-9]+)',
}
```

### Phase 3: Coverage Reporting

```bash
sdqctl verify traceability --coverage
# Output:
# Artifact Coverage Report
# ========================
# REQ: 15 found, 12 have SPEC (80%)
# SPEC: 12 found, 8 have TEST (67%)
# UCA: 5 found, 5 have SC (100%)
# GAP: 8 found, 3 closed (38%)
```

---

## Compatibility

### Nightscout Ecosystem

The Nightscout ecosystem currently uses:
- `GAP-{DOMAIN}-NNN` format (compatible)
- Short-form code refs like `trio:Preferences.swift` (needs full paths)
- No standardized LOSS/HAZ artifacts (STPA not adopted)

**Migration Path:**
1. Document current patterns in ecosystem
2. Add missing STPA artifacts where appropriate
3. Migrate short-form refs to full paths

### Legacy Patterns

Some codebases may use:
- `REQUIREMENT-001` instead of `REQ-001`
- `ISSUE-001` instead of `BUG-001`
- `TODO-001` for action items

**Recommendation:** Support aliases in configuration:
```yaml
# .sdqctl.yaml
artifact_aliases:
  REQUIREMENT: REQ
  ISSUE: BUG
  TODO: GAP
```

---

## Open Questions

1. **Global vs Scoped IDs?**
   - Option A: `REQ-001` (simple, may collide in multi-project)
   - Option B: `REQ-LOOP-001` (explicit, verbose)
   - **Recommendation:** Allow both; scoped preferred for multi-project

2. **Verification Strictness?**
   - Option A: Fail on orphans (strict)
   - Option B: Warn only (lenient)
   - **Recommendation:** Configurable, default lenient

3. **BUG vs Q distinction?**
   - Q = Quirk (known surprising behavior, may be intentional)
   - BUG = Defect (unintended behavior to fix)
   - **Recommendation:** Keep distinct; Q can escalate to BUG

4. **PROP lifecycle?**
   - PROPOSAL → ACCEPTED → REQ extraction
   - PROPOSAL → REJECTED → Archived
   - **Recommendation:** Document in PROP status field

---

## References

- [STPA Handbook](https://psas.scripts.mit.edu/home/materials/) - MIT STPA methodology
- [docs/TRACEABILITY-WORKFLOW.md](../docs/TRACEABILITY-WORKFLOW.md) - Current guidance
- [docs/QUIRKS.md](../docs/QUIRKS.md) - Q-pattern examples
- [proposals/STPA-INTEGRATION.md](STPA-INTEGRATION.md) - STPA integration proposal

---

## Changelog

- 2026-01-24: Initial proposal
