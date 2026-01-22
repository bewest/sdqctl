# Known Quirks and Surprising Behaviors

This document catalogs non-obvious behaviors discovered while developing and using sdqctl with the Copilot SDK. These are not bugs per se, but unexpected interactions that can confuse users.

---

## Quick Reference

| ID | Quirk | Priority | Workaround Available |
|----|-------|----------|---------------------|
| [Q-001](#q-001-workflow-filename-influences-agent-behavior) | Workflow filename influences agent behavior | P0 | ✅ Yes |
| [Q-002](#q-002-sdk-abort-events-not-emitted) | SDK abort events not emitted | P1 | ✅ Yes |
| [Q-003](#q-003-template-variables-in-examples-encourage-problematic-patterns) | Template variables in examples encourage problematic patterns | P2 | ✅ Yes |

---

## Q-001: Workflow Filename Influences Agent Behavior

**Priority:** P0 - High Impact  
**Discovered:** 2026-01-22  
**Status:** Documented, workarounds available

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

### Future Fix Options

Let's explicitly take pathnames/filenames out of the injected prompts because
this was surprising. Instead we can consider a user controlled variable that
can be overriden using a cli switch somehow in places where the
pathname/filename was being used as prompt material.  It's ok to consider
additional directives and breaking changes because we're still early but let's
consider them proposals for additional review without compelling evidence.

Prior alternatives:
| Option | Effort | Breaking Change |
|--------|--------|-----------------|
| A. Add `MODE-HINT implement` directive | Low | No |
| C. Document prominently (this document) | Low | No |

---

## Q-002: SDK Abort Events Not Emitted

**Priority:** P1 - Medium Impact  
**Discovered:** 2026-01-22  
**Status:** Documented, client-side workaround implemented

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

### Fix desired
Consider lowering detection thresholds to minimum the minimum that seem  work
well.  Also consider using detection/escalation metaphor to request the agent
to create a STOPAUTOMATION.json or similar file that we can positively detect
and stop.  If we detect its existence during duplication detection mode, we can
stop.  We can consider making it more secure by making the filename a
calculated unique value that we can definitely check for "this single unique
instance", maybe a hash of our session id?
Let's see how sensitive we can make this detection work so that we don't abuse
the API and can balance injecting too much into context.

### See Also

- `docs/LOOP-STRESS-TEST.md` - Full stress test methodology and results
- `COPILOT-SDK-INTEGRATION.md` - Gap documentation for SDK abort events

---

## Q-003: Template Variables in Examples Encourage Problematic Patterns

**Priority:** P2 - Low Impact  
**Discovered:** 2026-01-22  
**Status:** Documented

### Description

Example workflows in `examples/workflows/` use `{{WORKFLOW_NAME}}` in headers:

```dockerfile
# From test-discovery.conv
HEADER ## Workflow: {{WORKFLOW_NAME}}

# From verify-with-run.conv
HEADER # Verification Report - {{WORKFLOW_NAME}}
```

Users copying these patterns may inadvertently trigger Q-001 (filename influencing behavior).

### Impact

- Users learn patterns that can cause subtle issues
- Copy-paste workflow creation inherits problematic patterns

### Workaround

When creating new workflows:
1. Use literal descriptions instead of `{{WORKFLOW_NAME}}` for headers visible to the agent
2. Reserve `{{WORKFLOW_NAME}}` for output filenames and metadata not parsed by the agent
3. Choose implementation-oriented filenames from the start

### Recommended Pattern

```dockerfile
# For headers (visible to agent) - use literals:
HEADER # Security Audit Report
HEADER ## Generated: {{DATETIME}}

# For output files (not parsed by agent) - {{WORKFLOW_NAME}} is safe:
OUTPUT-FILE reports/{{WORKFLOW_NAME}}-{{DATE}}.md
```

---

Potential desirable fix cross cutting other ideas/components:
* is there a way to export/import interpreted conversations as plans? in json?
* for all the variables that exist, is it desirable to be able to accept import/export
  of entire plan with the variables well defined, or worth the complexity of doing something like a (potentially customized schema) where all variables can come from a file (stdin/file).  This might integrate with tooling nicely.
* A cross cutting concern here, but out of scope, is potentially having a
  jsonnet executor in between export/import to apply logic.  This may put a
  pressure relief or a way to standardize the proposal for how to branch on
  error/timaeout when RUN directives may fail.
* Is it possible for arbitrary environment variables to be used?   Should it?
  What are the risks/impacts?  Deny/accept list, read from .env file, inject
  from json?


IMPORTANT:
Let's make sure in accordance with the above fixes that pathnames and other
filesystem information does not go into prompt materials, or that if it is
possible, it is explicit with variable like __FILENAME__.

## Template Variables Reference

Variables that may have semantic impact when visible to the agent:

| Variable | Source | Semantic Impact |
|----------|--------|-----------------|
| `{{WORKFLOW_NAME}}` | Filename stem | **HIGH** - Word choice affects agent role interpretation |
| `{{WORKFLOW_PATH}}` | Full path | **MEDIUM** - Path may contain project/folder names |
| `{{COMPONENT_NAME}}` | Component file | LOW - Typically neutral file names |
| `{{GIT_BRANCH}}` | Git | LOW - Branch names usually technical |
| `{{CWD}}` | System | LOW - Directory names |
| `{{DATE}}`, `{{DATETIME}}` | System | NONE |
| `{{GIT_COMMIT}}` | Git | NONE |

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
