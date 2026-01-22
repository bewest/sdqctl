# Loop Detection Stress Test Tool

A stress testing tool for validating the Copilot SDK's abort/loop detection mechanisms.

## Overview

This tool tests four detection mechanisms in the `LoopDetector` class:

1. **REASONING_PATTERN** - Detects when the AI's reasoning contains loop-aware phrases like "in a loop", "repeated prompt", etc.
2. **IDENTICAL_RESPONSES** - Detects when 2 consecutive responses are identical (lowered from 3 in Q-002 fix)
3. **MINIMAL_RESPONSE** - Detects when responses become suspiciously short (<100 chars) after the first cycle
4. **STOP_FILE** - Detects when the agent creates a `STOPAUTOMATION-{session_hash}.json` file to signal stop

## Quick Start

```bash
# Activate the sdqctl environment
source sdqctl/bin/activate

# Run all tests with default settings (gpt-4o model)
./test-loop-stress.sh --verbose

# Run a specific test
./test-loop-stress.sh --elicit --verbose

# Use mock adapter for development (no API calls)
./test-loop-stress.sh --mock --verbose
```

## Test Cases

### 1. Repeated Prompt Test (`--repeated`)

Sends the same prompt N times to trigger identical response detection:

```bash
./test-loop-stress.sh --repeated --cycles 5 --verbose
```

**Expected Results:**
- `MINIMAL_RESPONSE` triggers after cycle 2 (responses ~31 chars)
- `IDENTICAL_RESPONSES` may trigger if AI gives same response 3+ times

### 2. Loop Elicit Test (`--elicit`)

Sends a prompt asking the AI to respond as if in a loop:

```bash
./test-loop-stress.sh --elicit --verbose
```

**Expected Results:**
- `REASONING_PATTERN` triggers immediately (cycle 1)
- AI reasoning contains phrases like "loop situation", "repeated prompt"

### 3. Minimal Response Test (`--minimal`)

Sends a prompt asking for very short response after setup:

```bash
./test-loop-stress.sh --minimal --verbose
```

**Expected Results:**
- `MINIMAL_RESPONSE` triggers on cycle 2 (responses <100 chars)

### 4. Stop File Detection

The agent can create a stop file to explicitly request automation stop:

```bash
# Agent creates: STOPAUTOMATION-{session_hash}.json
# with contents like: {"reason": "Task complete, no further work needed"}
```

**Expected Results:**
- `STOP_FILE` triggers when the file is detected during any cycle
- Session hash is derived from session ID for security (agent must know the ID)

**Enabling Stop File Support:**

The `${STOP_FILE}` template variable is now available in prompts. Add this to your workflow's PROLOGUE to enable agent-initiated stops:

```conv
PROLOGUE @stop-file-instructions.md
```

Where `stop-file-instructions.md` contains:

```markdown
## Stop Automation Signal

If you detect you are in a repetitive loop, cannot make further progress, 
or the task requires human review, create a file named:

    ${STOP_FILE}

With JSON contents explaining why:

    {"reason": "Your explanation here", "needs_review": true}

This will gracefully stop the automation cycle.
```

The `${STOP_FILE}` variable is only substituted once per session (same value across all cycles), so including it in a PROLOGUE is efficient.

## Python CLI

The tool can also be run directly via Python:

```bash
python -m tests.integration.test_loop_stress --help
python -m tests.integration.test_loop_stress --adapter copilot --model gpt-4o elicit
python -m tests.integration.test_loop_stress --verbose all --cycles 5
```

## Output

### Console Summary

```
                             Loop Detection Stress Test Results                             
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Test                 ┃ Cycles ┃ SDK Abort ┃ LoopDetector                  ┃ Events File                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ repeated_prompt      │      5 │ —         │ ✓ minimal_response (cycle 5)  │ repeated_prompt_events.jsonl  │
│ explicit_loop_elicit │      1 │ —         │ ✓ reasoning_pattern (cycle 1) │ loop_elicit_events.jsonl      │
│ minimal_response     │      2 │ —         │ ✓ minimal_response (cycle 2)  │ minimal_response_events.jsonl │
└──────────────────────┴────────┴───────────┴───────────────────────────────┴───────────────────────────────┘
```

### JSONL Event Logs

Events are logged to `./loop-test-logs/*.jsonl` in JSONL format:

```jsonl
{"event_type": "assistant.reasoning", "timestamp": "2026-01-21T23:58:10", "data": {"content": "The user is asking me to pretend I'm in a loop..."}, "session_id": "abc123", "turn": 1}
{"event_type": "assistant.message", "timestamp": "2026-01-21T23:58:11", "data": {"content": "I notice I'm receiving the same request again..."}, "session_id": "abc123", "turn": 1}
```

## Findings from Testing (2026-01-22)

### Test Results Summary

| Test | Detection | Trigger Cycle | Notes |
|------|-----------|---------------|-------|
| **Loop Elicit** | `REASONING_PATTERN` | 1 | AI reasoning included "loop situation", matched our patterns |
| **Repeated Prompt** | `MINIMAL_RESPONSE` | 2+ | Responses only ~31 chars ("Acknowledged. Cycle N received.") |
| **Minimal Response** | `MINIMAL_RESPONSE` | 2 | "OK" response triggers short response detection |
| **Stop File** | `STOP_FILE` | Any | Agent creates `STOPAUTOMATION-{hash}.json` to signal stop |

### Key Observations

1. **Reasoning Pattern Detection Works**
   - When prompted to "respond as if in a loop", the AI's reasoning naturally includes phrases that match our patterns
   - The pattern `\bin a loop\b` successfully matched the AI's reasoning text
   - This is the most reliable way to detect when the AI itself recognizes a loop situation

2. **Minimal Response Detection Works**
   - The 100-char minimum threshold (raised from 50 in Q-002) reliably catches terse responses
   - Short acknowledgments like "Acknowledged. Cycle N received." (31 chars) trigger detection
   - This catches cases where the AI is giving up on providing useful content

3. **Identical Response Detection (Q-002 Fix Applied)**
   - Threshold lowered from 3 to 2 for faster loop detection
   - Now triggers on just 2 identical responses instead of waiting for 3
   - Original observation: responses varied slightly ("Cycle 1" vs "Cycle 2") so didn't trigger

4. **Stop File Detection (Q-002 Feature)**
   - Agent can create `STOPAUTOMATION-{session_hash}.json` to explicitly request stop
   - Session hash derived from session ID for security (prevents unauthorized stops)
   - File can include JSON with `{"reason": "..."}` for detailed stop reason
   - Cleaned up automatically after detection

5. **SDK Abort Events Not Observed**
   - No `abort` events were seen from the SDK in these tests
   - The SDK may not emit abort events for reasoning-based loop detection
   - Our client-side `LoopDetector` is the primary detection mechanism

### Default Configuration (Q-002 Thresholds)

After the Q-002 fix, these are the default thresholds:

| Setting | Default Value | Notes |
|---------|---------------|-------|
| `identical_threshold` | 2 | Triggers on 2 identical responses (was 3) |
| `min_response_length` | 100 | Responses <100 chars trigger (was 50) |
| `session_id` | None | Required for secure stop file naming |
| `stop_file_dir` | CWD | Directory to check for stop file |

### Template Variables for Stop File

These variables are available in prompts and prologues:

| Variable | Example Value | Notes |
|----------|---------------|-------|
| `${STOP_FILE}` | `STOPAUTOMATION-bd7065173b6b.json` | Full filename agent should create |
| `${SESSION_ID}` | `20260122-213045-abc123` | Session ID (useful for logging) |

### Recommendations

1. **For sdqctl cycle command**: Keep using `LoopDetector` as the primary loop detection mechanism
2. **For stricter detection**: Configure `LoopDetector(identical_threshold=1, min_response_length=150)`
3. **For agent-initiated stops**: Include `${STOP_FILE}` in a PROLOGUE to tell the agent the filename
4. **For research**: The `--event-log` output provides rich data for analyzing AI behavior

## Files

```
sdqctl/
├── tests/integration/
│   ├── __init__.py
│   └── test_loop_stress.py      # Main test tool
├── test-loop-stress.sh          # Shell wrapper
└── loop-test-logs/              # Output directory (gitignored)
    ├── repeated_prompt_events.jsonl
    ├── loop_elicit_events.jsonl
    └── minimal_response_events.jsonl
```

## Related

- `sdqctl/core/loop_detector.py` - The LoopDetector class being tested
- `sdqctl/core/exceptions.py` - LoopDetected exception and LoopReason enum
- `sdqctl/adapters/copilot.py` - EventCollector and abort event handling
- `docs/QUIRKS.md` - Q-002 documents the SDK abort event gap and client-side workarounds
