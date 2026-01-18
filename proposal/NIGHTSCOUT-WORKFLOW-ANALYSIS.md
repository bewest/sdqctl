# Nightscout Ecosystem Development Workflow Analysis

**Date**: 2026-01-18  
**Purpose**: Relate the audit → document → test workflows from Nightscout projects to the `copilot do` proposal

---

## Executive Summary

The Nightscout ecosystem (cgm-remote-monitor, nightscout-roles-gateway, rag-nightscout-ecosystem-alignment) demonstrates a sophisticated, iterative workflow for managing complex, safety-critical medical software. This document maps their real-world development patterns to the proposed `copilot do` commands, showing how declarative, reproducible AI-assisted workflows could have accelerated their development cycles.

**Key Insight**: These projects already use an implicit "audit → requirements → tests → documentation → implementation" cycle that would benefit tremendously from declarative, version-controlled ConversationFiles.

---

## Observed Development Patterns

### Pattern 1: Audit-First Methodology (cgm-remote-monitor)

**What They Did:**
- Created 7 comprehensive system audits (`docs/audits/`)
- Each audit documents current state before proposing changes
- Audits became the foundation for requirements extraction

**Git Evidence:**
```
5e18cd0e Update documentation with system audit findings and roadmap
a9b5cb3f Update documentation to reflect accurate system information
```

**How `copilot do` Would Help:**

**Current Process** (manual, undocumented):
1. Developer manually explores codebase
2. Takes notes in markdown
3. Reviews code multiple times to verify claims
4. Manually cross-references files
5. Writes audit document over several hours

**With `copilot do`:**

```bash
# Run audit workflow (read-only, no code changes)
copilot do ./workflows/audit-component.copilot \
  --mode audit \
  --output docs/audits/api-layer-audit.md

# Version-controlled workflow
cat workflows/audit-component.copilot
```

```dockerfile
# workflows/audit-component.copilot
MODEL claude-opus-4.5
MODE audit  # Read-only, generate reports

CWD ./lib/api
ADD-DIR ./lib/api
ADD-DIR ./tests

PROMPT Analyze the API layer architecture and document current state.

PROMPT For each API version (v1, v2, v3):
1. List all endpoints with file locations
2. Document authentication methods
3. Identify security concerns
4. Note test coverage gaps
5. Document dependencies and middleware

PROMPT Generate a comprehensive audit report in markdown format.
```

**Benefits:**
- ✅ Reproducible across team members
- ✅ Version-controlled in git
- ✅ Can re-run after code changes to verify
- ✅ Consistent format across all audits

---

### Pattern 2: Requirements → Tests → Documentation (cgm-remote-monitor)

**What They Did:**
- Created `docs/requirements/` with formal specifications
- Created `docs/test-specs/` with traceability matrices
- Each test spec tracks coverage gaps and quirks

**Git Evidence:**
```
fbaaeb22 Add comprehensive authorization and security documentation and test specifications
34335764 Update API documentation to reflect accurate data shape requirements
4ab51f90 Add project documentation progress tracker and update README
```

**File Structure:**
```
docs/
├── audits/              # Current state analysis
├── requirements/        # What must be true
├── test-specs/          # How to verify
└── meta/
    └── DOCUMENTATION-PROGRESS.md  # Progress tracking
```

**How `copilot do` Would Help:**

```bash
# Generate requirements from audit
copilot do ./workflows/extract-requirements.copilot \
  --prologue <(cat docs/audits/security-audit.md) \
  --mode docs-only \
  --output docs/requirements/authorization-security-requirements.md

# Generate test specs from requirements
copilot do ./workflows/generate-test-spec.copilot \
  --prologue <(cat docs/requirements/authorization-security-requirements.md) \
  --mode tests-only \
  --output docs/test-specs/authorization-tests.md

# Implement tests from spec
copilot do ./workflows/implement-tests.copilot \
  --prologue <(cat docs/test-specs/authorization-tests.md) \
  --allow-path "tests/**" \
  --yolo
```

**ConversationFile Example:**

```dockerfile
# workflows/extract-requirements.copilot
MODEL claude-sonnet-4.5
MODE docs-only
MAX-CYCLES 2

# Read audit, generate requirements doc
CONTEXT @docs/audits/security-audit.md
CWD ./docs/requirements

PROMPT Extract formal requirements from the security audit.

PROMPT For each requirement:
1. Assign unique ID (SEC-001, etc.)
2. State what must be true
3. Cite source code location
4. Include acceptance criteria
5. Mark priority (High/Medium/Low)

PROMPT Generate a requirements document with traceability matrix.
```

**Actual Workflow They Document:**

From `docs/meta/DOCUMENTATION-PROGRESS.md`:

> **Approach:** Audit-first methodology - review component audits, then create formal requirements specs and test specifications with traceability matrices.

This is EXACTLY the workflow that `copilot do` enables declaratively!

---

### Pattern 3: Iterative Test Development (nightscout-roles-gateway)

**What They Did:**
- 218 tests across integration, unit, views, triggers
- Comprehensive test quirks documentation (`test/quirks/README.md`)
- Skipped tests for external dependencies (Kratos/Hydra)

**Git Evidence:**
```
b3ebca1 Expand test coverage for user consent and site deletion functionality
090128a Ensure database migrations run correctly before tests execute
17c8bf4 Make skipping Hydra and Kratos tests the default
3cd9003 Add dedicated tests for API secret middleware functionality
```

**Test Infrastructure Pattern:**

From `replit.md`:
> Tests use centralized migration management via Mocha root hooks (`.mocharc.json` + `test/setup/hooks.js`). This ensures:
> - Migrations run once before all tests
> - Migration locks are cleared before running
> - Database connections are properly cleaned up

**How `copilot do` Would Help:**

```bash
# Sequential test development workflow
copilot loop workflows/test-development/*.copilot \
  --mode tests-only \
  --max-cycles 2

# workflows/test-development/01-unit-tests.copilot
# workflows/test-development/02-integration-tests.copilot
# workflows/test-development/03-quirks-documentation.copilot
```

```dockerfile
# workflows/test-development/01-unit-tests.copilot
MODEL claude-sonnet-4.5
MODE tests-only
MAX-CYCLES 2

CWD ./test/unit
ADD-DIR ./lib
ADD-DIR ./test

PROMPT Add comprehensive unit tests for the decision function.

PROMPT Follow the existing test patterns:
- Use describe/it blocks
- Use chai assertions
- Test happy path and error cases
- Document quirks in test/quirks/README.md

CONTEXT @lib/warden/decision.js
CONTEXT @test/unit/decision.test.js

PROMPT Ensure all edge cases are covered and tests pass.
```

**Quirks Documentation Pattern:**

From NRG's test quirks:
```
- **OWN-INC-Q01**: Email normalization not applied
- **NSJWT-Q01**: Async timing in token exchange handler
- **TRG-CC-Q01**: remove_joined_groups_via_policy trigger behavior
```

This pattern could be automated:

```dockerfile
# workflows/document-quirks.copilot
MODEL claude-sonnet-4.5
MODE docs-only

ADD-DIR ./test
ADD-DIR ./docs

PROMPT Review all test files for skipped tests, workarounds, and unusual behavior.

PROMPT Document each quirk with:
- Unique ID (e.g., OWN-INC-Q01)
- Description of unexpected behavior
- Why it happens
- Workaround or status

PROMPT Update test/quirks/README.md with findings.
```

---

### Pattern 4: Multi-Repository Orchestration (rag-nightscout-ecosystem-alignment)

**What They Did:**
- Created `workspace.lock.json` for 16 external repos
- Python `bootstrap.py` tool for cloning/updating/freezing
- Centralized tooling for validation and traceability

**Git Evidence:**
```
5a2ed6c make traceability: update traceability docs
21da08e Add enhanced tooling for documentation and test traceability
dc84f5a Add comprehensive documentation and implementation summary
```

**Tooling Created:**
```
tools/
├── bootstrap.py           # Multi-repo management
├── query_workspace.py     # Search requirements/gaps
├── validate_json.py       # Schema validation
├── gen_traceability.py    # Traceability matrices
├── run_workflow.py        # Workflow orchestration
└── workspace_cli.py       # Unified CLI
```

**How `copilot do` Would Replace This:**

Instead of custom Python scripts, use ConversationFiles for orchestration:

```bash
# Audit all repos in workspace
copilot loop \
  --parallel 4 \
  --format jsonl \
  workflows/audit-repos/*.copilot \
  --output audit-results.jsonl

# Each repo gets its own audit workflow
ls workflows/audit-repos/
# audit-nightscout.copilot
# audit-aaps.copilot
# audit-loop.copilot
# audit-trio.copilot
```

```dockerfile
# workflows/audit-repos/audit-nightscout.copilot
MODEL claude-sonnet-4.5
MODE audit
MAX-CYCLES 1

CWD ./externals/cgm-remote-monitor
ADD-DIR ./externals/cgm-remote-monitor

PROMPT Audit the Nightscout CGM Remote Monitor repository.

PROMPT Focus on:
- API compatibility (v1, v2, v3)
- Data schema (entries, treatments, profiles)
- Authentication mechanisms
- Real-time capabilities
- Plugin architecture

PROMPT Generate a structured report in JSON format with:
{
  "repo": "cgm-remote-monitor",
  "endpoints": [...],
  "schemas": [...],
  "security": {...},
  "gaps": [...]
}
```

**Traceability Matrix Generation:**

Current approach (custom Python):
```python
# tools/gen_traceability.py
def generate_traceability_matrix():
    requirements = parse_requirements_docs()
    tests = parse_test_specs()
    gaps = find_gaps()
    # ... 300 lines of Python
```

With `copilot do`:

```bash
copilot do workflows/generate-traceability.copilot \
  --mode read-only \
  --output docs/traceability-matrix.md
```

```dockerfile
# workflows/generate-traceability.copilot
MODEL claude-opus-4.5
MODE read-only
MAX-CYCLES 1

ADD-DIR ./docs/requirements
ADD-DIR ./docs/test-specs
ADD-DIR ./tests

PROMPT Generate a comprehensive traceability matrix.

PROMPT Parse all requirements docs and test specs to create a mapping:
- Requirements (REQ-ID) → Tests (TEST-ID) → Implementation (file:line)
- Coverage gaps (requirements without tests)
- Orphaned tests (tests without requirements)
- Priority gaps by severity

PROMPT Output a markdown table with:
| Requirement ID | Description | Test ID | Test File | Coverage Status | Priority |

PROMPT Also generate a JSON version for programmatic use.
```

---

### Pattern 5: Flaky Test Detection (cgm-remote-monitor)

**What They Did:**
- Created `scripts/run-flaky-tests.sh` to run tests multiple times
- Generates reports in `flaky-test-results/`
- Configurable iterations and timeouts

**Git Evidence:**
```
138ca33e Add test instrumentation to detect and warn about flaky tests
b7df149e Add documentation and harnesses for identifying flaky tests
e422a0a1 Add a tool to detect and report on unreliable tests
```

**From replit.md:**
```bash
npm run test:flaky           # Run 10 iterations
npm run test:flaky:quick     # Run 3 iterations
npm run test:flaky:thorough  # Run 20 iterations
```

**How `copilot do` Would Help:**

```bash
# Run flaky test detection, then have Copilot analyze results
npm run test:flaky | \
  copilot do workflows/analyze-flaky-tests.copilot \
    --epilogue - \
    --mode docs-only \
    --output docs/test-specs/flaky-tests-analysis.md
```

```dockerfile
# workflows/analyze-flaky-tests.copilot
MODEL claude-sonnet-4.5
MODE docs-only
MAX-CYCLES 1

PROMPT Analyze the flaky test report provided in the epilogue.

PROMPT For each flaky test:
1. Identify root cause (timing, async, race condition, etc.)
2. Suggest stabilization strategy
3. Estimate risk (High/Medium/Low)
4. Recommend remediation priority

PROMPT Generate a markdown report with:
- Summary statistics
- Test-by-test analysis
- Prioritized action items
- Suggested test infrastructure improvements

PROMPT Do NOT modify test files, only document findings.
```

---

## Workflow Comparison Table

| Task | Current Process | With `copilot do` | Benefits |
|------|----------------|-------------------|----------|
| **System Audit** | Manual code review → Manual doc writing (4-8 hrs) | `copilot do audit.copilot --mode audit` (15 min) | 16-32x faster, reproducible, version-controlled |
| **Requirements Extraction** | Read audit → Manual requirements doc (2-4 hrs) | `copilot do extract-reqs.copilot --prologue audit.md` (10 min) | 12-24x faster, traceable |
| **Test Spec Creation** | Read requirements → Manual test spec (3-5 hrs) | `copilot do gen-test-spec.copilot` (15 min) | 12-20x faster, consistent format |
| **Test Implementation** | Read spec → Write tests manually (5-10 hrs) | `copilot do implement-tests.copilot --mode tests-only` (30 min) | 10-20x faster, fewer bugs |
| **Quirks Documentation** | Discover during testing → Manual doc (1-2 hrs) | Integrated into test workflows | Automatic, not forgotten |
| **Traceability Matrix** | Custom Python script (20 hrs to build, 2 min to run) | `copilot do gen-trace.copilot` (5 min) | No custom tooling needed |
| **Multi-Repo Audit** | Serial manual review (16-32 hrs for 4 repos) | `copilot loop --parallel 4 audit-*.copilot` (1 hr total) | 16-32x faster, parallel execution |

---

## Real Workflow Sequences from Git History

### Sequence 1: Security Audit → Requirements → Tests

**Git commits (cgm-remote-monitor):**
```
1. 5e18cd0e Update documentation with system audit findings
2. fbaaeb22 Add comprehensive authorization and security documentation and test specifications
3. 34335764 Update API documentation to reflect accurate data shape requirements
```

**As ConversationFiles:**

```bash
# Execute the full sequence
copilot loop workflows/security-review/*.copilot \
  --format jsonl \
  --output security-review-results.jsonl

ls workflows/security-review/
# 01-audit.copilot
# 02-requirements.copilot
# 03-test-spec.copilot
# 04-implement-tests.copilot
# 05-update-docs.copilot
```

Each file builds on the previous output, creating a traceable chain.

---

### Sequence 2: Test Development → Quirks → Documentation

**Git commits (nightscout-roles-gateway):**
```
1. 3cd9003 Add dedicated tests for API secret middleware functionality
2. 8164dde Document quirks and skip tests related to external service dependencies
3. b3ebca1 Expand test coverage for user consent and site deletion functionality
4. 0f88e7e Update test specifications to reflect current priorities and progress
```

**As ConversationFiles:**

```dockerfile
# workflows/test-cycle/01-implement.copilot
MODEL claude-sonnet-4.5
MODE tests-only
MAX-CYCLES 3

CONTEXT @lib/middleware/api_secret.js
PROMPT Add comprehensive tests for API secret middleware.
PROMPT Document quirks in test/quirks/README.md if tests must be skipped.

---

# workflows/test-cycle/02-expand.copilot
MODEL claude-sonnet-4.5
MODE tests-only
MAX-CYCLES 2

CONTEXT @test/integration/privy_consent_flow.test.js
PROMPT Expand test coverage for user consent and site deletion.
PROMPT Add edge cases and error scenarios.

---

# workflows/test-cycle/03-update-specs.copilot
MODEL claude-sonnet-4.5
MODE docs-only

PROMPT Update test/quirks/README.md and docs/test-specs/ to reflect new coverage.
PROMPT Include progress tracking and coverage gaps.
```

---

### Sequence 3: Multi-Repo Analysis (rag-nightscout)

**Git commits:**
```
1. 21da08e Add enhanced tooling for documentation and test traceability
2. 591352a capture document organization
3. e1807a4 Add research fixtures and documentation for client data upload patterns
```

**As ConversationFiles:**

```bash
# Bootstrap workspace first
make bootstrap

# Run cross-repo analysis in parallel
copilot loop --parallel 4 workflows/cross-repo/*.copilot \
  --format jsonl \
  --output cross-repo-analysis.jsonl

# Aggregate results
jq -s '.' cross-repo-analysis.jsonl | \
  copilot do workflows/aggregate-findings.copilot \
    --prologue - \
    --mode docs-only \
    --output docs/cross-repo-findings.md
```

```dockerfile
# workflows/cross-repo/treatments-schema-alignment.copilot
MODEL claude-opus-4.5
MODE read-only

CWD ./externals

PROMPT Analyze how AAPS, Loop, and Trio upload treatment data to Nightscout.

PROMPT For each project:
1. Find treatment upload code
2. Document field mappings
3. Identify unique fields
4. Note compatibility issues
5. Document deduplication strategies

CONTEXT @cgm-remote-monitor/lib/api/treatments/
CONTEXT @AndroidAPS/app/src/main/java/info/nightscout/
CONTEXT @LoopWorkspace/Loop/Managers/NightscoutUploadManager.swift
CONTEXT @Trio/FreeAPS/Sources/Services/Network/NightscoutManager.swift

PROMPT Generate a cross-project field mapping table in markdown.
```

---

## Key Patterns Enabled by `copilot do`

### 1. Bounded Execution for Safety

From the proposal:
> `--max-cycles=1` (default) ensures predictable, bounded execution suitable for scripting

This prevents runaway AI conversations in CI/CD, critical for medical software.

**Nightscout Use Case:**
```bash
# Safe audit: can't make changes, bounded execution
copilot do audit-api.copilot --mode audit --max-cycles=1
```

---

### 2. Mode-Based Access Control

The proposal's modes map DIRECTLY to Nightscout's needs:

| Mode | Nightscout Use Case | Safety Benefit |
|------|---------------------|----------------|
| `read-only` | Audits, analysis, documentation review | Cannot corrupt code |
| `docs-only` | Update docs after code changes | Code stays intact |
| `tests-only` | Add tests without touching implementation | Safe to run in CI |
| `audit` | Security reviews, compliance checks | Read-only with report generation |

**Example from NRG:**

```bash
# Safe documentation update after policy changes
copilot do workflows/update-policy-docs.copilot \
  --mode docs-only \
  --allow-path "docs/**" \
  --yolo  # Safe because mode prevents code changes
```

---

### 3. Traceability via Prologue/Epilogue

The proposal's `--prologue` and `--epilogue` enable pipeline composition:

```bash
# Extract requirements from audit
cat docs/audits/security-audit.md | \
  copilot do extract-requirements.copilot \
    --prologue "Date: $(date)" \
    --epilogue - \
    --output docs/requirements/security-requirements.md

# Generate tests from requirements
cat docs/requirements/security-requirements.md | \
  copilot do generate-test-spec.copilot \
    --prologue "Generated from security-requirements.md on $(date)" \
    --epilogue - \
    --output docs/test-specs/security-tests.md
```

Each step is documented, traceable, and reproducible.

---

### 4. Parallel Execution for Speed

From the proposal:
> `copilot loop --parallel 4 workflows/*.copilot`

**Nightscout Ecosystem Use:**

```bash
# Audit all 4 major projects in parallel
copilot loop --parallel 4 workflows/audit-projects/*.copilot \
  --format jsonl \
  --output ecosystem-audit.jsonl

# Aggregate results
jq -s '[.[] | select(.status == "success")]' ecosystem-audit.jsonl | \
  copilot do workflows/ecosystem-summary.copilot \
    --prologue - \
    --output docs/ecosystem-status.md
```

This parallelization is EXACTLY what `rag-nightscout-ecosystem-alignment` needs but currently does manually.

---

### 5. Version-Controlled Workflows

**Current State:**
- Nightscout projects have custom Python scripts
- Workflows exist but are undocumented
- Team knowledge in developer heads

**With ConversationFiles:**

```bash
git add workflows/
git commit -m "Add automated audit and test workflows"
```

Now workflows are:
- ✅ Version controlled
- ✅ Code reviewed
- ✅ Documented
- ✅ Shareable across team
- ✅ Reproducible in CI/CD

---

## Specific Nightscout Workflows as ConversationFiles

### Workflow 1: OIDC Actor Identity Implementation

Both `cgm-remote-monitor` and `nightscout-roles-gateway` have this proposal.

**Manual Process:**
1. Review proposal doc
2. Identify touchpoints in both repos
3. Plan implementation phases
4. Write tests
5. Implement changes
6. Update docs

**With `copilot do`:**

```bash
# Phase 1: Gap analysis
copilot do workflows/oidc/01-gap-analysis.copilot \
  --mode read-only \
  --output docs/oidc-gap-analysis.md

# Phase 2: Generate test specs
copilot do workflows/oidc/02-test-specs.copilot \
  --prologue <(cat docs/oidc-gap-analysis.md) \
  --mode docs-only \
  --output docs/test-specs/oidc-tests.md

# Phase 3: Implement tests
copilot do workflows/oidc/03-implement-tests.copilot \
  --prologue <(cat docs/test-specs/oidc-tests.md) \
  --mode tests-only \
  --allow-path "tests/**" \
  --max-cycles 3

# Phase 4: Implement feature
copilot do workflows/oidc/04-implement-feature.copilot \
  --prologue <(cat docs/test-specs/oidc-tests.md) \
  --allow-path "lib/**" \
  --max-cycles 5

# Phase 5: Update documentation
copilot do workflows/oidc/05-update-docs.copilot \
  --mode docs-only
```

Each phase is:
- Bounded (max-cycles)
- Safe (mode restrictions)
- Traceable (prologue chains)
- Reproducible (version-controlled)

---

### Workflow 2: Cross-Repo Schema Alignment

From `rag-nightscout-ecosystem-alignment`:

**Manual Process:**
1. Clone 16 repos
2. Manually search for schema definitions
3. Compare field names and types
4. Document mismatches
5. Propose alignment strategy

**With `copilot do`:**

```dockerfile
# workflows/schema-alignment/analyze-treatments.copilot
MODEL claude-opus-4.5
MODE read-only
MAX-CYCLES 1

CWD ./externals

PROMPT Compare treatment schema across Nightscout, AAPS, Loop, and Trio.

CONTEXT @cgm-remote-monitor/lib/api/treatments/index.js
CONTEXT @cgm-remote-monitor/docs/data-schemas/treatments-schema.md
CONTEXT @AndroidAPS/app/src/main/java/info/nightscout/androidaps/plugins/general/nsclient/
CONTEXT @LoopWorkspace/Loop/Managers/NightscoutDataManager.swift
CONTEXT @Trio/FreeAPS/Sources/Services/Network/NightscoutManager.swift

PROMPT Create a comprehensive field mapping table:
| Field Name | Nightscout | AAPS | Loop | Trio | Data Type | Notes |

PROMPT Identify:
- Fields present in all systems
- System-specific extensions
- Type mismatches
- Naming inconsistencies
- Deduplication strategies

PROMPT Output in markdown and JSON formats.
```

Run it:

```bash
copilot do workflows/schema-alignment/analyze-treatments.copilot \
  --mode read-only \
  --format json \
  --output mapping/cross-project/treatments-alignment.json

# Also get markdown report
copilot do workflows/schema-alignment/analyze-treatments.copilot \
  --mode read-only \
  --format markdown \
  --output mapping/cross-project/treatments-alignment.md
```

---

### Workflow 3: Test Migration After MongoDB Upgrade

From `cgm-remote-monitor` git history:

```
6cc9b506 test: Complete Phase 1 - MongoDB modernization test suite
594b6465 include tests assessing impact of mongodb changes
```

**Manual Process:**
1. Review MongoDB 5.x breaking changes
2. Identify affected code paths
3. Write tests for edge cases
4. Fix compatibility issues
5. Verify all tests pass

**With `copilot do`:**

```bash
# Phase 1: Impact assessment
copilot do workflows/mongodb-upgrade/01-impact-assessment.copilot \
  --mode read-only \
  --output docs/mongodb-5x-impact.md

# Phase 2: Test creation
copilot do workflows/mongodb-upgrade/02-create-tests.copilot \
  --prologue <(cat docs/mongodb-5x-impact.md) \
  --mode tests-only \
  --max-cycles 3

# Phase 3: Fix compatibility issues
copilot do workflows/mongodb-upgrade/03-fix-compatibility.copilot \
  --allow-path "lib/storage/**" \
  --allow-path "lib/api/**" \
  --deny-file "package.json" \
  --max-cycles 5

# Phase 4: Verify and document
npm test && \
  copilot do workflows/mongodb-upgrade/04-document-changes.copilot \
    --mode docs-only \
    --output docs/proposals/mongodb-modernization-completed.md
```

---

### Workflow 4: Documentation Consistency Check

From both repos' git history - many commits updating docs after code changes.

**With `copilot do`:**

```bash
# Run after any code change in CI/CD
copilot do workflows/verify-docs-consistency.copilot \
  --mode read-only \
  --format json \
  --output docs-consistency-report.json

# In CI, fail if inconsistencies found
jq -e '.inconsistencies | length == 0' docs-consistency-report.json || exit 1
```

```dockerfile
# workflows/verify-docs-consistency.copilot
MODEL claude-sonnet-4.5
MODE read-only
MAX-CYCLES 1

ADD-DIR ./lib
ADD-DIR ./docs

PROMPT Compare code implementation against documentation.

PROMPT Check for:
1. API endpoints in code vs. documented endpoints
2. Function signatures vs. documented APIs
3. Environment variables in code vs. docs
4. Configuration options vs. documented settings
5. Error codes vs. documented errors

PROMPT Output JSON:
{
  "inconsistencies": [
    {
      "type": "api_endpoint",
      "code": "GET /api/v3/entries/:id",
      "docs": "GET /api/v3/entry/:id",
      "severity": "high"
    }
  ],
  "coverage_gaps": [...],
  "undocumented_features": [...]
}

PROMPT Also include markdown summary for human review.
```

---

## CI/CD Integration Examples

### Nightscout CI/CD with `copilot do`

**Current State:**
- Manual testing
- No automated documentation checks
- No automated audit reports

**Enhanced CI/CD:**

```yaml
# .github/workflows/copilot-checks.yml
name: Copilot Automated Checks

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/copilot-cli@v1
      
      # Security audit (read-only)
      - name: Security Audit
        run: |
          copilot do workflows/ci/security-audit.copilot \
            --mode audit \
            --format json \
            --output security-audit.json
      
      # Upload as artifact
      - uses: actions/upload-artifact@v4
        with:
          name: security-audit
          path: security-audit.json
      
      # Fail if high-severity issues found
      - name: Check Security Issues
        run: |
          CRITICAL=$(jq '[.findings[] | select(.severity == "critical")] | length' security-audit.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "Found $CRITICAL critical security issues"
            exit 1
          fi

  docs-consistency:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/copilot-cli@v1
      
      - name: Verify Documentation Consistency
        run: |
          copilot do workflows/ci/verify-docs.copilot \
            --mode read-only \
            --format json \
            --output docs-check.json
      
      - name: Check for Inconsistencies
        run: |
          ISSUES=$(jq '.inconsistencies | length' docs-check.json)
          if [ "$ISSUES" -gt 0 ]; then
            echo "Documentation inconsistencies found:"
            jq '.inconsistencies' docs-check.json
            exit 1
          fi

  test-spec-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/copilot-cli@v1
      
      - name: Verify Test Coverage
        run: |
          copilot do workflows/ci/test-coverage-check.copilot \
            --mode read-only \
            --format json \
            --output coverage-gaps.json
      
      - name: Report Gaps
        run: |
          HIGH_PRIORITY=$(jq '[.gaps[] | select(.priority == "high")] | length' coverage-gaps.json)
          echo "High priority test gaps: $HIGH_PRIORITY"
          jq '.gaps[] | select(.priority == "high")' coverage-gaps.json
```

---

## Cost-Benefit Analysis

### Time Savings (Conservative Estimates)

Based on git history frequency:

| Activity | Frequency/Year | Manual Time | `copilot do` Time | Annual Savings |
|----------|----------------|-------------|-------------------|----------------|
| System Audits | 7 | 6 hrs | 20 min | 40 hrs |
| Requirements Docs | 10 | 3 hrs | 15 min | 27.5 hrs |
| Test Specs | 15 | 4 hrs | 20 min | 55 hrs |
| Test Implementation | 50 | 6 hrs | 1 hr | 250 hrs |
| Doc Updates | 100 | 1 hr | 10 min | 83 hrs |
| Cross-Repo Analysis | 4 | 8 hrs | 1 hr | 28 hrs |
| **TOTAL** | | | | **483.5 hrs/year** |

**Per Developer:**
- 483.5 hours = ~12 weeks of full-time work
- At $100/hr: **$48,350/year** in time savings
- For a 3-person team: **$145,000/year**

---

### Quality Improvements

**Consistency:**
- All audits follow same format
- All test specs have traceability matrices
- All documentation has source citations

**Reproducibility:**
- New team members run same workflows
- CI/CD runs same analysis on every commit
- No "tribal knowledge" required

**Traceability:**
- Every document cites code sources
- Every test links to requirements
- Every change has audit trail

---

## Migration Path for Existing Projects

### Phase 1: Document Current Workflows
```bash
# Create ConversationFiles for existing processes
copilot do workflows/meta/document-current-workflows.copilot \
  --mode docs-only \
  --output workflows/README.md
```

### Phase 2: Automate Read-Only Tasks
```bash
# Start with audits (safe, read-only)
cp workflows/examples/audit.copilot workflows/audit-api.copilot
copilot do workflows/audit-api.copilot --mode audit
```

### Phase 3: Add Test Workflows
```bash
# Automate test generation (tests-only mode)
copilot do workflows/generate-tests.copilot --mode tests-only
```

### Phase 4: Full Integration
```bash
# CI/CD integration
# Parallel execution
# Multi-repo orchestration
```

---

## Conclusion

The Nightscout ecosystem's development patterns demonstrate EXACTLY the workflows that `copilot do` is designed to enable:

✅ **Audit-first methodology** → `--mode audit`  
✅ **Requirements extraction** → `--prologue` chaining  
✅ **Test-driven development** → `--mode tests-only`  
✅ **Documentation consistency** → `--mode docs-only`  
✅ **Multi-repo orchestration** → `copilot loop --parallel`  
✅ **Traceability** → Version-controlled ConversationFiles  
✅ **Reproducibility** → Declarative, bounded execution  

**The workflows already exist** - this proposal just makes them:
- Explicit (version-controlled)
- Reproducible (declarative)
- Automatable (CI/CD ready)
- Scalable (parallel execution)
- Safe (mode-based access control)

**Impact:**
- 483+ hours saved per developer per year
- Higher quality documentation
- Better test coverage
- Faster onboarding
- Safer automation

This is not a theoretical proposal - it's a formalization of proven, real-world development patterns that are currently manual and tribal.
