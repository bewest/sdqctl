# Proposal: CLI Ergonomics & Help System

> **Status**: Draft (Naming Assessment Complete)  
> **Date**: 2026-01-23  
> **Author**: Ben West  
> **Scope**: Help system, command taxonomy, naming investigation  
> **Assessment Date**: 2026-01-23

---

## Summary

This proposal addresses three related concerns about sdqctl's command-line interface:

1. **Help System** - Add discoverable, topic-based help beyond `--help` flags
2. **Command Classification** - Clarify SDK-invoking vs tooling commands
3. **Naming Investigation** - Assess impact of renaming `run` command

---

## Motivation

sdqctl has grown to include multiple commands and ~40 directives. Users face several challenges:

### Discoverability
- `--help` provides syntax but not guidance
- Directive documentation scattered across docs/
- No way to ask "how do I use ELIDE effectively?"

### Semantic Confusion
- `sdqctl run` executes workflows with AI
- `RUN` directive executes shell commands
- These are unrelated but share a name

### Command Taxonomy
- Some commands invoke the SDK (expensive, require API keys)
- Some commands are local tooling (fast, no network)
- Users can't tell which is which without reading docs

---

## Proposal A: Help System

### Design

Two-tier help structure:

```bash
# Level 1: Command-specific help
sdqctl help                     # Overview + list of topics
sdqctl help run                 # Detailed help for 'run' command
sdqctl help cycle               # Detailed help for 'cycle' command

# Level 2: Guidance topics (conceptual documentation)
sdqctl help guidance            # List all guidance topics
sdqctl help guidance elide      # When and how to use ELIDE
sdqctl help guidance compaction # Context management strategies
sdqctl help guidance directives # Quick reference for all directives
```

### Help Content Sources

| Source | Content Type |
|--------|--------------|
| Embedded docstrings | Command syntax, options |
| `docs/*.md` files | Conceptual guidance |
| `proposals/*.md` | Design rationale |

### Initial Guidance Topics

1. **elide** - ELIDE directive usage patterns
2. **compaction** - When to compact, session modes
3. **context** - Context management, limits, on-context-limit
4. **directives** - Quick reference table
5. **workflows** - Writing effective .conv files
6. **run-vs-RUN** - Clarify command vs directive

### Implementation

```python
# sdqctl/commands/help.py
@cli.group()
def help():
    """Access documentation and guidance."""
    pass

@help.command()
@click.argument('topic', required=False)
def guidance(topic: Optional[str]):
    """Show guidance on a topic.
    
    Without TOPIC, lists available topics.
    With TOPIC, shows detailed guidance.
    """
    pass
```

---

## Proposal B: Command Classification

### SDK-Invoking Commands

These commands send prompts to AI and require API access:

| Command | Description | Typical Use |
|---------|-------------|-------------|
| `run` | Single prompt/workflow | Quick tasks |
| `cycle` | Multi-cycle with compaction | Extended analysis |
| `apply` | Workflow across components | Multi-file changes |
| `flow` | Parallel batch execution | Batch processing |

### Tooling Commands

These commands run locally without AI:

| Command | Description | Status |
|---------|-------------|--------|
| `render` | Preview resolved prompts | ✅ Implemented |
| `verify` | Run verifications | ✅ Implemented |
| `status` | Session/system info | ✅ Implemented |
| `help` | Documentation access | 🟡 Proposed |
| `validate` | Syntax checking | 🟡 Proposed |
| `show` | Display workflow structure | 🟡 Proposed |

### Gap Analysis Questions

1. Should `validate` be separate from `verify`?
   - `validate` = syntax/structure correctness
   - `verify` = semantic correctness (refs exist, links work)

2. Should `show` exist or is `render` sufficient?
   - `render` outputs resolved prompts
   - `show` could output metadata, step count, directives used

3. Should any tooling become directives?
   - VALIDATE as pre-flight check? (probably not - adds complexity)

---

## Proposal C: Run Command Naming

### Problem Statement

The name `run` is overloaded:

```bash
sdqctl run workflow.conv      # Yield control to AI for conversation
RUN pytest tests/             # Execute shell command (directive)
docker run image              # Start container (different semantics)
npm run script                # Execute package script (different semantics)
```

### Candidate Names

| Name | Description | Pros | Cons |
|------|-------------|------|------|
| `run` | Current name | Familiar | Conflicts with RUN directive |
| `yield` | Yield control to agent | Accurate semantics | Python keyword, unusual |
| `do` | Plan/do mental model | Short, intuitive | Possibly overloaded |
| `exec` | Execute workflow | Clear | Conflicts with shell exec |
| `prompt` | Send prompt to AI | Describes action | Doesn't fit multi-step workflows |
| `invoke` | Invoke workflow | Precise | Verbose |
| `converse` | Have conversation | Accurate | Long, unusual |

### Preferred Candidate: `yield`

**Rationale**: "Yielding control to the agent" accurately describes what happens:
- User surrenders control for the conversation duration
- Agent takes actions, user observes
- Control returns when conversation completes

**Concerns**:
- `yield` is a Python keyword (but valid as CLI command)
- Less familiar than `run`
- May need explanation for new users

### Impact Assessment Required

Before any rename, we need:

1. **Code Impact**
   - Files: `commands/run.py`, `cli.py`, tests
   - Imports and references
   - Backward compatibility (alias?)

2. **Documentation Impact**
   - README.md
   - GETTING-STARTED.md
   - All example workflows
   - External references

3. **User Impact**
   - Mental model shift
   - Muscle memory retraining
   - Existing scripts/automation

### Recommendation

**Investigate only** - Do not implement rename without:
1. Full impact assessment
2. User feedback
3. Deprecation/migration strategy

---

## Naming Assessment Results (2026-01-23)

> **Status**: ✅ Investigation Complete  
> **Recommendation**: `invoke` (safest) or keep `run` with documentation fix

### Code Impact Analysis

**Total References Found**: 128 occurrences across codebase

#### Python Files Requiring Modification

| File | Change Required |
|------|-----------------|
| `sdqctl/commands/run.py` | Rename to `{new}.py` |
| `sdqctl/commands/__init__.py` | Update import |
| `sdqctl/cli.py` (line 83) | Update `cli.add_command()` |
| `tests/test_run_command.py` | Rename test file |
| `tests/test_conversation.py` | Update import (`process_elided_steps`) |
| `tests/test_stop_file_existence_check.py` | Update import |
| `sdqctl/core/logging.py` | Update reference |

#### Documentation Files

| File | References |
|------|------------|
| `README.md` | 11 |
| `docs/GETTING-STARTED.md` | 9 |
| `docs/TRACEABILITY-WORKFLOW.md` | 6 |
| `docs/REVERSE-ENGINEERING.md` | 5 |
| `docs/IO-ARCHITECTURE.md` | 3 |
| `examples/workflows/*.conv` | 20+ files |
| `sdqctl/commands/help.py` | ~20 |

#### Additional Impact

- `render run` subcommand: 10+ references
- Entry point in `pyproject.toml`: `sdqctl = "sdqctl.cli:main"` (unchanged)

### Technical Conflict Analysis

#### Python Keyword/Builtin Status

```python
import keyword
yield: keyword.iskeyword('yield')  # True  - RESERVED
do:    keyword.iskeyword('do')     # False - Safe
exec:  keyword.iskeyword('exec')   # False - Builtin (shadows exec())
invoke: keyword.iskeyword('invoke') # False - Safe
```

#### Shell Keyword/Builtin Status

```bash
type yield   # not found - Safe
type do      # shell keyword (do...done) - CONFLICT
type exec    # shell builtin - CONFLICT
type invoke  # not found - Safe
```

### Detailed Candidate Evaluation

#### 1. YIELD ("yielding control to agent")

| Aspect | Rating | Notes |
|--------|--------|-------|
| Semantic Fit | ★★★★★ | Perfect - "surrender control to agent" |
| Technical | ★★☆☆☆ | Python keyword blocks implementation |
| Ecosystem | ★★★★☆ | Unique, no CLI precedent |
| User Experience | ★★★☆☆ | Unfamiliar verb |

**Critical Issue**: Python reserved keyword
```python
# These are SyntaxErrors:
from .yield import yield
def yield(): pass

# Must use workarounds:
# File: yield_cmd.py
# Function: yield_cmd()
# Import: from .yield_cmd import yield_cmd as yield_command
```

**Verdict**: Best semantics, HIGH implementation friction

#### 2. DO (plan/do mental model)

| Aspect | Rating | Notes |
|--------|--------|-------|
| Semantic Fit | ★★★☆☆ | Generic, maps to plan→do |
| Technical | ★★★★★ | Clean Python implementation |
| Ecosystem | ★★★☆☆ | Shell keyword creates friction |
| User Experience | ★★★★★ | Short (2 chars), intuitive |

**Shell Friction**:
```bash
# Visually confusing in loops:
for f in *.conv; do sdqctl do $f; done
#                ^^        ^^
```

**Verdict**: Best UX, shell keyword causes documentation friction

#### 3. EXEC (generic execution)

| Aspect | Rating | Notes |
|--------|--------|-------|
| Semantic Fit | ★★☆☆☆ | Same as "run" - no improvement |
| Technical | ★★★★☆ | Shadows Python builtin |
| Ecosystem | ★★☆☆☆ | Overloaded (docker exec, kubectl exec) |
| User Experience | ★★★☆☆ | Familiar but wrong mental model |

**Verdict**: NO ADVANTAGE over 'run' - NOT RECOMMENDED

#### 4. INVOKE (call a workflow)

| Aspect | Rating | Notes |
|--------|--------|-------|
| Semantic Fit | ★★★★☆ | "Trigger/delegate" - good for AI handoff |
| Technical | ★★★★★ | No Python/shell conflicts |
| Ecosystem | ★★★★☆ | AWS Lambda, PowerShell precedent |
| User Experience | ★★★☆☆ | Longer (6 chars), formal tone |

**Implementation**: Clean path
```python
# File: invoke.py
# Function: invoke()
# Import: from .invoke import invoke
# No workarounds needed
```

**Verdict**: SAFEST CHOICE - cleanest implementation

#### 5. RUN (keep current)

| Aspect | Rating | Notes |
|--------|--------|-------|
| Semantic Fit | ★★☆☆☆ | Conflicts with RUN directive |
| Technical | ★★★★★ | Already implemented |
| Ecosystem | ★★★★★ | Universal pattern |
| User Experience | ★★★★★ | Zero learning curve |

**Alternative Fix**: Add `sdqctl help run-vs-RUN` documentation topic

**Verdict**: LOWEST COST - address confusion via documentation

### Recommendation Matrix

| Criteria (1-5) | yield | do | exec | invoke | run |
|----------------|-------|-----|------|--------|-----|
| Technical safety | 3 | 4 | 3 | **5** | 5 |
| Semantic clarity | **5** | 4 | 2 | 4 | 2 |
| Ergonomics | 2 | **5** | 4 | 3 | 5 |
| Uniqueness | **5** | 3 | 1 | 4 | 1 |
| Migration cost | 2 | 3 | 3 | 4 | **5** |
| **TOTAL** | 17 | 19 | 13 | **20** | 18 |

### Backward Compatibility Options

#### Option A: Hard Rename (Breaking)

```python
# Simply rename, remove old command
cli.add_command(invoke)  # 'run' gone
```

- **User Impact**: HIGH - all scripts break
- **Maintenance**: None
- **Recommended For**: Pre-1.0 projects

#### Option B: Deprecation Period

```python
# In invoke.py:
@click.command("invoke")
@click.pass_context
def invoke(ctx, ...):
    if ctx.info_name == 'run':
        click.secho("⚠ 'run' deprecated, use 'invoke'", fg='yellow', err=True)
    # ... rest of command

# In cli.py:
cli.add_command(invoke)              # Primary
cli.add_command(invoke, name='run')  # Deprecated alias
```

- **User Impact**: LOW - scripts work, see warning
- **Maintenance**: Temporary (remove in v2.0)
- **Recommended For**: Mature projects

#### Option C: Permanent Alias

```python
cli.add_command(invoke)
cli.add_command(invoke, name='run')  # Silent, forever
```

- **User Impact**: NONE
- **Maintenance**: Forever
- **Recommended For**: Risk-averse projects

#### Option D: Hidden Alias (Recommended)

```python
cli.add_command(invoke)

@cli.command('run', hidden=True)
@click.pass_context
def run_alias(ctx):
    click.secho("⚠ 'run' deprecated, use 'invoke'", fg='yellow', err=True)
    ctx.invoke(invoke, **ctx.params)
```

- **User Impact**: LOW - scripts work, warning shown
- **Maintenance**: Temporary
- **Help Output**: Clean (run not shown)
- **Recommended For**: Mature projects

### Final Recommendation

```
IF renaming is desired:
  → Use 'invoke' (score: 20/25)
  → Use Option D (hidden alias with deprecation warning)
  
IF minimal disruption preferred:
  → Keep 'run'
  → Add 'sdqctl help run-vs-RUN' topic to clarify distinction
  → Document: "run command yields to agent; RUN directive executes shell"
```

### Decision Pending

User must decide:

1. **Command Name**: invoke / do / yield / keep run?
2. **Compatibility** (if renaming): A / B / C / D?

---

## Implementation Workflows

Three .conv files implement this proposal:

### 01-help-system.conv
- Design help command structure
- Implement `sdqctl help` and `sdqctl help guidance [topic]`
- Add initial guidance topics
- Tests and documentation

### 02-tooling-gap-analysis.conv
- Analyze proposals vs implementation
- Identify missing tooling commands
- Evaluate directive candidates
- Update BACKLOG.md

### 03-run-rename-assessment.conv
- Impact analysis for each candidate name
- Code grep for usage patterns
- Compatibility strategy options
- Recommendation with trade-offs

---

## Success Criteria

### Help System
- [ ] `sdqctl help` shows overview
- [ ] `sdqctl help guidance` lists topics
- [ ] `sdqctl help guidance <topic>` shows content
- [ ] At least 5 guidance topics available
- [ ] Tests for help command

### Gap Analysis
- [ ] Document all SDK vs tooling commands
- [ ] Decision on validate/show commands
- [ ] Updated BACKLOG.md

### Naming Assessment
- [x] Impact report for top 3 candidates
- [x] Backward compatibility strategy
- [x] Recommendation document
- [ ] User decision on command name
- [ ] User decision on compatibility option
- [ ] Implementation (if approved)

---

## Related Proposals

- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - verify command
- [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md) - render command

---

## References

- [GETTING-STARTED.md](../docs/GETTING-STARTED.md) - Current command docs
- [CONTEXT-MANAGEMENT.md](../docs/CONTEXT-MANAGEMENT.md) - Compaction guidance
- [FEATURE-INTERACTIONS.md](../docs/FEATURE-INTERACTIONS.md) - Directive interactions
