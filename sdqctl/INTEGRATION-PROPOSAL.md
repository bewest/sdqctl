# sdqctl ↔ rag-nightscout-ecosystem-alignment Integration Proposal

**Version:** 1.0  
**Date:** 2026-01-20  
**Status:** Proposal

---

## Executive Summary

This document proposes integrating the tooling from `rag-nightscout-ecosystem-alignment` into the `sdqctl` CLI, creating a unified command-line interface for:

1. **Workspace management** - Multi-repo bootstrapping and synchronization
2. **Static verification** - Code references, coverage, terminology, assertions
3. **Traceability** - Requirements ↔ tests ↔ documentation mapping
4. **AI-assisted workflows** - Using the .conv format for reproducible analysis

Additionally, the research fixtures from the ecosystem alignment project can be converted into:
- **pytest fixtures** for sdqctl testing
- **Example .conv workflows** for documentation and demonstration

---

## Part 1: Current State Analysis

### 1.1 sdqctl Capabilities

| Feature | Status | Implementation |
|---------|--------|----------------|
| ConversationFile parser | ✅ Complete | `core/conversation.py` |
| Context management | ✅ Complete | `core/context.py` |
| Session/checkpoint | ✅ Complete | `core/session.py` |
| Mock adapter | ✅ Complete | `adapters/mock.py` |
| Copilot adapter | ✅ Complete | `adapters/copilot.py` |
| `sdqctl run` | ✅ Complete | `commands/run.py` |
| `sdqctl cycle` | ✅ Complete | `commands/cycle.py` |
| `sdqctl flow` | ✅ Complete | `commands/flow.py` |
| `sdqctl status` | ✅ Complete | `commands/status.py` |
| `sdqctl validate` | ✅ Basic | Built into `cli.py` |
| Workspace management | ❌ Missing | - |
| Static verification | ❌ Missing | - |
| Traceability | ❌ Missing | - |

### 1.2 rag-nightscout Tools Inventory

Located in `externals/rag-nightscout-ecosystem-alignment/tools/`:

| Tool | Lines | Purpose | CLI Interface |
|------|-------|---------|---------------|
| `bootstrap.py` | 340 | Clone/update repos from lockfile | argparse: `bootstrap`, `status`, `freeze`, `add`, `remove` |
| `workspace_cli.py` | 330 | Unified CLI wrapper | argparse: `status`, `validate`, `verify`, `query`, `trace` |
| `run_workflow.py` | 290 | Orchestrate validation workflows | argparse: `--workflow`, `--quick`, `--json` |
| `gen_traceability.py` | 400 | Generate traceability matrices | argparse: `--type`, `--json`, `--include-code-refs` |
| `query_workspace.py` | 330 | Search docs, requirements, gaps | argparse: `--req`, `--gap`, `--search`, `--term` |
| `verify_refs.py` | 350 | Validate code references | argparse: `--verbose`, `--json`, `--fix-stale` |
| `verify_coverage.py` | 360 | Coverage analysis | argparse: `--verbose`, `--json` |
| `verify_terminology.py` | 320 | Terminology consistency | argparse: `--verbose`, `--json` |
| `verify_assertions.py` | 370 | Assertion tracing | argparse: `--verbose`, `--json` |
| `validate_json.py` | 290 | Schema validation | argparse: `--verbose`, `--json` |
| `validate_fixtures.py` | 260 | Fixture validation | argparse: `--verbose` |
| `gen_coverage.py` | 260 | Coverage matrix generation | argparse: `--verbose` |
| `gen_inventory.py` | 300 | Workspace inventory | argparse: `--verbose` |
| `linkcheck.py` | 250 | Link validation | argparse: `--verbose` |
| `run_conformance.py` | 280 | Conformance tests | argparse: `--verbose` |

**Common patterns across tools:**
- All use `argparse` for CLI
- All support `--json` for machine-readable output
- All use `WORKSPACE_ROOT = Path(__file__).parent.parent`
- All write reports to `traceability/` directory
- Exit code 0 on success, 1 on failure

### 1.3 Makefile Analysis

The Makefile provides 22 targets wrapping Python tools:

```makefile
# Repository management
bootstrap    → python3 tools/bootstrap.py bootstrap
status       → python3 tools/bootstrap.py status
freeze       → python3 tools/bootstrap.py freeze
submodules   → python3 tools/checkout_submodules.py all
clean        → rm -rf externals/*

# Validation & Testing
validate     → python3 tools/validate_fixtures.py
conformance  → python3 tools/run_conformance.py
coverage     → python3 tools/gen_coverage.py
inventory    → python3 tools/gen_inventory.py
check        → validate + conformance + linkcheck
ci           → check + coverage + verify + compileall

# Static Verification
verify       → verify_refs + verify_coverage + verify_terminology + verify_assertions
verify-refs  → python3 tools/verify_refs.py
verify-coverage → python3 tools/verify_coverage.py
verify-terminology → python3 tools/verify_terminology.py
verify-assertions → python3 tools/verify_assertions.py

# New Tooling
query        → python3 tools/query_workspace.py --search "$(TERM)"
trace        → python3 tools/query_workspace.py --req/--gap "$(ID)"
traceability → python3 tools/gen_traceability.py
validate-json → python3 tools/validate_json.py
workflow     → python3 tools/run_workflow.py --workflow $(TYPE)
cli          → python3 tools/workspace_cli.py
```

---

## Part 2: Integration Design

### 2.1 Proposed sdqctl Command Structure

```
sdqctl
├── run              # (existing) Single prompt/workflow
├── cycle            # (existing) Multi-cycle with compaction
├── flow             # (existing) Batch execution
├── status           # (existing) Session status
├── init             # (existing) Initialize project
├── validate         # (existing) Validate .conv files
├── show             # (existing) Display parsed .conv
├── resume           # (existing) Resume from pause
│
├── workspace        # NEW: Multi-repo workspace management
│   ├── sync         # Clone/update repos (make bootstrap)
│   ├── status       # Repo status (make status)
│   ├── freeze       # Pin versions (make freeze)
│   ├── inventory    # Generate inventory (make inventory)
│   ├── add          # Add repository
│   ├── remove       # Remove repository
│   └── clean        # Remove cloned repos (make clean)
│
├── verify           # NEW: Static verification suite
│   ├── all          # Run all verifications (make verify)
│   ├── refs         # Code reference validation (make verify-refs)
│   ├── coverage     # Coverage analysis (make verify-coverage)
│   ├── terminology  # Term consistency (make verify-terminology)
│   ├── assertions   # Assertion tracing (make verify-assertions)
│   └── links        # Link checking
│
├── trace            # NEW: Traceability commands
│   ├── req          # Trace requirement (sdqctl trace req REQ-001)
│   ├── gap          # Trace gap (sdqctl trace gap GAP-SYNC-001)
│   ├── matrix       # Generate full matrix (make traceability)
│   └── search       # Search docs (make query TERM=x)
│
├── conformance      # NEW: Conformance testing (make conformance)
│
└── ci               # NEW: Full CI pipeline (make ci)
```

### 2.2 Command Mapping: Makefile → sdqctl

| Make Target | sdqctl Command | Notes |
|-------------|----------------|-------|
| `make bootstrap` | `sdqctl workspace sync` | "sync" implies update existing |
| `make status` | `sdqctl workspace status` | Direct mapping |
| `make freeze` | `sdqctl workspace freeze` | Direct mapping |
| `make submodules` | `sdqctl workspace sync --submodules` | Flag on sync |
| `make clean` | `sdqctl workspace clean` | Direct mapping |
| `make validate` | `sdqctl validate --fixtures` | Extend existing validate |
| `make conformance` | `sdqctl conformance` | New command |
| `make coverage` | `sdqctl verify coverage --report` | Part of verify |
| `make inventory` | `sdqctl workspace inventory` | Part of workspace |
| `make check` | `sdqctl verify --quick` | Quick subset |
| `make ci` | `sdqctl ci` | New command |
| `make verify` | `sdqctl verify all` | Run all verifiers |
| `make verify-refs` | `sdqctl verify refs` | Direct mapping |
| `make verify-coverage` | `sdqctl verify coverage` | Direct mapping |
| `make verify-terminology` | `sdqctl verify terminology` | Direct mapping |
| `make verify-assertions` | `sdqctl verify assertions` | Direct mapping |
| `make query TERM=x` | `sdqctl trace search "x"` | Part of trace |
| `make trace ID=x` | `sdqctl trace req REQ-xxx` | Part of trace |
| `make traceability` | `sdqctl trace matrix` | Part of trace |
| `make validate-json` | `sdqctl validate --json-schema` | Extend validate |
| `make workflow TYPE=x` | `sdqctl flow --type x` | Extend existing flow |
| `make cli` | `sdqctl --interactive` | Interactive mode flag |

### 2.3 Implementation Approach

**Option A: Embed tools directly**
- Copy Python code into sdqctl
- Refactor to use click instead of argparse
- Pros: Self-contained, single package
- Cons: Code duplication, harder to keep in sync

**Option B: Wrap tools as subprocess**
- sdqctl calls existing Python scripts
- Pros: No code changes to tools
- Cons: Dependency on external tools directory

**Option C: Import as library** ⭐ Recommended
- Package rag-nightscout tools as importable module
- sdqctl imports and calls functions directly
- Pros: No subprocess overhead, type safety, testable
- Cons: Requires refactoring tools for import

### 2.4 Architecture for Option C

```python
# sdqctl/commands/workspace.py
import click
from rag_ecosystem_tools import bootstrap, inventory

@click.group()
def workspace():
    """Multi-repo workspace management."""
    pass

@workspace.command()
@click.option("--json", "json_output", is_flag=True)
def sync(json_output: bool):
    """Clone/update all repositories from lockfile."""
    result = bootstrap.bootstrap_workspace()
    if json_output:
        click.echo(json.dumps(result))
    else:
        for repo, status in result.items():
            click.echo(f"{repo}: {status}")
```

```python
# sdqctl/commands/verify.py
import click
from rag_ecosystem_tools import (
    verify_refs,
    verify_coverage, 
    verify_terminology,
    verify_assertions,
)

@click.group()
def verify():
    """Static verification suite."""
    pass

@verify.command()
@click.option("--json", "json_output", is_flag=True)
@click.option("--fix-stale", is_flag=True)
def refs(json_output: bool, fix_stale: bool):
    """Verify code references resolve to actual files."""
    result = verify_refs.validate_all_refs(fix_stale=fix_stale)
    # ... output handling
```

---

## Part 3: Fixture Integration

### 3.1 Existing Fixtures Inventory

Located in `externals/rag-nightscout-ecosystem-alignment/docs/60-research/fixtures/`:

| File | Size | Content | Data Structures |
|------|------|---------|-----------------|
| `aaps-single-doc.js` | 4KB | AAPS upload patterns | `sgvEntry`, `smbBolus`, `mealBolus`, `tempBasal`, `carbCorrection`, `temporaryTarget` |
| `loop-batch.js` | 2KB | Loop batch uploads | `sgvBatch`, `treatmentBatch` |
| `trio-pipeline.js` | 5KB | Trio pipeline data | `pipeline`, `stages`, `validations` |
| `deduplication.js` | 4KB | Dedup scenarios | `aapsDuplicatePumpId`, `aapsDuplicateEntry`, `loopDuplicateSyncId`, `loopDuplicateDose` |
| `edge-cases.js` | 6KB | Edge case data | `emptyArray`, `nullAndUndefinedFields`, `mixedValidityBatch`, `extendedEmulatedTempBasal`, `largeProfileJson` |
| `partial-failures.js` | 5KB | Failure modes | `partialBatchFailure`, `retryScenarios` |
| `index.js` | 1KB | Fixture exports | Module index |

### 3.2 Fixture → pytest Conversion Strategy

**Step 1: Convert JS fixtures to Python data structures**

```python
# sdqctl/tests/fixtures/aaps_data.py
"""AAPS upload pattern fixtures - converted from JS research fixtures."""

import pytest
from datetime import datetime, timezone

@pytest.fixture
def aaps_sgv_entry():
    """AAPS-style SGV entry."""
    return {
        "type": "sgv",
        "sgv": 120,
        "date": int(datetime.now(timezone.utc).timestamp() * 1000),
        "dateString": datetime.now(timezone.utc).isoformat(),
        "device": "AndroidAPS-DexcomG6",
        "direction": "Flat",
        "app": "AAPS",
        "utcOffset": 120,
    }

@pytest.fixture
def aaps_smb_bolus():
    """AAPS SMB (Super Micro Bolus) entry."""
    return {
        "eventType": "Correction Bolus",
        "insulin": 0.25,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "date": int(datetime.now(timezone.utc).timestamp() * 1000),
        "type": "SMB",
        "isValid": True,
        "isSMB": True,
        "pumpId": 4148,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }

@pytest.fixture
def aaps_temp_basal():
    """AAPS temporary basal rate entry."""
    return {
        "eventType": "Temp Basal",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "enteredBy": "openaps://AndroidAPS",
        "isValid": True,
        "duration": 60,
        "rate": 0,
        "type": "NORMAL",
        "absolute": 0,
        "pumpId": 284835,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }
```

**Step 2: Create deduplication scenario fixtures**

```python
# sdqctl/tests/fixtures/dedup_scenarios.py
"""Deduplication test scenarios - converted from JS research fixtures."""

import pytest

@pytest.fixture
def duplicate_pump_id_pair():
    """Two entries with same pumpId - should be deduplicated."""
    base = {
        "eventType": "Correction Bolus",
        "insulin": 0.25,
        "type": "SMB",
        "isValid": True,
        "isSMB": True,
        "pumpId": 4148,
        "pumpType": "ACCU_CHEK_INSIGHT_BLUETOOTH",
        "pumpSerial": "33013206",
        "app": "AAPS",
    }
    return {"first": base.copy(), "duplicate": base.copy()}

@pytest.fixture
def duplicate_sync_id_pair():
    """Two Loop entries with same syncIdentifier."""
    base = {
        "eventType": "Carb Correction",
        "carbs": 15,
        "syncIdentifier": "loop-sync-abc123",
        "created_at": "2024-01-18T12:00:00.000Z",
        "enteredBy": "loop://iPhone",
    }
    return {"first": base.copy(), "duplicate": base.copy()}
```

**Step 3: Create edge case fixtures**

```python
# sdqctl/tests/fixtures/edge_cases.py
"""Edge case fixtures for error handling tests."""

import pytest

@pytest.fixture
def empty_array():
    """Empty array - should handle gracefully."""
    return []

@pytest.fixture
def null_fields_entry():
    """Entry with null/None fields."""
    return {
        "type": "sgv",
        "sgv": 120,
        "date": 1705579200000,
        "direction": None,
        "device": None,
        "noise": None,
        "filtered": None,
    }

@pytest.fixture
def mixed_validity_batch():
    """Batch with mixed isValid states."""
    return [
        {"type": "sgv", "sgv": 120, "isValid": True},
        {"type": "sgv", "sgv": 115, "isValid": False},
        {"type": "sgv", "sgv": 125, "isValid": True},
    ]
```

### 3.3 Fixture → .conv Workflow Generation

**Template pattern:**

```dockerfile
# Generated workflow template
# Source: docs/60-research/fixtures/{fixture_name}.js

MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

# Include fixture and related documentation
CONTEXT @docs/60-research/fixtures/{fixture_name}.js
CONTEXT @mapping/client/{client_type}-upload.md

PROMPT Analyze the {client_name} upload pattern:
1. Data schema validation
2. Required vs optional fields
3. Deduplication strategy
4. Timestamp handling
5. Error scenarios

OUTPUT-FORMAT markdown
OUTPUT-FILE analysis/{fixture_name}-analysis.md
```

**Generated examples:**

```dockerfile
# workflows/nightscout/aaps-upload-audit.conv
MODEL gpt-4
ADAPTER mock  
MODE audit
MAX-CYCLES 1

CONTEXT @docs/60-research/fixtures/aaps-single-doc.js
CONTEXT @mapping/client/aaps-openaps-upload.md

PROMPT Analyze the AAPS upload pattern for:
1. SGV entry schema compliance
2. Treatment event validation
3. Pump ID-based deduplication
4. Timestamp field handling (date vs dateString vs created_at)
5. App identification patterns

OUTPUT-FORMAT markdown
OUTPUT-FILE audits/aaps-upload-analysis.md
```

```dockerfile
# workflows/nightscout/dedup-strategy-audit.conv
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @docs/60-research/fixtures/deduplication.js
CONTEXT @mapping/client/aaps-openaps-upload.md
CONTEXT @mapping/client/loop-upload.md

PROMPT Analyze deduplication strategies across AID systems:
1. AAPS pumpId-based deduplication
2. Loop syncIdentifier-based deduplication
3. Timestamp-based fallback strategies
4. Edge cases: same content, different IDs
5. Recommendations for unified approach

OUTPUT-FORMAT markdown
OUTPUT-FILE audits/deduplication-strategy.md
```

```dockerfile
# workflows/nightscout/edge-case-audit.conv
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @docs/60-research/fixtures/edge-cases.js
CONTEXT @specs/nightscout-api/entries-spec.md

PROMPT Analyze edge case handling:
1. Empty array handling
2. Null/undefined field treatment
3. Mixed validity batches
4. Extended/emulated temp basals
5. Large profile JSON handling

PROMPT Generate test recommendations for each edge case.

OUTPUT-FORMAT markdown
OUTPUT-FILE audits/edge-case-handling.md
```

---

## Part 4: Implementation Roadmap

### Phase 1: Core Infrastructure
**Complexity: Low (skeleton + registration)**
**Goal: Add new command groups to sdqctl**

- [ ] Create `sdqctl/commands/workspace.py` skeleton
- [ ] Create `sdqctl/commands/verify.py` skeleton
- [ ] Create `sdqctl/commands/trace.py` skeleton
- [ ] Register new command groups in `cli.py`
- [ ] Add `--json` output support to all new commands
- [ ] Write unit tests for command registration

### Phase 2: Workspace Commands
**Complexity: Moderate (port existing code)**
**Goal: Replace `make bootstrap/status/freeze`**

- [ ] Port `bootstrap.py` functions to importable module
- [ ] Implement `sdqctl workspace sync`
- [ ] Implement `sdqctl workspace status`
- [ ] Implement `sdqctl workspace freeze`
- [ ] Implement `sdqctl workspace inventory`
- [ ] Implement `sdqctl workspace clean`
- [ ] Test against rag-nightscout-ecosystem-alignment repo

### Phase 3: Verify Commands
**Complexity: Moderate (port existing code)**
**Goal: Replace `make verify-*`**

- [ ] Port `verify_refs.py` to importable module
- [ ] Port `verify_coverage.py` to importable module
- [ ] Port `verify_terminology.py` to importable module
- [ ] Port `verify_assertions.py` to importable module
- [ ] Implement `sdqctl verify refs`
- [ ] Implement `sdqctl verify coverage`
- [ ] Implement `sdqctl verify terminology`
- [ ] Implement `sdqctl verify assertions`
- [ ] Implement `sdqctl verify all`
- [ ] Add `--fix` options where applicable

### Phase 4: Trace Commands
**Complexity: Moderate (port existing code)**
**Goal: Replace `make query/trace/traceability`**

- [ ] Port `query_workspace.py` to importable module
- [ ] Port `gen_traceability.py` to importable module
- [ ] Implement `sdqctl trace req REQ-xxx`
- [ ] Implement `sdqctl trace gap GAP-xxx`
- [ ] Implement `sdqctl trace matrix`
- [ ] Implement `sdqctl trace search "term"`

### Phase 5: CI & Conformance
**Complexity: Low (orchestration layer)**
**Goal: Replace `make ci` and `make conformance`**

- [ ] Port `run_conformance.py` to importable module
- [ ] Implement `sdqctl conformance`
- [ ] Implement `sdqctl ci` (orchestrates all checks)
- [ ] Create GitHub Actions workflow using sdqctl

### Phase 6: Fixture Integration
**Complexity: High (cross-language conversion)**
**Goal: Generate tests and workflows from fixtures**

- [ ] Create fixture conversion script
- [ ] Generate `sdqctl/tests/fixtures/*.py` from JS fixtures
- [ ] Generate `sdqctl/examples/workflows/nightscout/*.conv`
- [ ] Write tests using converted fixtures
- [ ] Document fixture-to-workflow patterns

### Phase 7: Documentation & Migration
**Complexity: Low (documentation)**
**Goal: Complete documentation and deprecation guide**

- [ ] Update sdqctl README with new commands
- [ ] Create migration guide: Makefile → sdqctl
- [ ] Add deprecation notices to Makefile
- [ ] Create command reference documentation
- [ ] Record demo/tutorial

---

## Part 5: Benefits Analysis

### 5.1 Benefits of Unification

| Benefit | Description |
|---------|-------------|
| **Single entry point** | `sdqctl` replaces `make` + `python tools/X.py` |
| **Consistent UX** | All commands use click, consistent flags |
| **Better discoverability** | `sdqctl --help` shows all capabilities |
| **JSON output** | All commands support `--json` for automation |
| **Cross-platform** | No GNU Make dependency |
| **Testable** | Python code can be unit tested |
| **Composable** | Commands can be chained in workflows |
| **AI-ready** | Verification results feed into .conv workflows |

### 5.2 Benefits of Fixture Integration

| Benefit | Description |
|---------|-------------|
| **Real-world data** | Tests use actual ecosystem patterns |
| **Living documentation** | .conv files document expected behavior |
| **Regression detection** | Catch breaking changes early |
| **Example workflows** | New users see practical examples |
| **Coverage** | Systematic testing across AID systems |

### 5.3 Metrics for Success

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Command coverage | 100% | All Makefile targets have sdqctl equivalent |
| Test coverage | 80%+ | pytest coverage report |
| CI time | <5 min | GitHub Actions workflow time |
| Documentation | Complete | All commands documented |
| Adoption | Makefile deprecated | Users switch to sdqctl |

---

## Part 6: Risk Assessment

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tool porting complexity | Medium | Medium | Start with simplest tools (bootstrap) |
| Breaking changes | Low | High | Maintain backward compat, deprecation period |
| Performance regression | Low | Medium | Benchmark before/after |
| Missing edge cases | Medium | Low | Comprehensive fixture testing |

### 6.2 Organizational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | High | Medium | Strict phasing, MVP approach |
| Maintenance burden | Medium | Medium | Clear ownership, documentation |
| Learning curve | Low | Low | Migration guide, examples |

---

## Appendix A: Tool Interface Details

### verify_refs.py

```python
def validate_all_refs(
    verbose: bool = False,
    fix_stale: bool = False
) -> dict:
    """
    Validate code references in mapping documents.
    
    Returns:
        {
            "valid": int,
            "broken": int,
            "stale": int,
            "refs": [
                {
                    "ref": "crm:lib/auth.js#L10",
                    "file": "mapping/client/auth.md",
                    "status": "valid|broken|stale",
                    "suggestion": "..." # if fix_stale
                }
            ]
        }
    """
```

### query_workspace.py

```python
def search_workspace(
    term: str,
    filter_type: str = None  # "requirements", "gaps", "docs"
) -> list[dict]:
    """
    Search workspace for term.
    
    Returns:
        [
            {
                "file": "path/to/file.md",
                "line": 42,
                "context": "...matching line...",
                "type": "requirement|gap|doc"
            }
        ]
    """

def trace_requirement(req_id: str) -> dict:
    """
    Trace a requirement through specs, tests, docs.
    
    Returns:
        {
            "id": "REQ-001",
            "title": "...",
            "specs": ["specs/auth.md"],
            "tests": ["conformance/auth.test.js"],
            "docs": ["docs/auth.md"],
            "gaps": ["GAP-AUTH-001"]
        }
    """
```

---

## Appendix B: Fixture Conversion Script

```python
#!/usr/bin/env python3
"""Convert JS fixtures to Python pytest fixtures."""

import json
import re
from pathlib import Path

JS_FIXTURE_DIR = Path("externals/rag-nightscout-ecosystem-alignment/docs/60-research/fixtures")
PY_FIXTURE_DIR = Path("sdqctl/tests/fixtures")
CONV_WORKFLOW_DIR = Path("sdqctl/examples/workflows/nightscout")

def convert_js_to_python(js_content: str) -> str:
    """Convert JS fixture to Python pytest fixture."""
    # Parse module.exports = { ... }
    # Convert to @pytest.fixture decorated functions
    # Handle Date.now() → datetime.now()
    # Handle undefined → None
    pass

def generate_conv_workflow(fixture_name: str, fixture_content: dict) -> str:
    """Generate .conv workflow from fixture."""
    template = '''# Generated from {fixture_name}.js
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @docs/60-research/fixtures/{fixture_name}.js

PROMPT Analyze the data patterns in this fixture:
1. Schema compliance
2. Required fields
3. Edge cases
4. Validation rules

OUTPUT-FORMAT markdown
OUTPUT-FILE audits/{fixture_name}-analysis.md
'''
    return template.format(fixture_name=fixture_name)

def main():
    PY_FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    CONV_WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    
    for js_file in JS_FIXTURE_DIR.glob("*.js"):
        if js_file.name == "index.js":
            continue
            
        # Convert to Python fixture
        py_content = convert_js_to_python(js_file.read_text())
        py_file = PY_FIXTURE_DIR / js_file.with_suffix(".py").name
        py_file.write_text(py_content)
        
        # Generate .conv workflow
        conv_content = generate_conv_workflow(js_file.stem, {})
        conv_file = CONV_WORKFLOW_DIR / f"{js_file.stem}-audit.conv"
        conv_file.write_text(conv_content)

if __name__ == "__main__":
    main()
```

---

## Appendix C: Migration Guide Outline

### From Makefile to sdqctl

```bash
# Before (Makefile)
make bootstrap
make status
make verify
make ci

# After (sdqctl)
sdqctl workspace sync
sdqctl workspace status
sdqctl verify all
sdqctl ci
```

### Environment Setup

```bash
# Install sdqctl with ecosystem tools
pip install sdqctl[ecosystem]

# Or install from source
cd sdqctl
pip install -e ".[ecosystem]"
```

### Gradual Migration

1. Install sdqctl alongside existing Makefile
2. Run both in parallel to verify equivalence
3. Update CI to use sdqctl
4. Add deprecation notice to Makefile
5. Remove Makefile after transition period

---

## Conclusion

This proposal outlines a comprehensive integration of rag-nightscout-ecosystem-alignment tooling into sdqctl. The integration:

1. **Unifies** 22 Makefile targets under sdqctl commands
2. **Converts** 7 JS fixtures to Python test fixtures
3. **Generates** example .conv workflows from research material
4. **Maintains** backward compatibility during transition
5. **Improves** discoverability, testability, and AI-readiness

The phased approach minimizes risk while delivering incremental value. The resulting tool will serve both the Nightscout ecosystem and as a reference implementation for similar multi-repo orchestration needs.

---

**Next Steps:**
1. Review and approve this proposal
2. Create tracking issues for each phase
3. Begin Phase 1: Core Infrastructure
