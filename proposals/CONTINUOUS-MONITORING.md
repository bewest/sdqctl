# Continuous Alignment Monitoring Proposal

> **Status**: Proposal (R&D)  
> **Priority**: P3 (Future)  
> **Effort**: High  
> **Source**: Nightscout ecosystem alignment requirements

## Summary

Add continuous monitoring capabilities to detect drift, breaking changes, and alignment opportunities across external repositories.

## Proposed Commands

### `sdqctl watch`

Monitor external repositories for changes that affect alignment:

```bash
# Watch all externals for changes
sdqctl watch --externals externals/

# Watch specific repos with webhook integration
sdqctl watch --repos "Loop,AAPS,Trio" \
  --webhook https://hooks.example.com/alignment

# Watch with automatic analysis
sdqctl watch --auto-analyze \
  --workflow workflows/analysis/gap-discovery.conv
```

### `sdqctl drift`

One-shot drift detection:

```bash
# Check for drift since last analysis
sdqctl drift --since "2026-01-01"

# Check specific paths
sdqctl drift --paths "*/treatments/*" --repos "Loop,AAPS"

# Generate drift report
sdqctl drift --report docs/drift-report.md
```

## Architecture

### Watch Loop

```python
class AlignmentWatcher:
    def watch(self, config: WatchConfig):
        while True:
            for repo in config.repos:
                changes = self.detect_changes(repo)
                if changes:
                    analysis = self.analyze_impact(changes)
                    if analysis.significant:
                        self.notify(analysis)
                        if config.auto_analyze:
                            self.trigger_workflow(analysis)
            
            sleep(config.interval)
```

### Change Detection

```python
def detect_changes(self, repo: Path) -> list[Change]:
    # Get commits since last check
    commits = git_log(repo, since=self.last_check[repo])
    
    changes = []
    for commit in commits:
        # Analyze changed files
        for file in commit.files:
            if self.is_alignment_relevant(file):
                changes.append(Change(
                    repo=repo,
                    file=file,
                    type=self.classify_change(file),
                    commit=commit
                ))
    
    return changes
```

### Impact Analysis

Classify changes by alignment impact:

| Impact Level | Description | Action |
|--------------|-------------|--------|
| Critical | API breaking change | Immediate notification + analysis |
| High | New treatment type or field | Queue for next analysis cycle |
| Medium | Implementation change | Log for batch review |
| Low | Documentation/comment only | Record for reference |

## Use Cases

### 1. Breaking Change Detection

```bash
# Nightscout API change detected
sdqctl watch --trigger-on "api/*" --action alert

# Output:
# ⚠️  Breaking change detected in cgm-remote-monitor
# File: lib/api3/doc/tutorial.md
# Commit: abc123
# Impact: High - API endpoint renamed
# Affected: Loop, AAPS, Trio sync logic
```

### 2. New Feature Discovery

```bash
# New treatment type added to AAPS
sdqctl watch --trigger-on "*/treatments/*" --action analyze

# Output:
# 🆕 New treatment type in AndroidAPS
# File: core/nssdk/src/main/kotlin/app/aaps/core/nssdk/localmodel/treatment/NSTherapyEvent.kt
# Type: TherapyEvent.Type.EXERCISE
# Action: Queued for terminology mapping
```

### 3. Drift Report Generation

```bash
sdqctl drift --since "2026-01-01" --report

# Output: docs/drift-report-2026-01.md
# - 47 commits across 6 repositories
# - 3 new treatment types discovered
# - 2 API changes requiring gap updates
# - 1 terminology drift detected
```

## Integration Points

### GitHub Webhooks

```yaml
# .github/workflows/alignment-check.yml
on:
  push:
    paths:
      - 'lib/api3/**'
      - 'lib/treatments/**'

jobs:
  check-alignment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check alignment impact
        run: sdqctl drift --paths "${{ github.event.commits[0].modified }}"
```

### Slack/Discord Notifications

```bash
sdqctl watch --notify slack \
  --webhook $SLACK_WEBHOOK \
  --filter "impact:high OR impact:critical"
```

### Automatic Workflow Triggers

```bash
# When drift detected, auto-run gap discovery
sdqctl watch --on-drift "sdqctl iterate workflows/analysis/gap-discovery.conv --prologue 'Drift detected: {{changes}}'"
```

## Monitoring Dashboard

Generate status page showing:

```markdown
# Alignment Status

## Repository Health

| Repository | Last Sync | Drift Status | Gaps |
|------------|-----------|--------------|------|
| Loop | 2h ago | ✓ Aligned | 2 open |
| AAPS | 1d ago | ⚠️ 3 changes | 5 open |
| Trio | 3h ago | ✓ Aligned | 1 open |
| Nightscout | 6h ago | ✓ Aligned | 3 open |

## Recent Changes

- [AAPS] New TherapyEvent type added (2h ago)
- [Loop] Treatment sync refactored (1d ago)
- [Nightscout] API v3.1 released (3d ago)
```

## Configuration

```yaml
# .sdqctl/watch.yaml
watch:
  interval: 1h
  repos:
    - path: externals/Loop
      triggers:
        - "LoopKit/*/Treatments/*"
        - "Loop/Managers/*Sync*"
    - path: externals/AndroidAPS
      triggers:
        - "core/nssdk/**"
        - "plugins/sync/**"
  
  notifications:
    - type: slack
      webhook: $SLACK_WEBHOOK
      filter: "impact >= high"
    - type: file
      path: docs/drift-log.md
      filter: all
  
  auto_workflows:
    - trigger: "new_treatment_type"
      workflow: workflows/analysis/extract-spec.conv
    - trigger: "api_change"
      workflow: workflows/analysis/gap-discovery.conv
```

## Open Questions

1. How to handle rate limits when watching many repos?
2. Should watch state persist across restarts?
3. How to deduplicate notifications for related changes?
4. Integration with existing CI/CD pipelines?

## Related Proposals

- [AGENTIC-ANALYSIS.md](./AGENTIC-ANALYSIS.md) - Autonomous analysis triggered by watch
- [SDK-SESSION-PERSISTENCE.md](./SDK-SESSION-PERSISTENCE.md) - State persistence
