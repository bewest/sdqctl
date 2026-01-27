# Feature Interaction Matrix

> **Status**: Complete  
> **Purpose**: Define how sdqctl features compose when used together  
> **Related**: [BACKLOG.md](../proposals/BACKLOG.md)

---

## Overview

sdqctl features are designed to be orthogonal but must have defined behavior when combined. This document specifies interactions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Feature Dependency Graph                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌─────────────┐                    │
│   │  ELIDE   │────▶│ Affects turn │────▶│   PROMPT    │                    │
│   └──────────┘     │  boundaries  │     │   RUN       │                    │
│                    └──────────────┘     └─────────────┘                    │
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌─────────────┐                    │
│   │ COMPACT  │────▶│ Affects      │────▶│  All prior  │                    │
│   └──────────┘     │  context     │     │  content    │                    │
│                    └──────────────┘     └─────────────┘                    │
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌─────────────┐                    │
│   │  VERIFY  │────▶│ Produces     │────▶│  Affects    │                    │
│   └──────────┘     │  output      │     │  ELIDE/next │                    │
│                    └──────────────┘     └─────────────┘                    │
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌─────────────┐                    │
│   │RUN-BRANCH│────▶│ Control flow │────▶│  ELIDE      │                    │
│   └──────────┘     │  divergence  │     │  CHECKPOINT │                    │
│                    └──────────────┘     └─────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Interaction Matrix

### Legend
- ✅ = Compatible, defined behavior
- ⚠️ = Compatible with constraints
- ❌ = Not allowed (parse error or runtime error)
- 🔶 = Needs design decision

|                 | ELIDE | COMPACT | VERIFY | RUN-BRANCH | CHECKPOINT | MAX-CYCLES |
|-----------------|-------|---------|--------|------------|------------|------------|
| **ELIDE**       | —     | ⚠️      | ✅     | ❌         | ⚠️         | ✅         |
| **COMPACT**     | ⚠️    | —       | ✅     | ✅         | ✅         | ✅         |
| **VERIFY**      | ✅    | ✅      | —      | ✅         | ✅         | ✅         |
| **RUN-BRANCH**  | ❌    | ✅      | ✅     | —          | ✅         | ⚠️         |
| **CHECKPOINT**  | ⚠️    | ✅      | ✅     | ✅         | —          | ✅         |
| **MAX-CYCLES**  | ✅    | ✅      | ✅     | ⚠️         | ✅         | —          |

---

## Detailed Interactions

### ELIDE + RUN-BRANCHING ❌

**Rule**: ELIDE chains MUST NOT contain branching constructs.

```dockerfile
# ❌ INVALID - parse error
RUN pytest
ELIDE
ON-FAILURE
  PROMPT Fix the tests
```

**Rationale**: ELIDE merges adjacent elements into one turn. Branching introduces control flow that can't be "merged" — the branch decision must complete before knowing what to merge.

**Alternative**: Put branching outside the ELIDE chain:

```dockerfile
# ✅ VALID
RUN pytest
ON-FAILURE
  ELIDE
  PROMPT Fix the tests
  RUN pytest
```

---

### ELIDE + COMPACT ⚠️

**Rule**: COMPACT breaks any active ELIDE chain.

```dockerfile
RUN pytest
ELIDE
COMPACT          # ← Breaks the ELIDE chain
PROMPT Analyze   # ← Starts fresh turn after compaction
```

**Rationale**: COMPACT summarizes context and sends to model. This is a natural turn boundary.

---

### ELIDE + CHECKPOINT ⚠️

**Rule**: CHECKPOINT inside ELIDE chain saves state but doesn't break the chain.

```dockerfile
RUN pytest
ELIDE
CHECKPOINT test-complete   # ← State saved, chain continues
PROMPT Fix failures        # ← Still same turn
```

**Rationale**: Checkpoints are metadata operations, not model interactions.

---

### COMPACT + VERIFY ✅

**Decision**: VERIFY output is treated like any other context during COMPACT.

**Behavior**:
1. VERIFY output included in compaction summary (not preserved verbatim)
2. To preserve specific findings, use `COMPACT-PRESERVE verification`
3. Critical VERIFY results should be written to files before COMPACT

```dockerfile
VERIFY refs
VERIFY traceability
# Optional: preserve verification if needed
COMPACT-PRESERVE verification
COMPACT
PROMPT Continue analysis with summarized context...
```

**Rationale**: Consistent with how RUN output and PROMPT results are handled. Users who need exact VERIFY results can save them explicitly.

---

### VERIFY + ELIDE ✅

**Rule**: VERIFY output can be elided into next directive.

```dockerfile
VERIFY-REFS @requirements/*.md
ELIDE
PROMPT Fix any missing references found above.
```

**Behavior**: Agent sees VERIFY results and prompt in same turn.

---

### RUN-BRANCH + CHECKPOINT ✅

**Decision**: CHECKPOINT is allowed inside ON-FAILURE blocks.

```dockerfile
RUN pytest
ON-FAILURE
  CHECKPOINT before-fix
  PROMPT Fix the failing tests
```

**Behavior**: Checkpoint saves the branch state, including:
- The failure context from RUN
- Any prompts/responses within the branch
- Position within the ON-FAILURE block

**Resume behavior**: `sdqctl resume` continues from checkpoint position within the branch.

**Rationale**: Useful for long recovery operations where human review may be needed mid-fix.

---

### RUN-BRANCH + MAX-CYCLES ⚠️

**Rule**: RUN-RETRY attempts count separately from MAX-CYCLES.

```dockerfile
MAX-CYCLES 3
RUN-RETRY 2 pytest   # Up to 2 retries per cycle
```

**Total possible pytest runs**: 3 cycles × 3 attempts = 9

**Rationale**: MAX-CYCLES controls workflow iterations; RUN-RETRY controls command resilience. Conflating them loses granularity.

---

### CHECKPOINT + COMPACT ✅

**Rule**: CHECKPOINT after COMPACT saves the compacted state.

```dockerfile
COMPACT
CHECKPOINT post-compact   # ← Saves summarized context
```

**Behavior**: Resume loads the compacted (smaller) context.

---

## Template Variable Precedence

When using `--from-json` with existing template variables:

| Source | Precedence | Example |
|--------|------------|---------|
| JSON stdin | 1 (highest) | `{"template_variables": {"PROJECT": "loop"}}` |
| CLI flags | 2 | `--var PROJECT=aaps` |
| .conv file | 3 | `PROJECT loop` in workflow |
| Defaults | 4 (lowest) | Built-in defaults |

**Rule**: Later sources can't override earlier sources (stdin wins).

---

## Open Questions

~~1. **COMPACT + VERIFY**: Should verification results be compactable?~~ **Resolved**: Yes, treated as normal context.
~~2. **RUN-BRANCH + CHECKPOINT**: Allow checkpoints in branches?~~ **Resolved**: Yes, allowed.
3. **Nested branching**: Allow ON-FAILURE inside ON-FAILURE? **Decision: No** — parse error to prevent infinite nesting.

---

## REFCAT Interactions

REFCAT is orthogonal to control flow directives. It injects precise file excerpts into context.

| Feature | Interaction | Notes |
|---------|-------------|-------|
| CONTEXT | ✅ Compatible | REFCAT adds partial files alongside full CONTEXT files |
| COMPACT | ✅ Compatible | REFCAT content is compactable |
| ELIDE | ✅ Compatible | REFCAT content available in merged prompts |
| VERIFY | ✅ Compatible | REFCAT refs validated by `sdqctl validate` |

**Key behaviors**:
- REFCAT refs resolved at render time (not parse time)
- Missing refs fail validation in strict mode
- REFCAT content appears before prompts in rendered output

---

## See Also

- [BACKLOG.md](../proposals/BACKLOG.md) - Open design questions
- [SYNTHESIS-CYCLES.md](SYNTHESIS-CYCLES.md) - Workflow patterns
- [GLOSSARY.md](GLOSSARY.md) - Terminology
