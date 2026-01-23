# Proposal: Pipeline Architecture for Workflow Composition

> **Status**: Draft / Discussion  
> **Date**: 2026-01-23  
> **Author**: sdqctl development  
> **Scope**: Round-trip JSON workflows, external transformation, stdin execution

---

## Problem Statement

sdqctl can **export** fully-rendered workflows as JSON via `sdqctl render --json`, but cannot **import** transformed JSON back for execution. This prevents powerful composition patterns:

```bash
# Currently impossible:
sdqctl render cycle workflow.conv --json \
  | jsonnet transform.jsonnet \
  | sdqctl cycle --from-json -
```

**Use cases blocked by this limitation:**

1. **Conditional workflow selection**: Choose different prompts based on external state
2. **Dynamic context injection**: Add/remove context files based on analysis
3. **Workflow templating**: Generate variations of a base workflow
4. **CI/CD integration**: Modify workflows based on pipeline variables
5. **Testing**: Validate transformed workflows without execution

---

## Design Philosophy

### When to Use Each Pattern

sdqctl supports multiple patterns for adaptive workflows. Each serves a different purpose:

| Pattern | Timing | Who Decides | Complexity | Best For |
|---------|--------|-------------|------------|----------|
| **Synthesis cycles** | Cross-session | AI (via state files) | Low | Incremental progress |
| **RUN branching** | Runtime | ConversationFile | Medium | Error recovery, retries |
| **External pipeline** | Pre-execution | External tool | High | Workflow composition |
| **ELIDE chains** | Single turn | N/A (efficiency) | Low | Token optimization |

### Decision Tree

```
Need to adapt workflow behavior?
│
├─ Based on previous session results?
│   └─ Use SYNTHESIS CYCLE (state files + prompts)
│
├─ Based on command failure at runtime?
│   └─ Use RUN BRANCHING (ON-FAILURE, RUN-RETRY)
│
├─ Based on external data before execution?
│   └─ Use EXTERNAL PIPELINE (render → transform → execute)
│
└─ Just want fewer agent turns?
    └─ Use ELIDE (merge adjacent steps)
```

---

## Proposed Solution

### New CLI Capability: Stdin Input

Add `--from-json` flag to execution commands:

```bash
# Read workflow definition from stdin
sdqctl cycle --from-json -

# Read from file
sdqctl cycle --from-json rendered.json

# Full pipeline
sdqctl render cycle workflow.conv --json \
  | jq '.cycles[0].prompts += [{"raw": "Additional prompt"}]' \
  | sdqctl cycle --from-json -
```

### JSON Schema for Round-Trip

The existing `format_rendered_json()` output becomes the canonical schema:

```json
{
  "workflow": "path/to/workflow.conv",
  "workflow_name": "workflow",
  "mode": "full",
  "session_mode": "accumulate",
  "adapter": "copilot",
  "model": "gpt-4",
  "max_cycles": 3,
  "template_variables": {
    "DATE": "2026-01-23",
    "GIT_BRANCH": "main"
  },
  "cycles": [
    {
      "number": 1,
      "variables": {"CYCLE_NUMBER": "1"},
      "context_files": [
        {"path": "lib/auth.js", "content": "...", "tokens_estimate": 500}
      ],
      "prompts": [
        {
          "index": 1,
          "raw": "Original prompt text",
          "prologues": ["Prologue content"],
          "epilogues": ["Epilogue content"],
          "resolved": "Full assembled prompt"
        }
      ]
    }
  ]
}
```

### Schema Stability Guarantee

For pipeline consumers, we guarantee:

| Field | Stability | Notes |
|-------|-----------|-------|
| `cycles[].prompts[].resolved` | **Stable** | Primary execution input |
| `cycles[].prompts[].raw` | Stable | Original before expansion |
| `cycles[].context_files[].path` | Stable | File identification |
| `cycles[].context_files[].content` | Stable | File contents |
| `adapter`, `model` | Stable | Execution parameters |
| `template_variables` | Stable | Available for transforms |
| Internal fields | Unstable | May change between versions |

---

## Example: Jsonnet Transformation

### Use Case: Environment-Specific Prompts

```jsonnet
// transform.jsonnet
local workflow = std.parseJson(std.extVar('workflow'));
local env = std.extVar('environment');  // "staging" or "production"

local addEnvironmentContext(prompt) = prompt + {
  resolved: |||
    Environment: %(env)s
    
    %(original)s
  ||| % {env: env, original: prompt.resolved}
};

workflow + {
  cycles: [
    cycle + {
      prompts: [addEnvironmentContext(p) for p in cycle.prompts]
    }
    for cycle in workflow.cycles
  ]
}
```

```bash
sdqctl render cycle deploy.conv --json \
  | jsonnet --ext-str environment=staging transform.jsonnet \
  | sdqctl cycle --from-json -
```

### Use Case: Conditional Cycle Skipping

```jsonnet
// skip-if-tests-pass.jsonnet
local workflow = std.parseJson(std.extVar('workflow'));
local testsPassed = std.extVar('tests_passed') == 'true';

if testsPassed then
  workflow + {
    cycles: [workflow.cycles[0]]  // Skip fix cycles, just deploy
  }
else
  workflow  // Run full workflow including fix cycles
```

### Use Case: Merge Multiple Workflows

```jsonnet
// merge-workflows.jsonnet
local audit = std.parseJson(std.extVar('audit'));
local fix = std.parseJson(std.extVar('fix'));

audit + {
  cycles: audit.cycles + fix.cycles,
  max_cycles: std.length(audit.cycles) + std.length(fix.cycles)
}
```

```bash
sdqctl render cycle audit.conv --json > /tmp/audit.json
sdqctl render cycle fix.conv --json > /tmp/fix.json
jsonnet --ext-code-file audit=/tmp/audit.json \
        --ext-code-file fix=/tmp/fix.json \
        merge-workflows.jsonnet \
  | sdqctl cycle --from-json -
```

---

## Comparison: Pipeline vs RUN Branching

### Scenario: Run Tests, Fix if Failing

**Pipeline Approach** (decide before execution):

```bash
#!/bin/bash
pytest -v > /tmp/test-output.txt 2>&1
if [ $? -eq 0 ]; then
  sdqctl run deploy.conv
else
  sdqctl render cycle fix-tests.conv --json \
    | jq --rawfile output /tmp/test-output.txt \
         '.cycles[0].prompts[0].resolved += "\n\nTest output:\n" + $output' \
    | sdqctl cycle --from-json -
fi
```

**RUN Branching Approach** (decide at runtime):

```dockerfile
# fix-and-deploy.conv
RUN pytest -v
ON-FAILURE
  PROMPT Analyze test failures and fix them.
  RUN pytest -v
ON-SUCCESS
  PROMPT Deploy the application.
```

**Comparison:**

| Aspect | Pipeline | RUN Branching |
|--------|----------|---------------|
| Shell logic | Full bash/Python | ConversationFile only |
| AI participation | None in decision | AI can influence via prompts |
| Debugging | External logs | Integrated session |
| Composability | High (Unix pipes) | Medium (single file) |
| Learning curve | Higher | Lower |

**Recommendation**: Use pipeline for **complex orchestration**; use RUN branching for **simple error recovery**.

---

## Implementation Plan

### Phase 1: Schema Documentation

1. Document JSON schema in `docs/PIPELINE-SCHEMA.md`
2. Add schema version field for future compatibility
3. Define stable vs unstable fields

### Phase 2: Stdin Input Support

Add to `cycle.py`:

```python
@click.option("--from-json", "from_json", type=click.Path(), 
              help="Read workflow from JSON file or - for stdin")
def cycle(workflow, from_json, ...):
    if from_json:
        if from_json == "-":
            data = json.load(sys.stdin)
        else:
            data = json.loads(Path(from_json).read_text())
        conv = ConversationFile.from_rendered_json(data)
    else:
        conv = ConversationFile.from_file(Path(workflow))
    # ... rest of execution
```

### Phase 3: ConversationFile.from_rendered_json()

Add to `conversation.py`:

```python
@classmethod
def from_rendered_json(cls, data: dict) -> "ConversationFile":
    """Reconstruct ConversationFile from rendered JSON.
    
    Uses resolved prompts directly (no re-expansion needed).
    """
    conv = cls()
    conv.adapter = data.get("adapter", "copilot")
    conv.model = data.get("model", "gpt-4")
    conv.max_cycles = data.get("max_cycles", 1)
    
    # Extract prompts from cycles
    for cycle in data.get("cycles", []):
        for prompt in cycle.get("prompts", []):
            # Use resolved (fully expanded) prompt
            conv.prompts.append(prompt.get("resolved", prompt.get("raw", "")))
    
    # Context is already resolved - store for injection
    conv._preloaded_context = data.get("cycles", [{}])[0].get("context_files", [])
    
    return conv
```

### Phase 4: Validation Command

```bash
# Validate JSON without executing
sdqctl validate --from-json workflow.json

# Check schema version compatibility
sdqctl validate --from-json workflow.json --strict
```

---

## Open Questions

### 1. Schema Versioning

Should we add explicit schema version?

```json
{
  "schema_version": "1.0",
  "workflow": "...",
  ...
}
```

**Recommendation**: Yes, add version field for forward compatibility.

### 2. Partial Round-Trip

Can we modify only some fields and preserve others?

```bash
# Only change prompts, keep context
sdqctl render cycle workflow.conv --json \
  | jq '.cycles[0].prompts[0].resolved = "New prompt"' \
  | sdqctl cycle --from-json -
```

**Recommendation**: Yes, support partial updates. Missing fields use defaults.

### 3. Context File Re-resolution

If `context_files[].content` is modified, should we:
- A) Use modified content directly
- B) Re-read from `context_files[].path`
- C) Error if content doesn't match path

**Recommendation**: Option A (use provided content). This enables synthetic context injection.

### 4. Dry-Run Mode

Should `--from-json` support `--dry-run`?

```bash
sdqctl cycle --from-json workflow.json --dry-run
# Output: Would execute 3 cycles with 2 prompts each
```

**Recommendation**: Yes, useful for validation pipelines.

---

## Security Considerations

### Untrusted JSON Input

When accepting JSON from stdin, consider:

1. **Size limits**: Reject unreasonably large inputs
2. **Path traversal**: Validate `context_files[].path` doesn't escape sandbox
3. **Command injection**: `RUN` commands in prompts execute with user privileges

**Mitigation**: Add `--trust-input` flag required for stdin from untrusted sources.

---

## Related Proposals

- [RUN-BRANCHING.md](./RUN-BRANCHING.md) - Runtime conditional execution
- [VERIFICATION-DIRECTIVES.md](./VERIFICATION-DIRECTIVES.md) - Verification output in pipelines

---

## References

- [Jsonnet language](https://jsonnet.org/) - Data templating language
- [jq manual](https://stedolan.github.io/jq/manual/) - JSON processor
- [Unix pipeline philosophy](https://en.wikipedia.org/wiki/Pipeline_(Unix)) - Composable tools
- `sdqctl render --json` - Current export implementation
- `docs/IO-ARCHITECTURE.md` - Stream separation patterns

---

**Feedback requested.** Is external pipeline composition valuable enough to implement? Or should RUN branching cover most use cases?
