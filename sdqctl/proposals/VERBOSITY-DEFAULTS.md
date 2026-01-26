# Proposal: Default Verbosity Key Actions

> **Status**: Draft  
> **Priority**: P3  
> **Blocks**: OQ-004  
> **Created**: 2026-01-26

---

## Problem Statement

At default verbosity (`-v 0`), sdqctl produces almost no output during workflow execution. Users may not realize:
- That anything is happening
- How far along a multi-phase workflow has progressed
- Whether the system is waiting, processing, or stuck

This creates a poor first-run experience and makes it harder to observe long-running workflows without opting into verbose logging.

---

## Current Behavior

From `sdqctl/core/logging.py`:

| Verbosity | Flag | Level | What's Visible |
|-----------|------|-------|----------------|
| 0 | (default) | WARNING | Errors and warnings only |
| 1 | `-v` | INFO | Turns, tools, tokens, intents |
| 2 | `-vv` | DEBUG | Reasoning, args, context usage |
| 3+ | `-vvv` | TRACE | Deltas, raw events, partial results |

**At level 0**, the only output is:
- Error messages
- Warning messages (rare)
- Final result/exit code

**User experience**: Run a 9-phase workflow and see... nothing until it finishes or fails.

---

## Proposed Behavior

Add a new category of output: **milestone messages** that appear at default verbosity.

These are distinct from logging and represent user-facing progress:
- Cycle start/end
- Phase transitions
- Completion summary

---

## Alternatives

### Option A: Minimal Milestones (Recommended)

Print cycle and phase boundaries only:

```
[Cycle 1/5] Starting...
  Phase 1: Work Selection ✓
  Phase 2: Execute ✓
  Phase 3: Verify ✓
  ...
[Cycle 1/5] Complete (45.2s)
```

**Pros**: Low noise, shows progress, no secrets/content exposed  
**Cons**: Requires changes to iterate.py and run.py

**Implementation**: Use `progress()` function (already exists in `core/progress.py`) with a `milestone=True` flag.

### Option B: Tool Call Summaries

Print tool calls at default verbosity:

```
🔧 view: /path/to/file.py
🔧 edit: 3 changes
🔧 bash: pytest (2.3s)
```

**Pros**: Shows what the agent is doing  
**Cons**: More verbose, may expose paths, harder to summarize

### Option C: INFO at WARNING Level

Route all INFO messages to WARNING level (effectively making `-v` the default).

**Pros**: No code changes to message sites  
**Cons**: Too verbose for default, breaks expectations, harder to filter

### Option D: No Change (Keep Quiet Default)

Keep current behavior. Users who want output use `-v`.

**Pros**: Unix philosophy (quiet by default), no changes needed  
**Cons**: Poor discoverability, bad first-run experience

---

## Trade-offs

| Consideration | A: Milestones | B: Tools | C: INFO→WARN | D: No Change |
|---------------|---------------|----------|--------------|--------------|
| First-run UX | ✅ Good | ⚠️ Verbose | ❌ Too much | ❌ Silent |
| CI/automation | ✅ Clean | ⚠️ Noisy | ❌ Log bloat | ✅ Clean |
| Implementation | Medium | Medium | Low | None |
| Unix philosophy | ✅ Aligned | ⚠️ Moderate | ❌ Violated | ✅ Aligned |

---

## Recommendation

**Option A: Minimal Milestones**

This provides:
1. Visible progress for interactive use
2. Minimal noise for CI/automation
3. Clear semantic distinction from logging

### Implementation Sketch

```python
# core/progress.py - add milestone support
def milestone(message: str, verbosity: int = 0) -> None:
    """Print a milestone message (visible at default verbosity)."""
    if get_verbosity() >= verbosity:
        console.print(f"[dim]{message}[/dim]")

# commands/iterate.py - use milestones
milestone(f"[Cycle {cycle}/{total}] Starting...")
# ... execute phases ...
milestone(f"[Cycle {cycle}/{total}] Complete ({elapsed:.1f}s)")
```

---

## Decision Needed

- [ ] Approve Option A (Minimal Milestones)
- [ ] Approve Option B (Tool Summaries)
- [ ] Approve Option D (No Change)
- [ ] Request more information
- [ ] Other direction: ________________

---

## References

- `sdqctl/core/logging.py` - Current verbosity implementation
- `sdqctl/core/progress.py` - Progress output utilities
- `docs/OPEN-QUESTIONS.md` - OQ-004 entry
- `proposals/BACKLOG.md` - Blocked P3 item
