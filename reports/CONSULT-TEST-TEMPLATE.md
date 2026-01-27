# CONSULT Feature Test Report Template

> **Date**: YYYY-MM-DD  
> **Tester**: [Your name]  
> **Session**: [Session name]  
> **Duration**: [Time spent]

---

## Test Configuration

- **Workflow**: `tests/integration/workflows/consult-minimal.conv` or `examples/workflows/consult-design.conv`
- **Adapter**: copilot
- **Model**: gpt-4
- **sdqctl Version**: [version]

---

## Test Results

| Test Case | Description | Result | Notes |
|-----------|-------------|--------|-------|
| TC-01 | CONSULT pauses workflow | ⬜ | |
| TC-02 | Checkpoint saves "consulting" status | ⬜ | |
| TC-03 | Resume detects CONSULT and injects prompt | ⬜ | |
| TC-04 | Agent presents questions via ask_user | ⬜ | |
| TC-05 | Workflow continues after questions answered | ⬜ | |

**Legend**: ✅ Pass | ❌ Fail | ⚠️ Partial | ⬜ Not tested

---

## Phase A: Run to CONSULT

**Command**: `./test-consult.sh --minimal`

**Observations**:
- [ ] Workflow started successfully
- [ ] Agent executed first PROMPT
- [ ] CONSULT directive triggered pause
- [ ] Resume instructions printed

**Console output** (key excerpts):
```
[Paste relevant output here]
```

---

## Phase B: Checkpoint Verification

**Checkpoint file**: `~/.sdqctl/sessions/[session-name]/pause.json`

**Content**:
```json
{
  "status": "...",
  "message": "...",
  ...
}
```

**Verification**:
- [ ] File exists
- [ ] Status is "consulting"
- [ ] Message contains topic "TODO App Design Decisions" (or expected topic)

---

## Phase C: Resume Session

**Command**: `sdqctl sessions resume [session-name]`

**Observations**:
- [ ] Session resumed successfully
- [ ] Consultation prompt injected (topic shown)
- [ ] Agent proactively presented questions
- [ ] Agent used ask_user tool for input

**Agent's question presentation**:
```
[Paste how agent presented questions]
```

**Answers provided**:
1. Question 1: [Your answer]
2. Question 2: [Your answer]
3. Question 3: [Your answer]

---

## Phase D: Workflow Continuation

**After questions answered**:
- [ ] Agent acknowledged answers
- [ ] Workflow continued to post-CONSULT PROMPT
- [ ] Final output generated
- [ ] Session completed or can be continued

**Final output** (if any):
```
[Paste final output or summary]
```

---

## Issues Found

### Issue 1: [Title]
- **Severity**: 🔴 Critical / 🟡 Medium / 🟢 Low
- **Description**: 
- **Steps to reproduce**:
- **Expected behavior**:
- **Actual behavior**:
- **Workaround** (if any):

---

## Recommendations

1. [Recommendation based on findings]
2. [Any improvements to CONSULT feature]
3. [Any improvements to test script]

---

## Log Files

- Test log: `consult-test-logs/consult-test-YYYY-MM-DD-HHMMSS.log`
- Summary: `consult-test-logs/consult-test-summary-YYYY-MM-DD-HHMMSS.md`
- Event log: [if --event-log was used]

---

## Conclusion

[Overall assessment of CONSULT feature readiness]

**Feature Status**: ⬜ Ready for use / ⬜ Needs fixes / ⬜ Blocked
