# Documentation Sync Audit Report

**Generated:** 2026-01-24T00:58:55Z  
**Auditor:** sdqctl documentation auditor  
**Scope:** README.md, docs/*.md vs sdqctl/**/*.py

---

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 1 | Completely wrong information |
| 🟠 High | 4 | Outdated after breaking changes |
| 🟡 Medium | 6 | Minor inconsistencies |
| 🟢 Low | 4 | Style or formatting issues |
| **Total** | **15** | |

---

## 🔴 Critical Issues

### C-001: `verify links` and `verify traceability` commands don't exist

**Location:** `README.md:599-603`

**Current documentation:**
```bash
# Verify markdown links
sdqctl verify links

# Verify STPA traceability (UCA→SC→REQ→SPEC→TEST)
sdqctl verify traceability
```

**Actual behavior:**
```
$ sdqctl verify links
Error: No such command 'links'.

$ sdqctl verify traceability  
Error: No such command 'traceability'.
```

**Code reference:** `sdqctl/commands/verify.py:27,40` - Only `refs` and `all` subcommands registered

**Impact:** Users following documentation will get errors. The verifiers exist in code (`sdqctl/verifiers/__init__.py:14-17`) but are not exposed via CLI.

**Fix required:** Add CLI commands in `sdqctl/commands/verify.py`:
```python
@verify.command("links")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".")
def verify_links(json_output: bool, verbose: bool, path: str):
    """Verify markdown links resolve correctly."""
    verifier = VERIFIERS["links"]()
    result = verifier.verify(Path(path))
    _output_result(result, json_output, verbose, "links")

@verify.command("traceability")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".")
def verify_traceability(json_output: bool, verbose: bool, path: str):
    """Verify STPA traceability chain."""
    verifier = VERIFIERS["traceability"]()
    result = verifier.verify(Path(path))
    _output_result(result, json_output, verbose, "traceability")
```

---

## 🟠 High Severity Issues

### H-001: `claude` and `openai` adapters listed but not implemented

**Location:** `README.md:718-723`

**Current documentation:**
```markdown
| `claude` | `anthropic` | Anthropic Claude |
| `openai` | `openai` | OpenAI GPT |
```

**Actual behavior:** No `claude.py` or `openai.py` files exist in `sdqctl/adapters/`. The registry (`sdqctl/adapters/registry.py:50-57`) attempts to import them but silently fails.

**Impact:** Users expect these adapters to work; `sdqctl run --adapter claude` silently falls back or errors.

**Fix required:** Update `README.md:718-723`:
```markdown
| Adapter | Package | Description | Status |
|---------|---------|-------------|--------|
| `mock` | Built-in | Testing adapter | ✅ Available |
| `copilot` | `github-copilot-sdk` | GitHub Copilot CLI | ✅ Available |
| `claude` | `anthropic` | Anthropic Claude | 🔜 Planned |
| `openai` | `openai` | OpenAI GPT | 🔜 Planned |
```

---

### H-002: `validate` and `show` commands undocumented in README

**Location:** `README.md` (missing section between lines 710-715)

**Current documentation:** Not present. Commands section has no `validate` or `show`.

**Actual behavior:** Both commands are fully implemented:
- `sdqctl/cli.py:364-486` - `validate` command
- `sdqctl/cli.py:488-535` - `show` command

**Impact:** Users unaware of validation tooling; CI/CD integration guidance missing.

**Fix required:** Add to README.md after `### sdqctl help` section:
```markdown
### `sdqctl validate`

Validate a ConversationFile without executing:

```bash
sdqctl validate workflow.conv
sdqctl validate workflow.conv --allow-missing
sdqctl validate workflow.conv --exclude "*.yaml"
sdqctl validate workflow.conv --strict
sdqctl validate workflow.conv --json
```

### `sdqctl show`

Display parsed representation of a workflow:

```bash
sdqctl show workflow.conv
```
```

---

### H-003: Session checkpoint path incorrect

**Location:** `README.md:425`

**Current documentation:**
```bash
sdqctl resume ~/.sdqctl/sessions/<session-id>/pause.json
```

**Actual behavior:** `sdqctl/cli.py:597`:
```python
sessions_dir = Path(".sdqctl/sessions")  # CWD-relative
```

**Impact:** Users looking in wrong location for checkpoints; resume instructions fail.

**Fix required:** Update `README.md:425`:
```bash
sdqctl resume .sdqctl/sessions/<session-id>/pause.json
```

---

### H-004: 16 directives implemented but not documented

**Location:** `README.md:159-196`

**Current documentation:** Lists 28 directives

**Actual behavior:** `sdqctl/core/conversation.py:23-108` defines 44 directive types

**Missing directives:**

| Directive | Code Line | Purpose |
|-----------|-----------|---------|
| `CONTEXT-OPTIONAL` | 35 | Optional context (warn if missing) |
| `CONTEXT-EXCLUDE` | 36 | Exclude patterns from validation |
| `VALIDATION-MODE` | 41 | strict, lenient, exploratory |
| `ALLOW-FILES` | 44 | Glob pattern for allowed files |
| `DENY-FILES` | 45 | Glob pattern for denied files |
| `ALLOW-DIR` | 46 | Directory to allow |
| `DENY-DIR` | 47 | Directory to deny |
| `CWD` | 31 | Working directory for workflow |
| `NEW-CONVERSATION` | 63 | Start fresh conversation |
| `CHECKPOINT` | 69 | Create named checkpoint |
| `CHECKPOINT-NAME` | 71 | Name for checkpoint |
| `COMPACT-SUMMARY` | 60 | Custom compaction summary |
| `OUTPUT` | 78 | Alias for OUTPUT-FILE |
| `OUTPUT-DIR` | 81 | Output directory |
| `RUN-ASYNC` | 92 | Run command in background |
| `RUN-WAIT` | 93 | Wait/sleep duration |
| `DEBUG` | 106 | Debug categories |
| `DEBUG-INTENTS` | 107 | Enable intent tracking |
| `EVENT-LOG` | 108 | Path for event export |

**Impact:** Users unaware of available features for validation control, debugging, async commands.

**Fix required:** Add missing directives to README.md table.

---

## 🟡 Medium Severity Issues

### M-001: Alias feature documented but not implemented

**Location:** `README.md:687-688`

**Current documentation:**
```bash
# With alias (defined in ~/.sdqctl/aliases.yaml)
sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

**Actual behavior:** No code loads `~/.sdqctl/aliases.yaml`. The `refcat` command does not implement alias resolution.

**Impact:** Users may create alias files that are never loaded.

**Fix required:** Update `README.md:684-691`:
```markdown
For cross-repository workflows, aliases are planned:

```bash
# Planned feature (not yet implemented)
# sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

See `proposals/REFCAT-DESIGN.md` for the alias specification.
```

---

### M-002: `--render-only` deprecated but in examples

**Location:** `README.md:448, 458`

**Current documentation:**
```bash
sdqctl run workflow.conv --render-only  # Preview prompts, no AI calls
sdqctl cycle workflow.conv -n 3 --render-only  # Preview all cycles
```

**Actual behavior:** Flag works but `README.md:539` says it's deprecated.

**Impact:** Inconsistent guidance; users may use deprecated pattern.

**Fix required:** Remove `--render-only` from examples, add comment:
```bash
sdqctl run workflow.conv --dry-run
# For prompt preview, use: sdqctl render run workflow.conv
```

---

### M-003: `refcat` options underdocumented

**Location:** `README.md:647-671`

**Current documentation:** Shows only `--json`, `--validate-only`, `--no-line-numbers`

**Actual behavior:** `sdqctl/commands/refcat.py:105-149` defines 9 options:
- `--json`
- `--no-line-numbers`
- `--no-cwd`
- `--absolute`
- `--relative-to`
- `-q/--quiet`
- `--validate-only`
- `--from-workflow`
- `--list-files`

**Impact:** Users missing useful options for scripting.

**Fix required:** Add examples:
```bash
sdqctl refcat "@docs/*.md" --list-files
sdqctl refcat --from-workflow audit.conv --list-files
sdqctl refcat @file.py --absolute
```

---

### M-004: `run` command options underdocumented

**Location:** `README.md:443-449`

**Current documentation:** Shows only `--adapter`, `--dry-run`, `--render-only`

**Actual behavior:** `sdqctl/commands/run.py:273-292` defines 15 options including:
- `--context`, `-c`
- `--allow-files`, `--deny-files`
- `--allow-dir`, `--deny-dir`
- `--event-log`
- `--min-compaction-density`
- `--no-stop-file-prologue`
- `--stop-file-nonce`

**Impact:** Users unaware of file restriction and event logging features.

**Fix required:** Add key options to examples.

---

### M-005: `cycle` command options underdocumented

**Location:** `README.md:455-459`

**Current documentation:** Shows `--max-cycles`, `--checkpoint-dir`, `--render-only`

**Actual behavior:** `sdqctl/commands/cycle.py:56-76` defines:
- `--from-json`
- `--session-mode`
- `--event-log`
- `--min-compaction-density`
- `--no-stop-file-prologue`
- `--stop-file-nonce`

**Impact:** Pipeline integration features (`--from-json`) not visible.

---

### M-006: `apply` command options underdocumented

**Location:** `README.md:553-564`

**Current documentation:** Shows `--components`, `--progress`, `--parallel`, `--output-dir`

**Actual behavior:** `sdqctl/commands/apply.py:39-53` also defines:
- `--from-discovery`
- `--no-stop-file-prologue`
- `--stop-file-nonce`

---

## 🟢 Low Severity Issues

### L-001: Inconsistent terminology for workflow files

**Locations:** Throughout README.md and docs/*.md

**Issue:** Mixed usage of:
- "ConversationFile" (class name)
- "workflow file"
- ".conv file"
- "workflow"

**Impact:** Minor confusion for new users.

**Fix:** Standardize on "workflow file" for user-facing docs, reserve "ConversationFile" for API references.

---

### L-002: Directive table formatting inconsistent

**Location:** `README.md:159-196`

**Issue:** Some descriptions have parenthetical options, others don't:
- `MODE` → "Execution mode (audit, read-only, full)"
- `COMPACT` → "Trigger compaction (with optional preserve list)"
- `CONTEXT` → "Include file/pattern" (no options shown)

**Fix:** Consistent format: `Directive` → "Brief description (options if applicable)"

---

### L-003: GETTING-STARTED.md adapter list inconsistent with README

**Location:** `docs/GETTING-STARTED.md:198`

**Current documentation:**
```dockerfile
ADAPTER copilot                # Provider (copilot, mock, claude, openai)
```

**Issue:** Lists `claude` and `openai` which are not implemented.

**Fix:** Update to `(copilot, mock)` or add "(planned: claude, openai)"

---

### L-004: Code examples use inconsistent quoting

**Location:** Various README.md examples

**Issue:** Some use double quotes, some single:
```bash
sdqctl apply audit.conv --components "lib/plugins/*.js"
sdqctl refcat @path/file.py#/def my_func/
```

**Fix:** Standardize on double quotes for glob patterns and pattern arguments.

---

## Verification Commands

Run these to verify fixes:

```bash
# Check verify subcommands exist
sdqctl verify --help

# Check all documented commands work
sdqctl validate --help
sdqctl show --help
sdqctl refcat --help

# Verify session paths
ls -la .sdqctl/sessions/

# Check adapter availability
sdqctl status --adapters
```

---

## Recommended Fix Priority

1. **Immediate (before next release):**
   - C-001: Add `verify links` and `verify traceability` commands
   - H-002: Document `validate` and `show` commands

2. **Soon (this week):**
   - H-001: Add status column to adapters table
   - H-003: Fix session path documentation
   - H-004: Document missing directives

3. **When convenient:**
   - M-001 through M-006: Update option documentation
   - L-001 through L-004: Style consistency

---

## Files Requiring Changes

| File | Changes Needed |
|------|----------------|
| `sdqctl/commands/verify.py` | Add `links` and `traceability` commands |
| `README.md` | 9 sections need updates |
| `docs/GETTING-STARTED.md` | Update adapter list |

---

*Report generated by sdqctl documentation auditor*
