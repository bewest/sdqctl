# Traceability Workflows: Requirements → Code → Verification

Traceability workflows establish clear links between **requirements**, **specifications**, **tests**, **code**, and **verification**. sdqctl orchestrates this pipeline with AI assistance at each phase.

---

## The Traceability Pipeline

```
Requirements  →  Specifications  →  Tests  →  Code  →  Verification
    │                 │              │         │            │
    └─────────────────┴──────────────┴─────────┴────────────┘
                          Traceability Links
```

Each phase produces artifacts that reference the previous phase:
- Specs cite requirement IDs
- Tests reference spec sections
- Code links to test cases
- Verification confirms all links are valid

---

## Phase 1: Requirements Extraction

Use `run` mode to extract requirements from documentation:

```dockerfile
# requirements-discovery.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Extract requirements from the project documentation.
  Key documents are in docs/ and README.md.
  
  For each requirement:
  - Assign an ID (REQ-001, REQ-002, etc.)
  - Classify as functional/non-functional
  - Note the source location
  
  Output as a markdown table.

OUTPUT-FILE requirements/requirements.md
```

```bash
sdqctl iterate requirements-discovery.conv --adapter copilot
```

### Output Example

```markdown
| ID | Type | Requirement | Source |
|----|------|-------------|--------|
| REQ-001 | Functional | System shall parse .conv files | README.md:45 |
| REQ-002 | Functional | System shall support multiple adapters | PROPOSAL.md:120 |
| REQ-003 | Non-functional | Response time < 100ms | docs/PERFORMANCE.md:15 |
```

---

## Phase 2: Specification Generation

Use `iterate` mode to generate detailed specifications:

```dockerfile
# spec-generator.conv
MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 2

# Cycle 1: Generate specs for high-priority requirements
PROMPT Generate specifications for requirements in requirements/requirements.md.
  Focus on REQ-001 through REQ-005 (highest priority).
  
  For each specification:
  - Reference the requirement ID
  - Define acceptance criteria
  - List edge cases
  - Note dependencies

# Cycle 2: Review and refine
PROMPT Review the specifications for completeness.
  Ensure each has:
  - Clear acceptance criteria (testable)
  - Edge cases identified
  - No ambiguous language

OUTPUT-FILE specs/specifications.md
```

```bash
sdqctl iterate spec-generator.conv --adapter copilot -n 2
```

---

## Phase 3: Test Scaffolding

Generate test stubs from specifications:

```dockerfile
# test-scaffolding.conv
MODEL gpt-4
ADAPTER copilot
MODE implement

PROMPT Generate pytest test stubs from specs/specifications.md.
  
  For each specification:
  - Create a test function named test_<spec_id>_<description>
  - Add docstring referencing the spec ID
  - Include TODO comments for implementation
  - Cover the listed edge cases
  
  Reference format:
  ```python
  def test_spec001_parse_conv_file():
      """Test SPEC-001: ConversationFile parsing.
      
      Requirement: REQ-001
      Acceptance: File parses without error
      """
      # TODO: Implement
      pass
  ```

OUTPUT-FILE tests/test_generated.py
```

---

## Phase 4: Implementation with Validation

Use `iterate` with RUN commands to implement and verify:

```dockerfile
# implement-with-tests.conv
MODEL gpt-4
ADAPTER copilot
MODE implement
MAX-CYCLES 3

RUN-ON-ERROR continue
RUN-OUTPUT on-error

# Cycle 1: Implement first test
PROMPT Review tests/test_generated.py.
  Implement the first TODO test case.
  Run the test to verify it passes.

RUN python -m pytest tests/test_generated.py -v --tb=short

# Cycle 2: Continue implementation
PROMPT Continue implementing test cases.
  If the previous test failed, fix it first.
  Then implement the next TODO.

RUN python -m pytest tests/test_generated.py -v --tb=short

# Cycle 3: Verify all pass
PROMPT Ensure all implemented tests pass.
  Document any tests that need the actual feature implemented.

RUN python -m pytest tests/test_generated.py -v
```

> **Tip:** Use `ELIDE` to merge RUN output with the follow-up PROMPT for more efficient workflows:
> ```dockerfile
> RUN python -m pytest tests/test_generated.py -v
> ELIDE
> PROMPT Fix any failing tests shown above.
> ```
> See [SYNTHESIS-CYCLES.md](SYNTHESIS-CYCLES.md#use-elide-to-reduce-agent-turns) for details.

---

## Phase 5: Verification Loop

Verify traceability links are complete and valid:

```dockerfile
# verification-loop.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

# Run verification tooling (if available)
RUN-ON-ERROR continue
RUN-OUTPUT always
RUN python tools/verify_refs.py --json 2>/dev/null || echo "No verification tool"

PROMPT Verify traceability across artifacts:
  
  1. Requirements coverage:
     - Which requirements have specs? (check specs/specifications.md)
     - Which requirements lack specs?
  
  2. Specification coverage:
     - Which specs have tests? (check tests/)
     - Which specs lack tests?
  
  3. Implementation coverage:
     - Which tests are implemented vs TODO?
  
  Generate a traceability matrix showing gaps.

OUTPUT-FILE reports/traceability-matrix.md
```

---

## Real Example: sdqctl Test Discovery

The `examples/workflows/test-discovery.conv` demonstrates this pattern:

1. **Extracts requirements** from INTEGRATION-PROPOSAL.md and README.md
2. **Identifies implementation** in conversation.py and run.py
3. **Finds gaps** between documented and implemented features
4. **Recommends tests** to close the gaps

```bash
# Run the discovery
sdqctl iterate examples/workflows/test-discovery.conv --adapter copilot

# Review output
cat reports/test-discovery-*.md
```

---

## Real Example: Nightscout Ecosystem

For the Nightscout ecosystem, traceability links:

```
OpenAPS spec  →  Loop implementation  →  Conformance tests  →  Verification
      │                  │                      │                   │
  oref0 docs        LoopKit/Loop          tests/conformance    verify_refs.py
```

Workflow to verify alignment:

```dockerfile
# nightscout-traceability.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Analyze traceability for the Nightscout AID ecosystem.
  
  Key artifacts:
  - OpenAPS reference: externals/oref0/
  - Loop implementation: (if cloned)
  - Conformance specs: conformance/
  - Traceability matrices: traceability/
  
  Identify:
  1. Which oref0 algorithms have Loop implementations?
  2. Which implementations have conformance tests?
  3. Where are the gaps?

OUTPUT-FILE reports/nightscout-traceability.md
```

---

## Context-Light Traceability

### Don't Inject Everything

❌ Loading all artifacts upfront:
```dockerfile
CONTEXT @requirements/**/*.md
CONTEXT @specs/**/*.md
CONTEXT @tests/**/*.py
CONTEXT @traceability/**/*.md
```

✅ Let agent explore on demand:
```dockerfile
PROMPT Verify traceability links.
  Requirements are in requirements/
  Specs are in specs/
  Tests are in tests/
  Check each and report gaps.
```

### Chunk Into Phases

Instead of one massive workflow, use phases:

```bash
# Phase 1: Requirements
sdqctl iterate requirements-discovery.conv --adapter copilot

# Phase 2: Specs (references Phase 1 output)
sdqctl iterate spec-generator.conv --adapter copilot

# Phase 3: Tests (references Phase 2 output)
sdqctl iterate test-scaffolding.conv --adapter copilot

# Phase 4: Verification (checks all phases)
sdqctl iterate verification-loop.conv --adapter copilot
```

Each phase outputs to files that the next phase references.

---

## Traceability Matrix Template

```markdown
# Traceability Matrix

## Requirements → Specifications

| Requirement | Specification | Status |
|-------------|---------------|--------|
| REQ-001 | SPEC-001 | ✅ Covered |
| REQ-002 | SPEC-002, SPEC-003 | ✅ Covered |
| REQ-003 | - | ❌ Missing |

## Specifications → Tests

| Specification | Test | Status |
|---------------|------|--------|
| SPEC-001 | test_spec001_* | ✅ Implemented |
| SPEC-002 | test_spec002_* | ⚠️ TODO |
| SPEC-003 | - | ❌ Missing |

## Coverage Summary

- Requirements: 2/3 (67%) have specs
- Specifications: 1/3 (33%) have tests
- Tests: 1/2 (50%) implemented

## Priority Gaps

1. REQ-003 needs specification
2. SPEC-002 needs test implementation
3. SPEC-003 needs test creation
```

---

## Artifact Types Quick Reference

sdqctl recognizes these artifact types for traceability verification. For complete enumeration strategies, ID lifecycle, and formatting guidelines, see [ARTIFACT-TAXONOMY.md](../proposals/ARTIFACT-TAXONOMY.md).

### Core Traceability Artifacts

| Type | Pattern | Description |
|------|---------|-------------|
| **REQ** | `REQ-NNN` or `REQ-{DOMAIN}-NNN` | Requirement (e.g., `REQ-001`, `REQ-CGM-010`) |
| **SPEC** | `SPEC-NNN` | Specification with acceptance criteria |
| **TEST** | `TEST-NNN` | Test case that verifies a SPEC |
| **GAP** | `GAP-{DOMAIN}-NNN` | Implementation gap (e.g., `GAP-SYNC-004`) |

### STPA Safety Artifacts

| Type | Pattern | Description |
|------|---------|-------------|
| **LOSS** | `LOSS-NNN` | System-level loss (e.g., patient harm) |
| **HAZ** | `HAZ-NNN` | Hazard leading to loss |
| **UCA** | `UCA-NNN` or `UCA-{CTRL}-NNN` | Unsafe Control Action (e.g., `UCA-BOLUS-003`) |
| **SC** | `SC-NNN{x}` or `SC-{CTRL}-NNN{x}` | Safety Constraint mitigating UCA (e.g., `SC-BOLUS-003a`) |

### Development Artifacts

| Type | Pattern | Description |
|------|---------|-------------|
| **Q** | `Q-NNN` | Quirk - known surprising behavior |
| **BUG** | `BUG-NNN` | Bug report - unintended behavior |
| **PROP** | `PROP-NNN` | Proposal for new feature/change |
| **IQ** | `IQ-NNN` | Implementation quality issue |

### Traceability Chain

The standard verification chain flows top-down:

```
LOSS → HAZ → UCA → SC → REQ → SPEC → TEST → CODE
```

Use `sdqctl verify traceability` to check coverage along this chain.

---

## Next Steps

- **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Go backwards: code → docs → requirements
- **[Synthesis Cycles](SYNTHESIS-CYCLES.md)** — Self-improving iteration loops
- **[Getting Started](GETTING-STARTED.md)** — sdqctl basics
- **[Artifact Taxonomy](../proposals/ARTIFACT-TAXONOMY.md)** — Full artifact enumeration and ID strategies

See `examples/workflows/test-discovery.conv` for a working traceability example.

---

## Appendix: Author Requirements for sdqctl Traceability

This section documents what authors need to do in their markdown, code, tests, docs, and JSON files for sdqctl tools to establish traceability.

### Reference Formats

sdqctl tools recognize two types of traceable references:

#### 1. @-References (File References)

Reference files relative to workspace root:

```markdown
# ✅ CORRECT: Relative to workspace root
See @traceability/requirements.md for the full list.
Context from @mapping/loop/README.md shows the implementation.

# ✅ CORRECT: Explicit relative path
See @./local-file.md in this directory.

# ❌ INCORRECT: Paths that don't exist
See @docs/missing-file.md for details.
```

#### 2. Alias References (Code References)

Reference code in external repositories using `alias:path` format:

```markdown
# ✅ CORRECT: Full path from alias root
See `loop:LoopKit/LoopKit/TemporaryScheduleOverride.swift#L22-L50` for the implementation.
The algorithm is in `aaps:database/impl/src/main/kotlin/app/aaps/database/entities/Carbs.kt`.

# ❌ INCORRECT: Short-form (won't validate)
See `loop:TemporaryScheduleOverride.swift` for the implementation.

# ❌ INCORRECT: Placeholder paths
See `loop:path/to/file.swift` for details.
```

**Finding correct paths:**
```bash
# Use find to locate the file
find externals/LoopWorkspace -name "TemporaryScheduleOverride.swift"
# → externals/LoopWorkspace/LoopKit/LoopKit/TemporaryScheduleOverride.swift

# Construct the ref (remove externals/LoopWorkspace prefix, use loop: alias)
# loop:LoopKit/LoopKit/TemporaryScheduleOverride.swift
```

### Workspace Configuration

For alias references to work, create a `workspace.lock.json`:

```json
{
  "aliases": {
    "loop": {
      "path": "externals/LoopWorkspace",
      "type": "git",
      "url": "https://github.com/LoopKit/LoopWorkspace.git"
    },
    "aaps": {
      "path": "externals/AndroidAPS",
      "type": "git",
      "url": "https://github.com/nightscout/AndroidAPS.git"
    },
    "trio": {
      "path": "externals/Trio",
      "type": "git",
      "url": "https://github.com/nightscout/Trio.git"
    }
  }
}
```

### Requirement Format (REQ-NNN)

For sdqctl to track requirements:

```markdown
### REQ-001: Override Identity

**Statement**: Every override MUST have a unique, stable identifier that persists across system restarts.

**Rationale**: Required for supersession tracking and historical queries.

**Type**: Functional

**Priority**: P0

**Verification**: Create override, restart system, query by ID - should return same override.

**Code References**:
- `loop:LoopKit/LoopKit/TemporaryScheduleOverride.swift#L22` - UUID property
- `trio:Trio/Sources/Models/Override.swift#L15` - id field
```

### Gap Format (GAP-XXX-NNN)

For tracking implementation gaps:

```markdown
### GAP-SYNC-004: Override supersession not tracked

**Scenario**: [Override Supersede](../conformance/scenarios/override-supersede/)

**Description**: When a new override is created that supersedes an existing one, 
the supersession relationship is not recorded.

**Impact**: Cannot query "what override was active at time T"

**Severity**: Medium

**Related Requirements**: [REQ-001](#req-001-override-identity)

**Code References**:
- `loop:Loop/Managers/LoopDataManager.swift#L200-L250` - no supersession tracking
```

### Test Traceability

Link tests to requirements and specs:

```python
def test_override_identity_persists():
    """Test REQ-001: Override identity persists across restarts.
    
    Requirement: REQ-001
    Specification: SPEC-001
    Scenario: override-supersede
    """
    # Test implementation
    pass
```

### JSON Schema Traceability

In JSON schemas, use `$comment` for traceability:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/override.schema.json",
  "$comment": "REQ-001: Override Identity",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "$comment": "REQ-001: Unique stable identifier"
    }
  }
}
```

### Verification Commands

```bash
# Verify all references
sdqctl verify refs

# With fix suggestions
sdqctl verify refs --suggest-fixes -v

# Verify links (markdown links)
sdqctl verify links

# Verify traceability coverage
sdqctl verify traceability

# All verifications
sdqctl verify all

# JSON output for CI
sdqctl verify refs --json > refs-report.json
```

### Fixing Broken References

Use the fix-broken-refs workflow:

```bash
# 3-cycle workflow to fix broken refs
sdqctl iterate examples/workflows/traceability/fix-broken-refs.conv -n 3

# Or manually with suggestions
sdqctl verify refs --suggest-fixes -v 2>&1 | grep "Suggestion"
```

### Common Issues and Solutions

| Issue | Example | Solution |
|-------|---------|----------|
| Short-form ref | `trio:Preferences.swift` | Use full path: `trio:Trio/Sources/Models/Preferences.swift` |
| Unknown alias | `CGMBLEKit:File.swift` | Add alias to `workspace.lock.json` |
| Missing file | `loop:Missing.swift` | Check if file moved, use `find` to locate |
| Placeholder path | `path/to/file.swift` | Replace with actual file path |

### Tool Cohesion

sdqctl tools are designed with loose coupling:

| Tool | Purpose | Inputs | Outputs |
|------|---------|--------|---------|
| `refcat` | Extract code snippets | `alias:path#lines` | Code content |
| `verify refs` | Validate references | Markdown/conv files | Error report |
| `verify links` | Validate markdown links | Markdown files | Broken links |
| `verify traceability` | Check REQ→Test coverage | All files | Coverage matrix |
| `validate` | Validate workflow syntax | .conv files | Syntax errors |

Tools can be used independently or composed in workflows.
