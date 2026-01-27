# [Topic] Improvements - Topic Focus

**Topic:** `[component/feature name]`  
**Source:** `reports/improvements-tracker.md`  
**Created:** {{DATE}}  
**Status:** In Progress

---

## Scope Boundaries

### In Scope
- `path/to/main/file.py` - main implementation
- Specific feature or behavior
- Related tests

### Out of Scope (for this topic)
- Other commands/features
- Unrelated modules
- Infrastructure changes

---

## Improvement Chunks

Work is organized by priority within each category. Complete one chunk before moving to the next.

### 1. Reliability & Error Recovery

#### R1: [Title] (P?) ⏳
**File:** `path/to/file.py` lines X-Y  
**Issue:** Description of the problem  
**Recommendation:** What should be done

**Tasks:**
- [ ] Design/plan the change
- [ ] Implement the change
- [ ] Add tests
- [ ] Document if needed

### 2. Security

#### S1: [Title] (P?) ⏳
**File:** `path/to/file.py`  
**Issue:** Description

**Tasks:**
- [ ] Task 1
- [ ] Task 2

### 3. Ergonomics

#### E1: [Title] (P?) ⏳
**File:** `path/to/file.py`  
**Issue:** Description

**Tasks:**
- [ ] Task 1
- [ ] Task 2

### 4. Code Quality

#### Q1: [Title] (P?) ⏳
**File:** `path/to/file.py`  
**Issue:** Description

**Tasks:**
- [ ] Task 1
- [ ] Task 2

### 5. Testing

#### T1: [Title] ⏳
**File:** `tests/test_[module].py`  
**Current:** X tests, ~Y% coverage  
**Gap:** What needs more coverage

**Tasks:**
- [ ] Test scenario 1
- [ ] Test scenario 2

---

## Completed This Session

<!-- Updated after each cycle -->

### Session 1 ({{DATE}})
- Completed: [item]
- Files modified: [list]

---

## Lessons Learned

<!-- Updated after each cycle with barriers, workarounds, insights -->

### Barriers Encountered
- [Barrier 1]: [How resolved or why blocked]

### Insights
- [Insight that may help future work]

---

## Next Session Command

```bash
cd /path/to/project
sdqctl -vv cycle -n 3 --adapter copilot \
  --prologue @reports/[topic]-improvements-focus.md \
  --epilogue "Update @reports/[topic]-improvements-focus.md with completed items and lessons learned" \
  examples/workflows/implement-improvements.conv
```

---

## References

- `path/to/main/file.py` - main implementation
- `reports/improvements-tracker.md` - full improvements list
- `tests/test_[module].py` - existing tests
