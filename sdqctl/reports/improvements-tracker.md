# sdqctl Improvements Tracker

**Analysis Date:** 2026-01-21  
**Git Branch:** main  
**Test Status:** 357/357 passing

---

## Completed Items (2026-01-21)

### ✅ P1-2: Context Files Now Filtered by Restrictions - COMPLETED
- Added `path_filter` parameter to ContextManager
- Session passes FileRestrictions.is_path_allowed as filter
- Context loading now respects ALLOW-FILES/DENY-FILES directives
- Added 6 tests in `tests/test_context.py`:
  - Path filter denies specific files
  - Path filter with glob patterns
  - Session respects deny patterns
  - Session respects allow patterns

### ✅ P1-1: Resource Leak in Error Paths - COMPLETED
- Restructured `run.py` with nested try/finally for proper session cleanup
- Restructured `cycle.py` with same pattern
- destroy_session() now called in finally block (handles both success and error paths)
- Early returns no longer manually call cleanup (handled by finally)

### ✅ P0-2: Shell Injection Vulnerability Fixed - COMPLETED
- Added `ALLOW-SHELL` directive (default: false for security)
- RUN directive now uses `shlex.split()` by default (no shell injection possible)
- Shell features (pipes, redirects) require explicit `ALLOW-SHELL true`
- Added 9 tests in `tests/test_run_command.py`:
  - ALLOW-SHELL parsing (true, yes, false, no, bare)
  - shlex.split behavior verification
  - Shell injection prevention tests

### ✅ P0-1: Config File Loading - COMPLETED
- Added `sdqctl/core/config.py` with `load_config()` function
- Searches: cwd → parent dirs (stops at git root) → ~/.sdqctl.yaml
- Config values provide defaults for adapter, model, context_limit
- ConversationFile now uses `default_factory` to load config-based defaults
- Added `tests/test_config.py` with 23 tests covering:
  - Config parsing from YAML
  - Search path resolution
  - Caching behavior
  - Helper functions
  - Integration with ConversationFile

### ✅ P0-3: CLI Integration Tests - COMPLETED
- Added `tests/test_cli.py` with 22 tests covering CLI entry points
- Added `tests/test_run_command.py` with 18 tests for step execution  
- Added `tests/test_cycle_command.py` with 15 tests for multi-cycle workflows
- Added `tests/test_flow_command.py` with 15 tests for parallel execution
- Added `tests/test_apply_command.py` with 17 tests for component iteration
- Total test coverage increased from 109 to 196 tests

### ✅ P1-5: Copilot Adapter Tests - COMPLETED
- Added `tests/test_copilot_adapter.py` with 25 tests covering:
  - Adapter initialization and lifecycle
  - Session creation/destruction
  - Message sending and event handling
  - Token usage accumulation
  - Tool call tracking
  - Context usage estimation

### ✅ P2-7: Status Command Tests - COMPLETED
- Added `tests/test_status_command.py` with 21 tests covering:
  - Overview display and JSON output
  - Adapter listing
  - Session enumeration
  - Checkpoint details
  - Edge cases (corrupted files, empty dirs)

### ✅ P2-8: Logging Configuration Tests - COMPLETED  
- Added `tests/test_logging.py` with 28 tests covering:
  - TRACE level setup
  - Verbosity levels (0=WARNING, 1=INFO, 2=DEBUG, 3=TRACE)
  - Quiet mode
  - Log format at different levels
  - Handler configuration
  - Module logger inheritance

### ✅ P2-9: Progress Module Tests - COMPLETED
- Added `tests/test_progress.py` with 28 tests covering:
  - Quiet mode functionality
  - progress() function output
  - Helper functions (progress_step, progress_file, progress_done)
  - progress_timer context manager
  - ProgressTracker class (start, step, checkpoint, done)
  - Integration with quiet mode

### ✅ P2-10: Adapter Registry Tests - COMPLETED
- Added `tests/test_registry.py` with 21 tests covering:
  - register_adapter() function
  - get_adapter() with lazy loading
  - list_adapters() discovery
  - Error handling for unknown adapters
  - Built-in adapter loading (mock, copilot)
  - Integration with async methods

### ✅ P1-3: File Reference Warning - COMPLETED
- Added warning logging for unresolved `@file` references in `conversation.py`
- Users now get log warning: "File reference not found: @path (resolved to /full/path)"

### ✅ P1-4: Checkpoint Restore Diagnostics - COMPLETED
- Added diagnostic info to checkpoint restore errors in `session.py`
- Error now includes: "Conversation file not found: /path/to/file (checkpoint: /path/to/checkpoint)"

### ✅ P2-2: Template Variable Documentation - COMPLETED
- Synced README.md template variables with docstring in conversation.py
- Added 6 missing variables: WORKFLOW_PATH, COMPONENT_PATH, COMPONENT_DIR, COMPONENT_TYPE, CYCLE_NUMBER, CYCLE_TOTAL

### ✅ Code Quality Fixes - COMPLETED
- Fixed type hint `any` → `Any` in `adapters/copilot.py` line 85
- Removed dead code: unused `cli_restrictions` variable in `commands/run.py` lines 213-218
- Added `pytest-cov` to dev dependencies in `pyproject.toml`
- Added CLI test fixtures to `tests/conftest.py`

---

## Next Three Highest Priority Work Areas

### 1. No Retry Logic (P1)
**Files:** `adapters/copilot.py`, `commands/run.py`  
**Issue:** Network errors and transient failures cause immediate failure

**Recommendation:** Add configurable retry with exponential backoff.

### 2. RUN Directive Timeout Hardcoded (P2)
**File:** `sdqctl/commands/run.py` line 448
**Issue:** RUN directive uses hardcoded 60s timeout

**Recommendation:** Add RUN-TIMEOUT directive or configuration option.

### 3. Progress Tracker File Format Not Documented (P2)
**File:** `sdqctl/commands/apply.py`, lines 341-431  
**Issue:** The `ProgressTracker` class writes markdown but format isn't documented

**Recommendation:** Add format documentation to README.md or add JSON output option.

---

## Detailed Findings

### P0 - Critical Issues

#### P0-1: Config File Not Loaded ✅ FIXED
**File:** `sdqctl/cli.py` lines 83-127 vs `sdqctl/core/config.py`  
**Issue:** Config file created but never loaded

**Resolution:** Added `sdqctl/core/config.py` with full config loading. ConversationFile now uses config defaults.

#### P0-2: Shell Injection in RUN Directive ✅ FIXED
**File:** `sdqctl/commands/run.py` lines 437-455  
**Issue:** `shell=True` with untrusted command content

**Resolution:** Added `ALLOW-SHELL` directive (default false). RUN now uses `shlex.split()` by default. Shell features require explicit opt-in.

#### P0-3: Missing CLI Integration Tests
**Files:** `tests/` directory  
**Issue:** No tests for CLI entry points

The CLI layer (`cli.py`, commands/*) handles argument parsing, async orchestration, and output formatting but has zero test coverage. A bug in these layers would ship undetected.

**Evidence:**
- `test_conversation.py` - 36 tests for parser only
- `test_session.py` - 30 tests for session state only  
- `test_context.py` - 27 tests for context manager only
- `test_adapters.py` - 20 tests for mock adapter only
- No tests for: `run`, `cycle`, `flow`, `apply`, `status`, `init`, `validate`, `show`, `resume`

**Recommendation:** Create `tests/test_cli.py` with Click test runner patterns.

---

### P1 - High Priority Issues

#### P1-1: Resource Leak in Adapter Error Paths ✅ FIXED
**File:** `sdqctl/commands/run.py`, `sdqctl/commands/cycle.py`  
**Issue:** Adapter sessions may leak if create_session() fails

**Resolution:** Restructured with nested try/finally. destroy_session() now in finally block.

**Recommendation:** Add nested try/finally for session lifecycle.

#### P1-2: RUN Directive Error Recovery
**File:** `sdqctl/commands/run.py`, lines 489-498  
**Issue:** RUN-ON-ERROR "continue" works, but timeout path doesn't capture partial output

```python
except subprocess.TimeoutExpired:
    logger.error(f"  ✗ Command timed out")
    progress(f"  ✗ Command timed out")
    
    if conv.run_on_error == "stop":
        # ... stops execution
    # ELSE: continues but no output captured, no context for AI
```

When `run_on_error == "continue"`, the code path after timeout doesn't capture or log partial output.

**Recommendation:** Capture partial stdout/stderr from timed-out process.

#### P1-3: build_prompt_with_injection File Reference Errors ✅ FIXED
**File:** `sdqctl/core/conversation.py`, lines 424-445  
**Issue:** `resolve_content_reference` silently returns original `@path` if file not found

**Resolution:** Added warning logging: "File reference not found: @path (resolved to /full/path)"

#### P1-4: Session Checkpoint Restore Missing Error Context ✅ FIXED
**File:** `sdqctl/core/session.py`, lines 206-239  
**Issue:** `load_from_pause` raises generic ValueError without diagnostic info

**Resolution:** Error now includes: "Conversation file not found: /path/to/file (checkpoint: /path/to/checkpoint)"

#### P1-5: Copilot Adapter Not Tested ✅ FIXED
**File:** `sdqctl/adapters/copilot.py`  
**Issue:** Copilot adapter exists but has no tests

**Resolution:** Added `tests/test_copilot_adapter.py` with 25 mocked tests covering initialization, lifecycle, sessions, events, and stats.

#### P1-6: Unused cli_restrictions Variable ✅ FIXED
**File:** `sdqctl/commands/run.py` lines 213-218  
**Issue:** `cli_restrictions` created but never used

**Resolution:** Removed dead code - the variable was created but merge_with_cli was called with raw lists instead.

---

### P2 - Medium Priority Issues

#### P2-1: Progress Tracker File Format Not Documented
**File:** `sdqctl/commands/apply.py`, lines 341-431  
**Issue:** The `ProgressTracker` class writes markdown but format isn't documented

Users may want to parse this programmatically but have no schema reference.

**Recommendation:** Add format documentation to README.md or add JSON output option.

#### P2-2: Template Variable Documentation Incomplete
**File:** `sdqctl/core/conversation.py`, lines 394-408  
**Issue:** `get_standard_variables` docstring lists variables, but README.md table is subset

The docstring lists `GIT_BRANCH`, `GIT_COMMIT`, `CWD`, etc. but README.md table may be incomplete.

**Recommendation:** Ensure README.md and docstring are synchronized.

#### P2-3: Context Manager Token Estimation Inaccurate
**File:** `sdqctl/core/context.py`, lines 112-113  
**Issue:** Token estimation uses `len(content) // 4` which is rough approximation

```python
# Line 112-113
# Estimate tokens (rough: 4 chars per token)
tokens = len(content) // 4
```

This can be 2-3x off for non-English text or code with many symbols.

**Recommendation:** Use tiktoken library for accurate GPT tokenization, or document limitation.

#### P2-4: FileRestrictions.is_path_allowed Edge Cases
**File:** `sdqctl/core/conversation.py`, lines 101-136  
**Issue:** `relative_to` can fail on paths that don't share a common ancestor

The test suite only covers simple cases. Complex relative path scenarios may fail silently.

**Recommendation:** Add edge case tests for absolute vs relative paths, symlinks.

#### P2-5: Missing pytest-cov Dependency
**File:** `pyproject.toml`, lines 41-45  
**Issue:** `dev` dependencies don't include `pytest-cov` for coverage reporting

```toml
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
```

**Recommendation:** Add `pytest-cov>=4.0` to dev dependencies. ✅ DONE

#### P2-6: Adapter Registry Extensibility
**File:** `sdqctl/adapters/registry.py`  
**Issue:** No plugin mechanism for adding custom adapters

Users cannot register their own adapters without modifying source code.

**Recommendation:** Add entry_points or config-based adapter registration.

---

## Test Coverage Gap Analysis

| Module | Tests | Coverage Estimate | Gap |
|--------|-------|-------------------|-----|
| `core/conversation.py` | 36 | ~85% | Multiline edge cases |
| `core/context.py` | 27 | ~90% | Binary file handling |
| `core/session.py` | 30 | ~80% | Error recovery paths |
| `core/logging.py` | 28 | ~95% | None significant |
| `core/progress.py` | 28 | ~95% | None significant |
| `adapters/mock.py` | 20 | ~95% | None significant |
| `adapters/copilot.py` | 25 | ~75% | Real SDK integration |
| `adapters/registry.py` | 21 | ~90% | Plugin entry points |
| `commands/run.py` | 18 | ~40% | RUN subprocess paths |
| `commands/cycle.py` | 15 | ~60% | Compaction triggers |
| `commands/flow.py` | 15 | ~60% | Error aggregation |
| `commands/apply.py` | 17 | ~65% | Progress file edge cases |
| `commands/status.py` | 21 | ~85% | None significant |
| `cli.py` | 22 | ~60% | Entry points covered |

**Total estimate:** ~80% code coverage (improved from ~75%)

---

## Recommended Test Additions (Priority Order)

1. ~~**`tests/test_cli.py`** - CLI command integration tests using Click test runner~~ ✅ DONE (22 tests)
2. ~~**`tests/test_run.py`** - `sdqctl run` command with mock adapter~~ ✅ DONE (18 tests)
3. ~~**`tests/test_cycle.py`** - Multi-cycle workflow tests~~ ✅ DONE (15 tests)
4. ~~**`tests/test_apply.py`** - Component iteration tests~~ ✅ DONE (17 tests)
5. ~~**`tests/test_flow.py`** - Parallel execution tests~~ ✅ DONE (15 tests)
6. ~~**`tests/test_copilot_adapter.py`** - Mocked Copilot SDK tests~~ ✅ DONE (25 tests)
7. ~~**`tests/test_status_command.py`** - Status command output~~ ✅ DONE (21 tests)
8. ~~**`tests/test_logging.py`** - Logging configuration~~ ✅ DONE (28 tests)
9. ~~**`tests/test_progress.py`** - Progress module tests~~ ✅ DONE (28 tests)
10. ~~**`tests/test_registry.py`** - Adapter registry tests~~ ✅ DONE (21 tests)

**All recommended tests completed!**

---

## Architecture Observations

### Strengths
- Clean separation between core (conversation, context, session) and adapters
- Good use of dataclasses for structured data
- Comprehensive ConversationFile directive support
- Template variable system is flexible

### Areas for Improvement
- CLI commands duplicate async patterns - consider abstracting
- Error handling could be more consistent (some raise, some log and continue)
- No structured logging (currently uses `get_logger` but no structured fields)

---

## References

- `INTEGRATION-PROPOSAL.md` - workspace/verify/trace command proposal
- `TEST-PLAN.md` - Manual testing scenarios
- `examples/workflows/verify-with-run.conv` - RUN directive example

---

## Non-Test Improvements (Moved from Test Analysis)

### Architecture Improvements

#### A1: Async Pattern Duplication (P2)
**Files:** `commands/run.py`, `commands/cycle.py`, `commands/flow.py`, `commands/apply.py`  
**Issue:** Each command duplicates the async runner pattern:
```python
def command(...):
    asyncio.run(_command_async(...))

async def _command_async(...):
    # actual implementation
```

**Recommendation:** Create shared async wrapper decorator or context manager.

#### A2: Missing Structured Logging (P2)
**File:** `sdqctl/core/logging.py`, lines 30-85  
**Issue:** Logger uses string interpolation without structured fields

Current:
```python
logger.info(f"Session complete: {stats.turns} turns, ...")
```

Better:
```python
logger.info("Session complete", extra={"turns": stats.turns, ...})
```

**Recommendation:** Add structured logging support for JSON log aggregation.

#### A3: Progress/Logging Confusion (P2)
**Files:** `core/progress.py` (stdout), `core/logging.py` (stderr)  
**Issue:** Two parallel output systems can be confusing

- `progress()` → stdout for user-facing messages
- `logger.info()` → stderr for diagnostics

**Recommendation:** Document distinction clearly, or unify under single system.

### Code Quality Improvements

#### Q1: Type Hints Incomplete ✅ FIXED
**File:** `sdqctl/adapters/copilot.py`, line 85  
**Issue:** `sessions: dict[str, any]` uses lowercase `any` (should be `Any`)

**Resolution:** Fixed to `dict[str, Any]` with proper import.

#### Q2: Magic Numbers (P2)
**File:** `sdqctl/core/context.py`, line 31  
**Issue:** Default max_tokens hardcoded as 128000

```python
# Line 31
max_tokens: int = 128000  # Default for modern models
```

**Recommendation:** Move to configuration constant or config file.

#### Q3: Subprocess Timeout Hardcoded (P2)
**File:** `sdqctl/commands/run.py`, line 248  
**Issue:** RUN directive uses hardcoded 60s timeout

```python
# Line 248
timeout=60,  # Default timeout
```

**Recommendation:** Add RUN-TIMEOUT directive or configuration option.

### Feature Gaps

#### F1: No Retry Logic (P1)
**Files:** `adapters/copilot.py`, `commands/run.py`  
**Issue:** Network errors and transient failures cause immediate failure

**Recommendation:** Add configurable retry with exponential backoff.

#### F2: No Metrics Collection (P2)
**File:** All command files  
**Issue:** No timing/success metrics captured for analysis

**Recommendation:** Add optional metrics output (timings, token usage, etc.)

#### F3: No Config File Support ✅ FIXED
**File:** `sdqctl/core/config.py`  
**Issue:** `sdqctl init` creates `.sdqctl.yaml` but it's not loaded

**Resolution:** Implemented full config loading with search paths (cwd → parents → home).

---

## Implementation Quality Review

**Review Date:** 2026-01-21

### Code Quality Metrics

| Metric | Status | Notes |
|--------|--------|-------|
| Type hints | Partial | Some `any` instead of `Any`, missing in places |
| Docstrings | Good | Most public functions documented |
| Error handling | Inconsistent | Mix of raise, log, and silent failures |
| Resource cleanup | Has gaps | Adapter sessions can leak on error |
| Security | Has issues | Shell injection in RUN directive |

### Specific Code Quality Issues

#### IQ-1: Inconsistent Error Handling Patterns (P1)
**Files:** Multiple command files  

Commands handle errors differently:
- `run.py` L280-285: Catches ValueError, prints, continues with mock
- `cycle.py` L110-115: Same pattern
- `flow.py` L106-110: Same pattern  

But:
- `apply.py` L202-207: Catches ValueError, uses mock
- Session errors: Raised to user

**Recommendation:** Define consistent error handling policy.

#### IQ-2: Duplicate Pattern Detection (P2)
**Files:** All command files

Every command has identical boilerplate:

```python
@click.command("name")
def name(...):
    asyncio.run(_name_async(...))

async def _name_async(...):
    # Get adapter with fallback
    try:
        ai_adapter = get_adapter(conv.adapter)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        ai_adapter = get_adapter("mock")
    
    try:
        await ai_adapter.start()
        adapter_session = await ai_adapter.create_session(...)
        # work
    finally:
        await ai_adapter.stop()
```

**Recommendation:** Extract to shared async_command decorator or context manager.

#### IQ-3: Progress vs Logger Redundancy (P2)
**File:** `sdqctl/commands/run.py` lines 327-328

```python
logger.info(f"Sending prompt {prompt_count}/{total_prompts}...")
progress(f"  Step {prompt_count}/{total_prompts}: Sending prompt...")
```

Same info logged twice to different streams.

**Recommendation:** Decide on primary output channel, use the other only for debugging.

#### IQ-4: Steps Processing Inconsistency (P1)
**File:** `sdqctl/commands/run.py` lines 314-320

```python
steps_to_process = conv.steps if conv.steps else [
    {"type": "prompt", "content": p} for p in conv.prompts
]

for step in steps_to_process:
    step_type = step.type if hasattr(step, 'type') else step.get('type')
    step_content = step.content if hasattr(step, 'content') else step.get('content', '')
```

Mixed handling of dataclass `ConversationStep` vs dict creates fragile duck typing.

**Recommendation:** Ensure `conv.steps` is always a list of `ConversationStep` objects.

#### IQ-5: Verbose Flag Ignored (P2)
**File:** `sdqctl/commands/run.py` line 105, 122

```python
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(..., verbose: bool, ...):
```

The `verbose` parameter is accepted but **never used** in the function body. Verbosity is controlled by the global `-v` flag instead.

**Recommendation:** Remove the duplicate `--verbose` flag from individual commands, or document that it's deprecated.

#### IQ-6: Context Files Not Filtered by Restrictions ✅ FIXED
**File:** `sdqctl/core/session.py`, `sdqctl/core/context.py`

**Resolution:** Added path_filter to ContextManager. Session now passes FileRestrictions.is_path_allowed as filter.

**Recommendation:** Apply file restrictions when loading context.

### Security Considerations

| Issue | Severity | Location | Status |
|-------|----------|----------|--------|
| Shell injection | High | `run.py` shell=True | ✅ FIXED - ALLOW-SHELL opt-in |
| Path traversal | Medium | Context pattern resolution | Open |
| Config injection | Low | No validation of .conv files |

### Maintainability Score: B-

**Strengths:**
- Clear module separation
- Consistent naming conventions
- Good use of dataclasses
- Comprehensive directive support

**Weaknesses:**
- Dead code (`cli_restrictions` variable)
- Duplicate patterns across commands
- Inconsistent error handling
- Security vulnerabilities
- Config file not implemented
