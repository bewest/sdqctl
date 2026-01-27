# ADR-004: SDK Session Persistence

**Status**: Accepted  
**Date**: 2026-01-25  
**Deciders**: sdqctl team

## Context

Copilot SDK v2 supports persistent sessions. Users want to:
1. List existing sessions
2. Resume previous conversations
3. Clean up old sessions
4. Name sessions in workflow files for resumability

The question was where to implement this functionality.

## Decision

**Implement session persistence via adapter methods and CLI commands.**

Adapter methods:
- `list_sessions()` - List available sessions
- `resume_session(session_id, config)` - Resume a session
- `delete_session(session_id)` - Delete a session

CLI commands:
- `sdqctl sessions list` - List sessions
- `sdqctl sessions delete <id>` - Delete session
- `sdqctl sessions cleanup` - Remove old sessions
- `sdqctl sessions resume <id>` - Resume session

Directive:
- `SESSION-NAME <name>` - Named sessions in workflow files

## Consequences

### Positive

- Full session management from CLI
- Named sessions enable reproducible workflows
- Cleanup command prevents storage bloat

### Negative

- Session storage is adapter-specific (not portable)
- Resume requires matching adapter

### Neutral

- CLI flags override directive values

## References

- [SDK-SESSION-PERSISTENCE.md](../../proposals/SDK-SESSION-PERSISTENCE.md) - Full proposal
