# Error Handling Strategy

> **Status**: Implemented ✅  
> **Created**: 2026-01-24  
> **Updated**: 2026-01-24  
> **Priority**: P1 (High Value)

---

## Problem Statement

Error handling patterns are scattered across multiple documents:

| Pattern | Location | Scope |
|---------|----------|-------|
| `RUN-ON-ERROR` | RUN-BRANCHING.md | Shell command failures |
| `VERIFY-ON-ERROR` | VERIFICATION-DIRECTIVES.md | Verification failures |
| `ON-FAILURE` blocks | RUN-BRANCHING.md (proposed) | Complex recovery |
| `RUN-RETRY` | conversation.py (implemented) | Retry with AI fix |
| SDK abort events | QUIRKS.md Q-002 | Session termination |
| Stop file mechanism | QUIRKS.md Q-002 | External abort trigger |

This fragmentation leads to:
- Inconsistent error behavior across directives
- Confusing UX when errors occur
- Difficulty understanding "what happens when X fails"

---

## Current Error Handling

### Implemented

| Directive | Error Behavior | Options |
|-----------|---------------|---------|
| `RUN` | Stop workflow | `RUN-ON-ERROR continue\|stop` |
| `RUN-RETRY` | Retry N times with AI fix | `RUN-RETRY 3 "Fix the error"` |
| `VERIFY` | Log and continue | `VERIFY-ON-ERROR fail\|continue` |
| `CONTEXT` | Fail on missing | `CONTEXT-OPTIONAL` for lenient |
| `ON-FAILURE` block | Execute block on RUN failure | Conditional branching |
| `ON-SUCCESS` block | Execute block on RUN success | Conditional branching |

### Not Yet Implemented

| Feature | Proposal | Status |
|---------|----------|--------|
| Global error handler | None | Not proposed |
| Timeout handling | Partial (RUN-TIMEOUT) | Implemented |

---

## Proposed Unified Model

### Error Categories

| Category | Examples | Default Behavior |
|----------|----------|------------------|
| **Recoverable** | Test failure, lint warning | Continue (log warning) |
| **Transient** | Network timeout, rate limit | Retry (with backoff) |
| **Fatal** | Missing required file, parse error | Stop immediately |
| **User abort** | Stop file, Ctrl+C, SDK abort | Clean exit |

### Directive Consistency

All directives that can fail should support:

```dockerfile
# Pattern: DIRECTIVE-ON-ERROR behavior
RUN-ON-ERROR continue      # For RUN
VERIFY-ON-ERROR fail       # For VERIFY
CONTEXT-ON-ERROR warn      # For CONTEXT (proposed)
```

Behaviors:
- `stop` / `fail` - Halt workflow immediately
- `continue` - Log warning, proceed
- `warn` - Log warning, proceed (alias for continue)
- `retry` - Retry with backoff (where applicable)

---

## Blocker Surfacing Pattern

From [PHILOSOPHY.md](../docs/PHILOSOPHY.md):

> "Every synthesis cycle needs scope partitioning for when AI encounters blockers."

Error handling should support blocker surfacing and categorical chunking:

```dockerfile
# If AI can't fix after N retries, document the blocker
RUN-RETRY 3 "Fix the failing test"
RUN-ON-ERROR continue

PROMPT """
If the test still fails after retries, document the issue:
1. What test is failing?
2. What error message?
3. What have you tried?
4. Add to BLOCKERS.md
"""
```

---

## SDK Abort Event Gap

> **Reference**: [SDK-LEARNINGS.md](../docs/SDK-LEARNINGS.md#2-sdk-abort-events-are-not-emitted-q-002) | [Archived Q-002](../archive/quirks/2026-01-resolved-quirks.md#q-002-sdk-abort-events-not-emitted)

The Copilot SDK does not reliably emit abort events. Current workarounds:

| Mechanism | Detection | Action |
|-----------|-----------|--------|
| Stop file | Check `.sdqctl-stop` | Clean exit |
| Inactivity timeout | No events for N seconds | Assume stuck |
| Turn limit | MAX-CYCLES exceeded | Stop with checkpoint |

### Proposed: `ON-ABORT` Directive

```dockerfile
ON-ABORT
  CHECKPOINT                    # Save state
  OUTPUT-FILE abort-state.json  # Dump context
  RUN notify-team.sh            # Alert
```

**Status**: Future work - needs SDK improvements first

---

## Error Reporting

### Current

Errors logged to console with Rich formatting:
```
[red]✗ RUN failed: pytest exited with code 1[/red]
```

### Proposed: Structured Error Output

```json
{
  "error": {
    "type": "run_failed",
    "directive": "RUN",
    "command": "pytest",
    "exit_code": 1,
    "stderr": "...",
    "recovery": "RUN-ON-ERROR continue"
  }
}
```

Enable with `--json-errors` flag for CI integration.

---

## Open Questions

1. **Global error handler?** Should there be a workflow-level `ON-ANY-ERROR` block?

2. **Error escalation?** Should multiple warnings eventually become a fatal error?

3. **Error context?** How much error context should be preserved across compaction?

4. **Retry backoff?** Should `RUN-RETRY` support exponential backoff?

---

## Implementation Roadmap

| Phase | Feature | Complexity | Status |
|-------|---------|------------|--------|
| 0 | Consolidate docs (this file) | Low | ✅ Complete |
| 1 | Add `--strict` to verify | Low | ✅ Complete (2026-01-24) |
| 2 | Implement ON-FAILURE blocks | Moderate | ✅ Complete (2026-01-24) |
| 3 | Add `--json-errors` output | Moderate | ✅ Complete (2026-01-24) |
| 4 | ON-ABORT handling | Moderate | Pending |

### Phase 1 Implementation Notes

Added `--strict` flag to all verify commands:

| Command | --strict | Notes |
|---------|----------|-------|
| `verify refs` | ✅ | Promotes warnings to errors |
| `verify links` | ✅ | Promotes warnings to errors |
| `verify traceability` | ✅ | Already had --strict |
| `verify terminology` | ✅ | Already had --strict |
| `verify assertions` | ⚡ | Uses --require-message/--require-trace instead |
| `verify all` | ✅ | Propagates --strict to all verifiers |

**Usage for CI:**
```bash
# Fail CI build if any warnings
sdqctl verify all --strict
sdqctl verify traceability --strict
```

### Phase 2 Implementation Notes

Implemented `ON-FAILURE` and `ON-SUCCESS` blocks for conditional execution based on RUN result:

| Component | Implementation | Notes |
|-----------|----------------|-------|
| Directive types | `core/conversation.py` | `DirectiveType.ON_FAILURE`, `ON_SUCCESS`, `END` |
| Step fields | `core/conversation.py` | `ConversationStep.on_failure`, `on_success` lists |
| Block parsing | `core/conversation.py` | Block context tracking in `parse()` method |
| ELIDE validation | `core/conversation.py` | `validate_elide_chains()` checks for blocks |
| Block execution | `commands/run.py` | `_execute_block_steps()` helper |
| Tests | `tests/test_conversation.py` | 9 tests in `TestOnFailureDirectiveParsing` |

**Syntax:**
```dockerfile
RUN pytest
ON-FAILURE
PROMPT Fix the failing tests.
RUN git diff
END
ON-SUCCESS
PROMPT All tests passed! Deploy now.
END
```

**Semantics:**
- `ON-FAILURE` block executes if preceding RUN exits non-zero
- `ON-SUCCESS` block executes if preceding RUN exits zero
- Both blocks are optional
- Block content should NOT be indented (indentation = multiline continuation)
- Blocks cannot be nested
- Blocks inside ELIDE chains are invalid (parse error)

**Interaction with stop-on-error:**
- If `ON-FAILURE` block is present and run_on_error=stop, workflow continues (block handles failure)
- If no `ON-FAILURE` block and run_on_error=stop, workflow stops as before

### Phase 3 Implementation Notes

Added `--json-errors` global flag for structured error output:

| Component | Implementation | Notes |
|-----------|----------------|-------|
| Global flag | `cli.py` | `--json-errors` option |
| Exception serialization | `core/exceptions.py` | `exception_to_json()`, `format_json_error()` |
| Error handler | `utils/output.py` | `handle_error()`, `print_json_error()` |
| Run command | `commands/run.py` | Uses `handle_error()` for failures |
| Cycle command | `commands/cycle.py` | Uses `handle_error()` for failures |
| Exit codes | `core/exceptions.py` | Added `RUN_FAILED`, `VALIDATION_FAILED`, `VERIFY_FAILED` |

**New exception types:**
- `RunCommandFailed` - For RUN directive failures

**JSON error structure:**
```json
{
  "error": {
    "type": "MissingContextFiles",
    "message": "Human-readable error message",
    "exit_code": 2,
    "files": ["@missing.md"],
    "context": {
      "workflow": "path/to/workflow.conv",
      "checkpoint": "path/to/checkpoint"
    }
  }
}
```

**Usage for CI:**
```bash
# JSON errors for CI pipelines
sdqctl --json-errors run workflow.conv 2>&1 | jq '.error.type'
sdqctl --json-errors cycle workflow.conv | jq .

# Combine with quiet mode (implicit when --json-errors is set)
sdqctl --json-errors run workflow.conv
```

---

## References

- [RUN-BRANCHING.md](RUN-BRANCHING.md) - ON-FAILURE proposal
- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - VERIFY-ON-ERROR
- [QUIRKS.md](../docs/QUIRKS.md) - Q-002 abort events
- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Blocker surfacing pattern
