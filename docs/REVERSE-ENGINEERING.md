# Reverse Engineering: Code → Documentation

Reverse engineering workflows analyze existing code to generate documentation, extract implicit requirements, and understand architecture. This is the opposite direction of traceability — starting from code and working backwards.

---

## When to Reverse Engineer

- **Legacy codebases** with missing or outdated documentation
- **Onboarding** to understand an unfamiliar project
- **Documentation debt** where code evolved faster than docs
- **Architecture recovery** after team changes
- **Compliance** requiring documented requirements

---

## The Reverse Pipeline

```
Code  →  Documentation  →  Specifications  →  Requirements
  │           │                  │                 │
  └───────────┴──────────────────┴─────────────────┘
              Extracted from implementation
```

---

## Phase 1: Code Analysis

Start with `run` to understand structure:

```dockerfile
# code-analysis.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Analyze the codebase structure.
  
  Explore:
  - Directory organization
  - Key modules and their purposes
  - Entry points (main, CLI, API)
  - Dependencies and their roles
  
  Output a high-level architecture summary.
  Note files worth deeper analysis.

OUTPUT-FILE docs/architecture-overview.md
```

```bash
sdqctl iterate code-analysis.conv --adapter copilot
```

### Key Insight: Let the Agent Explore

Don't pre-load files with CONTEXT. The agent will:
1. List directories to understand structure
2. Read key files it identifies
3. Follow imports and references
4. Build understanding incrementally

---

## Phase 2: API Documentation

Generate docs from code:

```dockerfile
# api-docs-generator.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Generate API documentation for the public interfaces.
  
  Focus on:
  - Public functions and classes
  - Parameters and return types
  - Usage examples
  - Error conditions
  
  Key modules to document are in lib/ and sdqctl/.
  Reference the architecture overview in docs/architecture-overview.md.
  
  Format as markdown with code examples.

OUTPUT-FILE docs/API.md
```

---

## Phase 3: Architecture Extraction

Use `iterate` for deeper analysis:

```dockerfile
# architecture-extraction.conv
MODEL gpt-4
ADAPTER copilot
MODE audit
MAX-CYCLES 2

# Cycle 1: Component analysis
PROMPT Identify architectural components and their relationships.
  
  For each component:
  - Purpose and responsibility
  - Dependencies (what it uses)
  - Dependents (what uses it)
  - Key interfaces
  
  Start with the entry point and trace outward.

# Cycle 2: Generate diagram description
PROMPT Generate a component diagram description.
  
  Format as Mermaid syntax:
  ```mermaid
  graph TD
    A[Component A] --> B[Component B]
    B --> C[Component C]
  ```
  
  Include data flow arrows and labels.

OUTPUT-FILE docs/architecture-diagram.md
```

---

## Phase 4: Requirements Extraction

Extract implicit requirements from implementation:

```dockerfile
# requirements-extraction.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Extract implicit requirements from the implementation.
  
  Look for:
  - What the code validates (input requirements)
  - What the code produces (output requirements)
  - Error handling (reliability requirements)
  - Configuration options (flexibility requirements)
  - Performance considerations (non-functional requirements)
  
  The architecture overview is in docs/architecture-overview.md.
  
  Format as:
  | ID | Type | Implied Requirement | Evidence (file:line) |

OUTPUT-FILE requirements/extracted-requirements.md
```

---

## Real Example: Documenting sdqctl

### Step 1: Analyze Structure

```bash
sdqctl iterate code-analysis.conv --adapter copilot
```

The agent explores:
- `sdqctl/` directory structure
- `cli.py` entry point
- `core/` and `commands/` modules
- `adapters/` pattern

### Step 2: Generate Module Docs

```dockerfile
# sdqctl-module-docs.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Document the sdqctl core modules.
  
  Modules to cover:
  - sdqctl/core/conversation.py - ConversationFile parsing
  - sdqctl/core/context.py - Context management
  - sdqctl/core/session.py - Session handling
  
  For each module:
  - Purpose
  - Key classes/functions
  - Usage patterns
  - Integration points

OUTPUT-FILE docs/core-modules.md
```

### Step 3: Extract Design Decisions

```dockerfile
# design-decisions.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Identify design decisions evident in the implementation.
  
  Look for:
  - Why ConversationFile uses directive-based format (not YAML/JSON)?
  - Why adapters use async pattern?
  - Why context uses glob patterns?
  - Why checkpointing is file-based?
  
  Document each decision with:
  - The decision made
  - Evidence from code
  - Likely rationale
  - Trade-offs accepted

OUTPUT-FILE docs/design-decisions.md
```

---

## Real Example: Nightscout API

For the Nightscout CGM remote monitor:

```dockerfile
# nightscout-api-docs.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Generate API documentation for Nightscout endpoints.
  
  The API is in lib/api/.
  Swagger/OpenAPI definitions may be in swagger.yaml.
  
  For each endpoint:
  - HTTP method and path
  - Request parameters
  - Response format
  - Authentication requirements
  - Example usage

OUTPUT-FILE docs/nightscout-api.md
```

---

## Context-Light Strategies

### Let the Agent Navigate

❌ Pre-loading everything:
```dockerfile
CONTEXT @lib/**/*.py
CONTEXT @sdqctl/**/*.py
```

✅ Give hints, let agent explore:
```dockerfile
PROMPT Analyze the authentication module.
  Start with lib/auth/index.js and trace the authentication flow.
  Document what you find.
```

### Chunked Documentation

Instead of one massive doc generation:

```bash
# Generate in phases, each builds on previous
sdqctl iterate code-analysis.conv          # → architecture-overview.md
sdqctl iterate api-docs-generator.conv     # → API.md (references architecture)
sdqctl iterate design-decisions.conv       # → design-decisions.md
```

Each phase references previous outputs as context hints.

---

## Avoiding Context Bloat

### Problem: Large Codebases

Generating docs for a large codebase can exhaust context.

### Solution 1: Component-by-Component

Use `apply` to document each component separately:

```dockerfile
# component-doc.conv
PROMPT Document the component at {{COMPONENT_PATH}}.
  
  Include:
  - Purpose
  - Public API
  - Usage example
  - Dependencies

OUTPUT-FILE docs/components/{{COMPONENT_NAME}}.md
```

```bash
sdqctl apply component-doc.conv \
  --components "lib/plugins/*.js" \
  --output-dir docs/components/
```

### Solution 2: Iterative Deepening

Start broad, then zoom in:

1. **Broad survey** (run): High-level structure
2. **Module focus** (cycle): Detailed module docs
3. **Function detail** (apply): Per-function documentation

### Solution 3: Fresh Mode

Use `--session-mode fresh` so each cycle reads current file state:

```bash
sdqctl iterate doc-generator.conv -n 5 --session-mode fresh
```

---

## Output Templates

### Architecture Overview Template

```markdown
# Architecture Overview

## System Purpose
[High-level description]

## Component Structure
```
project/
├── lib/           # Core libraries
│   ├── auth/      # Authentication
│   └── api/       # API handlers
├── commands/      # CLI commands
└── tests/         # Test suites
```

## Key Components

### [Component Name]
- **Purpose**: [description]
- **Location**: [path]
- **Depends on**: [components]
- **Used by**: [components]

## Data Flow
[Mermaid diagram or description]

## Key Patterns
- [Pattern 1]: [where used]
- [Pattern 2]: [where used]
```

### API Documentation Template

```markdown
# API Reference

## [Module Name]

### `function_name(param1, param2)`

[Description]

**Parameters:**
- `param1` (type): Description
- `param2` (type): Description

**Returns:** type - Description

**Raises:**
- `ErrorType`: When condition

**Example:**
```python
result = function_name("value", 123)
```
```

---

## Verification

After generating documentation, verify accuracy:

```dockerfile
# verify-docs.conv
MODEL gpt-4
ADAPTER copilot
MODE audit

PROMPT Verify the generated documentation against the code.
  
  Check:
  1. docs/API.md - Are all public functions documented?
  2. docs/architecture-overview.md - Does it match actual structure?
  3. requirements/extracted-requirements.md - Are IDs unique and complete?
  
  Report discrepancies and missing items.

OUTPUT-FILE reports/doc-verification.md
```

---

## Next Steps

- **[Traceability Workflows](TRACEABILITY-WORKFLOW.md)** — Go forward: requirements → code
- **[Synthesis Cycles](SYNTHESIS-CYCLES.md)** — Self-improving iterations
- **[Getting Started](GETTING-STARTED.md)** — sdqctl basics

See `examples/workflows/test-discovery.conv` for code analysis patterns.
