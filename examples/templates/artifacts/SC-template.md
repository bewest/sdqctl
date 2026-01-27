# SC-{DOMAIN}-NNNx: {Safety Constraint Title}

**Status:** PROPOSED | IMPLEMENTED | VERIFIED | DEPLOYED  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD  
**Owner:** @username

---

## Constraint Statement

{Clear statement of what the system MUST do or MUST NOT do to prevent the hazard}

---

## Mitigates

| UCA | Description |
|-----|-------------|
| `UCA-{DOMAIN}-NNN` | {Brief description of the UCA being mitigated} |

---

## Implementation Approach

{How this safety constraint is/will be implemented}

### Design Approach
{Architecture or design decisions}

### Validation Method
{How to verify the constraint is correctly implemented}

- [ ] Unit test
- [ ] Integration test
- [ ] Manual review
- [ ] Runtime monitoring

---

## Traceability

| Relationship | Artifact | Status |
|--------------|----------|--------|
| Mitigates | `UCA-{DOMAIN}-NNN` | |
| Implemented by | `REQ-{DOMAIN}-NNN` | |
| Verified by | `TEST-NNN` | |
| Code location | `alias:path/file.ext#L{start}-L{end}` | |

---

## Implementation Evidence

### Code References
```
{alias}:{path/to/implementation}#L{start}-L{end}
```

### Test References
- `TEST-NNN`: {Test description}

---

## Residual Risk

{Any remaining risk after this constraint is implemented}

**Risk Level:** Acceptable | Needs additional mitigation | Unacceptable

---

## Changelog

- YYYY-MM-DD: Constraint defined
- YYYY-MM-DD: Implementation complete
- YYYY-MM-DD: Verification complete
