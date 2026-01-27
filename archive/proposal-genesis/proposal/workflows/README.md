# Example Workflows for copilot-do

This directory contains real-world ConversationFile workflows based on analysis of the Nightscout ecosystem development patterns (see `GIT-HISTORY-ANALYSIS.md`).

## Directory Structure

```
workflows/
├── cross-repo/           # Cross-repository coordination workflows
├── governance/           # Regulatory, security, and compliance workflows
├── agent-collab/         # AI-human collaboration tracking workflows
├── documentation/        # Documentation sync and validation workflows
├── audit/                # Component audit workflows
├── oidc/                 # OIDC implementation workflows
└── test-cycle/           # Test generation and validation workflows
```

## Workflow Categories

### Cross-Repository Workflows

**Purpose:** Coordinate changes across multiple repositories in the Nightscout ecosystem.

- **`verify-breaking-changes.copilot`** - Analyze API changes and their impact on dependent repos
  
  ```bash
  # Before releasing a new version
  copilot do workflows/cross-repo/verify-breaking-changes.copilot \
    --format markdown \
    --output breaking-changes-report.md
  ```

**Use Case:** From GIT-HISTORY-ANALYSIS.md Use Case 4 - Track how changes in cgm-remote-monitor affect nightscout-connect and nightscout-roles-gateway.

### Governance Workflows

**Purpose:** Support regulatory compliance, security audits, and clinical validation.

- **`clinical-validation.copilot`** - Document clinical impact of algorithm changes (FDA audit trail)
- **`security-audit.copilot`** - Comprehensive security vulnerability assessment

```bash
# Run security audit before release
copilot do workflows/governance/security-audit.copilot \
  --mode audit \
  --format json \
  --output security-audit-$(date +%Y%m%d).json

# Generate clinical validation documentation
copilot do workflows/governance/clinical-validation.copilot \
  --mode audit \
  --format markdown \
  --output clinical-validation-report.md
```

**Use Cases:**
- Use Case 1: Regulatory audit trail for medical device software (FDA, HIPAA)
- Use Case 2: Security incident response and vulnerability tracking

### Agent Collaboration Workflows

**Purpose:** Track and analyze AI-human collaboration patterns.

- **`multi-agent-trace.copilot`** - Analyze agent contributions and attribution

```bash
# Monthly agent collaboration analysis
copilot do workflows/agent-collab/multi-agent-trace.copilot \
  --format markdown \
  --output reports/agent-collab-$(date +%Y-%m).md
```

**Use Case:** From Use Case 3 - Understand contribution breakdown between human and AI, track agent effectiveness.

### Documentation Workflows

**Purpose:** Ensure documentation stays in sync with code changes.

- **`sync-verification.copilot`** - Verify docs match code, check for outdated examples

```bash
# Run in CI/CD
copilot do workflows/documentation/sync-verification.copilot \
  --format json \
  --output sync-check.json

# Fail build if gaps found
jq -e '.sync_gaps == 0' sync-check.json || exit 1
```

**Use Case:** From Use Case 5 - Automatic linking between code and doc commits.

## Running Workflows

### Single Workflow

```bash
# Execute a workflow
copilot do workflows/governance/security-audit.copilot

# With options
copilot do workflows/governance/security-audit.copilot \
  --mode audit \
  --format markdown \
  --output reports/security-audit.md
```

### Batch Execution

```bash
# Run all governance workflows
copilot loop workflows/governance/*.copilot \
  --parallel 2 \
  --format jsonl \
  --output governance-results.jsonl

# Run all workflows (sequentially for safety)
copilot loop workflows/**/*.copilot
```

### Integration with CI/CD

#### GitHub Actions Example

```yaml
# .github/workflows/quality-checks.yml
name: Quality Checks

on:
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Security Audit
        run: |
          copilot do workflows/governance/security-audit.copilot \
            --mode audit \
            --format json \
            --output security-audit.json
            
      - name: Check for Critical Issues
        run: |
          CRITICAL=$(jq '[.findings[] | select(.severity == "Critical")] | length' security-audit.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "::error::$CRITICAL critical security issues found"
            exit 1
          fi
          
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: security-audit
          path: security-audit.json

  doc-sync:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify Documentation Sync
        run: |
          copilot do workflows/documentation/sync-verification.copilot \
            --format json \
            --output sync-check.json
            
      - name: Check for Gaps
        run: |
          jq -e '.sync_gaps == 0' sync-check.json || {
            echo "::warning::Documentation sync gaps found"
            jq '.gaps' sync-check.json
          }
```

## Workflow Templates

### Creating Custom Workflows

Based on the patterns in this directory, here's a template:

```dockerfile
# [Workflow Name]
# Based on: [Use case or requirement]
# Purpose: [What this workflow accomplishes]

MODEL claude-sonnet-4.5
MODE [read-only|audit|docs-only|tests-only|full]
MAX-CYCLES 1

CWD ./

PROLOGUE [Context information - date, version, etc.]

PROMPT [What to analyze]
CONTEXT @[files to include]

PROMPT [Specific tasks to perform]

PROMPT [Output format and requirements]
```

### Common Modes

- **`read-only`** - Analyze and document, make no changes
- **`audit`** - Same as read-only but focused on compliance/governance
- **`docs-only`** - Can only modify documentation files
- **`tests-only`** - Can only modify test files
- **`full`** - Can modify any files (use with caution)

## Best Practices

### 1. Use Descriptive Names

```
✅ verify-breaking-changes.copilot
✅ security-audit.copilot
❌ check.copilot
❌ workflow1.copilot
```

### 2. Document Purpose

Always include header comments explaining:
- What the workflow does
- Which use case it addresses
- How to run it
- Expected outputs

### 3. Set Appropriate Modes

```dockerfile
# For analysis/reporting - use read-only or audit
MODE audit

# For targeted updates - use restrictive modes
MODE docs-only
MODE tests-only

# For complex changes - use full mode carefully
MODE full
```

### 4. Limit Cycles

```dockerfile
# Most workflows should complete in one cycle
MAX-CYCLES 1

# Only use higher values when iterative refinement is needed
MAX-CYCLES 3  # For complex refactoring
```

### 5. Include Context

```dockerfile
# Add relevant context files
CONTEXT @lib/api/**/*.js
CONTEXT @docs/api-v3.md
CONTEXT @CHANGELOG.md

# Add prologue for runtime context
PROLOGUE Current version: $(git describe --tags)
PROLOGUE Analysis date: $(date -Iseconds)
```

## Integration with Complementary Tooling

These workflows are designed to work with the proposed complementary tooling:

### Component Discovery

```bash
# Generate audit workflows for all components
copilot list-components --type plugin --format json | \
jq -r '.components[].id' | \
while read component; do
  copilot list-components --id "$component" --generate-workflow audit \
    > "workflows/audit/audit-$component.copilot"
done
```

### Component Verification

```bash
# Verify components, then run fix workflows
copilot verify-components --format json > verification.json

jq -r '.failures[] | .id' verification.json | \
while read component; do
  copilot do "Fix verification issues in $component"
done
```

### Traceability

```bash
# Generate audit trail report
copilot trace --since 2024-01-01 \
  --clinical-impact high \
  --format markdown \
  --output audit-trail-2024.md
```

## Nightscout-Specific Examples

### Pre-Release Checklist

```bash
#!/bin/bash
# pre-release.sh - Run before creating a release

VERSION=$1

echo "Pre-release checks for v$VERSION"

# 1. Security audit
copilot do workflows/governance/security-audit.copilot \
  --mode audit \
  --output "reports/security-audit-$VERSION.json"

# 2. Clinical validation
copilot do workflows/governance/clinical-validation.copilot \
  --mode audit \
  --output "reports/clinical-validation-$VERSION.md"

# 3. Breaking changes
copilot do workflows/cross-repo/verify-breaking-changes.copilot \
  --output "reports/breaking-changes-$VERSION.md"

# 4. Documentation sync
copilot do workflows/documentation/sync-verification.copilot \
  --format json \
  --output "reports/doc-sync-$VERSION.json"

# 5. Check results
echo "Checking for blockers..."
CRITICAL=$(jq '[.findings[] | select(.severity == "Critical")] | length' reports/security-audit-$VERSION.json)
GAPS=$(jq '.sync_gaps' reports/doc-sync-$VERSION.json)

if [ "$CRITICAL" -gt 0 ]; then
  echo "❌ $CRITICAL critical security issues - RELEASE BLOCKED"
  exit 1
fi

if [ "$GAPS" -gt 0 ]; then
  echo "⚠️  $GAPS documentation sync gaps found"
fi

echo "✅ Pre-release checks complete"
echo "Reports in reports/"
```

### Monthly Review

```bash
#!/bin/bash
# monthly-review.sh - Run monthly for ongoing governance

MONTH=$(date +%Y-%m)

# Agent collaboration analysis
copilot do workflows/agent-collab/multi-agent-trace.copilot \
  --output "reports/agent-collab-$MONTH.md"

# Security audit
copilot do workflows/governance/security-audit.copilot \
  --mode audit \
  --output "reports/security-$MONTH.json"

# Documentation sync
copilot do workflows/documentation/sync-verification.copilot \
  --output "reports/doc-sync-$MONTH.md"

echo "Monthly review complete for $MONTH"
echo "Reports in reports/"
```

## References

- **GIT-HISTORY-ANALYSIS.md** - Analysis of Nightscout development patterns
- **COMPLEMENTARY-TOOLING.md** - Proposed tooling ecosystem
- **../NIGHTSCOUT-WORKFLOW-ANALYSIS.md** - Detailed Nightscout workflow analysis

## Contributing

When adding new workflows:

1. Follow naming convention: `category/verb-noun.copilot`
2. Include header comments with purpose and use case
3. Set appropriate MODE and MAX-CYCLES
4. Document expected outputs
5. Add examples to this README
6. Link to relevant use cases in GIT-HISTORY-ANALYSIS.md
