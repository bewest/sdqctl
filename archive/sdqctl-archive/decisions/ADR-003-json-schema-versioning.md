# ADR-003: JSON Schema Versioning

**Status**: Accepted  
**Date**: 2026-01-23  
**Deciders**: sdqctl team

## Context

The `--json` output flag produces structured data that can be piped to external tools. As the schema evolves, consumers need to know which version they're receiving.

Options considered:
1. No versioning (assume latest)
2. URL-based schema identifier
3. Simple `schema_version` field

## Decision

**Add explicit `schema_version` field to JSON output.**

```json
{
  "schema_version": "1.0",
  "workflow": "...",
  ...
}
```

Versioning policy: `major.minor` where major = breaking changes.

## Consequences

### Positive

- External tools can detect and handle schema changes
- Breaking changes are clearly signaled
- Backward compatibility checking is possible

### Negative

- Must maintain version number discipline
- Consumers must implement version checking

### Neutral

- `--from-json` flag validates schema version on input

## References

- [PIPELINE-ARCHITECTURE.md](../../proposals/PIPELINE-ARCHITECTURE.md) - Full proposal
- Commit `90242c5` - `--from-json` implementation
