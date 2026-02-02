# CLI Backlog

> **Domain**: Commands, flags, help system, user experience  
> **Parent**: [BACKLOG.md](../BACKLOG.md)  
> **Last Updated**: 2026-02-02

---

## Active Items

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| CLI-001 | Render command should show processed steps (ELIDE merging, RUN placeholders) | P3 | Medium | See Q-RENDER-001 below |

### Q-RENDER-001: Render doesn't reflect ELIDE processing

**Problem**: `sdqctl render --json` uses `conv.prompts` (legacy flat list) instead of `conv.steps`. This means:
- RUN steps are invisible in render output
- ELIDE merging effects not shown
- Actual turn count not reflected (shows 2 prompts when execution produces 1 turn)

**Options**:
- A: Quick fix - call `process_elided_steps()` in renderer, show merged prompts with `[RUN: cmd]` placeholders
- B: Add `--show-steps` flag for full step structure in JSON
- C: Both - default shows processed turns, `--raw-steps` shows unprocessed

**Files**: `sdqctl/core/renderer.py` lines 190-205 use `conv.prompts`

**Related**: Fixed ELIDE processing in `iterate.py` (commit 96317a5)

---

## Completed

*Migrated from main BACKLOG.md - see WP-001 step 3*

---

## References

- [docs/COMMANDS.md](../../docs/COMMANDS.md) - Command reference
- [docs/CLI-ERGONOMICS.md](../CLI-ERGONOMICS.md) - UX proposal
