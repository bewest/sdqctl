# Proposal: Model Requirements - Abstract Model Selection

**Date:** 2026-01-23  
**Status:** Implemented (Phase 1-4 Complete)  
**Author:** Generated via sdqctl planning session  
**Related:** Metadata directives (MODEL, ADAPTER)

---

## Summary

This proposal introduces **abstract model selection** based on capability requirements rather than explicit model names. Authors and operators describe *what they need* (context window size, cost tier, latency), and the system resolves this to an appropriate concrete model.

```dockerfile
# Current: explicit model binding
MODEL claude-sonnet-4.5

# Proposed: requirement-based selection
MODEL-REQUIRES context:5k
MODEL-REQUIRES tier:standard
```

---

## Problem Statement

### Current State

The `MODEL` directive requires specifying a concrete model name:

```dockerfile
MODEL claude-sonnet-4.5
ADAPTER copilot
```

**Problems with explicit model binding:**

1. **Vendor lock-in** - Workflows hardcode specific models, breaking portability
2. **Deprecation fragility** - Models are deprecated/renamed regularly
3. **Operator inflexibility** - Operators cannot substitute equivalent models
4. **Over-specification** - Authors may not care about model, just capabilities
5. **Under-specification** - No way to express "needs 100k context" abstractly

### Motivating Use Cases

| Use Case | Current Approach | Pain Point |
|----------|------------------|------------|
| Simple refactoring workflow | `MODEL gpt-4.1` | Over-specified; any capable model would work |
| Large codebase analysis | `MODEL claude-opus-4` | Actually needs 100k+ context; opus happens to have it |
| Cost-sensitive batch job | `MODEL gpt-5-mini` | Wants "cheapest that works"; model names change |
| Safety-critical audit | `MODEL claude-sonnet-4.5` | Needs "best reasoning"; different orgs have different "best" |

---

## Proposed Solution

### New Directives

| Directive | Purpose | Example Values |
|-----------|---------|----------------|
| `MODEL-REQUIRES` | Specify a capability requirement | `context:5k`, `tier:standard`, `speed:fast` |
| `MODEL-PREFERS` | Soft preference (hint, not constraint) | `vendor:anthropic`, `family:claude` |
| `MODEL-POLICY` | Resolution strategy | `cheapest`, `fastest`, `best-fit`, `operator-default` |

### Capability Dimensions

#### 1. Context Window (`context:`)

Specify minimum context window needed for the workflow.

```dockerfile
MODEL-REQUIRES context:1k      # Minimal: fits a few files
MODEL-REQUIRES context:5k      # Standard: typical component analysis
MODEL-REQUIRES context:50k     # Large: multi-file refactoring
MODEL-REQUIRES context:100k    # Very large: codebase-wide analysis
```

**Resolution**: Select model with `context_window >= requirement`.

#### 2. Cost Tier (`tier:`)

Specify acceptable cost tier.

```dockerfile
MODEL-REQUIRES tier:economy    # Cheapest available (e.g., gpt-4.1, haiku)
MODEL-REQUIRES tier:standard   # Balanced cost/capability (e.g., sonnet, gpt-5)
MODEL-REQUIRES tier:premium    # Best available (e.g., opus, o1)
```

**Resolution**: Filter models by tier, then apply other requirements.

#### 3. Speed/Latency (`speed:`)

Specify latency requirements.

```dockerfile
MODEL-REQUIRES speed:fast       # Prioritize low latency (e.g., haiku, mini)
MODEL-REQUIRES speed:standard   # Default latency acceptable
MODEL-REQUIRES speed:deliberate # Extended thinking OK (e.g., o1, opus)
```

**Resolution**: Consider time-to-first-token and total latency.

#### 4. Capability Class (`capability:`)

Specify required capability level.

```dockerfile
MODEL-REQUIRES capability:code       # Code-optimized (e.g., codex models)
MODEL-REQUIRES capability:reasoning  # Strong reasoning (e.g., o1, opus)
MODEL-REQUIRES capability:general    # General purpose (default)
```

**Resolution**: Match model strengths to declared need.

### Soft Preferences

Preferences influence selection but don't constrain it:

```dockerfile
MODEL-PREFERS vendor:anthropic   # Prefer Anthropic models if available
MODEL-PREFERS vendor:openai      # Prefer OpenAI models
MODEL-PREFERS family:claude      # Prefer Claude family
MODEL-PREFERS family:gpt         # Prefer GPT family
```

### Resolution Policy

```dockerfile
MODEL-POLICY cheapest      # Among matching models, pick cheapest
MODEL-POLICY fastest       # Among matching models, pick fastest
MODEL-POLICY best-fit      # Balance all requirements (default)
MODEL-POLICY operator-default  # Defer entirely to operator configuration
```

### Full Example

```dockerfile
# Workflow for large codebase security audit
# Needs significant context, good reasoning, but cost-aware

MODEL-REQUIRES context:50k
MODEL-REQUIRES capability:reasoning
MODEL-REQUIRES tier:standard
MODEL-PREFERS vendor:anthropic
MODEL-POLICY best-fit

ADAPTER copilot
MODE audit
MAX-CYCLES 5

CONTEXT @src/**/*.py
PROMPT Analyze for security vulnerabilities...
```

---

## Design Questions

### Q1: Resolution Mechanism

**Who resolves abstract requirements to a concrete model?**

| Option | Pros | Cons |
|--------|------|------|
| **A: Adapter resolves** | Adapters know their available models; decentralized | Each adapter reimplements resolution logic |
| **B: sdqctl registry** | Centralized model database; consistent resolution | Requires maintaining model capability data |
| **C: Operator config** | Operators define their mappings; full control | Per-site configuration burden |
| **D: Hybrid** | sdqctl provides defaults, operators/adapters override | More complex but flexible |

**✅ DECIDED (2026-01-24): Adapter-first with hints**

Adapters implement `select_model(requirements: dict) -> str` to "right-size" model selection:

1. Workflow specifies preferences: `MODEL-REQUIRES context:50k speed:fast`
2. sdqctl passes requirements as hints to adapter
3. Adapter selects best-fit model from its available models
4. Fallback: use explicit `MODEL` if adapter can't satisfy requirements

```python
# Adapter interface
class AIAdapter:
    def select_model(self, requirements: dict[str, str]) -> str:
        """Select best model matching requirements. Returns model identifier."""
        # Default: return self.default_model
        # Copilot adapter: may delegate to backend
        ...
```

This approach keeps adapters in control while sdqctl provides a consistent interface.

### Q2: Compatibility with MODEL

**How do explicit MODEL and abstract MODEL-REQUIRES interact?**

| Option | Behavior |
|--------|----------|
| **A: MODEL wins** | If MODEL specified, ignore MODEL-REQUIRES entirely |
| **B: MODEL-REQUIRES wins** | Abstract requirements override explicit model |
| **C: Validation** | If both present, verify MODEL satisfies REQUIRES |
| **D: Error** | Cannot specify both; choose one pattern |

**Recommendation**: Option C - Allow both, validate compatibility. This enables:
```dockerfile
MODEL-REQUIRES context:50k      # Minimum requirement
MODEL claude-sonnet-4.5         # Specific choice (must satisfy requirement)
```

### Q3: Unknown Capability Handling

**What if a requirement cannot be satisfied?**

| Option | Behavior |
|--------|----------|
| **A: Fail fast** | Error at parse/load time |
| **B: Warn + fallback** | Warning, select closest match |
| **C: Operator fallback** | Defer to operator-configured default |

**Recommendation**: Option A for hard requirements (`MODEL-REQUIRES`), Option B for preferences (`MODEL-PREFERS`).

### Q4: Capability Discovery

**How do workflows/operators discover available capabilities?**

```bash
# Potential CLI commands
sdqctl status --models                  # List available models
sdqctl status --models --capabilities   # Show model capabilities
sdqctl validate workflow.conv --check-model  # Verify model requirements satisfiable
```

### Q5: Runtime vs Parse-time Resolution

**When is the concrete model selected?**

| Option | Timing | Implications |
|--------|--------|--------------|
| **A: Parse-time** | When .conv loaded | Model baked into workflow; deterministic |
| **B: Runtime** | At first API call | Can adapt to availability; less reproducible |
| **C: Configurable** | `--resolve-model=parse\|runtime` | Flexibility with explicit control |

**Recommendation**: Option A (parse-time) for reproducibility, with `--resolve-model=runtime` override.

---

## Implementation Considerations

### Capability Registry

A model capability registry mapping model IDs to capabilities:

```python
MODEL_CAPABILITIES = {
    "claude-sonnet-4.5": {
        "context_window": 200_000,
        "tier": "standard",
        "speed": "standard",
        "capability": "general",
        "vendor": "anthropic",
        "family": "claude",
    },
    "gpt-5-mini": {
        "context_window": 128_000,
        "tier": "economy",
        "speed": "fast",
        "capability": "general",
        "vendor": "openai",
        "family": "gpt",
    },
    # ...
}
```

**Maintenance concern**: This registry needs updates as models evolve.

### Adapter Integration

Adapters could provide their own capability data:

```python
class CopilotAdapter:
    def get_available_models(self) -> list[ModelInfo]:
        """Return models available through this adapter."""
        ...
    
    def resolve_requirements(self, reqs: ModelRequirements) -> str:
        """Select best model matching requirements."""
        ...
```

### Operator Configuration

Operators could configure default policies:

```yaml
# ~/.config/sdqctl/models.yaml
default_policy: cheapest
tier_overrides:
  standard: claude-sonnet-4.5  # Pin "standard" to specific model
  economy: gpt-4.1
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Registry goes stale | Wrong model selected | Version registry with sdqctl; allow adapter override |
| Adapter has limited models | Can't satisfy requirements | Clear error messages; operator fallback config |
| Over-abstraction | Users confused | Keep MODEL for explicit cases; REQUIRES is opt-in |
| Non-determinism | Workflow behaves differently | Parse-time resolution default; resolved model logged |

---

## Alternatives Considered

### Alternative A: Just Use MODEL

Keep explicit model names only.

**Pros**: Simple, deterministic  
**Cons**: Portability issues, deprecation fragility

### Alternative B: MODEL with Fallbacks

```dockerfile
MODEL claude-sonnet-4.5 | gpt-5 | gemini-2
```

**Pros**: Simple syntax, explicit fallback order  
**Cons**: Still hardcodes specific models; combinatorial fallback chains

### Alternative C: Tags on MODEL

```dockerfile
MODEL @reasoning @100k-context
```

**Pros**: Concise syntax  
**Cons**: Tag semantics unclear; mixing concrete and abstract

---

## Phased Implementation

### Phase 0: Discussion ✅ (2026-01-25)

- [x] Decide on Q1-Q5 design questions
- [x] Validate use cases with operators/authors
- [x] Finalize directive syntax

### Phase 1: Core Registry ✅ (2026-01-25)

- [x] Create `sdqctl/core/models.py` with capability registry
- [x] Add `MODEL-REQUIRES` directive parsing
- [x] Add `MODEL-PREFERS` directive parsing
- [x] Add `MODEL-POLICY` directive parsing
- [x] Implement basic resolution logic
- [x] Tests: 24 new tests passing

### Phase 2: CLI Integration

- [x] Add `sdqctl status --models` command (already existed)
- [x] Add `sdqctl validate --check-model` flag
- [x] Resolved model appears in validate output
- [x] Tests: 2 CLI integration tests added

### Phase 3: Adapter Integration ✅ (2026-01-25)

- [x] Define adapter `get_available_models()` protocol
- [x] Adapter-specific capability data
- [x] Fallback to sdqctl registry if adapter doesn't provide
- [x] Tests: 3 adapter integration tests added

### Phase 4: Operator Configuration ✅ (2026-01-25)

- [x] `~/.config/sdqctl/models.yaml` support
- [x] Environment variable overrides (`SDQCTL_MODEL_DEFAULT`, `SDQCTL_MODEL_ALIAS_*`)
- [x] `get_operator_default_model()`, `resolve_model_alias()`, `get_operator_models()`
- [x] `get_effective_capabilities()` merges built-in + operator models
- [x] Tests: 7 new operator config tests (36 total model tests)

---

## Open Questions for Discussion

1. **Syntax**: Is `MODEL-REQUIRES key:value` the right syntax, or would `MODEL context>=50k tier=standard` be clearer?
   - ✅ **DECIDED (2026-01-25)**: Use colon syntax `MODEL-REQUIRES key:value`. More Dockerfile-like, one requirement per line.

2. **Scope**: Should this cover *all* model selection concerns, or just the common ones (context, cost, speed)?
   - ✅ **DECIDED (2026-01-25)**: Full coverage from the start. Include context, tier, speed, capability, vendor, family.

3. **Defaults**: Should workflows without MODEL or MODEL-REQUIRES get a default? What default?
   - ✅ **DECIDED (2026-01-25)**: Default to adapter's default model. No error for missing MODEL.

4. **Verification**: Should `sdqctl verify` check that resolved models actually have claimed capabilities (e.g., by testing context limits)?
   - ✅ **DECIDED (2026-01-25)**: Defer. Trust registry/adapter for now. Revisit when we have real usage data.

5. **Dynamic Requirements**: Should context requirements be computable from CONTEXT directives? E.g., "context window must fit all CONTEXT files"?
   - ✅ **DECIDED (2026-01-25)**: No. Keep requirements explicit. Author knows their workflow needs.

---

## References

- Current implementation: `sdqctl/core/conversation.py` lines 27, 657-658
- MODEL directive documentation: `sdqctl help directives`
- Related: ADAPTER resolution (already adapter-specific)
