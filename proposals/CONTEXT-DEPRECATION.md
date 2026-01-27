# Proposal: CONTEXT Directive Deprecation

> **Status**: Draft  
> **Created**: 2026-01-26  
> **Author**: sdqctl development  
> **Related**: [REFCAT-DESIGN.md](REFCAT-DESIGN.md)

---

## Summary

Deprecate the `CONTEXT` directive in favor of `REFCAT` for file content injection. REFCAT provides superset functionality with precise line-level control.

---

## Motivation

### Current State

Two directives for including file content:

| Directive | Syntax | Capability |
|-----------|--------|------------|
| `CONTEXT` | `CONTEXT @path` | Whole file inclusion |
| `REFCAT` | `REFCAT @path#L10-L50` | Line ranges, patterns, aliases |

### Problem

1. **Redundancy**: CONTEXT is a subset of REFCAT functionality
2. **Confusion**: Users unsure which to use
3. **Maintenance**: Two code paths for similar behavior

### Solution

Deprecate CONTEXT with:
1. Emit warning when CONTEXT is parsed
2. Update examples to use REFCAT
3. Document migration path
4. Remove CONTEXT in future version (v2.0)

---

## Migration Guide

### Simple Replacements

| Before | After |
|--------|-------|
| `CONTEXT @path/file.py` | `REFCAT @path/file.py` |
| `CONTEXT @docs/*.md` | `REFCAT @docs/*.md` |
| `CONTEXT-OPTIONAL @file` | `REFCAT @file` (REFCAT handles missing gracefully) |

### REFCAT Advantages

```
# Whole file (same as CONTEXT)
REFCAT @src/main.py

# Specific lines (CONTEXT can't do this)
REFCAT @src/main.py#L1-L50

# Function extraction (CONTEXT can't do this)
REFCAT @src/main.py#/def process/

# Multiple refs in one line
REFCAT @src/a.py#L1-10 @src/b.py#L1-10
```

---

## Implementation

### Phase 1: Warning (Current)

Add deprecation warning to `conversation.py`:

```python
if directive_type == DirectiveType.CONTEXT:
    logger.warning(
        f"CONTEXT directive is deprecated. "
        f"Use REFCAT instead: REFCAT {args}"
    )
```

### Phase 2: Documentation (Current)

- Update all example `.conv` files to use REFCAT
- Add deprecation notice to DIRECTIVE-REFERENCE.md
- Update GETTING-STARTED.md examples

### Phase 3: Removal (v2.0)

- Remove CONTEXT directive parsing
- Error with helpful migration message

---

## Affected Files

### Examples to Update

- `examples/workflows/backlog-processor.conv`
- `examples/workflows/backlog-processor-v2.conv`
- Any other `.conv` files using CONTEXT

### Documentation to Update

- `docs/DIRECTIVE-REFERENCE.md` - Add deprecation notice
- `docs/GETTING-STARTED.md` - Update examples
- `docs/CONTEXT-MANAGEMENT.md` - Note REFCAT preference

---

## Timeline

| Phase | Version | Action |
|-------|---------|--------|
| Warning | v1.x | Emit deprecation warning |
| Docs | v1.x | Update examples and docs |
| Removal | v2.0 | Remove CONTEXT, error with migration help |

---

## Open Questions

None - straightforward deprecation.

---

## Decision

**Approved**: Proceed with deprecation warning and documentation updates.
