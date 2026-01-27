# Archive

This directory contains historical material that has been archived from active documentation.

## Purpose

- **Reduce backlog size** - Keep BACKLOG.md focused on active work
- **Preserve history** - Completed work and decisions remain accessible
- **Document decisions** - Design choices are recorded for future reference

## Structure

```
archive/
├── README.md           # This file
├── DECISIONS.md        # Summary of all design decisions
├── SESSIONS/           # Completed session logs by date
│   ├── 2026-01-23.md
│   ├── 2026-01-24.md
│   └── ...
└── decisions/          # Architecture Decision Records (ADRs)
    ├── ADR-template.md
    ├── ADR-001-*.md
    └── ...
```

## What Gets Archived

| Item Type | Criteria | Destination |
|-----------|----------|-------------|
| Session logs | Work completed, not active | `SESSIONS/YYYY-MM-DD.md` |
| Design decisions | Resolved, implemented | `DECISIONS.md` + ADR if major |
| Rejected proposals | Status = Rejected | `proposals/` (future) |

## What Stays in BACKLOG.md

- Active work items and priorities
- Open design questions
- Current roadmap and gap analysis
- References to archived material (links)

## Archival Process

### When to Archive

1. **Session logs**: After all items in a session are complete and verified
2. **Design decisions**: When implemented and no longer under discussion
3. **Proposals**: When fully implemented or explicitly rejected

### How to Archive

1. **Session logs**:
   - Cut the session section from BACKLOG.md
   - Paste into `SESSIONS/YYYY-MM-DD.md` (create or append)
   - Add one-line summary with link in BACKLOG.md's Completed section

2. **Design decisions**:
   - Add summary row to `DECISIONS.md` table
   - For major decisions, create `decisions/ADR-NNN-title.md`
   - Remove detailed discussion from BACKLOG.md

3. **Keep links working**:
   - Update any internal references to point to archive location
   - Use relative paths: `../archive/SESSIONS/2026-01-24.md`

## ADR Format

Architecture Decision Records follow this format:

```markdown
# ADR-NNN: Title

**Status**: Accepted | Superseded | Deprecated  
**Date**: YYYY-MM-DD  
**Deciders**: Who made the decision

## Context

What prompted the decision? What problem were we solving?

## Decision

What we decided to do.

## Consequences

- What this means going forward
- Trade-offs accepted
- What we gave up
```

## References

- [BACKLOG.md](../proposals/BACKLOG.md) - Active work items
- [DECISIONS.md](DECISIONS.md) - All design decisions summary
