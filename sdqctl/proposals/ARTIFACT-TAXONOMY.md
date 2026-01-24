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

## Enumeration Strategies

This section provides guidelines for consistent, collision-free artifact ID assignment.

### Core Principles

1. **Uniqueness**: Every artifact ID must be unique within its scope
2. **Stability**: Once assigned, IDs should never change
3. **Parseability**: IDs must be machine-readable with consistent patterns
4. **Readability**: IDs should convey meaning to humans
5. **Traceability**: IDs must support automated linking

### Numbering Schemes

#### Sequential (Recommended for Single Projects)

```
REQ-001, REQ-002, REQ-003, ...
SPEC-001, SPEC-002, ...
```

**Pros:** Simple, dense, easy to track gaps  
**Cons:** May collide in multi-project workspaces

#### Category-Scoped (Recommended for Multi-Project)

```
REQ-CGM-001    # CGM domain requirements
REQ-BOLUS-001  # Bolus domain requirements
GAP-SYNC-004   # Sync-related gap
UCA-PUMP-003   # Pump control UCAs
```

**Pros:** Domain context, collision-resistant  
**Cons:** Longer IDs, requires category taxonomy

#### Project-Scoped (For Cross-Project Traceability)

```
LOOP-REQ-001   # Loop project requirement
AAPS-REQ-001   # AAPS project requirement
TRIO-GAP-005   # Trio project gap
```

**Pros:** Explicit project ownership  
**Cons:** Verbose, project name changes break IDs

### Recommended Strategies by Artifact Type

| Type | Strategy | Format | Example |
|------|----------|--------|---------|
| REQ | Category-scoped | `REQ-{DOMAIN}-NNN` | REQ-CGM-010 |
| SPEC | Sequential | `SPEC-NNN` | SPEC-042 |
| TEST | Match SPEC | `TEST-{SPEC#}` | TEST-042 |
| GAP | Category-scoped | `GAP-{DOMAIN}-NNN` | GAP-SYNC-004 |
| UCA | Category-scoped | `UCA-{CONTROL}-NNN` | UCA-BOLUS-003 |
| SC | Match UCA + suffix | `SC-{UCA#}{x}` | SC-BOLUS-003a |
| Q | Sequential | `Q-NNN` | Q-012 |
| BUG | Sequential | `BUG-NNN` | BUG-001 |
| PROP | Sequential | `PROP-NNN` | PROP-007 |

### Category Taxonomy

Define categories before starting enumeration:

```yaml
# Example category taxonomy for AID systems
domains:
  CGM: Continuous Glucose Monitoring
  BOLUS: Insulin bolus delivery
  BASAL: Basal rate management
  SYNC: Data synchronization
  AUTH: Authentication/authorization
  PUMP: Pump communication
  UI: User interface
  CONFIG: Configuration/settings
```

### ID Lifecycle

#### Assignment Rules

1. **Never reuse IDs** - Even if artifact is deleted, ID is retired
2. **Reserve ranges** - Pre-allocate ranges for parallel work
   ```
   Team A: REQ-CGM-001 to REQ-CGM-099
   Team B: REQ-CGM-100 to REQ-CGM-199
   ```
3. **Document retirements** - Track deleted IDs to prevent accidental reuse

#### Status Progression

```
PROPOSED → ACCEPTED → IMPLEMENTED → VERIFIED → CLOSED
                   ↘ REJECTED
                   ↘ DEFERRED
```

#### Retirement

```markdown
### REQ-CGM-005: [RETIRED]
**Status:** RETIRED (2026-01-15)
**Reason:** Superseded by REQ-CGM-010
**Successor:** REQ-CGM-010
```

### Collision Avoidance

#### Single Project

Use a registry file to track assigned IDs:

```markdown
# artifact-registry.md

## Requirements
| ID | Title | Status | Owner |
|----|-------|--------|-------|
| REQ-001 | Override Identity | Active | @alice |
| REQ-002 | CGM Freshness | Active | @bob |
| REQ-003 | [RETIRED] | Retired | - |
| REQ-004 | Pump Timeout | Draft | @carol |
```

#### Multi-Project Workspace

Use project prefix to namespace:

```markdown
# Nightscout Ecosystem ID Ranges

| Project | REQ Range | GAP Range | UCA Range |
|---------|-----------|-----------|-----------|
| loop | 001-199 | LOOP-001+ | LOOP-001+ |
| aaps | 200-399 | AAPS-001+ | AAPS-001+ |
| trio | 400-599 | TRIO-001+ | TRIO-001+ |
| xdrip | 600-799 | XDRIP-001+ | XDRIP-001+ |
```

Or use fully-qualified IDs:

```
LOOP-REQ-001, AAPS-REQ-001, TRIO-REQ-001
```

### Formatting Guidelines

#### ID Format

- **UPPERCASE** for type prefix: `REQ`, `SPEC`, `UCA`
- **UPPERCASE** for category: `CGM`, `BOLUS`, `SYNC`
- **Zero-padded numbers**: `001`, `042`, `100`
- **Lowercase suffix** for variants: `a`, `b`, `c`
- **Hyphen separator**: `REQ-CGM-001`, not `REQ_CGM_001`

#### ID in Text

```markdown
# ✅ CORRECT: Backticks for inline IDs
See `REQ-001` for the requirement.
The gap `GAP-SYNC-004` blocks this feature.

# ✅ CORRECT: Heading with ID
### REQ-001: Override Identity

# ✅ CORRECT: Table with IDs
| ID | Title | Status |
|----|-------|--------|
| REQ-001 | Override Identity | Active |

# ❌ INCORRECT: No backticks for inline
See REQ-001 for the requirement.  # Harder to parse

# ❌ INCORRECT: ID after title
### Override Identity (REQ-001)  # Inconsistent
```

#### Anchor Generation

IDs should generate predictable anchors:

```markdown
### REQ-001: Override Identity
<!-- Anchor: #req-001-override-identity -->

### GAP-SYNC-004: Supersession Not Tracked
<!-- Anchor: #gap-sync-004-supersession-not-tracked -->
```

### Tooling Support

#### Next ID Generation

```bash
# Find next available ID
sdqctl artifact next REQ
# → REQ-043

sdqctl artifact next REQ-CGM
# → REQ-CGM-011

# With specific file
sdqctl artifact next REQ --registry artifact-registry.md
```

#### Validation

```bash
# Check for ID collisions
sdqctl verify artifacts --check-collisions

# Check for orphaned IDs (defined but never referenced)
sdqctl verify artifacts --check-orphans

# Check for format violations
sdqctl verify artifacts --check-format
```

#### Migration

```bash
# Rename artifact (updates all references)
sdqctl artifact rename REQ-001 REQ-OVERRIDE-001

# Retire artifact
sdqctl artifact retire REQ-003 --reason "Superseded by REQ-010"
```

### Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Reusing retired IDs | Breaks historical traceability | Never reuse; always increment |
| Inconsistent casing | `req-001` vs `REQ-001` | Always UPPERCASE type/category |
| Gaps in sequence | Confusing: 001, 002, 005? | Document retired IDs |
| Category drift | REQ-CGM-001 for pump feature | Reassign to correct category |
| Overly long categories | `REQ-GLUCOSE-MONITORING-001` | Use abbreviations: `REQ-CGM-001` |
| No category for large projects | REQ-001 to REQ-999 collisions | Add categories early |

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

## Resolved Questions

### 1. Global vs Scoped IDs

**✅ DECIDED (2026-01-24): Allow both, prefer scoped for multi-project**

| Context | Format | Example |
|---------|--------|---------|
| Single project | Simple | `REQ-001`, `UCA-015` |
| Cross-project refs | Scoped | `REQ-LOOP-001`, `UCA-TRIO-015` |
| Ecosystem docs | Scoped | `GAP-XDRIP-003` |

The `traceability` verifier will detect collisions when simple IDs are used across projects.

### 2. Verification Strictness

**✅ DECIDED (2026-01-24): Configurable with `--strict` flag, default warn**

```bash
# Default: warn on orphans, exit 0
sdqctl verify traceability

# Strict: fail on orphans, exit 1 (for CI)
sdqctl verify traceability --strict
```

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

- 2026-01-24: Added `artifact retire` command implementation
- 2026-01-24: Initial proposal
