# Known Quirks and Surprising Behaviors

This document catalogs non-obvious behaviors discovered while developing and using sdqctl with the Copilot SDK. These are not bugs per se, but unexpected interactions that can confuse users.

> **Active quirks only.** Resolved quirks archived to [`archive/quirks/`](../archive/quirks/).  
> **Extracted learnings:** [`SDK-LEARNINGS.md`](SDK-LEARNINGS.md)

---

## Quick Reference

### Active Quirks

| ID | Quirk | Priority | Status |
|----|-------|----------|--------|
| *(No active quirks)* | | | |

### Resolved Quirks (Archived)

| ID | Quirk | Resolution | Archive |
|----|-------|------------|---------|
| Q-019A | Progress messages lack timestamps | Timestamps enabled when -v flag used | 2026-01-26 |
| Q-021 | `---` separator requires `--` prefix on CLI | Documented in iterate --help | 2026-01-26 |
| Q-017 | E501 line too long | All E501 fixed (core + tests) | 2026-01-25 |
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

## Q-021: `---` Separator Requires `--` Prefix on CLI

**Priority:** P2 - Ergonomics  
**Discovered:** 2026-01-26  
**Status:** ✅ RESOLVED - Documented in `iterate --help` (2026-01-26)

### Description

The `---` turn separator documented in `iterate --help` fails when used directly:

```bash
# Fails: Click interprets --- as an option
sdqctl iterate "Focus on X" --- workflow.conv
# Error: No such option: ---

# Works: Use -- to stop option parsing first
sdqctl iterate -n 2 -- "Focus on X" --- workflow.conv
```

### Root Cause

Click's argument parser sees `---` (starts with `-`) and attempts to parse it as an option before the arguments reach `parse_targets()`.

### Resolution

Help text now documents the `--` requirement before using `---` separators.

### Workarounds

1. **Use `--` before targets** (recommended):
   ```bash
   sdqctl iterate -n 2 -- "prompt" --- workflow.conv
   ```

2. **Put all options first, then targets without `---`**:
   ```bash
   sdqctl iterate -n 2 "prompt" workflow.conv  # elides by default
   ```

3. **Use `--prologue` instead of inline**:
   ```bash
   sdqctl iterate -n 2 --prologue "Focus on X" workflow.conv
   ```

---

## Q-019A: Progress Messages Lack Timestamps

**Priority:** P3 - Cosmetic  
**Discovered:** 2026-01-25  
**Status:** ✅ RESOLVED (2026-01-26)

### Description

Progress messages appear interleaved with logger output but lack timestamps:

```
15:28:04 [INFO] sdqctl.adapters.copilot: Compaction started
 🗜️ Compacting...                    <-- No timestamp
15:28:04 [DEBUG] sdqctl.adapters.copilot: Context: 104,300/128,000 tokens
```

### Resolution

Added `set_timestamps()` function to `core/progress.py`. Timestamps are automatically
enabled when `-v` (verbose) flag is used, aligning progress output with logger format.

```
15:28:04 [INFO] sdqctl.adapters.copilot: Compaction started
15:28:04  🗜️ Compacting...             <-- Now has timestamp
15:28:04 [DEBUG] sdqctl.adapters.copilot: Context: 104,300/128,000 tokens
```

---

## Q-017: Linting Issues Backlog

**Priority:** P3 - Low (Cosmetic)  
**Discovered:** 2026-01-25  
**Status:** ✅ RESOLVED - All E501 fixed

### Description

Comprehensive ruff linting revealed issues across the codebase. Auto-fix applied 2026-01-25.

### Progress

| Before | After | Fixed |
|--------|-------|-------|
| 1,994 issues | 0 E501 | 1,994 (100%) |

### Remaining Issues

| Category | Count | Notes |
|----------|-------|-------|
| E501 (line too long >100) | 0 | ✅ All fixed (2026-01-25) |
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
