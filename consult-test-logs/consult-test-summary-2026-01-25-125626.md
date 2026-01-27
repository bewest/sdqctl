# CONSULT Test Summary - 2026-01-25 125626

## Configuration
- Workflow: minimal (/home/bewest/src/copilot-do-proposal/sdqctl/tests/integration/workflows/consult-minimal.conv)
- Adapter: copilot
- Session: consult-test-minimal

## Results

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-01 | CONSULT pauses workflow | Check log |
| TC-02 | Checkpoint saves status | FAIL |
| TC-03 | Resume with prompt injection | Manual |
| TC-04 | Agent presents questions | Manual |

## Checkpoint Content

```json
Not found
```

## Next Steps

1. Run: `sdqctl sessions resume consult-test-minimal`
2. Verify agent presents questions
3. Answer questions and verify workflow continues
4. Record findings in reports/

## Log File

/home/bewest/src/copilot-do-proposal/sdqctl/consult-test-logs/consult-test-2026-01-25-125626.log
