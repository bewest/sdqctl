# Proposal: STPA Deep Integration Research

> **Status**: Research  
> **Date**: 2026-01-27  
> **Author**: sdqctl development  
> **Scope**: Comprehensive STPA integration for Nightscout ecosystem  
> **Deliverable**: Multi-faceted report and usage guide for ecosystem team

---

## Problem Statement

Existing STPA proposals provide foundation but lack actionable guidance:

| Existing Artifact | What It Provides | What's Missing |
|-------------------|------------------|----------------|
| [STPA-INTEGRATION.md](STPA-INTEGRATION.md) | sdqctl directive patterns | End-to-end workflow |
| [STPA-TRACEABILITY-FRAMEWORK.md](../../externals/rag-nightscout-ecosystem-alignment/docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md) | UCA/SC/CF taxonomy | Practical usage guide |

**Gap**: Ecosystem team needs a comprehensive guide to actually *use* STPA with their tooling, plus predictions for future improvements to inform their roadmap.

---

## Research Questions

### R1: Scalability
How can AI-assisted UCA (Unsafe Control Action) discovery scale to 16+ projects?
- What's the right batch size for analysis?
- How to handle cross-project UCAs (sync issues span Loop ↔ AAPS ↔ Nightscout)?

### R2: Human-AI Handoff
What's the optimal handoff between automated analysis and human review?
- Which UCA types need mandatory human review?
- What review gates prevent false positives from reaching production docs?

### R3: Methodology Integration
How should STPA artifacts integrate with existing 5-facet methodology?
- Does STPA become a 6th facet or overlay on existing facets?
- How to avoid documentation duplication?

### R4: Multi-Jurisdiction Compliance
What severity classification standard best fits global regulatory requirements?
- ISO 14971 (risk management) vs IEC 62304 (software lifecycle) vs custom?
- How to map between standards when needed?

---

## Deliverables

### D1: STPA Usage Guide for Ecosystem Team

**Format**: Markdown document (~2000 words)  
**Location**: `externals/rag-nightscout-ecosystem-alignment/docs/STPA-USAGE-GUIDE.md`

**Contents**:
1. Quick start: Adding STPA analysis to a new project
2. Step-by-step workflow with sdqctl commands
3. Template files for UCA, SC, CF entries
4. Integration with existing tools (gen_traceability.py, verify_refs.py)
5. Common pitfalls and how to avoid them
6. Checklist for STPA analysis completion

### D2: Improvement Predictions Report

**Format**: Structured report with timeline  
**Location**: `externals/rag-nightscout-ecosystem-alignment/docs/STPA-ROADMAP.md`

**Contents**:

| Timeframe | Improvement | Rationale | Effort |
|-----------|-------------|-----------|--------|
| Near-term (3 months) | Incremental tooling improvements | Low risk, immediate value | Low |
| Medium-term (6 months) | Automation opportunities | Reduce manual analysis burden | Medium |
| Long-term (12 months) | Full CI/CD integration | Continuous compliance validation | High |

### D3: Cross-Project STPA Patterns

**Format**: Pattern catalog  
**Location**: `externals/rag-nightscout-ecosystem-alignment/traceability/stpa/cross-project-patterns.md`

**Contents**:
1. UCAs that span multiple projects (with project matrix)
2. Shared safety constraints that should be standardized
3. Gap analysis: STPA coverage by project tier
4. Recommendations for Tier 1 vs Tier 2 vs Tier 3 projects

---

## Research Phases

### Phase 1: Current State Analysis (1 iteration)

- [ ] Audit existing STPA artifacts in ecosystem workspace
  - How many UCAs documented? Coverage by control action?
  - How many safety constraints? Linked to requirements?
- [ ] Map gaps between current state and FDA-ready state
  - What's missing for 21 CFR 820.30 compliance?
  - What's missing for IEC 62304 Class C software?
- [ ] Interview ecosystem team on pain points (async via OPEN-QUESTIONS.md)
  - What's hardest about STPA today?
  - What would help most?

**Output**: Current state assessment document

### Phase 2: Pattern Discovery (1 iteration)

- [ ] Identify cross-project UCAs
  - Analyze GAP-XXX entries for multi-project scope
  - Catalog UCAs related to: sync, remote commands, data integrity
- [ ] Catalog shared safety constraints
  - Which SCs should be identical across Loop/AAPS/Trio?
  - Which SCs are project-specific?
- [ ] Analyze automation potential
  - Which UCA types can be discovered automatically?
  - Which require human domain expertise?

**Output**: Pattern catalog (D3 draft)

### Phase 3: Guide Development (1 iteration)

- [ ] Write STPA usage guide (D1)
- [ ] Create templates for UCA, SC, CF entries
- [ ] Test guide with one Tier 1 project (e.g., Loop bolus handling)
- [ ] Refine based on test results

**Output**: STPA Usage Guide (D1 complete)

### Phase 4: Predictions & Roadmap (1 iteration)

- [ ] Synthesize improvement predictions (D2)
- [ ] Create roadmap with dependencies
- [ ] Present recommendations to ecosystem team
- [ ] Document lessons learned

**Output**: Improvement Predictions Report (D2 complete)

---

## Integration with Existing Work

### 5-Facet Methodology

Current 5 facets:
1. Terminology → `mapping/cross-project/terminology-matrix.md`
2. Gaps → `traceability/gaps.md`
3. Requirements → `traceability/requirements.md`
4. Deep Dive → `docs/10-domain/{topic}-deep-dive.md`
5. Progress → `progress.md`

**Proposal**: STPA as overlay, not 6th facet

```
┌─────────────────────────────────────────────────────────────┐
│                    5-Facet Methodology                       │
├─────────────────────────────────────────────────────────────┤
│  Terminology ──┬── Gaps ──┬── Requirements ──┬── Deep Dive  │
│                │          │                  │               │
│                └────┬─────┴────────┬─────────┘               │
│                     │              │                         │
│              ┌──────▼──────────────▼──────┐                  │
│              │      STPA Overlay          │                  │
│              │  UCAs link to Gaps         │                  │
│              │  SCs link to Requirements  │                  │
│              │  CFs explain root causes   │                  │
│              └────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Conformance Scenarios

Link UCAs to test assertions:

```markdown
## UCA-BOLUS-003: Double bolus due to sync failure

**Verification**:
- Scenario: `conformance/scenarios/bolus-dedup.yaml`
- Assertions: `ASSERT-BATCH-003`, `ASSERT-BATCH-004`
```

### sdqctl Workflows

Existing STPA workflows:
- `examples/workflows/stpa/stpa-audit.conv` - UCA discovery
- `examples/workflows/stpa/trace-verification.conv` - Trace validation

**Enhancement**: Add ecosystem-specific workflows via plugin system (see PLUGIN-SYSTEM.md)

---

## Open Questions

| ID | Question | Options | Decision (2026-01-27) |
|----|----------|---------|----------------------|
| OQ-STPA-001 | Who maintains STPA artifacts? | Central team / Per-project / Hybrid | **Incubation**: Nightscout ecosystem alignment team incubates until sub-projects adopt |
| OQ-STPA-002 | Severity classification standard | ISO 14971 / IEC 62304 / Custom | **Custom with ISO 14971 mapping**: Start simple, provide mapping to standard |
| OQ-STPA-003 | AI/human review handoff | Mandatory gates / Continuous review | **Continuous review**: AI suggests, human approves incrementally |
| OQ-STPA-004 | STPA artifact lifecycle | Matches code / Separate cadence | **Research deliverable**: Include recommendations with impact analysis on management/bloat vs value |

### Notes from Recent Discussions

- **OQ-STPA-001**: Ecosystem team will incubate artifacts centrally, with a path for sub-projects to adopt ownership when ready.
- **OQ-STPA-004**: Lifecycle recommendations will be part of D2 (Improvement Predictions Report) with trade-off analysis.

---

## Success Criteria

1. **Actionable**: Ecosystem team has step-by-step usage guide they can follow
2. **Predictive**: At least 3 improvement predictions with clear rationale and timeline
3. **Comprehensive**: Cross-project patterns documented for Tier 1 projects
4. **Roadmap**: Clear 12-month roadmap with dependencies
5. **Validated**: Guide tested with at least one real project analysis

---

## Resource Requirements

| Resource | Effort | Notes |
|----------|--------|-------|
| Research iterations | 4 | One per phase |
| Ecosystem team input | 2-3 hours | Async via OPEN-QUESTIONS.md |
| Test project (Tier 1) | 1 | Preferably Loop or AAPS |
| Review cycle | 1 | Final review before publishing |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ecosystem team bandwidth | Medium | High | Keep guide concise, provide templates |
| STPA complexity overwhelming | Medium | Medium | Start with single control action example |
| Regulatory uncertainty | Low | High | Focus on ISO 14971 + IEC 62304 (globally recognized) |
| Scope creep | Medium | Medium | Fixed 4-iteration timeline, clear deliverables |

---

## References

### sdqctl Proposals
- [STPA-INTEGRATION.md](STPA-INTEGRATION.md) - Directive patterns for STPA
- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - Traceability verification
- [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md) - Ecosystem extensions

### Ecosystem Artifacts
- [STPA-TRACEABILITY-FRAMEWORK.md](../../externals/rag-nightscout-ecosystem-alignment/docs/sdqctl-proposals/STPA-TRACEABILITY-FRAMEWORK.md) - Framework proposal

### Regulatory Standards
- **ISO 14971:2019** — Risk management for medical devices
- **IEC 62304:2006+AMD1:2015** — Medical device software lifecycle
- **FDA 21 CFR 820.30** — Design Controls
- **EU MDR 2017/745** — Medical Device Regulation

### STPA Resources
- [MIT STPA Handbook](https://psas.scripts.mit.edu/home/materials/)
- [STPA Primer](http://psas.scripts.mit.edu/home/get_file.php?name=STPA_Primer-v1.pdf)

---

**Document Version**: 0.1  
**Last Updated**: 2026-01-27
