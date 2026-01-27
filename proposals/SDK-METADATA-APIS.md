# SDK Metadata APIs Integration

> **Status**: Implemented ✅  
> **Date**: 2026-01-24  
> **Updated**: 2026-01-25  
> **Priority**: P1 (Quick Win)  
> **Scope**: Status, auth, and model discovery APIs

---

## Executive Summary

The Copilot SDK v2 provides metadata APIs (`get_status`, `get_auth_status`, `list_models`) that can enhance sdqctl's `status` command and enable model capability filtering. This proposal outlines the integration.

---

## SDK APIs

### Get Status

```python
status = await client.get_status()
# Returns:
# {
#     "version": "0.0.394",
#     "protocolVersion": 2
# }
```

### Get Auth Status

```python
auth = await client.get_auth_status()
# Returns:
# {
#     "isAuthenticated": True,
#     "authType": "user",  # or "env", "gh-cli", "hmac", "api-key", "token"
#     "host": "github.com",
#     "login": "bewest",
#     "statusMessage": "Authenticated as bewest"
# }
```

### List Models

```python
models = await client.list_models()
# Returns list of ModelInfo:
# [
#     {
#         "id": "gpt-5",
#         "name": "GPT-5",
#         "capabilities": {
#             "supports": {"vision": True},
#             "limits": {
#                 "max_prompt_tokens": 128000,
#                 "max_context_window_tokens": 200000,
#                 "vision": {
#                     "supported_media_types": ["image/jpeg", "image/png"],
#                     "max_prompt_images": 10,
#                     "max_prompt_image_size": 20971520
#                 }
#             }
#         },
#         "policy": {"state": "enabled", "terms": "..."},
#         "billing": {"multiplier": 1.0}
#     },
#     ...
# ]
```

---

## Proposed Integration

### Enhanced Status Command

```bash
$ sdqctl status

sdqctl v0.2.0
─────────────────────────────────
Copilot CLI:    v0.0.394 (protocol v2)
Auth:           ✓ Authenticated as bewest (user)
Host:           github.com

Adapters:
  copilot       ✓ Available (default)
  mock          ✓ Available

Models:
  gpt-5              128K context  vision: ✓
  claude-sonnet-4.5  200K context  vision: ✓
  claude-haiku-4.5   200K context  vision: ✓
  claude-sonnet-4    200K context  vision: ✓

Sessions:       3 active (use --sessions for details)
```

### Detailed Options

```bash
# Show model details
sdqctl status --models

# Output:
# Models:
#   gpt-5
#     Context: 200,000 tokens (128,000 prompt max)
#     Vision:  ✓ (jpeg, png, gif, webp)
#     Policy:  enabled
#     Billing: 1.0x
#   
#   claude-sonnet-4.5
#     Context: 200,000 tokens
#     Vision:  ✓ (jpeg, png, gif, webp)
#     Policy:  enabled
#     Billing: 1.2x

# Show session list
sdqctl status --sessions

# Show all details
sdqctl status --all

# JSON output for scripting
sdqctl status --format json
```

### Model Discovery for Workflows

```bash
# List models supporting vision
sdqctl status --models --filter vision

# List models with large context
sdqctl status --models --filter "context>150000"
```

---

## Implementation

### Phase 1: Adapter Methods ✅ Complete (2026-01-24)

Added to `sdqctl/adapters/base.py`:
- `get_cli_status()` - Returns CLI version info (default: empty dict)
- `get_auth_status()` - Returns auth status (default: empty dict)
- `list_models()` - Returns model list (default: empty list)

Added to `sdqctl/adapters/copilot.py`:
- Full implementations calling SDK methods
- Error handling with logging

Added to `sdqctl/adapters/mock.py`:
- Mock implementations for testing

Added 4 tests in `tests/test_adapters.py::TestAdapterMetadataAPIs`

### Phase 2: Status Command Enhancement ✅ Complete (2026-01-24)

Implemented enhanced status command with adapter metadata display.

**New CLI Options:**
- `--models` - Show available models with context window and vision support
- `--auth` - Show authentication status
- `--all` - Show comprehensive status (adapters, models, auth, sessions)
- `-a/--adapter` - Specify which adapter to query (default: copilot)

**Usage Examples:**
```bash
# Default overview with CLI/auth status
sdqctl status

# Show available models
sdqctl status --models

# Show auth status details
sdqctl status --auth

# Show everything
sdqctl status --all

# JSON output for scripting
sdqctl status --json
```

**Implementation:**
- Updated `sdqctl/commands/status.py` with async metadata retrieval
- Added `_show_overview_async()`, `_show_models_async()`, `_show_auth_async()`, `_show_all_async()`
- 6 tests in `tests/test_cli.py::TestStatusCommand`

Previous sketch (superseded by actual implementation):

```python
# sdqctl/commands/status.py

@click.command()
@click.option("--models", is_flag=True, help="Show available models")
@click.option("--sessions", is_flag=True, help="Show active sessions")
@click.option("--all", "show_all", is_flag=True, help="Show all details")
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
async def status(models, sessions, show_all, format):
    """Show sdqctl and Copilot CLI status."""
    
    adapter = get_adapter()
    
    if format == "json":
        data = await collect_status_data(adapter, include_models=models or show_all,
                                         include_sessions=sessions or show_all)
        click.echo(json.dumps(data, indent=2))
        return
    
    # Header
    click.echo(f"sdqctl v{__version__}")
    click.echo("─" * 35)
    
    try:
        await adapter.start()
        
        # CLI status
        cli_status = await adapter.get_cli_status()
        click.echo(f"Copilot CLI:    v{cli_status['version']} (protocol v{cli_status['protocol_version']})")
        
        # Auth status
        auth = await adapter.get_auth_status()
        if auth["authenticated"]:
            click.echo(f"Auth:           ✓ Authenticated as {auth['login']} ({auth['auth_type']})")
        else:
            click.echo(f"Auth:           ✗ Not authenticated")
        
        if auth.get("host"):
            click.echo(f"Host:           {auth['host']}")
        
        click.echo()
        
        # Models
        if models or show_all:
            click.echo("Models:")
            model_list = await adapter.list_models()
            for m in model_list:
                context = f"{m['context_window']//1000}K" if m['context_window'] else "?"
                vision = "✓" if m['vision'] else "✗"
                click.echo(f"  {m['id']:20} {context} context  vision: {vision}")
            click.echo()
        
        # Sessions
        if sessions or show_all:
            click.echo("Sessions:")
            session_list = await adapter.list_sessions()
            if session_list:
                for s in session_list[:10]:  # Limit display
                    age = format_age(s["modified_time"])
                    click.echo(f"  {s['id'][:40]:40} modified: {age}")
                if len(session_list) > 10:
                    click.echo(f"  ... and {len(session_list) - 10} more")
            else:
                click.echo("  No active sessions")
            click.echo()
        
        # Adapters
        click.echo("Adapters:")
        for name, info in get_available_adapters().items():
            status_icon = "✓" if info["available"] else "✗"
            default = " (default)" if name == "copilot" else ""
            click.echo(f"  {name:14} {status_icon} {info['status']}{default}")
        
    finally:
        await adapter.stop()
```

### Phase 3: Model Requirements Integration

Connect to the `MODEL-REQUIREMENTS` proposal:

```python
# sdqctl/core/model_selector.py

async def select_model_by_requirements(
    adapter: AdapterBase,
    requirements: dict,
) -> str:
    """Select a model that meets requirements."""
    
    models = await adapter.list_models()
    
    for model in models:
        # Check vision requirement
        if requirements.get("vision") and not model["vision"]:
            continue
        
        # Check context requirement
        min_context = requirements.get("min_context", 0)
        if model["context_window"] and model["context_window"] < min_context:
            continue
        
        # Check policy (must be enabled)
        if model["policy_state"] != "enabled":
            continue
        
        return model["id"]
    
    raise ValueError("No model meets requirements")
```

Usage in ConversationFile:

```dockerfile
# Require vision support
MODEL-REQUIRES vision

# Require large context
MODEL-REQUIRES context>150000

# sdqctl selects appropriate model automatically
```

---

## Benefits

1. **Visibility** - Users can see CLI version, auth status, available models
2. **Debugging** - Quick check if Copilot is properly configured
3. **Model discovery** - See what models are available with capabilities
4. **Scripting** - JSON output for automation
5. **Model selection** - Future: automatic model selection by requirements

---

## Testing

```python
def test_get_cli_status():
    adapter = CopilotAdapter()
    await adapter.start()
    status = await adapter.get_cli_status()
    assert "version" in status
    assert "protocol_version" in status
    await adapter.stop()

def test_list_models():
    adapter = CopilotAdapter()
    await adapter.start()
    models = await adapter.list_models()
    assert len(models) > 0
    assert all("id" in m for m in models)
    await adapter.stop()
```

---

## Open Questions

1. **Caching** - Should model list be cached? How long?
2. **Offline mode** - What to show when CLI is unavailable?
3. **Policy visibility** - Should disabled models be shown?

---

## References

- [SDK Types - GetStatusResponse](../../copilot-sdk/python/copilot/types.py)
- [SDK Types - GetAuthStatusResponse](../../copilot-sdk/python/copilot/types.py)
- [SDK Types - ModelInfo](../../copilot-sdk/python/copilot/types.py)
- [MODEL-REQUIREMENTS Proposal](MODEL-REQUIREMENTS.md)
