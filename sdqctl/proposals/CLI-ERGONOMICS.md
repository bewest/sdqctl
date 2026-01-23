# Proposal: CLI Ergonomics & Help System

> **Status**: Draft  
> **Date**: 2026-01-23  
> **Author**: Ben West  
> **Scope**: Help system, command taxonomy, naming investigation

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

| Command | Description | Typical Duration |
|---------|-------------|------------------|
| `run` | Single prompt/workflow | Seconds to minutes |
| `cycle` | Multi-cycle with compaction | Minutes to hours |
| `apply` | Workflow across components | Minutes to hours |
| `flow` | Parallel batch execution | Varies |

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
- [ ] Impact report for top 3 candidates
- [ ] Backward compatibility strategy
- [ ] Recommendation document

---

## Related Proposals

- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - verify command
- [PIPELINE-ARCHITECTURE.md](PIPELINE-ARCHITECTURE.md) - render command

---

## References

- [GETTING-STARTED.md](../docs/GETTING-STARTED.md) - Current command docs
- [CONTEXT-MANAGEMENT.md](../docs/CONTEXT-MANAGEMENT.md) - Compaction guidance
- [FEATURE-INTERACTIONS.md](../docs/FEATURE-INTERACTIONS.md) - Directive interactions
