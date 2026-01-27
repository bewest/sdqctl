# Upstream Contribution Support Proposal

> **Status**: Proposal (R&D)  
> **Priority**: P3 (Future)  
> **Effort**: High  
> **Source**: Nightscout ecosystem alignment requirements

## Summary

Add tooling to help draft and manage upstream contributions that address identified gaps, improving cross-project alignment through actual code and documentation changes.

## Proposed Commands

### `sdqctl delegate <GAP-ID>`

Draft upstream fixes for identified gaps:

```bash
# Draft a fix for a gap
sdqctl delegate GAP-SYNC-001 --to cgm-remote-monitor

# Generate PR template with context
sdqctl delegate GAP-BATCH-003 --to AndroidAPS \
  --branch fix/batch-timestamp-handling

# Dry run - show what would be created
sdqctl delegate GAP-API-002 --to Loop --dry-run
```

### `sdqctl upstream status`

Track contribution status across repos:

```bash
sdqctl upstream status

# Output:
# Upstream Contributions
# 
# | GAP-ID | Repository | Branch | PR | Status |
# |--------|------------|--------|-----|--------|
# | GAP-SYNC-001 | cgm-remote-monitor | fix/sync-order | #1234 | Open |
# | GAP-BATCH-003 | AndroidAPS | fix/batch-ts | #567 | Merged |
# | GAP-API-002 | Loop | - | - | Draft |
```

## Workflow

### 1. Gap to Contribution Flow

```
GAP-XXX-NNN identified
    ↓
sdqctl delegate GAP-XXX-NNN --to <repo>
    ↓
Agent analyzes gap and generates:
  - Branch name
  - Proposed changes (diff preview)
  - PR description from gap context
  - Test suggestions
    ↓
Human review and approval
    ↓
Branch created, PR opened
    ↓
Track in upstream status
    ↓
On merge: Update gap status to RESOLVED
```

### 2. Delegation Workflow

```dockerfile
# delegate-workflow.conv (internal)

MODEL claude-sonnet-4-20250514
ADAPTER copilot
MODE generation

CONTEXT @traceability/gaps.md
CONTEXT @traceability/requirements.md

PROMPT ## Analyze Gap for Upstream Fix

Gap ID: {{gap_id}}
Target Repository: {{target_repo}}

1. Load the gap details from traceability/gaps.md
2. Identify the specific files that need changes
3. Analyze the target repo's contribution guidelines
4. Draft the minimal fix that addresses the gap

Output:
- Files to modify
- Proposed changes (as diff)
- PR title and description
- Related requirements addressed
- Test suggestions

PROMPT ## Generate PR Template

Create a pull request template that:
1. Links back to the gap analysis
2. Explains the interoperability benefit
3. Includes test verification steps
4. References related projects that will benefit
```

## PR Template Generation

```markdown
## Summary

This PR addresses [GAP-{{gap_id}}](link-to-gap) identified in the
Nightscout ecosystem alignment analysis.

## Problem

{{gap_description}}

## Solution

{{proposed_fix_summary}}

## Interoperability Impact

This change improves compatibility with:
- [ ] Loop
- [ ] AndroidAPS  
- [ ] Trio
- [ ] Other: ___

## Verification

{{test_suggestions}}

## Related

- Gap Analysis: {{gap_link}}
- Requirements: {{req_links}}
- Ecosystem Alignment: [rag-nightscout-ecosystem-alignment](repo-link)
```

## Contribution Tracking

### Database Schema

```yaml
# .sdqctl/contributions.yaml
contributions:
  - gap_id: GAP-SYNC-001
    target_repo: cgm-remote-monitor
    branch: fix/sync-order
    pr_number: 1234
    pr_url: https://github.com/nightscout/cgm-remote-monitor/pull/1234
    status: open
    created: 2026-01-15
    updated: 2026-01-20
    
  - gap_id: GAP-BATCH-003
    target_repo: AndroidAPS
    branch: fix/batch-timestamp
    pr_number: 567
    pr_url: https://github.com/nightscout/AndroidAPS/pull/567
    status: merged
    merged: 2026-01-18
```

### Status Sync

```bash
# Sync PR status from GitHub
sdqctl upstream sync

# Auto-update gaps on merge
sdqctl upstream sync --update-gaps
```

## Cross-Project Dependencies

Track when fixes in one repo depend on or enable fixes in others:

```yaml
dependencies:
  - gap_id: GAP-API-002
    upstream:
      - repo: cgm-remote-monitor
        pr: 1234
        status: open
    downstream:
      - repo: Loop
        blocked_by: GAP-API-002
      - repo: AndroidAPS
        blocked_by: GAP-API-002
```

### Dependency Visualization

```bash
sdqctl upstream deps GAP-API-002

# Output:
# GAP-API-002: Nightscout API v3.1 batch endpoint
# 
# Upstream (must merge first):
#   └── cgm-remote-monitor#1234 [OPEN]
#         Adds batch upload endpoint
# 
# Downstream (blocked until upstream merges):
#   ├── Loop: Can't implement batch sync
#   └── AndroidAPS: Using workaround
```

## Safety Guardrails

### Human Approval Required

```bash
# Always require approval before creating branches/PRs
sdqctl delegate GAP-XXX --approve

# Show what would happen
sdqctl delegate GAP-XXX --dry-run
```

### Repository Permissions

- Read-only access to external repos by default
- Write access only to user-owned forks
- PR creation requires explicit `--create-pr` flag

### Change Scope Limits

- Maximum files per PR: 10
- Maximum lines changed: 500
- Automatic split suggestion for larger changes

## Integration

### GitHub CLI

```bash
# Uses gh cli for PR operations
sdqctl delegate GAP-XXX --to repo \
  --gh-token $GITHUB_TOKEN

# Or use GitHub App
sdqctl delegate GAP-XXX --to repo \
  --github-app $APP_ID
```

### Contribution Guidelines Awareness

```bash
# Parse CONTRIBUTING.md before drafting
sdqctl delegate GAP-XXX --to repo --respect-guidelines

# Output includes:
# ⚠️  Repository requires:
#   - Signed commits
#   - Issue reference in PR title
#   - Test coverage > 80%
```

## Open Questions

1. How to handle repos with different branching strategies?
2. Should we auto-create issues before PRs?
3. How to handle CLA requirements?
4. Integration with project-specific CI checks?

## Related Proposals

- [AGENTIC-ANALYSIS.md](./AGENTIC-ANALYSIS.md) - Gap identification that feeds delegation
- [CONTINUOUS-MONITORING.md](./CONTINUOUS-MONITORING.md) - Track upstream changes after merge
