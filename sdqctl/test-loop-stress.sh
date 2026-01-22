#!/bin/bash
# Loop Detection Stress Test Runner
# Usage: ./test-loop-stress.sh [options]
#
# Options:
#   --all       Run all tests (default)
#   --repeated  Run only repeated prompt test
#   --elicit    Run only loop elicit test
#   --minimal   Run only minimal response test
#   --mock      Use mock adapter (no API calls)
#   --verbose   Verbose output
#   --cycles N  Number of cycles for repeated test (default: 5)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Defaults
TEST_CMD="all"
ADAPTER="copilot"
VERBOSE=""
CYCLES="5"
OUTPUT_DIR="$SCRIPT_DIR/loop-test-logs"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            TEST_CMD="all"
            shift
            ;;
        --repeated)
            TEST_CMD="repeated"
            shift
            ;;
        --elicit)
            TEST_CMD="elicit"
            shift
            ;;
        --minimal)
            TEST_CMD="minimal"
            shift
            ;;
        --mock)
            ADAPTER="mock"
            shift
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --cycles|-n)
            CYCLES="$2"
            shift 2
            ;;
        --output-dir|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Loop Detection Stress Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Test Selection:"
            echo "  --all       Run all tests (default)"
            echo "  --repeated  Run only repeated prompt test"
            echo "  --elicit    Run only loop elicit test"
            echo "  --minimal   Run only minimal response test"
            echo ""
            echo "Options:"
            echo "  --mock           Use mock adapter (no API calls)"
            echo "  --verbose, -v    Verbose output"
            echo "  --cycles N       Number of cycles for repeated test (default: 5)"
            echo "  --output-dir DIR Output directory for event logs"
            echo ""
            echo "Examples:"
            echo "  $0                       # Run all tests with real API"
            echo "  $0 --mock --verbose      # Test with mock adapter"
            echo "  $0 --repeated --cycles 3 # Quick repeated test"
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

echo "=============================================="
echo "Loop Detection Stress Test"
echo "=============================================="
echo "Adapter:    $ADAPTER"
echo "Test:       $TEST_CMD"
echo "Output:     $OUTPUT_DIR"
echo "=============================================="
echo ""

# Build command
CMD="python3 -m tests.integration.test_loop_stress"
CMD="$CMD --adapter $ADAPTER"
CMD="$CMD --output-dir $OUTPUT_DIR"
CMD="$CMD $VERBOSE"

if [[ "$TEST_CMD" == "repeated" ]]; then
    CMD="$CMD repeated --cycles $CYCLES"
elif [[ "$TEST_CMD" == "elicit" ]]; then
    CMD="$CMD elicit"
elif [[ "$TEST_CMD" == "minimal" ]]; then
    CMD="$CMD minimal"
else
    CMD="$CMD all --cycles $CYCLES"
fi

# Run from sdqctl directory
cd "$SCRIPT_DIR"
$CMD

echo ""
echo "=============================================="
echo "Test Complete"
echo "Event logs saved to: $OUTPUT_DIR"
echo "=============================================="
