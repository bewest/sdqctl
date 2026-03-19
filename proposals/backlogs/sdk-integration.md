# SDK Integration Backlog

> **Domain**: Copilot SDK, adapters, sessions, API interactions  
> **Parent**: [BACKLOG.md](../BACKLOG.md)  
> **Last Updated**: 2026-03-19

---

## R&D: SDK Feature Audit (2026-03-19)

**Context**: The Copilot SDK has had 266 commits in the past 2 months. We discovered several capabilities not yet used by sdqctl. Need systematic audit and experiments before adopting or blocking.

### Research Track: Tool & Agent Control APIs

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| SDK-R01 | Audit `excluded_tools` / `available_tools` | P1 | Low | Verify works for built-in tools (sql, task, etc) |
| SDK-R02 | Audit `disabled_skills` capability | P2 | Low | Test skill filtering |
| SDK-R03 | Audit `session.rpc.agent.*` APIs | P2 | Medium | list, select, deselect agents programmatically |
| SDK-R04 | Audit `session.rpc.fleet.start()` | P2 | Medium | Parallel agent orchestration |
| SDK-R05 | Audit `session.rpc.compaction.compact()` | P2 | Low | Manual compaction trigger |
| SDK-R06 | Audit `session.rpc.shell.exec()` | P3 | Low | Programmatic shell vs RUN directive |

### Research Track: Recent SDK Features (Jan-Mar 2026)

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| SDK-R10 | `reasoningEffort` parameter | P2 | Low | Model reasoning control (ea90f076) |
| SDK-R11 | Blob attachment type | P3 | Low | Inline base64 data (698b2598) |
| SDK-R12 | OpenTelemetry support | P2 | Medium | Observability integration (f2d21a0b) |
| SDK-R13 | `skipPermission` for tools | P1 | Low | Auto-approve specific tools (10c4d029) |
| SDK-R14 | `SessionConfig.OnEvent` | P2 | Low | Early event handler (4125fe76) |
| SDK-R15 | Custom agent pre-selection | P2 | Low | `agent` param in session (7766b1a3) |
| SDK-R16 | Mid-session model switching | P2 | Low | `session.setModel()` (bd98e3a3) |

### Experiments Needed

| # | Experiment | Goal | Blocking |
|---|------------|------|----------|
| SDK-E01 | Test `excluded_tools: ["sql"]` | Does it prevent SQL tool use? | SDK-R01 |
| SDK-E02 | Test `excluded_tools: ["task"]` | Does it prevent sub-agent spawn? | SDK-R01 |
| SDK-E03 | Compare agent delegation vs RUN | Token/time efficiency | SDK-R03/R04 |
| SDK-E04 | Test fleet mode for parallel work | Does it improve backlog throughput? | SDK-R04 |
| SDK-E05 | Manual compaction timing | Better than auto? | SDK-R05 |

### Proposed Directives (Pending Research)

```dockerfile
# Tool control (SDK-R01, SDK-E01, SDK-E02)
EXCLUDE-TOOLS sql store_memory task
AVAILABLE-TOOLS view edit bash grep glob

# Skill control (SDK-R02)
DISABLE-SKILLS nightscout-cgm

# Agent control (SDK-R03, SDK-R15)
AGENT ecosystem-alignment

# Permission shortcuts (SDK-R13)
AUTO-APPROVE-TOOLS bash grep view

# Model tuning (SDK-R10, SDK-R16)
REASONING-EFFORT high
```

---

## Active Items

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| SDK-001 | `sessions analytics` command | P2 | Low | Aggregate metrics view |
| SDK-002 | `sessions outliers` command | P2 | Low | Detect anomalous sessions |
| SDK-003 | `sessions trends` command | P3 | Medium | Time-based analysis |
| SDK-004 | `sessions export` command | P3 | Medium | CSV/JSON export |
| SDK-005 | Compaction recommendations engine | P3 | Medium | Suggest compaction for marathon sessions |

**Proposal**: [SESSION-ANALYTICS.md](../SESSION-ANALYTICS.md)

---

## Completed

*Migrated from main BACKLOG.md - see WP-001 step 3*

---

## References

- [docs/SDK-LEARNINGS.md](../../docs/SDK-LEARNINGS.md) - SDK patterns
- [docs/QUIRKS.md](../../docs/QUIRKS.md) - Active quirks
- [COPILOT-SDK-INTEGRATION.md](../../COPILOT-SDK-INTEGRATION.md) - Integration guide
