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
| 3 | Event Export (JSONL) | ⏳ In Progress | 0/5 |
| 4 | TRACE Level (-vvv) | ⏳ Pending | 0/4 |
| 5 | Debug ConversationFile Directives | ⏳ Pending | 0/5 |

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

## Sprint 3: Event Export (JSONL) ⏳

Export all SDK events to JSONL file for offline analysis.

**Current state:** Events are logged but not persisted in structured format.

- [ ] Create `EventRecord` dataclass with event_type, timestamp, data, session_id, turn
- [ ] Create `EventCollector` class to accumulate events during session
- [ ] Add `--event-log PATH` option to `run` and `cycle` commands
- [ ] Write events to JSONL on session complete or error
- [ ] Add test for event export format validation

**Files to modify:**
- `sdqctl/adapters/copilot.py` (EventRecord, EventCollector)
- `sdqctl/commands/run.py` (--event-log option)
- `sdqctl/commands/cycle.py` (--event-log option)

---

## Sprint 4: TRACE Level (-vvv) ⏳

Add TRACE level logging for maximum visibility during debugging.

**Current state:** -vv gives DEBUG, but no way to see all SDK events.

- [ ] Define `TRACE = 5` level in `core/logging.py` with `logging.addLevelName()`
- [ ] Update `setup_logging()` to set TRACE for `-vvv`
- [ ] Route all SDK events (including UNKNOWN) to TRACE level
- [ ] Document TRACE level in README.md

**Files to modify:**
- `sdqctl/core/logging.py` (TRACE level, setup_logging)
- `sdqctl/adapters/copilot.py` (use TRACE for verbose events)
- `README.md` (documentation)

---

## Sprint 5: Debug ConversationFile Directives ⏳

Add ConversationFile directives for debug configuration.

**Current state:** Debug options only available via CLI flags.

- [ ] Add `DEBUG` directive to DirectiveType enum (comma-separated categories)
- [ ] Add `DEBUG-INTENTS` directive (true/false)
- [ ] Add `EVENT-LOG` directive (path with {{DATETIME}} template vars)
- [ ] Parse debug config in `ConversationFile.from_file()`
- [ ] Pass debug config through to adapter

**Files to modify:**
- `sdqctl/core/conversation.py` (DirectiveType, parsing)
- `sdqctl/adapters/base.py` (AdapterConfig debug fields)
- `sdqctl/adapters/copilot.py` (use debug config)

---

## Next Three Work Items

| Priority | Sprint | Item | Rationale |
|----------|--------|------|-----------|
| 1 | 3 | Create EventRecord dataclass | Foundation for event capture |
| 2 | 3 | Add EventCollector class | Accumulates events for export |
| 3 | 3 | Add --event-log CLI option | User-facing feature |

---

## Barriers & Lessons

*None yet - tracker initialized 2026-01-22*

---

## Session History

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
