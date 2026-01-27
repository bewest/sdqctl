# sdqctl Architecture

> **Purpose**: Technical reference for contributors. Covers module structure, data flow, and extension points.  
> **Last Updated**: 2026-01-27

---

## Overview

sdqctl is a vendor-agnostic CLI for orchestrating AI-assisted development workflows. The architecture follows a layered design:

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│   cli.py, commands/                                         │
├─────────────────────────────────────────────────────────────┤
│                     Core Layer                              │
│   conversation/, session.py, renderer.py, context.py        │
├─────────────────────────────────────────────────────────────┤
│                   Adapter Layer                             │
│   adapters/base.py, copilot.py, mock.py                     │
├─────────────────────────────────────────────────────────────┤
│                  Verifier Layer                             │
│   verifiers/base.py, refs.py, links.py, traceability.py     │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

### Package Layout

```
sdqctl/
├── __init__.py           # Package exports: ConversationFile, Session
├── cli.py                # Click CLI entrypoint (main command group)
│
├── core/                 # Core abstractions
│   ├── conversation/     # ConversationFile parsing (7 modules)
│   │   ├── __init__.py   # Re-exports for backward compatibility
│   │   ├── types.py      # DirectiveType enum, dataclasses
│   │   ├── parser.py     # parse_line() function
│   │   ├── applicator.py # apply_directive() functions
│   │   ├── templates.py  # Template variable substitution
│   │   ├── utilities.py  # Content resolution, builders
│   │   └── file.py       # ConversationFile class
│   ├── session.py        # Session, ExecutionContext
│   ├── renderer.py       # Prompt rendering, template expansion
│   ├── context.py        # ContextManager for file loading
│   ├── config.py         # Configuration loading (.sdqctl.yaml)
│   ├── models.py         # ModelRequirements, model selection
│   ├── refcat.py         # REFCAT line-level excerpts
│   ├── exceptions.py     # Custom exceptions with exit codes
│   ├── artifact_ids.py   # Artifact ID patterns and utilities (213 lines)
│   ├── help_commands.py  # Command help content (550 lines)
│   ├── help_topics.py    # Topic help content (623 lines)
│   ├── logging.py        # Logging configuration
│   ├── progress.py       # Progress tracking
│   └── loop_detector.py  # Infinite loop detection
│
├── adapters/             # AI provider adapters
│   ├── __init__.py       # Exports AdapterBase, get_adapter
│   ├── base.py           # AdapterBase, AdapterConfig, AdapterSession
│   ├── registry.py       # Adapter discovery and registration
│   ├── stats.py          # SessionStats, TurnStats, CompactionEvent
│   ├── events.py         # EventCollector, CopilotEventHandler, helpers
│   ├── copilot.py        # GitHub Copilot SDK adapter (670 lines)
│   └── mock.py           # Mock adapter for testing
│
├── commands/             # CLI command implementations
│   ├── __init__.py
│   ├── run.py            # Single-pass workflow execution
│   ├── iterate.py        # Multi-cycle execution with compaction
│   ├── apply.py          # Batch execution over components
│   ├── render.py         # Prompt rendering (dry-run)
│   ├── verify.py         # Verification CLI (532 lines, uses verify_output.py)
│   ├── verify_output.py  # Verification output helpers (114 lines)
│   ├── sessions.py       # Session management (list, resume)
│   ├── status.py         # Adapter status (auth, models)
│   ├── artifact.py       # Artifact ID CLI commands (500 lines, uses core/artifact_ids.py)
│   ├── refcat.py         # REFCAT extraction
│   ├── lsp.py            # LSP type lookup commands
│   ├── drift.py          # Drift detection commands
│   ├── flow.py           # Workflow parsing info
│   ├── help.py           # Help command (156 lines, uses core/help_*.py)
│   ├── blocks.py         # ON-FAILURE/ON-SUCCESS block execution
│   ├── elide.py          # Elision step processing
│   ├── compact_steps.py  # COMPACT/CHECKPOINT step handlers
│   ├── iterate_helpers.py # Session/compaction helpers, target parsing
│   ├── json_pipeline.py  # JSON pipeline handler (--from-json)
│   ├── output_steps.py   # Output writing and error handling
│   ├── prompt_steps.py   # Prompt building and loop detection
│   ├── run_steps.py      # RUN/RUN-ASYNC/RUN-WAIT step handlers
│   ├── verify_steps.py   # VERIFY/VERIFY-TRACE/VERIFY-COVERAGE handlers
│   ├── lsp_steps.py      # LSP directive step handler
│   └── utils.py          # Shared command utilities
│
├── lsp/                  # Language Server Protocol integration
│   └── __init__.py       # LSPClient, TypeDefinition, detect_language()
│
├── monitoring/           # Drift detection and change analysis
│   └── __init__.py       # ChangeDetector, GitChangeDetector, DriftReport
│
├── verifiers/            # Verification subsystem
│   ├── __init__.py       # Exports VERIFIERS registry, auto-registers plugins
│   ├── base.py           # VerifierBase, VerificationResult
│   ├── refs.py           # Reference verifier (@file checks)
│   ├── links.py          # Link verifier (URL checks)
│   ├── terminology.py    # Terminology consistency
│   ├── traceability.py   # Traceability matrix (571 lines)
│   ├── traceability_coverage.py  # Coverage calculation helpers (135 lines)
│   └── assertions.py     # Inline assertion checks
│
├── plugins.py            # Plugin discovery and registration
│                         # Loads .sdqctl/directives.yaml manifests
│
└── utils/                # Shared utilities
    ├── __init__.py
    ├── decorators.py     # @handle_io_errors, etc.
    └── output.py         # JSON output helpers
```

---

## Key Abstractions

### ConversationFile

The core workflow definition, parsed from `.conv` files:

```python
@dataclass
class ConversationFile:
    model: str              # AI model to use
    adapter: str            # Adapter name (copilot, mock)
    steps: list[ConversationStep]  # Ordered execution steps
    prologues: list[str]    # Content prepended to prompts
    epilogues: list[str]    # Content appended to prompts
    # ... many more fields
```

**Location**: `core/conversation/file.py`

### Session

Manages conversation state and checkpointing:

```python
@dataclass
class Session:
    id: str
    workflow_path: Path
    checkpoints: list[Checkpoint]
    outputs: list[str]
    # Methods: save_checkpoint(), restore_checkpoint()
```

**Location**: `core/session.py`

### ExecutionContext

Unified context for command execution:

```python
@dataclass
class ExecutionContext:
    adapter: AdapterBase
    adapter_config: AdapterConfig
    adapter_session: AdapterSession
    session: Session
    conv: ConversationFile
    verbosity: int
    console: Console
```

**Location**: `core/session.py`

### AdapterBase

Abstract base for AI provider adapters:

```python
class AdapterBase(ABC):
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def create_session(self, config: AdapterConfig) -> AdapterSession: ...
    @abstractmethod
    async def send(self, session: AdapterSession, prompt: str) -> str: ...
    async def compact(self, session, preserve, summary) -> CompactionResult: ...
    async def checkpoint(self, session, name) -> dict: ...
```

**Location**: `adapters/base.py`

### VerifierBase

Abstract base for verification checks:

```python
class VerifierBase(ABC):
    @abstractmethod
    def verify(self, root: Path, **options) -> VerificationResult: ...
```

**Location**: `verifiers/base.py`

---

## Data Flow

### Workflow Execution

```
                    ┌─────────────────┐
                    │   .conv File    │
                    └────────┬────────┘
                             │ parse
                             ▼
                    ┌─────────────────┐
                    │ ConversationFile│
                    └────────┬────────┘
                             │ render
                             ▼
                    ┌─────────────────┐
                    │ RenderedWorkflow│
                    │ (expanded prompts)
                    └────────┬────────┘
                             │ execute
                             ▼
                    ┌─────────────────┐
                    │ AdapterSession  │
                    │ (adapter.send())│
                    └────────┬────────┘
                             │ response
                             ▼
                    ┌─────────────────┐
                    │  Session Output │
                    │  (checkpoints)  │
                    └─────────────────┘
```

### Step Execution Loop

```python
# Simplified iterate.py flow
for cycle in range(max_cycles):
    for step in conv.steps:
        match step.type:
            case "prompt":
                response = await adapter.send(session, step.content)
            case "run":
                result = await execute_command(step.content)
            case "compact":
                await adapter.compact(session, step.preserve)
            case "checkpoint":
                session.save_checkpoint(step.content)
            case "verify":
                run_verification(step.verify_type)
```

---

## Extension Points

### 1. Adding Adapters

Create a new adapter in `adapters/`:

```python
# adapters/anthropic.py
from .base import AdapterBase, AdapterConfig, AdapterSession

class AnthropicAdapter(AdapterBase):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def create_session(self, config) -> AdapterSession: ...
    async def send(self, session, prompt) -> str: ...
```

Register in `adapters/registry.py`:

```python
ADAPTERS = {
    "copilot": "sdqctl.adapters.copilot:CopilotAdapter",
    "anthropic": "sdqctl.adapters.anthropic:AnthropicAdapter",
}
```

### 2. Adding Verifiers

Create a new verifier in `verifiers/`:

```python
# verifiers/security.py
from .base import VerifierBase, VerificationResult

class SecurityVerifier(VerifierBase):
    name = "security"
    
    def verify(self, root: Path, **options) -> VerificationResult:
        # Scan for security issues
        return VerificationResult(passed=True, issues=[])
```

Register in `verifiers/__init__.py`:

```python
VERIFIERS = {
    "refs": RefsVerifier,
    "links": LinksVerifier,
    "security": SecurityVerifier,  # New
}
```

### 2b. Adding Plugin Verifiers (External)

Create `.sdqctl/directives.yaml` in your workspace:

```yaml
version: 1
directives:
  VERIFY:
    my-check:
      handler: python tools/verify_mycheck.py
      description: "My custom verification"
      timeout: 60
```

Plugin verifiers are auto-discovered and registered at import time.
See `proposals/PLUGIN-SYSTEM.md` for the full specification.

### 3. Adding Directives

Add to `core/conversation/types.py`:

```python
class DirectiveType(Enum):
    # ... existing
    MY_DIRECTIVE = "MY-DIRECTIVE"
```

Handle in `core/conversation/applicator.py`:

```python
case DirectiveType.MY_DIRECTIVE:
    conv.my_field = directive.value
```

### 4. Adding Commands

Create in `commands/`:

```python
# commands/mycommand.py
import click

@click.command()
@click.argument("workflow")
def mycommand(workflow):
    """My custom command."""
    pass
```

Register in `cli.py`:

```python
from .commands.mycommand import mycommand
cli.add_command(mycommand)
```

---

## Configuration Hierarchy

Configuration is resolved in this order (later overrides earlier):

1. **Defaults** - Hardcoded in code
2. **Config file** - `.sdqctl.yaml` in project root
3. **Environment** - `SDQCTL_*` environment variables
4. **Workflow file** - Directives in `.conv` file
5. **CLI flags** - Command-line arguments

Example `.sdqctl.yaml`:

```yaml
adapter: copilot
model: gpt-4o
context_limit: 0.8
```

---

## Error Handling

Errors use typed exceptions with exit codes:

```python
# core/exceptions.py
class SDQCTLError(Exception):
    exit_code: int = 1

class MissingContextFiles(SDQCTLError):
    exit_code = 2

class AdapterError(SDQCTLError):
    exit_code = 3
```

JSON error output available via `--json-errors`:

```json
{
  "error": {
    "type": "MissingContextFiles",
    "message": "Missing mandatory context file: @missing.md",
    "exit_code": 2,
    "files": ["@missing.md"]
  }
}
```

---

## Testing Strategy

| Layer | Test Location | Approach |
|-------|--------------|----------|
| Core | `tests/test_conversation.py` | Unit tests for parsing |
| Adapters | `tests/test_adapters.py` | Mock adapter tests |
| Commands | `tests/test_*_command.py` | CLI integration tests |
| Verifiers | `tests/test_verifiers.py` | Verification logic tests |
| E2E | `test-loop-stress.sh` | Full workflow tests |

Run tests:

```bash
pytest                    # All tests
pytest tests/test_conversation.py  # Specific module
./test-loop-stress.sh     # Integration stress test
```

---

## See Also

- [GETTING-STARTED.md](GETTING-STARTED.md) - User quickstart
- [DIRECTIVE-REFERENCE.md](DIRECTIVE-REFERENCE.md) - Complete directive catalog
- [ADAPTERS.md](ADAPTERS.md) - Adapter implementation details
- [EXTENDING-VERIFIERS.md](EXTENDING-VERIFIERS.md) - Verifier extension guide
- [PLUGIN-AUTHORING.md](PLUGIN-AUTHORING.md) - External plugin development
- [CODE-QUALITY.md](CODE-QUALITY.md) - Code standards
