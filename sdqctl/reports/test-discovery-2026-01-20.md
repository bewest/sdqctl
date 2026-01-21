# sdqctl Test Discovery Report

## Workflow: test-discovery

**Generated:** 2026-01-20T23:22:33

**Branch:** main

---

Created `reports/improvements-tracker.md` with detailed findings.

**Summary:** 109/109 tests pass, but coverage is ~40% because CLI commands have zero tests. 

**Top 3 Priority Work Areas:**
1. **P0: CLI Integration Tests** - `run`, `cycle`, `flow`, `apply`, `status` commands untested
2. **P1: Error Handling Gaps** - RUN timeout recovery, file reference errors, checkpoint restore 
3. **P1: Workspace Integration** - workspace/verify/trace commands from INTEGRATION-PROPOSAL.md not implemented

---

Now let me output the test recommendations:

## Test Recommendations for sdqctl

**Analysis Date:** 2026-01-21  
**Current Status:** 109/109 tests passing  
**Estimated Coverage:** ~40% (core modules tested, CLI/commands untested)

---

### P0 - Critical Test Gaps

#### P0-1: CLI Command Integration Tests
**Missing:** `tests/test_cli.py`  
**Impact:** Commands `run`, `cycle`, `flow`, `apply`, `status`, `validate`, `show`, `resume` have 0% coverage

```python
# Recommended tests using Click test runner
from click.testing import CliRunner
from sdqctl.cli import cli

class TestCliRun:
    def test_run_dry_run(self, tmp_path):
        """Test sdqctl run --dry-run"""
        runner = CliRunner()
        result = runner.invoke(cli, ['run', str(conv_file), '--dry-run'])
        assert result.exit_code == 0
        
    def test_run_with_mock_adapter(self, tmp_path):
        """Test sdqctl run with mock adapter"""
        result = runner.invoke(cli, ['run', str(conv_file), '--adapter', 'mock'])
        assert result.exit_code == 0

class TestCliValidate:
    def test_validate_valid_workflow(self, tmp_path):
        """Test validating a correct .conv file"""
        
    def test_validate_invalid_workflow(self, tmp_path):
        """Test error handling for invalid .conv file"""
```

#### P0-2: Run Command Step Execution
**File:** `sdqctl/commands/run.py`, lines 163-280  
**Issue:** Step types (prompt, checkpoint, compact, new_conversation, run) untested

```python
# Recommended tests
class TestRunStepExecution:
    @pytest.mark.asyncio
    async def test_prompt_step_execution(self):
        """Test PROMPT steps send to adapter and track response"""
        
    @pytest.mark.asyncio
    async def test_checkpoint_step_creates_checkpoint(self):
        """Test CHECKPOINT step saves session state"""
        
    @pytest.mark.asyncio
    async def test_run_step_executes_command(self):
        """Test RUN step executes shell command"""
        # Line 239-280 subprocess handling
        
    @pytest.mark.asyncio
    async def test_run_step_timeout_handling(self):
        """Test RUN-ON-ERROR behavior on timeout"""
        # Line 265-273
```

---

### P1 - High Priority Test Gaps

#### P1-1: Cycle Command Multi-Cycle Execution
**File:** `sdqctl/commands/cycle.py`, lines 117-200  
**Issue:** Cycle iteration, compaction triggers, checkpoint policies untested

```python
class TestCycleCommand:
    @pytest.mark.asyncio
    async def test_cycle_runs_multiple_cycles(self):
        """Test MAX-CYCLES iterations"""
        # Lines 139-197
        
    @pytest.mark.asyncio
    async def test_cycle_triggers_compaction(self):
        """Test compaction when context near limit"""
        # Lines 149-160
        
    @pytest.mark.asyncio
    async def test_cycle_checkpoints_per_policy(self):
        """Test CHECKPOINT-AFTER each-cycle"""
        # Lines 163-166
```

#### P1-2: Flow Command Parallel Execution
**File:** `sdqctl/commands/flow.py`, lines 114-206  
**Issue:** Parallel workflow execution, error handling untested

```python
class TestFlowCommand:
    @pytest.mark.asyncio
    async def test_flow_parallel_execution(self):
        """Test --parallel limits concurrent executions"""
        # Lines 114-115 semaphore
        
    @pytest.mark.asyncio
    async def test_flow_continue_on_error(self):
        """Test --continue-on-error doesn't stop on failure"""
        # Lines 173-175
        
    def test_flow_glob_pattern_expansion(self):
        """Test workflow file discovery from glob"""
        # Lines 70-84
```

#### P1-3: Apply Command Component Iteration
**File:** `sdqctl/commands/apply.py`, lines 270-338  
**Issue:** Template variable substitution, progress tracking untested

```python
class TestApplyCommand:
    @pytest.mark.asyncio
    async def test_apply_substitutes_component_variables(self):
        """Test {{COMPONENT_PATH}}, {{ITERATION_INDEX}} substitution"""
        # Lines 287-289 apply_iteration_context
        
    def test_apply_progress_tracker_writes_markdown(self, tmp_path):
        """Test ProgressTracker output format"""
        # Lines 341-431
        
    @pytest.mark.asyncio
    async def test_apply_from_discovery_file(self):
        """Test --from-discovery JSON input"""
        # Lines 122-141
```

#### P1-4: Copilot Adapter Tests
**File:** `sdqctl/adapters/copilot.py`  
**Issue:** Zero test coverage for real adapter

```python
class TestCopilotAdapterMocked:
    """Tests using mocked SDK"""
    
    @pytest.mark.asyncio
    async def test_start_initializes_client(self, mocker):
        """Test start() creates CopilotClient"""
        # Lines 88-100
        
    @pytest.mark.asyncio
    async def test_send_handles_events(self, mocker):
        """Test event handler processes all event types"""
        # Lines 181-311 on_event function
        
    @pytest.mark.asyncio
    async def test_session_stats_accumulated(self, mocker):
        """Test usage events update SessionStats"""
        # Lines 249-255
```

---

### P2 - Medium Priority Test Gaps

#### P2-1: Status Command Output
**File:** `sdqctl/commands/status.py`  
**Issue:** Session enumeration, JSON output format untested

```python
class TestStatusCommand:
    def test_status_overview(self):
        """Test default status output"""
        # Lines 51-78
        
    def test_status_adapters_list(self):
        """Test --adapters flag"""
        # Lines 81-123
        
    def test_status_sessions_json(self, tmp_path):
        """Test --sessions --json output"""
        # Lines 126-193
```

#### P2-2: Logging Configuration
**File:** `sdqctl/core/logging.py`  

```python
class TestLogging:
    def test_verbosity_levels(self):
        """Test -v, -vv, -vvv set correct log level"""
        # Lines 40-50
        
    def test_quiet_suppresses_output(self):
        """Test -q sets ERROR level"""
        # Lines 41-42
        
    def test_trace_level_works(self):
        """Test custom TRACE level"""
        # Lines 16-27
```

#### P2-3: Progress Module
**File:** `sdqctl/core/progress.py`  

```python
class TestProgress:
    def test_quiet_mode_suppresses(self):
        """Test set_quiet(True) suppresses output"""
        # Lines 24-28
        
    def test_progress_tracker_timing(self):
        """Test ProgressTracker elapsed time"""
        # Lines 96-150
```

#### P2-4: Registry Plugin Loading
**File:** `sdqctl/adapters/registry.py`  

```python
class TestRegistry:
    def test_register_custom_adapter(self):
        """Test register_adapter adds to registry"""
        # Lines 13-15
        
    def test_lazy_load_adapters(self):
        """Test adapters loaded on demand"""
        # Lines 39-60
        
    def test_missing_dependency_handled(self):
        """Test ImportError caught for optional deps"""
        # Lines 58-60
```

---

### Test Infrastructure Recommendations

#### Add pytest-cov to dev dependencies
**File:** `pyproject.toml`, lines 41-45

```toml
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0",  # ADD THIS
    "ruff>=0.1.0",
]
```

#### Add Click test fixtures to conftest.py
**File:** `tests/conftest.py`

```python
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    """Click test runner for CLI testing."""
    return CliRunner()

@pytest.fixture
def workflow_file(tmp_path):
    """Create a valid workflow file for testing."""
    content = """MODEL gpt-4
ADAPTER mock
PROMPT Test prompt.
"""
    f = tmp_path / "test.conv"
    f.write_text(content)
    return f
```

---

### Summary: Test Priority Order

1. **`tests/test_cli.py`** - CLI entry points (P0)
2. **`tests/test_run_command.py`** - Run command step execution (P0)
3. **`tests/test_cycle_command.py`** - Cycle multi-iteration (P1)
4. **`tests/test_apply_command.py`** - Apply component iteration (P1)
5. **`tests/test_flow_command.py`** - Flow parallel execution (P1)
6. **`tests/test_copilot_adapter.py`** - Mocked Copilot SDK (P1)
7. **`tests/test_status_command.py`** - Status output (P2)
8. **`tests/test_logging.py`** - Logging configuration (P2)

---

Analysis complete. The `reports/improvements-tracker.md` now contains:

**Top 3 Priority Work Areas:**
1. **P0: Config File Loading** - `sdqctl init` creates `.sdqctl.yaml` but nothing loads it (cli.py L83-127)
2. **P0: Shell Injection** - RUN directive uses `shell=True` unsafely (run.py L444)
3. **P1: Resource Leak** - Adapter sessions can leak on intermediate failures (run.py L287-510)

**Implementation Quality Review added with:**
- Code quality metrics table
- 6 specific issues (IQ-1 through IQ-6) with line numbers
- Security considerations matrix
- Maintainability score: B-

**Key findings across all sections:**
- 109/109 tests passing, but ~40% coverage (CLI commands: 0%, copilot adapter: 0%)
- Type hint inconsistencies (`any` vs `Any` at copilot.py L85)
- Dead code: `cli_restrictions` never used (run.py L213-218)
- Duplicate boilerplate across all command files
- Context files bypass FileRestrictions (session.py L86-87)

---

## Next Steps

1. Create test files based on recommendations

2. Run tests with pytest

3. Update documentation for any gaps found



*Generated by sdqctl test-discovery workflow*