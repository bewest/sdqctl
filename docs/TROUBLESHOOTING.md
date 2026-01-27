# Troubleshooting Guide

Common issues and solutions for sdqctl.

---

## Quick Diagnostics

```bash
# Check sdqctl is installed
sdqctl --version

# Check adapter availability
sdqctl status --adapters

# Check authentication
sdqctl status --auth

# Validate workflow syntax
sdqctl validate workflow.conv

# Test with mock adapter (no AI calls)
sdqctl run workflow.conv --adapter mock --dry-run
```

---

## Common Issues

### "Adapter not available"

**Symptom:**
```
Error: Adapter 'copilot' not available.
```

**Solution:**
```bash
# Install the adapter
pip install -e ".[copilot]"

# Or for all adapters
pip install -e ".[all]"

# Verify installation
sdqctl status --adapters
```

---

### "Authentication failed"

**Symptom:**
```
Error: GitHub authentication required
```

**Solution:**
```bash
# Option 1: Use GitHub CLI
gh auth login --scopes "copilot"

# Option 2: Set environment variable
export GH_TOKEN="your-github-token"

# Verify
sdqctl status --auth
```

---

### "Context limit exceeded"

**Symptom:**
```
Warning: Context at 95%, compaction required
```

**Solutions:**

1. **Use infinite sessions** (recommended):
   ```dockerfile
   INFINITE-SESSIONS enabled
   COMPACTION-THRESHOLD 80%
   ```

2. **Use fresh session mode**:
   ```bash
   sdqctl iterate workflow.conv -n 5 --session-mode fresh
   ```

3. **Add explicit COMPACT**:
   ```dockerfile
   PROMPT Phase 1 analysis
   COMPACT
   PROMPT Phase 2 (summarized context)
   ```

See [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md) for detailed strategies.

---

### "Workflow validation failed"

**Symptom:**
```
Error: Line 15: Unknown directive 'PROMT'
```

**Solution:**
```bash
# Check syntax
sdqctl validate workflow.conv

# See what was parsed
sdqctl show workflow.conv

# Preview rendered prompts
sdqctl render run workflow.conv
```

Common typos: `PROMT` → `PROMPT`, `CONTXT` → `CONTEXT`

---

### "File not found" in CONTEXT

**Symptom:**
```
Error: Context file not found: @lib/missing.py
```

**Solutions:**

1. **Check path is relative to workflow file**:
   ```dockerfile
   # If workflow is in workflows/audit.conv
   # and file is in lib/auth.py
   CONTEXT @../lib/auth.py
   ```

2. **Use glob patterns**:
   ```dockerfile
   CONTEXT @lib/**/*.py
   ```

3. **Allow missing files** (for optional context):
   ```bash
   sdqctl validate workflow.conv --allow-missing
   ```

---

### "RUN command failed"

**Symptom:**
```
Error: RUN failed with exit code 1
```

**Solutions:**

1. **Check the command works standalone**:
   ```bash
   # Run the same command manually
   npm test
   ```

2. **Use ON-FAILURE for recovery**:
   ```dockerfile
   RUN npm test
   ON-FAILURE
     PROMPT Analyze the test failures and fix them.
   ```

3. **Use RUN-RETRY for flaky commands**:
   ```dockerfile
   RUN npm test
   RUN-RETRY 3 "Fix any failing tests"
   ```

4. **Continue on error** (for non-critical commands):
   ```dockerfile
   RUN-ON-ERROR continue
   RUN npm run lint
   ```

---

### "Session not found" on resume

**Symptom:**
```
Error: Session 'abc123' not found
```

**Solutions:**

1. **List available sessions**:
   ```bash
   sdqctl sessions list
   ```

2. **Use named sessions** (easier to find):
   ```dockerfile
   SESSION-NAME my-audit-session
   ```

3. **Check session directory**:
   ```bash
   ls ~/.sdqctl/sessions/
   ```

---

### Agent seems stuck or looping

**Symptom:** Agent repeats similar responses or makes no progress.

**Solutions:**

1. **Check for stop file** (agent may have requested stop):
   ```bash
   ls STOPAUTOMATION-*.json
   cat STOPAUTOMATION-*.json  # See reason
   rm STOPAUTOMATION-*.json   # Remove to continue
   ```

2. **Use fresh session mode**:
   ```bash
   sdqctl iterate workflow.conv -n 3 --session-mode fresh
   ```

3. **Add explicit instructions in PROLOGUE**:
   ```dockerfile
   PROLOGUE You are an implementation assistant. Make direct edits.
   PROLOGUE Do not describe changes - use the edit tool to make them.
   ```

See [SDK-LEARNINGS.md](SDK-LEARNINGS.md#1-filename-semantics-influence-agent-role-q-001) for filename influence.

---

### "Too many tool calls" or slow execution

**Symptom:** Workflow takes very long, logs show many repeated tool calls.

**Solutions:**

1. **Use ELIDE to reduce turns**:
   ```dockerfile
   RUN pytest -v
   ELIDE
   PROMPT Fix any failing tests above.
   # Agent sees test output + instruction in one turn
   ```

2. **Provide hints, don't inject everything**:
   ```dockerfile
   # Instead of:
   CONTEXT @docs/**/*.md
   
   # Use:
   PROMPT Check docs/ for relevant files if needed.
   ```

3. **Use compact session mode** for long workflows:
   ```bash
   sdqctl iterate workflow.conv -n 10 --session-mode compact
   ```

---

## Debugging Workflows

### See what prompts are sent

```bash
# Show prompts on stderr
sdqctl -P run workflow.conv

# Capture prompts to file
sdqctl -P run workflow.conv 2> prompts.log
```

### Increase verbosity

```bash
sdqctl -v run workflow.conv     # Progress + context %
sdqctl -vv run workflow.conv    # Streaming responses
sdqctl -vvv run workflow.conv   # Full debug (tools, reasoning)
```

See [IO-ARCHITECTURE.md §Verbosity Quick Reference](IO-ARCHITECTURE.md#verbosity-quick-reference) for details.

### Preview without executing

```bash
# Render prompts without AI calls
sdqctl render run workflow.conv

# Show parsed structure
sdqctl show workflow.conv

# Dry run (no file writes)
sdqctl run workflow.conv --dry-run
```

---

## Getting Help

```bash
# General help
sdqctl help

# Command-specific help
sdqctl help run
sdqctl help iterate

# Topic help
sdqctl help directives
sdqctl help variables
```

---

## See Also

- [GETTING-STARTED.md](GETTING-STARTED.md) - Quick start guide
- [QUIRKS.md](QUIRKS.md) - Known behaviors and workarounds
- [IO-ARCHITECTURE.md](IO-ARCHITECTURE.md) - Output and verbosity details
- [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md) - Context strategies
