# Session Resilience & Observability

> **Status**: Research ⚗️  
> **Created**: 2026-01-26  
> **Priority**: P3 (Medium-term)  
> **Source**: backlog-processor-v2 Run #5 observations

---

## Problem Statement

Long-running autonomous sessions (30-60 minutes) encounter three related challenges:

1. **Rate limits terminate sessions unpredictably** - Run #5 hit rate limit at 40 minutes with no warning
2. **Checkpoint resume is untested** - SDK supports resume but sdqctl hasn't validated it post-rate-limit
3. **Compaction effectiveness is unmeasured** - Every compaction in Run #5 *increased* tokens (counter-intuitive)

These issues become critical as we move toward longer autonomous workflows.

---

## Proposed Features

### Feature 1: Rate Limit Prediction

**Problem**: Sessions hit rate limits without warning, losing work-in-progress.

**Observation from Run #5**:
- 353 turns consumed 28.9M input tokens in 40 minutes
- Token consumption rate: ~723K tokens/minute
- Rate limit hit at turn 353

**Proposed Solution**:

Add token consumption rate tracking to `SessionStats`:

```python
@dataclass
class SessionStats:
    # ... existing fields ...
    
    # Rate limit awareness
    session_start_time: Optional[datetime] = None
    tokens_per_minute: float = 0.0  # Rolling average
    estimated_remaining_turns: Optional[int] = None
    rate_limit_warning_threshold: float = 0.8  # Warn at 80% of limit
```

Display warnings when approaching limits:

```
⚠️  Token consumption rate: 723K/min
⚠️  At current rate, ~15 minutes before rate limit
💡 Consider: --max-cycles 3 or adding COMPACT between phases
```

**Research Needed**:
- [ ] What is the actual rate limit? (tokens/minute? tokens/hour?)
- [ ] Does Copilot SDK expose rate limit metadata?
- [ ] Can we get remaining quota from API?
- [ ] Is rate limit per-session or per-user?

**Implementation Tasks** (if feasible):
- [ ] Add `session_start_time` to SessionStats
- [ ] Track token consumption rate (rolling 5-minute window)
- [ ] Calculate estimated remaining capacity
- [ ] Add warning output at 80% threshold
- [ ] Add `--rate-limit-aware` flag to enable predictive behavior

---

### Feature 2: Checkpoint Resume After Rate Limit

**Problem**: Rate limit termination saves checkpoint, but resume path is untested.

**Current State**:
- SDK supports `client.resume_session(session_id)`
- sdqctl has `sdqctl sessions resume <id>` command
- Checkpoints save on graceful shutdown
- Rate limit triggers graceful shutdown

**Untested Scenario**:
1. Run hits rate limit at Cycle 5, Phase 3
2. Checkpoint saved with current state
3. Wait for cooldown (46 minutes in Run #5)
4. Resume with `sdqctl sessions resume <id>`
5. Continue from Phase 3

**Research Needed**:
- [ ] Does rate limit checkpoint include full conversation state?
- [ ] Does resume restore context correctly?
- [ ] Can we resume mid-phase or only at phase boundaries?
- [ ] What happens to uncommitted work during rate limit?

**Validation Test Plan**:

```bash
# Test 1: Basic resume after rate limit
sdqctl -vvv iterate workflow.conv --adapter copilot -n 10
# Wait for rate limit
# After cooldown:
sdqctl sessions list  # Find session ID
sdqctl sessions resume <session_id>

# Test 2: Resume with continuation workflow
sdqctl sessions resume <session_id> --continue workflow.conv

# Test 3: Resume and verify state
sdqctl sessions show <session_id> --format json
# Check: phase, cycle, token counts, conversation length
```

**Implementation Tasks** (if gaps found):
- [ ] Document resume workflow in COMMANDS.md
- [ ] Add `--resume-from-rate-limit` convenience flag
- [ ] Ensure rate limit checkpoint includes phase/cycle info
- [ ] Add integration test for resume flow

---

### Feature 3: Compaction Effectiveness Metrics

**Problem**: Cannot assess whether compaction is helping or hurting.

**Observation from Run #5**:

| Cycle | Before | After | Δ | Effective? |
|-------|--------|-------|---|------------|
| 2 | 4,207,052 | 4,286,221 | +79,169 | ❌ No |
| 3 | 12,357,123 | 12,484,456 | +127,333 | ❌ No |
| 4 | 19,376,316 | 19,448,450 | +72,134 | ❌ No |
| 5 | 25,189,006 | 25,291,736 | +102,730 | ❌ No |

**Root Cause Hypothesis**:
The `COMPACT-PRESERVE prompts,errors,tool-results` directive preserves most content, and the summary is larger than the removed content.

**Proposed Metrics**:

Add to `CompactionResult` (already exists in copilot.py):

```python
@dataclass
class CompactionResult:
    preserved_content: str
    summary: str
    tokens_before: int
    tokens_after: int
    # New fields:
    token_delta: int  # After - Before (negative = reduction)
    compression_ratio: float  # Before / After
    effective: bool  # True if tokens decreased
    preserved_count: int  # Number of preserved items
    summary_tokens: int  # Tokens in summary alone
```

Track across session:

```python
@dataclass  
class SessionStats:
    # ... existing fields ...
    
    # Compaction tracking
    compaction_count: int = 0
    compaction_events: list = field(default_factory=list)
    total_tokens_saved: int = 0  # Cumulative (can be negative!)
    
    def compaction_effectiveness(self) -> float:
        """Return overall compaction effectiveness (< 1.0 = good)."""
        if not self.compaction_events:
            return 0.0
        total_before = sum(e.tokens_before for e in self.compaction_events)
        total_after = sum(e.tokens_after for e in self.compaction_events)
        return total_after / total_before if total_before > 0 else 0.0
```

Display in session summary:

```
📊 Compaction Summary:
   Events: 4
   Total Δ: +381,366 tokens (ineffective)
   Ratio: 1.02x (target: <0.8x)
   
💡 Recommendation: Use COMPACT (without PRESERVE) or reduce preserved categories
```

**Research Needed**:
- [ ] What is the optimal COMPACT-PRESERVE strategy?
- [ ] Does summary-only mode produce better results?
- [ ] What's the minimum context needed to maintain coherence?
- [ ] Is there a break-even point for preservation?

**Implementation Tasks**:
- [ ] Add `token_delta` and `effective` to CompactionResult
- [ ] Add `compaction_events` list to SessionStats
- [ ] Calculate and display effectiveness in session summary
- [ ] Add `--compaction-report` flag for detailed analysis
- [ ] Document compaction strategies in PHILOSOPHY.md

---

## Implementation Phases

### Phase 1: Observability (P3) - Low Effort

Add metrics without changing behavior:
- Compaction effectiveness tracking
- Token consumption rate display
- Session timing metadata

**Deliverables**:
- Enhanced CompactionResult dataclass
- SessionStats with timing/rate fields
- Summary output at session end

### Phase 2: Checkpoint Resume Testing (P3) - Medium Effort

Validate and document resume flow:
- Create test scenarios
- Document in COMMANDS.md
- Fix any gaps found

**Deliverables**:
- Resume workflow documentation
- Integration test for rate-limit resume
- Any bug fixes discovered

### Phase 3: Predictive Rate Limiting (P3) - Medium Effort

Add proactive warnings:
- Rate limit prediction algorithm
- Warning thresholds
- Suggested actions

**Deliverables**:
- Rate limit prediction in SessionStats
- Warning output at 80% threshold
- `--rate-limit-aware` flag

### Phase 4: Compaction Strategy Tuning (Future)

Research optimal strategies:
- Benchmark different PRESERVE options
- Document best practices
- Consider adaptive compaction

**Deliverables**:
- Compaction strategy guide
- Benchmarks in reports/
- Possibly new COMPACT modes

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Rate limit surprise | 100% (no warning) | <20% (predictive) |
| Resume success rate | Unknown | >90% |
| Compaction effectiveness | 1.02x (worse) | <0.8x (better) |
| Observability | Token counts only | Full session metrics |

---

## Dependencies

- [SDK-SESSION-PERSISTENCE.md](SDK-SESSION-PERSISTENCE.md) - Session resume APIs ✅
- [SDK-INFINITE-SESSIONS.md](SDK-INFINITE-SESSIONS.md) - Compaction implementation ✅
- [ERROR-HANDLING.md](ERROR-HANDLING.md) - Graceful shutdown ✅

---

## References

- Run #5 Analysis: `reports/backlogv2-run5-analysis-2026-01-26.md`
- SessionStats: `sdqctl/adapters/stats.py`
- Compaction: `sdqctl/adapters/copilot.py` (lines 750-842)
- Session Resume: `sdqctl/commands/sessions.py`
