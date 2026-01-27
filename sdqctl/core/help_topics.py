"""
Help topics for HELP directive injection and sdqctl help command.

This module is separate from commands/help.py to avoid circular imports.
core/renderer.py and core/conversation.py need access to TOPICS without
importing the full commands module.
"""

# Topic documentation
TOPICS = {
    "directives": """
# ConversationFile Directives

Directives control workflow behavior in `.conv` files.

## Core Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `MODEL` | AI model to use | `MODEL gpt-4` |
| `ADAPTER` | AI provider | `ADAPTER copilot` |
| `MODE` | Execution mode | `MODE audit` |
| `MAX-CYCLES` | Maximum iterations | `MAX-CYCLES 5` |
| `SESSION-NAME` | Named session for resumability | `SESSION-NAME audit-2026-01` |
| `PROMPT` | Prompt to send | `PROMPT Analyze the code` |

## Model Requirements (Abstract Selection)

| Directive | Purpose | Example |
|-----------|---------|---------|
| `MODEL-REQUIRES` | Capability requirement | `MODEL-REQUIRES context:50k` |
| `MODEL-PREFERS` | Soft preference (hint) | `MODEL-PREFERS vendor:anthropic` |
| `MODEL-POLICY` | Resolution strategy | `MODEL-POLICY cheapest` |

Requirements: `context:Nk`, `tier:economy|standard|premium`, `speed:fast|standard|deliberate`,
`capability:code|reasoning|general`

## Context Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `CONTEXT` | Include file/pattern | `CONTEXT @lib/*.js` |
| `CONTEXT-LIMIT` | Window threshold | `CONTEXT-LIMIT 80%` |
| `ON-CONTEXT-LIMIT` | Limit action | `ON-CONTEXT-LIMIT compact` |

## Injection Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `PROLOGUE` | Prepend to first prompt | `PROLOGUE Current date: {{DATE}}` |
| `EPILOGUE` | Append to last prompt | `EPILOGUE Update progress.md` |
| `HELP` | Inject help topics (prologue) | `HELP directives workflow` |
| `HELP-INLINE` | Inject help before next prompt | `HELP-INLINE stpa gap-ids` |
| `HEADER` | Prepend to output | `HEADER # Report` |
| `FOOTER` | Append to output | `FOOTER ---` |

## RUN Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `RUN` | Execute shell command | `RUN pytest -v` |
| `RUN-RETRY` | Retry with AI fix | `RUN-RETRY 3 "Fix errors"` |
| `RUN-ON-ERROR` | Error behavior | `RUN-ON-ERROR continue` |
| `RUN-OUTPUT` | Output inclusion | `RUN-OUTPUT on-error` |
| `RUN-OUTPUT-LIMIT` | Max output chars | `RUN-OUTPUT-LIMIT 10K` |
| `RUN-TIMEOUT` | Command timeout | `RUN-TIMEOUT 2m` |
| `RUN-CWD` | Working directory | `RUN-CWD ./backend` |
| `RUN-ENV` | Environment variable | `RUN-ENV API_KEY=secret` |
| `ALLOW-SHELL` | Enable shell features | `ALLOW-SHELL true` |
| `ON-FAILURE` | Block on RUN failure | `ON-FAILURE` ... `END` |
| `ON-SUCCESS` | Block on RUN success | `ON-SUCCESS` ... `END` |

## Control Flow

| Directive | Purpose | Example |
|-----------|---------|---------|
| `PAUSE` | Checkpoint and exit | `PAUSE Review findings` |
| `CONSULT` | Pause for human consultation | `CONSULT Design Decisions` |
| `CONSULT-TIMEOUT` | Set CONSULT expiration | `CONSULT-TIMEOUT 1h` |
| `ELIDE` | Merge adjacent elements | `ELIDE` |
| `COMPACT` | Trigger compaction | `COMPACT` |
| `REQUIRE` | Pre-flight checks | `REQUIRE @file.py cmd:git` |
| `END` | End ON-FAILURE/ON-SUCCESS | `END` |

## Output Directives

| Directive | Purpose | Example |
|-----------|---------|---------|
| `OUTPUT-FORMAT` | Output format | `OUTPUT-FORMAT markdown` |
| `OUTPUT-FILE` | Output destination | `OUTPUT-FILE report.md` |

See `sdqctl help workflow` for full ConversationFile examples.
""",

    "adapters": """
# AI Adapters

sdqctl supports multiple AI providers through adapters.

## Available Adapters

| Adapter | Package | Description |
|---------|---------|-------------|
| `mock` | Built-in | Testing adapter (no AI calls) |
| `copilot` | github-copilot-sdk | GitHub Copilot CLI |
| `claude` | anthropic | Anthropic Claude |
| `openai` | openai | OpenAI GPT models |

## Specifying Adapters

In ConversationFile:
```dockerfile
ADAPTER copilot
MODEL gpt-4
```

Via CLI:
```bash
sdqctl run workflow.conv --adapter copilot
```

## Checking Adapter Status

```bash
sdqctl status --adapters
```

## Mock Adapter

The `mock` adapter is useful for testing workflow mechanics without AI calls:

```bash
sdqctl run workflow.conv --adapter mock --verbose
```

Returns canned responses, allowing you to test:
- Workflow parsing and execution
- Checkpointing behavior
- Output file handling
""",

    "workflow": """
# ConversationFile Workflow Format

ConversationFiles (`.conv`) are declarative workflow definitions.

## Basic Structure

```dockerfile
# workflow.conv
MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 1

# Include context files
CONTEXT @lib/auth/*.js
CONTEXT @tests/auth.test.js

# Context management
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

# Prompts (run in sequence)
PROMPT Analyze authentication for security vulnerabilities.
PROMPT Generate a report with severity ratings.

# Output configuration
OUTPUT-FORMAT markdown
OUTPUT-FILE security-report.md
```

## Template Variables

Available in prompts and output paths:

| Variable | Example |
|----------|---------|
| `{{DATE}}` | 2026-01-21 |
| `{{DATETIME}}` | 2026-01-21T12:00:00 |
| `{{CYCLE_NUMBER}}` | 2 |
| `{{COMPONENT_NAME}}` | auth |
| `{{GIT_BRANCH}}` | main |

## Multi-Cycle Workflow

```dockerfile
MODEL gpt-4
MAX-CYCLES 3

PROLOGUE Iteration {{CYCLE_NUMBER}}/{{CYCLE_TOTAL}}
PROMPT Refine the implementation.
EPILOGUE Checkpoint progress.
```

## Human-in-the-Loop

```dockerfile
PROMPT Analyze security issues.
PAUSE "Review findings before remediation"
PROMPT Generate remediation plan.
```

Resume with: `sdqctl resume --list`

## Running Workflows

```bash
sdqctl run workflow.conv              # Single execution
sdqctl cycle workflow.conv -n 5       # Multi-cycle
sdqctl apply workflow.conv --components "lib/*.js"  # Apply to files
```
""",

    "variables": """
# Template Variables

Template variables are expanded in prompts, context, and output paths.

## Date/Time Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{DATE}}` | ISO date | 2026-01-21 |
| `{{DATETIME}}` | ISO datetime | 2026-01-21T12:00:00 |

## Workflow Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{WORKFLOW_NAME}}` | Workflow filename | security-audit |
| `{{WORKFLOW_PATH}}` | Full workflow path | /path/to/audit.conv |

## Component Variables (apply command)

| Variable | Description | Example |
|----------|-------------|---------|
| `{{COMPONENT_NAME}}` | Component name | auth |
| `{{COMPONENT_PATH}}` | Component path | /path/to/auth.py |
| `{{COMPONENT_DIR}}` | Parent directory | /path/to |
| `{{COMPONENT_TYPE}}` | Discovery type | plugin |

## Iteration Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ITERATION_INDEX}}` | Current iteration | 3 |
| `{{ITERATION_TOTAL}}` | Total iterations | 15 |
| `{{CYCLE_NUMBER}}` | Current cycle | 2 |
| `{{CYCLE_TOTAL}}` | Total cycles | 5 |

## Git Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{GIT_BRANCH}}` | Current branch | main |
| `{{GIT_COMMIT}}` | Short commit SHA | abc1234 |

## System Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{CWD}}` | Current directory | /home/user/project |
| `{{STOP_FILE}}` | Stop signal filename | STOPAUTOMATION-a1b2c3.json |
""",

    "context": """
# Context Management

sdqctl manages AI context windows automatically.

## Including Context Files

```dockerfile
# Single file
CONTEXT @lib/auth.js

# Glob pattern
CONTEXT @lib/**/*.js

# Optional (won't fail if missing)
CONTEXT-OPTIONAL @lib/legacy/*.js

# Exclude patterns
CONTEXT-EXCLUDE @node_modules/**
```

## Context Limits

```dockerfile
# Trigger action at 80% capacity
CONTEXT-LIMIT 80%

# Actions when limit reached
ON-CONTEXT-LIMIT compact    # Summarize and continue
ON-CONTEXT-LIMIT stop       # Stop and checkpoint
```

## Session Modes (cycle command)

```bash
sdqctl cycle workflow.conv --session-mode accumulate  # Grow context
sdqctl cycle workflow.conv --session-mode compact     # Summarize per cycle
sdqctl cycle workflow.conv --session-mode fresh       # Reset per cycle
```

## Compaction

```dockerfile
# Explicit compaction
COMPACT

# Preserve important content
COMPACT-PRESERVE @lib/core.js

# Add context before/after summary
COMPACT-PROLOGUE Previous context summary:
COMPACT-EPILOGUE Continue with the summarized context above.
```
""",

    "examples": """
# Workflow Examples

## Security Audit

```dockerfile
# security-audit.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

CONTEXT @lib/auth/*.js
CONTEXT @lib/crypto/*.js

PROMPT Analyze for security vulnerabilities.
PROMPT Focus on: authentication, input validation, encryption.
PROMPT Generate severity-rated findings.

OUTPUT-FILE security-report.md
```

## Test-Fix Loop

```dockerfile
# test-fix.conv
MODEL gpt-4
MAX-CYCLES 3

RUN pytest tests/
RUN-RETRY 2 "Analyze test failures and fix the code"

PROMPT Summarize fixes made this cycle.

CHECKPOINT-AFTER each-cycle
```

## Conditional Branching on RUN Result

```dockerfile
# deploy-with-fallback.conv
MODEL gpt-4

RUN npm test
ON-FAILURE
PROMPT Analyze test failures.
RUN git diff
PROMPT Fix the failing tests based on the diff.
END
ON-SUCCESS
PROMPT All tests passed! Deploy to staging.
RUN npm run deploy:staging
END

PROMPT Continue with next steps.
```

## Multi-Component Migration

```dockerfile
# migration.conv
MODEL gpt-4

PROLOGUE Component: {{COMPONENT_NAME}}
CONTEXT @{{COMPONENT_PATH}}

PROMPT Migrate this component to TypeScript.
PROMPT Update imports and add type annotations.

EPILOGUE Update progress.md with migration status.
OUTPUT-FILE reports/{{COMPONENT_NAME}}.md
```

Run with:
```bash
sdqctl apply migration.conv --components "lib/*.js" --progress progress.md
```

## Human Review Workflow

```dockerfile
# review-workflow.conv
MODEL gpt-4

PROMPT Analyze codebase for issues.
PAUSE "Review findings before proceeding"

PROMPT Generate remediation plan.
PAUSE "Approve remediation plan"

PROMPT Implement approved changes.
```

## Human Consultation Workflow

```dockerfile
# consultation-workflow.conv
MODEL gpt-4
SESSION-NAME feature-design
CONSULT-TIMEOUT 2h

PROMPT Analyze this proposal and identify open questions.
  Add questions to the document's "## Open Questions" section.
CONSULT "Design Decisions"

PROMPT Now that the design decisions are resolved,
  update the proposal with the decisions and create tasks.
```

The CONSULT directive pauses like PAUSE, but when the human resumes
with `sdqctl sessions resume SESSION` (or `copilot --resume SESSION`),
the agent proactively presents open questions and guides the human
through answering them.

Use `CONSULT-TIMEOUT` to set an expiration (e.g., `1h`, `30m`, `7d`).
If the human doesn't resume before the timeout, the session expires
with a clear error message.
""",

    "validation": """
# Validation and Verification Workflow

sdqctl provides static verification commands that run **without AI calls**.

## Command Pipeline

```
validate → verify → render → run/cycle
(syntax)   (refs)   (preview)  (execute)
```

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `validate` | Check .conv syntax | `sdqctl validate workflow.conv` |
| `verify refs` | Check @-references | `sdqctl verify refs` |
| `verify links` | Check markdown links | `sdqctl verify links` |
| `verify traceability` | Check STPA traces | `sdqctl verify traceability` |
| `verify terminology` | Check term consistency | `sdqctl verify terminology` |
| `verify assertions` | Check assertion docs | `sdqctl verify assertions` |
| `verify all` | Run all verifiers | `sdqctl verify all --json` |
| `show` | Display parsed structure | `sdqctl show workflow.conv` |
| `render` | Preview prompts | `sdqctl render run workflow.conv` |
| `refcat` | Extract file content | `sdqctl refcat @file.py#L10-L50` |

## Decision Tree

- **Syntax/parse issues?** → `sdqctl validate`
- **Broken references?** → `sdqctl verify refs`
- **Broken links?** → `sdqctl verify links`
- **Missing traces?** → `sdqctl verify traceability`
- **Terminology issues?** → `sdqctl verify terminology`
- **Assertion docs?** → `sdqctl verify assertions`
- **See parsed structure?** → `sdqctl show`
- **Preview prompts?** → `sdqctl render run`
- **Extract file lines?** → `sdqctl refcat`

## VERIFY Directive

Run verification during workflow execution:

```dockerfile
VERIFY refs
VERIFY-ON-ERROR continue
VERIFY-OUTPUT on-error
```

## CI/CD Pattern

```bash
# Validate all workflows
for f in workflows/*.conv; do
  sdqctl validate "$f" --json || exit 1
done

# Verify references
sdqctl verify refs --json
```

## refcat Syntax

```
@path/file.py              # Full file
@path/file.py#L10-L50      # Lines 10-50
@path/file.py#L10          # Single line
@path/file.py#L10-         # Line 10 to EOF
alias:path/file.py#L10     # Cross-repo alias
```

See `docs/VALIDATION-WORKFLOW.md` for comprehensive guide.
""",

    "ai": """
# Guidance for AI Workflow Authors

When authoring sdqctl workflows, follow these principles.

## 1. Context Window Mental Model

Think of conversation files as **describing how context windows fit over workflow steps**,
not as containers for detailed specifications.

The .conv file orchestrates the *flow* of work. Documentation files hold the *details*.

❌ **Anti-pattern**: Embedding specifications in the .conv file
```dockerfile
PROMPT ## Phase 1: Implement Feature X
  The feature should:
  - Support format A with fields x, y, z
  - Handle error cases: E1, E2, E3
  - Follow pattern from lib/similar.py lines 45-120
  ... 50 more lines of spec ...
```

✅ **Pattern**: Reference documentation deliverables
```dockerfile
# Small, critical file - OK to inject
CONTEXT @proposals/FEATURE-X.md

# Let agent read details on demand
PROMPT Implement Feature X according to the design in proposals/FEATURE-X.md
```

## 2. Documentation Reading Order

**For workflow authoring:**
1. `sdqctl help workflow` - Basic structure
2. `sdqctl help directives` - All directives
3. `sdqctl help examples` - Common patterns

**For advanced patterns:**
- `docs/SYNTHESIS-CYCLES.md` - Iterative refinement workflows
- `docs/CONTEXT-MANAGEMENT.md` - Token efficiency strategies
- `docs/QUIRKS.md` - Surprising behaviors to avoid
- `docs/WORKFLOW-DESIGN.md` - Deep dive on conversation file design

## 3. Key Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Hint, don't inject** | Agent reads files on demand, saving tokens |
| **Name for action** | Filename influences agent role (use verbs) |
| **Specs in docs** | Put details in .md files, reference from .conv |
| **ELIDE for efficiency** | Merge RUN output with prompts in one turn |
| **Fresh mode for edits** | Agent sees file changes between cycles |
| **COMPACT between phases** | Free context before synthesis |

## 4. Workflow Structure Template

```dockerfile
# [action-verb]-[noun].conv - Brief description
MODEL gpt-4
ADAPTER copilot
MODE implement    # or: audit, read-only
MAX-CYCLES 3

# Role clarification (prevents passive interpretation)
PROLOGUE You are an implementation assistant. Edit files directly.
PROLOGUE Session: {{DATE}} | Branch: {{GIT_BRANCH}}

# Small critical context only
CONTEXT @proposals/DESIGN.md

# Cycle 1: Analyze
PROMPT Review the design and select one task to implement.

# Cycle 2: Implement
PROMPT Implement the selected task. Run tests to verify.

COMPACT

# Cycle 3: Document
PROMPT Summarize changes and update docs.

OUTPUT-FILE reports/{{DATE}}-progress.md
```

## 5. Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `CONTEXT @lib/**/*.py` | Hint at paths, let agent read |
| Naming file `tracker.conv` | Use `implement-fixes.conv` |
| 50-line PROMPT blocks | Move specs to .md files |
| No COMPACT in long workflows | Add between phases |
| Hardcoded commit messages | Let agent write them |

## 6. Getting Templates

```bash
# Show workflow examples
sdqctl help examples

# Render existing workflow as template
sdqctl render run examples/workflows/security-audit.conv

# Preview what would be sent to AI
sdqctl render cycle workflow.conv -n 3
```

See also: `sdqctl help workflow`, `docs/GETTING-STARTED.md`
""",

    # Ecosystem-specific topics for Nightscout and AID systems
    "gap-ids": """
# Gap ID Taxonomy

Gap IDs track alignment issues between AID projects and Nightscout.

## Format

```
GAP-{CATEGORY}-{NUMBER}
```

## Categories

| Prefix | Domain | Example |
|--------|--------|---------|
| `GAP-CGM-` | CGM data handling | GAP-CGM-001 timestamp normalization |
| `GAP-TREAT-` | Treatment records | GAP-TREAT-002 bolus wizard mapping |
| `GAP-SYNC-` | Data synchronization | GAP-SYNC-003 upload retry logic |
| `GAP-PROF-` | Profile management | GAP-PROF-001 basal schedule format |
| `GAP-LOOP-` | Loop algorithm data | GAP-LOOP-004 IOB calculation diff |
| `GAP-UI-` | User interface | GAP-UI-001 glucose unit display |
| `GAP-SEC-` | Security concerns | GAP-SEC-002 token handling |
| `GAP-API-` | API compatibility | GAP-API-001 endpoint versioning |

## States

| State | Meaning |
|-------|---------|
| `open` | Identified, not yet addressed |
| `in-progress` | Being worked on |
| `resolved` | Fix implemented |
| `wontfix` | Intentional difference |
| `deferred` | Postponed to future version |

## Usage

When identifying issues:
```
GAP-CGM-005: Loop uses mg/dL internally, AAPS uses mmol/L
  Status: open
  Severity: medium
  Projects: Loop, AAPS
  Impact: Display mismatch in Nightscout
```
""",

    "5-facet": """
# 5-Facet Documentation Pattern

Comprehensive documentation structure for cross-project alignment.

## Facets

### 1. Terminology
Definitions, synonyms, and cross-project mappings.

```markdown
| Term | Loop | AAPS | Nightscout | Definition |
|------|------|------|------------|------------|
| IOB | insulinOnBoard | iob | iob | Insulin remaining active |
```

### 2. Behaviors
Functional behavior descriptions with acceptance criteria.

```markdown
## Behavior: Glucose Display
- Input: CGM reading
- Process: Convert to user-preferred units
- Output: Formatted value with trend arrow
- Verify: `verify trace REQ-001 -> TEST-001`
```

### 3. Traceability
Links between requirements, specs, tests, and code.

```markdown
REQ-001 → SPEC-001 → TEST-001 → Loop/Sources/CGM.swift#L42
```

### 4. Gaps
Alignment issues with severity and remediation.

```markdown
GAP-CGM-001: Timestamp format mismatch
  Severity: high
  Loop: ISO 8601 with milliseconds
  AAPS: Unix epoch seconds
  Resolution: Normalize in upload adapter
```

### 5. Safety (STPA)
Hazard analysis for safety-critical functionality.

```markdown
LOSS-001: Incorrect insulin delivery
HAZ-001: Stale glucose data used for dosing
UCA-001: Bolus calculated with >15min old data
SC-001: Reject CGM readings older than 5 minutes
```

## Integration

```bash
# Verify all 5 facets are documented
sdqctl verify coverage "overall >= 80"
```
""",

    "stpa": """
# STPA Hazard Analysis

System-Theoretic Process Analysis for safety-critical AID systems.

## Artifact Hierarchy

```
LOSS → HAZ → UCA → SC
```

| Artifact | Purpose | Example |
|----------|---------|---------|
| `LOSS-XXX` | Unacceptable outcome | LOSS-001 Hypoglycemia |
| `HAZ-XXX` | System state leading to loss | HAZ-001 Overdose of insulin |
| `UCA-XXX` | Unsafe Control Action | UCA-001 Bolus when BG < 70 |
| `SC-XXX` | Safety Constraint | SC-001 Block bolus if BG < 80 |

## Creating Entries

### LOSS (Loss Scenario)
```markdown
LOSS-001: Severe hypoglycemia requiring assistance
  Severity: critical
  Category: health
```

### HAZ (Hazard)
```markdown
HAZ-001: Excessive insulin delivery
  Links: LOSS-001
  System: Insulin dosing
```

### UCA (Unsafe Control Action)
```markdown
UCA-001: Automated bolus when glucose falling rapidly
  Links: HAZ-001
  Control: Bolus command
  Context: Glucose trend > -2 mg/dL/min
  Type: provided-causes-hazard
```

### SC (Safety Constraint)
```markdown
SC-001: Suspend automated delivery when trend > -3 mg/dL/min
  Links: UCA-001
  Implementation: Loop/SafetyManager.swift#L45
```

## Verification

```bash
# Check STPA traceability
sdqctl verify traceability

# Verify specific link
sdqctl verify trace UCA-001 SC-001
```
""",

    "conformance": """
# Conformance Testing

Structured test scenarios for cross-project compatibility.

## Scenario Format

```yaml
Scenario: CGM upload with missing values
  Given: CGM reading with null trend
  When: Upload to Nightscout
  Then: Entry created with trend = "NOT_COMPUTABLE"
  Projects: [Loop, AAPS, xDrip+]
  Traces: [REQ-CGM-005, SPEC-CGM-005]
```

## Categories

| Category | Tests | Example |
|----------|-------|---------|
| `CONF-CGM-` | CGM data handling | CONF-CGM-001 trend arrow mapping |
| `CONF-TREAT-` | Treatment upload | CONF-TREAT-002 bolus wizard fields |
| `CONF-PROF-` | Profile sync | CONF-PROF-001 basal schedule format |
| `CONF-API-` | API compatibility | CONF-API-001 v3 entry creation |

## Writing Tests

### Input Specification
```yaml
Input:
  source: Loop
  type: sgv
  value: 120
  direction: "FortyFiveUp"
  date: "2026-01-27T10:30:00Z"
```

### Expected Output
```yaml
Expected:
  nightscout:
    sgv: 120
    direction: "FortyFiveUp"
    dateString: "2026-01-27T10:30:00.000Z"
```

### Verification
```yaml
Verify:
  - Field mapping correct
  - Date format normalized
  - Optional fields handled
```

## Running Conformance Tests

```bash
# Run all conformance tests
sdqctl verify conformance

# Run specific category
sdqctl verify conformance --category CGM
```
""",

    "nightscout": """
# Nightscout Ecosystem

Overview of the Nightscout project and related AID systems.

## Core Projects

| Project | Language | Purpose |
|---------|----------|---------|
| **cgm-remote-monitor** | JavaScript | Web-based glucose monitoring |
| **Loop** | Swift | iOS automated insulin delivery |
| **AAPS** | Kotlin | Android automated insulin delivery |
| **xDrip+** | Java | Android CGM app |
| **Trio** | Swift | Fork of Loop with Oref1 algorithm |

## Data Flow

```
CGM Device → AID App → Nightscout → Caregivers/Reports
```

## API Versions

| Version | Status | Key Features |
|---------|--------|--------------|
| v1 | Legacy | Basic entries, treatments |
| v2 | Current | Authorization, extended fields |
| v3 | Future | GraphQL, streaming |

## Entry Types

| Type | Field | Description |
|------|-------|-------------|
| `sgv` | Sensor glucose value | CGM readings |
| `mbg` | Meter blood glucose | Fingerstick readings |
| `treatments` | Various | Bolus, carbs, temp basal |
| `profile` | Object | Basal rates, ISF, CR |
| `devicestatus` | Object | Loop/AAPS algorithm state |

## Alignment Workflow

```bash
# Analyze a specific topic
sdqctl iterate analyze-cgm-handling.conv

# Check current alignment
sdqctl verify traceability --path docs/ecosystem/

# Identify gaps
sdqctl verify coverage "overall >= 80"
```

## Resources

- [Nightscout Docs](https://nightscout.github.io/)
- [Loop Docs](https://loopkit.github.io/loopdocs/)
- [AAPS Wiki](https://androidaps.readthedocs.io/)
- [OpenAPS Docs](https://openaps.readthedocs.io/)
"""
}
