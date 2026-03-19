# GitHub Copilot CLI - Available Tools Inventory

> **Generated**: 2026-03-19  
> **Source**: SDK `client.rpc.tools.list()` + CLI documentation  
> **Status**: SDK-E16 experiment results ✓ VERIFIED  
> **Test Script**: `tests/sdk-integration/test_tool_discovery.py`

---

## SDK Tool Discovery Results

**14 core tools** returned by `client.rpc.tools.list()`:

| Tool | Category | Required Params |
|------|----------|-----------------|
| ask_user | Session | question |
| bash | Shell | command, description |
| fetch_copilot_cli_documentation | Meta | - |
| glob | File System | pattern |
| grep | File System | pattern |
| list_bash | Shell | - |
| read_bash | Shell | shellId, delay |
| report_intent | Session | intent |
| skill | Agents | skill |
| stop_bash | Shell | shellId |
| str_replace_editor | File System | command, path |
| task | Agents | prompt, agent_type, name |
| web_fetch | Network | url |
| write_bash | Shell | shellId, delay |

> **Note**: Additional tools like `sql`, `store_memory`, `view`, `edit`, `create`, 
> and GitHub MCP tools may be added based on session configuration.

---

## Available Models (19)

| Model ID | Display Name | Billing | Reasoning |
|----------|--------------|---------|-----------|
| claude-sonnet-4.6 | Claude Sonnet 4.6 | x1.0 | medium |
| claude-sonnet-4.5 | Claude Sonnet 4.5 | x1.0 | - |
| claude-haiku-4.5 | Claude Haiku 4.5 | x0.33 | - |
| claude-opus-4.6 | Claude Opus 4.6 | x3.0 | high |
| claude-opus-4.6-fast | Claude Opus 4.6 (fast) | x30.0 | high |
| claude-opus-4.5 | Claude Opus 4.5 | x3.0 | - |
| claude-sonnet-4 | Claude Sonnet 4 | x1.0 | - |
| gemini-3-pro-preview | Gemini 3 Pro (Preview) | x1.0 | - |
| gpt-5.4 | GPT-5.4 | x1.0 | medium |
| gpt-5.3-codex | GPT-5.3-Codex | x1.0 | medium |
| gpt-5.2-codex | GPT-5.2-Codex | x1.0 | high |
| gpt-5.2 | GPT-5.2 | x1.0 | medium |
| gpt-5.1-codex-max | GPT-5.1-Codex-Max | x1.0 | medium |
| gpt-5.1-codex | GPT-5.1-Codex | x1.0 | medium |
| gpt-5.1 | GPT-5.1 | x1.0 | medium |
| gpt-5.4-mini | GPT-5.4 mini | x0.33 | medium |
| gpt-5.1-codex-mini | GPT-5.1-Codex-Mini | x0.33 | medium |
| gpt-5-mini | GPT-5 mini | x0.0 | medium |
| gpt-4.1 | GPT-4.1 | x0.0 | - |

---

## Overview

This document catalogs all built-in tools available in GitHub Copilot CLI. Tools can be controlled via:

- `availableTools: ["tool1", "tool2"]` — Whitelist mode (only these tools)
- `excludedTools: ["sql", "task"]` — Blacklist mode (all except these)
- `tools: [customTool]` — Add custom tools via SDK

---

## Core File System Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `view` | Read file contents or list directory entries | Read-only |
| `create` | Create new files (fails if exists) | Write |
| `edit` | Modify existing files via search/replace | Write |
| `glob` | Find files by pattern matching | Read-only |
| `grep` | Search file contents with regex (ripgrep) | Read-only |

### view

**Parameters**:
- `path` (required): Absolute path to file or directory
- `view_range` (optional): Line range `[start, end]` for partial view
- `forceReadLargeFiles` (optional): Skip large file check

**Example**:
```json
{"path": "/home/user/src/main.py", "view_range": [1, 50]}
```

### create

**Parameters**:
- `path` (required): Absolute path for new file
- `file_text` (required): Content to write

**Constraints**: Parent directories must exist; file must not exist.

### edit

**Parameters**:
- `path` (required): Absolute path to existing file
- `old_str` (required): Exact string to find (must be unique)
- `new_str` (required): Replacement string

**Usage**: Make surgical edits by matching exact content including whitespace.

### glob

**Parameters**:
- `pattern` (required): Glob pattern (e.g., `**/*.py`, `src/**/*.ts`)
- `path` (optional): Directory to search in

**Supports**: `*`, `**`, `?`, `{a,b}` patterns

### grep

**Parameters**:
- `pattern` (required): Regex pattern to search
- `path` (optional): Directory to search in
- `glob` (optional): File pattern filter (e.g., `*.py`)
- `output_mode` (optional): `content`, `files_with_matches`, `count`
- `-n`, `-A`, `-B`, `-C` (optional): Line numbers and context

---

## Shell Execution Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `bash` | Execute bash commands | Execute |
| `read_bash` | Read output from async shell | Read-only |
| `write_bash` | Send input to async shell | Execute |
| `stop_bash` | Terminate a shell session | Execute |
| `list_bash` | List active shell sessions | Read-only |

### bash

**Parameters**:
- `command` (required): Command to execute
- `description` (required): Human-readable description
- `mode` (optional): `sync` (default) or `async`
- `initial_wait` (optional): Seconds to wait for sync mode
- `detach` (optional): Keep running after session ends
- `shellId` (optional): Reuse existing session

**Modes**:
- `sync`: Wait for completion (default 30s timeout)
- `async`: Background execution, use read_bash/write_bash
- `async + detach`: Survives session shutdown

### read_bash

**Parameters**:
- `shellId` (required): Session ID from bash call
- `delay` (optional): Seconds to wait before reading

### write_bash

**Parameters**:
- `shellId` (required): Session ID
- `input` (required): Text or special keys (`{enter}`, `{up}`, `{down}`)
- `delay` (required): Seconds to wait after sending

### stop_bash

**Parameters**:
- `shellId` (required): Session ID to terminate

---

## Session Management Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `sql` | Query session SQLite database | Session |
| `store_memory` | Persist facts for future sessions | Session |
| `report_intent` | Update UI intent display | Session |
| `ask_user` | Prompt user for input | Interactive |

### sql

**Parameters**:
- `query` (required): SQLite SQL statement
- `description` (required): What the query does
- `database` (optional): `session` (default) or `session_store`

**Pre-existing tables**: `todos`, `todo_deps`

**Use cases**: Task tracking, batch operations, state machines

### store_memory

**Parameters**:
- `subject` (required): Topic (1-2 words)
- `fact` (required): Description (<200 chars)
- `citations` (required): Source reference
- `reason` (required): Why this is important
- `category` (required): `bootstrap_and_build`, `user_preferences`, `general`, `file_specific`

### report_intent

**Parameters**:
- `intent` (required): Current action description (4 words max)

### ask_user

**Parameters**:
- `question` (required): Question to ask
- `choices` (optional): Multiple choice options
- `allow_freeform` (optional): Allow text input (default: true)

---

## Agent & Task Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `task` | Launch specialized sub-agents | Spawn |
| `read_agent` | Check sub-agent status/results | Read-only |
| `list_agents` | List active background agents | Read-only |
| `skill` | Invoke registered skills | Execute |

### task

**Parameters**:
- `name` (required): Short name for agent
- `prompt` (required): Task description with full context
- `agent_type` (required): `explore`, `task`, `general-purpose`, `code-review`
- `description` (required): 3-5 word summary
- `mode` (optional): `sync` or `background`
- `model` (optional): Model override

**Agent Types**:
| Type | Tools | Model | Use Case |
|------|-------|-------|----------|
| `explore` | grep, glob, view, bash | Haiku | Code exploration, Q&A |
| `task` | All CLI tools | Haiku | Builds, tests, lints |
| `general-purpose` | All CLI tools | Sonnet | Complex multi-step |
| `code-review` | All CLI tools (read) | - | PR review |

### read_agent

**Parameters**:
- `agent_id` (required): ID from task call
- `since_turn` (optional): Get turns after this index
- `wait` (optional): Block until completion
- `timeout` (optional): Max wait time (default 10s, max 300s)

### skill

**Parameters**:
- `skill` (required): Skill name to invoke

---

## External Integration Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `web_fetch` | Fetch URL content as markdown | Network |
| `github-mcp-server-*` | GitHub API operations | Network |

### web_fetch

**Parameters**:
- `url` (required): URL to fetch
- `raw` (optional): Return HTML instead of markdown
- `max_length` (optional): Character limit (default 5000, max 20000)
- `start_index` (optional): Pagination offset

### GitHub MCP Tools

GitHub integration is provided via MCP server. Available tools:

| Tool | Purpose |
|------|---------|
| `github-mcp-server-actions_get` | Get workflow/run/job details |
| `github-mcp-server-actions_list` | List workflows/runs/jobs |
| `github-mcp-server-get_commit` | Get commit details |
| `github-mcp-server-get_file_contents` | Read repo files |
| `github-mcp-server-get_job_logs` | Get CI job logs |
| `github-mcp-server-issue_read` | Get issue details |
| `github-mcp-server-list_branches` | List branches |
| `github-mcp-server-list_commits` | List commits |
| `github-mcp-server-list_issues` | List issues |
| `github-mcp-server-list_pull_requests` | List PRs |
| `github-mcp-server-pull_request_read` | Get PR details/diff/status |
| `github-mcp-server-search_code` | Search code across GitHub |
| `github-mcp-server-search_issues` | Search issues |
| `github-mcp-server-search_pull_requests` | Search PRs |
| `github-mcp-server-search_repositories` | Search repos |
| `github-mcp-server-search_users` | Search users |
| `github-mcp-server-get_copilot_space` | Access Copilot Spaces |
| `github-mcp-server-list_copilot_spaces` | List Copilot Spaces |

---

## Documentation & Meta Tools

| Tool | Description |
|------|-------------|
| `fetch_copilot_cli_documentation` | Get CLI help/README |

---

## Tool Filtering Examples

### Read-Only Mode
```typescript
const session = await client.createSession({
    availableTools: ["view", "grep", "glob"],
});
```

### No Shell Access
```typescript
const session = await client.createSession({
    excludedTools: ["bash", "read_bash", "write_bash", "stop_bash"],
});
```

### No SQL/Task Management
```typescript
const session = await client.createSession({
    excludedTools: ["sql", "task", "store_memory"],
});
```

### Custom Agent with Limited Tools
```typescript
const session = await client.createSession({
    customAgents: [{
        name: "researcher",
        displayName: "Research Agent",
        tools: ["grep", "glob", "view"],
        prompt: "You are a research assistant. No modifications allowed.",
    }],
});
```

---

## Tool Categories Summary

| Category | Tools | Count |
|----------|-------|-------|
| **File System** | view, create, edit, glob, grep | 5 |
| **Shell** | bash, read_bash, write_bash, stop_bash, list_bash | 5 |
| **Session** | sql, store_memory, report_intent, ask_user | 4 |
| **Agents** | task, read_agent, list_agents, skill | 4 |
| **Network** | web_fetch | 1 |
| **GitHub** | github-mcp-server-* | 17+ |
| **Meta** | fetch_copilot_cli_documentation | 1 |

**Total**: ~37+ built-in tools

---

## sdqctl Integration Considerations

### Tools to Consider Excluding

For tighter workflow control with sdqctl:

| Tool | Reason to Exclude |
|------|-------------------|
| `sql` | Conflicts with markdown backlog tracking |
| `task` | sdqctl controls iteration, not sub-agents |
| `store_memory` | sdqctl manages cross-session state |

### Tools to Keep

| Tool | Reason to Keep |
|------|----------------|
| `view`, `grep`, `glob` | Essential for exploration |
| `edit`, `create` | Essential for modifications |
| `bash` | Required for builds/tests |
| `ask_user` | Required for clarifications |

### Proposed sdqctl Directive

```dockerfile
# In .conv file
EXCLUDE-TOOLS sql task store_memory
```

Implementation:
```python
session = await client.createSession({
    excluded_tools: ["sql", "task", "store_memory"],
})
```

---

## References

- SDK Types: `copilot-sdk/python/copilot/types.py`
- RPC Definitions: `copilot-sdk/python/copilot/generated/rpc.py`
- Test Scenarios: `copilot-sdk/test/scenarios/tools/`
- CLI Help: `/help` command

---

## Known Issues

### CLI v1.0.9 SDK Session Error

When using the Python SDK to create sessions programmatically, there's a bug where 
`send_and_wait` or event-driven messaging fails with:

```
TypeError: t.asString is not a function
at Object.asXML
```

**Status**: Affects CLI v1.0.9
**Workaround**: Use CLI directly or wait for patch
**Impact**: Tool filtering experiments (SDK-E01, SDK-E02) cannot be validated via SDK

### RPC Tool Discovery Works

`client.rpc.tools.list()` successfully enumerates available tools:
- 14 core built-in tools
- 19 available models
- Model billing multipliers accessible

### Session Creation Works

`client.create_session()` completes successfully, but subsequent `send()` calls fail.

---
