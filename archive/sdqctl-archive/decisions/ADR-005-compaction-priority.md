# ADR-005: Compaction Priority

**Status**: Accepted  
**Date**: 2026-01-25  
**Deciders**: sdqctl team

## Context

Context compaction can be controlled at multiple levels:
1. CLI flags: `--compact`, `--compaction-min`
2. Workflow directives: `COMPACT`, `COMPACTION-MIN`, `COMPACTION-THRESHOLD`
3. System defaults

The question was which level takes precedence when multiple are specified.

## Decision

**Layered priority: CLI flags > Directives > Defaults.**

Priority order (highest to lowest):
1. **CLI flags** - Explicit user intent at runtime
2. **Workflow directives** - Author's workflow design
3. **Defaults** - System configuration

This follows the principle that more specific/explicit settings override more general ones.

## Consequences

### Positive

- Users can override workflow settings without modifying files
- Workflow authors can set sensible defaults
- Predictable precedence rules

### Negative

- Must document priority clearly to avoid confusion
- Three places to check when debugging compaction issues

### Neutral

- Same pattern used for other layered settings (adapters, verbosity)

## References

- [SDK-INFINITE-SESSIONS.md](../../proposals/SDK-INFINITE-SESSIONS.md) - Full proposal
- [CONTEXT-MANAGEMENT.md](../../docs/CONTEXT-MANAGEMENT.md) - Documentation
