#!/bin/bash
# sdqctl test runner for rag-nightscout-ecosystem-alignment
# Usage: ./test-sdqctl.sh

set -e

# Setup
export PYTHONPATH="/home/bewest/src/copilot-do-proposal/sdqctl:$PYTHONPATH"
TARGET_REPO="/home/bewest/src/rag-nightscout-ecosystem-alignment"

echo "=============================================="
echo "sdqctl Test Suite"
echo "Target: $TARGET_REPO"
echo "=============================================="

cd "$TARGET_REPO"

# Create test workflows
cat > /tmp/test-docs-audit.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @docs/**/*.md
CONTEXT @README.md

PROMPT Analyze the documentation structure and identify coverage gaps and outdated sections.

OUTPUT-FORMAT markdown
EOF

cat > /tmp/test-tools-review.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit  
MAX-CYCLES 1

CONTEXT @tools/*.py

PROMPT Review the Python tools for code quality, error handling, and documentation.

OUTPUT-FORMAT markdown
EOF

cat > /tmp/test-traceability.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @traceability/*.md
CONTEXT @conformance/**/*.md

PROMPT Analyze traceability coverage and identify gaps in requirement mapping.

OUTPUT-FORMAT markdown
EOF

echo ""
echo "=== Test 1: Adapter Status ==="
python3 -m sdqctl.cli status --adapters

echo ""
echo "=== Test 2: Validate Workflows ==="
for wf in /tmp/test-docs-audit.conv /tmp/test-tools-review.conv /tmp/test-traceability.conv; do
    echo "Validating $(basename $wf)..."
    python3 -m sdqctl.cli validate "$wf"
done

echo ""
echo "=== Test 3: Dry Run ==="
python3 -m sdqctl.cli run /tmp/test-docs-audit.conv --adapter mock --dry-run

echo ""
echo "=== Test 4: Execute Workflow ==="
python3 -m sdqctl.cli run /tmp/test-tools-review.conv --adapter mock --verbose

echo ""
echo "=== Test 5: Show Parsed Workflow ==="
python3 -m sdqctl.cli show /tmp/test-traceability.conv

echo ""
echo "=============================================="
echo "✓ All tests passed!"
echo "=============================================="
