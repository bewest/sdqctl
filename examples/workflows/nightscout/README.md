# Nightscout Ecosystem Workflows
# Example .conv workflows for auditing diabetes data systems

This directory contains example sdqctl workflows generated from the
rag-nightscout-ecosystem-alignment research fixtures.

## Available Workflows

| Workflow | Description | Source Fixture |
|----------|-------------|----------------|
| `aaps-upload-audit.conv` | Analyze AAPS upload patterns | `aaps-single-doc.js` |
| `dedup-strategy-audit.conv` | Compare deduplication strategies | `deduplication.js` |
| `edge-case-audit.conv` | Test edge case handling | `edge-cases.js` |

## Usage

```bash
# Run with mock adapter (no AI calls)
sdqctl run examples/workflows/nightscout/aaps-upload-audit.conv --adapter mock

# Run with dry-run to see configuration
sdqctl run examples/workflows/nightscout/dedup-strategy-audit.conv --dry-run

# Run with actual AI adapter
sdqctl run examples/workflows/nightscout/edge-case-audit.conv --adapter copilot
```

## Context Requirements

These workflows reference files from the rag-nightscout-ecosystem-alignment
repository. Ensure the repository is available at:

```
externals/rag-nightscout-ecosystem-alignment/
├── docs/60-research/fixtures/
│   ├── aaps-single-doc.js
│   ├── deduplication.js
│   ├── edge-cases.js
│   └── ...
├── mapping/client/
│   ├── aaps-openaps-upload.md
│   ├── loop-upload.md
│   └── ...
└── specs/nightscout-api/
    └── entries-spec.md
```

## Generating New Workflows

To generate workflows from other fixtures:

```bash
# Use the fixture conversion script
python scripts/fixture_to_workflow.py docs/60-research/fixtures/new-fixture.js
```

## Testing

These workflows are used as integration tests:

```bash
# Run all nightscout workflow tests
pytest tests/test_nightscout_workflows.py

# Test individual workflow
sdqctl validate examples/workflows/nightscout/aaps-upload-audit.conv
```
