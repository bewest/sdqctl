# Code Quality Standards

Guidelines for maintaining code quality in sdqctl.

> **Extracted from**: proposals/BACKLOG.md §Code Quality Review (2026-01-25)

---

## Linting

**Tool**: [ruff](https://github.com/astral-sh/ruff) (configured in pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

### Running Lints

```bash
# Check for issues
ruff check sdqctl/

# Auto-fix safe issues
ruff check --fix sdqctl/

# Check tests too
ruff check sdqctl/ tests/
```

### Current Status (as of 2026-01-25)

| Category | Target | Current | Notes |
|----------|--------|---------|-------|
| E501 (line length >100) | 0 | ~192 | Requires manual refactoring |
| F841 (unused variables) | 0 | ~5 | Needs code review |
| All others | 0 | 0 | ✅ Clean |

---

## File Size Guidelines

Large files are harder to maintain, test, and understand.

| Threshold | Action |
|-----------|--------|
| >300 lines | Consider if logic can be split |
| >500 lines | Plan refactoring |
| >1000 lines | Split required - creates maintenance burden |

### Current Large Files

| File | Lines | Planned Action | Priority |
|------|-------|----------------|----------|
| `core/conversation.py` | 1,768 | Split into parser/validator/directives/templates | P3 |
| `commands/run.py` | 1,513 | Extract StepExecutor, split into modules | P1 |
| `commands/iterate.py` | 1,079 | Share execution engine with run.py | P2 |
| `adapters/copilot.py` | 1,000+ | Extract events/stats/session modules | P3 |

### Refactoring Strategy

When splitting a large file:

1. **Identify responsibilities** - Each module should have one clear purpose
2. **Extract dataclasses first** - Move data structures to separate module
3. **Extract utilities** - Move helper functions that don't depend on main class
4. **Create focused modules** - One public class/function per module
5. **Update imports** - Use `__init__.py` to maintain backward compatibility

Example for `conversation.py`:
```
core/
  conversation/
    __init__.py      # Re-exports ConversationFile (backward compat)
    parser.py        # DirectiveParser
    validator.py     # ConversationValidator  
    directives.py    # DirectiveType enum, DirectiveSpec
    templates.py     # Template variable substitution
```

---

## Test Quality

### Test Organization

```
tests/
  conftest.py           # Shared fixtures
  fixtures/             # Test data files
  integration/          # End-to-end tests
  test_<module>.py      # Unit tests per module
```

### Testing Guidelines

| Practice | Description |
|----------|-------------|
| Use parametrize | `@pytest.mark.parametrize` for test variants |
| Add markers | `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow` |
| Scope fixtures | Use `scope="session"` for expensive setup |
| Test error paths | Include malformed input tests |
| Use mock adapter | Test workflow mechanics without AI calls |

**Running selective tests:**
```bash
pytest -m unit           # Fast tests only (0.36s, 219 tests)
pytest -m integration    # Integration tests
pytest -m "not slow"     # Skip slow tests
```

### Current Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No error path tests | Unknown failure behavior | Add malformed .conv tests |
| Missing parametrization | Incomplete variant coverage | Use `@pytest.mark.parametrize` |
| ~~No test markers~~ | ~~Can't run selective tests~~ | ✅ Markers added (unit/integration/slow) |
| Fixtures not scoped | Slow test runs | Add session-scoped fixtures |
| Limited integration tests | Only loop stress testing | Add adapter, CLI integration tests |

---

## Type Annotations

### Guidelines

- All public functions should have type annotations
- Use `TYPE_CHECKING` for imports only needed by type checkers
- Package includes `py.typed` marker (PEP 561) for downstream type checking

### Example

```python
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import ModelRequirements

def resolve_model(
    requirements: "ModelRequirements",
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Resolve model requirements to concrete model name."""
    ...
```

---

## Security Considerations

See [SECURITY-MODEL.md](SECURITY-MODEL.md) for detailed security documentation.

### Quick Reference

| Concern | Risk | Mitigation |
|---------|------|------------|
| `ALLOW-SHELL` | Shell injection | Defaults to `false`; document risk |
| Path traversal | File access outside project | Use `.resolve()` and validate paths |
| `RUN-ENV` | LD_PRELOAD injection | Consider env var whitelist |
| `OUTPUT-FILE` | Write outside project | Validate output paths |

---

## Code Review Checklist

Before merging:

- [ ] Ruff passes with no errors
- [ ] New public functions have docstrings
- [ ] New public functions have type annotations
- [ ] Tests added for new functionality
- [ ] No files exceed 500 lines (or split is planned)
- [ ] Security implications considered for RUN/shell features

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Module structure and extension points
- [SECURITY-MODEL.md](SECURITY-MODEL.md) - Security documentation
- [../pyproject.toml](../pyproject.toml) - Ruff configuration
- [EXTENDING-VERIFIERS.md](EXTENDING-VERIFIERS.md) - Adding new verifiers
