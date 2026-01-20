# sdqctl Examples

This directory contains example workflows for sdqctl.

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

- `security-audit.conv` - Security vulnerability analysis
- `typescript-migration.conv` - Multi-cycle TypeScript conversion
- `documentation-sync.conv` - Documentation consistency check
- `human-review.conv` - Human-in-the-loop review with PAUSE directive
