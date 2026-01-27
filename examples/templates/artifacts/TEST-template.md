# TEST-NNN: {Test Title}

**Status:** DEFINED | IMPLEMENTED | PASSING | FAILING | SKIPPED  
**Type:** Unit | Integration | System | Acceptance  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD

---

## Verifies

| Artifact | Title |
|----------|-------|
| `SPEC-NNN` | {Specification title} |
| `REQ-{DOMAIN}-NNN` | {Requirement title} |

---

## Test Description

{Clear description of what this test validates}

---

## Prerequisites

- {Prerequisite 1: e.g., "Database seeded with test data"}
- {Prerequisite 2: e.g., "Mock server running"}
- {Prerequisite 3: e.g., "Feature flag enabled"}

---

## Test Steps

1. **Given** {initial state/context}
2. **When** {action performed}
3. **Then** {expected outcome}

### Detailed Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | {action} | {result} |
| 2 | {action} | {result} |
| 3 | {action} | {result} |

---

## Test Data

| Input | Value | Notes |
|-------|-------|-------|
| {param1} | {value} | {notes} |
| {param2} | {value} | {notes} |

---

## Expected Output

```
{Expected output format or values}
```

---

## Pass/Fail Criteria

- **Pass:** {Explicit pass criteria}
- **Fail:** {Explicit fail criteria}

---

## Implementation

**Test File:** `tests/test_{module}.py::test_{name}`

```python
# Example test implementation location
def test_{name}():
    # Given
    ...
    # When
    ...
    # Then
    assert ...
```

---

## Traceability

| Relationship | Artifact |
|--------------|----------|
| Verifies | `SPEC-NNN` |
| Implements | `REQ-{DOMAIN}-NNN` |

---

## Execution History

| Date | Result | Notes |
|------|--------|-------|
| YYYY-MM-DD | PASS/FAIL | {notes} |

---

## Changelog

- YYYY-MM-DD: Test defined
- YYYY-MM-DD: Test implemented
