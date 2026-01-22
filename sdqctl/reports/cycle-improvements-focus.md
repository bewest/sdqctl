# Cycle Command Improvements - Topic Focus

**Topic:** `sdqctl cycle` command session management  
**Source:** User feedback + code analysis  
**Created:** 2026-01-21  
**Status:** Complete (C1 ✅, T1 ✅, E1 ✅, Q1 ✅)

---

## What is the Cycle Command?

The `cycle` command runs multi-cycle workflows with different session management strategies:

```bash
sdqctl cycle workflow.conv -n 5 --session-mode fresh
sdqctl cycle workflow.conv --session-mode compact
sdqctl cycle workflow.conv --session-mode accumulate  # currently called 'shared'
```

**Implementation:** `sdqctl/commands/cycle.py`  
**Session Management:** `sdqctl/core/session.py`  
**Context Loading:** `sdqctl/core/context.py`

---

## Scope Boundaries

### In Scope
- Session mode semantics (fresh, compact, accumulate)
- Context file reloading between cycles
- Mode naming clarity
- Testing of session mode behavior

### Out of Scope (for this topic)
- RUN directive execution (separate topic)
- Compaction algorithm details
- Checkpoint persistence format
- Adapter-specific session handling

---

## Current Behavior Analysis

### Session Modes

| Mode | CLI Name | Intended Behavior | Current Implementation |
|------|----------|-------------------|------------------------|
| **Accumulate** | `accumulate` | Context grows, compact only when limit reached | ✅ Works correctly |
| **Compact** | `compact` | Summarize after each cycle, stay in same session | ✅ Works correctly |
| **Fresh** | `fresh` | Start completely new session each cycle | ✅ Fixed - reloads CONTEXT files |

### Fresh Mode Gaps

**What currently happens on "fresh" (cycle.py lines 190-195, 232-236):**
1. ✅ Destroy old adapter session, create new one
2. ✅ Re-inject context via `session.context.get_context_content()`
3. ❌ **CONTEXT files NOT re-read from disk** (cached at Session.__init__)
4. ✅ Prologues/epilogues ARE re-read (resolved in `build_prompt_with_injection`)

**User expectation:**
- "Fresh" should be equivalent to running `sdqctl run` from scratch
- Any files modified during cycle N should be visible in cycle N+1
- CONTEXT files (from `CONTEXT @reports/tracker.md` directive) should refresh

---

## Improvement Chunks

Work is organized by complexity. Complete one chunk before moving to the next.

### 1. Correctness (C)

#### C1: Fresh Mode Should Reload CONTEXT Files ✅

**Current State:**
- `Session.__init__()` loads CONTEXT files once (session.py lines 92-94)
- `session.context.files` cached for entire run
- Fresh mode gets stale file contents

**Technical Details:**
```python
# session.py lines 92-94 - only called once at Session creation
for pattern in conversation.context_files:
    self.context.add_pattern(pattern)
```

**Required Changes:**
1. Add `Session.reload_context()` method that clears and reloads files
2. Call `reload_context()` at start of each cycle in fresh mode
3. Preserve ContextManager config (base_path, limit_threshold, path_filter)

**Files to Modify:**
- `sdqctl/core/session.py`: Add `reload_context()` method (~10 lines)
- `sdqctl/commands/cycle.py`: Call on fresh mode cycles (~3 lines)

**Test Cases:**
- CONTEXT file modified during cycle → visible in next cycle (fresh mode)
- CONTEXT file modified during cycle → NOT visible (compact/accumulate mode)

**Acceptance Criteria:**
- [x] `reload_context()` method exists
- [x] Fresh mode calls it at cycle start
- [x] Integration test validates file refresh

---

### 2. Ergonomics (E)

#### E1: Rename 'shared' to 'accumulate' 

**Current State:**
- `--session-mode` accepts: `shared`, `compact`, `fresh`
- "shared" is unclear - sounds like multi-user sharing
- "accumulate" better describes context growth behavior

**Required Changes:**
1. Rename option value in click decorator
2. Update variable name in code
3. Update docstring and help text
4. Update tests
5. Update documentation

**Files to Modify:**
- `sdqctl/commands/cycle.py`: ~8 occurrences of "shared"
- `sdqctl/cli.py`: Help text if referenced
- `tests/test_cycle_command.py`: Test fixtures
- `examples/workflows/README.md`: Documentation

**Breaking Change:** Yes - existing scripts using `--session-mode shared` will break

**Migration Path:** Log deprecation warning if "shared" used, accept as alias for 6 months

**Acceptance Criteria:**
- [x] `accumulate` is the documented mode name
- [x] `shared` removed (breaking change as decided)
- [x] Tests updated

---

### 3. Code Quality (Q)

#### Q1: Document Session Mode Semantics

**Current State:**
- Mode differences scattered in code comments
- No single source of truth for behavior

**Required Changes:**
1. Add comprehensive docstring to `_cycle_async()`
2. Add SESSION_MODES constant with documentation
3. Update README with clear mode comparison

**Files to Modify:**
- `sdqctl/commands/cycle.py`: Docstring expansion
- `README.md`: Session modes documentation section

**Acceptance Criteria:**
- [x] Each mode has clear documented behavior
- [x] README has comparison table

---

### 4. Testing (T)

#### T1: Session Mode Integration Tests

**Current State:**
- Basic dry-run tests exist
- No tests for actual file refresh behavior
- No tests validating mode semantics

**Required Tests:**
```python
class TestCycleSessionModes:
    async def test_fresh_mode_reloads_context_files(self):
        """Fresh mode should see file changes between cycles."""
        
    async def test_accumulate_mode_preserves_context(self):
        """Accumulate mode maintains conversation history."""
        
    async def test_compact_mode_summarizes_between_cycles(self):
        """Compact mode reduces context via summarization."""
        
    async def test_fresh_mode_reinjects_prologue(self):
        """Fresh mode sends prologue on every cycle."""
```

**Files to Modify:**
- `tests/test_cycle_command.py`: Add session mode tests

**Acceptance Criteria:**
- [x] Each mode has dedicated test
- [x] File refresh behavior verified for fresh mode

---

## Priority Order

1. **C1**: Fresh mode context reload - core correctness issue
2. **T1**: Tests - validate the fix works
3. **E1**: Rename shared → accumulate - clarity
4. **Q1**: Documentation - long-term maintainability

---

## Session Tracking

### Current Session
- **Date:** 2026-01-21/2026-01-22
- **Focus:** Q1 Implementation - Document Session Mode Semantics
- **Status:** ✅ All tasks complete!

### Completed Items
- [x] Analyzed cycle.py implementation
- [x] Identified fresh mode gap (context files not reloaded)
- [x] Clarified scope with user (reload CONTEXT files, not .conv)
- [x] Confirmed naming change: shared → accumulate
- [x] **C1: Implemented `reload_context()` method** (session.py:96-106)
- [x] **C1: Added call in fresh mode** (cycle.py:277)
- [x] **T1 (partial): Added unit tests for reload_context** (test_session.py:345-393)
- [x] **T1: Added session mode integration tests** (test_cycle_command.py:193-277)
- [x] **Bugfix: Extended mock adapter responses** (mock.py:27-31) - fixed loop detector triggering
- [x] **E1: Renamed 'shared' → 'accumulate'** (cycle.py:35-36, 78-79, 294-295, 335-336)
- [x] **E1: Updated tests** (test_cycle_command.py - 4 occurrences)
- [x] **Q1: Added module docstring with session mode docs** (cycle.py:1-19)
- [x] **Q1: Added SESSION_MODES constant** (cycle.py:44-48)
- [x] **Q1: Enhanced _cycle_async docstring** (cycle.py:171-182)
- [x] **Q1: Added README session modes section** (README.md:276-294)

### Remaining Work
- [x] Q1: Update documentation (README session modes section) ✅

### Git Commits (2026-01-22)
- `e2dd4f6` feat(cycle): implement session mode improvements (C1, T1, E1)
- `9d3dd6c` docs: update cycle improvements focus and progress
- `0719614` chore: disable heavy CONTEXT files in progress-tracker workflow

---

## Lessons Learned

### Analysis Phase
- **Finding:** Prologues/epilogues already work correctly for fresh mode
  - `resolve_content_reference()` called on every prompt in loop
  - Only CONTEXT files (from CONTEXT directive) are cached
  
- **Finding:** The gap is specifically `Session.__init__` loading files once
  - Fix is localized to session.py + cycle.py
  - Low complexity change (~15-20 lines)

### Implementation Phase (2026-01-22)
- **C1 Implementation:** Added `reload_context()` method that:
  - Uses existing `clear_files()` to remove cached files
  - Re-reads patterns from `self.conversation.context_files`
  - Preserves conversation token count (not cleared by `clear_files()`)
  
- **Key files modified:**
  - `sdqctl/core/session.py:96-106` - new `reload_context()` method
  - `sdqctl/commands/cycle.py:277` - call in fresh mode block
  - `tests/test_session.py:345-393` - 2 new tests

- **T1 Implementation:** Added session mode integration tests:
  - 5 new tests in `TestCycleSessionModes` class (test_cycle_command.py:193-277)
  - Tests verify fresh, compact, and shared modes all execute correctly
  - Tests validate context file reloading in fresh mode
  
- **Bugfix discovered during T1:**
  - Mock adapter responses were 45 chars, below MIN_RESPONSE_LENGTH (50)
  - Loop detector triggered false positive on multi-cycle tests
  - Fixed by extending mock responses to ~120 chars each (mock.py:27-31)
  - This also fixed 2 pre-existing test failures in TestCycleExecution

### Design Decisions
1. **Q: Re-read .conv file on fresh mode?**  
   A: No - .conv is the "stable contract" that defines workflow structure
   
2. **Q: Keep 'shared' as alias?**  
   A: User chose breaking change (rename to 'accumulate')

---

## Next 3 Taskable Areas

### 1. Loop Detector Tuning (Medium Priority - Research) ⏳

**Research Findings (2026-01-22):**

The loop detector already supports configuration via constructor:
- `LoopDetector(min_response_length=100)` - customize threshold
- `LoopDetector(identical_threshold=2)` - stricter duplicate detection

**Current Issue:**
- `cycle.py:262` creates detector with hardcoded defaults
- `MIN_RESPONSE_LENGTH = 50` triggers on valid short responses
- Mock adapter responses were 45 chars, causing false positives

**Potential Solutions:**
1. **Workflow directive** - Add `LOOP-THRESHOLD` to .conv format
2. **CLI option** - Add `--min-response-length` to cycle command  
3. **Adaptive** - Scale threshold based on prompt complexity
4. **Skip first N** - Allow short responses in early cycles

**Recommendation:** Option 2 (CLI option) is lowest friction. Add:
```python
@click.option("--min-response-length", type=int, default=50, 
              help="Minimum response length for loop detection")
```

**Files:** `cycle.py:262`, potentially `loop_detector.py`  
**Effort:** ~10 lines if CLI option, ~30 lines if workflow directive

### 2. Fresh Mode Enhancements (Low Priority - Future)
Potential improvements for fresh mode:
- Option to preserve specific context across cycles
- Selective file reload (only modified files)
- Performance optimization for large context sets

**Files:** `session.py`, `cycle.py`  
**Effort:** Design discussion needed

### 3. New Topic Selection
This focus topic is complete! Consider:
- RUN directive execution improvements
- Adapter reliability and retry logic
- Checkpoint/resume workflow enhancements

**Files:** Various  
**Effort:** New focus document needed

---

## Usage

Run focused cycle with this prologue:

```bash
sdqctl -vv cycle -n 3 --adapter copilot \
  --prologue @reports/cycle-improvements-focus.md \
  --epilogue "Update @reports/cycle-improvements-focus.md with completed items" \
  examples/workflows/progress-tracker.conv
```
