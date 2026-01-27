## Documentation Audit Results

I found several discrepancies between the README.md documentation and the actual code implementation:

---

### **Discrepancy 1: Missing `verify links` and `verify traceability` subcommands**

**Documentation (README.md:598-600)**:
```bash
# Verify markdown links
sdqctl verify links

# Verify STPA traceability (UCA→SC→REQ→SPEC→TEST)
sdqctl verify traceability
```

**Actual Code (sdqctl/commands/verify.py:27,40)**:
Only `refs` and `all` subcommands are registered:
```python
@verify.command("refs")   # line 27
@verify.command("all")    # line 40
```

The `LinksVerifier` and `TraceabilityVerifier` exist in `sdqctl/verifiers/__init__.py:11-12` but lack CLI commands.

**Fix**: Add `@verify.command("links")` and `@verify.command("traceability")` in `sdqctl/commands/verify.py`.

---

### **Discrepancy 2: Adapters `claude` and `openai` referenced but not implemented**

**Documentation (README.md:718-722)**:
```
| `claude` | `anthropic` | Anthropic Claude |
| `openai` | `openai` | OpenAI GPT |
```

**Actual Code (sdqctl/adapters/)**:
Only `base.py`, `copilot.py`, `mock.py`, and `registry.py` exist. No `claude.py` or `openai.py` files.

`sdqctl/adapters/registry.py:50-57` tries to import them but will silently fail:
```python
elif name == "claude":
    from .claude import ClaudeAdapter  # File doesn't exist
```

**Fix**: Either implement the adapters, or update README.md to note they are "planned" with a status indicator.

---

### **Discrepancy 3: `--render-only` documented but deprecated**

**Documentation (README.md:447-448)**:
```bash
sdqctl run workflow.conv --render-only  # Preview prompts, no AI calls
```

**Actual Code (sdqctl/commands/run.py:288)**:
The option exists but README.md:539 says:
> `--render-only` flag on `run` and `cycle` commands is deprecated.

**Fix**: README.md should consistently mark `--render-only` as deprecated in all examples, not just in one note.

---

### **Discrepancy 4: Session path mismatch for `resume --list`**

**Documentation (README.md:425)**:
```bash
sdqctl resume ~/.sdqctl/sessions/<session-id>/pause.json
```

**Actual Code (sdqctl/cli.py:597)**:
```python
sessions_dir = Path(".sdqctl/sessions")  # Relative path, not ~/.sdqctl
```

The documentation suggests home-directory paths (`~/.sdqctl/`) while code uses `.sdqctl/` (CWD-relative).

**Fix**: Update README.md:425 to use `.sdqctl/sessions/` instead of `~/.sdqctl/sessions/`.

---

### **Summary of Required Changes**

| File | Line | Issue | Severity |
|------|------|-------|----------|
| README.md | 598-600 | `verify links` and `verify traceability` commands don't exist as CLI subcommands | High |
| README.md | 718-722 | `claude` and `openai` adapters not implemented | Medium |
| README.md | 447, 459, 460 | `--render-only` examples should be deprecated | Low |
| README.md | 425 | Path `~/.sdqctl/` should be `.sdqctl/` | Low |
| commands/verify.py | 27-80 | Missing `links` and `traceability` subcommands | High |

---

Now let me generate the complete audit report:

## Documentation Audit Report

### 1. **Outdated API Documentation**

#### 1.1 Missing `verify links` and `verify traceability` CLI subcommands

| Location | Issue |
|----------|-------|
| **README.md:598-600** | Documents `sdqctl verify links` and `sdqctl verify traceability` |
| **sdqctl/commands/verify.py:27,40** | Only `refs` and `all` subcommands are registered |

**Evidence:** The verifiers exist in `sdqctl/verifiers/__init__.py:14-17`:
```python
VERIFIERS: dict[str, type] = {
    "refs": RefsVerifier,
    "links": LinksVerifier,
    "traceability": TraceabilityVerifier,
}
```
But CLI commands are not wired.

**Fix:** Add missing subcommands in `sdqctl/commands/verify.py`.

---

#### 1.2 `claude` and `openai` adapters documented but not implemented

| Location | Issue |
|----------|-------|
| **README.md:718-722** | Lists `claude` and `openai` adapters with packages |
| **sdqctl/adapters/** | Only `base.py`, `copilot.py`, `mock.py` exist |
| **sdqctl/adapters/registry.py:50-57** | Import will silently fail |

**Fix:** Add status column to adapter table: `claude` (planned), `openai` (planned).

---

#### 1.3 `--render-only` deprecated but still documented as primary option

| Location | Issue |
|----------|-------|
| **README.md:447-448, 458** | Shows `--render-only` in examples |
| **README.md:539** | Notes it's deprecated |

**Fix:** Update examples to use `sdqctl render run` instead.

---

### 2. **Missing Documentation**

#### 2.1 `validate` and `show` commands not in README

| Location | Issue |
|----------|-------|
| **sdqctl/cli.py:364-486, 488-535** | `validate` and `show` commands implemented |
| **README.md** | No section documenting these commands |

The commands are mentioned in generated help files (`.github/copilot-instructions.md`) but not in the main README.

**Fix:** Add `### sdqctl validate` and `### sdqctl show` sections.

---

#### 2.2 Missing CLI options in README documentation

| Command | Missing Options in README |
|---------|--------------------------|
| `run` | `--allow-files`, `--deny-files`, `--allow-dir`, `--deny-dir`, `--context`, `--min-compaction-density`, `--event-log` |
| `cycle` | `--from-json`, `--checkpoint-dir`, `--min-compaction-density`, `--event-log` |
| `apply` | `--from-discovery`, `--event-log` |
| `refcat` | `--from-workflow`, `--list-files`, `--absolute`, `--relative-to`, `--no-cwd` |

**Evidence:** Compare `sdqctl/commands/run.py:273-292` against README.md:443-448.

---

#### 2.3 Missing directives in README table

| Directive | Location in Code | Missing from README |
|-----------|------------------|---------------------|
| `CONTEXT-OPTIONAL` | conversation.py:35 | ❌ Not documented |
| `CONTEXT-EXCLUDE` | conversation.py:36 | ❌ Not documented |
| `VALIDATION-MODE` | conversation.py:41 | ❌ Not documented |
| `ALLOW-FILES`/`DENY-FILES` | conversation.py:44-45 | ❌ Not documented |
| `ALLOW-DIR`/`DENY-DIR` | conversation.py:46-47 | ❌ Not documented |
| `DEBUG` | conversation.py:106 | ❌ Not documented |
| `DEBUG-INTENTS` | conversation.py:107 | ❌ Not documented |
| `EVENT-LOG` | conversation.py:108 | ❌ Not documented |
| `RUN-ASYNC`/`RUN-WAIT` | conversation.py:92-93 | ❌ Not documented |
| `NEW-CONVERSATION` | conversation.py:63 | ❌ Not documented |
| `COMPACT-SUMMARY` | conversation.py:60 | ❌ Not documented |
| `CHECKPOINT`/`CHECKPOINT-NAME` | conversation.py:69-71 | ❌ Not documented |
| `OUTPUT`/`OUTPUT-DIR` | conversation.py:78, 81 | ❌ Not documented |
| `CWD` | conversation.py:31 | ❌ Not documented |

---

### 3. **Broken Code Examples**

#### 3.1 Session path mismatch

| Location | Issue |
|----------|-------|
| **README.md:425** | `~/.sdqctl/sessions/<session-id>/pause.json` |
| **sdqctl/cli.py:597** | `sessions_dir = Path(".sdqctl/sessions")` (CWD-relative) |

**Fix:** Change `~/.sdqctl/` to `.sdqctl/` in documentation.

---

#### 3.2 Alias file location undocumented/unimplemented

| Location | Issue |
|----------|-------|
| **README.md:687-688** | References `~/.sdqctl/aliases.yaml` |
| **sdqctl/** | No code loads alias configuration |

This is aspirational documentation - the alias feature is proposed but not implemented.

---

### 4. **Inconsistent Terminology**

| Term 1 | Term 2 | Locations |
|--------|--------|-----------|
| "ConversationFile" (class) | "workflow file" | Mixed usage throughout |
| ".conv file" | "workflow" | README uses both interchangeably |
| "prompt injection" | "PROLOGUE/EPILOGUE" | GETTING-STARTED.md vs README.md |
| `on_context_limit` | `ON-CONTEXT-LIMIT` | Code uses snake_case, docs use SCREAMING-KEBAB |

**Recommendation:** Standardize on:
- "workflow file" or "ConversationFile" (pick one for user-facing docs)
- "PROLOGUE/EPILOGUE directives" for the mechanism
- Directive names always as `SCREAMING-KEBAB-CASE`

---

### 5. **Summary Table**

| Category | Count | Severity |
|----------|-------|----------|
| Outdated API docs | 3 | High |
| Missing documentation | 3 | Medium |
| Broken examples | 2 | Medium |
| Inconsistent terminology | 4 | Low |

---

Now I have all the context needed. Here's the detailed audit report:

---

## Detailed Documentation Audit Report

---

### Issue 1: Missing `verify links` and `verify traceability` CLI subcommands

**Location:** `README.md:599-603`

**Current documentation text:**
```bash
# Verify markdown links
sdqctl verify links

# Verify STPA traceability (UCA→SC→REQ→SPEC→TEST)
sdqctl verify traceability
```

**What the code actually does:**
`sdqctl/commands/verify.py:21-45` only registers two subcommands:
```python
@verify.command("refs")     # line 27
@verify.command("all")      # line 40
```

Running `sdqctl verify links` returns:
```
Error: No such command 'links'.
```

The verifiers exist (`sdqctl/verifiers/__init__.py:14-17`) but are not exposed as CLI commands.

**Suggested fix for `sdqctl/commands/verify.py`:**
Add after line 37:
```python
@verify.command("links")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", 
              help="Directory to verify")
def verify_links(json_output: bool, verbose: bool, path: str):
    """Verify markdown links resolve correctly."""
    verifier = VERIFIERS["links"]()
    result = verifier.verify(Path(path))
    _output_result(result, json_output, verbose, "links")


@verify.command("traceability")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Show all findings")
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Directory to verify")
def verify_traceability(json_output: bool, verbose: bool, path: str):
    """Verify STPA traceability chain (UCA→SC→REQ→SPEC→TEST)."""
    verifier = VERIFIERS["traceability"]()
    result = verifier.verify(Path(path))
    _output_result(result, json_output, verbose, "traceability")
```

---

### Issue 2: `claude` and `openai` adapters documented but not implemented

**Location:** `README.md:718-723`

**Current documentation text:**
```markdown
| Adapter | Package | Description |
|---------|---------|-------------|
| `mock` | Built-in | Testing adapter |
| `copilot` | `github-copilot-sdk` | GitHub Copilot CLI |
| `claude` | `anthropic` | Anthropic Claude |
| `openai` | `openai` | OpenAI GPT |
```

**What the code actually does:**
`sdqctl/adapters/` directory contains only:
- `base.py`
- `copilot.py`  
- `mock.py`
- `registry.py`

No `claude.py` or `openai.py` files exist. `registry.py:50-57` attempts to import them but silently fails.

**Suggested fix for `README.md:718-723`:**
```markdown
| Adapter | Package | Description | Status |
|---------|---------|-------------|--------|
| `mock` | Built-in | Testing adapter | ✅ Available |
| `copilot` | `github-copilot-sdk` | GitHub Copilot CLI | ✅ Available |
| `claude` | `anthropic` | Anthropic Claude | 🔜 Planned |
| `openai` | `openai` | OpenAI GPT | 🔜 Planned |
```

---

### Issue 3: `--render-only` deprecated but shown in examples

**Location:** `README.md:448, 458`

**Current documentation text:**
```bash
sdqctl run workflow.conv --render-only  # Preview prompts, no AI calls
sdqctl cycle workflow.conv -n 3 --render-only  # Preview all cycles
```

**What the code actually does:**
The flag exists and works, but `README.md:539` says:
> `--render-only` flag on `run` and `cycle` commands is deprecated.
> Use `sdqctl render run` or `sdqctl render cycle` instead.

**Suggested fix for `README.md:447-449`:**
```bash
sdqctl run "Analyze this codebase"
sdqctl run workflow.conv --adapter copilot
sdqctl run workflow.conv --dry-run
```

**Suggested fix for `README.md:456-459`:**
```bash
sdqctl cycle workflow.conv --max-cycles 5
sdqctl cycle workflow.conv --checkpoint-dir ./checkpoints
sdqctl cycle workflow.conv -n 3  # Use 'sdqctl render cycle' to preview
```

---

### Issue 4: Session path uses `~/.sdqctl/` but code uses `.sdqctl/`

**Location:** `README.md:425`

**Current documentation text:**
```bash
sdqctl resume ~/.sdqctl/sessions/<session-id>/pause.json
```

**What the code actually does:**
`sdqctl/cli.py:597`:
```python
sessions_dir = Path(".sdqctl/sessions")  # CWD-relative, not home directory
```

**Suggested fix for `README.md:425`:**
```bash
sdqctl resume .sdqctl/sessions/<session-id>/pause.json
```

---

### Issue 5: Alias file feature documented but not implemented

**Location:** `README.md:687-688`

**Current documentation text:**
```bash
# With alias (defined in ~/.sdqctl/aliases.yaml)
sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

**What the code actually does:**
No code in `sdqctl/` loads or parses `~/.sdqctl/aliases.yaml`. The `refcat` command (`sdqctl/commands/refcat.py`) does not implement alias resolution.

**Suggested fix for `README.md:684-691`:**
```markdown
For cross-repository workflows, aliases can be used (planned feature):

```bash
# Planned: With alias (defined in ~/.sdqctl/aliases.yaml)
# sdqctl refcat loop:LoopKit/Sources/Algorithm.swift#L100-L200
```

See `proposals/REFCAT-DESIGN.md` for the alias specification.
```

---

### Issue 6: `validate` and `show` commands not documented in README

**Location:** README.md (missing section)

**Current documentation text:**
Not present. Commands section jumps from `help` to Adapters.

**What the code actually does:**
`sdqctl/cli.py:364-486` implements `validate`:
```python
@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
@click.option("--allow-missing", is_flag=True, ...)
@click.option("--exclude", "-e", multiple=True, ...)
@click.option("--strict", is_flag=True, ...)
@click.option("--json", "json_output", is_flag=True, ...)
def validate(workflow: str, allow_missing: bool, exclude: tuple, strict: bool, json_output: bool):
```

`sdqctl/cli.py:488-535` implements `show`:
```python
@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
def show(workflow: str):
```

**Suggested fix:** Add after `### sdqctl help` section (around line 710):

```markdown
### `sdqctl validate`

Validate a ConversationFile without executing:

```bash
sdqctl validate workflow.conv
sdqctl validate workflow.conv --allow-missing
sdqctl validate workflow.conv --exclude "conformance/**/*.yaml"
sdqctl validate workflow.conv -e "*.yaml" -e "mapping/*"
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

### Issue 7: Missing directives in README table

**Location:** `README.md:159-196`

**Current documentation text:**
Table lists 28 directives.

**What the code actually does:**
`sdqctl/core/conversation.py:23-108` defines 44 directive types.

**Missing directives:**

| Directive | Code Location | Purpose |
|-----------|---------------|---------|
| `CONTEXT-OPTIONAL` | conversation.py:35 | Optional context (warn if missing) |
| `CONTEXT-EXCLUDE` | conversation.py:36 | Exclude patterns from validation |
| `VALIDATION-MODE` | conversation.py:41 | strict, lenient, exploratory |
| `ALLOW-FILES` | conversation.py:44 | Glob pattern for allowed files |
| `DENY-FILES` | conversation.py:45 | Glob pattern for denied files |
| `ALLOW-DIR` | conversation.py:46 | Directory to allow |
| `DENY-DIR` | conversation.py:47 | Directory to deny |
| `CWD` | conversation.py:31 | Working directory for workflow |
| `NEW-CONVERSATION` | conversation.py:63 | Start fresh conversation |
| `CHECKPOINT` | conversation.py:69 | Create named checkpoint |
| `CHECKPOINT-NAME` | conversation.py:71 | Name for checkpoint |
| `COMPACT-SUMMARY` | conversation.py:60 | Custom compaction summary |
| `OUTPUT` | conversation.py:78 | Alias for OUTPUT-FILE |
| `OUTPUT-DIR` | conversation.py:81 | Output directory |
| `RUN-ASYNC` | conversation.py:92 | Run command in background |
| `RUN-WAIT` | conversation.py:93 | Wait/sleep duration |
| `DEBUG` | conversation.py:106 | Debug categories |
| `DEBUG-INTENTS` | conversation.py:107 | Enable intent tracking |
| `EVENT-LOG` | conversation.py:108 | Path for event export |

**Suggested fix:** Add to README.md directives table:
```markdown
| `CONTEXT-OPTIONAL` | Include file/pattern (warn if missing, don't fail) |
| `CONTEXT-EXCLUDE` | Pattern to exclude from validation |
| `VALIDATION-MODE` | Validation strictness (strict, lenient) |
| `CWD` | Working directory for workflow |
| `DEBUG` | Debug categories (session, tool, intent, event) |
| `EVENT-LOG` | Export SDK events to file |
```

---

### Issue 8: Missing CLI options not documented

**Location:** `README.md:440-449` (run command section)

**Current documentation text:**
```bash
sdqctl run "Analyze this codebase"
sdqctl run workflow.conv --adapter copilot
sdqctl run workflow.conv --dry-run
sdqctl run workflow.conv --render-only  # Preview prompts, no AI calls
```

**What the code actually does:**
`sdqctl/commands/run.py:273-292` defines many more options:
```python
@click.option("--context", "-c", multiple=True, ...)
@click.option("--allow-files", multiple=True, ...)
@click.option("--deny-files", multiple=True, ...)
@click.option("--allow-dir", multiple=True, ...)
@click.option("--deny-dir", multiple=True, ...)
@click.option("--event-log", default=None, ...)
@click.option("--min-compaction-density", type=int, default=0, ...)
@click.option("--no-stop-file-prologue", is_flag=True, ...)
@click.option("--stop-file-nonce", default=None, ...)
```

**Suggested fix:** Add to README.md run command section:
```bash
# Additional options
sdqctl run workflow.conv --context @extra-file.md  # Add context
sdqctl run workflow.conv --allow-files "*.py"       # File restrictions
sdqctl run workflow.conv --event-log events.jsonl   # Export events
sdqctl run workflow.conv --no-stop-file-prologue    # Disable stop file
```

---

### Issue 9: `refcat` missing options in README

**Location:** `README.md:643-671`

**Current documentation text:**
Shows `--json`, `--validate-only`, `--no-line-numbers`

**What the code actually does:**
`sdqctl/commands/refcat.py:105-149` defines additional options:
```python
@click.option("--no-cwd", is_flag=True, ...)
@click.option("--absolute", is_flag=True, ...)
@click.option("--relative-to", type=click.Path(...), ...)
@click.option("--from-workflow", type=click.Path(...), ...)
@click.option("--list-files", is_flag=True, ...)
```

**Suggested fix for `README.md:647-671`:**
```bash
# Extract specific lines
sdqctl refcat @path/file.py#L10-L50

# Glob pattern - list matching files
sdqctl refcat "@docs/*.md" --list-files

# Extract all context from a workflow
sdqctl refcat --from-workflow workflows/audit.conv

# JSON output for scripting
sdqctl refcat @file.py#L10-L50 --json

# Show absolute paths
sdqctl refcat @file.py#L10-L50 --absolute

# Validate refs without output
sdqctl refcat @file.py#L10-L50 --validate-only
```

---

### Summary of Required Changes

| File | Lines | Action | Priority |
|------|-------|--------|----------|
| `sdqctl/commands/verify.py` | 37+ | Add `links` and `traceability` commands | High |
| `README.md` | 718-723 | Add Status column to adapters table | Medium |
| `README.md` | 448, 458 | Remove `--render-only` examples | Low |
| `README.md` | 425 | Change `~/.sdqctl/` to `.sdqctl/` | Medium |
| `README.md` | 684-691 | Mark alias feature as planned | Low |
| `README.md` | ~710 | Add `validate` and `show` sections | High |
| `README.md` | 159-196 | Add missing directives | Medium |
| `README.md` | 440-449 | Document additional run options | Low |
| `README.md` | 647-671 | Document additional refcat options | Low |

---

## Documentation Sync Audit Complete

Report saved to: `reports/documentation-sync-audit-2026-01-24.md`

### Summary by Severity

| Severity | Count | Key Issues |
|----------|-------|------------|
| 🔴 **Critical** | 1 | `verify links` and `verify traceability` commands don't exist |
| 🟠 **High** | 4 | Adapters not implemented, `validate`/`show` undocumented, wrong paths, 16 missing directives |
| 🟡 **Medium** | 6 | Alias feature not implemented, deprecated flag in examples, underdocumented options |
| 🟢 **Low** | 4 | Terminology and formatting inconsistencies |

### Immediate Actions Required

1. **C-001**: Add `verify links` and `verify traceability` CLI commands to `sdqctl/commands/verify.py`
2. **H-002**: Add `validate` and `show` command sections to README.md
3. **H-001**: Mark `claude`/`openai` adapters as "Planned" in README.md
4. **H-003**: Fix session path from `~/.sdqctl/` to `.sdqctl/`