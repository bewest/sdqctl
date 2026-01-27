#!/bin/bash
# CONSULT Directive End-to-End Test Runner
# 
# Tests the CONSULT directive feature by:
# 1. Running a workflow that hits CONSULT
# 2. Verifying checkpoint status is "consulting"
# 3. Resuming and verifying prompt injection
# 4. Recording results for analysis
#
# Usage: ./test-consult.sh [options]
#
# Options:
#   --minimal   Run minimal test workflow (default)
#   --full      Run full consult-design.conv example
#   --mock      Use mock adapter (no API calls, quick validation)
#   --verbose   Verbose output
#   --help      Show this help
#
# Phases:
#   Phase A: Run workflow to CONSULT pause
#   Phase B: Verify checkpoint status
#   Phase C: Resume session (interactive)
#
# Output:
#   Logs saved to consult-test-logs/
#   Report saved to reports/consult-test-report-YYYY-MM-DD.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Defaults
TEST_WORKFLOW="minimal"
ADAPTER="copilot"
VERBOSE=""
DRY_RUN=""
OUTPUT_DIR="$SCRIPT_DIR/consult-test-logs"
SESSION_NAME="consult-test"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H%M%S)

# Command to run workflows (will change to 'iterate' when unified)
RUN_CMD="run"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --minimal)
            TEST_WORKFLOW="minimal"
            SESSION_NAME="consult-test-minimal"
            shift
            ;;
        --full)
            TEST_WORKFLOW="full"
            SESSION_NAME="design-consultation"
            shift
            ;;
        --mock)
            ADAPTER="mock"
            shift
            ;;
        --verbose|-v)
            VERBOSE="yes"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --session-name|-s)
            SESSION_NAME="$2"
            shift 2
            ;;
        --output-dir|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "CONSULT Directive End-to-End Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Workflow Selection:"
            echo "  --minimal   Run minimal test workflow (default)"
            echo "  --full      Run full consult-design.conv example"
            echo ""
            echo "Options:"
            echo "  --mock           Use mock adapter (no API calls)"
            echo "  --dry-run        Dry run (show what would happen)"
            echo "  --verbose, -v    Verbose output"
            echo "  --session-name   Override session name"
            echo "  --output-dir DIR Output directory for logs"
            echo ""
            echo "Examples:"
            echo "  $0                        # Run minimal test with real API"
            echo "  $0 --mock --verbose       # Quick validation with mock"
            echo "  $0 --full                 # Run full design consultation"
            echo ""
            echo "Test Phases:"
            echo "  Phase A: Run workflow to CONSULT pause point"
            echo "  Phase B: Verify checkpoint status ('consulting')"
            echo "  Phase C: Resume session and interact with agent"
            echo ""
            echo "The test pauses after Phase A so you can manually resume."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Select workflow file
if [[ "$TEST_WORKFLOW" == "full" ]]; then
    WORKFLOW_FILE="$SCRIPT_DIR/examples/workflows/consult-design.conv"
else
    WORKFLOW_FILE="$SCRIPT_DIR/tests/integration/workflows/consult-minimal.conv"
fi

# Check workflow exists
if [[ ! -f "$WORKFLOW_FILE" ]]; then
    echo "❌ Workflow not found: $WORKFLOW_FILE"
    exit 1
fi

# Log file for this run
LOG_FILE="$OUTPUT_DIR/consult-test-$DATE-$TIME.log"
CHECKPOINT_DIR="$HOME/.sdqctl/sessions/$SESSION_NAME"

echo "=============================================="
echo "CONSULT Directive End-to-End Test"
echo "=============================================="
echo "Date:       $DATE $TIME"
echo "Workflow:   $TEST_WORKFLOW"
echo "File:       $WORKFLOW_FILE"
echo "Adapter:    $ADAPTER"
echo "Session:    $SESSION_NAME"
echo "Output:     $OUTPUT_DIR"
echo "Log:        $LOG_FILE"
echo "=============================================="
echo ""

# Function to check checkpoint status
check_checkpoint() {
    local checkpoint_file="$CHECKPOINT_DIR/pause.json"
    
    if [[ -f "$checkpoint_file" ]]; then
        echo "✓ Checkpoint file exists: $checkpoint_file"
        
        # Extract status
        local status=$(python3 -c "import json; print(json.load(open('$checkpoint_file')).get('status', 'unknown'))" 2>/dev/null || echo "parse_error")
        local message=$(python3 -c "import json; print(json.load(open('$checkpoint_file')).get('message', ''))" 2>/dev/null || echo "")
        
        echo "  Status:  $status"
        echo "  Message: $message"
        
        if [[ "$status" == "consulting" ]]; then
            echo "✓ TC-02 PASS: Checkpoint status is 'consulting'"
            return 0
        else
            echo "✗ TC-02 FAIL: Expected 'consulting', got '$status'"
            return 1
        fi
    else
        echo "✗ Checkpoint file not found: $checkpoint_file"
        return 1
    fi
}

# Phase A: Run workflow to CONSULT pause
echo "═══════════════════════════════════════════════"
echo "Phase A: Run workflow to CONSULT pause point"
echo "═══════════════════════════════════════════════"
echo ""

# Clean up any existing session
if [[ -d "$CHECKPOINT_DIR" ]]; then
    echo "Cleaning up existing session: $SESSION_NAME"
    rm -rf "$CHECKPOINT_DIR"
fi

# Build run command
RUN_ARGS="--adapter $ADAPTER --session-name $SESSION_NAME"
if [[ -n "$DRY_RUN" ]]; then
    RUN_ARGS="$RUN_ARGS --dry-run"
fi

echo "Running: python3 -m sdqctl.cli $RUN_CMD $WORKFLOW_FILE $RUN_ARGS"
echo ""

# Run the workflow - it should pause at CONSULT
if python3 -m sdqctl.cli $RUN_CMD "$WORKFLOW_FILE" $RUN_ARGS 2>&1 | tee -a "$LOG_FILE"; then
    echo ""
    echo "✓ Workflow executed (check if it paused at CONSULT)"
else
    # Non-zero exit might be expected if CONSULT causes early exit
    echo ""
    echo "Workflow exited (this may be expected for CONSULT)"
fi

echo ""

# Phase B: Verify checkpoint status
echo "═══════════════════════════════════════════════"
echo "Phase B: Verify checkpoint status"
echo "═══════════════════════════════════════════════"
echo ""

TC02_RESULT="UNKNOWN"
if check_checkpoint; then
    TC02_RESULT="PASS"
else
    TC02_RESULT="FAIL"
fi

echo ""

# Show checkpoint content
if [[ -f "$CHECKPOINT_DIR/pause.json" ]]; then
    echo "Checkpoint content:"
    echo "---"
    cat "$CHECKPOINT_DIR/pause.json" | python3 -m json.tool 2>/dev/null || cat "$CHECKPOINT_DIR/pause.json"
    echo "---"
fi

echo ""

# Phase C: Resume instructions
echo "═══════════════════════════════════════════════"
echo "Phase C: Resume Session (Manual)"
echo "═══════════════════════════════════════════════"
echo ""
echo "To continue testing, resume the session:"
echo ""
echo "  sdqctl sessions resume $SESSION_NAME"
echo ""
echo "Or with a prompt:"
echo ""
echo "  sdqctl sessions resume $SESSION_NAME --prompt 'Present the open questions'"
echo ""
echo "Expected behavior on resume:"
echo "  1. Agent receives consultation prompt with topic"
echo "  2. Agent presents open questions interactively"
echo "  3. Agent uses ask_user tool for structured input"
echo ""

# Summary
echo "═══════════════════════════════════════════════"
echo "Test Summary"
echo "═══════════════════════════════════════════════"
echo ""
echo "TC-01: CONSULT pauses workflow     - Check log above"
echo "TC-02: Checkpoint saves status     - $TC02_RESULT"
echo "TC-03: Resume with prompt injection - Manual verification needed"
echo "TC-04: Agent presents questions     - Manual verification needed"
echo ""
echo "Log file: $LOG_FILE"
echo ""

# Generate quick report
REPORT_FILE="$OUTPUT_DIR/consult-test-summary-$DATE-$TIME.md"
cat > "$REPORT_FILE" << EOF
# CONSULT Test Summary - $DATE $TIME

## Configuration
- Workflow: $TEST_WORKFLOW ($WORKFLOW_FILE)
- Adapter: $ADAPTER
- Session: $SESSION_NAME

## Results

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-01 | CONSULT pauses workflow | Check log |
| TC-02 | Checkpoint saves status | $TC02_RESULT |
| TC-03 | Resume with prompt injection | Manual |
| TC-04 | Agent presents questions | Manual |

## Checkpoint Content

\`\`\`json
$(cat "$CHECKPOINT_DIR/pause.json" 2>/dev/null || echo "Not found")
\`\`\`

## Next Steps

1. Run: \`sdqctl sessions resume $SESSION_NAME\`
2. Verify agent presents questions
3. Answer questions and verify workflow continues
4. Record findings in reports/

## Log File

$LOG_FILE
EOF

echo "Summary saved: $REPORT_FILE"
echo ""
echo "=============================================="
echo "Phase A & B Complete - Resume manually to continue"
echo "=============================================="
