# Iteration Patterns

Validated patterns for productive AI-assisted development iterations with sdqctl.

> **Source**: Analysis of 8-cycle (37m, 8 commits) and 3-cycle (19m, 9 commits) runs in January 2026.

---

## Pattern 1: Self-Grooming with Introduction Hint

When the Ready Queue is low, prompt the agent to discover and break down work mid-run.

### Usage

```bash
sdqctl iterate workflow.conv -n 5 \
  --introduction "We may need to groom backlog in order to find work."
```

### Behavior

1. Agent completes available Low-effort items
2. When queue runs low, agent examines Medium/High items
3. Agent breaks them into Low-effort steps and continues
4. Result: More work completed per run

### Evidence

| Run | Approach | Cycles | Commits | Efficiency |
|-----|----------|--------|---------|------------|
| 8-cycle | Pre-groomed Low items | 8/8 | 8 | 4.7 min/commit |
| 3-cycle | Self-grooming with hint | 3/3 | 9 | 2.2 min/commit |

The 3-cycle run was **3x more efficient** in lines-per-token.

---

## Pattern 2: Medium Items Over Low Batches

Medium-effort items often deliver complete features, while Low items are incremental.

### Guidance

| Situation | Recommendation |
|-----------|----------------|
| Queue has Low items only | Use `-n 8` or higher |
| Queue has Medium items | Use `-n 3-5`, let agent complete features |
| Queue is empty | Groom first, or use self-grooming hint |

### Rationale

- Low items: ~1 commit each, ~4-5 min each
- Medium items: ~2-3 commits, deliver cohesive features
- Breaking Medium → Low adds overhead without proportional benefit

---

## Pattern 3: Cycle Count Selection

Match cycle count to queue state and available time.

| -n Value | Best For | Expected Duration |
|----------|----------|-------------------|
| 1-2 | Quick fixes, single items | 5-15 min |
| 3-5 | Feature completion, grooming | 15-30 min |
| 8-10 | Batch processing, full queue | 35-50 min |

### Self-Termination Prevention

Agent self-terminates when:
1. Ready Queue is exhausted
2. Only Medium/High items remain without grooming
3. Context approaches limits

**Mitigation**: Pre-groom or use self-grooming introduction hint.

---

## Pattern 4: Work Package Batching

Agent naturally batches related work package items together.

### Observed Behavior

In the 8-cycle run, agent completed:
1. All WP-001 items (commits 1-4)
2. WP-004 item (commit 5)
3. All WP-005 items (commits 6-8)

### Recommendation

- Group related items in Work Packages
- Use `--introduction "Prioritize WP-00X"` for focus
- Let agent complete one WP before moving to next

---

## Pattern 5: Optimal Run Structure

The validated pattern for productive iterations:

```
groom → specify → run (with self-grooming hint)
```

### Steps

1. **Groom**: Break Medium/High items into Low-effort steps
2. **Specify**: Resolve open questions (OQ-*) blocking work
3. **Run**: Execute with self-grooming hint for resilience

### When to Skip Grooming

- Queue has 8+ Low items → run directly
- Items are clearly scoped → run directly
- Self-grooming hint covers edge cases

---

## Anti-Patterns

### ❌ Over-Breaking Items

Breaking every Medium item into Low items adds overhead:
- More backlog maintenance
- Less cohesive features
- Agent spends time on trivial items

**Instead**: Trust agent to handle Medium items; use self-grooming for dynamic breakdown.

### ❌ High Cycle Counts with Low Queue

Running `-n 10` with only 3 items in queue:
- Agent self-terminates early
- Wastes allocated time
- May trigger unnecessary grooming loops

**Instead**: Match `-n` to queue depth: `items / 1.5 ≈ cycles`

### ❌ No Introduction on Empty Queue

Running without `--introduction` when queue is low:
- Agent has no guidance on what to do
- May self-terminate immediately
- Wastes a cycle

**Instead**: Always use `--introduction` for context when queue state is uncertain.

---

## Metrics Reference

From recent runs:

| Metric | 8-cycle Run | 3-cycle Run |
|--------|-------------|-------------|
| Time per commit | 4.7 min | 2.2 min |
| Lines per minute | ~21 | ~117 |
| Tokens per line | 25,569 | 3,814 |
| Context at end | 17% | N/A |

---

## Future: backlog-processor-v3

These patterns inform the design of backlog-processor-v3.conv:

1. **Self-grooming phase** - Automatic when Ready Queue < 3 items
2. **Domain-aware routing** - Use domain backlogs for item discovery
3. **Economy metrics** - Track and display items/cycle, recommend -n
4. **Adaptive introduction** - Generate from queue state

See [SDK-ECONOMY.md](../proposals/SDK-ECONOMY.md) for full specification.

---

## References

- [reports/8-cycle-wp-run-analysis-2026-01-27.md](../reports/8-cycle-wp-run-analysis-2026-01-27.md)
- [reports/3-cycle-completion-run-2026-01-27.md](../reports/3-cycle-completion-run-2026-01-27.md)
- [proposals/SDK-ECONOMY.md](../proposals/SDK-ECONOMY.md)
- [docs/PHILOSOPHY.md](PHILOSOPHY.md)
