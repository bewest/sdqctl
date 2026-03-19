# SDK Feature Inventory

> **Purpose**: Comprehensive inventory of Copilot SDK features for sdqctl integration planning  
> **SDK Version**: v0.1.33-preview.3 (as of 2026-03-19)  
> **SDK Location**: `../copilot-sdk/python`  
> **Last Audited**: 2026-03-19

---

## Executive Summary

The Copilot SDK has **468 commits** in the past 2 months. This inventory identifies features relevant to sdqctl that are **not yet utilized**.

### Key Findings

| Category | Features Available | Currently Used by sdqctl | Gap |
|----------|-------------------|-------------------------|-----|
| Tool Control | 3 | 0 | `excluded_tools`, `available_tools`, `skip_permission` |
| Agent Control | 4 | 0 | `agent`, `custom_agents`, AgentApi, FleetApi |
| Hooks | 6 | 0 | Pre/post tool use, prompt submitted, session lifecycle |
| Session APIs | 8 | 2 | Mode, Plan, Workspace, Compaction APIs unused |
| Observability | 2 | 0 | TelemetryConfig, OpenTelemetry |

---

## 1. SessionConfig Options

### Currently Used by sdqctl

```python
session_config = {
    "model": config.model,           # ✅ Used
    "streaming": config.streaming,   # ✅ Used  
    "on_permission_request": ...,    # ✅ Used
    "tools": config.tools,           # ✅ Used (custom tools)
    "infinite_sessions": {...},      # ✅ Used
}
```

### NOT Used (Opportunities)

| Option | Type | Purpose | sdqctl Directive Potential |
|--------|------|---------|---------------------------|
| `excluded_tools` | `list[str]` | Disable built-in tools | `EXCLUDE-TOOLS sql task store_memory` |
| `available_tools` | `list[str]` | Allowlist only these tools | `AVAILABLE-TOOLS view edit bash` |
| `disabled_skills` | `list[str]` | Disable skills | `DISABLE-SKILLS nightscout-cgm` |
| `custom_agents` | `list[CustomAgentConfig]` | Define custom agents | `DEFINE-AGENT name prompt` |
| `agent` | `str` | Pre-select agent at start | `AGENT ecosystem-alignment` |
| `mcp_servers` | `dict[str, MCPServerConfig]` | MCP server configs | `MCP-SERVER name config` |
| `reasoning_effort` | `"low"\|"medium"\|"high"\|"xhigh"` | Model reasoning level | `REASONING-EFFORT high` |
| `system_message` | `SystemMessageConfig` | Custom system message | `SYSTEM-MESSAGE append\|replace` |
| `hooks` | `SessionHooks` | Lifecycle hooks | See Hooks section |
| `working_directory` | `str` | Session CWD | `CWD` directive (exists) |
| `skill_directories` | `list[str]` | Load skills from dirs | `SKILL-DIRS ./skills` |
| `config_dir` | `str` | Override config location | `CONFIG-DIR ./config` |
| `on_event` | `Callable[[SessionEvent], None]` | Early event handler | Internal use |

---

## 2. Tool Control Features

### `excluded_tools` / `available_tools`

**SDK Definition** (types.py):
```python
class SessionConfig(TypedDict, total=False):
    # List of tool names to allow (takes precedence over excluded_tools)
    available_tools: list[str]
    # List of tool names to disable (ignored if available_tools is set)
    excluded_tools: list[str]
```

**Experiment Needed**: Does this work for built-in tools like `sql`, `task`, `store_memory`?

**Proposed Directive**:
```dockerfile
# Disable SQL to avoid dual bookkeeping with markdown
EXCLUDE-TOOLS sql store_memory

# Or allowlist mode for strict control
AVAILABLE-TOOLS view edit bash grep glob create
```

### `skip_permission` for Tools

**SDK Definition** (types.py):
```python
@dataclass
class Tool:
    name: str
    description: str
    handler: ToolHandler
    parameters: dict[str, Any] | None = None
    overrides_built_in_tool: bool = False
    skip_permission: bool = False  # ← Auto-approve
```

**Use Case**: Auto-approve safe tools without permission prompts.

---

## 3. Agent & Fleet APIs

### AgentApi (session.rpc.agent.*)

| Method | Purpose | Potential Use |
|--------|---------|---------------|
| `list()` | List available agents | Discover agents dynamically |
| `get_current()` | Get active agent | Track agent state |
| `select(name)` | Switch to agent | Mid-workflow agent switching |
| `deselect()` | Return to default | Exit agent mode |

### FleetApi (session.rpc.fleet.*)

| Method | Purpose | Potential Use |
|--------|---------|---------------|
| `start(prompt)` | Start parallel fleet | Parallel backlog processing |

**Proposed Directives**:
```dockerfile
# Pre-select agent at session start
AGENT ecosystem-alignment

# Launch fleet for parallel work
FLEET-START "Process all P1 items in parallel"
```

### CustomAgentConfig

**SDK Definition**:
```python
class CustomAgentConfig(TypedDict, total=False):
    name: str                    # Unique name
    display_name: str            # UI display name  
    description: str             # What agent does
    tools: list[str] | None      # Tools agent can use
    prompt: str                  # Agent prompt
    mcp_servers: dict[str, MCPServerConfig]  # Agent-specific MCP
    infer: bool                  # Available for inference
```

**Proposed Directive**:
```dockerfile
# Define inline agent
DEFINE-AGENT backlog-processor
  TOOLS view edit bash grep
  PROMPT You are a backlog processor. Pick next item, execute, mark done.
END-AGENT
```

---

## 4. Session Hooks

### Available Hooks (SessionHooks)

| Hook | Trigger | Potential Use |
|------|---------|---------------|
| `on_pre_tool_use` | Before tool executes | Audit, filter, inject context |
| `on_post_tool_use` | After tool executes | Capture results, checkpoint |
| `on_user_prompt_submitted` | User sends message | Inject prologue, log |
| `on_session_start` | Session begins | Initialize state |
| `on_session_end` | Session ends | Cleanup, persist state |
| `on_error_occurred` | Error happens | Custom error handling |

### PreToolUseHookInput/Output

```python
class PreToolUseHookInput(TypedDict):
    timestamp: int
    cwd: str
    tool_name: str      # ← Can inspect which tool
    arguments: dict     # ← Can inspect arguments

class PreToolUseHookOutput(TypedDict, total=False):
    allow: bool         # ← Can BLOCK tool execution!
    modify_args: dict   # ← Can MODIFY arguments
```

**Key Insight**: Hooks can **block or modify** tool calls. This is more powerful than `excluded_tools` because it's dynamic and context-aware.

**Proposed Directive**:
```dockerfile
# Block sql tool writes, allow reads
HOOK pre_tool_use
  IF tool_name == "sql" AND NOT query.startswith("SELECT"):
    BLOCK "SQL writes disabled by SYNC-SQL readonly policy"
  END
END-HOOK
```

---

## 5. Session RPC APIs

### Currently Accessible via `session.rpc.*`

| API | Methods | Status | sdqctl Use |
|-----|---------|--------|------------|
| `model` | `get_current()`, `switch_to()` | Available | ❌ Not used (could enable mid-session model switch) |
| `mode` | `get()`, `set()` | Available | ❌ Not used (interactive/plan mode) |
| `plan` | `read()`, `update()`, `delete()` | Available | ❌ Not used (plan.md manipulation) |
| `workspace` | `list_files()`, `read_file()`, `create_file()` | Available | ❌ Not used (workspace file ops) |
| `fleet` | `start()` | Available | ❌ Not used (parallel agents) |
| `agent` | `list()`, `get_current()`, `select()`, `deselect()` | Available | ❌ Not used |
| `compaction` | `compact()` | Experimental | ❌ Not used (manual compaction trigger) |
| `tools` | `handle_pending_tool_call()` | Internal | Used by SDK |
| `permissions` | `handle_pending_permission_request()` | Internal | Used by SDK |
| `shell` | `exec()`, `kill()` | Available | ❌ Not used (programmatic shell) |

### High-Value Unexplored APIs

1. **`session.rpc.compaction.compact()`** — Trigger compaction programmatically
   - Use case: Force compact before checkpoint
   - Directive: `COMPACT` (explicit trigger)

2. **`session.rpc.model.switch_to()`** — Change model mid-session
   - Use case: Start cheap (haiku), upgrade to expensive (opus) for complex work
   - Directive: `MODEL-SWITCH claude-opus-4` inline in workflow

3. **`session.rpc.shell.exec()`** — Programmatic shell execution
   - Use case: Alternative to RUN directive with more control
   - Returns: `SessionShellExecResult` with structured output

4. **`session.rpc.workspace.*`** — File operations in workspace
   - Use case: Manage session artifacts programmatically
   - Could replace some CONTEXT/OUTPUT-FILE handling

---

## 6. Observability Features

### TelemetryConfig

```python
class TelemetryConfig(TypedDict, total=False):
    otlp_endpoint: str      # OpenTelemetry endpoint
    file_path: str          # Log to file
    exporter_type: str      # Exporter type
    source_name: str        # Source identifier
    capture_content: bool   # Include message content
```

**Use Case**: Export session telemetry to observability stack.

**Proposed Directive**:
```dockerfile
TELEMETRY otlp://localhost:4317
TELEMETRY-SOURCE sdqctl-backlog-processor
```

---

## 7. Client-Level APIs

### CopilotClient Methods

| Method | Purpose | sdqctl Use |
|--------|---------|------------|
| `start()` | Start CLI server | ✅ Used |
| `stop()` | Stop CLI server | ✅ Used |
| `create_session(config)` | Create session | ✅ Used |
| `resume_session(id, config)` | Resume session | ✅ Used |
| `list_models()` | Get available models | ❌ Not used (could validate MODEL directive) |
| `list_sessions(filter)` | List sessions | ✅ Used in `sessions list` |
| `delete_session(id)` | Delete session | ✅ Used |
| `ping()` | Health check | ❌ Not used |
| `get_status()` | Server status | ✅ Used in `status` |
| `get_auth_status()` | Auth status | ✅ Used in `status` |
| `get_last_session_id()` | Last session | ❌ Not used |
| `get_foreground_session_id()` | Foreground session | ❌ Not used |
| `set_foreground_session_id()` | Set foreground | ❌ Not used |
| `on(handler)` | Lifecycle events | ❌ Not used |
| `rpc.tools.list(model)` | List tools for model | ❌ Not used (could audit available tools) |

### `client.rpc.tools.list()`

**Key Discovery**: Can list all tools available for a model!

```python
tools_result = await client.rpc.tools.list(ToolsListParams(model="claude-sonnet-4"))
for tool in tools_result.tools:
    print(f"{tool.name}: {tool.description}")
```

**Use Case**: Validate `EXCLUDE-TOOLS` directive against actual available tools.

---

## 8. Priority Ranking for Implementation

### P1 - High Value, Low Effort

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| `excluded_tools` | ~20 lines | High | Solves SQL/agent control problem |
| `available_tools` | ~20 lines | High | Stricter tool control |
| `reasoning_effort` | ~5 lines | Medium | Model tuning per workflow |
| `client.rpc.tools.list()` | ~30 lines | Medium | Tool discovery/validation |

### P2 - High Value, Medium Effort

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| `hooks.on_pre_tool_use` | ~100 lines | High | Dynamic tool filtering |
| `session.rpc.agent.*` | ~50 lines | Medium | Agent orchestration |
| `session.rpc.compaction.compact()` | ~20 lines | Medium | Manual compaction |
| `custom_agents` | ~100 lines | Medium | Inline agent definition |

### P3 - Medium Value, Higher Effort

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| `session.rpc.fleet.start()` | ~150 lines | High | Parallel execution |
| `TelemetryConfig` | ~100 lines | Medium | Observability |
| `mcp_servers` | ~200 lines | Medium | MCP integration |

---

## 9. Recommended Experiments

### Experiment 1: Tool Exclusion (SDK-E01)

**Goal**: Verify `excluded_tools` works for built-in tools.

```python
import asyncio
from copilot import CopilotClient, PermissionHandler

async def test_excluded_tools():
    client = CopilotClient()
    await client.start()
    
    session = await client.create_session({
        "excluded_tools": ["sql"],
        "on_permission_request": PermissionHandler.approve_all,
    })
    
    reply = await session.send_and_wait(
        "Use the sql tool to SELECT 1"
    )
    print(f"Reply: {reply.data.content}")
    # Expected: Tool not available or error
    
    await client.stop()

asyncio.run(test_excluded_tools())
```

### Experiment 2: Pre-Tool Hook Filtering (SDK-E06)

**Goal**: Test dynamic tool blocking via hooks.

```python
async def test_pre_tool_hook():
    def block_sql_writes(input: dict) -> dict:
        if input.get("tool_name") == "sql":
            query = input.get("arguments", {}).get("query", "")
            if not query.strip().upper().startswith("SELECT"):
                return {"allow": False}
        return {"allow": True}
    
    session = await client.create_session({
        "hooks": {
            "on_pre_tool_use": block_sql_writes,
        },
        ...
    })
```

### Experiment 3: Tool Discovery (SDK-E07)

**Goal**: List all available tools to validate exclusion directives.

```python
async def discover_tools():
    result = await client.rpc.tools.list(ToolsListParams(model="claude-sonnet-4"))
    for tool in result.tools:
        print(f"{tool.name}")
```

---

## 10. References

- SDK Source: `../copilot-sdk/python/copilot/`
- SDK Types: `../copilot-sdk/python/copilot/types.py`
- SDK RPC: `../copilot-sdk/python/copilot/generated/rpc.py`
- SDK Events: `../copilot-sdk/python/copilot/generated/session_events.py`
- sdqctl Adapter: `sdqctl/adapters/copilot.py`
- Related Backlog: `proposals/backlogs/sdk-integration.md`
