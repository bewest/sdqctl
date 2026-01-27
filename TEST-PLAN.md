# sdqctl Test Plan
## Testing against rag-nightscout-ecosystem-alignment

### Overview

This plan tests sdqctl commands against the sibling repository which contains:
- Python tooling for workspace management
- Documentation in markdown
- Conformance tests and specs
- Traceability matrices

---

## Phase 1: Setup (No pip required)

Since pip isn't available, we'll run sdqctl directly via Python:

```bash
# Set up Python path
export PYTHONPATH="/home/bewest/src/copilot-do-proposal/sdqctl:$PYTHONPATH"

# Verify import works
python3 -c "from sdqctl.cli import cli; print('sdqctl loaded')"

# Create alias for convenience
alias sdqctl='python3 -m sdqctl.cli'
```

---

## Phase 2: Create Test Workflows

### Workflow 1: Documentation Audit
Target: `docs/` directory in rag-nightscout-ecosystem-alignment

```bash
# Create workflow for auditing documentation
cat > /tmp/test-docs-audit.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @docs/**/*.md
CONTEXT @README.md

PROMPT Analyze the documentation structure and identify:
1. Coverage gaps
2. Outdated sections
3. Missing cross-references
4. Terminology inconsistencies

OUTPUT-FORMAT markdown
EOF
```

### Workflow 2: Python Tools Review
Target: `tools/` directory

```bash
cat > /tmp/test-tools-review.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @tools/*.py

PROMPT Review the Python tools for:
1. Code quality and consistency
2. Error handling patterns
3. Documentation completeness
4. Potential improvements

OUTPUT-FORMAT markdown
EOF
```

### Workflow 3: Conformance Check
Target: `conformance/` and `specs/`

```bash
cat > /tmp/test-conformance.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

CONTEXT @conformance/**/*.md
CONTEXT @specs/**/*.md

PROMPT Analyze conformance documentation:
1. Requirement coverage
2. Test case completeness
3. Traceability gaps

OUTPUT-FORMAT markdown
EOF
```

---

## Phase 3: Run Tests

### Test 1: Validate Workflows
```bash
cd /home/bewest/src/rag-nightscout-ecosystem-alignment

# Validate each workflow parses correctly
python3 -c "
from sdqctl.core.conversation import ConversationFile
from pathlib import Path

for wf in ['/tmp/test-docs-audit.conv', '/tmp/test-tools-review.conv', '/tmp/test-conformance.conv']:
    conv = ConversationFile.from_file(Path(wf))
    print(f'✓ {wf}: {len(conv.prompts)} prompts, {len(conv.context_files)} context patterns')
"
```

### Test 2: Run with Mock Adapter
```bash
cd /home/bewest/src/rag-nightscout-ecosystem-alignment
export PYTHONPATH="/home/bewest/src/copilot-do-proposal/sdqctl:$PYTHONPATH"

# Run documentation audit
python3 -c "
import asyncio
from pathlib import Path
from sdqctl.core.conversation import ConversationFile
from sdqctl.core.session import Session
from sdqctl.adapters.mock import MockAdapter
from sdqctl.adapters.base import AdapterConfig

async def run_workflow(workflow_path):
    conv = ConversationFile.from_file(Path(workflow_path))
    session = Session(conv, base_path=Path.cwd())
    
    print(f'Workflow: {workflow_path}')
    print(f'  Context files found: {session.context.get_status()[\"files_loaded\"]}')
    print(f'  Prompts: {len(conv.prompts)}')
    
    # Run with mock adapter
    adapter = MockAdapter()
    await adapter.start()
    
    adapter_session = await adapter.create_session(AdapterConfig(model=conv.model))
    
    for i, prompt in enumerate(conv.prompts):
        response = await adapter.send(adapter_session, prompt)
        print(f'  Prompt {i+1} response: {response[:50]}...')
    
    await adapter.stop()
    print('  ✓ Complete')
    print()

asyncio.run(run_workflow('/tmp/test-docs-audit.conv'))
"
```

### Test 3: Context Resolution
```bash
cd /home/bewest/src/rag-nightscout-ecosystem-alignment

python3 -c "
from sdqctl.core.context import ContextManager
from pathlib import Path

ctx = ContextManager(base_path=Path.cwd())

# Test different patterns
patterns = [
    '@docs/**/*.md',
    '@tools/*.py',
    '@README.md',
    '@conformance/**/*.md',
]

for pattern in patterns:
    files = ctx.resolve_pattern(pattern)
    print(f'{pattern}: {len(files)} files')
    for f in files[:3]:
        print(f'  - {f.relative_to(Path.cwd())}')
    if len(files) > 3:
        print(f'  ... and {len(files) - 3} more')
    print()
"
```

### Test 4: Batch Workflow Execution
```bash
cd /home/bewest/src/rag-nightscout-ecosystem-alignment
export PYTHONPATH="/home/bewest/src/copilot-do-proposal/sdqctl:$PYTHONPATH"

# Run multiple workflows
python3 -c "
import asyncio
from pathlib import Path
from sdqctl.core.conversation import ConversationFile
from sdqctl.core.session import Session
from sdqctl.adapters.mock import MockAdapter
from sdqctl.adapters.base import AdapterConfig

async def run_batch():
    workflows = [
        '/tmp/test-docs-audit.conv',
        '/tmp/test-tools-review.conv',
        '/tmp/test-conformance.conv',
    ]
    
    adapter = MockAdapter()
    await adapter.start()
    
    for wf_path in workflows:
        conv = ConversationFile.from_file(Path(wf_path))
        session = Session(conv)
        
        adapter_session = await adapter.create_session(AdapterConfig(model=conv.model))
        
        print(f'Running: {Path(wf_path).name}')
        for prompt in conv.prompts:
            await adapter.send(adapter_session, prompt)
        print(f'  ✓ Complete')
        
        await adapter.destroy_session(adapter_session)
    
    await adapter.stop()
    print()
    print('All workflows complete!')

asyncio.run(run_batch())
"
```

---

## Phase 4: Integration with Existing Tools

### Create workflow that uses existing workspace_cli.py patterns

```bash
cat > /tmp/test-integration.conv << 'EOF'
MODEL gpt-4
ADAPTER mock
MODE audit
MAX-CYCLES 1

# Include existing tool outputs as context
CONTEXT @traceability/*.md
CONTEXT @tools/workspace_cli.py

PROMPT Analyze the workspace CLI and suggest improvements for:
1. Better integration with AI-assisted workflows
2. Enhanced traceability features
3. Additional commands that would be useful

OUTPUT-FORMAT markdown
EOF
```

---

## Phase 5: Full CLI Test (if dependencies work)

```bash
cd /home/bewest/src/rag-nightscout-ecosystem-alignment
export PYTHONPATH="/home/bewest/src/copilot-do-proposal/sdqctl:$PYTHONPATH"

# Run CLI directly
python3 -m sdqctl.cli status --adapters
python3 -m sdqctl.cli validate /tmp/test-docs-audit.conv
python3 -m sdqctl.cli show /tmp/test-docs-audit.conv
python3 -m sdqctl.cli run /tmp/test-docs-audit.conv --adapter mock --verbose --dry-run
```

---

## Expected Outcomes

1. **ConversationFile parsing** - All test workflows parse correctly
2. **Context resolution** - Glob patterns resolve to actual files
3. **Mock adapter execution** - Workflows run end-to-end with mock
4. **Session management** - Sessions track state correctly
5. **CLI commands** - All commands execute without errors

---

## Success Criteria

- [ ] All workflows validate successfully
- [ ] Context patterns resolve to correct files
- [ ] Mock adapter executes all prompts
- [ ] No Python import/runtime errors
- [ ] Output matches expected format
