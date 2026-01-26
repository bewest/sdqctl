# Session Resilience & Observability

> **Status**: ✅ COMPLETE (All phases)  
> **Created**: 2026-01-26  
> **Updated**: 2026-01-26  
> **Priority**: Complete  
> **Source**: backlog-processor-v2 Run #5 observations + SDK research

---

## Problem Statement

Long-running autonomous sessions (30-60 minutes) encounter three related challenges:

1. **Rate limits terminate sessions unpredictably** - Run #5 hit rate limit at 40 minutes with no warning
2. **SDK provides rich metrics we don't parse** - quota, cost, cache, compaction data available but ignored
3. **Compaction effectiveness is unmeasured** - Every compaction in Run #5 *increased* tokens (counter-intuitive)

These issues become critical as we move toward longer autonomous workflows.

---

## Proposed Features

### Feature 1: Metrics Instrumentation (NEW - P2)

**Problem**: SDK events contain rich observability data that sdqctl doesn't parse.

**Current State**:
| Event | What's Extracted | What's Ignored |
|-------|------------------|----------------|
| `assistant.usage` | `input_tokens`, `output_tokens` | `quota_snapshots`, `cost`, `cache_*_tokens` |
| `session.usage_info` | `current_tokens`, `token_limit` | - |
| `session.error` | Generic message | `error_type`, `error.code` |
| `session.compaction_complete` | ✅ Logged | `tokens_removed`, `summary_content`, metrics |

**Available SDK Data**:

1. **Quota Tracking** (from `assistant.usage`):
   ```python
   quota_snapshots: {
       "premium": {
           "remaining_percentage": 78.5,
           "reset_date": "2026-01-27T00:00:00Z",
           "is_unlimited_entitlement": False,
           "used_requests": 215,
           "entitlement_requests": 1000
       }
   }
   ```

2. **Cost & Cache** (from `assistant.usage`):
   - `cost` - API call cost
   - `cache_read_tokens` - Tokens served from cache
   - `cache_write_tokens` - Tokens added to cache

3. **Compaction Metrics** (from `session.compaction_complete`):
   - `tokens_removed`, `pre/post_compaction_tokens`
   - `summary_content` - The actual summary
   - `compaction_tokens_used.{input, output, cached_input}`

---

### Feature 2: Rate Limit Prediction

**Problem**: Sessions hit rate limits without warning, losing work-in-progress.

**Observation from Run #5**:
- 353 turns consumed 28.9M input tokens in 40 minutes
- Token consumption rate: ~723K tokens/minute
- Rate limit hit at turn 353

#### Key Finding: Request Frequency, Not Token Consumption

Analysis of Run #5 rate limit reveals the limit is **request-based**, not token-based:

| Evidence | Value | Implication |
|----------|-------|-------------|
| Error message | "restricts the number of **Copilot model requests**" | Explicitly says "requests" |
| Context at limit | 88K/128K tokens (68%) | Plenty of token headroom |
| Turns at limit | 353 | Request count is the constraint |
| Cumulative tokens | 28.9M | Misleading - this is sum of all turns |

**Rate Limit Characterization**:

| Metric | Value | Source |
|--------|-------|--------|
| Turns per cycle | ~78 | 353 turns / 4.5 cycles |
| Implied limit | ~350-400 requests | Per 40-60 min window |
| Cooldown | 46 minutes | From error message |

**Cycle Planning Guide**:

| -n Value | Est. Turns | Safety |
|----------|------------|--------|
| **3** | 234 | ✅ Safe (66% of limit) |
| **4** | 312 | ✅ Likely safe (89% of limit) |
| **5** | 390 | ⚠️ Borderline (111% of limit) |
| **6+** | 468+ | ❌ Will hit limit |

**Critical Insight**: Compaction does NOT help with rate limits:
- Compaction reduces context window tokens
- But adds request count (compaction request + re-injection)
- May actually *accelerate* rate limit hit

**Proposed Solution**:

Add request rate tracking to `SessionStats`:

```python
@dataclass
class SessionStats:
    # ... existing fields ...
    
    # Rate limit awareness (REQUEST-based, not token-based)
    session_start_time: Optional[datetime] = None
    requests_per_minute: float = 0.0  # Rolling average
    total_requests: int = 0  # Same as turns
    estimated_remaining_requests: Optional[int] = None
    rate_limit_warning_threshold: float = 0.8  # Warn at 80% of limit
```

Display warnings when approaching limits:

```
⚠️  Request rate: 8.8/min (353 total)
⚠️  Estimated limit: ~350-400 requests per window
⚠️  At current rate, ~5 minutes before rate limit
💡 Recommendation: Complete current cycle, then stop
```

**Research Completed (2026-01-26)**:

The SDK **does** expose quota information! Found in `copilot-sdk/python/copilot/generated/session_events.py`:

```python
@dataclass
class QuotaSnapshot:
    entitlement_requests: float      # Total allowed requests
    is_unlimited_entitlement: bool   # Unlimited plan?
    overage: float                   # Amount over quota
    overage_allowed_with_exhausted_quota: bool
    remaining_percentage: float      # ← KEY: How much quota left (0-100)
    usage_allowed_with_exhausted_quota: bool
    used_requests: float             # Requests consumed
    reset_date: Optional[datetime]   # When quota resets
```

This is attached to the `assistant.usage` event in `data.quota_snapshots: Dict[str, QuotaSnapshot]`.

**Key Findings**:
- ✅ `remaining_percentage` - exact remaining quota percentage
- ✅ `reset_date` - when quota resets (tells us window duration)
- ✅ `entitlement_requests` / `used_requests` - absolute counts
- ✅ `is_unlimited_entitlement` - can skip tracking for unlimited plans
- ❓ Not yet verified: Is this per-session, per-user, or per-organization?

**Error Event Structure** (for rate limit detection):

```python
@dataclass
class ErrorClass:
    message: str
    code: Optional[str] = None  # ← May contain rate limit error code
    stack: Optional[str] = None

# Session error event data fields:
error_type: Optional[str] = None  # ← Type classification
error: Optional[Union[ErrorClass, str]] = None  # ← Full error object
```

**Implementation Tasks** (updated with SDK knowledge):
- [ ] Parse `quota_snapshots` from `assistant.usage` events
- [ ] Add `quota_remaining_percentage` to SessionStats
- [ ] Add `quota_reset_date` to SessionStats  
- [ ] Skip quota tracking if `is_unlimited_entitlement`
- [ ] Warn when `remaining_percentage < 20%`
- [ ] Parse `error_type` and `error.code` for rate limit codes
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

### Phase 0: Quota Event Parsing (P2) - ✅ COMPLETE

Parse existing SDK events that already contain quota data:

```python
# In event handler (adapters/copilot.py)
elif event_type == "assistant.usage":
    # ... existing token tracking ...
    
    # NEW: Extract quota snapshots
    quota_snapshots = _get_field(data, "quota_snapshots", "quotaSnapshots", default={})
    for quota_type, snapshot in quota_snapshots.items():
        remaining = snapshot.get("remainingPercentage", 100)
        if remaining < 20:
            logger.warning(f"⚠️  Quota low: {remaining:.0f}% remaining ({quota_type})")
            progress(f"  ⚠️  Quota: {remaining:.0f}% remaining")
        stats.quota_remaining = min(stats.quota_remaining, remaining)
        stats.quota_reset_date = snapshot.get("resetDate")
```

**Deliverables** (Completed 2026-01-26):
- ✅ Add `quota_remaining`, `quota_reset_date` to SessionStats
- ✅ Add `quota_used_requests`, `quota_entitlement_requests`, `is_unlimited_quota` to SessionStats
- ✅ Parse `quota_snapshots` from `assistant.usage` events
- ✅ Log warning when quota < 20%
- ✅ 3 new tests for quota tracking

**Effort**: ~50 lines of code changes

### Phase 0.5: Error Event Enhancement (P2) - ✅ COMPLETE

Parse `session.error` for rate limit specifics:

```python
elif event_type == "session.error":
    error = _get_field(data, "error", "message", default=str(data))
    error_type = _get_field(data, "error_type", "errorType", default=None)
    error_code = None
    
    # Extract code from ErrorClass structure
    if isinstance(error, dict):
        error_code = error.get("code")
        error_msg = error.get("message", str(error))
    else:
        error_msg = str(error)
    
    # Detect rate limit errors
    if error_code == "429" or error_type == "rate_limit" or "rate limit" in error_msg.lower():
        logger.warning(f"Rate limit hit: {error_msg}")
        stats.rate_limited = True
        progress(f"  🛑 Rate limited - wait before retrying")
    else:
        logger.error(f"Session error: {error_msg}")
        progress(f"  ⚠️  Error: {error_msg}")
```

**Deliverables** (Completed 2026-01-26):
- ✅ Add `rate_limited: bool` to SessionStats
- ✅ Add `rate_limit_message: Optional[str]` to SessionStats
- ✅ Specific handling for rate limit errors (code 429, message patterns)
- ✅ User-friendly rate limit message in progress output
- ✅ 3 new tests for rate limit detection

**Effort**: ~30 lines of code changes

### Phase 1: Observability (P3) - ✅ COMPLETE

Add metrics without changing behavior:
- Compaction effectiveness tracking
- Token consumption rate display
- Session timing metadata

**Deliverables** (Completed 2026-01-26):
- ✅ `CompactionEvent` dataclass with `token_delta` and `effective` properties
- ✅ SessionStats with `session_start_time`, `compaction_events` list
- ✅ SessionStats properties: `session_duration_seconds`, `requests_per_minute`
- ✅ SessionStats properties: `compaction_count`, `compaction_effectiveness`, `total_tokens_saved`
- ✅ 5 new tests for observability features

**Note**: Summary output at session end deferred - requires changes in run.py/iterate.py

### Phase 2: Checkpoint Resume Testing (P2) - ✅ COMPLETE

Validate and document resume flow:
- Create test scenarios
- Document in COMMANDS.md
- Fix any gaps found

**Deliverables** (Completed 2026-01-26):
- ✅ Resume workflow documentation in COMMANDS.md (rate limit recovery section)
- ✅ 4 integration tests for rate-limit resume (TestRateLimitResumeFlow)
- ✅ No gaps found - checkpoint and resume flow works correctly

**Finding**: Current implementation handles rate limits well:
- Checkpoints saved automatically on all errors (including rate limits)
- `sessions resume` restores SDK conversation state
- `resume` command handles local checkpoint files
- CONSULT-TIMEOUT expiration check prevents stale resumes

### Phase 3: Predictive Rate Limiting (P2) - ✅ COMPLETE

Add proactive warnings:
- Rate limit prediction algorithm
- Warning thresholds
- Suggested actions

**Deliverables** (Completed 2026-01-26):
- ✅ Rate limit prediction in SessionStats
  - `estimated_remaining_requests` - calculates from quota data
  - `estimated_minutes_remaining` - time until rate limit at current rate
  - `should_warn_rate_limit(threshold)` - check if warning needed
  - `get_rate_limit_warning()` - formatted warning message
- ✅ Warning output at 20% threshold (integrated into copilot adapter)
- ⏸️ `--rate-limit-aware` flag deferred (current warning is automatic)
- ✅ 9 new tests for rate limit prediction

**Example warning output**:
```
⚠️  Quota: 15% remaining | ~150 requests left | ~15 min at current rate
```

### Phase 4: Compaction Strategy Tuning (P2) - ✅ COMPLETE

Research optimal strategies:
- Benchmark different PRESERVE options
- Document best practices
- Consider adaptive compaction

**Deliverables** (Completed 2026-01-26):
- ✅ Compaction effectiveness display in session completion output
  - Shows compaction count and effectiveness ratio
  - Green for effective (<1.0x), yellow for ineffective (>1.0x)
- ✅ Compaction stats in JSON output (`adapter_stats.compaction`)
- ✅ 3 new tests for compaction summary display
- ⏸️ Compaction strategy guide deferred (existing docs in CONTEXT-MANAGEMENT.md are comprehensive)

**Example output:**
```
✓ Completed 5 cycles
Total messages: 47
Compactions: 4 (1.02x - increased context)
```

**Key finding from Run #5 analysis:** COMPACT-PRESERVE with many categories often increases tokens because the summary is larger than removed content. Consider using minimal preservation or no PRESERVE for best results.

---

## SDK Data Sources Reference

### QuotaSnapshot (from `assistant.usage` event)

Located in `copilot-sdk/python/copilot/generated/session_events.py`:

| Field | Type | Description |
|-------|------|-------------|
| `remaining_percentage` | float | Quota remaining (0-100) |
| `entitlement_requests` | float | Total allowed requests |
| `used_requests` | float | Requests consumed |
| `overage` | float | Amount over quota |
| `is_unlimited_entitlement` | bool | Unlimited plan flag |
| `reset_date` | datetime? | When quota resets |
| `overage_allowed_with_exhausted_quota` | bool | Overage policy |
| `usage_allowed_with_exhausted_quota` | bool | Continued usage policy |

**Accessed via**: `event.data.quota_snapshots["<quota_type>"]`

### ErrorClass (from `session.error` event)

| Field | Type | Description |
|-------|------|-------------|
| `message` | str | Error message |
| `code` | str? | Error code (may be "429" for rate limits) |
| `stack` | str? | Stack trace |

**Additional fields on error event data**:
- `error_type` - Classification of error type
- `error` - Either ErrorClass object or string

### Usage Events Currently Parsed

| Event | Current Handling | Data Available |
|-------|-----------------|----------------|
| `assistant.usage` | ✅ Tokens counted | + `quota_snapshots` (not parsed) |
| `session.usage_info` | ✅ Context tracked | `current_tokens`, `token_limit` |
| `session.error` | ⚠️ Generic log | `error_type`, `error.code` (not parsed) |

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

---

## Appendix: Operational Guidance (from Run #5)

### Rate Limit Avoidance

Based on empirical data from Run #5 (353 turns, 40 min, 4.5 cycles):

```
Rule of Thumb: 78 turns per cycle, limit ~350 requests per window

Safe:      -n 3  (234 turns, 66% of limit)
Optimal:   -n 4  (312 turns, 89% of limit)  
Risky:     -n 5  (390 turns, 111% of limit)
Unsafe:    -n 6+ (468+ turns)
```

### Why Compaction Doesn't Help Rate Limits

| Action | Token Impact | Request Impact |
|--------|--------------|----------------|
| Normal turn | +varies | +1 request |
| Compaction | Reduces context | +2 requests (compact + reinject) |
| Long turn with tools | +many | +1 request |

**Implication**: Minimize turn count, not token count:
- Batch tool calls where possible
- Combine related operations
- Skip verbose verification phases in long runs

### Cooldown Strategy

When rate-limited at 40 min with 46 min cooldown:
1. Save checkpoint (automatic on graceful shutdown)
2. Wait for cooldown (use timer/alarm)
3. Resume with: `sdqctl sessions resume <session_id>`
4. Or start fresh with `-n 4` to stay under limit

### Context % vs Rate Limit

These are **independent** constraints:

| Constraint | Metric | Symptom |
|------------|--------|---------|
| Context window | 128K tokens (68% at limit) | Compaction needed |
| Rate limit | ~350 requests/window | Cooldown needed |

Run #5 hit rate limit at 68% context utilization - context was fine, requests weren't.
- SDK Session Events: `copilot-sdk/python/copilot/generated/session_events.py`
- QuotaSnapshot: lines 205-240
- ErrorClass: lines 160-181
