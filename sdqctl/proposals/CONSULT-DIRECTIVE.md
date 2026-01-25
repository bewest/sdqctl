# Proposal: CONSULT Directive - Human Consultation Workflow

**Date:** 2026-01-25  
**Status:** Draft  
**Author:** bewest + sdqctl planning session  
**Related:** PAUSE directive, SDK-SESSION-PERSISTENCE, session resume

---

## Summary

The `CONSULT` directive extends `PAUSE` to enable **proactive human consultation**. When a workflow hits `CONSULT`, it pauses like `PAUSE`, but when the human resumes the session, the agent immediately presents open questions and guides the human through answering them.

```dockerfile
# Current: PAUSE waits, human must ask what's needed
PAUSE "Review findings before continuing"

# Proposed: CONSULT proactively presents questions on resume
CONSULT "Design Decisions"
```

---

## Problem Statement

### Current State

The `PAUSE` directive stops workflow execution and waits for human resume:

```dockerfile
PROMPT Analyze the proposal and identify open questions.
PAUSE "Ready for human review"
PROMPT Continue with resolved questions.
```

When the human resumes with `copilot --resume session-name`:
- The agent has context about the work done
- But the agent waits passively for the human to ask questions
- Human must know to ask "What are the open questions?"

### Desired State

When the human resumes after `CONSULT`:
- Agent proactively summarizes open questions
- Agent presents them interactively (menus, choices)
- Human answers questions one by one
- Workflow continues with answers incorporated

---

## Proposed Solution

### New Directive: CONSULT

```dockerfile
CONSULT "topic description"
```

**Behavior:**

| Phase | PAUSE | CONSULT |
|-------|-------|---------|
| Pause execution | ✅ | ✅ |
| Save session | ✅ | ✅ |
| Print resume instructions | ✅ | ✅ |
| On resume: wait for human | ✅ | ❌ |
| On resume: present questions | ❌ | ✅ |
| On resume: collect answers | ❌ | ✅ |

### Example Workflow

```dockerfile
# consultation-workflow.conv
MODEL gpt-4
ADAPTER copilot
SESSION-NAME feature-design

CONTEXT @proposals/new-feature.md

PROMPT Analyze this feature proposal. 
  - Identify any gaps or ambiguities
  - Add open questions to the document's "## Open Questions" section
  - Categorize by: blocking vs nice-to-have

CONSULT "Feature Design Decisions"

PROMPT Now that the design decisions are resolved:
  - Update the proposal with the decisions
  - Create implementation tasks
  - Estimate effort for each task

OUTPUT-FILE proposals/new-feature-final.md
```

### Human Experience

```
$ sdqctl run consultation-workflow.conv

📄 Loading consultation-workflow.conv
🤖 Running with adapter: copilot
📋 Session: feature-design

[Cycle 1/3] Analyzing proposal...
✅ Added 4 open questions to document

[CONSULT] Session paused for consultation.
  Topic: Feature Design Decisions
  
  Resume with: copilot --resume feature-design
  
$ copilot --resume feature-design

🔍 Design Decisions - 4 Open Questions

Based on my analysis, I need your input on these decisions:

**Q1: Authentication Method**
The proposal mentions "secure auth" but doesn't specify. Options:
  [1] OAuth 2.0 (Recommended - industry standard)
  [2] API Keys (Simpler, less secure)
  [3] SAML (Enterprise, more complex)

Your choice: 1

**Q2: Rate Limiting Strategy**
Should limits apply per-user or per-organization?
  [1] Per-user (fairer for individuals)
  [2] Per-organization (simpler billing)

Your choice: 2

**Q3: Data Retention Period**
How long should we keep historical data?
> 90 days

**Q4: Notification Preferences**
Allow users to disable email notifications?
  [1] Yes, fully configurable
  [2] No, always notify
  [3] Partial - critical only always sent

Your choice: 1

✅ All questions answered. Continuing workflow...

[Cycle 2/3] Updating proposal with decisions...
[Cycle 3/3] Creating implementation tasks...

📄 Output saved to: proposals/new-feature-final.md
```

---

## Implementation

### Parsing

`CONSULT` is parsed like `PAUSE` with additional metadata:

```python
class DirectiveType(Enum):
    PAUSE = "PAUSE"
    CONSULT = "CONSULT"  # New

# In conversation.py
case DirectiveType.CONSULT:
    steps.append(ConversationStep(
        type="consult",
        content=directive.value,  # Topic description
    ))
```

### Execution

In `run.py`, when hitting a `consult` step:

```python
elif step.type == "consult":
    topic = step.content or "Open Questions"
    
    # Save session state
    await session_manager.checkpoint(session_name)
    
    # Mark session as "awaiting consultation"
    await session_manager.set_status(session_name, "consulting", {
        "topic": topic,
        "paused_at": datetime.now().isoformat(),
    })
    
    # Print resume instructions
    print(f"\n[CONSULT] Session paused for consultation.")
    print(f"  Topic: {topic}")
    print(f"\n  Resume with: copilot --resume {session_name}\n")
    
    # Exit workflow (will resume later)
    return ConsultationPending(session_name, topic)
```

### Resume Behavior

When `copilot --resume session-name` is invoked:

The SDK resumes the session with existing context. The key difference from PAUSE:

1. **Session metadata check**: sdqctl (or the SDK) detects `status == "consulting"`
2. **Inject consultation prompt**: Before user interaction, inject:

```python
CONSULTATION_PROMPT = """
You are resuming a paused consultation session.

Topic: {topic}

Your task:
1. Review the work done so far in context
2. Identify all open questions that need human input
3. Present each question clearly with choices where applicable
4. Use the ask_user tool to collect answers interactively
5. After all questions are answered, summarize the decisions
6. Signal readiness to continue with: "All questions resolved. Ready to continue."

Be concise. Present one question at a time. Offer reasonable defaults.
"""
```

3. **Agent presents questions**: Using `ask_user` tool for structured choices
4. **Workflow continues**: After human signals done, remaining prompts execute

### Option: sdqctl resume

Alternative to `copilot --resume`:

```bash
$ sdqctl resume feature-design

# Equivalent to:
# 1. Resume session
# 2. Inject consultation prompt
# 3. Hand off to interactive mode
```

This could wrap `copilot --resume` with the consultation prompt injection.

---

## Design Decisions

### D1: CONSULT uses existing ask_user tool

Rather than inventing new interaction mechanics, CONSULT prompts the agent to use the existing `ask_user` tool that already supports:
- Multiple choice questions
- Freeform input
- Recommended options

### D2: Questions discovered from context, not declared

The agent identifies open questions by analyzing the session context (documents, previous analysis). This is more flexible than pre-declaring questions.

### D3: Simple syntax, no sub-directives

```dockerfile
# Yes - simple
CONSULT "Design Decisions"

# No - too complex
CONSULT "Design Decisions"
  FROM @doc.md#section
  MAX-QUESTIONS 5
  TIMEOUT 1h
```

Keep it simple. The agent is smart enough to find questions in context.

### D4: Session naming encouraged but not required

```dockerfile
SESSION-NAME my-design  # Recommended for CONSULT workflows
CONSULT "..."

# Without SESSION-NAME, auto-generated ID is used
# (less user-friendly for resume command)
```

---

## Interaction with Other Features

| Feature | Interaction | Notes |
|---------|-------------|-------|
| PAUSE | Superset | CONSULT = PAUSE + proactive presentation |
| CHECKPOINT | Compatible | CONSULT creates checkpoint automatically |
| SESSION-NAME | Recommended | Makes resume command user-friendly |
| COMPACT | Compatible | Can COMPACT before CONSULT to summarize |
| MAX-CYCLES | Compatible | CONSULT doesn't consume a cycle |

---

## Phased Implementation

### Phase 1: Basic CONSULT

- [ ] Add `CONSULT` directive type
- [ ] Parse like PAUSE, store as `type="consult"`
- [ ] On consult: checkpoint + pause + print instructions
- [ ] Document the directive

### Phase 2: Consultation Prompt Injection

- [ ] Detect "consulting" status on session resume
- [ ] Inject consultation system prompt
- [ ] Test with copilot --resume

### Phase 3: sdqctl resume Enhancement

- [ ] `sdqctl resume SESSION` command
- [ ] Wraps copilot --resume with prompt injection
- [ ] Shows consultation topic in output

### Phase 4: Refinements

- [ ] Consultation timeout handling
- [ ] Partial answer saving
- [ ] "Continue later" option

---

## Open Questions

1. **Session status storage**: Where to store "consulting" status? Checkpoint metadata?
   - **Tentative**: Add `status` field to checkpoint JSON

2. **Timeout handling**: What if human never resumes?
   - **Tentative**: No timeout by default; sessions persist until deleted

3. **Multiple CONSULT**: Can a workflow have multiple CONSULT points?
   - **Tentative**: Yes, each creates a pause point; resume continues to next

---

## Success Criteria

1. Workflow pauses at CONSULT directive
2. Human can resume with `copilot --resume session-name`
3. Agent proactively presents open questions on resume
4. Agent uses `ask_user` for structured question collection
5. Workflow continues after questions answered

---

## References

- [PAUSE directive](../sdqctl/core/conversation.py) - lines 117, 1377-1380
- [human-review.conv example](../examples/workflows/human-review.conv)
- [SDK Session Persistence](SDK-SESSION-PERSISTENCE.md)
- [ask_user tool](../../copilot-sdk/) - interactive question tool
