# Known Quirks and Surprising Behaviors

This document catalogs non-obvious behaviors discovered while developing and using sdqctl with the Copilot SDK. These are not bugs per se, but unexpected interactions that can confuse users.

---

## Quick Reference

### Active Quirks

| ID | Quirk | Priority | Status |
|----|-------|----------|--------|
| Q-013 | Tool name shows "unknown" in completion logs | P2 | 🔶 Open |

### Resolved Quirks

| ID | Quirk | Status | Resolution |
|----|-------|--------|------------|
| Q-001 | Workflow filename influences agent behavior | ✅ FIXED | `WORKFLOW_NAME` excluded from prompts by default |
| Q-002 | SDK abort events not emitted | ✅ IMPROVED | Lowered detection thresholds + stop file mechanism |
| Q-003 | Template variables encourage problematic patterns | ✅ RESOLVED | Q-001 fix + examples updated |
| Q-004 | Verbose logging shows duplicate content | ✅ IMPROVED | Delta logging removed |
| Q-005 | Tool names show "unknown" in verbose logs | ✅ FIXED | Added `_get_tool_name()` helper |
| Q-010 | COMPACT directive ignored by cycle command | ✅ FIXED | Refactored to iterate `conv.steps` |
| Q-011 | Compaction threshold options not fully wired | ✅ FIXED | `--min-compaction-density` now wired to `needs_compaction()` |
| Q-012 | COMPACT directive triggers unconditionally | ✅ FIXED | Now respects `--min-compaction-density` threshold | |

---

## Q-011: Compaction Threshold Options Not Fully Wired

**Priority:** P1 - Medium Impact  
**Discovered:** 2026-01-23  
**Status:** ✅ FIXED (2026-01-24)

### Resolution

The `--min-compaction-density` option is now wired into the compaction logic:

```python
# session.py - Updated needs_compaction()
def needs_compaction(self, min_density: float = 0) -> bool:
    """Check if context window is near limit and above minimum density."""
    if min_density > 0:
        min_threshold = min_density / 100 if min_density > 1 else min_density
        if self.context.window.usage_percent < min_threshold:
            return False  # Skip compaction - below minimum density
    return self.context.window.is_near_limit

# cycle.py - Now passes min_compaction_density
if session.needs_compaction(min_compaction_density):
    # compact
```

**What was fixed:**
- `--min-compaction-density` now controls whether automatic compaction is skipped
- Setting `--min-compaction-density 50` skips compaction if context < 50% full

**What remains as-designed:**
- Automatic compaction only at cycle boundaries (not per-turn)
- `COMPACT` directive is unconditional (see Q-012)
- Single threshold model (no two-tier operating/max thresholds)

### Original Description (Historical)

Several compaction threshold options were **declared but not functionally implemented**:

| Option | CLI Location | Implementation Status |
|--------|--------------|----------------------|
| `--min-compaction-density` | run.py:289, cycle.py:73 | ✅ **NOW WIRED** - skips compaction if below threshold |
| `CONTEXT-LIMIT N%` | conversation.py:673 | ✅ Sets threshold, checked at cycle boundaries |
| Automatic compaction | cycle.py:638-650 | ⚠️ **Partial** - only at cycle boundaries, not per-turn |

---

## Q-012: COMPACT Directive Triggers Unconditionally

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-23  
**Status:** ✅ FIXED (2026-01-24)

### Resolution

The `COMPACT` directive now respects the `--min-compaction-density` threshold:

```python
# run.py and cycle.py - Updated COMPACT handling
elif step_type == "compact":
    if session.needs_compaction(min_compaction_density):
        logger.info("🗜  COMPACTING conversation...")
        # ... execute compaction
    else:
        logger.info("📊 Skipping COMPACT - context below threshold")
```

**What was fixed:**
- `COMPACT` directive now checks `session.needs_compaction(min_compaction_density)` before executing
- Skips compaction when context is below the minimum density threshold
- Shows "Skipping COMPACT - context below threshold" message when skipped

**Behavior:**
- `--min-compaction-density 0` (default): COMPACT executes based on `needs_compaction()` logic
- `--min-compaction-density 50`: COMPACT skips if context < 50% full
- Consistent with automatic compaction at cycle boundaries

### Original Description (Historical)

The `COMPACT` directive in workflow files **always triggered compaction**, regardless of:
- Current context utilization
- `--min-compaction-density` setting
- Whether compaction would provide any benefit

---

## Q-010: COMPACT Directive Ignored by Cycle Command

**Priority:** P1 - Medium Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED

### Description

The `COMPACT` directive was parsed correctly and added to `conv.steps`, but the `cycle` command only iterated through `conv.prompts`, effectively ignoring COMPACT, CHECKPOINT, and other step-based directives.

### Root Cause

```python
# cycle.py (before fix) - only processed prompts
for prompt_idx, prompt in enumerate(conv.prompts):
    # ... prompt handling only

# run.py - correctly processed all steps  
for step in steps_to_process:
    if step_type == "prompt": ...
    elif step_type == "compact": ...  # ← cycle.py was missing this
```

### Fix Applied (2026-01-22)

Refactored `cycle.py` to iterate `conv.steps` instead of just `conv.prompts`:

1. Added step-based iteration matching `run.py` pattern
2. Handle `prompt`, `compact`, and `checkpoint` step types
3. Added backward compatibility fallback for legacy files without steps

**Files modified:** `sdqctl/commands/cycle.py`

### Verification

```bash
# COMPACT directives now execute during cycle
sdqctl cycle examples/workflows/fix-quirks.conv --adapter copilot
# 🗜  Compacting conversation... (now appears after phase 2)
```

---

## Q-013: Tool Name Shows "unknown" in Completion Logs

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-25  
**Status:** 🔶 Open

### Description

Despite Q-005 being marked fixed, tool completion logs still show "unknown" in many cases. A 88-minute session revealed **1,695 entries** with `✓ unknown` instead of the actual tool name:

```
15:43:02 [INFO] sdqctl.adapters.copilot: [backlog-processor:10/10:P4/4]   ✓ unknown (0.3s) → 906 chars
15:43:10 [INFO] sdqctl.adapters.copilot: [backlog-processor:10/10:P4/4]   ✓ unknown (0.3s) → 109 chars
```

The tools execute correctly (output sizes and timing are captured), but the name is not being extracted from `tool.execution_complete` events.

### Difference from Q-005

Q-005 addressed `tool.execution_start` events where `tool_requests` contained the tool info. Q-013 affects `tool.execution_complete` events which use a different structure:

- **Start events**: Tool info in `data.tool_requests[0].name` → Q-005 fixed
- **Complete events**: Should match via `tool_call_id` → Not working

### Root Cause Analysis

```python
elif event_type == "tool.execution_complete":
    tool_call_id = _get_field(data, "tool_call_id", None)
    
    if tool_call_id in stats.active_tools:
        tool_info = stats.active_tools.pop(tool_call_id)
        # Uses tool_info["name"] - works if matched
    else:
        # Falls through to "unknown" - this is happening 1,695 times
```

**Possible causes:**
1. `tool_call_id` in start differs from complete (SDK field naming)
2. Event ordering (complete before start in some cases)
3. Multiple start events for batch calls, single complete
4. Race condition in event processing

### Recommended Fix

Add debug logging to capture when matching fails:

```python
if tool_call_id not in stats.active_tools:
    logger.debug(f"Tool complete without matching start: id={tool_call_id}, "
                 f"active_ids={list(stats.active_tools.keys())}")
```

Then analyze logs to determine the mismatch pattern.

### Workaround

The current behavior is cosmetic — tools execute correctly. For now, `unknown` in logs doesn't indicate a functional problem.

---

## Q-005: Tool Names Show "unknown" in Verbose Logs

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED

### Description

When using `-vvv` verbose mode, tool execution events sometimes showed "unknown" as the tool name instead of the actual tool being executed.

### Root Cause

The Copilot SDK Data object can provide tool information in multiple locations:
- `data.tool_name` - Direct field (most common)
- `data.name` - Generic name field  
- `data.tool_requests` - Nested list of ToolRequest objects (for batch tool calls)

The original `_get_field()` helper only checked top-level fields. When the SDK returned tool info nested in `tool_requests`, the extraction failed and fell back to "unknown".

### Fix Applied (2026-01-22)

Added dedicated `_get_tool_name()` helper function that:
1. First tries direct fields: `tool_name`, `name`, `tool`
2. Falls back to checking `tool_requests[0].name` for nested tool info
3. Returns "unknown" only if all extraction attempts fail

**Files modified:** `sdqctl/adapters/copilot.py`

```python
def _get_tool_name(data: Any) -> str:
    """Extract tool name from event data, handling nested structures."""
    # Try direct fields first
    name = _get_field(data, "tool_name", "name", "tool")
    if name:
        return name
    
    # Check for tool_requests list (contains ToolRequest objects)
    tool_requests = _get_field(data, "tool_requests")
    if tool_requests and isinstance(tool_requests, list) and len(tool_requests) > 0:
        first_request = tool_requests[0]
        name = _get_field(first_request, "name", "tool_name")
        if name:
            return name
    
    return "unknown"
```

### Verification

Tool events now show actual tool names at all verbosity levels:
```bash
sdqctl -vvv run "Check files"
# 🔧 Tool: view  (not "🔧 Tool: unknown")
#   ✓ view (1.2s)
```

---

## Q-004: Verbose Logging Shows Duplicate Content

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ IMPROVED - Delta logging removed

### Description

When using `-vvvv` (maximum verbosity), delta messages often contain duplicate material, making logs hard to read. Additionally, reasoning and actions taken are only visible at high verbosity levels, not at the default level.

### Fix Applied (2026-01-22)

**Removed reasoning delta logging** to eliminate duplicate content:
- `assistant.reasoning_delta` events no longer logged (full reasoning logged via `assistant.reasoning`)
- Reduces noise at TRACE level significantly

**Logging levels remain:**
- WARNING (default): errors/warnings only
- INFO (-v): turns, tools, tokens, intents ← **use this for normal operation**
- DEBUG (-vv): reasoning, args, context usage
- TRACE (-vvv+): raw events

**Recommendation:** Use `-v` for useful operational output without noise.

### Remaining Consideration

Showing key actions at default level (no flags) could be considered, but would require careful selection of what's "key" vs noise. Current approach: `-v` is the recommended default for interactive use.

---


## Q-001: Workflow Filename Influences Agent Behavior

**Priority:** P0 - High Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ FIXED - `WORKFLOW_NAME` excluded from prompts by default

### Description

The `{{WORKFLOW_NAME}}` template variable extracts the filename stem (e.g., `implement-improvements` from `implement-improvements.conv`). When this variable is used in prompts, headers, or prologues, **the agent uses the filename words as semantic signals** about its intended role.

### Example

A workflow file named `implement-improvements.conv` with this header:

```dockerfile
HEADER # sdqctl Progress Report
HEADER ## Session: {{DATETIME}}
```

Even without explicitly using `{{WORKFLOW_NAME}}`, the workflow's semantic intent can be inferred by the agent from:
1. The file path visible in the session context
2. Comments in the workflow file referencing the filename
3. Related files in the same directory

When the filename contains words like "tracker", "doc", or "report", the agent may interpret its role as **documentation/tracking** rather than **implementation**, causing it to:
- Resist making code edits
- Focus on generating reports instead of modifying files
- Provide descriptions of changes instead of making them

### Impact

- Agent refuses to edit files even when explicitly instructed
- Prompts like "implement the fix now" are interpreted as "describe the fix"
- Significant debugging time spent identifying the cause

### Workarounds

**1. Choose implementation-oriented filenames:**
```bash
# Instead of:
progress-tracker.conv      # "tracker" suggests passive tracking
documentation-report.conv  # "report" suggests analysis, not editing

# Use:
implement-improvements.conv  # "implement" signals active editing
edit-and-sync.conv           # "edit" signals file modification
```

**2. Add explicit role clarification in PROLOGUE:**
```dockerfile
PROLOGUE You are an implementation assistant. Your job is to EDIT FILES directly.
PROLOGUE Do not just describe changes - make them using the edit tools.
PROLOGUE When asked to implement something, use the edit tool to modify source files.
```

**3. Avoid using `{{WORKFLOW_NAME}}` in prompts if the filename doesn't match intent:**
```dockerfile
# Instead of:
HEADER ## Workflow: {{WORKFLOW_NAME}}

# Use a descriptive literal:
HEADER ## Implementation Session
```

**4. Override with explicit MODE directive (aspirational):**
```dockerfile
MODE implement  # Signals implementation intent to the agent
```

### Root Cause Analysis

Template variables are injected into these locations (from `conversation.py`):
- Prompts
- Prologues and epilogues
- Headers and footers
- Output file paths
- Step content

The injection only occurs when `{{VAR}}` syntax is explicitly used. However, the agent also has access to:
- The workflow file path (visible in session context)
- Comments within the workflow file
- Directory structure

All of these provide semantic context that influences agent behavior.

### Fix Applied (2026-01-22)

The `WORKFLOW_NAME` and `WORKFLOW_PATH` variables are now **excluded from prompts by default** to prevent agent behavior being influenced by workflow filenames.

**What changed:**
- `get_standard_variables()` no longer includes `WORKFLOW_NAME`/`WORKFLOW_PATH` by default
- Output paths (OUTPUT-FILE, OUTPUT-DIR) still have access via `include_workflow_vars=True`
- Explicit opt-in variables `{{__WORKFLOW_NAME__}}` and `{{__WORKFLOW_PATH__}}` are always available

**Migration:**
- If you need the workflow name in prompts, use `{{__WORKFLOW_NAME__}}` (underscore prefix = explicit opt-in)
- Output paths like `OUTPUT-FILE reports/{{WORKFLOW_NAME}}-{{DATE}}.md` continue to work unchanged
- No changes needed for typical workflows

**Example:**
```dockerfile
# For agent-visible content - use explicit opt-in:
HEADER # Implementation Session for {{__WORKFLOW_NAME__}}

# For output paths - WORKFLOW_NAME still works:
OUTPUT-FILE reports/{{WORKFLOW_NAME}}-{{DATE}}.md
```

### Prior Workarounds (still valid)

1. **Choose implementation-oriented filenames**
2. **Add explicit role clarification in PROLOGUE**
3. **Avoid using `{{WORKFLOW_NAME}}` in prompts**

---

## Q-002: SDK Abort Events Not Emitted

**Priority:** P1 - Medium Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ IMPROVED - Lowered thresholds + stop file detection

### Description

The Copilot SDK documents an `ABORT = "abort"` event type, and our adapter handles it:

```python
elif event_type == "abort":
    reason = getattr(data, "reason", None)
    logger.warning(f"🛑 Agent abort signal: {reason}")
    stats.abort_reason = reason
    done.set()
```

**However, stress testing revealed this event is never emitted by the SDK**, even when:
- The agent's reasoning indicates it's stuck in a loop
- Responses become minimal/repetitive
- Token limits are approached

### Evidence

From `docs/LOOP-STRESS-TEST.md`:

| Test Scenario | Cycles | SDK Abort Event? | How Loop Was Detected |
|---------------|--------|------------------|----------------------|
| Loop elicit prompt | 1 | ❌ No | AI reasoning contained "in a loop" |
| Repeated identical prompt | 15 | ❌ No | Minimal response length (31 chars) |
| Minimal response prompt | 2 | ❌ No | Response < 50 chars threshold |

### Impact

- Cannot rely on structured SDK signal for loop detection
- Must parse response content heuristically
- May miss internal SDK signals we can't observe

### Workaround

The `LoopDetector` class provides client-side detection:

```python
from sdqctl.core.loop_detector import LoopDetector, LoopReason

detector = LoopDetector(
    identical_threshold=3,      # N identical responses
    min_response_length=50,     # Chars below = suspicious
    reasoning_patterns=[r'\bin a loop\b', r'repeated prompt']
)

# Check after each turn
if detector.check(response, reasoning):
    raise LoopDetected(detector.reason)
```

### Fix Applied (2026-01-22)

**Lowered detection thresholds** for faster loop detection:
- `identical_threshold`: 3 → 2 (detects duplicate responses faster)
- `min_response_length`: 50 → 100 (catches degraded responses earlier)

**Added stop file detection** for agent-initiated stops:
- Agent can create `STOPAUTOMATION-{session_hash}.json` to signal stop
- Session hash provides security (agent must know the session ID)
- Stop file contents can include reason: `{"reason": "Detected loop condition"}`

**Usage:**
```python
from sdqctl.core.loop_detector import LoopDetector

# With session ID for stop file security
detector = LoopDetector(session_id="my-session-123")

# Check includes stop file detection
if result := detector.check(reasoning, response, cycle):
    if result.reason == LoopReason.STOP_FILE:
        print("Agent requested stop via file")
    raise result

# Cleanup after workflow
detector.cleanup_stop_file()
```

**Template variables for agent communication:**

The `${STOP_FILE}` template variable is available in prompts. By default, stop file instructions are automatically injected on the first prompt:

```
## Automation Control

If you detect you are in a repetitive loop, cannot make further progress,
or need human review, create this file to stop automation:

    STOPAUTOMATION-a1b2c3d4e5f6.json

Include JSON explaining why: {"reason": "...", "needs_review": true}
```

Use `--no-stop-file-prologue` to disable this automatic injection, or `--stop-file-nonce=VALUE` to override the random nonce for testing.

**Stop File Persistence (Verified 2026-01-22):**

The stop file mechanism has been **verified working**. When an agent creates a stop file:
1. The file remains after automation stops for human inspection
2. Subsequent runs detect the existing file and refuse to continue
3. User must review and remove the file to continue

```bash
# After agent creates stop file, next run shows:
╭─────────────────── 🛑 Review Required ───────────────────╮
│ ⚠️  Stop file exists from previous run                   │
│ File: STOPAUTOMATION-abc123def456.json                   │
│ Reason: ...                                              │
│ To continue: Remove the stop file and run again          │
│     rm STOPAUTOMATION-abc123def456.json                  │
╰──────────────────────────────────────────────────────────╯
```

### See Also

- `docs/LOOP-STRESS-TEST.md` - Full stress test methodology and results
- `COPILOT-SDK-INTEGRATION.md` - Gap documentation for SDK abort events

---

## Q-003: Template Variables in Examples Encourage Problematic Patterns

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-22  
**Status:** ✅ RESOLVED - Q-001 fix + examples updated

### Description

Example workflows in `examples/workflows/` used `{{WORKFLOW_NAME}}` in headers.
With Q-001 fix, this is no longer problematic (WORKFLOW_NAME excluded from prompts).

### Fix Applied (2026-01-22)

1. **Q-001 fix resolves the root cause** - `{{WORKFLOW_NAME}}` is now excluded from
   prompts by default, so even if examples use it, it won't influence agent behavior.

2. **Examples updated** - Changed to use literal descriptions:
   - `test-discovery.conv`: `HEADER ## Session: {{DATETIME}}`
   - `verify-with-run.conv`: `HEADER # Verification Report`

3. **Examples enhanced with PROLOGUE patterns** (follow-up 2026-01-22):
   - `documentation-sync.conv`: Added explicit auditor role PROLOGUE
   - `security-audit.conv`: Added explicit security auditor role PROLOGUE
   - `test-discovery.conv`: Enhanced with explicit analyst role PROLOGUE
   - `component-analysis.conv`: Added explicit analyst role PROLOGUE
   
   All updated examples now follow `fix-quirks.conv` patterns:
   - Design principles documented in file header comments
   - Explicit role clarification in PROLOGUE
   - References to QUIRKS.md Q-001/Q-003 guidance

### Best Practice

```dockerfile
# For headers/prompts - use literal descriptions:
HEADER # Security Audit Report
HEADER ## Session: {{DATETIME}}

# For output paths - {{WORKFLOW_NAME}} still works:
OUTPUT-FILE reports/{{WORKFLOW_NAME}}-{{DATE}}.md

# If you need workflow name in prompts - use explicit opt-in:
PROLOGUE This is the {{__WORKFLOW_NAME__}} workflow.
```

---

## Future Considerations

> **Moved to [BACKLOG.md §4.5](../proposals/BACKLOG.md#45-workflow-authoring-enhancements-from-quirksmd)**
>
> Future enhancement ideas (JSON export, variable injection, etc.) are tracked in the proposal backlog,
> not in this quirks documentation.

## Template Variables Reference

Variables and their semantic impact when visible to the agent:

| Variable | Source | Semantic Impact | Notes |
|----------|--------|-----------------|-------|
| `{{WORKFLOW_NAME}}` | Filename stem | **SAFE** | Excluded from prompts by default (Q-001 fix) |
| `{{WORKFLOW_PATH}}` | Full path | **SAFE** | Excluded from prompts by default (Q-001 fix) |
| `{{__WORKFLOW_NAME__}}` | Filename stem | **HIGH** | Explicit opt-in - use with caution |
| `{{__WORKFLOW_PATH__}}` | Full path | **MEDIUM** | Explicit opt-in - use with caution |
| `{{COMPONENT_NAME}}` | Component file | LOW | Typically neutral file names |
| `{{GIT_BRANCH}}` | Git | LOW | Branch names usually technical |
| `{{CWD}}` | System | LOW | Directory names |
| `{{DATE}}`, `{{DATETIME}}` | System | NONE | Safe to use anywhere |
| `{{GIT_COMMIT}}` | Git | NONE | Safe to use anywhere |

**Key principle:** Variables with `__` prefix are explicit opt-in and may influence agent behavior.

---

## Contributing

When you discover a new quirk:

1. Add an entry following the template:
   - **ID**: Q-XXX (sequential)
   - **Priority**: P0 (high) / P1 (medium) / P2 (low)
   - **Description**: What happens
   - **Impact**: Why it matters
   - **Workaround**: How to avoid it
   - **Root cause** (if known)

2. Add to the Quick Reference table at the top

3. Cross-reference from related documentation

---

## See Also

- [COPILOT-SDK-INTEGRATION.md](../COPILOT-SDK-INTEGRATION.md) - SDK gaps and integration details
- [SYNTHESIS-CYCLES.md](SYNTHESIS-CYCLES.md) - Anti-patterns for workflows
- [LOOP-STRESS-TEST.md](LOOP-STRESS-TEST.md) - Loop detection testing methodology
