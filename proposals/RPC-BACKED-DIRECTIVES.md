# RPC-Backed Directives Proposal

> **Purpose**: Map session.rpc.* APIs to ConversationFile directives  
> **Status**: Draft  
> **Created**: 2026-03-19

---

## Problem Statement

sdqctl has several directives with "quirky" behavior because they don't use the proper SDK APIs:

1. **COMPACT** — Sends `/compact` text command, not `session.rpc.compaction.compact()`
2. **No MODE directive** — Can't switch to plan/autopilot mode mid-workflow
3. **No MODEL-SWITCH** — Model is fixed at session start
4. **No PLAN directive** — Can't read/update plan.md via API

Additionally, hooks enable powerful capabilities we're not using:
- Detecting when agents mark todos as done
- Injecting verification before tool completion
- Adding context based on tool usage patterns

---

## Proposed Directives

### 1. COMPACT (Fixed)

**Current**: Sends `/compact` as chat message
**Proposed**: Use `session.rpc.compaction.compact()`

```dockerfile
# Explicit compaction trigger
COMPACT

# Returns:
# - messagesRemoved: number
# - tokensRemoved: number
# - success: boolean
```

**Implementation**:
```python
async def execute_compact(session: CopilotSession) -> dict:
    result = await session.rpc.compaction.compact()
    return {
        "messages_removed": result.messages_removed,
        "tokens_removed": result.tokens_removed,
        "success": result.success,
    }
```

### 2. MODE (New)

**Purpose**: Switch between interactive/plan/autopilot modes

```dockerfile
# Set mode at any point in workflow
MODE interactive
MODE plan
MODE autopilot

# Query current mode
MODE ?
```

**Implementation**:
```python
async def set_mode(session: CopilotSession, mode: str):
    from copilot.generated.rpc import SessionModeSetParams, Mode
    params = SessionModeSetParams(mode=Mode(mode))
    result = await session.rpc.mode.set(params)
    return result.mode
```

### 3. MODEL-SWITCH (New)

**Purpose**: Change model mid-workflow (e.g., start cheap, upgrade for complex work)

```dockerfile
# Start with fast model
MODEL claude-haiku-4.5

PROMPT Do initial exploration...

# Switch to powerful model for synthesis
MODEL-SWITCH claude-opus-4
REASONING-EFFORT high

PROMPT Now synthesize findings...
```

**Implementation**:
```python
async def switch_model(session: CopilotSession, model_id: str, reasoning_effort: str = None):
    from copilot.generated.rpc import SessionModelSwitchToParams
    params = SessionModelSwitchToParams(
        model_id=model_id,
        reasoning_effort=reasoning_effort,
    )
    result = await session.rpc.model.switch_to(params)
    return result.model_id
```

### 4. PLAN (New)

**Purpose**: Read/update the session plan.md via API

```dockerfile
# Read current plan
PLAN read

# Update plan content
PLAN update
## Current Focus
- Item 1: In progress
- Item 2: Pending
END-PLAN

# Clear plan
PLAN delete
```

**Implementation**:
```python
async def plan_read(session: CopilotSession) -> str:
    result = await session.rpc.plan.read()
    return result.content

async def plan_update(session: CopilotSession, content: str):
    from copilot.generated.rpc import SessionPlanUpdateParams
    params = SessionPlanUpdateParams(content=content)
    await session.rpc.plan.update(params)
```

### 5. AGENT-SELECT (New)

**Purpose**: Switch to a different agent mid-workflow

```dockerfile
# Define agents at session start
DEFINE-AGENT researcher
  TOOLS grep glob view
  PROMPT You are a research assistant...
END-AGENT

DEFINE-AGENT editor
  TOOLS view edit bash
  PROMPT You are a code editor...
END-AGENT

# Later in workflow, switch agents
AGENT-SELECT researcher
PROMPT Explore the codebase...

AGENT-SELECT editor
PROMPT Now apply the changes...

# Return to default
AGENT-DESELECT
```

**Implementation**:
```python
async def agent_select(session: CopilotSession, name: str):
    from copilot.generated.rpc import SessionAgentSelectParams
    params = SessionAgentSelectParams(name=name)
    result = await session.rpc.agent.select(params)
    return result

async def agent_list(session: CopilotSession) -> list:
    result = await session.rpc.agent.list()
    return result.agents
```

---

## Hook-Based Directives

### 6. ON-TOOL-USE (New)

**Purpose**: React to specific tool usage patterns

```dockerfile
# Detect when agent marks todo as done
ON-TOOL-USE sql
  MATCH query CONTAINS "UPDATE.*status.*done"
  INJECT "Before marking done, verify the work was actually completed."
END-ON-TOOL-USE

# Log all bash commands
ON-TOOL-USE bash
  LOG command to session.log
END-ON-TOOL-USE
```

**Implementation**:
```python
def create_tool_hooks(rules: list[dict]) -> SessionHooks:
    def pre_tool_use(input: PreToolUseHookInput, ctx: dict) -> PreToolUseHookOutput:
        for rule in rules:
            if input["toolName"] == rule["tool"]:
                if rule.get("match") and rule["match"] in str(input["toolArgs"]):
                    return {"additionalContext": rule.get("inject", "")}
        return {}
    
    def post_tool_use(input: PostToolUseHookInput, ctx: dict) -> PostToolUseHookOutput:
        for rule in rules:
            if input["toolName"] == rule["tool"] and rule.get("log"):
                # Log to file or metrics
                pass
        return {}
    
    return {
        "on_pre_tool_use": pre_tool_use,
        "on_post_tool_use": post_tool_use,
    }
```

### 7. VERIFY-BEFORE-DONE (New)

**Purpose**: Inject verification when agent tries to mark work complete

```dockerfile
# Require verification before marking todos done
VERIFY-BEFORE-DONE
  RUN make test
  CHECK exit_code == 0
  INJECT "Tests passed. Proceeding with completion."
  ON-FAIL BLOCK "Cannot mark done - tests failed"
END-VERIFY
```

**Implementation**:
```python
def verify_before_done_hook(verify_config: dict) -> PreToolUseHandler:
    def hook(input: PreToolUseHookInput, ctx: dict) -> PreToolUseHookOutput:
        # Detect SQL UPDATE todos SET status='done'
        if input["toolName"] == "sql":
            query = input["toolArgs"].get("query", "")
            if "UPDATE" in query and "status" in query and ("done" in query or "complete" in query):
                # Run verification
                result = subprocess.run(verify_config["run"], shell=True)
                if result.returncode != 0:
                    return {
                        "permissionDecision": "deny",
                        "permissionDecisionReason": verify_config.get("on_fail", "Verification failed"),
                    }
                return {"additionalContext": verify_config.get("inject", "")}
        return {}
    return hook
```

---

## Tool Discovery Directive

### 8. TOOLS-LIST (New)

**Purpose**: Discover available tools for the current model

```dockerfile
# List all tools at workflow start
TOOLS-LIST

# List tools and validate exclusions
TOOLS-LIST validate-against EXCLUDE-TOOLS
```

**Implementation**:
```python
async def list_tools(client: CopilotClient, model: str = None) -> list[str]:
    from copilot.generated.rpc import ToolsListParams
    params = ToolsListParams(model=model)
    result = await client.rpc.tools.list(params)
    return [tool.name for tool in result.tools]
```

---

## Workspace API Directives

### 9. WORKSPACE (New)

**Purpose**: Manage session workspace files

```dockerfile
# List workspace files
WORKSPACE list

# Read workspace file
WORKSPACE read plan.md

# Create/update workspace file
WORKSPACE write progress.md
## Progress
- Completed: 5 items
END-WORKSPACE
```

---

## Priority Implementation Order

### P1 - Fix Existing + High Value

| Directive | Effort | Impact |
|-----------|--------|--------|
| COMPACT (fix) | Low | High — proper API, returns metrics |
| TOOLS-LIST | Low | High — enables validation |
| VERIFY-BEFORE-DONE | Medium | High — solves false completion problem |

### P2 - New Capabilities

| Directive | Effort | Impact |
|-----------|--------|--------|
| MODE | Low | Medium — plan/autopilot switching |
| MODEL-SWITCH | Low | Medium — cost optimization |
| ON-TOOL-USE | Medium | High — observability |

### P3 - Advanced

| Directive | Effort | Impact |
|-----------|--------|--------|
| AGENT-SELECT | Medium | Medium — agent orchestration |
| PLAN | Low | Low — plan.md API |
| WORKSPACE | Medium | Low — workspace management |

---

## Experiments Required

Before implementation, run these experiments:

| ID | Experiment | Validates |
|----|------------|-----------|
| SDK-E13 | `session.rpc.compaction.compact()` | COMPACT fix |
| SDK-E16 | `client.rpc.tools.list()` | TOOLS-LIST |
| SDK-E10 | Detect SQL UPDATE in hooks | VERIFY-BEFORE-DONE |
| SDK-E14 | `session.rpc.mode.set()` | MODE |
| SDK-E15 | `session.rpc.model.switchTo()` | MODEL-SWITCH |

---

## References

- SDK RPC Types: `../copilot-sdk/python/copilot/generated/rpc.py`
- SDK Hook Types: `../copilot-sdk/python/copilot/types.py`
- Current Adapter: `sdqctl/adapters/copilot.py`
- Feature Inventory: `docs/SDK-FEATURE-INVENTORY.md`
