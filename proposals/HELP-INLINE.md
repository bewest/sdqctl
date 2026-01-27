# HELP-INLINE Directive Proposal

> **Status**: ✅ Complete (2026-01-27)  
> **Priority**: P3 (Low)  
> **Effort**: Medium  
> **Source**: Nightscout ecosystem workflow requirements

## Summary

Extend the HELP directive to work anywhere in a ConversationFile, not just in prologues. This enables just-in-time help injection mid-workflow.

## Current Behavior

```dockerfile
# HELP only works in prologue section
HELP directives workflow  # ✓ Injected into first prompt

MODEL claude-sonnet-4-20250514
PROMPT Analyze the code.
HELP terminology  # ✗ Ignored or error - not in prologue
PROMPT Identify gaps.
```

HELP topics are collected during parsing and injected as prologues to the **first prompt only**.

## Proposed Behavior

Option A: **HELP-INLINE** as new directive
```dockerfile
PROMPT Analyze the code.
HELP-INLINE terminology  # Injects terminology help BEFORE next prompt
PROMPT Identify gaps using the terms above.
```

Option B: **HELP works like ELIDE** (merge with adjacent)
```dockerfile
PROMPT Analyze the code.
HELP terminology  # Merges with next prompt
PROMPT Identify gaps.
# Result: "Identify gaps." gets terminology prepended
```

Option C: **HELP anywhere, injects as separate prompt**
```dockerfile
PROMPT Analyze the code.
HELP terminology  # Becomes standalone prompt with help content
PROMPT Identify gaps.
```

## Recommendation

**Option A (HELP-INLINE)** provides:
- Backward compatibility (HELP in prologue unchanged)
- Clear intent (INLINE indicates placement)
- Consistent with existing pattern (cf. CONTEXT-OPTIONAL vs CONTEXT)

## Use Cases

### 1. Mid-Workflow Terminology Injection
```dockerfile
PROMPT Analyze treatment handling in Loop.
# Analysis shifts to AAPS which uses different terms
HELP-INLINE terminology
PROMPT Now compare with AAPS using consistent terminology.
```

### 2. Just-in-Time Gap ID Reference
```dockerfile
PROMPT Identify issues with timestamp handling.
HELP-INLINE gap-ids  # Inject GAP-XXX format reference
PROMPT Create gap entries for each issue found.
```

### 3. Safety Guidance Before STPA Analysis
```dockerfile
PROMPT Analyze the insulin bolus command flow.
HELP-INLINE stpa
PROMPT Identify hazards and unsafe control actions.
```

### 4. Conformance Format Before Generation
```dockerfile
PROMPT Summarize batch upload requirements.
HELP-INLINE conformance
PROMPT Generate conformance test scenarios.
```

## Implementation

### Parser Changes

Add `HELP-INLINE` to `DirectiveType` enum:
```python
HELP_INLINE = "HELP-INLINE"  # Inject help inline (not prologue-only)
```

### Applicator Changes

Handle HELP-INLINE as execution directive (like PROMPT/ELIDE):
```python
case DirectiveType.HELP_INLINE:
    topics = directive.value.split()
    help_content = render_help_topics(topics)
    # Create merged step with next prompt
    conv.steps.append(ConversationStep(
        type="help_inline",
        content=help_content,
        merge_with_next=True
    ))
```

### Renderer Changes

When rendering steps, merge HELP-INLINE content with following prompt:
```python
if step.type == "help_inline" and step.merge_with_next:
    next_step = steps[i + 1]
    next_step.content = f"{step.content}\n\n{next_step.content}"
```

## New Help Topics Needed

For Nightscout ecosystem workflows:

| Topic | Description |
|-------|-------------|
| `gap-ids` | GAP-XXX-NNN taxonomy (CGM, TREAT, SYNC, etc.) |
| `5-facet` | 5-facet documentation pattern |
| `stpa` | STPA hazard analysis guidance |
| `conformance` | Conformance test scenario format |
| `nightscout` | Nightscout ecosystem project overview |

## Migration Path

1. Add HELP-INLINE directive (no breaking changes)
2. Add new help topics for ecosystem workflows
3. Update workflows to use HELP-INLINE where beneficial
4. Document in DIRECTIVE-REFERENCE.md

## Related Work

- [REFCAT-DESIGN.md](./REFCAT-DESIGN.md) - Context injection patterns
- [CONSULT-DIRECTIVE.md](./CONSULT-DIRECTIVE.md) - Human-in-loop patterns
- [VERIFICATION-DIRECTIVES.md](./VERIFICATION-DIRECTIVES.md) - Workflow verification

## Open Questions

1. Should HELP-INLINE content be compacted differently than regular prompts?
2. Should multiple HELP-INLINE in sequence merge together?
3. Should HELP-INLINE work in ON-FAILURE/ON-SUCCESS blocks?
