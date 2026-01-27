# Adapter Configuration Guide

Adapters connect sdqctl to AI providers. This guide covers setup, authentication, and provider-specific options.

---

## Quick Reference

| Adapter | Package | Auth Method | Status |
|---------|---------|-------------|--------|
| `copilot` | `github-copilot-sdk` | GitHub OAuth / Token | ✅ Primary |
| `mock` | Built-in | None | ✅ Testing |
| `claude` | `anthropic` | API Key | 🔲 Stub (NotImplementedError) |
| `openai` | `openai` | API Key | 🔲 Stub (NotImplementedError) |

Check adapter availability:
```bash
sdqctl status --adapters
```

---

## copilot (GitHub Copilot SDK)

The primary adapter for production use. Uses the official GitHub Copilot SDK.

### Installation

```bash
pip install -e ".[copilot]"
# or
pip install github-copilot-sdk
```

### Authentication

The Copilot SDK uses GitHub's OAuth flow. Authentication is typically handled automatically when you have GitHub CLI configured:

```bash
# Option 1: GitHub CLI (recommended)
gh auth login --scopes "copilot"

# Option 2: Environment variable
export GH_TOKEN="your-github-token"
```

**Check authentication:**
```bash
sdqctl status --auth
```

### Usage

```bash
# CLI usage
sdqctl run workflow.conv --adapter copilot

# ConversationFile
ADAPTER copilot
MODEL gpt-4
```

### Features

| Feature | Support |
|---------|---------|
| Streaming | ✅ Yes |
| Tool use | ✅ Yes |
| Context compaction | ✅ Yes |
| Infinite sessions | ✅ Yes (SDK v2) |
| Session persistence | ✅ Yes (SDK v2) |

### Infinite Sessions (SDK v2)

Enable automatic context management:

```dockerfile
# ConversationFile
INFINITE-SESSIONS enabled
COMPACTION-THRESHOLD 80%
COMPACTION-MIN 30%
```

```bash
# CLI
sdqctl iterate workflow.conv -n 10 --infinite-sessions
```

### Session Observability

The Copilot adapter tracks session metrics for long-running operations:

**Quota Tracking** (from `assistant.usage` events):
- `quota_remaining` - Percentage of quota remaining (0-100)
- `quota_reset_date` - When quota resets (ISO timestamp)
- Automatic warning when quota drops below 20%

**Rate Limit Detection** (from `session.error` events):
- Detects HTTP 429 errors and rate limit messages
- `rate_limited` flag for programmatic handling
- User-friendly error messages

**Session Timing**:
- `session_start_time` - When session began
- `session_duration_seconds` - Elapsed time
- `requests_per_minute` - Average request rate

**Compaction Metrics**:
- `compaction_count` - Number of compactions
- `compaction_effectiveness` - Ratio (< 1.0 = good)
- `total_tokens_saved` - Cumulative tokens saved

Access metrics programmatically:
```python
stats = adapter.get_session_stats(session)
if stats.quota_remaining and stats.quota_remaining < 20:
    print(f"⚠️ Low quota: {stats.quota_remaining:.0f}%")
if stats.rate_limited:
    print(f"🛑 Rate limited: {stats.rate_limit_message}")
```

### Event Handler Architecture

The Copilot adapter uses `CopilotEventHandler` (in `adapters/events.py`) to process SDK events:

```python
from sdqctl.adapters.events import CopilotEventHandler
from sdqctl.adapters.stats import SessionStats

# Create handler with progress callback
stats = SessionStats()
handler = CopilotEventHandler(stats, progress_fn=print)

# Handler is registered once per session, reused across sends
copilot_session.on(handler.handle)
```

**Event types handled:**
| Category | Events |
|----------|--------|
| Session | `session.start`, `session.idle`, `session.error`, `session.truncation` |
| Turns | `assistant.turn_start`, `assistant.turn_end`, `assistant.intent` |
| Messages | `assistant.message`, `assistant.message_delta`, `assistant.reasoning` |
| Usage | `assistant.usage`, `session.usage_info` |
| Tools | `tool.execution_start`, `tool.execution_complete` |
| Compaction | `session.compaction_start`, `session.compaction_complete` |
| Control | `abort`, `session.handoff`, `session.model_change` |

---

## mock (Testing Adapter)

Built-in adapter for testing workflows without AI calls.

### Usage

```bash
# CLI - always available
sdqctl run workflow.conv --adapter mock

# With dry-run (no file writes)
sdqctl run workflow.conv --adapter mock --dry-run

# ConversationFile
ADAPTER mock
```

### Behavior

- Returns canned responses (cycles through 3 default responses)
- Simulates 0.1s delay per response
- Tracks token usage approximation
- No external dependencies

### Custom Responses (Programmatic)

```python
from sdqctl.adapters.mock import MockAdapter

adapter = MockAdapter(
    responses=["Custom response 1", "Custom response 2"],
    delay=0.5
)
```

---

## claude (Anthropic Claude)

> **Status**: Stub - adapter registered but methods raise `NotImplementedError`  
> **Contributions welcome**: Implement using `anthropic` Python SDK

### Installation

```bash
pip install anthropic
```

### Expected Configuration

```bash
# Environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Usage (after implementation)
sdqctl run workflow.conv --adapter claude --model claude-3-opus
```

### ConversationFile

```dockerfile
ADAPTER claude
MODEL claude-3-sonnet-20240229
```

### Available Models

The stub provides these model identifiers for future use:
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

---

## openai (OpenAI GPT)

> **Status**: Stub - adapter registered but methods raise `NotImplementedError`  
> **Contributions welcome**: Implement using `openai` Python SDK

### Installation

```bash
pip install openai
```

### Expected Configuration

```bash
# Environment
export OPENAI_API_KEY="sk-..."

# Usage (after implementation)
sdqctl run workflow.conv --adapter openai --model gpt-4-turbo
```

### ConversationFile

```dockerfile
ADAPTER openai
MODEL gpt-4-turbo-preview
```

### Available Models

The stub provides these model identifiers for future use:
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`
- `o1-preview`
- `o1-mini`

---

## Model Selection Guide

Choose the right model for your workflow based on task requirements, context needs, and cost.

### When to Use Each Model

| Model | Best For | Context | Cost | Notes |
|-------|----------|---------|------|-------|
| **gpt-4** | Complex reasoning, code generation | 8k-128k | $$$ | High accuracy, slower |
| **gpt-4-turbo** | Long documents, large codebases | 128k | $$ | Faster than gpt-4 |
| **claude-3-opus** | Deep analysis, nuanced writing | 200k | $$$ | Excellent reasoning |
| **claude-3-sonnet** | Balanced tasks, daily use | 200k | $$ | Good cost/performance |
| **claude-sonnet-4** | Tool use, code editing | 200k | $$ | Latest Sonnet |

### Practical Examples

**Code refactoring (moderate context)**
```dockerfile
MODEL gpt-4-turbo
# Good for: understanding codebase, making targeted edits
```

**Large codebase analysis (high context)**
```dockerfile
MODEL claude-3-opus
# Good for: reading 100+ files, producing comprehensive analysis
```

**Daily workflow automation (balanced)**
```dockerfile
MODEL claude-3-sonnet
# Good for: routine tasks, cost-effective automation
```

**Iteration-heavy synthesis (many turns)**
```dockerfile
MODEL claude-sonnet-4
INFINITE-SESSIONS enabled
# Good for: multi-cycle workflows that need context management
```

### Abstract Selection with MODEL-REQUIRES

Use requirements instead of hardcoding models for portable workflows:

```dockerfile
# Instead of hardcoding models:
MODEL gpt-4

# Use requirements-based selection:
MODEL-REQUIRES context:50k reasoning:strong
```

| Requirement | Description | Example Values |
|-------------|-------------|----------------|
| `context:` | Minimum context window | `50k`, `100k`, `200k` |
| `reasoning:` | Reasoning capability | `basic`, `strong` |
| `tools:` | Tool use support | `required`, `optional` |
| `vision:` | Image understanding | `required`, `optional` |

The adapter selects the best available model matching requirements.

### Decision Tree

```
What's your task?
├── Quick edit, simple fix → gpt-4-turbo or claude-3-sonnet
├── Large codebase (50k+ tokens) → claude-3-opus or MODEL-REQUIRES context:50k
├── Many iterations (10+ cycles) → claude-sonnet-4 + INFINITE-SESSIONS
├── Cost-sensitive automation → claude-3-sonnet or MODEL-PREFERS cost:low
└── Testing workflows → mock adapter (no AI cost)
```

### Model Preferences

When multiple models could work, use `MODEL-PREFERS` to express soft preferences:

```dockerfile
MODEL-REQUIRES context:50k reasoning:strong
MODEL-PREFERS cost:low latency:fast
```

The adapter will select a model that meets requirements while optimizing for preferences.

---

## Adapter Fallback

When an adapter is unavailable, sdqctl provides helpful errors:

```bash
$ sdqctl run workflow.conv --adapter claude
Error: Adapter 'claude' not available. 
Install with: pip install anthropic

Available adapters: copilot, mock
```

---

## Environment Variables Summary

| Variable | Adapter | Description |
|----------|---------|-------------|
| `GH_TOKEN` | copilot | GitHub personal access token |
| `GITHUB_TOKEN` | copilot | Alternative to GH_TOKEN |
| `ANTHROPIC_API_KEY` | claude | Anthropic API key |
| `OPENAI_API_KEY` | openai | OpenAI API key |

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Module structure and adapter extension guide
- [GETTING-STARTED.md](GETTING-STARTED.md) - Quick start guide
- [COMMANDS.md](COMMANDS.md) - CLI reference (`status --adapters`)
- [MODEL-REQUIREMENTS proposal](../proposals/MODEL-REQUIREMENTS.md) - Abstract model selection
