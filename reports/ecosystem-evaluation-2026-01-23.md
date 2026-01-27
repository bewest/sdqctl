# Nightscout Ecosystem sdqctl Integration Evaluation

**Date**: 2026-01-23  
**sdqctl Version**: 0.1.0  
**Target Workspace**: rag-nightscout-ecosystem-alignment  
**Workflows Tested**: 27 ConversationFiles

## Executive Summary

Successfully evaluated sdqctl against the Nightscout ecosystem alignment workspace. All 27 workflows validate, and two live workflows completed successfully via the copilot adapter. Key gap identified: **ref format mismatch** prevents VERIFY directive from replacing ecosystem Python tools.

## Results Overview

| Category | Status | Details |
|----------|--------|---------|
| Workflow Validation | ✅ 27/27 pass | All validate with `--allow-missing` |
| Context Resolution | ✅ Working | Globs, optionals, templates functional |
| RUN Directive | ⚠️ Partial | Executes but exit code semantics differ |
| VERIFY Directive | 🔴 Gap | Format mismatch with ecosystem refs |
| Mock Adapter | ✅ Working | Fast testing mode functional |
| Copilot Adapter | ✅ Success | Live tests completed |

## Live Workflow Tests

### Test 1: progress-update.conv
- **Time**: 48 seconds, 7 turns
- **Outcome**: Updated progress.md with STPA framework entry

### Test 2: gap-discovery.conv  
- **Time**: 662 seconds (~11 min), 145 turns
- **Outcome**: Generated 871 lines: 16 gaps, 14 requirements
- **Note**: Compaction triggered at turn 30 (128K→25K tokens)

## Critical Gap: Ref Format Mismatch

| System | Format | Example |
|--------|--------|---------|
| Ecosystem | `` `alias:path#L10-L50` `` | `` `loop:Loop/Models/Override.swift#L10` `` |
| sdqctl | `@path` | `@traceability/requirements.md` |

**Impact**: VERIFY directive cannot replace ecosystem Python tools

**Proposed Solution**: `refcat` command/directive (see proposals/REFCAT-DIRECTIVE.conv)

## Recommendations for Future sdqctl Development

### P0 - For Full Ecosystem Integration

1. **REFCAT directive** - Extract content from refs with line ranges
   - Status: Proposal saved as `proposals/REFCAT-DIRECTIVE.conv`
   - Enables: Piping ref specs to get content, replacing grep chains

2. **RUN branching** - Conditional execution based on RUN results
   - Need: `RUN-IF`, `RUN-ELSE`, or `RUN-ON exit_code=N`
   - Enables: Different paths based on verification tool findings

### P1 - Enhanced Integration

3. **Alias-aware ref resolution** - Read `workspace.lock.json`
   - Enables: Unified ref format across sdqctl and ecosystem

4. **Pluggable verifiers** - Register ecosystem tools as VERIFY backends
   - Enables: `VERIFY refs` using ecosystem's verify_refs.py

### P2 - Quality of Life

5. **Model availability documentation** - Which models work via copilot adapter
6. **Exit code conventions** - Document expected RUN exit codes

## What's Working Well

- `VALIDATION-MODE lenient` - Essential for cross-repo workflows
- `CONTEXT-OPTIONAL` - Handles missing externals gracefully  
- `ON-CONTEXT-LIMIT compact` - Large workflows continue after compaction
- Template variables (`{{DATE}}`, `{{GIT_BRANCH}}`) - Useful for tracking

## Next Steps

1. Implement REFCAT when ecosystem workflows need inline code context
2. Add RUN branching when conditional verification paths are needed
3. Consider pluggable verifiers for ecosystem tool integration

## Files Generated

- `reports/ecosystem-evaluation-2026-01-23.md` (this report)
- `proposals/REFCAT-DIRECTIVE.conv` (deferred implementation)

## Recommended Workflows for sdqctl Driving

Based on evaluation, these ecosystem workflows are most compatible with current sdqctl:

### Ready to Use (No Modifications Needed)

| Workflow | Purpose | Recommended Command |
|----------|---------|---------------------|
| `progress-update.conv` | Track session progress | `sdqctl run ... --adapter copilot --model gpt-4o` |
| `gap-discovery.conv` | Discover documentation gaps | `sdqctl run ... --model gpt-4o` |
| `deep-dive-template.conv` | 5-facet project analysis | `sdqctl run ... --model gpt-4o` |
| `specification-template.conv` | Generate specifications | `sdqctl run ... --model gpt-4o` |

### Need Minor Updates

| Workflow | Issue | Fix |
|----------|-------|-----|
| `tool-validation.conv` | Uses RUN with `2>/dev/null` | Remove stderr suppression |
| `verification-loop.conv` | Expects RUN exit code = 0 for "issues found" | Update expectations |
| `ci-pipeline.conv` | No RUN-RETRY usage | Add RUN-RETRY for flaky steps |

### Blocked Until Features Implemented

| Workflow | Blocking Gap | Required Feature |
|----------|-------------|------------------|
| Any using ecosystem refs | `alias:path#L10` format | REFCAT or alias-aware refs |
| Conditional verification | Branch on RUN result | ON-FAILURE blocks |
| Code context injection | Need file excerpts in prompt | REFCAT directive |

## Feature Priority for Ecosystem Integration

### Implemented & Working

- `RUN-RETRY N "prompt"` - ✅ Available for flaky command recovery
- `RUN-ON-ERROR continue` - ✅ Available for graceful failure handling
- `VALIDATION-MODE lenient` - ✅ Available for cross-repo workflows
- `ON-CONTEXT-LIMIT compact` - ✅ Works well in long workflows

### P0: Needed for Full Integration

1. **ON-FAILURE blocks** (proposal: RUN-BRANCHING.md, Phase 2)
   - Use case: Branch verification path based on tool findings
   - Current workaround: Use synthesis cycles with progress file

2. **REFCAT directive** (proposal: proposals/REFCAT-DIRECTIVE.conv)
   - Use case: Extract code context from refs into prompts
   - Current workaround: Manual grep chains in prompts

### P1: Would Improve Experience

3. **Alias-aware ref resolution**
   - Use case: `VERIFY refs` works with ecosystem `alias:path#L10` format
   - Current workaround: Use `RUN python3 tools/verify_refs.py`

4. **Model availability detection**
   - Use case: Workflow specifies capability, sdqctl selects model
   - Current workaround: `--model gpt-4o` override

## Commands for Replication

```bash
# Validate all workflows
cd externals/rag-nightscout-ecosystem-alignment
source activate-sdqctl.sh
for f in workflows/**/*.conv; do sdqctl validate "$f" --allow-missing; done

# Mock test
sdqctl run workflows/discovery/gap-discovery.conv --adapter mock

# Live test (requires copilot adapter)
sdqctl run workflows/iterate/progress-update.conv --adapter copilot --model gpt-4o

# Use RUN-RETRY for flaky commands (already implemented)
# Add to workflow: RUN-RETRY 3 "Fix the failing check"
```
