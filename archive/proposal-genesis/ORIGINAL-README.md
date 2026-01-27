# copilot agent - A Proposal for Orchestrated AI-Assisted Development

## Overview

GitHub Copilot CLI has an incredibly rich interactive mode, but lacks a streamlined way to orchestrate the coding agent from the command line for automation, scripting, and CI/CD integration. This proposal introduces the `copilot agent` command suite that bridges the gap between interactive AI assistance and traditional CLI automation workflows.

**Vision:** `copilot agent apply` should work as a cross between Dockerfile, `git rebase`/`git bisect`, and `pandoc`—enabling declarative, reproducible, and scriptable AI-assisted development workflows.

## Real-World Evidence: The Problem Today

### Manual Orchestration Across Multiple Focused Contexts

Analysis of the [Nightscout cgm-remote-monitor](https://github.com/nightscout/cgm-remote-monitor) development workflow reveals a sophisticated pattern: **developers purposefully use multiple focused AI sessions for different components**, but must manually orchestrate transitions, checkpoints, and aggregation.

**Why Multiple Contexts Are Necessary:**

For a project with 6 major components requiring testing/auditing:
- **6 focused contexts** - One deep-dive session per component (bounded scope, better accuracy)
- **3 passes per component** - Work → Accuracy check → Tool-assisted verification
- **18 total work sessions** - Managing cognitive load across large domains
- **1+ summary sessions** - Aggregate findings from all 18 sessions

**Total: ~19+ purposeful, bounded contexts** that need orchestration.

**Git History Evidence** (from recent development sessions):

```
Session dd62849e-ed2a:
  20:11:29 - "Transitioned from Plan to Build mode"
             ↓ (manual intervention required)
  20:25:36 - "Introduce warning timeouts..." (intermediate checkpoint)
             ↓ (manual intervention required)
  20:26:32 - "Saved progress at the end of the loop"

Session a10b5171-2266:
  20:39:16 - "Transitioned from Plan to Build mode"
             ↓ (manual intervention required)
  20:51:09 - "Add test instrumentation..." (intermediate checkpoint)
             ↓ (manual intervention required)
  20:51:41 - "Saved progress at the end of the loop"

...this pattern repeats across 6+ sessions spanning multiple days
```

**The Manual Orchestration Process:**
1. **Manually** start session 1 for Component A (audit pass)
2. **Manually** transition through Plan → Build modes
3. **Manually** commit checkpoint "Saved progress at end of loop"
4. **Manually** start session 2 for Component A (accuracy pass)
5. **Manually** transition and checkpoint again
6. **Manually** start session 3 for Component A (verification pass)
7. **Repeat steps 1-6 for Components B, C, D, E, F** (18 total sessions)
8. **Manually** start session 19 to aggregate all findings
9. **Manually** copy/paste context between sessions

**Pain Points Identified:**
- **20+ manual commits** saying "Saved progress at the end of the loop"
- **Manual sequencing** across 18+ purposeful contexts
- **Manual mode transitions** within each session (Plan → Build)
- **Manual context aggregation** - no way to collect results automatically
- **Not reproducible** - can't re-run the same 19-session workflow
- **Not parallelizable** - must sequence sessions manually even when independent
- **Not scriptable** - can't integrate into CI/CD or automation

### How `copilot agent apply` and `copilot agent batch` Would Solve This

**The key insight:** Multiple contexts are CORRECT for managing cognitive load, but orchestration should be AUTOMATED.

#### Example 1: Single-Component Multi-Pass Workflow

```bash
# Automated 3-pass workflow for one component
copilot agent apply ./workflows/audit-websocket-component.copilot
```

```dockerfile
# workflows/audit-websocket-component.copilot
MODEL claude-sonnet-4.5
MODE audit
MAX-CYCLES 2

# Pass 1: Deep analysis
PROMPT Audit the WebSocket component for security, performance, and correctness issues
@lib/websocket/
@tests/websocket*.test.js

# Pass 2: Tool-assisted verification
RUN npm test -- websocket
PROMPT Analyze test results and identify gaps or failures
```

#### Example 2: Multi-Component Orchestration with Aggregation

```bash
# Orchestrate 18 focused sessions + 1 summary automatically
copilot agent batch \
  --parallel 3 \
  --format jsonl \
  workflows/audit-*.copilot \
  --output audit-results.jsonl

# Then aggregate findings
copilot agent apply "Summarize all audit findings" \
  --mode read-only \
  --input audit-results.jsonl \
  --output AUDIT-SUMMARY.md
```

```bash
# Directory structure
workflows/
├── audit-websocket.copilot      # Component 1 (3 passes internally)
├── audit-api-v3.copilot          # Component 2 (3 passes internally)
├── audit-authentication.copilot  # Component 3 (3 passes internally)
├── audit-data-pipeline.copilot   # Component 4 (3 passes internally)
├── audit-notifications.copilot   # Component 5 (3 passes internally)
└── audit-plugins.copilot         # Component 6 (3 passes internally)
```

Each `.copilot` file encodes the 3-pass pattern:
```dockerfile
# workflows/audit-websocket.copilot
MODEL claude-sonnet-4.5
MODE audit
MAX-CYCLES 2

# Pass 1: Work (audit the component)
CWD ./lib/websocket
ADD-DIR ./lib/websocket
ADD-DIR ./tests
PROMPT Audit WebSocket implementation for security and correctness
@lib/websocket/
@tests/

# Pass 2: Accuracy (verify findings with code review)
PROMPT Cross-reference findings with test coverage and documentation

# Pass 3: Tool-assisted verification (run tests)
RUN npm test -- websocket
PROMPT Document test gaps and quirks in structured format (JSON)
```

#### Example 3: Parallelized Multi-Component Testing

```bash
# Run 6 component test suites in parallel (each with 3 internal passes)
# Automatically aggregate results
copilot agent batch \
  --parallel 6 \
  workflows/test-*.copilot \
  --output test-results.jsonl

# Then summarize findings from all sessions
copilot agent apply "Summarize test findings and identify patterns" \
  --mode read-only \
  --input test-results.jsonl \
  --output TEST-SUMMARY.md

# Equivalent to running 18+ sessions, but automated
```

#### Example 4: Multi-Faceted Analysis (Real Pattern from Nightscout Ecosystem)

**Observed pattern from git history:** When auditing each subcomponent (Dexcom G6/G7, Libre CGM, xDrip+, oref0, etc.), the developer sequentially updates **5 different facets**:

```
Commit: "Add detailed documentation for Dexcom G6 and G7 Bluetooth protocols"
Files touched:
  - mapping/cross-project/terminology-matrix.md    (terminology facet)
  - traceability/requirements.md                   (requirements facet)  
  - traceability/gaps.md                           (gaps facet)
  - docs/.../dexcom-g6-g7-protocol-deep-dive.md   (deep dive facet)
  
Commit: "Update insulin curve models and associated documentation"
Files touched:
  - mapping/cross-project/terminology-matrix.md
  - traceability/requirements.md
  - traceability/gaps.md
  - docs/.../insulin-curve-models-deep-dive.md
```

**Manual process** (what's happening today):
- Audit Dexcom protocols → Update 5 files manually → Commit
- Audit Libre protocols → Update same 5 files manually → Commit
- Audit xDrip+ → Update same 5 files manually → Commit
- Repeat for 10+ subcomponents
- **No way to ensure consistency across facets**
- **No automation for faceted analysis**

**With ConversationFiles** (automated faceted analysis):

```bash
# Audit one subcomponent across all 5 facets
copilot agent apply ./workflows/audit-cgm-dexcom-g6.copilot

# Or audit all CGM subcomponents in parallel
copilot agent batch \
  --parallel 4 \
  workflows/audit-cgm-*.copilot
```

```dockerfile
# workflows/audit-cgm-dexcom-g6.copilot
MODEL claude-sonnet-4.5
MODE full
MAX-CYCLES 2

# Facet 1: Terminology mapping
PROMPT Analyze Dexcom G6 BLE protocol and update terminology matrix
@mapping/cross-project/terminology-matrix.md
@docs/research/dexcom-g6-protocol.md

# Facet 2: Gap identification  
PROMPT Identify implementation gaps for Dexcom G6 across AID systems
@traceability/gaps.md

# Facet 3: Requirements extraction
PROMPT Extract formal requirements for Dexcom G6 integration
@traceability/requirements.md

# Facet 4: Traceability verification
RUN make traceability
PROMPT Verify traceability matrices are updated for Dexcom G6
@traceability/assertion-trace.json
@traceability/coverage-analysis.json

# Facet 5: Progress tracking
PROMPT Update progress tracking for Dexcom G6 analysis completion
@progress.md
```

**Impact:** Analyzing 10 CGM subcomponents across 5 facets = 50 manual file updates becomes:

```bash
# One command, parallel execution, automated consistency
copilot agent batch --parallel 4 workflows/audit-cgm-*.copilot
# audit-cgm-dexcom-g6.copilot
# audit-cgm-dexcom-g7.copilot
# audit-cgm-libre-2.copilot
# audit-cgm-libre-3.copilot
# ... etc
```

**Benefits of This Approach:**
- ✅ **Purposeful context boundaries** - Each component gets focused session (cognitive load management)
- ✅ **Automated orchestration** - No manual session starting/sequencing
- ✅ **Automated checkpointing** - Tool manages transitions, not developer
- ✅ **Automated aggregation** - Results collected automatically across sessions
- ✅ **Parallelization** - Independent components run simultaneously
- ✅ **Reproducible** - Same workflow runs identically every time
- ✅ **Scriptable** - Can run in CI/CD, Makefiles, or automation
- ✅ **Version-controlled** - All 19 workflows tracked in git
- ✅ **Team-wide** - Anyone can run the same multi-session workflow

**Impact:** What required manually orchestrating 19+ sessions over multiple days becomes:
```bash
make audit  # One command, 18 parallel sessions + 1 summary
```

The multiple contexts remain (that's GOOD), but the orchestration becomes automated and reproducible.

## Motivation

### Current Limitations
- No way to automate Copilot interactions in scripts or CI/CD pipelines
- Cannot orchestrate multiple related tasks across different components
- Difficult to version control and share conversation patterns
- No support for iterative batch processing across codebases

### Desired Capabilities
- Run Copilot conversations from the command line non-interactively
- Define reusable conversation patterns in version-controlled files
- Orchestrate AI-assisted tasks across multiple directories/components
- Integrate Copilot into build systems, testing workflows, and automation scripts
- Create reproducible development workflows that can be shared across teams

## Proposal

This proposal introduces three complementary features:

### 1. ConversationFile Format (`.copilot` files)
A declarative file format (similar to Dockerfile) that encodes Copilot conversations using slash commands as keywords. These files enable:
- Version-controlled conversation patterns
- Reusable workflows across projects
- Team-wide standardization of AI-assisted tasks
- Composition and orchestration of complex workflows

### 2. Agent Command Suite (`copilot agent`)
A unified command structure for orchestrating AI workflows:
- `copilot agent plan` - Strategic planning (like `/plan`)
- `copilot agent apply` - Execute workflows declaratively (like `kubectl apply`)
- `copilot agent checkpoint` - Manage session checkpoints
- `copilot agent compact` - Trigger context compaction
- `copilot agent batch` - Execute multiple workflows in parallel

### 3. Context & Compaction Controls
Fine-grained control over context windows, compaction triggers, and continuation strategies for long-running workflows.

## Proposed Commands

### `copilot agent apply [options] <prompt|conversationfile>`
Apply a conversational workflow or ConversationFile non-interactively. Similar to `kubectl apply` - declarative, idempotent execution.

**Options:**
- `--max-cycles <n>` - Maximum conversation cycles to run (default: 1, use -1 for unlimited)
- `--interactive` - Drop into interactive mode after execution
- `--format <format>` - Input/output format: text, json, jsonl, markdown (default: text)
- `--output <file|->` - Write output to file or stdout (default: stdout)
- `--input <file|->` - Read additional input from file or stdin
- `--prologue <file|->` - Prepend additional context from file or stdin to prompt
- `--epilogue <file|->` - Append additional context from file or stdin to prompt
- `--header <file|->` - Prepend content to output (e.g., metadata, timestamp, disclaimer)
- `--footer <file|->` - Append content to output (e.g., citations, signature, links)
- `--continue-on-error` - Continue execution even if errors occur
- `--dry-run` - Show what would be done without executing
- `--mode <mode>` - Execution mode: full, read-only, docs-only, tests-only, audit (default: full)
- `--allow-path <pattern>` - Allow modifications only to files matching pattern (can be used multiple times)
- `--deny-path <pattern>` - Deny access to files matching pattern (can be used multiple times)
- `--deny-file <file>` - Deny access to specific file (can be used multiple times)

**Note:** Default of `--max-cycles=1` ensures predictable, bounded execution suitable for scripting and automation. Use higher values when iterative refinement is needed.

**Examples:**
```bash
# Execute a simple prompt (single cycle)
copilot agent apply "Add error handling to all API endpoints"

# Execute a ConversationFile
copilot agent apply ./workflows/audit-component.copilot

# Prologue and epilogue add context to the prompt
make verify-docs | copilot agent apply ./workflows/update-docs.copilot \
  --prologue "Current date: $(date)" \
  --epilogue -

# Read-only audit mode - analyze code but make no changes
copilot agent apply "Document all known bugs and quirks in the authentication module" \
  --mode read-only \
  --format markdown \
  --output docs/known-issues.md

# Documentation-only mode - can only modify docs
copilot agent apply "Update documentation to reflect recent API changes" \
  --mode docs-only \
  --yolo

# Tests-only mode - can only modify test files
copilot agent apply "Add missing test cases for edge conditions" \
  --mode tests-only \
  --yolo

# Audit mode - read code and generate reports, no modifications
copilot agent apply "Audit security vulnerabilities and document findings" \
  --mode audit \
  --output security-audit-$(date +%Y%m%d).md

# Fine-grained allow patterns - only specific directories
copilot agent apply "Refactor utility functions" \
  --allow-path "src/utils/**" \
  --allow-path "tests/utils/**" \
  --yolo

# Header and footer add content to the output
copilot agent apply "Generate API documentation" \
  --format markdown \
  --output api-docs.md \
  --header <(echo "# API Documentation\n_Generated on $(date)_\n") \
  --footer <(echo "\n---\n_This documentation was generated by GitHub Copilot CLI_")

# Add metadata header to JSON output
copilot agent apply "Audit security vulnerabilities" \
  --format json \
  --output security-report.json \
  --header <(jq -n --arg date "$(date -Iseconds)" '{generatedAt: $date, version: "1.0"}')

# JSON input/output for programmatic use
echo '{"prompt": "Fix the bug", "context": ["main.js"]}' | \
  copilot agent apply --format json --input - --output results.json

# Dry run to preview what would happen
copilot agent apply ./workflows/refactor.copilot --dry-run

# Allow iterative refinement for complex tasks
copilot agent apply "Refactor auth module" --max-cycles=5

# Protect critical files during automated refactoring
copilot agent apply "Refactor database layer" \
  --deny-file package.json \
  --deny-file .env \
  --deny-path "*.key" \
  --yolo

# Drop into interactive mode after execution
copilot agent apply ./MyConversation --interactive
```

### `copilot agent plan <conversationfile|prompt>`
Analyze a ConversationFile or prompt and output an execution plan without making any changes. Leverages the existing `/plan` slash command functionality. Similar to `--dry-run` but focused on strategic planning rather than tactical step preview.

**Purpose:**
- Preview what the conversation would accomplish
- Understand the scope before execution
- Review proposed changes and approach
- Generate implementation plans for complex tasks

**Options:**
- `--format <format>` - Output format: text, json, markdown (default: text)
- `--output <file|->` - Write plan to file or stdout
- `--header <file|->` - Prepend content to output
- `--footer <file|->` - Append content to output
- `--interactive` - Drop into interactive mode to refine the plan

**Difference from `--dry-run`:**
- `copilot agent plan` - High-level strategic plan: "What will be accomplished?"
- `copilot agent apply --dry-run` - Low-level tactical preview: "What specific actions will be taken?"

**Examples:**
```bash
# Preview what a conversation would accomplish
copilot agent plan ./workflows/refactor-auth.copilot

# Output as JSON for further processing
copilot agent plan ./workflows/update-tests.copilot --format json

# Plan from a prompt
copilot agent plan "Add authentication to the API"

# Generate markdown plan for review
copilot agent plan "Migrate to TypeScript" --format markdown --output migration-plan.md

# Add metadata to plan output
copilot agent plan "Modernize codebase" \
  --format markdown \
  --output modernization-plan.md \
  --header <(cat << EOF
---
title: Modernization Plan
author: GitHub Copilot
date: $(date +%Y-%m-%d)
status: draft
---

EOF
) \
  --footer <(echo -e "\n## Next Steps\n- Review this plan\n- Get team approval\n- Execute with \`copilot agent apply\`")

# Refine the plan interactively before execution
copilot agent plan ./workflows/big-refactor.copilot --interactive
```

### `copilot agent batch [options] <conversationfiles...>`
Execute multiple ConversationFiles in sequence or parallel, with support for batching and aggregation.

**Options:**
- `--parallel <n>` - Run up to n conversations in parallel
- `--max-cycles <n>` - Maximum cycles per conversation (default: 1)
- `--format <format>` - Output format: json, jsonl (default: jsonl)
- `--output <file|->` - Write results to file or stdout
- `--header <file|->` - Prepend content to output (applied once, before all results)
- `--footer <file|->` - Append content to output (applied once, after all results)
- `--stop-on-error` - Stop execution on first error

**Note:** When running multiple conversations (especially in parallel), `--max-cycles=1` is the default to ensure predictable resource usage, cost control, and prevent runaway conversations. Individual ConversationFiles can override this with the `MAX-CYCLES` keyword.

**Examples:**
```bash
# Process all conversation files sequentially (1 cycle each by default)
copilot agent batch workflows/*.copilot

# Run in parallel with JSONL output
copilot agent batch --parallel 4 --format jsonl plans/* | tee results.jsonl

# Allow more cycles for complex batch operations
copilot agent batch --max-cycles=3 --parallel 2 refactoring/*.copilot

# Verify results programmatically
copilot agent batch --format json plans/* --output results.json
jq '.[] | select(.status == "failed")' results.json

# Add summary header/footer to batch results
copilot agent batch --parallel 4 --format jsonl refactor/*.copilot \
  --output refactor-results.jsonl \
  --header <(echo "# Refactoring Batch - Started $(date)") \
  --footer <(echo "# Refactoring Batch - Completed $(date)")
```

### `copilot agent checkpoint [save|restore|list] [name]`
Manage session checkpoints for long-running workflows. Leverages the existing `/session checkpoints` functionality.

**Purpose:**
- Save workflow state at key milestones
- Restore to previous checkpoint if needed
- Enable iterative development with rollback capability
- Create audit trail of workflow progression

**Options:**
- `save <name>` - Save current state as a named checkpoint
- `restore <name>` - Restore to a previously saved checkpoint
- `list` - List all available checkpoints
- `--format <format>` - Output format for list: text, json (default: text)

**Examples:**
```bash
# Save checkpoint after major milestone
copilot agent checkpoint save "after-refactoring"

# List available checkpoints
copilot agent checkpoint list

# Restore to previous state
copilot agent checkpoint restore "before-breaking-change"

# List checkpoints as JSON
copilot agent checkpoint list --format json
```

### `copilot agent compact [--save-pointer]`
Manually trigger conversation context compaction. Uses the existing `/compact` functionality.

**Purpose:**
- Free up context window space for long-running workflows
- Prevent hitting context limits during complex operations
- Optionally save continuation pointer before compaction

**Options:**
- `--save-pointer` - Before compaction, inject a prompt summarizing next actionable areas (quine-like pointer)
- `--output <file>` - Save compacted summary to file for reference

**Examples:**
```bash
# Compact conversation history
copilot agent compact

# Compact with continuation pointer for multi-session workflows
copilot agent compact --save-pointer

# Save compaction summary for audit trail
copilot agent compact --output compact-summary-$(date +%Y%m%d-%H%M%S).md
```

## ConversationFile Format

ConversationFiles use slash commands as declarative keywords, similar to Dockerfile syntax.

**Default filename:** `.copilot` or `*.copilot`

**Example:** `audit-component.copilot`
```dockerfile
# Set the model for this conversation
MODEL claude-sonnet-4.5
MODE read-only  # Cannot modify any files, only read and analyze

# Change to component directory
CWD ./lib/components/auth

# Add relevant directories for access
ADD-DIR ./tests
ADD-DIR ./docs

# Set up the conversation context
PROMPT Let's evaluate tests and test specs for this component.

# Reference specific files (@ syntax matches interactive mode)
@tests/auth.test.js
@README.md

# Execute the main task
PROMPT Ensure all edge cases are covered and suggest improvements.

# Plan before executing
PLAN Review test coverage and identify gaps

# Final verification
PROMPT Document all findings and recommendations without making changes.
```

**Example:** `document-bugs.copilot`
```dockerfile
# Bug documentation workflow - read-only mode
MODEL claude-sonnet-4.5
MODE read-only
MAX-CYCLES 1

CWD ./src

PROMPT Analyze the codebase and document all known bugs, quirks, and edge cases.

PROMPT For each issue found, include:
1. File and line number
2. Description of the bug/quirk
3. Impact and severity
4. Potential workarounds
5. Suggested fix (but do not implement)

PROMPT Focus on authentication, error handling, and data validation modules.
```

**Example:** `update-docs.copilot`
```dockerfile
# Documentation update workflow - can only modify docs
MODEL claude-sonnet-4.5
MODE docs-only

# Can read code but only write to docs
ADD-DIR ./src
ADD-DIR ./docs

PROLOGUE Recent changes have been made to the API. The code is the source of truth.

# Include files in context
@src/api/**/*.js
@docs/*.md

PROMPT Update documentation to match current implementation.

PROMPT Ensure all examples are accurate and API signatures are correct.
```

**Example:** `test-improvements.copilot`
```dockerfile
# Test-only workflow - can only modify test files
MODEL claude-opus-4.5
MODE tests-only
MAX-CYCLES 3

ADD-DIR ./src
ADD-DIR ./tests

PROMPT Review code coverage and add missing tests for edge cases.

PROMPT Focus on:
- Error handling paths
- Boundary conditions
- Integration scenarios
- Performance edge cases

PROMPT Ensure test coverage reaches 85% or higher.
```

**Example:** `security-audit.copilot`
```dockerfile
# Security audit - no code changes, only documentation
MODEL claude-opus-4.5
MODE audit

ADD-DIR ./src
ADD-DIR ./lib
ADD-DIR ./config

PROMPT Perform a comprehensive security audit of the codebase.

PROMPT Check for:
- SQL injection vulnerabilities
- XSS vulnerabilities
- Authentication/authorization issues
- Secrets in code
- Insecure dependencies
- CSRF vulnerabilities

PROMPT Generate a detailed report with severity ratings and remediation recommendations.
```

**Example:** `refactor-utilities.copilot`
```dockerfile
# Scoped refactoring - only specific directories
MODEL claude-sonnet-4.5
MODE full

# Only allow changes to utility functions and their tests
ALLOW-PATH "src/utils/**"
ALLOW-PATH "tests/utils/**"

# Protect everything else
DENY-PATH "src/api/**"
DENY-PATH "src/core/**"

MAX-CYCLES 5

PROMPT Refactor utility functions to:
1. Use modern JavaScript features
2. Improve error handling
3. Add comprehensive JSDoc comments
4. Ensure all functions have tests

PROMPT Do not modify API or core business logic.
```
```dockerfile
# Component audit workflow
MODEL claude-opus-4.5
MAX-CYCLES 1
SESSION checkpoints 10

PROMPT For each component, ensure:
1. Complete test coverage
2. Up-to-date documentation
3. Security best practices
4. Performance considerations

PLAN Create implementation plan for improvements
```

**Example:** `generate-docs.copilot`
```dockerfile
# Documentation generation workflow
MODEL claude-sonnet-4.5
CWD ./src

# Build context from existing docs
PROLOGUE Current project structure:
CONTEXT @README.md
CONTEXT @ARCHITECTURE.md

# Main documentation task
PROMPT Generate comprehensive API documentation for all exported functions.

# Additional requirements
EPILOGUE Ensure all examples are tested and working.
EPILOGUE Follow our documentation style guide at @.github/DOCS_STYLE.md
```

**Usage with header/footer:**
```bash
copilot do ./conversations/generate-docs.copilot \
  --format markdown \
  --output docs/api.md \
  --header <(cat << 'EOF'
---
title: API Reference
version: 2.0
updated: $(date +%Y-%m-%d)
---

# API Reference

This documentation is automatically generated.

EOF
) \
  --footer <(echo -e "\n---\n\n*Last updated: $(date)*\n*Generated by: GitHub Copilot CLI*")
```
```dockerfile
# Complex refactoring that may need multiple iterations
MODEL claude-sonnet-4.5
MAX-CYCLES 5  # Allow up to 5 cycles for iterative refinement

# Context management for long-running workflow
MAX-CONTEXT-TOKENS 150000  # Trigger compaction before hitting limit
COMPACT-EVERY 50000        # Or compact every 50k tokens
BEFORE-COMPACT-PROMPT "Before compacting, list remaining TODOs and next actionable steps"
ON-CONTEXT-LIMIT-PROMPT "Summarize: (1) What was completed, (2) What remains, (3) Where to start next session"

PROMPT Refactor the authentication module to use modern async/await patterns.

PROMPT Ensure all tests pass after each change.

PROMPT Verify backward compatibility is maintained.
```

**Example:** `long-running-analysis.copilot`
```dockerfile
# Long-running analysis with checkpoint strategy
MODEL claude-opus-4.5
MAX-CYCLES 10
MODE audit

# Preserve checkpoints during compaction instead of summarizing
COMPACT-STRATEGY checkpoints

# Save checkpoint after each major component
PROMPT Analyze authentication component
@lib/auth/
CHECKPOINT "auth-analysis-complete"

PROMPT Analyze API layer
@lib/api/
CHECKPOINT "api-analysis-complete"

PROMPT Analyze data layer
@lib/data/
CHECKPOINT "data-analysis-complete"

# Quine-like pointer for continuation in next session
ON-CONTEXT-LIMIT-PROMPT "Document completed components and list remaining components to analyze in next session. Include: (1) Files reviewed, (2) Key findings, (3) Next component to start with, (4) Context needed from this session."
```

**Example:** `multi-session-refactoring.copilot`
```dockerfile
# Designed for multi-session execution with continuation
MODEL claude-sonnet-4.5
MAX-CYCLES 8
MODE full

# Context controls for continuation
MAX-CONTEXT-TOKENS 120000
BEFORE-COMPACT-PROMPT "Create a summary of: (1) Refactorings completed, (2) Tests passing/failing, (3) Next functions to refactor"

PROLOGUE This is a multi-session refactoring. Check for previous session summary in REFACTORING-PROGRESS.md

# Check if continuation file exists
@REFACTORING-PROGRESS.md

PROMPT Refactor utility functions to modern JavaScript patterns. Update REFACTORING-PROGRESS.md after each function is refactored.

# Before context limit, save pointer for next session
ON-CONTEXT-LIMIT-PROMPT "Update REFACTORING-PROGRESS.md with: (1) Functions completed this session, (2) Current test status, (3) Next function to refactor, (4) Any blockers or issues found."
```

### ConversationFile Keywords

Based on existing slash commands, ConversationFiles support:

**Core Configuration:**
- `MODEL <model-name>` - Set AI model (maps to `/model`)
- `MAX-CYCLES <n>` - Override default max cycles for this conversation (default: 1)
- `MODE <mode>` - Set execution mode: full, read-only, docs-only, tests-only, audit

**Context & Compaction Controls:**
- `MAX-CONTEXT-TOKENS <n>` - Auto-compact when approaching this limit (default: based on model)
- `COMPACT-EVERY <n>` - Auto-compact every N tokens
- `COMPACT-STRATEGY <strategy>` - How to compact: summary, checkpoints, preserve-plan (default: summary)
- `BEFORE-COMPACT-PROMPT <text>` - Prompt to inject before auto-compaction
- `ON-CONTEXT-LIMIT-PROMPT <text>` - Final prompt when max context reached (quine-like pointer)

**Directory & File Access:**
- `CWD <directory>` - Change working directory (maps to `/cd`)
- `ADD-DIR <directory>` - Add allowed directory (maps to `/add-dir`)
- `ALLOW-PATH <pattern>` - Allow modifications only to files matching pattern
- `DENY-FILE <file>` - Deny access to specific file (maps to `/deny-file`)
- `DENY-PATH <pattern>` - Deny access to files matching glob pattern (maps to `/deny-path`)

**File Inclusion:**
- `@<file-pattern>` - Include files in context (matches interactive `@` syntax)

**Workflow Control:**
- `PROLOGUE <text|file>` - Add content before main prompts
- `EPILOGUE <text|file>` - Add content after main prompts
- `PROMPT <text>` - Add a prompt/message
- `PLAN <description>` - Create implementation plan (maps to `/plan`)
- `RUN <command>` - Execute shell command (uses bash tool)
- `COMPACT` - Manually trigger compaction (maps to `/compact`)
- `CHECKPOINT <name>` - Save named checkpoint (maps to `/session checkpoints`)

**Advanced:**
- `DELEGATE <prompt>` - Delegate to remote PR (maps to `/delegate`)
- `AGENT <agent-name>` - Select custom agent (maps to `/agent`)
- `SKILLS <subcommand> [args]` - Manage skills (maps to `/skills`)
- `MCP <subcommand> [args]` - Configure MCP servers (maps to `/mcp`)

**Notes:** 
- `HEADER` and `FOOTER` are output-only and controlled via CLI flags, not ConversationFile keywords
- Comments start with `#` (Dockerfile-style)
- Keywords are case-insensitive but UPPERCASE is conventional

## Use Cases & Workflows

### 1. Component Auditing
```bash
# Audit all components systematically (read-only mode)
for component in ./lib/components/*; do
  copilot agent apply ./workflows/audit-component.copilot \
    --cwd "$component" \
    --mode read-only \
    --format json \
    >> audit-results.json
done
```

### 2. Documentation Synchronization
```bash
# Ensure documentation matches implementation (docs-only mode)
for component in ./lib/components/*; do
  component_name=$(basename "$component")
  copilot agent apply "Ensure there is accurate documentation for $component_name in @docs/" \
    --cwd "$component" \
    --mode docs-only \
    --yolo
done
```

### 3. Bug Documentation Workflow
```bash
# Document bugs and quirks without fixing them (read-only mode)
copilot agent apply ./workflows/document-bugs.copilot \
  --format markdown \
  --output docs/known-issues-$(date +%Y%m%d).md \
  --header <(cat << EOF
# Known Issues and Quirks
Generated: $(date)
Branch: $(git branch --show-current)

This document catalogs known bugs and quirks in the codebase.
**Note:** This is a documentation-only audit; no code changes were made.

---

EOF
)
```

### 3. Test Coverage Enforcement
```bash
# Verify and improve test coverage (tests-only mode)
copilot agent batch --parallel 4 --format jsonl test-plans/*.copilot | \
  jq -r 'select(.coverage < 80) | .component' | \
  while read component; do
    echo "Low coverage in $component, generating tests..."
    copilot agent apply "Improve test coverage to 80%" \
      --cwd "$component" \
      --mode tests-only \
      --yolo
  done
```

### 4. Pipeline with Plan/Execute Workflow
```bash
# First, generate plans for all components
for component in ./lib/components/*; do
  copilot agent plan "Audit security and performance" \
    --cwd "$component" \
    --format json \
    --output "plans/$(basename $component).json"
done

# Review plans, then execute approved ones
for plan in plans/*.json; do
  component=$(basename "$plan" .json)
  # Execute the conversation based on the plan
  copilot agent apply --format json --input "$plan" \
    --cwd "./lib/components/$component" \
    --output "results/$component.json"
done
```

### 5. CI/CD Integration
```bash
# In .github/workflows/ai-code-review.yml
- name: AI Code Review
  run: |
    copilot agent apply ./workflows/pr-review.copilot \
      --mode read-only \
      --format json \
      --output review-results.json \
      --share-gist
    
    # Parse results and fail if issues found
    jq -e '.status == "success"' review-results.json
```

### 6. Iterative Refactoring
```bash
# Refactor with verification at each step, protecting critical files
copilot agent batch workflows/refactor-*.copilot \
  --deny-file Dockerfile \
  --deny-file docker-compose.yml \
  --deny-path ".github/workflows/*" \
  --format jsonl \
  --output refactor-results.jsonl \
  --stop-on-error

# Check all succeeded before running tests
if jq -e 'all(.status == "success")' refactor-results.jsonl; then
  npm test && \
    copilot agent apply "Verify all refactoring goals achieved" \
      --epilogue <(git diff) \
      --format markdown \
      --output refactor-summary.md
fi
```

### 7. Documentation Generation Pipeline
```bash
# Generate and verify documentation with proper formatting
make verify-docs | \
  copilot agent apply "Review build output and update docs accordingly" \
    --prologue "Build started: $(date)" \
    --epilogue - \
    --deny-path "config/production/*" \
    --deny-file .env.production \
    --format markdown \
    --output ./docs/ai-review-$(date +%Y%m%d).md \
    --header <(cat << EOF
# AI Documentation Review
Generated: $(date)
Project: $(git remote get-url origin)
Branch: $(git branch --show-current)

---

EOF
) \
    --footer <(cat << EOF

---

## Review Checklist
- [ ] All links are valid
- [ ] Code examples are tested
- [ ] Formatting is consistent

*Automated review by GitHub Copilot CLI*
EOF
)
```

### 9. Safe Automated Code Updates
```bash
# Update dependencies and code, but protect critical infrastructure
copilot do "Update all imports to use ES modules" \
  --deny-file package.json \
  --deny-file package-lock.json \
  --deny-file yarn.lock \
  --deny-file pnpm-lock.yaml \
  --deny-path ".github/*" \
  --deny-path "infrastructure/*" \
  --format json \
  --output migration-results.json \
  --yolo

# Analyze results
jq '.filesChanged, .summary' migration-results.json
```

### 10. Tool Chaining with JSON
```bash
# Chain multiple Copilot operations using JSON
copilot plan "Modernize codebase" --format json | \
  jq '.tasks[] | select(.priority == "high")' | \
  copilot do --format json --input - --output - | \
  jq '{completed: .filesChanged, remaining: .tasks | length}' | \
  tee progress.json
```

### 11. Automated Report Generation
```bash
# Generate weekly code quality report
copilot loop --parallel 3 --format json reports/*.copilot \
  --output weekly-report.json \
  --header <(cat << EOF
{
  "reportType": "weekly-quality",
  "generatedAt": "$(date -Iseconds)",
  "period": "$(date -d '7 days ago' +%Y-%m-%d) to $(date +%Y-%m-%d)",
  "results": [
EOF
) \
  --footer <(cat << EOF
  ],
  "summary": {
    "totalChecks": $(ls reports/*.copilot | wc -l),
    "generatedBy": "copilot-cli"
  }
}
EOF
)

# Convert to human-readable format
jq -r '.summary' weekly-report.json
```

## Benefits

### For Individual Developers
- **Reproducibility:** Save and reuse successful conversation patterns
- **Efficiency:** Automate repetitive AI-assisted tasks
- **Integration:** Combine Copilot with existing CLI workflows
- **Iteration:** Batch process multiple similar tasks
- **Safety:** Protect critical files during automated operations

### For Teams
- **Standardization:** Share conversation patterns across the team
- **Onboarding:** Provide new team members with proven workflows
- **Best Practices:** Encode organizational standards in ConversationFiles
- **Collaboration:** Version control AI-assisted development patterns
- **Guardrails:** Establish file protection policies in shared ConversationFiles

### For Organizations
- **CI/CD Integration:** Automate code quality checks and improvements
- **Consistency:** Ensure uniform application of coding standards
- **Scalability:** Process large codebases systematically
- **Auditability:** Track and review AI-assisted changes

## Implementation Considerations

### Backward Compatibility
- All existing `copilot` commands continue to work unchanged
- `--prompt` and `--interactive` flags remain the primary single-shot interfaces
- ConversationFiles are opt-in; traditional usage unaffected
- File denial follows same precedence model as existing `--deny-tool` and `--deny-url`

### Execution Model
- **Default cycles:** `--max-cycles=1` for predictable, atomic operations
  - Prevents runaway conversations in batch/parallel scenarios
  - Controls API usage and costs
  - Makes execution time predictable for CI/CD
  - Can be overridden per-command or per-ConversationFile
- **Streaming:** Supports both streaming and non-streaming modes
- **Permissions:** Respects all existing permission flags (`--allow-all`, `--yolo`, etc.)
- **Interactive transition:** Can drop into interactive mode with `--interactive` flag

**When to increase max-cycles:**
- Complex refactoring requiring iterative refinement (`--max-cycles=5`)
- Debug-fix-verify loops (`--max-cycles=3`)
- Exploratory analysis with follow-up questions (`--max-cycles=-1` for unlimited)
- Single-task `copilot do` invocations where iteration is expected

### Output Formats
- **text:** Human-readable output (default for `copilot do`)
- **json:** Structured output for programmatic consumption (single object)
- **jsonl:** Line-delimited JSON for streaming/batch processing (default for `copilot loop`)
- **markdown:** Formatted for documentation/sharing

**JSON Output Schema Example:**
```json
{
  "status": "success|failed|partial",
  "conversationId": "abc123",
  "cycles": 3,
  "filesChanged": ["src/auth.js", "tests/auth.test.js"],
  "summary": "Added error handling to authentication endpoints",
  "plan": {
    "tasks": [...],
    "estimatedComplexity": "medium"
  },
  "errors": [],
  "warnings": ["Coverage below 80% in auth.js"]
}
```

**JSONL Output Example (from `copilot loop`):**
```jsonl
{"file": "conv1.copilot", "status": "success", "filesChanged": 2, "duration": 12.3}
{"file": "conv2.copilot", "status": "failed", "error": "Permission denied", "duration": 3.1}
{"file": "conv3.copilot", "status": "success", "filesChanged": 5, "duration": 18.7}
```

### Error Handling
- Exit codes indicate success/failure for scripting
- `--continue-on-error` for batch processing
- `--dry-run` for safe preview
- Detailed error messages with context
- File access denials reported clearly with specific path/pattern that blocked access

## Related Work & Inspiration

- **Dockerfile:** Declarative, layered build instructions
- **git bisect/rebase:** Iterative, automated processing
- **pandoc:** Format conversion with extensible options
- **GitHub Actions:** YAML-based workflow automation
- **Make/Task runners:** Dependency-based execution

## Future Enhancements

- **Variables & Templating:** Parameterize ConversationFiles with `${VAR}` syntax
- **Conditionals:** Branch based on results (`IF`, `ELSE`, `ENDIF` keywords)
- **Composition:** Include/extend other ConversationFiles (`INCLUDE`, `EXTEND`)
- **Caching:** Reuse results from previous executions (content-addressed cache)
- **Parallel Execution:** Built-in parallelization primitives in ConversationFiles
- **Hooks:** Pre/post execution hooks for integration (`PRE-HOOK`, `POST-HOOK`)
- **File Allow Lists:** Complement deny patterns with explicit allow lists
- **Path Wildcarding:** Advanced glob patterns for fine-grained control
- **Interactive Deny:** Prompt for confirmation when accessing sensitive files
- **JSON Schema Validation:** Validate JSON input/output against schemas
- **Format Conversion:** `copilot convert` to transform between formats (like pandoc)
- **Watch Mode:** `copilot watch` to re-run conversations on file changes
- **Result Diffing:** Compare results across conversation runs

## Next Steps

1. **Community Feedback:** Gather input on proposed syntax and use cases
2. **Prototype:** Implement basic `copilot do` with ConversationFile support
3. **Documentation:** Create comprehensive guides and examples
4. **Integration:** Add CI/CD examples and templates
5. **Iteration:** Refine based on real-world usage

## Appendix

### Current `copilot --help` Output

For reference, the existing CLI interface:

```
Usage: copilot [options] [command]

GitHub Copilot CLI - An AI-powered coding assistant

Options:
  --add-dir <directory>               Add a directory to the allowed list for
                                      file access (can be used multiple times)
  --add-github-mcp-tool <tool>        Add a tool to enable for the GitHub MCP
                                      server instead of the default CLI subset
                                      (can be used multiple times). Use "*" for
                                      all tools.
  --add-github-mcp-toolset <toolset>  Add a toolset to enable for the GitHub MCP
                                      server instead of the default CLI subset
                                      (can be used multiple times). Use "all"
                                      for all toolsets.
  --additional-mcp-config <json>      Additional MCP servers configuration as
                                      JSON string or file path (prefix with @)
                                      (can be used multiple times; augments
                                      config from ~/.copilot/mcp-config.json for
                                      this session)
  --agent <agent>                     Specify a custom agent to use
  --allow-all                         Enable all permissions (equivalent to
                                      --allow-all-tools --allow-all-paths
                                      --allow-all-urls)
  --allow-all-paths                   Disable file path verification and allow
                                      access to any path
  --allow-all-tools                   Allow all tools to run automatically
                                      without confirmation; required for
                                      non-interactive mode (env:
                                      COPILOT_ALLOW_ALL)
  --allow-all-urls                    Allow access to all URLs without
                                      confirmation
  --allow-tool [tools...]             Tools the CLI has permission to use; will
                                      not prompt for permission
  --allow-url [urls...]               Allow access to specific URLs or domains
  --available-tools [tools...]        Only these tools will be available to the
                                      model
  --banner                            Show the startup banner
  --config-dir <directory>            Set the configuration directory (default:
                                      ~/.copilot)
  --continue                          Resume the most recent session
  --deny-tool [tools...]              Tools the CLI does not have permission to
                                      use; will not prompt for permission
  --deny-url [urls...]                Deny access to specific URLs or domains,
                                      takes precedence over --allow-url
  --disable-builtin-mcps              Disable all built-in MCP servers
                                      (currently: github-mcp-server)
  --disable-mcp-server <server-name>  Disable a specific MCP server (can be used
                                      multiple times)
  --disable-parallel-tools-execution  Disable parallel execution of tools (LLM
                                      can still make parallel tool calls, but
                                      they will be executed sequentially)
  --disallow-temp-dir                 Prevent automatic access to the system
                                      temporary directory
  --enable-all-github-mcp-tools       Enable all GitHub MCP server tools instead
                                      of the default CLI subset. Overrides
                                      --add-github-mcp-toolset and
                                      --add-github-mcp-tool options.
  --excluded-tools [tools...]         These tools will not be available to the
                                      model
  -h, --help                          display help for command
  -i, --interactive <prompt>          Start interactive mode and automatically
                                      execute this prompt
  --log-dir <directory>               Set log file directory (default:
                                      ~/.copilot/logs/)
  --log-level <level>                 Set the log level (choices: "none",
                                      "error", "warning", "info", "debug",
                                      "all", "default")
  --model <model>                     Set the AI model to use (choices:
                                      "claude-sonnet-4.5", "claude-haiku-4.5",
                                      "claude-opus-4.5", "claude-sonnet-4",
                                      "gpt-5.2-codex", "gpt-5.1-codex-max",
                                      "gpt-5.1-codex", "gpt-5.2", "gpt-5.1",
                                      "gpt-5", "gpt-5.1-codex-mini",
                                      "gpt-5-mini", "gpt-4.1",
                                      "gemini-3-pro-preview")
  --no-auto-update                    Disable downloading CLI update
                                      automatically
  --no-color                          Disable all color output
  --no-custom-instructions            Disable loading of custom instructions
                                      from AGENTS.md and related files
  -p, --prompt <text>                 Execute a prompt in non-interactive mode
                                      (exits after completion)
  --plain-diff                        Disable rich diff rendering (syntax
                                      highlighting via diff tool specified by
                                      git config)
  --resume [sessionId]                Resume from a previous session (optionally
                                      specify session ID)
  -s, --silent                        Output only the agent response (no stats),
                                      useful for scripting with -p
  --screen-reader                     Enable screen reader optimizations
  --share [path]                      Share session to markdown file after
                                      completion in non-interactive mode
                                      (default: ./copilot-session-<id>.md)
  --share-gist                        Share session to a secret GitHub gist
                                      after completion in non-interactive mode
  --stream <mode>                     Enable or disable streaming mode (choices:
                                      "on", "off")
  -v, --version                       show version information
  --yolo                              Enable all permissions (equivalent to
                                      --allow-all-tools --allow-all-paths
                                      --allow-all-urls)

Commands:
  help [topic]                        Display help information

Help Topics:
  config       Configuration Settings
  commands     Interactive Mode Commands
  environment  Environment Variables
  logging      Logging
  permissions  Permissions

Examples:
  # Start interactive mode
  $ copilot

  # Start interactive mode and automatically execute a prompt
  $ copilot -i "Fix the bug in main.js"

  # Execute a prompt in non-interactive mode (exits after completion)
  $ copilot -p "Fix the bug in main.js" --allow-all-tools

  # Enable all permissions with a single flag
  $ copilot -p "Fix the bug in main.js" --allow-all
  $ copilot -p "Fix the bug in main.js" --yolo

  # Start with a specific model
  $ copilot --model gpt-5

  # Resume the most recent session
  $ copilot --continue

  # Resume a previous session using session picker
  $ copilot --resume

  # Resume with auto-approval
  $ copilot --allow-all-tools --resume

  # Allow access to additional directory
  $ copilot --add-dir /home/user/projects

  # Allow multiple directories
  $ copilot --add-dir ~/workspace --add-dir /tmp

  # Disable path verification (allow access to any path)
  $ copilot --allow-all-paths

  # Allow all git commands except git push
  $ copilot --allow-tool 'shell(git:*)' --deny-tool 'shell(git push)'

  # Allow all file editing
  $ copilot --allow-tool 'write'

  # Allow all but one specific tool from MCP server with name "MyMCP"
  $ copilot --deny-tool 'MyMCP(denied_tool)' --allow-tool 'MyMCP'

  # Allow GitHub API access (defaults to HTTPS)
  $ copilot --allow-url github.com

  # Deny access to specific domain over HTTPS
  $ copilot --deny-url https://malicious-site.com
  $ copilot --deny-url malicious-site.com

  # Allow all URLs without confirmation
  $ copilot --allow-all-urls

```

## Execution Modes

The `--mode` flag enables lifecycle-specific workflows that align with different team roles and development phases:

### Mode: `full` (default)
- **Permissions:** Full read/write access (subject to allow/deny patterns)
- **Use cases:** General development, refactoring, feature implementation
- **Best for:** Individual developers working on features

### Mode: `read-only`
- **Permissions:** Can read all files, cannot modify anything
- **Tool restrictions:** `edit`, `create`, and file modification tools disabled
- **Use cases:** 
  - Code audits and security reviews
  - Bug and quirk documentation
  - Architecture analysis
  - Knowledge extraction
- **Best for:** Analysis phases, compliance reviews, onboarding documentation

### Mode: `docs-only`
- **Permissions:** Can only modify files in `docs/`, `*.md`, `README.*`
- **Read access:** Full codebase (to understand implementation)
- **Use cases:**
  - Documentation synchronization
  - API documentation generation
  - User guide updates
  - Keeping docs in sync with code
- **Best for:** Documentation specialists, technical writers

### Mode: `tests-only`
- **Permissions:** Can only modify files matching test patterns (`**/*.test.*`, `**/*.spec.*`, `tests/**`, `__tests__/**`)
- **Read access:** Full codebase (to understand what to test)
- **Use cases:**
  - Test coverage improvement
  - Test-driven development workflows
  - Adding edge case tests
  - Integration test creation
- **Best for:** QA engineers, test-driven development

### Mode: `audit`
- **Permissions:** Read-only with structured output requirements
- **Output:** Must produce structured reports (JSON/Markdown)
- **Use cases:**
  - Security audits
  - Performance analysis
  - Compliance checks
  - Code quality assessments
- **Best for:** Automated CI/CD checks, compliance teams

### Permission Precedence

When multiple permission mechanisms are combined:

1. **Mode** sets the base permissions
2. **--deny-path** and **--deny-file** further restrict access
3. **--allow-path** creates exceptions (only in `full` mode)

**Examples:**
```bash
# Read-only mode: deny patterns have no effect (already can't write)
copilot do --mode read-only --deny-file package.json  # deny is redundant

# Docs-only mode: can be further restricted
copilot do --mode docs-only --deny-path "docs/internal/*"  # OK

# Full mode: allow patterns create safe zones
copilot do --mode full --allow-path "src/utils/**" --yolo  # Only utils can change
```

## Team Workflow Patterns

### Separation of Concerns

Different team members can work on different aspects simultaneously:

```bash
# Developer: Feature implementation
copilot do "Add OAuth2 support" --mode full --allow-path "src/auth/**"

# QA Engineer: Test coverage
copilot do "Add OAuth2 tests" --mode tests-only

# Tech Writer: Documentation
copilot do "Document OAuth2 setup" --mode docs-only

# Security: Audit (no changes)
copilot do "Audit OAuth2 security" --mode audit --output security-report.md
```

### Phase-Based Workflows

Move through development phases with appropriate constraints:

```bash
# Phase 1: Analysis (read-only)
copilot do "Analyze authentication system" \
  --mode read-only \
  --output analysis.md

# Phase 2: Documentation (docs-only)
copilot do "Document current auth behavior" \
  --mode docs-only

# Phase 3: Implementation (scoped full access)
copilot do "Modernize auth system" \
  --mode full \
  --allow-path "src/auth/**" \
  --allow-path "tests/auth/**"

# Phase 4: Verification (tests-only)
copilot do "Add comprehensive auth tests" \
  --mode tests-only

# Phase 5: Final audit (read-only)
copilot do "Verify auth implementation" \
  --mode audit \
  --output final-audit.json
```

### Compliance and Governance

Enforce organizational policies through modes:

```bash
# Junior developers: Can only work on tests and docs
copilot do --mode tests-only ...
copilot do --mode docs-only ...

# Code reviews: Read-only with structured output
copilot do --mode audit --output review.json ...

# Production analysis: Absolutely no modifications
copilot do --mode read-only --format json ...
```

