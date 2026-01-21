# RUN Directive Improvements - Topic Focus

**Topic:** RUN directive (subprocess execution in .conv files)  
**Source:** `reports/improvements-tracker.md`  
**Created:** 2026-01-21  
**Status:** In Progress

---

## What is the RUN Directive?

The RUN directive executes shell commands within a conversation workflow:

```
RUN python3 -m pytest tests/
RUN-ON-ERROR continue
RUN-OUTPUT always
RUN-TIMEOUT 120
ALLOW-SHELL true
```

**Implementation:** `sdqctl/commands/run.py` lines 430-504  
**Parsing:** `sdqctl/core/conversation.py` (ConversationFile dataclass)

---

## Scope Boundaries

### In Scope
- RUN directive execution (`subprocess.run` handling)
- Related directives: RUN-ON-ERROR, RUN-OUTPUT, RUN-TIMEOUT, ALLOW-SHELL
- Error recovery and partial output capture
- Security considerations for command execution
- Testing of RUN directive behavior

### Out of Scope (for this topic)
- `sdqctl run` CLI command structure
- Adapter communication (AI interactions)
- Other step types (PROMPT, PAUSE)
- Session/checkpoint handling

---

## Improvement Chunks

Work is organized by priority within each category. Complete one chunk before moving to the next.

### 1. Reliability & Error Recovery

#### R1: Timeout Partial Output Capture (P1-2) ✅ DONE
**File:** `sdqctl/commands/run.py` lines 489-508  
**Completed:** 2026-01-21

```python
except subprocess.TimeoutExpired as e:
    logger.error(f"  ✗ Command timed out after {conv.run_timeout}s")
    
    # Capture partial output (always - timeout output is valuable for debugging)
    partial_stdout = e.stdout or ""
    partial_stderr = e.stderr or ""
    partial_output = partial_stdout
    if partial_stderr:
        partial_output += f"\n\n[stderr]\n{partial_stderr}"
    
    if partial_output.strip():
        run_context = f"```\n$ {command}\n[TIMEOUT after {conv.run_timeout}s]\n{partial_output}\n```"
        session.add_message("system", f"[RUN timeout - partial output]\n{run_context}")
```

**Tests added:** `TestTimeoutPartialOutput` class (2 tests) in `tests/test_run_command.py`

#### R2: RUN Failure Context Enhancement ⏳
**File:** `sdqctl/commands/run.py` lines 465-487  
**Status:** BUG CONFIRMED - needs fix

**Finding:** Output IS added to context (lines 477-487) when `include_output=True`, BUT when `run_on_error == "stop"` and command fails, the function returns at line 475 BEFORE output is added to context.

**Current behavior (run.py:469-487):**
- ✅ `RUN-ON-ERROR continue` + failure → output added to context (continues past line 475)
- ❌ `RUN-ON-ERROR stop` + failure → returns at line 475 BEFORE adding output (BUG)

**Fix needed:** Move the `include_output` block (lines 477-487) to run BEFORE the early return at line 475. Or restructure to always capture output, then check run_on_error.

**Tasks:**
- [x] Verify failure output behavior (done - found bug confirmed)
- [ ] Fix: add output to context BEFORE early return on stop
- [ ] Add tests to confirm failure context behavior

### 2. Security

#### S1: Shell Injection Prevention ✅ DONE
- Added `ALLOW-SHELL` directive (default: false)
- RUN uses `shlex.split()` by default (no shell injection)
- Shell features (pipes, redirects) require explicit `ALLOW-SHELL true`
- 9 tests added in `tests/test_run_command.py`

#### ~~S2: Command Allowlist/Denylist~~ SKIPPED
**Decision:** Skip entirely. RUN is local execution by sdqctl, not AI-controlled. ALLOW-SHELL is sufficient security for untrusted workflows.

### 3. Ergonomics

#### E1: RUN Output Limit ⏳
**File:** `sdqctl/commands/run.py` lines 477-487  
**Issue:** No limit on output size - massive logs could overwhelm context

**Design decision:** 
- Default: no limit (matches current behavior)
- Add `RUN-OUTPUT-LIMIT` directive for users who want limits
- Syntax: `RUN-OUTPUT-LIMIT 10K`, `RUN-OUTPUT-LIMIT none`
- Future: add truncation modes (`head`, `tail`, `head+tail`)

**Tasks:**
- [ ] Add `run_output_limit` field to ConversationFile (default: None = unlimited)
- [ ] Parse `RUN-OUTPUT-LIMIT` directive
- [ ] Truncate output before adding to context if limit set
- [ ] Add tests for output limiting

#### ~~E2: RUN Working Directory~~ SKIPPED
**Decision:** Skip - users can `cd subdir && command` with ALLOW-SHELL or use wrapper scripts.

### 4. Code Quality

#### Q1: Subprocess Handling Duplication ⏳
**File:** `sdqctl/commands/run.py` lines 430-453  
**Issue:** Similar subprocess.run() call duplicated for shell vs non-shell

```python
if conv.allow_shell:
    result = subprocess.run(command, shell=True, ...)
else:
    result = subprocess.run(shlex.split(command), shell=False, ...)
```

**Tasks:**
- [ ] Extract to helper function with shell parameter
- [ ] Reduce code duplication
- [ ] Make timeout and capture_output configurable per-call

### 5. Testing

#### T1: RUN Directive Integration Tests ✅ DONE
**File:** `tests/test_run_command.py`  
**Completed:** 2026-01-21  
**Tests added:** 7 new tests (34 → 41 total)

- `TestRunSubprocessExecution` (4 tests):
  - `test_run_echo_captures_output` - successful command output
  - `test_run_failing_command_returns_nonzero` - failure exit codes
  - `test_run_output_added_to_session` - output format verification
  - `test_run_failure_includes_stderr` - stderr capture

- `TestMultiStepWorkflow` (3 tests):
  - `test_multiple_prompts_parsed` - multi-prompt parsing
  - `test_mixed_steps_all_parsed` - PROMPT/RUN/CHECKPOINT order
  - `test_run_step_content_preserved` - command content preservation

---

## Completed This Session

**Session: 2026-01-21T19:33**

1. **All 41 tests passing** - Full test suite green (verified)
2. **R2 bug location confirmed** - run.py:469-475 returns early before output capture at lines 477-487
3. **Report updated** - Tracked progress, confirmed next priorities

**Previous Session: 2026-01-21T19:20**

1. **All 41 tests passing** - Full test suite green (verified current state)
2. **Progress review complete** - Analyzed run.py:430-520 for R2 status

**Previous Session: 2026-01-21T19:10**

1. **All 41 tests passing** - Full test suite green (34 → 41 tests)
2. **S1: Shell Injection Prevention** - Verified complete with 9 dedicated tests
3. **R1: Timeout Partial Output Capture** - IMPLEMENTED
   - Modified `run.py:489-508` to capture `e.stdout`/`e.stderr` on TimeoutExpired
   - Added `[TIMEOUT after Xs]` marker in context for clarity
   - Added 2 tests in `TestTimeoutPartialOutput` class
4. **Priority 0 BLOCKER FIXED** - Step loop indentation bug
   - Fixed `run.py:310-520` - entire step processing block now properly indented inside for loop
   - Multi-step workflows now process ALL steps (was only processing last step)
5. **T1: RUN Integration Tests** - IMPLEMENTED
   - Added `TestRunSubprocessExecution` class (4 tests): echo, failing command, output format, stderr
   - Added `TestMultiStepWorkflow` class (3 tests): multiple prompts, mixed steps, RUN content

---

## Lessons Learned

1. **TimeoutExpired has output attributes** - Research confirmed `subprocess.TimeoutExpired` exposes `stdout`, `stderr`, and `output` attributes. The fix for R1 is straightforward: access `e.stdout` and `e.stderr` in the except block.

2. **Test coverage is solid for parsing** - 41 tests now cover directive parsing AND subprocess execution patterns.

3. **CRITICAL BUG FIXED: run.py indentation** - Lines 310-313 defined the step loop, but the loop body (lines 314+) was NOT indented inside the loop! Only the last step was processed. **Fixed by re-indenting entire step processing block (lines 314-520).**

4. **R2 (failure context) bug CONFIRMED** - Reviewed run.py:469-475 vs run.py:477-487. When `run_on_error == "stop"` and command fails, the function returns at line 475 BEFORE the `include_output` block at lines 477-487. The output IS NOT added to context on stop+failure. This is a real bug that needs fixing.

5. **Parsing tests don't catch runtime bugs** - The original 34 tests all passed even with the indentation bug because they only tested ConversationFile parsing, not actual step execution. T1 integration tests now cover subprocess patterns.

6. **Integration tests verify behavior without mocking AI** - The T1 tests verify subprocess.run behavior directly, which catches real issues without needing to mock the adapter layer.

7. **Code review matches line numbers exactly** - run.py:430-520 confirmed the subprocess handling structure. The R2 bug is at lines 469-475 (early return) vs 477-487 (output capture).

8. **Short iterative sessions work well** - Each ~10 min session verified state, made progress, documented findings. Context files enable continuity.

---

## Research Needed

### RN1: Session Message Persistence on Early Return
**Question:** When `run.py` returns early at line 475 (stop on error), are session messages still saved/checkpointed, or is the context lost entirely?

**Why it matters:** If we fix R2 by adding output to context before the early return, we need to ensure that output is actually persisted somewhere useful.

**Research approach:**
- Trace `session.add_message()` to understand where messages are stored
- Check if the `finally` blocks at lines 517-520 handle session persistence
- Test by running a workflow with RUN-ON-ERROR stop and checking checkpoint files

---

## Next 3 Taskable Areas

### Priority 1: R2 - RUN Failure Context Fix (BUG)
**File:** `sdqctl/commands/run.py:469-487`  
**Effort:** ~20 min  
**Unblocked:** Yes - confirmed bug, clear fix path

Fix: Move output capture BEFORE early return. Structure change:
```python
# Current (buggy): 
if result.returncode != 0:
    if conv.run_on_error == "stop":
        return  # Output never captured!
if include_output:
    session.add_message(...)  # Only reached on continue

# Fixed:
if include_output:
    session.add_message(...)  # Always capture output first
if result.returncode != 0 and conv.run_on_error == "stop":
    return  # Now output is already captured
```

### Priority 2: Q1 - Subprocess Handling Refactor
**File:** `sdqctl/commands/run.py:434-456`  
**Effort:** ~30 min  
**Unblocked:** Yes - pure refactor, no behavioral change

```python
# Extract helper:
def _run_subprocess(command: str, allow_shell: bool, timeout: int, cwd: Path) -> subprocess.CompletedProcess:
    args = command if allow_shell else shlex.split(command)
    return subprocess.run(args, shell=allow_shell, capture_output=True, text=True, timeout=timeout, cwd=cwd)
```

### Priority 3: E1 - RUN Output Limit
**File:** `sdqctl/core/conversation.py` + `sdqctl/commands/run.py`  
**Effort:** ~45 min  
**Unblocked:** Yes

Tasks:
- [ ] Add `run_output_limit` field to ConversationFile (default: None = unlimited)
- [ ] Add `RUN-OUTPUT-LIMIT` directive type and parsing
- [ ] Truncate output before adding to context if limit set
- [ ] Add tests for output limiting

---

## Next Session Command

```bash
cd /path/to/sdqctl
sdqctl -vv cycle -n 3 --adapter copilot \
  --prologue @reports/run-improvements-focus.md \
  --epilogue "Update @reports/run-improvements-focus.md with completed items and lessons learned" \
  examples/workflows/progress-tracker.conv
```

---

## References

- `sdqctl/commands/run.py` - main implementation
- `reports/improvements-tracker.md` - full improvements list
- `examples/workflows/progress-tracker.conv` - cycle workflow
- `tests/test_run_command.py` - existing tests
