# ADR-001: ON-FAILURE Strategy

**Status**: Accepted  
**Date**: 2026-01-23  
**Deciders**: sdqctl team

## Context

When a RUN command fails, the workflow needs a way to handle the error. Two approaches were considered:

1. **RUN-RETRY only**: Simple retry with optional AI fix attempt
2. **ON-FAILURE blocks**: Full branching with arbitrary fallback logic

The question was whether to implement one or both, and in what order.

## Decision

**Implement both RUN-RETRY and ON-FAILURE/ON-SUCCESS blocks.**

Implementation order:
1. **Phase 1**: `RUN-RETRY N "prompt"` — simple retry with AI fix attempt
2. **Phase 2**: `ON-FAILURE`/`ON-SUCCESS` blocks — full branching for complex cases

## Consequences

### Positive

- RUN-RETRY covers ~80% of use cases with minimal complexity
- ON-FAILURE blocks provide full flexibility for complex error handling
- Phased implementation reduced initial development burden

### Negative

- Two mechanisms to document and maintain
- Users must choose which approach to use

### Neutral

- Both mechanisms are now implemented and tested

## References

- [RUN-BRANCHING.md](../../proposals/RUN-BRANCHING.md) - Full proposal
- Commit `3f75074` - RUN-RETRY implementation
