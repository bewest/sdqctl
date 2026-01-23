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
sdqctl run requirements-discovery.conv --adapter copilot
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

Use `cycle` mode to generate detailed specifications:

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
sdqctl cycle spec-generator.conv --adapter copilot -n 2
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

Use `cycle` with RUN commands to implement and verify:

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
> See [QUINE-WORKFLOWS.md](QUINE-WORKFLOWS.md#use-elide-to-reduce-agent-turns) for details.

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
sdqctl run examples/workflows/test-discovery.conv --adapter copilot

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
sdqctl run requirements-discovery.conv --adapter copilot

# Phase 2: Specs (references Phase 1 output)
sdqctl run spec-generator.conv --adapter copilot

# Phase 3: Tests (references Phase 2 output)
sdqctl run test-scaffolding.conv --adapter copilot

# Phase 4: Verification (checks all phases)
sdqctl run verification-loop.conv --adapter copilot
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

## Next Steps

- **[Reverse Engineering](REVERSE-ENGINEERING.md)** — Go backwards: code → docs → requirements
- **[Quine Workflows](QUINE-WORKFLOWS.md)** — Self-improving iteration loops
- **[Getting Started](GETTING-STARTED.md)** — sdqctl basics

See `examples/workflows/test-discovery.conv` for a working traceability example.
