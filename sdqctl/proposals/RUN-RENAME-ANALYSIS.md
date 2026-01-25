# `run` Command Rename Analysis

> **Status**: Draft - Needs User Research  
> **Created**: 2026-01-24  
> **Priority**: P2 (Deferred)  
> **Related**: [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md)

---

## Problem Statement

The `run` command name is overloaded in developer mental models:

| Context | "run" means |
|---------|-------------|
| sdqctl | Execute single workflow iteration |
| Shell | Execute a command (`./run.sh`) |
| npm/go | Execute script/binary (`npm run`, `go run`) |
| Tests | Execute test suite (`pytest`, `run tests`) |
| RUN directive | Execute shell command within workflow |

This creates potential confusion, especially with the `RUN` directive inside `.conv` files.

---

## Philosophy Constraints

From [PHILOSOPHY.md](../docs/PHILOSOPHY.md):

> "ConversationFile should NOT become a programming language. It should stay simple."

This rules out:
- `eval` - Too programmatic
- `exec` - Shell/process connotation
- `execute` - Same issue, verbose

---

## Candidates

### Shortlisted

| Candidate | Philosophy Fit | Pros | Cons |
|-----------|---------------|------|------|
| `run` (keep) | Neutral | Familiar, stable, ecosystem standard | Overloaded with RUN directive |
| `invoke` | Good | Clear verb, "invoke a conversation" | Slightly formal, 6 chars |
| `do` | Simple | Short, imperative, "do this workflow" | Generic, shell conflict (`do` keyword) |
| `yield` | Interesting | "Yield control to AI" | Unfamiliar, generator connotation |
| `converse` | Excellent | Perfect philosophy match | Long (8 chars), less action-oriented |
| `start` | Good | Clear, familiar | Implies long-running process |
| `go` | Simple | Short, familiar | Conflicts with Go language |

### Ruled Out

| Candidate | Reason |
|-----------|--------|
| `flow` | Already used for parallel execution |
| `exec` | Too programmatic |
| `eval` | Too programmatic |
| `call` | Function call connotation |

---

## Analysis Needed

### 1. User Perception Study

Survey existing users:
- What do you expect `sdqctl run` to do?
- Does `sdqctl invoke` feel natural?
- Does `yield` make sense for "AI takes over"?

### 2. Ecosystem Comparison

| Tool | Single execution | Multi execution | Parallel |
|------|------------------|-----------------|----------|
| sdqctl | `run` | `cycle` | `flow` |
| npm | `run` | - | - |
| make | (default) | - | `-j` |
| docker | `run` | - | compose |
| ansible | `ansible` | - | `ansible-playbook` |
| terraform | `apply` | - | - |

### 3. Migration Cost

If renaming:
- Update 40+ example files
- Update all documentation
- Provide compatibility alias
- Communicate to existing users

---

## Compatibility Options (if renaming)

| Option | Behavior | Migration Period |
|--------|----------|------------------|
| A) Hard rename | Remove `run` immediately | None (breaking) |
| B) Alias | Both work forever | Permanent |
| C) Deprecation | Warn on `run`, suggest new name | 2 major versions |
| D) Config switch | User chooses preferred name | Permanent |

**Recommendation**: Option C (deprecation with warning)

---

## Decision Criteria

Before deciding, answer:

1. **Is the confusion real?** Do users actually get confused, or is this theoretical?
2. **Is the benefit worth the cost?** Migration effort vs clarity gained
3. **What do users prefer?** Direct feedback needed

---

## Next Steps

- [ ] Gather user feedback on naming preferences
- [ ] Document actual confusion incidents (if any)
- [ ] Prototype deprecation warning message
- [ ] Make final decision with user input

---

## References

- [CLI-ERGONOMICS.md](CLI-ERGONOMICS.md) - Original analysis
- [PHILOSOPHY.md](../docs/PHILOSOPHY.md) - Design principles
- [GLOSSARY.md](../docs/GLOSSARY.md) - Terminology definitions
