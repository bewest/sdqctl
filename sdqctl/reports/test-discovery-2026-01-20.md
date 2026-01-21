# sdqctl Test Discovery Report

## Workflow: test-discovery

**Generated:** 2026-01-20T22:44:12

**Branch:** main

---

Now I have enough information to compile the requirements extraction analysis.

---

## Requirements Extraction Analysis: sdqctl

### P0 - Critical Issues

| ID | Issue | File | Lines | Action |
|----|-------|------|-------|--------|
| **P0-1** | Missing Claude adapter implementation | `sdqctl/adapters/registry.py` | L51-53 | Registry references `ClaudeAdapter` that doesn't exist. Create `sdqctl/adapters/claude.py` |
| **P0-2** | Missing OpenAI adapter implementation | `sdqctl/adapters/registry.py` | L55-57 | Registry references `OpenAIAdapter` that doesn't exist. Create `sdqctl/adapters/openai.py` |
| **P0-3** | No unit tests exist | `tests/` | - | Only fixture files exist. No actual test files (test_*.py) to verify functionality |

### P1 - High Priority Issues

| ID | Issue | File | Lines | Action |
|----|-------|------|-------|--------|
| **P1-1** | Resume command doesn't apply prompt injection | `sdqctl/cli.py` | L535-545 | `resume()` sends raw prompts without `build_prompt_with_injection()` like `run.py` does at L266-271 |
| **P1-2** | Resume command doesn't write output with injection | `sdqctl/cli.py` | L573-577 | Missing `build_output_with_injection()` for headers/footers |
| **P1-3** | `cycle.py` doesn't use prompt injection | `sdqctl/commands/cycle.py` | L171-187 | Prompts sent without PROLOGUE/EPILOGUE processing |
| **P1-4** | `flow.py` doesn't use prompt injection | `sdqctl/commands/flow.py` | L142-147 | Prompts sent without PROLOGUE/EPILOGUE processing |
| **P1-5** | `apply.py` doesn't use prompt injection | `sdqctl/commands/apply.py` | L303-310 | Prompts sent without PROLOGUE/EPILOGUE processing |
| **P1-6** | Copilot adapter `compact()` is incomplete | `sdqctl/adapters/copilot.py` | L350-366 | Implementation just `pass` and falls back to parent - should use `/compact` command |
| **P1-7** | File restrictions not enforced in context loading | `sdqctl/core/context.py` | L65-100 | `resolve_pattern()` doesn't check `FileRestrictions.is_path_allowed()` |

### P2 - Medium Priority Issues

| ID | Issue | File | Lines | Action |
|----|-------|------|-------|--------|
| **P2-1** | `show` command doesn't display file restrictions | `sdqctl/cli.py` | L431-447 | Parsed output missing `file_restrictions`, `prologues`, `epilogues`, `headers`, `footers` |
| **P2-2** | `validate` command doesn't check file references | `sdqctl/cli.py` | L369-403 | Doesn't validate PROLOGUE/EPILOGUE `@file` references exist |
| **P2-3** | Steps not used in `cycle.py` | `sdqctl/commands/cycle.py` | L171-197 | Uses flat `conv.prompts` instead of `conv.steps` (no CHECKPOINT/COMPACT/RUN support) |
| **P2-4** | Steps not used in `flow.py` | `sdqctl/commands/flow.py` | L142-148 | Uses flat `conv.prompts` instead of `conv.steps` |
| **P2-5** | Steps not used in `apply.py` | `sdqctl/commands/apply.py` | L303-313 | Uses flat `conv.prompts` instead of `conv.steps` |
| **P2-6** | Token estimation is rough | `sdqctl/core/context.py` | L112-113 | Uses `len(content) // 4` - should use tiktoken or model-specific tokenizer |
| **P2-7** | No validation for directive values | `sdqctl/core/conversation.py` | L316-417 | `_apply_directive()` accepts any value without validation (e.g., MODE could be invalid) |
| **P2-8** | Missing workspace commands | `INTEGRATION-PROPOSAL.md` | L68-82 | Proposal defines `sdqctl workspace sync/status/freeze` but not implemented |
| **P2-9** | Missing verify commands | `INTEGRATION-PROPOSAL.md` | L84-98 | Proposal defines `sdqctl verify refs/coverage/terminology` but not implemented |
| **P2-10** | Missing trace commands | `INTEGRATION-PROPOSAL.md` | L100-107 | Proposal defines `sdqctl trace req/gap/matrix` but not implemented |

### Feature Gaps (vs README claims)

| Feature | Claimed | Status | Gap |
|---------|---------|--------|-----|
| Claude adapter | `anthropic` package | ❌ Not implemented | L35-36 pyproject.toml lists dep, no adapter |
| OpenAI adapter | `openai` package | ❌ Not implemented | L38-39 pyproject.toml lists dep, no adapter |
| `sdqctl discover` | Referenced in apply.py | ❌ Not implemented | L38-39 apply.py references `--from-discovery` |
| Context compaction | Documented | ⚠️ Partial | `CopilotAdapter.compact()` stub at copilot.py:350-366 |
| File restrictions | Documented in README | ⚠️ Not enforced | context.py doesn't filter by restrictions |

### Consistency Issues

| Issue | Files | Description |
|-------|-------|-------------|
| Prompt processing varies | run.py vs cycle.py vs flow.py vs apply.py | Only `run.py` uses `build_prompt_with_injection()` |
| Step processing varies | run.py vs cycle.py vs flow.py vs apply.py | Only `run.py` processes `conv.steps` with RUN/CHECKPOINT/COMPACT |
| Output processing varies | run.py vs cycle.py vs flow.py | Only `run.py` uses `build_output_with_injection()` |

### Required Test Coverage

| Area | Test File Needed | Coverage |
|------|------------------|----------|
| ConversationFile parsing | `tests/test_conversation.py` | Parse directives, multiline, template vars |
| Context management | `tests/test_context.py` | Glob patterns, file restrictions, token tracking |
| Session lifecycle | `tests/test_session.py` | Checkpoint save/load, pause/resume |
| Mock adapter | `tests/test_adapters.py` | Send/receive, streaming, context usage |
| CLI commands | `tests/test_cli.py` | run, cycle, flow, apply, status |
| Prompt injection | `tests/test_injection.py` | PROLOGUE, EPILOGUE, template substitution |

---

### Summary

**Critical blockers (P0):** 3 items - missing adapters and no tests
**High priority (P1):** 7 items - inconsistent feature implementation across commands  
**Medium priority (P2):** 10 items - missing features, validation, proposed integrations

---

Now I have a complete picture. Let me provide comprehensive test recommendations:

---

## Test Recommendations: sdqctl

### Current State

**No test files exist.** The `tests/` directory contains only fixture modules (`tests/fixtures/*.py`) but zero actual test files (`test_*.py`). This represents ~3,926 lines of untested production code.

---

### P0 - Critical Test Requirements

| ID | Test File | Target | Lines to Cover | Purpose |
|----|-----------|--------|----------------|---------|
| **P0-1** | `tests/test_conversation.py` | `sdqctl/core/conversation.py` | L1-593 | Core parser - all workflows depend on it |
| **P0-2** | `tests/test_session.py` | `sdqctl/core/session.py` | L1-292 | Session state, checkpoint/restore |
| **P0-3** | `tests/test_adapters.py` | `sdqctl/adapters/mock.py` | L1-101 | Adapter interface contract verification |

#### P0-1: `tests/test_conversation.py`

```python
# Required test cases for sdqctl/core/conversation.py

class TestConversationFileParsing:
    """Core parsing tests - L195-244"""
    
    def test_parse_basic_directives(self):
        # L317-331: MODEL, ADAPTER, MODE, MAX_CYCLES, CWD
        pass
    
    def test_parse_context_directives(self):
        # L332-340: CONTEXT, CONTEXT-LIMIT, ON-CONTEXT-LIMIT
        pass
    
    def test_parse_file_restrictions(self):
        # L343-350: ALLOW-FILES, DENY-FILES, ALLOW-DIR, DENY-DIR
        pass
    
    def test_parse_prompt_injection(self):
        # L353-357: PROLOGUE, EPILOGUE
        pass
    
    def test_parse_prompts(self):
        # L360-363: PROMPT, ON-CONTEXT-LIMIT-PROMPT
        pass
    
    def test_parse_steps_from_prompts(self):
        # L361: Verify steps list populated when PROMPT parsed
        pass
    
    def test_parse_control_directives(self):
        # L366-373: COMPACT, NEW-CONVERSATION, CHECKPOINT
        pass
    
    def test_parse_output_directives(self):
        # L385-392: OUTPUT, OUTPUT-FORMAT, OUTPUT-FILE, OUTPUT-DIR
        pass
    
    def test_parse_header_footer(self):
        # L395-398: HEADER, FOOTER
        pass
    
    def test_parse_run_directives(self):
        # L401-405: RUN, RUN-ON-ERROR, RUN-OUTPUT
        pass
    
    def test_parse_pause(self):
        # L407-410: PAUSE with message
        pass
    
    def test_multiline_prompt(self):
        # L222-237: Continuation with indentation
        pass
    
    def test_unknown_directive_ignored(self):
        # L302-304: Forward compatibility
        pass


class TestFileRestrictions:
    """File restriction logic - L83-136"""
    
    def test_deny_wins_over_allow(self):
        # L111-114: Deny patterns checked first
        pass
    
    def test_allow_patterns_filter(self):
        # L126-131: When allow_patterns set, must match one
        pass
    
    def test_allow_dirs_filter(self):
        # L134-142: When allow_dirs set, must be under one
        pass
    
    def test_merge_with_cli(self):
        # L97-103: CLI overrides file patterns
        pass


class TestTemplateVariables:
    """Template substitution - L413-497"""
    
    def test_substitute_date_variables(self):
        # L427-430: DATE, DATETIME
        pass
    
    def test_substitute_workflow_variables(self):
        # L432-434: WORKFLOW_NAME, WORKFLOW_PATH
        pass
    
    def test_substitute_component_variables(self):
        # L489-494: COMPONENT_PATH, COMPONENT_NAME, etc.
        pass
    
    def test_substitute_git_variables(self):
        # L437-453: GIT_BRANCH, GIT_COMMIT (graceful failure)
        pass


class TestPromptInjection:
    """Prologue/epilogue injection - L526-565"""
    
    def test_build_prompt_with_prologue(self):
        # L542-545: Prologues prepended
        pass
    
    def test_build_prompt_with_epilogue(self):
        # L550-553: Epilogues appended
        pass
    
    def test_resolve_file_reference(self):
        # L499-516: @file syntax resolved to content
        pass
    
    def test_file_reference_not_found(self):
        # L511-513: Returns original reference if file missing
        pass
```

#### P0-2: `tests/test_session.py`

```python
# Required test cases for sdqctl/core/session.py

class TestSessionLifecycle:
    """Session creation and state - L59-88"""
    
    def test_session_initialization(self):
        # L62-87: ID generated, state initialized, context loaded
        pass
    
    def test_add_message_tracks_tokens(self):
        # L89-94: Messages added, context updated
        pass


class TestPromptNavigation:
    """Prompt/cycle advancement - L96-126"""
    
    def test_get_current_prompt(self):
        # L96-100: Returns correct prompt for index
        pass
    
    def test_advance_prompt(self):
        # L102-105: Increments index, returns more available
        pass
    
    def test_advance_cycle(self):
        # L107-111: Increments cycle, resets prompt index
        pass


class TestCheckpoints:
    """Checkpoint save/load - L113-240"""
    
    def test_should_checkpoint_each_cycle(self):
        # L113-126: Policy "each-cycle" triggers correctly
        pass
    
    def test_should_checkpoint_each_prompt(self):
        # L121-122: Policy "each-prompt" triggers correctly
        pass
    
    def test_create_checkpoint(self):
        # L128-150: Checkpoint created with correct data
        pass
    
    def test_save_pause_checkpoint(self):
        # L177-204: Pause checkpoint saved to disk
        pass
    
    def test_load_from_pause(self):
        # L206-239: Session restored from pause checkpoint
        pass
    
    def test_load_from_pause_inline(self):
        # L217-218: Works when conversation_inline used
        pass


class TestCompaction:
    """Compaction triggers - L241-258"""
    
    def test_needs_compaction(self):
        # L241-243: Returns True when context near limit
        pass
    
    def test_get_compaction_prompt(self):
        # L245-258: Prompt generated with preserve items
        pass
```

#### P0-3: `tests/test_adapters.py`

```python
# Required test cases for sdqctl/adapters/

class TestMockAdapter:
    """Mock adapter tests - sdqctl/adapters/mock.py"""
    
    async def test_lifecycle(self):
        # L36-42: start/stop work correctly
        pass
    
    async def test_create_destroy_session(self):
        # L44-59: Session created, tracked, destroyed
        pass
    
    async def test_send_returns_response(self):
        # L61-89: Response returned, cycles through list
        pass
    
    async def test_send_calls_on_chunk(self):
        # L82-87: Streaming callback invoked
        pass
    
    async def test_context_usage(self):
        # L91-94: Token usage tracked correctly
        pass


class TestAdapterRegistry:
    """Registry tests - sdqctl/adapters/registry.py"""
    
    def test_get_adapter_mock(self):
        # L18-28: Mock adapter retrieved
        pass
    
    def test_get_adapter_unknown_raises(self):
        # L24-26: ValueError for unknown adapter
        pass
    
    def test_list_adapters(self):
        # L31-36: Returns available adapters
        pass
```

---

### P1 - High Priority Test Requirements

| ID | Test File | Target | Lines to Cover | Purpose |
|----|-----------|--------|----------------|---------|
| **P1-1** | `tests/test_context.py` | `sdqctl/core/context.py` | L1-167 | File resolution, token tracking |
| **P1-2** | `tests/test_run.py` | `sdqctl/commands/run.py` | L1-402 | Primary command |
| **P1-3** | `tests/test_cli.py` | `sdqctl/cli.py` | L348-450 | validate, show, resume |

#### P1-1: `tests/test_context.py`

```python
class TestContextManager:
    """Context management - sdqctl/core/context.py"""
    
    def test_resolve_single_file(self):
        # L65-100: @lib/auth.js resolves
        pass
    
    def test_resolve_glob_pattern(self):
        # L81-94: @lib/*.js resolves
        pass
    
    def test_resolve_recursive_glob(self):
        # L84-89: @lib/**/*.js resolves
        pass
    
    def test_add_file_tracks_tokens(self):
        # L102-119: Token estimate updated
        pass
    
    def test_get_context_content(self):
        # L137-147: Formatted context string
        pass
    
    def test_context_window_near_limit(self):
        # L40-42: is_near_limit triggers correctly
        pass
```

#### P1-2: `tests/test_run.py`

```python
class TestRunCommand:
    """Run command - sdqctl/commands/run.py"""
    
    async def test_run_inline_prompt(self):
        # L140-146: Inline prompt creates minimal conv
        pass
    
    async def test_run_workflow_file(self):
        # L137-139: .conv file loaded
        pass
    
    async def test_run_applies_cli_overrides(self):
        # L149-157: adapter, model overridden
        pass
    
    async def test_run_file_restrictions_merged(self):
        # L169-177: CLI restrictions merged with file
        pass
    
    async def test_run_prompt_injection(self):
        # L266-271: PROLOGUE/EPILOGUE applied
        pass
    
    async def test_run_output_injection(self):
        # L356-360: HEADER/FOOTER applied
        pass
    
    async def test_run_step_checkpoint(self):
        # L290-311: CHECKPOINT step creates git commit
        pass
    
    async def test_run_step_compact(self):
        # L313-325: COMPACT step triggers compaction
        pass
    
    async def test_run_step_new_conversation(self):
        # L327-336: NEW-CONVERSATION creates fresh session
        pass
    
    async def test_run_step_run(self):
        # L338-388: RUN step executes command
        pass
    
    async def test_run_pause(self):
        # L282-288: PAUSE saves checkpoint and exits
        pass
```

---

### P2 - Medium Priority Test Requirements

| ID | Test File | Target | Purpose |
|----|-----------|--------|---------|
| **P2-1** | `tests/test_cycle.py` | `sdqctl/commands/cycle.py` | Multi-cycle execution |
| **P2-2** | `tests/test_flow.py` | `sdqctl/commands/flow.py` | Batch/parallel execution |
| **P2-3** | `tests/test_apply.py` | `sdqctl/commands/apply.py` | Component iteration |
| **P2-4** | `tests/test_logging.py` | `sdqctl/core/logging.py` | Verbosity levels |
| **P2-5** | `tests/test_progress.py` | `sdqctl/core/progress.py` | Progress output |

---

### Integration Test Requirements

| ID | Test File | Scenario |
|----|-----------|----------|
| **INT-1** | `tests/test_integration.py` | Full workflow execution with mock adapter |
| **INT-2** | `tests/test_pause_resume.py` | Pause, checkpoint, and resume flow |
| **INT-3** | `tests/test_examples.py` | Validate all `examples/workflows/*.conv` parse |

#### INT-3: Example workflow validation

```python
# tests/test_examples.py
import pytest
from pathlib import Path
from sdqctl.core.conversation import ConversationFile

EXAMPLES_DIR = Path(__file__).parent.parent / "examples" / "workflows"

@pytest.mark.parametrize("workflow_file", EXAMPLES_DIR.glob("*.conv"))
def test_example_workflow_parses(workflow_file):
    """All example workflows should parse without error."""
    conv = ConversationFile.from_file(workflow_file)
    assert conv.model is not None
    assert len(conv.prompts) > 0

def test_human_review_has_pause():
    """human-review.conv should have PAUSE directive."""
    # examples/workflows/human-review.conv L28
    conv = ConversationFile.from_file(EXAMPLES_DIR / "human-review.conv")
    assert len(conv.pause_points) > 0
    assert "findings" in conv.pause_points[0][1].lower()

def test_verify_with_run_has_run_steps():
    """verify-with-run.conv should have RUN steps."""
    # examples/workflows/verify-with-run.conv
    conv = ConversationFile.from_file(EXAMPLES_DIR / "verify-with-run.conv")
    run_steps = [s for s in conv.steps if s.type == "run"]
    assert len(run_steps) >= 2
```

---

### Test Configuration

```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    # Create test files
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "auth.js").write_text("// auth code")
    (tmp_path / "lib" / "utils.js").write_text("// utils code")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "auth.test.js").write_text("// auth tests")
    return tmp_path

@pytest.fixture
def sample_conv_content():
    """Minimal valid .conv file content."""
    return """
MODEL gpt-4
ADAPTER mock
MODE audit
PROMPT Analyze the code.
"""

@pytest.fixture
def complex_conv_content():
    """Full-featured .conv file content."""
    return """
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 2

CONTEXT @lib/*.js
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

ALLOW-FILES lib/*.js
DENY-FILES lib/secret.js

PROLOGUE Analysis date: {{DATE}}
EPILOGUE Remember to cite line numbers.

PROMPT Analyze code quality.
CHECKPOINT quality-analysis
PROMPT Generate improvement recommendations.

HEADER # Quality Report
FOOTER ---
FOOTER Generated by sdqctl

OUTPUT-FORMAT markdown
OUTPUT-FILE reports/quality-{{DATE}}.md
"""

# Re-export fixtures from fixtures package
pytest_plugins = ["tests.fixtures"]
```

---

### Coverage Targets

| Module | Target Coverage | Priority |
|--------|-----------------|----------|
| `core/conversation.py` | 90% | P0 |
| `core/session.py` | 85% | P0 |
| `adapters/mock.py` | 95% | P0 |
| `core/context.py` | 85% | P1 |
| `commands/run.py` | 80% | P1 |
| `cli.py` (validate/show/resume) | 75% | P1 |
| `commands/cycle.py` | 70% | P2 |
| `commands/flow.py` | 70% | P2 |
| `commands/apply.py` | 70% | P2 |
| `core/logging.py` | 60% | P2 |
| `core/progress.py` | 50% | P2 |

---

### Recommended Test Execution Order

1. **Phase 1 (P0):** `test_conversation.py`, `test_session.py`, `test_adapters.py`
2. **Phase 2 (P1):** `test_context.py`, `test_run.py`, `test_cli.py`
3. **Phase 3 (INT):** `test_examples.py`, `test_integration.py`, `test_pause_resume.py`
4. **Phase 4 (P2):** Remaining command tests

---

### Summary

| Priority | Test Files | Test Cases | Est. Lines |
|----------|------------|------------|------------|
| P0 | 3 | ~45 | ~400 |
| P1 | 3 | ~30 | ~300 |
| P2 | 5 | ~25 | ~250 |
| INT | 3 | ~15 | ~150 |
| **Total** | **14** | **~115** | **~1,100** |

---

Now I have enough information for a comprehensive implementation quality review.

---

## Implementation Quality Review: sdqctl

### Overview

**Codebase Size:** ~3,926 lines across 24 Python files  
**Architecture:** Click CLI + async adapters + dataclass models  
**Quality Grade:** B- (Good foundations, significant inconsistencies)

---

### P0 - Critical Implementation Issues

| ID | Issue | File:Line | Impact | Fix |
|----|-------|-----------|--------|-----|
| **P0-1** | Missing adapter implementations referenced in registry | `adapters/registry.py:51-57` | `ClaudeAdapter` and `OpenAIAdapter` referenced but files don't exist. Silent `ImportError` catch hides this. | Create stub files or remove references |
| **P0-2** | Bare `except Exception` swallows errors | Multiple locations (15 occurrences) | Debugging difficulty, silent failures | Use specific exceptions |
| **P0-3** | No input validation in `_apply_directive()` | `core/conversation.py:414-508` | Invalid directive values accepted silently (e.g., `MODE invalid`) | Add validation layer |

#### P0-2 Detail: Problematic Exception Handling

```python
# sdqctl/adapters/copilot.py:109 - Swallows destroy errors
except Exception:
    pass  # Session may remain in invalid state

# sdqctl/adapters/copilot.py:157 - Swallows destroy errors  
except Exception:
    pass

# sdqctl/core/context.py:109 - Hides file read errors
except Exception:
    return None  # Why couldn't we read the file?

# sdqctl/commands/status.py:163 - Hides checkpoint parse errors
except Exception:
    pass
```

---

### P1 - High Priority Implementation Issues

| ID | Issue | File:Line | Impact | Fix |
|----|-------|-----------|--------|-----|
| **P1-1** | Inconsistent prompt processing across commands | `run.py` vs `cycle.py` vs `flow.py` vs `apply.py` | PROLOGUE/EPILOGUE only work in `run` command | Extract shared `execute_workflow()` function |
| **P1-2** | Steps list ignored in most commands | `cycle.py:171`, `flow.py:142`, `apply.py:303` | RUN/CHECKPOINT/COMPACT directives only work in `run` | Refactor to use `conv.steps` everywhere |
| **P1-3** | File restrictions not enforced | `core/context.py:65-100` | `FileRestrictions` parsed but never checked in `resolve_pattern()` | Add `is_path_allowed()` check |
| **P1-4** | Duplicate context instantiation | `cli.py:498` vs `session.py:79-87` | Session created differently in `resume` vs `run` | Use Session constructor consistently |
| **P1-5** | Hardcoded token estimate | `core/context.py:112` | `len(content) // 4` is inaccurate | Use tiktoken or model-specific tokenizer |
| **P1-6** | Resume doesn't use prompt injection | `cli.py:535-545` | PROLOGUE/EPILOGUE ignored when resuming | Call `build_prompt_with_injection()` |

#### P1-1 Detail: Prompt Processing Inconsistency

```python
# sdqctl/commands/run.py:266-271 ✓ CORRECT
injected_prompt = build_prompt_with_injection(
    prompt, conv.prologues, conv.epilogues,
    base_path=base_path,
    variables=template_vars
)

# sdqctl/commands/cycle.py:175-177 ✗ MISSING
full_prompt = prompt  # No injection!
if cycle_num == 0 and prompt_idx == 0 and context_content:
    full_prompt = f"{context_content}\n\n{prompt}"

# sdqctl/commands/flow.py:144-145 ✗ MISSING
full_prompt = prompt
if i == 0 and context_content:
    full_prompt = f"{context_content}\n\n{prompt}"

# sdqctl/commands/apply.py:307-308 ✗ MISSING
full_prompt = prompt
if i == 0 and context_content:
    full_prompt = f"{context_content}\n\n{prompt}"
```

---

### P2 - Medium Priority Implementation Issues

| ID | Issue | File:Line | Impact | Fix |
|----|-------|-----------|--------|-----|
| **P2-1** | Global mutable state | `core/progress.py:21` | `_quiet` global affects all tests | Use context or dependency injection |
| **P2-2** | Typing inconsistency | `adapters/copilot.py:85` | `dict[str, any]` should be `dict[str, Any]` | Fix type annotation |
| **P2-3** | Unused imports in modules | Various | Dead code | Run `ruff --fix` |
| **P2-4** | Magic numbers | `core/context.py:31` | `128000` hardcoded as default max tokens | Extract to constant |
| **P2-5** | No timeout on git commands | `core/conversation.py:549-553` | `timeout=5` but no error message if times out | Add logging on timeout |
| **P2-6** | Inconsistent path handling | `core/conversation.py:578-594` | Mix of `str` and `Path` types | Standardize on `Path` |
| **P2-7** | `to_string()` incomplete | `core/conversation.py:292-393` | Doesn't serialize all directives (e.g., RUN) | Add missing directives |
| **P2-8** | Duplicate Console instantiation | Multiple commands | Each file creates own `Console()` | Singleton or injection |
| **P2-9** | `show` command incomplete | `cli.py:431-447` | Doesn't show file_restrictions, prologues, epilogues, headers, footers | Add to output |
| **P2-10** | `validate` command incomplete | `cli.py:369-403` | Doesn't validate @file references exist | Add reference validation |

---

### Code Duplication Analysis

| Pattern | Locations | Lines Duplicated | Refactoring |
|---------|-----------|------------------|-------------|
| Adapter initialization | `run.py:208-214`, `cycle.py:110-115`, `flow.py:106-110`, `apply.py:201-207` | ~30 lines × 4 | Extract `get_or_create_adapter()` |
| Session creation | `run.py:217-224`, `cycle.py:120-122`, `flow.py:135-137` | ~10 lines × 3 | Use factory method |
| Context loading | `run.py:276-279`, `cycle.py:169-170`, `flow.py:141`, `apply.py:301` | ~5 lines × 4 | Centralize in Session |
| Progress reporting | `run.py:341`, `cycle.py:146`, `apply.py:284` | ~3 lines × 3 | Use ProgressTracker class |
| JSON output handling | All commands | ~15 lines × 5 | Extract `output_result()` |

---

### Architecture Concerns

#### 1. Tight Coupling: Commands ↔ Adapters

```python
# sdqctl/commands/run.py:208-214
try:
    ai_adapter = get_adapter(conv.adapter)
except ValueError as e:
    console.print(f"[red]Error: {e}[/red]")
    console.print("[yellow]Using mock adapter instead[/yellow]")
    ai_adapter = get_adapter("mock")
```

**Issue:** Every command duplicates adapter fallback logic.  
**Fix:** Create `AdapterFactory.get_or_mock(name)` that handles fallback.

#### 2. Missing Abstraction: Workflow Execution

```python
# Current: Each command implements its own execution loop
# run.py: 260-390 (130 lines)
# cycle.py: 139-197 (60 lines)  
# flow.py: 118-165 (50 lines)
# apply.py: 270-337 (70 lines)
```

**Issue:** ~310 lines of duplicated workflow execution logic.  
**Fix:** Extract `WorkflowExecutor` class:

```python
class WorkflowExecutor:
    def __init__(self, conv: ConversationFile, adapter: AdapterBase):
        self.conv = conv
        self.adapter = adapter
    
    async def execute(self, 
        on_prompt: Callable[[int, str], None] = None,
        on_response: Callable[[int, str], None] = None,
    ) -> list[str]:
        """Execute all steps in workflow."""
        ...
```

#### 3. Inconsistent Async/Sync Boundary

```python
# sdqctl/commands/run.py:107-155 - Sync wrapper
def run(...):
    asyncio.run(_run_async(...))

# sdqctl/cli.py:456-481 - Sync wrapper with different pattern
def resume(...):
    asyncio.run(_resume_async(...))
```

**Issue:** Each command wraps async differently.  
**Fix:** Single entry point pattern or click-async integration.

---

### Type Safety Analysis

| Issue | Location | Current | Recommended |
|-------|----------|---------|-------------|
| Untyped dict returns | `session.py:260-272` | `dict` | `TypedDict` or dataclass |
| Any type escape hatch | `adapters/base.py:39` | `_internal: Any` | Generic type parameter |
| Loose return types | `conversation.py:227` | `ConversationFile` | Could return `Result[ConversationFile, ParseError]` |
| Missing type guards | `conversation.py:414-508` | Match on enum | Add exhaustiveness check |

---

### Error Handling Recommendations

#### Current State (Problem)
```python
# sdqctl/core/context.py:107-110
try:
    content = path.read_text()
except Exception:
    return None  # Caller has no idea why
```

#### Recommended (Solution)
```python
# Create custom exceptions
class ContextError(Exception):
    """Base error for context operations."""
    pass

class FileReadError(ContextError):
    def __init__(self, path: Path, cause: Exception):
        self.path = path
        self.cause = cause
        super().__init__(f"Failed to read {path}: {cause}")

# Use specific handling
def add_file(self, path: Path) -> Optional[ContextFile]:
    if not path.exists():
        return None  # Expected case: file doesn't exist
    try:
        content = path.read_text()
    except PermissionError as e:
        raise FileReadError(path, e)  # Propagate with context
    except UnicodeDecodeError as e:
        logger.warning(f"Skipping binary file: {path}")
        return None  # Expected case: binary file
```

---

### Logging Consistency

| Level | Should Log | Currently Logged |
|-------|------------|------------------|
| INFO | Workflow start/end, prompt N/M | ✓ Correct |
| DEBUG | Response previews, token counts | ⚠️ Inconsistent |
| WARNING | Fallback to mock, file not found | ⚠️ Missing some |
| ERROR | Adapter failures, parse errors | ✓ Correct |

**Issues Found:**
- `cycle.py` uses `console.print()` instead of `logger.debug()` for verbose output
- `flow.py:81` uses `console.print("[yellow]Warning...")` instead of `logger.warning()`
- Inconsistent use of `progress()` vs `logger.info()`

---

### Security Considerations

| Issue | Location | Risk | Mitigation |
|-------|----------|------|------------|
| Shell injection in RUN | `run.py:459` | HIGH | Sanitize or use `shell=False` |
| Path traversal in @file | `conversation.py:578-594` | MEDIUM | Validate path stays within CWD |
| Arbitrary file write | `run.py:378-381` | MEDIUM | Validate output path |

#### Shell Injection Detail
```python
# sdqctl/commands/run.py:459-465
result = subprocess.run(
    command,
    shell=True,  # ⚠️ Allows shell injection
    capture_output=True,
    text=True,
    timeout=60,
    cwd=conv.cwd or Path.cwd(),
)
```

If `command` comes from a `.conv` file that could be user-supplied, this is exploitable.

---

### Performance Considerations

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| Token re-estimation | `session.py:93` | Called on every message | Cache or batch |
| File content in memory | `context.py:115` | Large files cause memory pressure | Stream or chunk |
| Glob resolution | `context.py:84-89` | Recursive glob can be slow | Cache results |
| Progress file writes | `apply.py:368-378` | Disk I/O on every update | Debounce writes |

---

### Summary: Action Items by Priority

**P0 (Critical):**
1. Create stub `claude.py` and `openai.py` or remove registry references
2. Replace bare `except Exception:` with specific exceptions (15 locations)
3. Add validation layer for directive values

**P1 (High):**
1. Refactor prompt execution into shared `WorkflowExecutor` class
2. Enforce file restrictions in `ContextManager.resolve_pattern()`
3. Apply prompt injection in `cycle.py`, `flow.py`, `apply.py`, `resume`
4. Use `conv.steps` instead of `conv.prompts` in all commands

**P2 (Medium):**
1. Extract constants for magic numbers (token limits, timeouts)
2. Standardize on `Path` objects throughout
3. Create singleton `Console` instance
4. Complete `to_string()` serialization
5. Add shell injection mitigation for RUN directive

---

## Next Steps

1. Create test files based on recommendations

2. Run tests with pytest

3. Update documentation for any gaps found



*Generated by sdqctl test-discovery workflow*