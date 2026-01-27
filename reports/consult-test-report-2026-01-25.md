# CONSULT Feature Test Report

> **Date**: 2026-01-25  
> **Tester**: bewest + Copilot CLI  
> **Session**: 9859f571-b938-4b72-a8d0-472c4c3304e3  
> **Duration**: ~30 minutes (including investigation)

---

## Test Configuration

- **Workflow**: `tests/integration/workflows/consult-minimal.conv`
- **Adapter**: copilot
- **Model**: gpt-4
- **Test Script**: `test-consult.sh --minimal`

---

## Test Results

| Test Case | Description | Result | Notes |
|-----------|-------------|--------|-------|
| TC-01 | CONSULT pauses workflow | ✅ PASS | Printed resume instructions |
| TC-02 | Checkpoint saves "consulting" status | ✅ PASS | `pause.json` has correct status |
| TC-03 | Resume detects CONSULT and injects prompt | ✅ PASS | Agent presented questions on resume |
| TC-04 | Agent presents questions via ask_user | ✅ PASS | Interactive Q&A worked |
| TC-05 | Workflow continues after questions answered | ✅ PASS | Started doing work (CTRL-C'd) |

**Overall: CONSULT Feature Verified ✅**

---

## Phase A: Run to CONSULT

**Command**: `./test-consult.sh --minimal`

**Observations**:
- [x] Workflow started successfully
- [x] Agent executed first PROMPT (12.1s)
- [x] CONSULT directive triggered pause
- [x] Resume instructions printed

**Console output**:
```
Running consult-minimal.conv...
  Prompt 1/2 (ctx: 0%): Sending...
  Prompt 1/2 (ctx: 0%): Complete (12.1s)

⏸  CONSULT: "TODO App Design Decisions"
Session paused for human consultation.
Checkpoint saved: /home/bewest/.sdqctl/sessions/8b41b034/pause.json

To resume: copilot --resume consult-test
On resume, the agent will proactively present open questions.
```

---

## Phase B: Checkpoint Verification

**Checkpoint file**: `~/.sdqctl/sessions/8b41b034/pause.json`

**Content**:
```json
{
    "type": "pause",
    "message": "CONSULT: \"TODO App Design Decisions\"",
    "status": "consulting",
    "timestamp": "2026-01-25T20:56:40.206993+00:00",
    "session_id": "8b41b034",
    "conversation_file": ".../consult-minimal.conv",
    "prompt_index": 1,
    "messages": [
        {"role": "user", "content": "...TODO app design prompt..."},
        {"role": "assistant", "content": "## 🔴 CONSULT: Open Questions..."}
    ]
}
```

**Verification**:
- [x] File exists
- [x] Status is "consulting"
- [x] Message contains topic "TODO App Design Decisions"
- [x] Agent identified 3 questions in first response

---

## Phase C: Resume Session

**Initial attempts**:
1. `sdqctl sessions resume 8b41b034` → **FAILED** - "Session not found"
2. `copilot --resume consult-test` → **Session not in list** by name
3. `sdqctl sessions resume 9859f571-...` → ✅ **SUCCESS** (found by UUID)

**Finding**: Session ID mismatch between sdqctl checkpoint (`8b41b034`) and SDK session (`9859f571-...`). See Q-018 below.

**Observations after successful resume**:
- [x] Session resumed successfully
- [x] Agent proactively presented questions
- [x] Agent used interactive prompts for input
- [x] Workflow continued after answers

---

## Phase D: Workflow Continuation

**After questions answered**:
- [x] Agent acknowledged answers
- [x] Workflow started executing post-CONSULT PROMPT
- [x] User CTRL-C'd during work (confirming continuation worked)

---

## Issues Found

### Issue 1: Session ID Mismatch (Q-018)

- **Severity**: 🟡 Medium (UX friction, not data loss)
- **Description**: sdqctl checkpoint uses short ID (`8b41b034`) but SDK session uses UUID (`9859f571-b938-4b72-a8d0-472c4c3304e3`). Resume commands don't work with the ID printed in checkpoint message.
- **Steps to reproduce**:
  1. Run workflow with CONSULT
  2. Note checkpoint path printed (e.g., `8b41b034`)
  3. Try `sdqctl sessions resume 8b41b034`
  4. Fails with "Session not found"
- **Expected behavior**: Resume command works with the ID shown
- **Actual behavior**: Must find session by UUID in `sdqctl sessions list`
- **Root cause**: `--session-name` not being used as actual session ID
- **Workaround**: Use `sdqctl sessions list` to find the UUID, resume with that

### Issue 2: Test Script Path Assumption (Minor)

- **Severity**: 🟢 Low
- **Description**: `test-consult.sh` assumes checkpoint path based on `--session-name` but actual path uses generated short ID
- **Fix**: Update script to search for recent checkpoints or parse output

---

## Recommendations

1. **Q-018 Fix**: Ensure `--session-name` is used consistently as session ID, or update checkpoint message to show the correct resumable ID
2. **Test Script**: Update to dynamically find checkpoint path from sdqctl output
3. **Documentation**: Add note about finding session UUID for resume

---

## Conclusion

**The CONSULT feature works correctly end-to-end.** All 5 test cases passed. The session ID mismatch is a UX issue that should be addressed but doesn't block feature use.

**Feature Status**: ✅ Ready for use (with Q-018 workaround documented)

---

## Files

- Test script: `test-consult.sh`
- Minimal workflow: `tests/integration/workflows/consult-minimal.conv`
- Log: `consult-test-logs/consult-test-2026-01-25-125626.log`
- Checkpoint: `~/.sdqctl/sessions/8b41b034/pause.json`
