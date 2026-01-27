# Workflow Design Principles

How to design effective sdqctl conversation files.

---

## The Core Principle

> **Describe how context windows fit over workflow steps, not detailed specifications.**

A `.conv` file should orchestrate the *flow* of work across context windows. Documentation files (`.md`) should hold the *details* of what to implement.

This separation enables:
- **Reusable workflows** - Same `.conv` for different specs
- **Focused context** - Agent loads only what it needs per phase
- **Maintainable specs** - Update `.md` without changing workflow
- **Human-reviewable** - Specs are readable outside sdqctl

---

## Anti-Pattern: Specification Embedding

❌ **Don't put detailed specs in the conversation file:**

```dockerfile
# BAD: feature-x.conv
PROMPT ## Phase 1: Implement Feature X
  The feature should:
  - Support format A with fields x, y, z
  - Handle error cases: E1, E2, E3
  - Integrate with the existing FooManager class
  - Follow the pattern from lib/similar.py lines 45-120
  - Add validation for: null inputs, oversized payloads, malformed JSON
  - Emit events: feature.started, feature.completed, feature.failed
  ... 50 more lines of specification ...

PROMPT ## Phase 2: Add Tests
  Test the following scenarios:
  - Valid input returns expected output
  - Null input raises ValueError
  - Oversized payload is rejected with code 413
  ... 20 more test scenarios ...
```

**Problems:**
- Consumes tokens before agent even starts working
- Hard to review/edit specifications
- Not reusable for similar features
- Mixes orchestration with content

---

## Pattern: Reference Documentation Deliverables

✅ **Keep specs in `.md` files, reference from `.conv`:**

```dockerfile
# GOOD: implement-feature.conv
MODEL gpt-4
ADAPTER copilot
MODE implement
MAX-CYCLES 3

# Small critical file - OK to inject upfront
CONTEXT @proposals/feature-x-design.md

# Cycle 1: Understand and plan
PROMPT Review the design in proposals/feature-x-design.md.
  Select ONE aspect to implement this cycle.

# Cycle 2: Implement
PROMPT Implement the selected aspect. Run tests to verify.

COMPACT

# Cycle 3: Document
PROMPT Update docs with any API changes.

OUTPUT-FILE reports/feature-x-progress-{{DATE}}.md
```

**The spec lives in `proposals/feature-x-design.md`:**

```markdown
# Feature X Design

## Overview
Feature X provides...

## Requirements
- R1: Support format A with fields x, y, z
- R2: Handle error cases E1, E2, E3
...

## Implementation Notes
Follow the pattern in lib/similar.py (see function `example_handler`).

## Test Scenarios
1. Valid input returns expected output
2. Null input raises ValueError
...
```

**Benefits:**
- Workflow is 20 lines instead of 100
- Spec is human-reviewable
- Same workflow reusable for feature-y
- Agent reads spec details on demand

---

## Context Window Mental Model

Think of each cycle as a **context window** that the agent fills with:

1. **Your prompts** (from PROLOGUE, PROMPT, EPILOGUE)
2. **Injected files** (from CONTEXT)
3. **Tool results** (files the agent reads, command output)
4. **Agent responses** (reasoning, code, etc.)

```
┌─────────────────────────────────────────────────────────────┐
│ Cycle 1: Analyze                                            │
│                                                             │
│ ┌─ Your Input ─────────────────────────────────────────┐   │
│ │ PROLOGUE (session context)                            │   │
│ │ CONTEXT @design.md (100 lines)                        │   │
│ │ PROMPT "Review and select one task"                   │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ Agent Work ──────────────────────────────────────────┐   │
│ │ Reads design.md                                       │   │
│ │ Reads related source files (on demand)                │   │
│ │ Produces: selected task + rationale                   │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ Context usage: ~40%                                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ (COMPACT)
┌─────────────────────────────────────────────────────────────┐
│ Cycle 2: Implement                                          │
│                                                             │
│ ┌─ Your Input ─────────────────────────────────────────┐   │
│ │ COMPACT summary (replaces cycle 1 details)            │   │
│ │ PROMPT "Implement the selected task"                  │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ Agent Work ──────────────────────────────────────────┐   │
│ │ Reads source files                                    │   │
│ │ Edits files                                           │   │
│ │ Runs tests                                            │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ Context usage: ~60%                                         │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:** Each phase has its own context budget. Don't exhaust it upfront.

---

## Design Checklist

When authoring a workflow, ask:

| Question | If Yes | If No |
|----------|--------|-------|
| Is spec > 50 lines? | Move to `.md` file | Can inline |
| Do I need the whole file? | Use CONTEXT | Let agent read on demand |
| Is this a multi-phase workflow? | Add COMPACT between phases | Single prompt is fine |
| Does filename describe action? | Good | Rename to use verb |
| Could agent misunderstand role? | Add PROLOGUE role clarification | Prompt is clear enough |

---

## Workflow Patterns

### Pattern 1: Single-Spike (Research)

```dockerfile
# audit-security.conv
MODE audit

PROMPT Analyze lib/auth/ for security vulnerabilities.
  Focus on: input validation, authentication, session handling.
  
OUTPUT-FILE reports/security-audit-{{DATE}}.md
```

**Context strategy:** Let agent explore. No CONTEXT directives needed.

### Pattern 2: Multi-Phase (Implementation)

```dockerfile
# implement-feature.conv
MODE implement
MAX-CYCLES 3

CONTEXT @proposals/FEATURE.md    # Small spec file

PROMPT Phase 1: Select one task from the design.
PROMPT Phase 2: Implement it.
COMPACT
PROMPT Phase 3: Document changes.
```

**Context strategy:** Inject spec once, COMPACT between phases.

### Pattern 3: Test-Fix Loop

```dockerfile
# fix-tests.conv
MAX-CYCLES 5

RUN pytest tests/ -v
ELIDE
PROMPT Fix any failing tests shown above.

CHECKPOINT-AFTER each-cycle
```

**Context strategy:** ELIDE merges test output with fix prompt. Fresh test run each cycle.

### Pattern 4: Component Iteration

```dockerfile
# audit-components.conv
MODE audit

PROLOGUE Component: {{COMPONENT_NAME}}
PROMPT Analyze {{COMPONENT_PATH}} for issues.
OUTPUT-FILE reports/{{COMPONENT_NAME}}-audit.md
```

Run with: `sdqctl apply audit-components.conv --components "lib/*.py"`

**Context strategy:** Each component gets fresh context.

---

## Common Mistakes

| Mistake | Why It's Bad | Fix |
|---------|--------------|-----|
| `CONTEXT @lib/**/*.py` | Injects thousands of lines | Let agent read on demand |
| `--prologue @50kb-report.md` | Exhausts context | Reference file in prompt |
| No COMPACT in 5+ cycle workflow | Context overflow | Add COMPACT between phases |
| Hardcoded commit messages in RUN | Generic messages | Let agent write commits |
| 100-line PROMPT blocks | Wasted tokens, unmaintainable | Move to `.md` file |

---

## Relationship to Other Docs

| Doc | Focus |
|-----|-------|
| **This doc** | Conversation file design philosophy |
| [PHILOSOPHY.md](PHILOSOPHY.md) | Core workflow design principles |
| [GLOSSARY.md](GLOSSARY.md) | Terminology definitions |
| [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md) | Token budgets, COMPACT timing |
| [SYNTHESIS-CYCLES.md](SYNTHESIS-CYCLES.md) | Multi-cycle iteration patterns |
| [QUIRKS.md](QUIRKS.md) | Surprising behaviors to avoid |
| [GETTING-STARTED.md](GETTING-STARTED.md) | Basic usage |

---

## Quick Reference

```dockerfile
# ✅ Good workflow structure
MODEL gpt-4
MODE implement
MAX-CYCLES 3

# Role clarity
PROLOGUE You are an implementation assistant. Edit files directly.
PROLOGUE Session: {{DATE}} | Branch: {{GIT_BRANCH}}

# Reference specs, don't embed
CONTEXT @proposals/DESIGN.md

# Clear phases
PROMPT Phase 1: Review design and select task.
PROMPT Phase 2: Implement and test.
COMPACT
PROMPT Phase 3: Document changes.

# Output
OUTPUT-FILE reports/progress-{{DATE}}.md
```

---

## See Also

- `sdqctl help ai` - AI agent guidance
- `sdqctl help workflow` - Directive reference
- `sdqctl help examples` - Example patterns
- [SECURITY-MODEL.md](SECURITY-MODEL.md) - Shell execution and path handling security
