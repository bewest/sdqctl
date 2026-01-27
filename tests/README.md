# sdqctl Test Suite

> **Tests**: 1412+ | **Coverage**: Unit + Integration
> **Framework**: pytest

## Quick Start

```bash
# Run all tests
pytest

# Run fast tests only (skip slow)
pytest -m "not slow"

# Run integration tests only
pytest -m integration

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_conversation.py

# Run specific test class
pytest tests/test_verifiers.py::TestRefsVerifier
```

---

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures (session + function scoped)
├── fixtures/                   # Fixture modules and data
├── integration/                # Integration tests (auto-marked)
│   ├── conftest.py             # Auto-marks tests as @integration
│   ├── test_cli_integration.py # CLI command integration
│   ├── test_workflow_integration.py
│   ├── test_adapter_integration.py
│   └── test_loop_stress.py     # Extended iteration tests
└── test_*.py                   # Unit tests
```

---

## Test Markers

Markers enable selective test execution. Defined in `pyproject.toml`:

| Marker | Purpose | Usage |
|--------|---------|-------|
| `@pytest.mark.slow` | Tests taking >1s | `pytest -m "not slow"` |
| `@pytest.mark.integration` | Full stack tests | `pytest -m integration` |

### Using Markers

```python
import pytest

@pytest.mark.slow
def test_timeout_behavior(self):
    """Long-running timeout test."""
    ...

@pytest.mark.integration
class TestFullWorkflow:
    """Integration test class."""
    ...
```

### Integration Auto-Marking

Tests in `tests/integration/` are **automatically** marked via `integration/conftest.py`:

```python
def pytest_collection_modifyitems(items):
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
```

---

## Fixtures

### Session-Scoped (Shared)

Persist across entire test session - use for read-only resources:

| Fixture | Description |
|---------|-------------|
| `session_workspace` | Workspace with common test files |
| `shared_mock_adapter` | Reusable MockAdapter instance |
| `shared_adapter_config` | Common AdapterConfig |

```python
def test_example(session_workspace):
    # Uses shared workspace - don't modify files
    assert (session_workspace / "lib" / "auth.js").exists()
```

### Function-Scoped (Isolated)

Created fresh for each test - use for modifications:

| Fixture | Description |
|---------|-------------|
| `temp_workspace` | Fresh tmp_path with test structure |
| `cli_runner` | Click CliRunner instance |
| `workflow_file` | Valid minimal .conv file |
| `run_workflow_file` | .conv with RUN directive |
| `sample_conv_content` | Minimal valid conv content |
| `complex_conv_content` | Full-featured conv content |
| `consult_conv_content` | Conv with CONSULT directive |
| `pause_conv_content` | Conv with PAUSE directive |

```python
def test_modify_files(temp_workspace):
    # Uses isolated workspace - safe to modify
    (temp_workspace / "new_file.md").write_text("content")
```

### Fixture Patterns

**Creating test conversations**:
```python
@pytest.fixture
def my_conv(tmp_path):
    conv = tmp_path / "test.conv"
    conv.write_text("""MODEL mock
ADAPTER mock
PROMPT Test prompt.
""")
    return conv
```

**Workspace with structure**:
```python
@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "spec.md").write_text("# Spec")
    return tmp_path
```

---

## Parametrization

Use `@pytest.mark.parametrize` for testing variants:

### Basic Parametrization

```python
@pytest.mark.parametrize("directive,expected", [
    ("MODEL gpt-4", "gpt-4"),
    ("MODEL claude-3", "claude-3"),
    ("MODEL mock", "mock"),
])
def test_model_directive(directive, expected):
    conv = ConversationFile.from_string(f"{directive}\nPROMPT test")
    assert conv.model == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("timeout_value,expected_seconds", [
    ("30s", 30),
    ("5m", 300),
    ("2h", 7200),
    ("1d", 86400),
])
def test_consult_timeout_parsing(timeout_value, expected_seconds):
    ...
```

### Parametrized Classes

```python
@pytest.mark.parametrize("verifier_type", ["refs", "links", "traceability"])
class TestVerifierCommon:
    def test_empty_directory(self, verifier_type, tmp_path):
        ...
```

### IDs for Readability

```python
@pytest.mark.parametrize("input,expected", [
    pytest.param("valid", True, id="valid-input"),
    pytest.param("", False, id="empty-string"),
    pytest.param(None, False, id="none-value"),
])
def test_validation(input, expected):
    ...
```

---

## Common Test Patterns

### Testing CLI Commands

```python
from click.testing import CliRunner
from sdqctl.cli import cli

def test_command_succeeds(cli_runner):
    result = cli_runner.invoke(cli, ["validate", "file.conv"])
    assert result.exit_code == 0

def test_command_with_options(cli_runner):
    result = cli_runner.invoke(cli, [
        "verify", "refs",
        "--path", "/some/path",
        "--strict"
    ])
    assert result.exit_code == 0
```

### Testing Conversation Parsing

```python
from sdqctl.core.conversation import ConversationFile

def test_parse_directive(tmp_path):
    conv_path = tmp_path / "test.conv"
    conv_path.write_text("MODEL mock\nADAPTER mock\nPROMPT Test.")
    
    conv = ConversationFile.from_file(conv_path)
    assert conv.model == "mock"
```

### Testing Error Conditions

```python
def test_missing_file_error(cli_runner, tmp_path):
    result = cli_runner.invoke(cli, ["validate", str(tmp_path / "missing.conv")])
    assert result.exit_code != 0

def test_malformed_input_raises():
    with pytest.raises(ValueError):
        ConversationFile.from_string("INVALID CONTENT")
```

### Testing Verifiers

```python
from sdqctl.verifiers import RefsVerifier

def test_verifier_result(tmp_path):
    (tmp_path / "doc.md").write_text("See @other.md for details")
    (tmp_path / "other.md").write_text("# Other")
    
    verifier = RefsVerifier()
    result = verifier.verify(path=tmp_path)
    
    assert result.passed
    assert result.error_count == 0
```

---

## Best Practices

### Do

- ✅ Use session-scoped fixtures for expensive setup
- ✅ Use function-scoped fixtures when modifying state
- ✅ Add `@pytest.mark.slow` to tests >1s
- ✅ Use parametrization for variant testing
- ✅ Test both success and error paths
- ✅ Use descriptive test names (`test_<what>_<when>_<expected>`)

### Don't

- ❌ Share mutable state between tests
- ❌ Depend on test execution order
- ❌ Use real adapters in unit tests (use `mock`)
- ❌ Leave temp files outside `tmp_path` fixtures
- ❌ Skip writing tests for error conditions

---

## Running in CI

```yaml
# Example GitHub Actions step
- name: Run tests
  run: |
    pytest --tb=short -q -m "not slow"
```

For full test runs including slow tests:
```bash
pytest --tb=short
```

---

## Adding New Tests

1. **Unit test**: Add to appropriate `test_*.py` file
2. **Integration test**: Add to `tests/integration/`
3. **New test file**: Follow naming `test_<module>.py`
4. **New fixtures**: Add to `conftest.py` or `fixtures/`

### Checklist

- [ ] Test file follows `test_<module>.py` naming
- [ ] Tests have descriptive names
- [ ] Fixtures use appropriate scope
- [ ] Slow tests are marked
- [ ] Both success and error paths tested
