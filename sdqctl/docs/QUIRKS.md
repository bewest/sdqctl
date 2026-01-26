# Known Quirks and Surprising Behaviors

This document catalogs non-obvious behaviors discovered while developing and using sdqctl with the Copilot SDK. These are not bugs per se, but unexpected interactions that can confuse users.

> **Active quirks only.** Resolved quirks archived to [`archive/quirks/`](../archive/quirks/).  
> **Extracted learnings:** [`SDK-LEARNINGS.md`](SDK-LEARNINGS.md)

---

## Quick Reference

### Active Quirks

| ID | Quirk | Priority | Status |
|----|-------|----------|--------|
| Q-019A | Progress messages lack timestamps after compaction | P3 | 🟡 Open |
| Q-017 | 197 remaining linting issues (line length, unused vars) | P3 | 🟡 Backlog |

### Resolved Quirks (Archived)

| ID | Quirk | Resolution | Archive |
|----|-------|------------|---------|
| Q-020 | Context percentage shows 0% until compaction | Sync tokens after each send() | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-020-context-percentage-shows-0-until-compaction) |
| Q-019B | Context percentage diverges after compaction | Sync tokens from SDK | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-019b-context-percentage-diverges-after-compaction) |
| Q-018 | Session ID mismatch between checkpoint and SDK | Store SDK session UUID | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-018-session-id-mismatch-between-checkpoint-and-sdk) |
| Q-016 | 5 undefined name bugs (F821) | Variables corrected | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-016-undefined-name-bugs-f821) |
| Q-014 | Event handler multiplexing in accumulate mode | Register handler once | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-014-event-handler-multiplexing-in-accumulate-mode) |
| Q-015 | Duplicate tool calls at session termination | Fixed by Q-014 | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-015-duplicate-tool-calls-at-session-termination) |
| Q-013 | Tool name shows "unknown" in completion logs | Fixed by Q-014 | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-013-tool-name-shows-unknown-in-completion-logs) |
| Q-011 | Compaction threshold options not fully wired | Respects threshold | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-011-compaction-threshold-options-not-fully-wired) |
| Q-010 | COMPACT directive ignored by iterate command | Iterate conv.steps | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-010-compact-directive-ignored-by-cycle-command) |
| Q-005 | Tool names show "unknown" in verbose logs | Added `_get_tool_name()` | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-005-tool-names-show-unknown-in-verbose-logs) |
| Q-004 | Verbose logging shows duplicate content | Removed delta logging | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-004-verbose-logging-shows-duplicate-content) |
| Q-003 | Template variables encourage problematic patterns | Q-001 fix + examples | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-003-template-variables-encourage-problematic-patterns) |
| Q-002 | SDK abort events not emitted | Lowered thresholds + stop file | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-002-sdk-abort-events-not-emitted) |
| Q-001 | Workflow filename influences agent behavior | Excluded from prompts | [2026-01](../archive/quirks/2026-01-resolved-quirks.md#q-001-workflow-filename-influences-agent-behavior) |

---

## Q-019A: Progress Messages Lack Timestamps

**Priority:** P3 - Cosmetic  
**Discovered:** 2026-01-25  
**Status:** 🟡 Open

### Description

Progress messages appear interleaved with logger output but lack timestamps:

```
15:28:04 [INFO] sdqctl.adapters.copilot: Compaction started
 🗜️ Compacting...                    <-- No timestamp
15:28:04 [DEBUG] sdqctl.adapters.copilot: Context: 104,300/128,000 tokens
```

### Root Cause

Multiple files emit progress via stdout (no timestamps) while also logging:
- `copilot.py:607` - `progress("  🗜️  Compacting...")`
- `run.py:187` - `progress_fn("    🗜  Compacting...")`
- `cycle.py:442` - `progress_print("    Compacting...")`

### Fix Options

1. Route all compaction progress through logger
2. Suppress logger when progress is active
3. Add timestamps to progress output

---

## Q-017: Linting Issues Backlog

**Priority:** P3 - Low (Cosmetic)  
**Discovered:** 2026-01-25  
**Status:** 🟢 Ongoing reduction - 148 remaining

### Description

Comprehensive ruff linting revealed issues across the codebase. Auto-fix applied 2026-01-25.

### Progress

| Before | After | Fixed |
|--------|-------|-------|
| 1,994 issues | 148 issues | 1,846 (93%) |

### Remaining Issues

| Category | Count | Notes |
|----------|-------|-------|
| E501 (line too long >100) | 148 | Manual refactoring in progress |
| F841 (unused variables) | 0 | ✅ All fixed |

---

## Template Variables Reference

Variables and their semantic impact when visible to the agent:

| Variable | Semantic Impact | Notes |
|----------|-----------------|-------|
| `{{WORKFLOW_NAME}}` | **SAFE** | Excluded from prompts by default (Q-001 fix) |
| `{{WORKFLOW_PATH}}` | **SAFE** | Excluded from prompts by default (Q-001 fix) |
| `{{__WORKFLOW_NAME__}}` | **HIGH** | Explicit opt-in - use with caution |
| `{{__WORKFLOW_PATH__}}` | **MEDIUM** | Explicit opt-in - use with caution |
| `{{DATE}}`, `{{DATETIME}}` | NONE | Safe to use anywhere |
| `{{GIT_COMMIT}}`, `{{GIT_BRANCH}}` | LOW | Safe to use anywhere |

**Key principle:** Variables with `__` prefix are explicit opt-in and may influence agent behavior.

---

## Contributing

When you discover a new quirk:

1. Add an entry following the template:
   - **ID**: Q-XXX (sequential)
   - **Priority**: P0 (high) / P1 (medium) / P2 (low) / P3 (cosmetic)
   - **Description**: What happens
   - **Impact**: Why it matters
   - **Workaround**: How to avoid it
   - **Root cause** (if known)

2. Add to the Quick Reference table at the top

3. Cross-reference from related documentation

---

## See Also

- [SDK-LEARNINGS.md](SDK-LEARNINGS.md) - Extracted patterns from resolved quirks
- [archive/quirks/](../archive/quirks/) - Full investigation context for resolved quirks
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [LOOP-STRESS-TEST.md](LOOP-STRESS-TEST.md) - Loop detection testing methodology
