# Adapter Configuration Guide

Adapters connect sdqctl to AI providers. This guide covers setup, authentication, and provider-specific options.

---

## Quick Reference

| Adapter | Package | Auth Method | Status |
|---------|---------|-------------|--------|
| `copilot` | `github-copilot-sdk` | GitHub OAuth / Token | ✅ Primary |
| `mock` | Built-in | None | ✅ Testing |
| `claude` | `anthropic` | API Key | 🔧 Planned |
| `openai` | `openai` | API Key | 🔧 Planned |

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
sdqctl cycle workflow.conv -n 10 --infinite-sessions
```

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

> **Status**: Planned - adapter interface defined but not yet implemented

### Expected Configuration

```bash
# Environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Usage
sdqctl run workflow.conv --adapter claude --model claude-3-opus
```

### ConversationFile

```dockerfile
ADAPTER claude
MODEL claude-3-sonnet-20240229
```

---

## openai (OpenAI GPT)

> **Status**: Planned - adapter interface defined but not yet implemented

### Expected Configuration

```bash
# Environment
export OPENAI_API_KEY="sk-..."

# Usage
sdqctl run workflow.conv --adapter openai --model gpt-4-turbo
```

### ConversationFile

```dockerfile
ADAPTER openai
MODEL gpt-4-turbo-preview
```

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

- [GETTING-STARTED.md](GETTING-STARTED.md) - Quick start guide
- [COMMANDS.md](COMMANDS.md) - CLI reference (`status --adapters`)
- [MODEL-REQUIREMENTS proposal](../proposals/MODEL-REQUIREMENTS.md) - Abstract model selection
