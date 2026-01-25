# SDK Infinite Sessions Integration

> **Status**: ✅ Complete (Phase 1-4)  
> **Date**: 2026-01-24  
> **Updated**: 2026-01-25  
> **Priority**: P1 (High Impact)  
> **Scope**: Native SDK compaction for cycle mode  
> **SDK Available**: ✅ Yes - `../../copilot-sdk/python` (Protocol Version 2)

---

## Executive Summary

The Copilot SDK v2 introduces **Infinite Sessions** with native background compaction. This proposal outlines how to integrate this capability into sdqctl's `iterate` command, replacing the current client-side compaction approach with SDK-managed context window management.

---

## Problem Statement

### Current State

sdqctl implements **client-side compaction** via session reset:

```python
async def compact_with_session_reset(...):
    # 1. Get summary via /compact command
    summary = await self.send(session, "/compact ...")
    
    # 2. Destroy old session
    await self.destroy_session(session)
    
    # 3. Create new session with summary
    new_session = await self.create_session(config)
    await self.send(new_session, compacted_context)
    
    return new_session, CompactionResult(...)
```

**Limitations:**
- Extra API round-trip for session creation
- Summary injection as user message (not native context)
- Session ID changes mid-workflow
- No background compaction (blocking)
- Complex prologue/epilogue handling

### SDK Native Solution

The SDK now provides automatic context management:

```python
session = await client.create_session({
    "model": "gpt-5",
    "infinite_sessions": {
        "enabled": True,
        "background_compaction_threshold": 0.80,
        "buffer_exhaustion_threshold": 0.95,
    },
})
```

---

## Proposed Integration

### Default Cycle Mode Behavior

For `sdqctl iterate`, infinite sessions should be the default with intelligent threshold handling:

```
MIN_COMPACTION_DENSITY (default: 30%)
├─ If context < 30% → Skip compaction (not worth it)
│
BACKGROUND_THRESHOLD (SDK default: 80%)
├─ If context 30-80% → Normal operation
├─ If context > 80% → SDK starts background compaction
│
BUFFER_EXHAUSTION_THRESHOLD (SDK default: 95%)
└─ If context > 95% → SDK blocks until compaction complete
```

### Configuration Mapping

| sdqctl Directive/Option | SDK Parameter | Notes |
|------------------------|---------------|-------|
| `--min-compaction-density N` | (client logic) | Skip compaction if < N% |
| `--compaction-threshold N` | `background_compaction_threshold` | Start background compact |
| `--max-context N` | `buffer_exhaustion_threshold` | Block threshold |
| `COMPACT` directive | Force immediate compaction | Override auto behavior |

### New Directives

```dockerfile
# Enable/disable infinite sessions (default: enabled in cycle mode)
INFINITE-SESSIONS enabled|disabled

# Set thresholds
COMPACTION-MIN 30          # Skip if context < 30%
COMPACTION-THRESHOLD 80    # Background compact at 80%
COMPACTION-MAX 95          # Block at 95%
```

### CLI Options

```bash
# Use infinite sessions (default for cycle)
sdqctl iterate workflow.conv -n 10

# Disable infinite sessions (use client-side compaction)
sdqctl iterate workflow.conv -n 10 --no-infinite-sessions

# Custom thresholds
sdqctl iterate workflow.conv -n 10 \
    --min-compaction-density 25 \
    --compaction-threshold 75 \
    --max-context 90

# Override session mode (fresh = no compaction, new session each cycle)
sdqctl iterate workflow.conv -n 10 --session-mode fresh
```

---

## Implementation

### Phase 1: Adapter Configuration

Update `CopilotAdapter` to pass infinite session config:

```python
# sdqctl/adapters/copilot.py

@dataclass
class InfiniteSessionConfig:
    """Configuration for SDK infinite sessions."""
    enabled: bool = True
    min_compaction_density: float = 0.30  # Skip if below this
    background_threshold: float = 0.80     # Start background compact
    buffer_exhaustion: float = 0.95        # Block until complete

async def create_session(self, config: AdapterConfig) -> AdapterSession:
    """Create session with infinite sessions support."""
    
    # Extract infinite session config from AdapterConfig
    infinite_config = config.extra.get("infinite_sessions", InfiniteSessionConfig())
    
    session_config = {
        "model": config.model,
        "streaming": config.streaming,
    }
    
    if infinite_config.enabled:
        session_config["infinite_sessions"] = {
            "enabled": True,
            "background_compaction_threshold": infinite_config.background_threshold,
            "buffer_exhaustion_threshold": infinite_config.buffer_exhaustion,
        }
    else:
        session_config["infinite_sessions"] = {"enabled": False}
    
    session = await self._client.create_session(session_config)
    
    # Capture workspace path for session artifacts
    workspace_path = getattr(session, "workspace_path", None)
    
    return AdapterSession(
        id=session.session_id,
        adapter=self,
        config=config,
        _internal=session,
        workspace_path=workspace_path,
    )
```

### Phase 2: Compaction Event Handling

Monitor SDK compaction events:

```python
# In event handler
elif event_type == "session.compaction_start":
    logger.info("🗜️ Background compaction started")
    stats.compaction_in_progress = True
    if event_collector:
        event_collector.add(event_type, data, stats.turns)

elif event_type == "session.compaction_complete":
    tokens_before = _get_field(data, "tokens_before", default=0)
    tokens_after = _get_field(data, "tokens_after", default=0)
    tokens_removed = tokens_before - tokens_after
    
    logger.info(f"🗜️ Compaction complete: {tokens_before:,} → {tokens_after:,} "
                f"(freed {tokens_removed:,} tokens)")
    
    stats.compaction_in_progress = False
    stats.compaction_count += 1
    stats.tokens_compacted += tokens_removed
    
    if event_collector:
        event_collector.add(event_type, data, stats.turns)
```

### Phase 3: Cycle Mode Integration

Update cycle command to use infinite sessions by default:

```python
# sdqctl/commands/iterate.py

@click.option(
    "--no-infinite-sessions",
    is_flag=True,
    help="Disable SDK infinite sessions (use client-side compaction)",
)
@click.option(
    "--min-compaction-density",
    type=int,
    default=30,
    help="Skip compaction if context usage below this percentage (default: 30)",
)
@click.option(
    "--compaction-threshold",
    type=int,
    default=80,
    help="Start background compaction at this percentage (default: 80)",
)
async def cycle(..., no_infinite_sessions, min_compaction_density, compaction_threshold):
    """Run workflow in synthesis cycles."""
    
    # Configure infinite sessions
    infinite_config = InfiniteSessionConfig(
        enabled=not no_infinite_sessions,
        min_compaction_density=min_compaction_density / 100.0,
        background_threshold=compaction_threshold / 100.0,
    )
    
    config = AdapterConfig(
        model=model,
        extra={"infinite_sessions": infinite_config},
    )
    
    # ... rest of cycle logic
```

### Phase 4: Smart COMPACT Directive

When `COMPACT` directive is encountered:

```python
async def handle_compact_directive(session, config, min_density):
    """Handle explicit COMPACT directive with threshold check."""
    
    used, max_tokens = await adapter.get_context_usage(session)
    density = used / max_tokens if max_tokens > 0 else 0
    
    if density < min_density:
        logger.info(f"⏭️ Skipping compaction (context {density:.0%} < {min_density:.0%} threshold)")
        return session, None
    
    if config.infinite_sessions.enabled:
        # With infinite sessions, just let SDK handle it
        # Send a prompt that might trigger compaction if near threshold
        logger.info(f"🗜️ Compaction requested (context at {density:.0%})")
        # SDK will compact in background if above threshold
        return session, CompactionResult(summary="SDK-managed", ...)
    else:
        # Fall back to client-side compaction
        return await adapter.compact_with_session_reset(session, config, ...)
```

---

## Session Mode Interactions

| Session Mode | Infinite Sessions | Behavior |
|-------------|-------------------|----------|
| `accumulate` | enabled (default) | Context grows, SDK auto-compacts at threshold |
| `accumulate` | disabled | Context grows, manual `COMPACT` required |
| `fresh` | N/A | New session each cycle, no compaction needed |
| `compact` | enabled | SDK compacts + explicit `COMPACT` directives |

---

## Configuration Precedence

1. CLI options (highest priority)
2. ConversationFile directives
3. Workflow defaults
4. Adapter defaults (lowest priority)

```dockerfile
# ConversationFile overrides
INFINITE-SESSIONS enabled
COMPACTION-MIN 25
COMPACTION-THRESHOLD 70

# CLI can still override
# sdqctl iterate workflow.conv --compaction-threshold 85
```

---

## Benefits

1. **Simpler code** - Remove client-side compaction logic
2. **Consistent session** - No mid-workflow session ID changes
3. **Background operation** - Non-blocking compaction
4. **Native context handling** - SDK manages message history properly
5. **Workspace persistence** - Session artifacts in `workspace_path`

---

## Migration Path

### Backward Compatibility

- Client-side compaction remains available via `--no-infinite-sessions`
- Existing `COMPACT` directives continue to work
- `COMPACT-PROLOGUE` and `COMPACT-EPILOGUE` only used in client-side mode

### Deprecation Timeline

1. **v0.2.0**: Infinite sessions as default for cycle mode
2. **v0.3.0**: Deprecation warning for client-side compaction options
3. **v0.4.0**: Remove client-side compaction (optional)

---

## Testing

### Unit Tests

```python
def test_infinite_session_config_parsing():
    """Test directive parsing for infinite sessions."""
    conv = parse_conversation("""
        INFINITE-SESSIONS enabled
        COMPACTION-MIN 25
        COMPACTION-THRESHOLD 75
    """)
    assert conv.infinite_sessions.enabled is True
    assert conv.infinite_sessions.min_density == 0.25
    assert conv.infinite_sessions.background_threshold == 0.75

def test_compaction_skip_below_threshold():
    """Test that compaction is skipped when context is low."""
    # Setup session at 20% context
    # Trigger COMPACT directive
    # Verify compaction was skipped
```

### Integration Tests

```bash
# Test infinite sessions with many cycles
sdqctl iterate tests/fixtures/long-workflow.conv -n 20 -v

# Verify compaction events in log
grep "compaction" output.log
```

---

## Open Questions

1. **Workspace path usage** - Should sdqctl use `session.workspace_path` for artifacts?
  * ANSWER: from the AUTHORS: Unclear what this is blocking or impacting?
2. **Compaction visibility** - How verbose should compaction event logging be?
  * ANSWER: From the AUTHORS: with -vvv I want to be able to see when it's skipped (current), when it's triggered, and when it's started and ended.  I'd like to also be able to see the workflow/cycle/prompt/turn info.
3. **Threshold tuning** - Are 30%/80%/95% good defaults for most workflows?  Yes 30/85 is good by default, I think.

---

## References

- [Copilot SDK README - Infinite Sessions](../../copilot-sdk/python/README.md#infinite-sessions)
- [SDK Types - InfiniteSessionConfig](../../copilot-sdk/python/copilot/types.py)
- [Current Compaction Implementation](../sdqctl/adapters/copilot.py#L766)
- [Context Management Guide](../docs/CONTEXT-MANAGEMENT.md)

---

## Implementation Status (2026-01-25)

### Phase 1: Adapter Configuration ✅

| Component | Status | Location |
|-----------|--------|----------|
| `InfiniteSessionConfig` dataclass | ✅ Complete | `sdqctl/adapters/base.py` |
| SDK integration in `create_session()` | ✅ Complete | `sdqctl/adapters/copilot.py` |
| `AdapterConfig.infinite_sessions` field | ✅ Complete | `sdqctl/adapters/base.py` |

### Phase 2: CLI Options ✅

| Option | Status | Location |
|--------|--------|----------|
| `--no-infinite-sessions` flag | ✅ Complete | `sdqctl/commands/iterate.py` |
| `--compaction-threshold N` | ✅ Complete | `sdqctl/commands/iterate.py` |
| `--min-compaction-density N` | ✅ Complete | `sdqctl/commands/iterate.py` |
| `--buffer-threshold N` | ✅ Complete | `sdqctl/commands/iterate.py` |

### Phase 3: Cycle Mode Integration ✅

| Feature | Status | Notes |
|---------|--------|-------|
| CLI→AdapterConfig wiring | ✅ Complete | All 3 session creation points updated |
| `_cycle_async` integration | ✅ Complete | Uses `build_infinite_session_config()` |
| `_cycle_from_json_async` integration | ✅ Complete | Params added to function signature |
| `build_infinite_session_config()` helper | ✅ Complete | Converts CLI options to config |

### Phase 4: Smart COMPACT Directive ✅ Complete

| Feature | Status | Notes |
|---------|--------|-------|
| `INFINITE-SESSIONS` directive | ✅ Complete | `conversation.py`, enabled/disabled values |
| `COMPACTION-MIN` directive | ✅ Complete | `conversation.py`, 0-100 or 0%-100% |
| `COMPACTION-THRESHOLD` directive | ✅ Complete | `conversation.py`, 0-100 or 0%-100% |
| CLI + conv file priority | ✅ Complete | CLI options override conv file directives |
| Unit tests | ✅ Complete | 4 tests in `test_conversation.py` |

**Implementation (2026-01-25):**
- `DirectiveType.INFINITE_SESSIONS`, `COMPACTION_MIN`, `COMPACTION_THRESHOLD` added
- `ConversationFile.infinite_sessions`, `compaction_min`, `compaction_threshold` fields
- `apply_directive()` parses enabled/disabled and percentage values
- `to_string()` serializes directives for round-trip
- `build_infinite_session_config()` merges CLI options with conv file values
- Priority: CLI flags > ConversationFile directives > adapter defaults

### Tests

All 130 conversation tests pass including 4 new tests for infinite session directives.
