# Compaction Configuration Unification

> **Status**: ✅ Complete  
> **Date**: 2026-01-26  
> **Priority**: P2 (Medium)  
> **Scope**: Align directive/CLI naming and fill gaps  
> **Related**: [SDK-INFINITE-SESSIONS.md](SDK-INFINITE-SESSIONS.md)

---

## Executive Summary

The compaction configuration system has evolved organically, resulting in:
- Naming inconsistencies between directives and CLI options
- Missing directive for buffer exhaustion threshold
- Fragile CLI default detection logic
- Phase 5 compaction simplification blocked by these issues

This proposal unifies the configuration surface for clarity and maintainability.

---

## Problem Statement

### Current Mapping (Inconsistent)

| Directive | CLI Option | Issue |
|-----------|------------|-------|
| `INFINITE-SESSIONS enabled` | `--no-infinite-sessions` | ✓ OK (flag inversion is clear) |
| `COMPACTION-MIN 30` | `--min-compaction-density 30` | ❌ Different naming |
| `COMPACTION-THRESHOLD 80` | `--compaction-threshold 80` | ✓ OK (matches) |
| *(none)* | `--buffer-threshold 95` | ❌ No directive equivalent |

### Detection Logic Issues

```python
# Current: Uses magic number comparison
if compaction_threshold != 80:  # CLI override
    bg_threshold = compaction_threshold / 100.0

# Problem: Can't distinguish "user set 80" from "default 80"
```

---

## Proposed Changes

### Phase 1: Add Missing Directive

Add `COMPACTION-MAX` directive for buffer exhaustion threshold:

```dockerfile
# New directive - buffer exhaustion threshold
COMPACTION-MAX 95
```

| Directive | SDK Parameter | Purpose |
|-----------|---------------|---------|
| `COMPACTION-MIN 30` | *(client-side)* | Skip compaction if below |
| `COMPACTION-THRESHOLD 80` | `background_compaction_threshold` | Start background compact |
| `COMPACTION-MAX 95` | `buffer_exhaustion_threshold` | Block until complete |

**Implementation:**
- Add `DirectiveType.COMPACTION_MAX` to parser
- Add `conv.compaction_max: Optional[float]` to `ConversationFile`
- Add handler in `applicator.py`
- Wire into `build_infinite_session_config()`

### Phase 2: Align CLI Naming

Rename CLI options to match directives:

| Current CLI | Proposed CLI | Directive |
|-------------|--------------|-----------|
| `--min-compaction-density` | `--compaction-min` | `COMPACTION-MIN` |
| `--compaction-threshold` | *(unchanged)* | `COMPACTION-THRESHOLD` |
| `--buffer-threshold` | `--compaction-max` | `COMPACTION-MAX` |

**Implementation:**
- Rename options in `iterate.py` and `cli.py`
- Add deprecated aliases for backward compatibility
- Update help text and documentation

### Phase 3: Fix Default Detection

Replace magic number comparison with explicit `None` defaults:

```python
# Before (fragile)
@click.option("--compaction-threshold", type=int, default=80)
...
if compaction_threshold != 80:  # Can't detect explicit 80

# After (explicit)
@click.option("--compaction-threshold", type=int, default=None)
...
if compaction_threshold is not None:  # Clear intent
    bg_threshold = compaction_threshold / 100.0
elif conv_compaction_threshold is not None:
    bg_threshold = conv_compaction_threshold
else:
    bg_threshold = 0.80  # True default
```

**Implementation:**
- Change CLI defaults to `None`
- Update `build_infinite_session_config()` with proper None checks
- Add defaults at final resolution stage

### Phase 4: Documentation

Update all references:
- `docs/DIRECTIVE-REFERENCE.md` - Add COMPACTION-MAX
- `docs/CONTEXT-MANAGEMENT.md` - Unified configuration table
- `docs/COMMANDS.md` - Updated CLI reference
- `README.md` - Quick reference table

---

## Unified Configuration Reference (Post-Implementation)

### Directives

```dockerfile
# Enable/disable SDK automatic compaction (default: enabled in iterate)
INFINITE-SESSIONS enabled|disabled

# Compaction thresholds (as percentages)
COMPACTION-MIN 30        # Skip if context below 30%
COMPACTION-THRESHOLD 80  # Start background compact at 80%
COMPACTION-MAX 95        # Block until complete at 95%
```

### CLI Options

```bash
# Disable automatic compaction
sdqctl iterate workflow.conv --no-infinite-sessions

# Custom thresholds (percentages)
sdqctl iterate workflow.conv \
    --compaction-min 25 \
    --compaction-threshold 75 \
    --compaction-max 90
```

### Priority Resolution

```
CLI option (if set) > Directive (if set) > Default
```

---

## Migration Guide

### Deprecated CLI Options

| Old | New | Deprecation |
|-----|-----|-------------|
| `--min-compaction-density N` | `--compaction-min N` | Warning in v1.x, removed in v2.0 |
| `--buffer-threshold N` | `--compaction-max N` | Warning in v1.x, removed in v2.0 |

### Workflow Updates

No changes required for existing `.conv` files - new directive is additive.

---

## Implementation Checklist

- [x] **Phase 1: Add COMPACTION-MAX directive**
  - [x] Add `DirectiveType.COMPACTION_MAX` 
  - [x] Add `conv.compaction_max` field
  - [x] Add applicator handler
  - [x] Add to `build_infinite_session_config()`
  - [x] Add tests

- [x] **Phase 2: Align CLI naming**
  - [x] Rename `--min-compaction-density` → `--compaction-min`
  - [x] Rename `--buffer-threshold` → `--compaction-max`
  - [x] Add deprecated aliases
  - [x] Update help text

- [x] **Phase 3: Fix default detection**
  - [x] Change CLI defaults to `None`
  - [x] Update `build_infinite_session_config()` logic
  - [x] Add tests for explicit vs default

- [x] **Phase 4: Documentation**
  - [x] Update DIRECTIVE-REFERENCE.md

---

## Future Work

- Consider `COMPACTION-STRATEGY` directive for compact/fresh/accumulate hints
- Investigate directive for SDK compaction event hooks
- Add `--explain-compaction` flag for debugging threshold decisions
