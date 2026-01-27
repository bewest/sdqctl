# sdqctl: Software Defined Quality Control

## Executive Summary

`sdqctl` is a **vendor-agnostic CLI** for orchestrating AI-assisted development workflows with reproducible context management, compaction controls, and declarative workflow definitions.

**Key Insight:** The core value isn't tied to any specific AI provider—it's about **orchestrating conversations, context windows, and compaction in reproducible ways** across codebases and components.

---

## Why sdqctl?

### Current Gaps (From Feasibility Analysis)

| Need | Current State | sdqctl Solution |
|------|---------------|-----------------|
| Declarative workflows | ❌ Shell scripts only | ✅ ConversationFile format |
| Context/compaction controls | ⚠️ Manual `/compact` | ✅ Automatic policies |
| Batch/parallel execution | ❌ Sequential only | ✅ `sdqctl flow` |
| Named checkpoints | ⚠️ Session resume only | ✅ Explicit checkpointing |
| Multi-cycle iteration | ❌ Manual loops | ✅ `sdqctl cycle` |
| Vendor agnostic | ❌ Copilot-specific | ✅ Adapter pattern |

### Vendor Agnostic Design

```
sdqctl (orchestrator)
    │
    ├── adapters/
    │   ├── copilot.py      # github/copilot-sdk
    │   ├── claude.py       # anthropic SDK
    │   ├── openai.py       # openai SDK  
    │   └── ollama.py       # local models
    │
    └── core/
        ├── conversation.py  # ConversationFile parser
        ├── context.py       # Context window management
        ├── compaction.py    # Compaction policies
        └── checkpoint.py    # State management
```

---

## CLI Design

### Core Commands

```bash
# Single prompt execution
sdqctl run "Audit authentication module" [options]

# Multi-cycle iteration with compaction
sdqctl cycle workflow.conv --max-cycles 5

# Batch/parallel workflow execution  
sdqctl flow workflows/*.conv --parallel 4

# Apply workflow to components
sdqctl apply workflow.conv --components lib/plugins/*.js
```

### Full Command Reference

```
sdqctl - Software Defined Quality Control

COMMANDS:
  run       Execute single prompt with context
  cycle     Run multi-cycle workflow with compaction
  flow      Execute batch/parallel workflows
  apply     Apply workflow to multiple components
  
  init      Initialize sdqctl in project
  status    Show session/checkpoint status
  resume    Resume from checkpoint
  compact   Trigger context compaction
  
  adapter   Manage AI provider adapters
  config    Configuration management

OPTIONS:
  --adapter, -a     AI adapter to use (copilot, claude, openai, ollama)
  --model, -m       Model override
  --context, -c     Context file/directory to include
  --output, -o      Output file/directory
  --json            JSON output for scripting
  --verbose, -v     Verbose output
  --dry-run         Show what would happen
```

---

## ConversationFile Format (.conv)

A **declarative, Dockerfile-like format** for defining AI workflows:

```dockerfile
# workflow.conv - Audit authentication module

# Metadata
MODEL claude-sonnet-4.5
ADAPTER copilot
MODE audit
MAX-CYCLES 3

# Context controls
CONTEXT-LIMIT 80%
ON-CONTEXT-LIMIT compact

# Checkpointing
CHECKPOINT-AFTER each-cycle
CHECKPOINT-NAME auth-audit

# Context inclusion
CONTEXT @lib/auth/*.js
CONTEXT @tests/auth.test.js
CONTEXT @docs/authentication.md

# Working directory
CWD ./lib/auth

# Workflow steps
PROMPT Analyze the authentication module for security vulnerabilities.
PROMPT Focus on: JWT handling, password hashing, session management.

# Compaction hints
COMPACT-PRESERVE findings, recommendations
COMPACT-SUMMARY Summarize analysis progress

# Continuation for long workflows
ON-CONTEXT-LIMIT-PROMPT Continue analysis. Previous findings: {preserved}

# Output
OUTPUT-FORMAT markdown
OUTPUT-FILE audit-report.md
```

### Directives Reference

| Directive | Purpose | Example |
|-----------|---------|---------|
| `MODEL` | AI model to use | `MODEL claude-sonnet-4.5` |
| `ADAPTER` | AI provider adapter | `ADAPTER copilot` |
| `MODE` | Execution mode | `MODE audit\|read-only\|full` |
| `MAX-CYCLES` | Maximum iterations | `MAX-CYCLES 5` |
| `CONTEXT` | Include file/pattern | `CONTEXT @lib/*.js` |
| `CWD` | Working directory | `CWD ./lib/auth` |
| `PROMPT` | Prompt to send | `PROMPT Analyze security` |
| `CONTEXT-LIMIT` | Trigger threshold | `CONTEXT-LIMIT 80%` |
| `ON-CONTEXT-LIMIT` | Action when limit hit | `ON-CONTEXT-LIMIT compact` |
| `CHECKPOINT-AFTER` | When to checkpoint | `CHECKPOINT-AFTER each-cycle` |
| `CHECKPOINT-NAME` | Checkpoint identifier | `CHECKPOINT-NAME auth-v1` |
| `COMPACT-PRESERVE` | What to keep on compact | `COMPACT-PRESERVE findings` |
| `COMPACT-SUMMARY` | Summary prompt | `COMPACT-SUMMARY Summarize progress` |
| `OUTPUT-FORMAT` | Output format | `OUTPUT-FORMAT markdown\|json` |
| `OUTPUT-FILE` | Output destination | `OUTPUT-FILE report.md` |

---

## Architecture

### Core Components

```
sdqctl/
├── sdqctl/
│   ├── __init__.py
│   ├── cli.py              # Main CLI entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── run.py          # sdqctl run
│   │   ├── cycle.py        # sdqctl cycle
│   │   ├── flow.py         # sdqctl flow
│   │   ├── apply.py        # sdqctl apply
│   │   ├── status.py       # sdqctl status
│   │   └── resume.py       # sdqctl resume
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── conversation.py # ConversationFile parser
│   │   ├── context.py      # Context window tracking
│   │   ├── compaction.py   # Compaction policies
│   │   ├── checkpoint.py   # State/checkpoint management
│   │   └── session.py      # Session abstraction
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py         # Adapter interface
│   │   ├── copilot.py      # GitHub Copilot SDK adapter
│   │   ├── claude.py       # Anthropic Claude adapter
│   │   ├── openai.py       # OpenAI adapter
│   │   └── ollama.py       # Ollama local adapter
│   │
│   └── utils/
│       ├── __init__.py
│       ├── files.py        # File handling utilities
│       └── output.py       # Output formatting
│
├── tests/
├── examples/
│   └── workflows/
├── pyproject.toml
└── README.md
```

### Adapter Interface

```python
# sdqctl/adapters/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    
@dataclass
class SessionConfig:
    model: str
    tools: list = None
    streaming: bool = True
    
@dataclass  
class CompactionResult:
    preserved_content: str
    summary: str
    tokens_before: int
    tokens_after: int

class AdapterBase(ABC):
    """Base class for AI provider adapters."""
    
    @abstractmethod
    async def start(self) -> None:
        """Initialize the adapter."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Cleanup the adapter."""
        pass
    
    @abstractmethod
    async def create_session(self, config: SessionConfig) -> "Session":
        """Create a new conversation session."""
        pass
    
    @abstractmethod
    async def send(self, session: "Session", prompt: str) -> AsyncIterator[str]:
        """Send a prompt and stream response."""
        pass
    
    @abstractmethod
    async def get_context_usage(self, session: "Session") -> tuple[int, int]:
        """Get (used_tokens, max_tokens) for context window."""
        pass
    
    @abstractmethod
    async def compact(
        self, 
        session: "Session",
        preserve: list[str],
        summary_prompt: str
    ) -> CompactionResult:
        """Compact the conversation, preserving key content."""
        pass
    
    @abstractmethod
    async def checkpoint(self, session: "Session", name: str) -> str:
        """Save session state, return checkpoint ID."""
        pass
    
    @abstractmethod
    async def restore(self, checkpoint_id: str) -> "Session":
        """Restore session from checkpoint."""
        pass
```

### Copilot SDK Adapter

```python
# sdqctl/adapters/copilot.py
from copilot import CopilotClient
from .base import AdapterBase, SessionConfig, Message, CompactionResult

class CopilotAdapter(AdapterBase):
    """Adapter for GitHub Copilot SDK."""
    
    def __init__(self, cli_path: str = "copilot"):
        self.cli_path = cli_path
        self.client = None
        
    async def start(self) -> None:
        self.client = CopilotClient({"cli_path": self.cli_path})
        await self.client.start()
        
    async def stop(self) -> None:
        if self.client:
            await self.client.stop()
            
    async def create_session(self, config: SessionConfig) -> "CopilotSession":
        session = await self.client.create_session({
            "model": config.model,
            "streaming": config.streaming,
            "tools": config.tools or [],
        })
        return CopilotSession(session, config)
        
    async def send(self, session: "CopilotSession", prompt: str):
        import asyncio
        done = asyncio.Event()
        chunks = []
        
        def on_event(event):
            if event.type.value == "assistant.message_delta":
                chunk = event.data.delta_content or ""
                chunks.append(chunk)
            elif event.type.value == "session.idle":
                done.set()
                
        session._session.on(on_event)
        await session._session.send({"prompt": prompt})
        await done.wait()
        
        return "".join(chunks)
        
    async def get_context_usage(self, session) -> tuple[int, int]:
        # Copilot SDK may expose this via session stats
        # For now, estimate based on message history
        messages = await session._session.get_messages()
        estimated_tokens = sum(len(m.content) // 4 for m in messages)
        max_tokens = 128000  # Typical for modern models
        return (estimated_tokens, max_tokens)
        
    async def compact(self, session, preserve: list[str], summary_prompt: str):
        # Send compaction request to the model
        compact_prompt = f"""
        Summarize this conversation concisely.
        PRESERVE these key items: {', '.join(preserve)}
        {summary_prompt}
        """
        summary = await self.send(session, compact_prompt)
        
        # Create new session with summary as context
        # (Implementation depends on SDK capabilities)
        
        return CompactionResult(
            preserved_content=summary,
            summary=summary,
            tokens_before=0,  # Would need actual tracking
            tokens_after=0
        )
```

---

## Example Workflows

### Example 1: Security Audit

```dockerfile
# workflows/security-audit.conv
MODEL claude-sonnet-4.5
ADAPTER copilot
MODE audit
MAX-CYCLES 2

CONTEXT @lib/auth/**/*.js
CONTEXT @lib/api/**/*.js

PROMPT Perform a comprehensive security audit of authentication and API layers.
PROMPT Focus on:
  - JWT handling and validation
  - Input sanitization
  - SQL/NoSQL injection
  - XSS vulnerabilities
  - CSRF protection
  - Rate limiting

PROMPT Generate a security report with severity ratings.

OUTPUT-FORMAT markdown
OUTPUT-FILE reports/security-audit.md
```

**Usage:**
```bash
sdqctl run workflows/security-audit.conv
```

### Example 2: Multi-Cycle Code Migration

```dockerfile
# workflows/typescript-migration.conv
MODEL claude-sonnet-4.5
ADAPTER copilot
MODE full
MAX-CYCLES 5

CONTEXT-LIMIT 75%
ON-CONTEXT-LIMIT compact
COMPACT-PRESERVE converted_files, remaining_files, errors
COMPACT-SUMMARY Summarize migration progress and issues encountered.

CHECKPOINT-AFTER each-cycle
CHECKPOINT-NAME ts-migration

CONTEXT @lib/plugins/*.js

PROMPT Convert JavaScript files to TypeScript.
PROMPT For each file:
  1. Add type annotations
  2. Convert to ES modules
  3. Add JSDoc comments
  4. Update imports/exports

PROMPT After each file, update progress tracking.

ON-CONTEXT-LIMIT-PROMPT Continue TypeScript migration.
  Completed: {preserved.converted_files}
  Remaining: {preserved.remaining_files}
  Previous errors to avoid: {preserved.errors}
```

**Usage:**
```bash
sdqctl cycle workflows/typescript-migration.conv --max-cycles 10
```

### Example 3: Batch Component Audit

```dockerfile
# workflows/component-audit.conv
MODEL claude-sonnet-4.5
ADAPTER copilot
MODE audit

PROMPT Audit this component for:
  - Code quality
  - Test coverage gaps
  - Documentation completeness
  - Security considerations

OUTPUT-FORMAT json
```

**Usage:**
```bash
# Apply to all plugins in parallel
sdqctl apply workflows/component-audit.conv \
  --components "lib/plugins/*.js" \
  --parallel 4 \
  --output-dir reports/audits/
```

### Example 4: Cross-Repo Coordination

```yaml
# workflows/cross-repo-auth-update.flow
name: Update JWT Auth Across Repos
parallel: 2

phases:
  - name: Core Library
    repos:
      - nightscout/cgm-remote-monitor
    workflow: workflows/update-jwt-core.conv
    
  - name: Dependent Repos
    depends_on: [Core Library]
    repos:
      - nightscout/nightscout-connect
      - nightscout/nightscout-roles-gateway
    workflow: workflows/update-jwt-client.conv
    
  - name: Integration Tests
    depends_on: [Dependent Repos]
    run: npm run test:integration
```

**Usage:**
```bash
sdqctl flow workflows/cross-repo-auth-update.flow
```

---

## Integration with Existing Tooling

### From rag-nightscout-ecosystem-alignment

The existing `workspace_cli.py` and `run_workflow.py` patterns provide excellent foundations:

```python
# Integration example
from sdqctl.adapters.copilot import CopilotAdapter
from workspace_cli import WorkspaceCLI

class SDQWorkspace(WorkspaceCLI):
    """Extended workspace CLI with sdqctl integration."""
    
    def cmd_audit(self, args):
        """Run AI-assisted audit workflow."""
        component = args[0] if args else None
        
        # Generate ConversationFile for component
        conv_file = self.generate_audit_conv(component)
        
        # Execute via sdqctl
        return subprocess.run([
            "sdqctl", "run", conv_file,
            "--adapter", "copilot",
            "--json"
        ], capture_output=True)
```

### CI/CD Integration

```yaml
# .github/workflows/sdqctl-checks.yml
name: SDQ Quality Checks

on: [pull_request]

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install sdqctl
        run: pip install sdqctl
        
      - name: Security Audit
        run: |
          sdqctl run workflows/security-audit.conv \
            --adapter copilot \
            --json \
            --output security-report.json
            
      - name: Check Critical Issues
        run: |
          CRITICAL=$(jq '.findings | map(select(.severity == "critical")) | length' security-report.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "::error::$CRITICAL critical issues found"
            exit 1
          fi
```

---

## Implementation Phases

### Phase 1: Core CLI (Week 1)
- [ ] Project setup (pyproject.toml, structure)
- [ ] ConversationFile parser
- [ ] Basic `sdqctl run` command
- [ ] Copilot SDK adapter (using github/copilot-sdk)
- [ ] Simple context inclusion (@file syntax)

### Phase 2: Cycle & Context (Week 2)
- [ ] `sdqctl cycle` with MAX-CYCLES
- [ ] Context window tracking
- [ ] Basic compaction support
- [ ] Checkpoint/resume functionality

### Phase 3: Flow & Apply (Week 3)
- [ ] `sdqctl flow` for batch execution
- [ ] `sdqctl apply` for component iteration
- [ ] Parallel execution support
- [ ] Progress tracking and reporting

### Phase 4: Polish & Extend (Week 4)
- [ ] Additional adapters (claude, openai)
- [ ] Enhanced error handling
- [ ] Documentation
- [ ] Example workflows
- [ ] Integration tests

---

## Getting Started (First Implementation)

```bash
# Clone and setup
cd /home/bewest/src/copilot-do-proposal
mkdir -p sdqctl/sdqctl/{commands,core,adapters,utils}

# Create initial structure
cat > sdqctl/pyproject.toml << 'EOF'
[project]
name = "sdqctl"
version = "0.1.0"
description = "Software Defined Quality Control - Vendor-agnostic AI workflow orchestration"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
    "rich>=13.0",
    "github-copilot-sdk>=0.1.0",
]

[project.scripts]
sdqctl = "sdqctl.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Install in development mode
cd sdqctl
pip install -e .
```

---

## Comparison: sdqctl vs Alternatives

| Feature | sdqctl | Ralph | Shell Scripts | Copilot CLI |
|---------|--------|-------|---------------|-------------|
| Declarative workflows | ✅ ConversationFile | ⚠️ JSON PRD | ❌ Imperative | ❌ None |
| Vendor agnostic | ✅ Adapters | ❌ Copilot only | ⚠️ Manual | ❌ Copilot only |
| Context controls | ✅ Policies | ❌ None | ❌ None | ⚠️ Manual |
| Compaction | ✅ Automatic | ❌ None | ❌ None | ⚠️ Manual |
| Checkpointing | ✅ Named | ⚠️ Git commits | ❌ None | ⚠️ Session only |
| Parallel execution | ✅ Native | ❌ Sequential | ⚠️ `parallel` cmd | ❌ None |
| Multi-cycle | ✅ Controlled | ✅ Yes | ⚠️ Loops | ❌ None |

---

## Conclusion

`sdqctl` provides the **missing orchestration layer** for AI-assisted development:

1. **Declarative** - ConversationFile format encodes workflows
2. **Reproducible** - Same workflow, same results
3. **Vendor-agnostic** - Swap adapters without changing workflows
4. **Context-aware** - Automatic compaction and management
5. **Scalable** - Batch and parallel execution

The name `sdqctl` (Software Defined Quality Control) reflects the philosophy: **quality controls should be defined as code**, just like infrastructure.

---

## References

- [github/copilot-sdk](https://github.com/github/copilot-sdk) - Official Copilot CLI SDK
- [copilot-do-proposal](./README.md) - Original proposal
- [FEASIBILITY-ANALYSIS.md](./FEASIBILITY-ANALYSIS.md) - What's possible today
- [COMPLEMENTARY-TOOLING.md](./proposal/COMPLEMENTARY-TOOLING.md) - Tooling ecosystem
- [rag-nightscout-ecosystem-alignment](../rag-nightscout-ecosystem-alignment/) - Existing tooling patterns

---

**Version:** 1.0  
**Date:** 2026-01-20  
**Status:** Proposal / Ready for Implementation
