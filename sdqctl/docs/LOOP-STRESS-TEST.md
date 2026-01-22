# Loop Detection Stress Test Tool

A stress testing tool for validating the Copilot SDK's abort/loop detection mechanisms.

## Overview

This tool tests three detection mechanisms in the `LoopDetector` class:

1. **REASONING_PATTERN** - Detects when the AI's reasoning contains loop-aware phrases like "in a loop", "repeated prompt", etc.
2. **IDENTICAL_RESPONSES** - Detects when N consecutive responses are identical
3. **MINIMAL_RESPONSE** - Detects when responses become suspiciously short after the first cycle

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
- `MINIMAL_RESPONSE` triggers on cycle 2

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

### Key Observations

1. **Reasoning Pattern Detection Works**
   - When prompted to "respond as if in a loop", the AI's reasoning naturally includes phrases that match our patterns
   - The pattern `\bin a loop\b` successfully matched the AI's reasoning text
   - This is the most reliable way to detect when the AI itself recognizes a loop situation

2. **Minimal Response Detection Works**
   - The 50-char minimum threshold reliably catches terse responses
   - Short acknowledgments like "Acknowledged. Cycle N received." (31 chars) trigger detection
   - This catches cases where the AI is giving up on providing useful content

3. **Identical Response Detection Needs Tuning**
   - With 5 cycles, responses varied slightly ("Cycle 1" vs "Cycle 2") so didn't trigger
   - May need more cycles or prompt engineering to get truly identical responses
   - Consider lowering threshold from 3 to 2 for stricter detection

4. **SDK Abort Events Not Observed**
   - No `abort` events were seen from the SDK in these tests
   - The SDK may not emit abort events for reasoning-based loop detection
   - Our client-side `LoopDetector` is the primary detection mechanism

### Recommendations

1. **For sdqctl cycle command**: Keep using `LoopDetector` as the primary loop detection mechanism
2. **For strict detection**: Configure `LoopDetector(identical_threshold=2, min_response_length=100)`
3. **For research**: The `--event-log` output provides rich data for analyzing AI behavior

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
