# Copilot SDK Debug/Logging Integration Tracker

**Analysis Date:** 2026-01-22  
**Source Document:** `sdqctl/COPILOT-SDK-INTEGRATION.md`  
**Focus:** Debugging and Logging Features (Phase 1)  
**Git Branch:** main

---

## Sprint Status Overview

| Sprint | Title | Status | Items Done |
|--------|-------|--------|------------|
| 1 | Intent Tracking & Exposure | ✅ Complete | 5/5 |
| 2 | Enhanced Tool Logging | ✅ Complete | 4/4 |
| 3 | Event Export (JSONL) | ✅ Complete | 5/5 |
| 4 | TRACE Level (-vvv) | ✅ Complete | 4/4 |
| 5 | Debug ConversationFile Directives | ✅ Complete | 5/5 |

---

## Sprint 1: Intent Tracking & Exposure ✅ COMPLETE

Enable tracking and exposing of `assistant.intent` events for debugging workflow progress.

- [x] Add `current_intent: Optional[str]` and `intent_history: list[dict]` to `SessionStats`
- [x] Capture `assistant.intent` events in `on_event()` and store in stats
- [x] Include intent history in JSON output when `--json` flag used
- [x] Add INFO logging for intent changes with 🎯 emoji
- [x] Add test in `tests/test_copilot_adapter.py` for intent tracking

**Files modified:**
- `sdqctl/adapters/copilot.py` (SessionStats fields, on_event handler, destroy_session logging)
- `sdqctl/commands/run.py` (adapter_stats in JSON output)
- `sdqctl/commands/cycle.py` (adapter_stats in JSON output)
- `tests/test_copilot_adapter.py` (test_intent_tracking)

---

## Sprint 2: Enhanced Tool Logging ✅ COMPLETE

Improve visibility into tool execution with timing and status tracking.

- [x] Add `active_tools: dict` to track in-flight tools with start time
- [x] Log tool arguments at DEBUG level (truncated to 500 chars)
- [x] Log tool completion with duration and ✓/✗ status
- [x] Add tool summary to session stats (total, succeeded, failed counts)

**Files modified:**
- `sdqctl/adapters/copilot.py` (SessionStats, tool event handlers with timing)
- `sdqctl/commands/run.py` (tool stats in JSON output)
- `sdqctl/commands/cycle.py` (tool stats in JSON output)
- `tests/test_copilot_adapter.py` (test_tool_execution_with_timing_and_status)

---

## Sprint 3: Event Export (JSONL) ✅ COMPLETE

Export all SDK events to JSONL file for offline analysis.

- [x] Create `EventRecord` dataclass with event_type, timestamp, data, session_id, turn
- [x] Create `EventCollector` class to accumulate events during session
- [x] Add `--event-log PATH` option to `run` and `cycle` commands
- [x] Write events to JSONL on session complete or error
- [x] Add test for event export format validation

**Files modified:**
- `sdqctl/adapters/copilot.py` (EventRecord, EventCollector, export_events)
- `sdqctl/commands/run.py` (--event-log option)
- `sdqctl/commands/cycle.py` (--event-log option)
- `tests/test_copilot_adapter.py` (TestEventCollector, TestCopilotAdapterEventExport)

---

## Sprint 4: TRACE Level (-vvv) ✅ COMPLETE

Add TRACE level logging for maximum visibility during debugging.

- [x] Define `TRACE = 5` level in `core/logging.py` with `logging.addLevelName()`
- [x] Update `setup_logging()` to set TRACE for `-vvv`
- [x] Route all SDK events (including UNKNOWN) to TRACE level
- [x] Document TRACE level in README.md

**Note:** Already implemented in previous session. TRACE level (5) exists in core/logging.py.

---

## Sprint 5: Debug ConversationFile Directives ✅ COMPLETE

Add ConversationFile directives for debug configuration.

- [x] Add `DEBUG` directive to DirectiveType enum (comma-separated categories)
- [x] Add `DEBUG-INTENTS` directive (true/false)
- [x] Add `EVENT-LOG` directive (path with {{DATETIME}} template vars)
- [x] Parse debug config in `ConversationFile.from_file()`
- [x] Pass debug config through to adapter

**Files modified:**
- `sdqctl/core/conversation.py` (DirectiveType enum, ConversationFile fields, parsing)
- `sdqctl/adapters/base.py` (AdapterConfig debug fields)
- `sdqctl/commands/run.py` (pass debug config to adapter)
- `sdqctl/commands/cycle.py` (pass debug config to adapter)
- `tests/test_conversation.py` (test_parse_debug_directives, test_parse_debug_intents_false)

---

## Next Three Work Items

| Priority | Sprint | Item | Rationale |
|----------|--------|------|-----------|
| - | - | All sprints complete | Phase 1 Debug/Logging features done |

---

## Barriers & Lessons

*None yet - tracker initialized 2026-01-22*

---

## Session History

### Session 3: Sprint 5 Complete (2026-01-22)
**Completed:** 
- Sprint 5: Debug ConversationFile Directives (5 items)
**Files modified:**
- `sdqctl/core/conversation.py` - DEBUG, DEBUG-INTENTS, EVENT-LOG directives
- `sdqctl/adapters/base.py` - AdapterConfig debug fields
- `sdqctl/commands/run.py` - pass debug config to adapter
- `sdqctl/commands/cycle.py` - pass debug config to adapter
- `tests/test_conversation.py` - 2 new tests for debug directives
**Tests:** 488 total tests passing
**Status:** Phase 1 (Debug/Logging Features) COMPLETE

### Session 2: Sprint 3 Complete (2026-01-22)
**Completed:** 
- Sprint 3: Event Export (JSONL) (5 items)
**Files modified:**
- `sdqctl/adapters/copilot.py` - EventRecord, EventCollector, export_events
- `sdqctl/commands/run.py` - --event-log option
- `sdqctl/commands/cycle.py` - --event-log option
- `tests/test_copilot_adapter.py` - TestEventCollector, TestCopilotAdapterEventExport (8 new tests)
**Tests:** 486 total tests passing

### Session 1: Sprints 1-2 Complete (2026-01-22)
**Completed:** 
- Sprint 1: Intent Tracking & Exposure (5 items)
- Sprint 2: Enhanced Tool Logging (4 items)
**Files modified:**
- `sdqctl/adapters/copilot.py` - Intent + tool tracking in SessionStats
- `sdqctl/commands/run.py` - adapter_stats in JSON output
- `sdqctl/commands/cycle.py` - adapter_stats in JSON output
- `tests/test_copilot_adapter.py` - intent + tool timing tests
**Tests:** 478 total tests passing

### Session 0: Tracker Initialization (2026-01-22)
**Completed:** Created tracker and workflow from COPILOT-SDK-INTEGRATION.md analysis
**Files created:**
- `examples/workflows/sdk-debug-integration.conv`
- `reports/sdk-debug-integration-tracker.md`

---

## Usage

Run the next iteration:
```bash
cd /path/to/sdqctl
sdqctl cycle examples/workflows/sdk-debug-integration.conv \
  --prologue reports/sdk-debug-integration-tracker.md \
  --adapter copilot
```

Preview prompts without execution:
```bash
sdqctl cycle examples/workflows/sdk-debug-integration.conv \
  --prologue reports/sdk-debug-integration-tracker.md \
  --render-only
```
