# UCA-{DOMAIN}-NNN: {Brief unsafe action description}

**Type:** Type 1 (not providing) | Type 2 (providing) | Type 3 (too early/late) | Type 4 (stopped too soon/too long)  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD

---

## Control Action

{The control action being analyzed (e.g., "Deliver bolus", "Suspend basal", "Send alert")}

---

## Unsafe Control Action

{Complete description of the unsafe control action}

> **Type Definition:**
> - Type 1: Control action not provided (when needed)
> - Type 2: Control action provided (when it shouldn't be)
> - Type 3: Control action provided too early, too late, or out of order
> - Type 4: Control action stopped too soon or applied too long

---

## Context

{The specific conditions under which this UCA could occur}

- Environmental factors:
- System state:
- User state:
- Timing constraints:

---

## Leads to Hazard

| Hazard | Severity |
|--------|----------|
| `HAZ-NNN`: {Hazard title} | Catastrophic | Critical | Marginal | Negligible |

---

## Causal Factors

Potential causes for this UCA:

### Controller Issues
- [ ] Incorrect mental model
- [ ] Inadequate process model
- [ ] Algorithm flaw

### Feedback Issues
- [ ] Missing feedback
- [ ] Delayed feedback
- [ ] Incorrect feedback

### Actuator Issues
- [ ] Component failure
- [ ] Delayed response
- [ ] Inadequate capability

### Process Issues
- [ ] External disturbance
- [ ] Process model inconsistency

---

## Traceability

| Relationship | Artifact | Status |
|--------------|----------|--------|
| Leads to | `HAZ-NNN` | |
| Mitigated by | `SC-{DOMAIN}-NNNx` | |
| Implemented via | `REQ-{DOMAIN}-NNN` | |

---

## Mitigation Status

| Safety Constraint | Status | Notes |
|-------------------|--------|-------|
| `SC-{DOMAIN}-NNNa` | ✅ Implemented / ❌ Pending | |
| `SC-{DOMAIN}-NNNb` | ✅ Implemented / ❌ Pending | |

---

## Changelog

- YYYY-MM-DD: UCA identified during STPA analysis
