# Loop Detection Stress Test Tool

A stress testing tool for validating the Copilot SDK's abort/loop detection mechanisms.

## Overview

This tool tests four detection mechanisms in the `LoopDetector` class:

1. **REASONING_PATTERN** - Detects when the AI's reasoning contains loop-aware phrases like "in a loop", "repeated prompt", etc.
2. **IDENTICAL_RESPONSES** - Detects when 2 consecutive responses are identical (lowered from 3 in Q-002 fix)
3. **MINIMAL_RESPONSE** - Detects when responses become suspiciously short (<100 chars) after the first cycle. **Skipped if tools were called** (2026-01-26 fix for false positives on commit acknowledgments).
4. **STOP_FILE** - Detects when the agent creates a `STOPAUTOMATION-{nonce}.json` file to signal stop (✅ verified working)

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

## Test Types

### Automated Unit Tests (pytest)

The standard test suite (`pytest tests/`) includes **automated unit tests** for loop detection that run without API calls:

- `test_loop_detector.py` - Tests all 4 detection mechanisms with mock data
- `test_stop_file_existence_check.py` - Tests the "refuse to run if stop file exists" behavior

These run in CI and require no external dependencies.

### Manual Integration Tests (Live SDK)

The stress test tool (`tests/integration/test_loop_stress.py`) requires a **live Copilot SDK connection** for full verification:

```bash
# These make real API calls to the Copilot SDK
python -m tests.integration.test_loop_stress -v stopfile   # Verify agent creates stop file
python -m tests.integration.test_loop_stress -v elicit     # Verify loop-aware responses
python -m tests.integration.test_loop_stress -v repeated   # Verify identical response detection
```

Use `--adapter mock` for development without API calls (limited verification).

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
# Test stop file creation explicitly
python -m tests.integration.test_loop_stress -v stopfile --nonce testelicit01
```

**Expected Results:**
- Agent creates `STOPAUTOMATION-{nonce}.json` with JSON content
- `STOP_FILE` detection triggers when the file is detected during any cycle

**Verified Behavior (2026-01-22):**

The stop file mechanism has been **verified working** with the Copilot SDK (claude-sonnet-4-20250514 model via Copilot adapter):

1. **Agent receives instruction** - The stop file instruction is injected on first prompt
2. **Agent uses `create` tool** - Agent correctly uses the file creation tool
3. **File contains valid JSON** - Content matches the requested format
4. **Detection works** - LoopDetector finds and reads the file

Event log from successful test:
```
user.message: [STOP FILE CREATION TEST]... Create a stop file... STOPAUTOMATION-testelicit01.json
tool.execution_start: tool=create
assistant.message: Created `STOPAUTOMATION-testelicit01.json` with the requested JSON content.
```

Example verified test output:
```
✓ Stop file created!
Content: {
  "reason": "Stop file creation test - verifying agent can create automation stop signals",
  "needs_review": true,
  "test_id": "stop-file-elicit"
}
```

**Stop File Persistence:**

The stop file is **intentionally left in place** for human inspection. Subsequent runs will detect the existing file and refuse to continue until reviewed:

```
╭─────────────────── 🛑 Review Required ───────────────────╮
│ ⚠️  Stop file exists from previous run                   │
│                                                          │
│ File: STOPAUTOMATION-testelicit01.json                   │
│ Reason: ...                                              │
│                                                          │
│ A previous automation run requested human review.        │
│ Please review the agent's work before continuing.        │
│                                                          │
│ To continue: Remove the stop file and run again          │
│     rm STOPAUTOMATION-testelicit01.json                  │
╰──────────────────────────────────────────────────────────╯
```

**Default Behavior (Enabled by Default):**

Stop file instructions are now **automatically injected** on the first prompt of each session. The agent is told the exact filename to create. To disable:

```bash
# Disable automatic stop file instructions
sdqctl iterate workflow.conv --no-stop-file-prologue
sdqctl iterate workflow.conv --no-stop-file-prologue
sdqctl apply workflow.conv --components "*.py" --no-stop-file-prologue
```

**Manual Configuration (Legacy):**

If you've disabled the automatic injection, you can still use the `${STOP_FILE}` template variable in a custom PROLOGUE:

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
| `min_response_length` | 80 | Responses <80 chars trigger (configurable via `SDQCTL_MIN_RESPONSE_LENGTH`) |
| `nonce` | Random 12-char hex | For stop file naming (auto-generated) |
| `stop_file_dir` | CWD | Directory to check for stop file |

### Template Variables for Stop File

These variables are available in prompts and prologues:

| Variable | Example Value | Notes |
|----------|---------------|-------|
| `${STOP_FILE}` | `STOPAUTOMATION-a1b2c3d4e5f6.json` | Full filename agent should create |

### CLI Options

All commands support stop file configuration:

```bash
# Default: stop file instruction injected with random nonce
sdqctl iterate workflow.conv

# Disable stop file instruction
sdqctl iterate workflow.conv --no-stop-file-prologue

# Pin nonce for testing/reproducibility
sdqctl iterate workflow.conv --stop-file-nonce=testrun123
```

### Recommendations

1. **For sdqctl iterate command**: Keep using `LoopDetector` as the primary loop detection mechanism
2. **For stricter detection**: Configure `LoopDetector(identical_threshold=1, min_response_length=150)`
3. **For agent-initiated stops**: The `${STOP_FILE}` instruction is injected automatically on first prompt
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
