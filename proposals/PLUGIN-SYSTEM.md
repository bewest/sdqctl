# Proposal: Plugin System for Ecosystem Extensions

> **Status**: In Progress (Phase 4 pending - ecosystem adoption)  
> **Date**: 2026-01-27  
> **Author**: sdqctl development  
> **Scope**: Allow external workspaces to extend sdqctl with custom directives/commands

---

## Problem Statement

Ecosystem teams (e.g., rag-nightscout-ecosystem-alignment) need custom tooling for their specific workflows:

- **Custom directives** for domain-specific analysis (`VERIFY stpa-hazards`, `VERIFY ecosystem-gaps`)
- **Custom commands** for specialized workflows (`sdqctl ns-compare`, `sdqctl trace-uca`)
- **Independent iteration** without waiting for sdqctl release cycle

Currently, ecosystem teams must either:
1. Request features in sdqctl core (slow, coupling)
2. Write standalone scripts (no integration, duplicated effort)
3. Fork sdqctl (maintenance burden)

---

## Proposed Solution

### Option A: Plugin Directories

Discover plugins in well-known locations:

```
.sdqctl/plugins/           # Workspace-local plugins
~/.sdqctl/plugins/         # User-global plugins
```

**Structure:**
```
.sdqctl/plugins/
├── ecosystem-gaps/
│   ├── plugin.yaml        # Manifest: name, version, capabilities
│   ├── verify_gaps.py     # Implementation
│   └── README.md          # Documentation
```

**Pros:** Clear structure, versioning, documentation co-located  
**Cons:** More complex, requires manifest schema

### Option B: Script Wrappers (Simpler)

sdqctl provides SDK; teams write standalone scripts:

```python
# tools/verify_ecosystem_gaps.py
from sdqctl.sdk import Verifier, register_directive

@register_directive("VERIFY", "ecosystem-gaps")
class EcosystemGapsVerifier(Verifier):
    def verify(self, context):
        # Custom verification logic
        pass
```

**Pros:** Minimal overhead, familiar Python patterns  
**Cons:** Less discoverable, no standard structure

### Option C: Directive Extensions via Manifest (Recommended)

Register custom directives via `.sdqctl/directives.yaml`:

```yaml
# .sdqctl/directives.yaml
version: 1
directives:
  VERIFY:
    stpa-hazards:
      handler: python tools/verify_stpa.py
      description: "Verify STPA hazard traceability"
      
    ecosystem-gaps:
      handler: python tools/verify_gaps.py
      description: "Verify gap coverage across projects"
      
  # Custom directive type
  TRACE:
    uca:
      handler: python tools/trace_uca.py
      description: "Trace UCA to requirements and tests"
```

**Pros:** 
- Declarative, easy to understand
- Works with existing directive system
- Shell commands or Python handlers
- No Python knowledge required for simple cases

**Cons:**
- New manifest format to maintain
- Limited to directive patterns

---

## Recommended Approach: Option C with SDK

Combine manifest-based discovery with Python SDK for complex cases:

1. **Simple plugins**: YAML manifest pointing to shell commands
2. **Complex plugins**: Python SDK for full programmatic control
3. **Hybrid**: Manifest declares, Python implements

---

## Implementation Phases

### Phase 1: Design & Prototype (1 iteration) ✅ COMPLETE

- [x] Define `.sdqctl/directives.yaml` schema ✅ 2026-01-27
- [ ] Define capability/security model (what can plugins access?)
- [ ] Create minimal SDK interface (`sdqctl.sdk`)
- [ ] Document design decisions

**Deliverables:**
- `docs/directives-schema.json` - JSON Schema for manifest ✅
- `sdqctl/sdk/__init__.py` - SDK stubs (deferred to Phase 3)

### Phase 2: Hello World Plugin (1 iteration) ✅ COMPLETE

- [x] Implement directive discovery from manifest ✅ 2026-01-27
- [x] Create example plugin in `externals/rag-nightscout-ecosystem-alignment` ✅ 2026-01-27
- [x] `sdqctl verify plugin` command for running plugins ✅ 2026-01-27
- [ ] Test: `VERIFY ecosystem-gaps` directive works in .conv files (deferred)

**Deliverables:**
- `sdqctl/plugins.py` - Plugin discovery and registration ✅
- `tests/test_plugins.py` - 21 tests ✅
- `docs/PLUGIN-AUTHORING.md` - Plugin author guide ✅ 2026-01-27
- `externals/rag-nightscout-ecosystem-alignment/.sdqctl/directives.yaml` - Demo manifest ✅
- `externals/rag-nightscout-ecosystem-alignment/tools/verify_hello.py` - Demo plugin ✅

### Phase 3: Security & Polish (1 iteration) ✅ COMPLETE

- [x] Implement sandboxing or capability allowlist ✅ 2026-01-27
- [x] Add `sdqctl verify plugin --list` - Show discovered plugins ✅ 2026-01-27
- [x] Add `sdqctl plugin validate <path>` - Validate plugin structure ✅ 2026-01-27
- [x] Error handling and diagnostics for plugin failures ✅ 2026-01-27

**Deliverables:**
- `sdqctl/commands/plugin.py` - Plugin management commands ✅
- Capability validation in `DirectiveHandler` ✅
- 9 new tests (30 total in test_plugins.py) ✅

### Phase 4: Ecosystem Adoption (1 iteration)

- [ ] Migrate ecosystem-specific tools to plugin format
- [ ] Gather feedback from Nightscout alignment team
- [ ] Refine based on real usage patterns
- [ ] Document lessons learned

**Deliverables:**
- 2+ production plugins in ecosystem workspace
- Feedback integration

---

## Security Model

### Capabilities

Plugins can request capabilities in their manifest:

```yaml
# plugin.yaml or directives.yaml
capabilities:
  - read_files          # Read files in workspace
  - write_files         # Write to specific paths
  - run_commands        # Execute shell commands
  - network             # Make network requests (rare)
  - adapter_access      # Full adapter API (advanced)
```

### Sandboxing Options

| Level | Description | Use Case |
|-------|-------------|----------|
| **None** | Full access (like RUN directive) | Trusted internal plugins |
| **Path-restricted** | Can only access declared paths | Most plugins |
| **Subprocess** | Runs in isolated subprocess | Untrusted plugins |

**Recommendation:** Start with path-restricted (Phase 3), add subprocess isolation later if needed.

---

## SDK Interface (Draft)

```python
# sdqctl/sdk/__init__.py

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

@dataclass
class PluginContext:
    """Context passed to plugin handlers."""
    workspace_root: Path
    current_file: Optional[Path]
    verbosity: int
    
    # Restricted file access
    def read_file(self, path: str) -> str:
        """Read file relative to workspace root."""
        pass
    
    def write_file(self, path: str, content: str) -> None:
        """Write file (if write_files capability granted)."""
        pass
    
    def glob_files(self, pattern: str) -> List[Path]:
        """Find files matching pattern."""
        pass

class Verifier:
    """Base class for custom VERIFY handlers."""
    
    def verify(self, context: PluginContext) -> VerifyResult:
        """Override to implement verification logic."""
        raise NotImplementedError

@dataclass
class VerifyResult:
    success: bool
    message: str
    details: Optional[str] = None
    suggestions: Optional[List[str]] = None
```

---

## Open Questions

| ID | Question | Options | Decision (2026-01-27) |
|----|----------|---------|----------------------|
| OQ-PLUG-001 | Plugin discovery mechanism | File convention vs manifest vs both | **Manifest** (`.sdqctl/directives.yaml`) |
| OQ-PLUG-002 | Security model | Full access vs sandboxed API | **Full access** (trust workspace plugins) |
| OQ-PLUG-003 | Directive vs command plugins | Extend VERIFY vs new subcommands | **New directive types** (VERIFY, TRACE, CHECK, etc.) |
| OQ-PLUG-004 | Plugin distribution | Git submodules vs package registry | **Workspace-local only** (`.sdqctl/` in repo) |

---

## Success Criteria

1. **Independence**: Ecosystem team can create a working plugin without modifying sdqctl core
2. **Decoupling**: Plugin updates don't require sdqctl version bump
3. **Documentation**: Clear guide for plugin authors
4. **Adoption**: At least one real plugin in production use (ecosystem workspace)
5. **Security**: No privilege escalation beyond declared capabilities

---

## Hello World Plugin (Test Case)

Target: `externals/rag-nightscout-ecosystem-alignment/.sdqctl/directives.yaml`

```yaml
version: 1
directives:
  VERIFY:
    ecosystem-gaps:
      handler: python tools/verify_gaps.py
      description: "Verify all GAP-XXX entries have required fields"
      
    terminology-coverage:
      handler: python tools/verify_terminology.py
      description: "Check terminology matrix coverage"
```

**Test workflow:**
```dockerfile
# test-plugin.conv
MODEL claude-sonnet-4-20250514
ADAPTER copilot

VERIFY ecosystem-gaps
VERIFY-ON-ERROR continue

PROMPT Analyze the verification results and suggest improvements.
```

---

## References

- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - Built-in verify system
- [RUN-BRANCHING.md](RUN-BRANCHING.md) - Command execution patterns
- Python entry_points for plugin inspiration
- VS Code extension API for capability model inspiration

---

**Document Version**: 0.1  
**Last Updated**: 2026-01-27
