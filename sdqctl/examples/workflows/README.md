# sdqctl Examples

This directory contains example workflows for sdqctl.

## 📚 Documentation Guides

For in-depth explanations, see the guides in `docs/`:

| Guide | Use Case |
|-------|----------|
| [Getting Started](../../docs/GETTING-STARTED.md) | First steps with sdqctl |
| [Context Management](../../docs/CONTEXT-MANAGEMENT.md) | Optimal context window strategies |
| [Synthesis Cycles](../../docs/SYNTHESIS-CYCLES.md) | Self-improving iteration loops |
| [Traceability](../../docs/TRACEABILITY-WORKFLOW.md) | Requirements → code → verification |
| [Reverse Engineering](../../docs/REVERSE-ENGINEERING.md) | Code → documentation |

## Running Examples

```bash
# With mock adapter (for testing)
sdqctl run examples/workflows/security-audit.conv --adapter mock --verbose

# With Copilot (requires copilot-sdk)
sdqctl run examples/workflows/security-audit.conv --adapter copilot

# Multi-cycle workflow
sdqctl cycle examples/workflows/typescript-migration.conv --max-cycles 3

# Batch execution
sdqctl flow examples/workflows/*.conv --parallel 2

# Human-in-the-loop workflow (pauses for review)
sdqctl run examples/workflows/human-review.conv --adapter mock --verbose
# Then resume with: sdqctl resume <checkpoint-path>
```

## Available Workflows

### Core Examples
- `security-audit.conv` - Security vulnerability analysis
- `typescript-migration.conv` - Multi-cycle TypeScript conversion
- `documentation-sync.conv` - Documentation consistency check
- `human-review.conv` - Human-in-the-loop review with PAUSE directive
- `consult-design.conv` - Design decision consultation with CONSULT directive
- `implement-improvements.conv` - Quine-like self-improving workflow
- `test-discovery.conv` - Analyze code for test requirements

### Traceability Workflows
- `traceability/fix-broken-refs.conv` - Fix broken code references using `--suggest-fixes`
- `traceability/requirements-discovery.conv` - Extract requirements from documentation
- `traceability/verification-loop.conv` - Continuous verification cycle

### Tooling Workflows
- `tooling/refcat-improvement.conv` - 3-cycle false positive reduction
- `tooling/verifier-test-loop.conv` - 5-cycle TDD pattern for verifier improvements

### Pattern Quick Reference

| Pattern | Command | When to Use |
|---------|---------|-------------|
| **Testing a workflow** | `sdqctl run workflow.conv --dry-run` | Before committing to cycles |
| **Single execution** | `sdqctl run workflow.conv` | One-off tasks, priming |
| **Iterative refinement** | `sdqctl cycle workflow.conv -n 3` | Multi-step improvements |
| **Quine loop** | `sdqctl cycle implement-improvements.conv` | Self-improving workflows |
| **Batch processing** | `sdqctl apply workflow.conv --components "*.py"` | Per-component work |
| **Human consultation** | `sdqctl run consult-design.conv` | Design decisions needing human input |
| **Fix broken refs** | `sdqctl cycle traceability/fix-broken-refs.conv -n 3` | Update stale code references |
| **Improve verifiers** | `sdqctl cycle tooling/verifier-test-loop.conv -n 5` | TDD for tool development |

---

## Topic-Priming Prologue Pattern

When improving a codebase iteratively, use `implement-improvements.conv` with a **topic-focused prologue** to concentrate cycles on a specific area.

### The Pattern

1. **Identify a topic** from your improvements tracker (e.g., RUN command, adapter reliability)
2. **Create a topic-focused prologue** that chunks work into categories
3. **Run focused cycles** with the prologue priming each prompt
4. **Update the focus document** with lessons learned after each session

### Example: RUN Command Improvements

```bash
# Create topic focus from improvements-tracker.md
# See: reports/run-improvements-focus.md

# Run focused improvement cycle
sdqctl -vv cycle -n 3 --adapter copilot \
  --prologue @reports/run-improvements-focus.md \
  --epilogue "Update @reports/run-improvements-focus.md with completed items and lessons" \
  examples/workflows/implement-improvements.conv
```

### Topic Focus Document Structure

A topic prologue should contain:

```markdown
# [Topic] Improvements - Topic Focus

## Scope Boundaries
- In Scope: specific files, features
- Out of Scope: what to ignore this session

## Improvement Chunks
Work organized by category (safety → security → ergonomics → quality → testing)

### 1. [Category]
#### [ID]: [Title] ⏳
**File:** path/to/file.py
**Issue:** description
**Tasks:**
- [ ] task 1
- [ ] task 2

## Completed This Session
(Updated after each cycle)

## Lessons Learned
(Barriers, workarounds, insights)

## Next Session Command
(Exact command to continue)
```

### Creating a New Topic Focus

1. Open `reports/improvements-tracker.md`
2. Find items related to your topic
3. Copy to `reports/[topic]-improvements-focus.md`
4. Organize into categories: reliability, security, ergonomics, code quality, testing
5. Add scope boundaries
6. Run the cycle with `--prologue @reports/[topic]-improvements-focus.md`

### Why This Pattern Works

- **Focus**: Prologue primes every prompt to stay on topic
- **Chunking**: Complex topics broken into manageable pieces
- **Iteration**: Each cycle builds on previous work
- **Documentation**: Lessons captured for future sessions
- **Reusability**: Same workflow, different prologues for different topics

See `reports/run-improvements-focus.md` for a working example.
