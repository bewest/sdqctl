# Colophon

> **About this document**: A colophon traditionally describes the production of a work—
> the tools, techniques, and processes that brought it into being. This colophon
> documents the dogfooding journey of sdqctl: building an AI orchestration tool
> using AI orchestration.

## Origin Story

sdqctl began as a proposal document (SDQCTL-PROPOSAL.md) written on January 20, 2026.
The proposal outlined the problem of manual orchestration of AI-assisted development
workflows and proposed a solution: a vendor-agnostic CLI with declarative ConversationFiles
and context controls.

**What the proposal envisioned:**

| Aspect | Proposed |
|--------|----------|
| Timeline | 4 weeks |
| Commands | 4 core (`run`, `cycle`, `flow`, `apply`) |
| Directives | 17 |
| Adapters | 4 (copilot, claude, openai, ollama) |

**What actually happened:**

| Aspect | Proposed | Actual | Variance |
|--------|----------|--------|----------|
| Timeline | 4 weeks | 8 days | **-75%** |
| Commands | 4 | 18 | **+350%** |
| Directives | 17 | 74 | **+335%** |
| Adapters | 4 | 2 (copilot, mock) | Focus over breadth |

The proposal captured the *correct problem* and *correct solution shape*, but reality
revealed far more complexity in SDK integration, context management, and workflow patterns.

---

## The Dogfooding Story

sdqctl was developed in approximately **one week** (January 20-27, 2026), with the
majority of features implemented by AI agents orchestrated through the tool itself.
This recursive self-improvement—using sdqctl to build sdqctl—validated the core
design while revealing practical refinements.

### By the Numbers

| Metric | Value |
|--------|-------|
| Development period | 8 days (Jan 20-27, 2026) |
| Total commits | 596 |
| Lines of Python | ~23,000 |
| Test count | 1,571 |
| Test files | 46 |
| Documentation files | 30 |
| Proposals written | 29 |
| Work packages completed | 6 |

### Authorship Attribution

| Source | Commits | LOC | % of Code |
|--------|---------|-----|-----------|
| **Manual writing** | ~46 | ~2,000 | 9% |
| **Interactive Copilot** (attended) | ~194 | ~8,000 | 35% |
| **sdqctl iterate** (unattended) | ~356 | ~13,000 | 56% |

**~91% of the codebase was AI-synthesized**, with the majority (56%) produced by
unattended `sdqctl iterate` runs against the project's own backlog. The tool
literally built itself.

Commit patterns by development phase:

| Phase | Dates | Commits | Mode |
|-------|-------|---------|------|
| Inception | Jan 18-20 | 46 | Manual scaffolding |
| Feature dev | Jan 21-23 | 194 | Interactive Copilot REPL |
| Self-building | Jan 24-27 | 356 | Unattended sdqctl iterate |

## Construction Journey

### Phase 1: Foundation (Jan 20-21)

Initial scaffolding: basic CLI structure, conversation file parsing, and adapter
interfaces. The first commands (`run`, `cycle`) established the pattern of
declarative workflows with AI backends.

**Key commits**: `998b5a6 init sdqctl`, `c7da27bc expand commands`

### Phase 2: Core Features (Jan 22-24)

Rapid feature development as sdqctl began orchestrating its own development:
- Verification directives (`VERIFY refs`, `links`, `traceability`)
- Pipeline architecture (`--from-json`, schema versioning)
- CLI ergonomics (`help` command, 12 subcommands, 6 topics)
- STPA workflow templates for safety analysis

**Key deliverables**: 
- [`reports/proposal-session-2026-01-22.md`](../reports/proposal-session-2026-01-22.md)
- [`reports/proposal-session-2026-01-23.md`](../reports/proposal-session-2026-01-23.md)

### Phase 3: SDK Integration (Jan 24-25)

Deep integration with the Copilot SDK revealed critical patterns:
- Infinite sessions with automatic compaction
- Session persistence (`resume`, `SESSION-NAME`)
- Metadata APIs for status and diagnostics

**Quirks resolved**: Q-001 through Q-018 (all documented in 
[`docs/QUIRKS.md`](QUIRKS.md) and archived in [`archive/quirks/`](../archive/quirks/))

**Key deliverables**:
- [`reports/extended-backlog-session-2026-01-25.md`](../reports/extended-backlog-session-2026-01-25.md)
- [`archive/2026-01-backlog-migration.md`](../archive/2026-01-backlog-migration.md)

### Phase 4: Refinement (Jan 26)

Major refactoring driven by code quality analysis:
- ConversationFile split: 1,819 → 7 modules (largest 858 lines)
- CLI modularization: 966 → 413 lines (-57%)
- Copilot adapter: 1,143 → 670 lines (-41%)
- `run` command deprecation: 972 → 125 lines (thin wrapper to `iterate`)

**Analysis reports**:
- [`reports/dual-run-comparison-2026-01-26.md`](../reports/dual-run-comparison-2026-01-26.md)
- [`reports/iterate-run-analysis-2026-01-26.md`](../reports/iterate-run-analysis-2026-01-26.md)

### Phase 5: Ecosystem Features (Jan 27)

Final week brought advanced capabilities:
- LSP integration (`lsp type`, `lsp status`)
- Drift detection (`drift --since`, `--report`)
- Plugin system (directive discovery, `verify plugin`)
- Performance benchmarks

**Work packages completed**: WP-002 (Monitoring), WP-004 (Plugin), WP-005 (STPA), WP-006 (LSP)

**Analysis reports**:
- [`reports/8-cycle-wp-run-analysis-2026-01-27.md`](../reports/8-cycle-wp-run-analysis-2026-01-27.md)
- [`reports/lsp-phase1-completion-run-2026-01-27.md`](../reports/lsp-phase1-completion-run-2026-01-27.md)

## Key Discoveries

Several unexpected findings emerged during development that shaped the final design:

### Filename Semantics Influence Agent Behavior (Q-001)

The agent interprets workflow filename words as semantic signals. A file named
`progress-tracker.conv` caused the agent to focus on tracking/reporting rather than
implementing changes.

**Solution**: `{{WORKFLOW_NAME}}` is excluded from prompts by default. Use
`{{__WORKFLOW_NAME__}}` for explicit opt-in.

### SDK Abort Events Are Never Emitted (Q-002)

The SDK documents an `ABORT` event type, but it was never observed during stress testing.
This meant we couldn't rely on SDK signals for loop detection.

**Solution**: Implemented client-side `LoopDetector` with heuristics (identical responses,
minimal length, reasoning patterns) and a stop file mechanism (`STOPAUTOMATION-{hash}.json`).

### Event Handlers Persist Across Session (Q-014)

SDK `.on()` handlers are never automatically removed. In accumulate mode with N prompts,
N handlers all fire for each event—causing exponential log duplication.

**Solution**: Register handlers once per session with a flag:
```python
if not stats.handler_registered:
    copilot_session.on(on_event)
    stats.handler_registered = True
```

### COMPACT Placement Is Critical (v1 vs v2 workflow)

Cross-run analysis revealed dramatic differences based on COMPACT placement:

| Workflow | Context Peak | Cycles Completed |
|----------|--------------|------------------|
| v1 (6 phases, no strategic COMPACT) | 55-58% | 5.5/10 |
| v2 (9 phases, COMPACT after Phase 6) | **20%** | **10/10** |

This discovery led to the "Extended Workflow Pattern (v2)" documented in
[PHILOSOPHY.md](PHILOSOPHY.md).

### Bidirectional Flow Emerges

Long-running sessions naturally exhibit two information flows:

```
FORWARD: humans → decisions → BACKLOG.md → implementation
BACKWARD: implementation → discoveries → OPEN-QUESTIONS.md → humans
```

This pattern led to the `CONSULT` directive for pausing with proactive question presentation.

---

## Lessons Learned

Design principles distilled from recursive development:

| Lesson | Discovery Context | Impact |
|--------|-------------------|--------|
| **Process over domain** | Ecosystem workflows | Commands should be generic (`lsp type X`), not domain-specific. Direction comes from `--prologue`. |
| **Typesetting metaphor** | `--introduce` naming | CLI flags follow document structure: prologue→introduce→body→epilogue. |
| **Agent output visibility** | User feedback | Agent responses print to stdout by default. Users can't debug what they can't see. |
| **Plugin system decoupling** | Release cycle friction | Ecosystem teams need to extend sdqctl independently. Plugins > core features for domain needs. |
| **Warmup/priming pattern** | Feedback team | First-cycle-only context injection (`--introduce`) is a common need. |
| **LSP complements REFCAT** | Analysis workflow | Text extraction (REFCAT) and semantic queries (LSP) serve different needs. |

## Architecture Decisions

Key decisions made during development:

| Decision | Context | Resolution |
|----------|---------|------------|
| [ADR-004](../archive/decisions/ADR-004-sdk-session-persistence.md) | Session resume | Store SDK session UUID in checkpoint |
| [D-015](../archive/DECISIONS.md#d-015-backlog-organization) | Backlog hygiene | Domain backlogs + archive for completed items |
| Compaction strategy | Token economy | Background at 80%, blocking at 95% |
| Event handler pattern | Q-014 leak | Register once per session with flag |

## Development Workflow

The workflow that built sdqctl relied almost exclusively on the `iterate` subcommand
with `--introduction` and `--prologue` flags, powered by the backlog processor v2:

```bash
# Primary workflow: iterate with backlog processor v2
sdqctl iterate backlog.conv -n 8 \
  --session-mode accumulate \
  --introduction "Focus on P0-P2 Ready Queue items" \
  --prologue proposals/LIVE-BACKLOG.md
```

**Key patterns**:

| Element | Purpose |
|---------|---------|
| Backlog processor v2 | Core engine parsing structured markdown backlogs |
| `--introduction` | First-cycle-only warmup context (goals, focus areas) |
| `--prologue` | Injected before every cycle (live status, new priorities) |
| `LIVE-BACKLOG.md` | Mutable file for injecting new items mid-run |
| Interactive Copilot | Ad-hoc work item injection during spot checks |

**Mid-run steering with LIVE-BACKLOG.md and interactive Copilot**:

During longer cycles (`-n 5-10`), operators performed spot checks and used two
mechanisms to refocus the automation:

1. **Edit `LIVE-BACKLOG.md`** — Modify priorities without stopping the run
2. **Interactive Copilot** — Inject urgent work items conversationally

**Session modes observed**:
- `accumulate`: 70% of development (iterative refinement)
- `compact`: 20% (long documentation runs)
- `fresh`: 10% (independent file edits)

## Quality Metrics

Code quality tracked throughout development:

| Metric | Start (Jan 20) | End (Jan 27) | Change |
|--------|----------------|--------------|--------|
| Lint issues | 1,994 | 0 | -100% |
| Max file size | 1,819 | 858 | -53% |
| Test count | 0 | 1,562 | +1,562 |
| Test coverage | 0% | ~85% | — |

## References

### Session Logs
- [`archive/SESSIONS/`](../archive/SESSIONS/) - Daily development logs

### Analysis Reports
- [`reports/`](../reports/) - 33 analysis and run reports

### Proposals
- [`proposals/`](../proposals/) - 29 feature proposals

### Architecture
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) - Module structure
- [`docs/PHILOSOPHY.md`](PHILOSOPHY.md) - Design principles
- [`docs/SDK-LEARNINGS.md`](SDK-LEARNINGS.md) - Patterns from quirk resolution

---

*This document was generated with assistance from sdqctl, completing the 
recursive loop of a tool documenting its own creation.*
