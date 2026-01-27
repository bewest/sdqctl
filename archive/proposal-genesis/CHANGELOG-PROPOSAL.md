# Proposal Changes - January 2026

## Major Updates

### 1. Command Structure: `copilot do` → `copilot agent`

**Rationale:**
- Avoids bash keyword conflict with `do`
- Creates unified command suite for agent orchestration
- Aligns with existing slash command mental model

**New Command Structure:**
```bash
copilot agent plan       # Strategic planning (/plan)
copilot agent apply      # Execute workflows (like kubectl apply)
copilot agent batch      # Parallel/sequential execution
copilot agent checkpoint # Manage checkpoints
copilot agent compact    # Trigger compaction
```

### 2. ConversationFile Syntax: `CONTEXT @file` → `@file`

**Rationale:**
- Matches existing interactive `@` syntax
- Cleaner, more intuitive
- Consistent with how users already work

**Before:**
```dockerfile
CONTEXT @lib/auth/*.js
CONTEXT @tests/*.test.js
```

**After:**
```dockerfile
@lib/auth/*.js
@tests/*.test.js
```

### 3. Context & Compaction Controls

**New Keywords Added:**

```dockerfile
# Context management
MAX-CONTEXT-TOKENS 150000          # Auto-compact when approaching limit
COMPACT-EVERY 50000                # Or compact every N tokens
COMPACT-STRATEGY checkpoints       # How to compact: summary|checkpoints|preserve-plan

# Quine-like pointers for multi-session workflows
BEFORE-COMPACT-PROMPT "Summarize progress and next steps"
ON-CONTEXT-LIMIT-PROMPT "Create continuation file for next session"
```

**Rationale:**
- Enables long-running workflows
- Provides control over context window usage
- Supports multi-session continuation with "quine-like pointers"

### 4. Checkpoint Management

**New Command:**
```bash
copilot agent checkpoint save "milestone-name"
copilot agent checkpoint restore "milestone-name"
copilot agent checkpoint list
```

**New Keyword in .copilot files:**
```dockerfile
CHECKPOINT "auth-analysis-complete"
```

**Rationale:**
- Enables rollback capability
- Creates audit trail
- Supports iterative development

### 5. Manual Compaction Control

**New Command:**
```bash
copilot agent compact                    # Trigger compaction
copilot agent compact --save-pointer     # With continuation pointer
```

**Rationale:**
- Gives users explicit control
- Supports strategic context management
- Aligns with existing `/compact` slash command

## Compatibility

### Breaking Changes
- `copilot do` → `copilot agent apply`
- `copilot loop` → `copilot agent batch`
- `copilot plan` → `copilot agent plan`
- `CONTEXT @file` → `@file` (in .copilot files)

### Migration Path

**Update command invocations:**
```bash
# Old
copilot do workflow.copilot
copilot loop workflows/*.copilot
copilot plan workflow.copilot

# New
copilot agent apply workflow.copilot
copilot agent batch workflows/*.copilot
copilot agent plan workflow.copilot
```

**Update .copilot files:**
```bash
# Automated migration
sed -i 's/^CONTEXT @/@ /' workflows/*.copilot
```

## Benefits

### 1. Better Alignment with Existing CLI
- Commands map directly to slash commands
- No bash keyword conflicts
- Consistent `@` file inclusion syntax

### 2. Enhanced Long-Running Workflow Support
- Context compaction controls
- Checkpoint save/restore
- Multi-session continuation via quine-like pointers

### 3. Clearer Mental Model
- `copilot agent` groups related functionality
- `apply` suggests declarative, idempotent execution
- `batch` clearly indicates parallel/sequential processing

## Examples

### Before
```bash
copilot do ./workflows/audit.copilot
copilot loop --parallel 3 workflows/*.copilot
```

```dockerfile
# workflows/audit.copilot
MODEL claude-sonnet-4.5
CONTEXT @lib/auth/*.js
CONTEXT @tests/*.test.js
PROMPT Audit authentication
```

### After
```bash
copilot agent apply ./workflows/audit.copilot
copilot agent batch --parallel 3 workflows/*.copilot
```

```dockerfile
# workflows/audit.copilot
MODEL claude-sonnet-4.5
MAX-CONTEXT-TOKENS 150000
COMPACT-EVERY 50000
BEFORE-COMPACT-PROMPT "Summarize findings so far"

@lib/auth/*.js
@tests/*.test.js

PROMPT Audit authentication
CHECKPOINT "initial-audit-complete"

# Continue analysis...
ON-CONTEXT-LIMIT-PROMPT "Save findings to AUDIT-PROGRESS.md for next session"
```

## Implementation Notes

### Phase 1: Core Commands
- Implement `copilot agent apply`
- Implement `copilot agent batch`
- Implement `copilot agent plan`
- Support basic .copilot file parsing with `@` syntax

### Phase 2: Context Management
- Add `MAX-CONTEXT-TOKENS`, `COMPACT-EVERY` keywords
- Add `COMPACT-STRATEGY` support
- Implement auto-compaction triggers

### Phase 3: Advanced Features
- Add `copilot agent checkpoint` command
- Add `copilot agent compact` command
- Support `BEFORE-COMPACT-PROMPT` and `ON-CONTEXT-LIMIT-PROMPT`
- Implement checkpoint strategies during compaction

### Phase 4: Migration Tooling
- Provide migration script for old syntax
- Add deprecation warnings for `copilot do`/`copilot loop`
- Update documentation and examples

---

**Status:** Proposal Updated  
**Date:** January 19, 2026  
**Version:** 2.0
