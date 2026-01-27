# ADR-002: VERIFY Execution Model

**Status**: Accepted  
**Date**: 2026-01-23  
**Deciders**: sdqctl team

## Context

VERIFY directives check conditions during workflow execution. Two execution models were considered:

1. **Blocking (synchronous)**: Each VERIFY completes before the next directive
2. **Non-blocking (async)**: VERIFY runs in background, results collected later

The question was how to handle VERIFY results in subsequent prompts.

## Decision

**Blocking (synchronous) execution.**

Each VERIFY completes before the next directive. Results are guaranteed available for subsequent PROMPTs.

## Consequences

### Positive

- Simple mental model for workflow authors
- No race conditions between VERIFY and dependent directives
- VERIFY results immediately usable in PROMPT context

### Negative

- Serial execution may be slower for independent verifications
- Cannot parallelize multiple VERIFY operations

### Neutral

- Workflow authors can manually parallelize by running separate workflows

## References

- [VERIFICATION-DIRECTIVES.md](../../proposals/VERIFICATION-DIRECTIVES.md) - Full proposal
