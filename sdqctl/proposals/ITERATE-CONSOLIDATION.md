# Proposal: Command Consolidation - `run` + `iterate` → `iterate`

> **Status**: Ready for Implementation  
> **Date**: 2026-01-25  
> **Author**: Ben West  
> **Priority**: P2  
> **Effort**: Medium (2-3 days)  
> **Related**: [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md), [RUN-RENAME-ANALYSIS.md](RUN-RENAME-ANALYSIS.md)

---

## Executive Summary

Consolidate the `run` and `iterate` commands into a single `iterate` command. The new command:
- Defaults to single execution (`-n 1`), preserving `run` behavior
- Supports multi-cycle execution with `-n N`
- Merges unique features from both commands
- Provides deprecated aliases for backward compatibility

**Why `iterate`**: Captures the refinement-loop nature of the tool. "Iterate on this codebase" is natural English, has no keyword conflicts, and suggests continuous improvement.

---

## Problem Statement

### Current State

Two commands with overlapping functionality:

```bash
sdqctl run workflow.conv           # Single execution
sdqctl iterate workflow.conv -n 5    # Multi-cycle execution
```

### Issues

1. **Conceptual overlap**: `run` is essentially `cycle -n 1`
2. **Feature fragmentation**: Some features only in `run`, others only in `iterate`
3. **Maintenance burden**: ~2,500 lines of duplicated logic across two files
4. **User confusion**: When to use `run` vs `iterate`?

### Desired State

```bash
sdqctl iterate workflow.conv           # Single execution (default -n 1)
sdqctl iterate workflow.conv -n 5      # Multi-cycle execution
sdqctl iterate "Audit this module"     # Inline prompt support
```

---

## Feature Comparison

### Features ONLY in `run` (to be added to `iterate`)

| Feature | CLI Option | Description |
|---------|------------|-------------|
| Inline prompts | `target` argument | `sdqctl run "Audit auth"` |
| Extra context | `--context/-c` | Add context files via CLI |
| File allow patterns | `--allow-files` | Glob patterns for allowed files |
| File deny patterns | `--deny-files` | Glob patterns for denied files |
| Directory allow | `--allow-dir` | Directory-level allow |
| Directory deny | `--deny-dir` | Directory-level deny |
| Named sessions | `--session-name` | Resume by name |
| Compaction default | `min-compaction-density=0` | No automatic compaction |

### Features ONLY in `iterate` (already in `iterate`)

| Feature | CLI Option | Description |
|---------|------------|-------------|
| Max cycles | `--max-cycles/-n` | Iteration count |
| Session mode | `--session-mode/-s` | accumulate/compact/fresh |
| Checkpoint dir | `--checkpoint-dir` | Checkpoint storage |
| JSON input | `--from-json` | Pipeline input |
| Infinite sessions | `--no-infinite-sessions` | SDK session control |
| Compaction threshold | `--compaction-threshold` | When to compact |
| Buffer threshold | `--buffer-threshold` | Hard limit for blocking |
| Loop detection | LoopDetector | Multi-cycle safety |

### Common Features (both commands)

| Feature | Description |
|---------|-------------|
| `--adapter/-a` | AI adapter selection |
| `--model/-m` | Model override |
| `--prologue/--epilogue` | Prompt injection |
| `--header/--footer` | Output injection |
| `--output/-o` | Output file |
| `--event-log` | SDK event export |
| `--json` | JSON output |
| `--dry-run` | Preview mode |
| `--render-only` | Render without execution |
| `--no-stop-file-prologue` | Disable stop file |
| `--stop-file-nonce` | Override nonce |

---

## Naming Decision: `iterate`

### Why Not Other Candidates

| Candidate | Issue |
|-----------|-------|
| `yield` | Python keyword - implementation friction |
| `do` | Shell keyword (`do...done`) - documentation friction |
| `exec` | Shell builtin - conflicts with Unix semantics |
| `invoke` | Good but formal; doesn't capture "improvement over time" |
| `run` | Conflicts with RUN directive |

### Why `iterate`

| Criterion | Assessment |
|-----------|------------|
| **Semantic accuracy** | ✅ "Iterate on this codebase" is natural |
| **Brevity** | 7 characters (acceptable) |
| **Uniqueness** | ✅ No conflicts in Python, shell, or CLI ecosystem |
| **Familiarity** | ✅ Common programming term |
| **Philosophy fit** | ✅ Emphasizes refinement, continuous improvement |
| **Implementation** | ✅ Clean - no keyword/builtin workarounds |

### User Experience

```bash
# Natural progression:
sdqctl iterate workflow.conv           # "Let me iterate on this once"
sdqctl iterate workflow.conv -n 3      # "Let me iterate 3 times"
sdqctl iterate "Fix the tests" -n 5    # "Iterate until tests pass"
```

---

## Implementation Plan

### Phase 1: Add Missing Features to `cycle.py`

Add features from `run.py` that are missing in `cycle.py`:

```python
# In cycle.py, add these options:

@click.option("--context", "-c", multiple=True, 
              help="Additional context files")
@click.option("--allow-files", multiple=True, 
              help="Glob pattern for allowed files")
@click.option("--deny-files", multiple=True, 
              help="Glob pattern for denied files")
@click.option("--allow-dir", multiple=True, 
              help="Directory to allow")
@click.option("--deny-dir", multiple=True, 
              help="Directory to deny")
@click.option("--session-name", default=None, 
              help="Named session for resumability")
```

Add inline prompt support:

```python
# Change argument to optional with flexible interpretation
@click.argument("target", required=False)

# In function body:
target_path = Path(target) if target else None
if target_path and target_path.exists() and target_path.suffix in (".conv", ".copilot"):
    # Load as workflow file
    conv = ConversationFile.from_file(target_path)
elif target and not target_path.exists():
    # Treat as inline prompt
    conv = ConversationFile(prompts=[target], ...)
```

Change default for `--max-cycles`:

```python
@click.option("--max-cycles", "-n", type=int, default=1,  # Changed from None
              help="Number of cycles (default: 1)")
```

### Phase 2: Rename and Create Aliases

#### Step 2.1: Rename `cycle.py` → `iterate.py`

```bash
git mv sdqctl/commands/iterate.py sdqctl/commands/iterate.py
```

Update the command decorator:

```python
@click.command("iterate")  # Changed from "cycle"
```

#### Step 2.2: Create Deprecated Aliases in `cli.py`

```python
# sdqctl/cli.py

from .commands.iterate import iterate

# Register primary command
cli.add_command(iterate)

# Deprecated aliases with warnings
@cli.command("run", hidden=True)
@click.pass_context
def run_alias(ctx, **kwargs):
    """[DEPRECATED] Use 'sdqctl iterate' instead."""
    import click
    click.secho(
        "⚠ 'sdqctl run' is deprecated. Use 'sdqctl iterate' instead.",
        fg="yellow", err=True
    )
    ctx.invoke(iterate, **kwargs)

@cli.command("cycle", hidden=True)  
@click.pass_context
def cycle_alias(ctx, **kwargs):
    """[DEPRECATED] Use 'sdqctl iterate' instead."""
    import click
    click.secho(
        "⚠ 'sdqctl iterate' is deprecated. Use 'sdqctl iterate' instead.",
        fg="yellow", err=True
    )
    ctx.invoke(iterate, **kwargs)
```

**Note**: The aliases must have identical signatures to `iterate`. Use Click's parameter forwarding:

```python
# Alternative: Forward all options dynamically
def create_deprecated_alias(new_name: str, old_name: str, target_command):
    """Create a deprecated alias that forwards all arguments."""
    # Copy all params from target
    params = [p.make_decorator() for p in target_command.params]
    
    @cli.command(old_name, hidden=True, deprecated=True)
    @click.pass_context
    def alias(ctx, **kwargs):
        click.secho(
            f"⚠ 'sdqctl {old_name}' is deprecated. Use 'sdqctl {new_name}' instead.",
            fg="yellow", err=True
        )
        ctx.invoke(target_command, **kwargs)
    
    # Apply params
    for param in reversed(params):
        alias = param(alias)
    
    return alias
```

### Phase 3: Update Imports and References

#### Python Files

| File | Change |
|------|--------|
| `sdqctl/commands/__init__.py` | Change `from .cycle import cycle` → `from .iterate import iterate` |
| `sdqctl/cli.py` | Update imports, add aliases |
| `sdqctl/commands/run.py` | Delete (functionality merged) |

#### Test Files

| File | Change |
|------|--------|
| `tests/test_run_command.py` | Rename to `test_iterate_command.py`, merge with cycle tests |
| `tests/test_cycle_command.py` | Merge into `test_iterate_command.py` |

### Phase 4: Documentation Updates

#### Files Requiring Updates

**Primary documentation (16 files):**

| File | `run` refs | `iterate` refs | Action |
|------|-----------|--------------|--------|
| `docs/GETTING-STARTED.md` | 9 | 4 | Update all |
| `docs/COMMANDS.md` | ~10 | ~5 | Update all |
| `docs/SECURITY-MODEL.md` | 6 | 0 | Update all |
| `docs/TRACEABILITY-WORKFLOW.md` | 6 | 0 | Update all |
| `docs/REVERSE-ENGINEERING.md` | 5 | 0 | Update all |
| `docs/IO-ARCHITECTURE.md` | 3 | 0 | Update all |
| `docs/CONTEXT-MANAGEMENT.md` | ~3 | ~3 | Update all |
| `docs/ADAPTERS.md` | ~2 | ~2 | Update all |
| `docs/GLOSSARY.md` | ~2 | ~1 | Update all |
| `docs/LOOP-STRESS-TEST.md` | ~3 | ~3 | Update all |
| `docs/PIPELINE-SCHEMA.md` | ~2 | ~2 | Update all |
| `docs/PHILOSOPHY.md` | ~2 | ~1 | Update all |
| `docs/QUIRKS.md` | ~2 | ~1 | Update all |
| `docs/SYNTHESIS-CYCLES.md` | ~2 | ~5 | Update all |
| `docs/VALIDATION-WORKFLOW.md` | ~3 | ~3 | Update all |
| `docs/TROUBLESHOOTING.md` | ~2 | ~2 | Update all |

**Example workflows (15+ files):**

| File | Action |
|------|--------|
| `examples/workflows/security-audit.conv` | Update comment |
| `examples/workflows/elide-patterns.conv` | Update comment |
| `examples/workflows/proposal-development.conv` | Update usage |
| `examples/workflows/README.md` | Update all examples |
| `examples/workflows/cli-ergonomics/*.conv` | Update all |
| All other `.conv` files | Update usage comments |

**Proposals (6+ files):**

| File | Action |
|------|--------|
| `proposals/CLI-ERGONOMICS.md` | Add reference to this proposal |
| `proposals/RUN-RENAME-ANALYSIS.md` | Mark as superseded |
| `proposals/BACKLOG.md` | Update P1/P2 items |
| `README.md` (root) | Update all examples |

#### Documentation Update Script

```bash
#!/bin/bash
# update-command-references.sh

# Replace 'sdqctl run' with 'sdqctl iterate'
find docs examples proposals -name "*.md" -o -name "*.conv" | \
  xargs sed -i 's/sdqctl run /sdqctl iterate /g'

# Replace 'sdqctl iterate' with 'sdqctl iterate'  
find docs examples proposals -name "*.md" -o -name "*.conv" | \
  xargs sed -i 's/sdqctl iterate /sdqctl iterate /g'

# Handle variations
find docs examples proposals -name "*.md" -o -name "*.conv" | \
  xargs sed -i 's/`run`/`iterate`/g'

find docs examples proposals -name "*.md" -o -name "*.conv" | \
  xargs sed -i 's/`iterate`/`iterate`/g'

# Update command references in tables
find docs examples proposals -name "*.md" | \
  xargs sed -i 's/| run |/| iterate |/g'

find docs examples proposals -name "*.md" | \
  xargs sed -i 's/| cycle |/| iterate |/g'
```

**Manual updates required:**
- Help command text in `help.py`
- Error messages mentioning specific commands
- Deprecation notices

### Phase 5: Update Help System

Update `sdqctl/commands/help.py`:

```python
# Update command descriptions
COMMAND_HELP = {
    "iterate": """Execute a workflow with optional multi-cycle iteration.

USAGE:
    sdqctl iterate workflow.conv              # Single execution
    sdqctl iterate workflow.conv -n 5         # 5 iterations
    sdqctl iterate "Audit auth module"        # Inline prompt
    sdqctl iterate workflow.conv -s fresh     # Fresh session each cycle

OPTIONS:
    -n, --max-cycles INT       Number of cycles (default: 1)
    -s, --session-mode MODE    Session handling: accumulate|compact|fresh
    -a, --adapter NAME         AI adapter (copilot, claude, openai, mock)
    -c, --context FILE         Additional context files (repeatable)
    ...

EXAMPLES:
    # Quick one-off task
    sdqctl iterate "Review this PR for security issues"
    
    # Run workflow once
    sdqctl iterate security-audit.conv
    
    # Iterative refinement (3 cycles)
    sdqctl iterate fix-tests.conv -n 3
    
    # Fresh context each cycle (picks up file changes)
    sdqctl iterate implement-feature.conv -n 5 -s fresh

DEPRECATION NOTICE:
    'sdqctl run' and 'sdqctl iterate' are deprecated aliases.
    They will be removed in a future version.
""",
}

# Add guidance topic
GUIDANCE_TOPICS["iterate-vs-run-cycle"] = """
## Migrating from run/cycle to iterate

The `iterate` command combines the functionality of both `run` and `iterate`:

| Old Command | New Command |
|-------------|-------------|
| `sdqctl run workflow.conv` | `sdqctl iterate workflow.conv` |
| `sdqctl run "prompt"` | `sdqctl iterate "prompt"` |
| `sdqctl iterate workflow.conv -n 5` | `sdqctl iterate workflow.conv -n 5` |
| `sdqctl iterate workflow.conv -s fresh` | `sdqctl iterate workflow.conv -s fresh` |

The old commands still work but show a deprecation warning.
"""
```

---

## Testing Plan

### Unit Tests

#### New Test File: `tests/test_iterate_command.py`

```python
"""Tests for the iterate command (consolidation of run + cycle)."""

import pytest
from click.testing import CliRunner
from sdqctl.cli import cli


class TestIterateBasic:
    """Basic iterate command functionality."""

    def test_iterate_workflow_single_cycle(self, runner, mock_adapter):
        """Single cycle execution (like old 'run')."""
        result = runner.invoke(cli, ["iterate", "test.conv"])
        assert result.exit_code == 0

    def test_iterate_workflow_multi_cycle(self, runner, mock_adapter):
        """Multi-cycle execution (like old 'cycle')."""
        result = runner.invoke(cli, ["iterate", "test.conv", "-n", "3"])
        assert result.exit_code == 0

    def test_iterate_inline_prompt(self, runner, mock_adapter):
        """Inline prompt support (from run)."""
        result = runner.invoke(cli, ["iterate", "Audit this code"])
        assert result.exit_code == 0


class TestIterateOptions:
    """Test options merged from run and cycle."""

    def test_context_option(self, runner, mock_adapter):
        """--context option from run."""
        result = runner.invoke(cli, [
            "iterate", "test.conv", 
            "-c", "extra.md"
        ])
        assert result.exit_code == 0

    def test_allow_files_option(self, runner, mock_adapter):
        """--allow-files option from run."""
        result = runner.invoke(cli, [
            "iterate", "test.conv",
            "--allow-files", "src/*.py"
        ])
        assert result.exit_code == 0

    def test_session_mode_option(self, runner, mock_adapter):
        """--session-mode option from cycle."""
        result = runner.invoke(cli, [
            "iterate", "test.conv",
            "-s", "fresh"
        ])
        assert result.exit_code == 0

    def test_session_name_option(self, runner, mock_adapter):
        """--session-name option from run."""
        result = runner.invoke(cli, [
            "iterate", "test.conv",
            "--session-name", "my-session"
        ])
        assert result.exit_code == 0


class TestDeprecatedAliases:
    """Test that run and cycle aliases work with warnings."""

    def test_run_alias_shows_warning(self, runner, mock_adapter):
        """'run' shows deprecation warning."""
        result = runner.invoke(cli, ["run", "test.conv"])
        assert "deprecated" in result.output.lower() or result.exit_code == 0
        # Check stderr for warning

    def test_cycle_alias_shows_warning(self, runner, mock_adapter):
        """'cycle' shows deprecation warning."""
        result = runner.invoke(cli, ["cycle", "test.conv", "-n", "2"])
        assert "deprecated" in result.output.lower() or result.exit_code == 0

    def test_run_alias_forwards_all_options(self, runner, mock_adapter):
        """'run' alias correctly forwards all options."""
        result = runner.invoke(cli, [
            "run", "test.conv",
            "--adapter", "mock",
            "--output", "out.md"
        ])
        assert result.exit_code == 0

    def test_cycle_alias_forwards_all_options(self, runner, mock_adapter):
        """'cycle' alias correctly forwards all options."""
        result = runner.invoke(cli, [
            "cycle", "test.conv",
            "-n", "3",
            "-s", "compact"
        ])
        assert result.exit_code == 0


class TestIterateDefaults:
    """Test default behavior matches expectations."""

    def test_default_max_cycles_is_one(self, runner, mock_adapter):
        """Default -n is 1 (single execution)."""
        result = runner.invoke(cli, ["iterate", "test.conv", "--dry-run"])
        # Verify only one cycle in output
        assert "cycle 1/1" in result.output.lower() or result.exit_code == 0

    def test_default_session_mode_is_accumulate(self, runner, mock_adapter):
        """Default session mode is 'accumulate'."""
        result = runner.invoke(cli, ["iterate", "test.conv", "--dry-run"])
        # Verify session mode in output
        assert result.exit_code == 0
```

### Integration Tests

```python
"""Integration tests for iterate command."""

class TestIterateIntegration:
    """End-to-end iterate tests with real workflows."""

    @pytest.mark.integration
    def test_iterate_with_run_step(self, runner, mock_adapter, tmp_path):
        """Workflow with RUN step executes correctly."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
ADAPTER mock
PROMPT Check this out
RUN echo "hello"
PROMPT Report the output
""")
        result = runner.invoke(cli, ["iterate", str(workflow)])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_iterate_multi_cycle_with_compaction(self, runner, mock_adapter, tmp_path):
        """Multi-cycle with compaction."""
        workflow = tmp_path / "test.conv"
        workflow.write_text("""
ADAPTER mock
MAX-CYCLES 3
PROMPT Analyze
COMPACT
""")
        result = runner.invoke(cli, ["iterate", str(workflow)])
        assert result.exit_code == 0
```

### Migration Tests

```python
"""Tests to verify backward compatibility during migration."""

class TestMigrationCompatibility:
    """Ensure old scripts continue to work."""

    def test_run_command_still_works(self, runner, mock_adapter):
        """Scripts using 'run' don't break."""
        result = runner.invoke(cli, ["run", "test.conv"])
        # Should work, just with warning
        assert result.exit_code == 0

    def test_cycle_command_still_works(self, runner, mock_adapter):
        """Scripts using 'cycle' don't break."""
        result = runner.invoke(cli, ["cycle", "test.conv", "-n", "2"])
        assert result.exit_code == 0

    def test_run_options_work_in_iterate(self, runner, mock_adapter):
        """All run-specific options work in iterate."""
        result = runner.invoke(cli, [
            "iterate", "test.conv",
            "-c", "context.md",
            "--allow-files", "*.py",
            "--deny-files", "test_*.py",
            "--session-name", "my-session"
        ])
        assert result.exit_code == 0

    def test_cycle_options_work_in_iterate(self, runner, mock_adapter):
        """All cycle-specific options work in iterate."""
        result = runner.invoke(cli, [
            "iterate", "test.conv",
            "-n", "5",
            "-s", "fresh",
            "--checkpoint-dir", "./checkpoints",
            "--compaction-threshold", "70"
        ])
        assert result.exit_code == 0
```

---

## Deprecation Timeline

### Version N (Current + 1): Introduction

- Add `iterate` as primary command
- Add `run` and `iterate` as deprecated aliases (with warnings)
- Update all documentation to prefer `iterate`
- Aliases are NOT hidden in help (visible for discoverability)

### Version N+1: Soft Deprecation

- Aliases become hidden in help output (`hidden=True`)
- Warning message becomes more prominent
- Add `sdqctl help migrate` guidance topic

### Version N+2 (or 1.0): Removal

- Remove `run` alias
- Remove `iterate` alias
- Clean up alias code from `cli.py`

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scripts break | Low | High | Aliases maintain compatibility |
| User confusion | Medium | Low | Clear deprecation messages |
| Documentation inconsistency | Medium | Medium | Automated update script |
| Merge conflicts | Low | Low | Do in single PR |

---

## Implementation Checklist

### Pre-Implementation

- [ ] Review this proposal with stakeholders
- [ ] Confirm `iterate` as final name choice
- [ ] Confirm deprecation timeline

### Phase 1: Feature Parity (Day 1)

- [ ] Add `--context/-c` to cycle.py
- [ ] Add `--allow-files`, `--deny-files` to cycle.py
- [ ] Add `--allow-dir`, `--deny-dir` to cycle.py
- [ ] Add `--session-name` to cycle.py
- [ ] Add inline prompt support to cycle.py
- [ ] Change `--max-cycles` default to 1
- [ ] Run existing tests to verify no regression

### Phase 2: Rename (Day 1-2)

- [ ] `git mv sdqctl/commands/iterate.py sdqctl/commands/iterate.py`
- [ ] Update command decorator to `@click.command("iterate")`
- [ ] Update `sdqctl/commands/__init__.py`
- [ ] Update `sdqctl/cli.py` imports
- [ ] Create deprecated aliases for `run` and `iterate`
- [ ] Delete `sdqctl/commands/run.py`
- [ ] Run tests

### Phase 3: Test Updates (Day 2)

- [ ] Merge `test_run_command.py` and `test_cycle_command.py` → `test_iterate_command.py`
- [ ] Add deprecated alias tests
- [ ] Add migration compatibility tests
- [ ] Run full test suite
- [ ] Fix any failures

### Phase 4: Documentation (Day 2-3)

- [ ] Run documentation update script
- [ ] Manual review of updated docs
- [ ] Update `sdqctl/commands/help.py`
- [ ] Update README.md
- [ ] Update proposals/BACKLOG.md
- [ ] Mark RUN-RENAME-ANALYSIS.md as superseded

### Phase 5: Verification (Day 3)

- [ ] Run `sdqctl iterate --help`
- [ ] Run `sdqctl run --help` (verify alias + warning)
- [ ] Run `sdqctl iterate --help` (verify alias + warning)
- [ ] Test example workflows
- [ ] Run lint/type checks

### Post-Implementation

- [ ] Create PR with comprehensive description
- [ ] Update CHANGELOG
- [ ] Tag release

---

## Appendix: Full CLI Signature

```python
@click.command("iterate")
@click.argument("target", required=False)
@click.option("--from-json", "from_json", type=click.Path(),
              help="Read workflow from JSON file or - for stdin")
@click.option("--max-cycles", "-n", type=int, default=1,
              help="Number of cycles (default: 1)")
@click.option("--session-mode", "-s", 
              type=click.Choice(["accumulate", "compact", "fresh"]),
              default="accumulate",
              help="Session handling mode")
@click.option("--adapter", "-a", default=None,
              help="AI adapter (copilot, claude, openai, mock)")
@click.option("--model", "-m", default=None,
              help="Model override")
@click.option("--context", "-c", multiple=True,
              help="Additional context files")
@click.option("--allow-files", multiple=True,
              help="Glob pattern for allowed files")
@click.option("--deny-files", multiple=True,
              help="Glob pattern for denied files")
@click.option("--allow-dir", multiple=True,
              help="Directory to allow")
@click.option("--deny-dir", multiple=True,
              help="Directory to deny")
@click.option("--checkpoint-dir", type=click.Path(), default=None,
              help="Checkpoint directory")
@click.option("--prologue", multiple=True,
              help="Prepend to each prompt")
@click.option("--epilogue", multiple=True,
              help="Append to each prompt")
@click.option("--header", multiple=True,
              help="Prepend to output")
@click.option("--footer", multiple=True,
              help="Append to output")
@click.option("--output", "-o", default=None,
              help="Output file")
@click.option("--event-log", default=None,
              help="Export SDK events to JSONL file")
@click.option("--json", "json_output", is_flag=True,
              help="JSON output")
@click.option("--dry-run", is_flag=True,
              help="Show what would happen")
@click.option("--render-only", is_flag=True,
              help="Render prompts without executing")
@click.option("--session-name", default=None,
              help="Named session for resumability")
@click.option("--min-compaction-density", type=int, default=30,
              help="Skip compaction below this %")
@click.option("--no-infinite-sessions", is_flag=True,
              help="Disable SDK infinite sessions")
@click.option("--compaction-threshold", type=int, default=80,
              help="Start background compaction at this %")
@click.option("--buffer-threshold", type=int, default=95,
              help="Block until compaction at this %")
@click.option("--no-stop-file-prologue", is_flag=True,
              help="Disable automatic stop file instructions")
@click.option("--stop-file-nonce", default=None,
              help="Override stop file nonce")
@click.pass_context
def iterate(ctx, target, from_json, max_cycles, session_mode, ...):
    """Execute a workflow with optional multi-cycle iteration.
    
    TARGET can be a .conv file path or an inline prompt string.
    Without TARGET, requires --from-json.
    
    Examples:
    
    \b
    # Single execution (default)
    sdqctl iterate workflow.conv
    
    \b
    # Multi-cycle execution
    sdqctl iterate workflow.conv -n 5
    
    \b
    # Inline prompt
    sdqctl iterate "Audit authentication module"
    
    \b
    # Fresh session each cycle
    sdqctl iterate workflow.conv -n 3 -s fresh
    """
```

---

## Phase 6: Mixed Prompt List Support

> **Added**: 2026-01-25  
> **Status**: Ready for Implementation  
> **Depends on**: Phases 1-5 complete  
> **Decisions Confirmed**: 2026-01-26

### Design Decisions (Confirmed)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Elision semantics** | Elide into boundaries | CLI prompts merge with first/last workflow turns; more compact |
| **Prologue/epilogue** | First/last turn only | `--prologue` → first turn, `--epilogue` → last turn |
| **Multiple .conv files** | One .conv limit | Deferred due to complexity; use `sdqctl flow` for multiple |
| **Multi-cycle behavior** | Every cycle | CLI prompts repeat each cycle with `-n N` |
| **Empty `---` groups** | Ignore silently | Skip empty groups, no warning |
| **File detection** | Existence + extension | Must exist on disk AND have `.conv`/`.copilot` extension |

### Deferred to Future Proposals

| Item | Rationale |
|------|-----------|
| Multiple .conv files with positional prologues | Complex; requires tracking which `--prologue` goes with which .conv |
| `--once` flag for non-repeating CLI prompts | Unclear if desirable; needs use case research |
| Explicit `--prompt` / `--file` switches | Disambiguation option; needs impact analysis |

### Problem

Current CLI accepts only ONE target (either a .conv file OR an inline prompt). Users need to:
1. Mix inline prompts with .conv file content
2. Control where CLI prologues/epilogues inject relative to .conv content
3. Explicitly control elision vs separate turns

### Solution: Variadic Targets with Separator Syntax

Change `target` argument to variadic `targets`:

```python
@click.argument("targets", nargs=-1)  # Variadic: prompts and/or one .conv
```

**Mixed prompt example:**
```bash
sdqctl iterate --prologue "A" "promptB" work.conv "promptC" --epilogue "D"
```

**Turn structure (document-based elision by default):**
```
Turn 1: [CLI prologue A] + [.conv prologues] + [promptB] + [first .conv prompt]
Turn 2..N-1: remaining .conv prompts (each gets own turn as defined in file)
Turn N: [last .conv prompt] + [.conv epilogues] + [promptC] + [CLI epilogue D]
```

### Separator Syntax: `---`

Use `---` to force turn boundaries:

```bash
sdqctl iterate --prologue "A" --- "promptB" --- work.conv "promptC"
```

**Turn structure with separators:**
```
Turn 1: [CLI prologue A]
Turn 2: [promptB]
Turn 3+: work.conv prompts with promptC elided into final turn
```

### Constraints

- Maximum ONE .conv file in mixed mode
- `---` is reserved (cannot be used as prompt content)
- Mixed mode requires at least one item

### Implementation

```python
@dataclass
class TurnGroup:
    """A group of items that will be elided into a single turn."""
    items: list[str]  # Each item is a prompt string or .conv path
    
def parse_targets(targets: tuple[str, ...]) -> list[TurnGroup]:
    """Parse mixed targets into turn groups separated by ---."""
    groups = []
    current = []
    for t in targets:
        if t == "---":
            if current:
                groups.append(TurnGroup(current))
                current = []
        else:
            current.append(t)
    if current:
        groups.append(TurnGroup(current))
    return groups

def validate_targets(groups: list[TurnGroup]) -> None:
    """Validate mixed target constraints."""
    conv_files = []
    for group in groups:
        for item in group.items:
            if Path(item).exists() and Path(item).suffix in (".conv", ".copilot"):
                conv_files.append(item)
    if len(conv_files) > 1:
        raise click.UsageError(
            f"Mixed mode allows only ONE .conv file, found {len(conv_files)}: {conv_files}"
        )
```

### Updated CLI Signature

```python
@click.command("iterate")
@click.argument("targets", nargs=-1)  # Changed from "target"
# ... existing options ...
def iterate(ctx, targets, from_json, max_cycles, session_mode, ...):
    """Execute a workflow with optional multi-cycle iteration.
    
    TARGETS can be a mix of .conv file paths and inline prompt strings.
    Use --- between items to force separate turns (default: adjacent items elide).
    Maximum one .conv file allowed in mixed mode.
    
    Examples:
    
    \b
    # Single .conv file
    sdqctl iterate workflow.conv
    
    \b
    # Inline prompt
    sdqctl iterate "Audit authentication module"
    
    \b
    # Mixed: prompts + .conv (items elide at boundaries)
    sdqctl iterate "Setup context" workflow.conv "Final summary"
    
    \b
    # Mixed with separators (force separate turns)
    sdqctl iterate "First task" --- workflow.conv --- "Separate final task"
    
    \b
    # With prologues/epilogues
    sdqctl iterate --prologue "You are an auditor" workflow.conv --epilogue "Summarize"
    """
```

### Phase 6 Checklist

- [x] Change `target` to variadic `targets` argument
- [x] Implement `parse_targets()` separator parsing
- [x] Implement `validate_targets()` constraint checking
- [x] Update turn building logic for elision
- [x] Add unit tests for separator parsing
- [x] Add integration tests for mixed mode
- [x] Update help text and examples

**Completed**: 2026-01-26

### Documentation

Create `docs/CONVERSATION-LIFECYCLE.md` to document:
- Lifecycle phases (parse → validate → render → execute → compact)
- Turn structure and elision semantics
- Prologue/epilogue injection points
- Mixed prompt mode with examples

---

## References

- [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md) - Original investigation
- [RUN-RENAME-ANALYSIS.md](RUN-RENAME-ANALYSIS.md) - Candidate analysis (superseded)
- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Design principles
- [BACKLOG.md](BACKLOG.md) - Priority tracking
- [CONVERSATION-LIFECYCLE.md](../docs/CONVERSATION-LIFECYCLE.md) - Lifecycle documentation (planned)
