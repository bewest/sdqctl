# SDK Session Persistence Integration

> **Status**: In Progress (Phase 1 Complete)  
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

### Phase 2: Sessions Command Group

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

### Phase 3: Resume Command

```python
# sdqctl/commands/resume.py

@click.command()
@click.argument("session_id")
@click.option("--prompt", help="Additional prompt to send")
@click.option("--continue", "continue_file", type=click.Path(exists=True),
              help="Continue with remaining steps from workflow file")
async def resume(session_id, prompt, continue_file):
    """Resume a previous session."""
    adapter = get_adapter()
    await adapter.start()
    
    try:
        config = AdapterConfig(model="gpt-5")  # Could be from session metadata
        session = await adapter.resume_session(session_id, config)
        
        click.echo(f"Resumed session: {session_id}")
        
        if prompt:
            response = await adapter.send(session, prompt)
            click.echo(response)
        
        if continue_file:
            # Parse workflow, skip completed steps, run remaining
            # This would need checkpoint tracking
            pass
            
    finally:
        await adapter.stop()
```

### Phase 4: Named Sessions in Workflows

```python
# sdqctl/core/conversation.py

# Add directive
SESSION_NAME = "SESSION-NAME"

def parse_session_name(line: str) -> Optional[str]:
    """Parse SESSION-NAME directive."""
    if line.startswith("SESSION-NAME"):
        return line[len("SESSION-NAME"):].strip()
    return None
```

```python
# sdqctl/commands/run.py

# Use session name if specified
if conversation.session_name:
    session = await adapter.resume_session(conversation.session_name, config)
else:
    session = await adapter.create_session(config)
```

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

1. **Session naming conflicts** - What if session name already exists? (warn/error)
2. **Cross-machine sessions** - Can `isRemote` sessions be resumed? (Answer: Defer for now).
3. **Session expiration** - Should sdqctl auto-cleanup very old sessions? (Answer: Defer for now).

---

## References

- [SDK Multiple Sessions Recipe](../../copilot-sdk/cookbook/python/multiple-sessions.md)
- [SDK Persisting Sessions Recipe](../../copilot-sdk/cookbook/python/persisting-sessions.md)
- [SDK Types - SessionMetadata](../../copilot-sdk/python/copilot/types.py)
