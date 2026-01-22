# Known Quirks and Surprising Behaviors

This document catalogs non-obvious behaviors discovered while developing and using sdqctl with the Copilot SDK. These are not bugs per se, but unexpected interactions that can confuse users.

---

## Quick Reference

| ID | Quirk | Priority | Status |
|----|-------|----------|--------|
| [Q-001](#q-001-workflow-filename-influences-agent-behavior) | Workflow filename influences agent behavior | P0 | ✅ FIXED |
| [Q-002](#q-002-sdk-abort-events-not-emitted) | SDK abort events not emitted | P1 | ✅ IMPROVED |
| [Q-003](#q-003-template-variables-in-examples-encourage-problematic-patterns) | Template variables in examples encourage problematic patterns | P2 | ✅ RESOLVED |
| [Q-004](#q-004-verbose-logging-shows-duplicate-content) | Verbose logging shows duplicate content | P2 | ✅ IMPROVED |
| [Q-010](#q-010-compact-directive-ignored-by-cycle-command) | COMPACT directive ignored by cycle command | P1 | ✅ FIXED |

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

The `{{WORKFLOW_NAME}}` template variable extracts the filename stem (e.g., `progress-tracker` from `progress-tracker.conv`). When this variable is used in prompts, headers, or prologues, **the agent uses the filename words as semantic signals** about its intended role.

### Example

A workflow file named `progress-tracker.conv` with this header:

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
progress-tracker.conv
documentation-sync.conv

# Use:
implement-improvements.conv
edit-and-sync.conv
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

**Agent instruction example:**
```
If you detect you are in a loop or cannot make progress, create a file
named STOPAUTOMATION-{hash}.json with {"reason": "your explanation"}.
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

These are documented ideas for future enhancement, not current quirks:

* **Export/import plans as JSON** - Allow interpreted conversations to be serialized
* **External variable injection** - Accept variables from file/stdin/env
* **Jsonnet integration** - Apply logic for branching on RUN failures
* **Environment variables** - Deny/accept list for env var access

> **Note:** The Q-001 fix addresses the concern about pathnames in prompts.
> Filesystem paths are now excluded by default, with explicit opt-in via `__` prefix.

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
- [QUINE-WORKFLOWS.md](QUINE-WORKFLOWS.md) - Anti-patterns for workflows
- [LOOP-STRESS-TEST.md](LOOP-STRESS-TEST.md) - Loop detection testing methodology
