# SDK Session Persistence Integration

> **Status**: Complete ✅  
> **Date**: 2026-01-24  
> **Updated**: 2026-01-25  
> **Priority**: P2 (Medium Impact)  
> **Scope**: Resume, list, and delete sessions  
> **SDK Available**: ✅ Yes - `../../copilot-sdk/python` (Protocol Version 2)

---

## Executive Summary

The Copilot SDK v2 provides session persistence APIs (`resume_session`, `list_sessions`, `delete_session`) that enable multi-day workflows and session management. This proposal outlines how to expose these capabilities through sdqctl.

---

## SDK APIs

### Available Methods

```python
from copilot import CopilotClient

async with CopilotClient() as client:
    await client.start()
    
    # List all sessions with metadata
    sessions = await client.list_sessions()
    # Returns: [SessionMetadata, ...]
    # SessionMetadata: {sessionId, startTime, modifiedTime, summary?, isRemote}
    
    # Resume an existing session
    session = await client.resume_session("user-123-conversation")
    # Conversation history is restored
    
    # Delete a session permanently
    await client.delete_session("user-123-conversation")
```

### Session Metadata

```python
class SessionMetadata(TypedDict):
    sessionId: str          # Session identifier
    startTime: str          # ISO 8601 timestamp
    modifiedTime: str       # ISO 8601 timestamp  
    summary: NotRequired[str]  # Optional summary
    isRemote: bool          # Whether session is remote
```

---

## Proposed Features

### 1. Named Sessions for Workflows

Allow workflows to specify a session name for resumability:

```dockerfile
# ConversationFile directive
SESSION-NAME security-audit-2026-01

PROMPT Review the authentication module.
```

```bash
# CLI option
sdqctl run workflow.conv --session-name security-audit-2026-01
```

### 2. Resume Workflow Command

Continue a previous workflow session:

```bash
# Resume by session name
sdqctl resume security-audit-2026-01

# Resume with additional prompts
sdqctl resume security-audit-2026-01 --prompt "Continue with the authorization module"

# Resume and run remaining steps from a workflow
sdqctl resume security-audit-2026-01 --continue workflow.conv
```

### 3. Session Management Commands

```bash
# List all sessions
sdqctl sessions list
sdqctl sessions list --format json
sdqctl sessions list --filter "security*"

# Show session details
sdqctl sessions show security-audit-2026-01

# Delete a session
sdqctl sessions delete security-audit-2026-01
sdqctl sessions delete --older-than 7d

# Clean up old sessions
sdqctl sessions cleanup --older-than 30d --dry-run
sdqctl sessions cleanup --older-than 30d
```

### 4. Enhanced Status Command

```bash
# Show sessions in status
sdqctl status --sessions

# Output:
# Sessions:
#   security-audit-2026-01  modified: 2h ago   remote: no
#   refcat-exploration      modified: 1d ago   remote: no
#   stpa-analysis           modified: 3d ago   remote: no
```

---

## Implementation

### Phase 1: Adapter Methods ✅

**Status**: Complete (2026-01-25)

Added session management methods to `CopilotAdapter` in `sdqctl/adapters/copilot.py`:

- `list_sessions()` - Returns list of session metadata dicts
- `resume_session(session_id, config)` - Resumes an existing session
- `delete_session(session_id)` - Deletes a session permanently

**Tests**: 8 new tests in `tests/test_copilot_adapter.py::TestSessionPersistence`

```python
# sdqctl/adapters/copilot.py

async def list_sessions(self) -> list[dict]:
    """List all available sessions."""
    _ensure_copilot_sdk()
    if not self._client:
        await self.start()
    
    sessions = await self._client.list_sessions()
    return [
        {
            "id": s["sessionId"],
            "start_time": s["startTime"],
            "modified_time": s["modifiedTime"],
            "summary": s.get("summary"),
            "is_remote": s["isRemote"],
        }
        for s in sessions
    ]

async def resume_session(
    self, 
    session_id: str, 
    config: AdapterConfig
) -> AdapterSession:
    """Resume an existing session by ID."""
    _ensure_copilot_sdk()
    if not self._client:
        await self.start()
    
    session = await self._client.resume_session(session_id)
    
    return AdapterSession(
        id=session.session_id,
        adapter=self,
        config=config,
        _internal=session,
    )

async def delete_session(self, session_id: str) -> None:
    """Delete a session permanently."""
    _ensure_copilot_sdk()
    if not self._client:
        await self.start()
    
    await self._client.delete_session(session_id)
```

### Phase 2: Sessions Command Group ✅

**Status**: Complete (2026-01-25)

Added `sdqctl sessions` command group with subcommands in `sdqctl/commands/sessions.py`:

- `sessions list` - List all available sessions with filtering
- `sessions delete` - Delete a session permanently  
- `sessions cleanup` - Clean up old sessions by age

**Features**:
- Table and JSON output formats
- Glob pattern filtering (`--filter "audit-*"`)
- Age-based cleanup (`--older-than 7d`)
- Dry-run mode for cleanup
- Remote session filtering (skipped per design decision)
- Old session tips (prompts for cleanup when sessions >30 days exist)

**Tests**: 36 new tests in `tests/test_sessions_command.py`

```python
# sdqctl/commands/sessions.py

import click
from datetime import datetime, timedelta

@click.group()
def sessions():
    """Manage conversation sessions."""
    pass

@sessions.command("list")
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.option("--filter", "name_filter", help="Filter by session name pattern")
async def list_sessions(format, name_filter):
    """List all available sessions."""
    adapter = get_adapter()
    await adapter.start()
    
    try:
        sessions = await adapter.list_sessions()
        
        if name_filter:
            import fnmatch
            sessions = [s for s in sessions if fnmatch.fnmatch(s["id"], name_filter)]
        
        if format == "json":
            click.echo(json.dumps(sessions, indent=2))
        else:
            for s in sessions:
                age = format_age(s["modified_time"])
                click.echo(f"  {s['id']:40} modified: {age:10} remote: {s['is_remote']}")
    finally:
        await adapter.stop()

@sessions.command("delete")
@click.argument("session_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
async def delete_session(session_id, force):
    """Delete a session permanently."""
    if not force:
        click.confirm(f"Delete session '{session_id}'?", abort=True)
    
    adapter = get_adapter()
    await adapter.start()
    
    try:
        await adapter.delete_session(session_id)
        click.echo(f"Deleted session: {session_id}")
    finally:
        await adapter.stop()

@sessions.command("cleanup")
@click.option("--older-than", required=True, help="Delete sessions older than (e.g., 7d, 24h)")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
async def cleanup_sessions(older_than, dry_run):
    """Clean up old sessions."""
    cutoff = parse_duration(older_than)
    
    adapter = get_adapter()
    await adapter.start()
    
    try:
        sessions = await adapter.list_sessions()
        old_sessions = [
            s for s in sessions 
            if datetime.fromisoformat(s["modified_time"]) < cutoff
        ]
        
        if dry_run:
            click.echo(f"Would delete {len(old_sessions)} sessions:")
            for s in old_sessions:
                click.echo(f"  {s['id']}")
        else:
            for s in old_sessions:
                await adapter.delete_session(s["id"])
                click.echo(f"Deleted: {s['id']}")
            click.echo(f"Deleted {len(old_sessions)} sessions")
    finally:
        await adapter.stop()
```

### Phase 3: Resume Command ✅

**Status**: Complete (2026-01-25)

Added `sessions resume` subcommand in `sdqctl/commands/sessions.py`:

```python
@sessions.command("resume")
@click.argument("session_id")
@click.option("--prompt", "-p", help="Send an immediate prompt after resuming")
@click.option("--adapter", "-a", default="copilot", help="Adapter to use")
@click.option("--model", "-m", help="Model to use for resumed session")
async def resume_session_cmd(session_id, prompt, adapter, model, streaming):
    """Resume a previous conversation session."""
    config = AdapterConfig(model=model or "gpt-4", streaming=streaming)
    session = await ai_adapter.resume_session(session_id, config)
    
    if prompt:
        response = await ai_adapter.send(session, prompt)
        # Display response
```

**Usage**:
```bash
sdqctl sessions resume security-audit-2026-01
sdqctl sessions resume my-session --prompt "Continue with auth module"
```

**Tests**: 5 tests in `tests/test_sessions_command.py::TestSessionsResumeCommand`

### Phase 4: Named Sessions in Workflows ✅

**Status**: Complete (2026-01-25)

Added `SESSION-NAME` directive to `sdqctl/core/conversation.py`:

- `DirectiveType.SESSION_NAME` enum value
- `session_name` field in `ConversationFile` dataclass
- Directive parsing in `_apply_directive()`

Added `--session-name` CLI option to `sdqctl run`:

```python
# sdqctl/commands/run.py

# Determine session name: CLI overrides workflow directive
effective_session_name = session_name or conv.session_name

# Create or resume adapter session based on session name
if effective_session_name:
    try:
        adapter_session = await ai_adapter.resume_session(effective_session_name, adapter_config)
    except Exception:
        adapter_session = await ai_adapter.create_session(adapter_config)
else:
    adapter_session = await ai_adapter.create_session(adapter_config)
```

**Usage**:
```dockerfile
# In workflow file
SESSION-NAME security-audit-2026-01
MODEL gpt-4
PROMPT Analyze the code.
```

```bash
# Or via CLI
sdqctl run workflow.conv --session-name security-audit-2026-01
```

**Tests**: 4 tests in `tests/test_sessions_command.py::TestSessionNameDirective`

---

## Use Cases

### 1. Multi-Day Security Audit

```bash
# Day 1: Start audit
sdqctl run security-audit.conv --session-name audit-2026-01-24

# Day 2: Continue where you left off
sdqctl resume audit-2026-01-24 --prompt "Continue with the API endpoints"

# Day 3: Finish and cleanup
sdqctl resume audit-2026-01-24 --prompt "Generate final report"
sdqctl sessions delete audit-2026-01-24
```

### 2. Exploratory Analysis

```bash
# Start exploration
sdqctl run explore.conv --session-name codebase-exploration

# Later, continue exploring
sdqctl resume codebase-exploration
# Interactive mode with conversation history preserved
```

### 3. CI/CD Session Management

```bash
# In CI: Clean up old sessions
sdqctl sessions cleanup --older-than 7d

# Keep named sessions for ongoing work
sdqctl sessions list --filter "release-*"
```

---

## Configuration

### New AdapterConfig Fields

```python
@dataclass
class AdapterConfig:
    model: str = "gpt-4"
    streaming: bool = True
    session_name: Optional[str] = None  # Named session for resumability
    resume_if_exists: bool = False      # Resume named session if it exists
```

### ConversationFile Directives

```dockerfile
# Name this session for later resumption
SESSION-NAME my-analysis

# Resume existing session if available, else create new
SESSION-RESUME-IF-EXISTS true
```

---

## Benefits

1. **Multi-day workflows** - Don't lose context between work sessions
2. **Exploratory analysis** - Continue investigations without re-explaining
3. **Session management** - List, clean up, organize sessions
4. **CI/CD integration** - Automated session lifecycle management

---

## Testing

```python
def test_list_sessions():
    """Test listing sessions."""
    adapter = CopilotAdapter()
    sessions = await adapter.list_sessions()
    assert isinstance(sessions, list)

def test_session_resume():
    """Test resuming a session."""
    # Create session
    session = await adapter.create_session(config)
    session_id = session.id
    
    # Destroy session (keeps data)
    await adapter.destroy_session(session)
    
    # Resume
    resumed = await adapter.resume_session(session_id, config)
    assert resumed.id == session_id
```

---

## Open Questions

1. **Session naming conflicts** - What if session name already exists?
   - ✅ **DECIDED (2026-01-25)**: Resume existing session automatically. This supports multi-day workflows where users want to pick up where they left off. Named sessions are explicitly for resumability.

2. **Cross-machine sessions** - Can `isRemote` sessions be resumed?
   - ✅ **DECIDED (2026-01-25)**: No - skip remote sessions silently in listings. Focus on local session management first; remote session handling deferred to future work.

3. **Session expiration** - Should sdqctl auto-cleanup very old sessions?
   - ✅ **DECIDED (2026-01-25)**: Two-pronged approach:
     - Add manual `sdqctl sessions cleanup --older-than 30d` command
     - Prompt user when sessions >30 days exist (during `sessions list`), offer cleanup
     - No silent auto-deletion; user always in control

---

## References

- [SDK Multiple Sessions Recipe](../../copilot-sdk/cookbook/python/multiple-sessions.md)
- [SDK Persisting Sessions Recipe](../../copilot-sdk/cookbook/python/persisting-sessions.md)
- [SDK Types - SessionMetadata](../../copilot-sdk/python/copilot/types.py)
