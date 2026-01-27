# Agentic Analysis Proposal

> **Status**: Proposal (R&D)  
> **Priority**: P3 (Future)  
> **Effort**: High  
> **Source**: Nightscout ecosystem alignment requirements

## Summary

Add autonomous analysis capabilities to sdqctl that can run multi-cycle deep dives with automatic context management and documentation updates.

## Proposed Commands

### `sdqctl agent analyze <topic>`

Autonomous multi-cycle analysis that:
1. Explores the topic across relevant repositories
2. Compacts context as needed
3. Updates all 5 facets automatically
4. Escalates unclear decisions to OPEN-QUESTIONS.md

```bash
# Run autonomous deep-dive on treatment sync
sdqctl agent analyze "treatment synchronization" \
  --repos "Loop,AAPS,Trio,Nightscout" \
  --max-cycles 10 \
  --output docs/10-domain/treatment-sync-deep-dive.md

# Analyze with scope constraints
sdqctl agent analyze "bolus commands" \
  --scope "remote commands only" \
  --max-tokens 100000
```

### Behavior

```
Cycle 1: Survey repositories for relevant files
Cycle 2: Extract key data structures and APIs
Cycle 3: Compare implementations
Cycle 4: Identify gaps and inconsistencies
Cycle 5: Update terminology matrix
Cycle 6: Create/update gap entries
Cycle 7: Draft requirements if needed
Cycle 8: Generate deep-dive document
Cycle 9: Update progress.md
Cycle 10: Escalate open questions
```

## Architecture

### Agent Loop

```python
class AnalysisAgent:
    def run(self, topic: str, config: AgentConfig) -> AgentResult:
        context = self.initialize_context(topic)
        
        for cycle in range(config.max_cycles):
            # Check context limits
            if context.usage > config.context_limit:
                context = self.compact(context)
            
            # Determine next action
            action = self.plan_next_action(context)
            
            # Execute action
            result = self.execute(action)
            
            # Check for completion or escalation
            if result.complete or result.needs_human:
                break
            
            context.update(result)
        
        return self.finalize(context)
```

### Integration with ConversationFiles

The agent internally uses process-oriented workflows:

```dockerfile
# Internal workflow template
MODEL claude-sonnet-4-20250514
ADAPTER copilot
MODE analysis

PROMPT ## Agent Cycle {{cycle}}

Current state: {{state}}
Topic: {{topic}}
Repositories: {{repos}}

Determine the next analysis step. Options:
1. EXPLORE - Find more relevant files
2. EXTRACT - Pull out specific information
3. COMPARE - Analyze differences
4. UPDATE - Modify documentation
5. ESCALATE - Need human decision
6. COMPLETE - Analysis finished

Output your choice and reasoning.
```

## Use Cases

### 1. Comprehensive Feature Analysis
```bash
sdqctl agent analyze "insulin on board calculation" \
  --repos "Loop,AAPS,Trio,oref0" \
  --depth comprehensive
```

### 2. Quick Gap Discovery
```bash
sdqctl agent analyze "batch upload handling" \
  --mode quick \
  --max-cycles 3
```

### 3. Terminology Mapping
```bash
sdqctl agent analyze "pump communication terminology" \
  --focus terminology \
  --output mapping/cross-project/pump-terms.md
```

## 5-Facet Auto-Update

Agent automatically updates all 5 documentation facets:

| Facet | Auto-Update Behavior |
|-------|---------------------|
| Terminology | Add new terms found during analysis |
| Gaps | Create GAP-XXX entries for issues |
| Requirements | Draft REQ-NNN for clear needs |
| Deep Dive | Generate/update topic document |
| Progress | Log dated completion entry |

## Guardrails

### Human Oversight
- `--confirm-updates` - Require confirmation before file changes
- `--dry-run` - Show planned changes without executing
- Automatic escalation to OPEN-QUESTIONS.md for unclear decisions

### Resource Limits
- `--max-cycles N` - Hard limit on iterations
- `--max-tokens N` - Context budget
- `--timeout 30m` - Wall-clock limit

### Safety
- No code execution in external repos
- Read-only access to externals/
- Write access only to docs/, traceability/, mapping/

## Implementation Phases

### Phase 1: Basic Agent Loop
- Single-topic analysis with manual workflow selection
- Context tracking and compaction
- Progress logging

### Phase 2: Autonomous Planning
- Agent selects appropriate workflow per cycle
- Multi-phase analysis with state tracking
- Automatic 5-facet updates

### Phase 3: Multi-Agent Coordination
- Parallel analysis of related topics
- Cross-agent context sharing
- Consolidated reporting

## Open Questions

1. How should agent handle conflicting information across repos?
2. Should agent be able to spawn sub-agents for parallel analysis?
3. What's the right balance between autonomy and human checkpoints?
4. How to handle rate limits and API costs?

## Related Proposals

- [HELP-INLINE.md](./HELP-INLINE.md) - Just-in-time context injection
- [SDK-INFINITE-SESSIONS.md](./SDK-INFINITE-SESSIONS.md) - Long-running session support
- [COMPACTION-UNIFICATION.md](./COMPACTION-UNIFICATION.md) - Context management
