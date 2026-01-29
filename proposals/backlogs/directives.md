# Directives Backlog

> **Domain**: Directive system, plugins, extensibility  
> **Parent**: [BACKLOG.md](../BACKLOG.md)  
> **Last Updated**: 2026-01-29

---

## Active Items

| # | Item | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| *(No active items)* | | | | All directive work complete |

---

## Backlog Details

### DIR-001: Custom directive types from plugins

**Problem**: External projects (e.g., rag-nightscout-ecosystem-alignment) can define custom directive types in `.sdqctl/directives.yaml` (e.g., `HYGIENE`), but sdqctl only processes `VERIFY` plugins. The parser ignores unknown directives.

**Current limitation** (plugins.py line 237):
```python
if handler.directive_type == "VERIFY":
    # Only VERIFY handlers are registered
```

**Requirements**:
1. Parser should recognize plugin-defined directive types
2. Directive handlers should be callable from .conv files
3. CLI subcommands for custom directives (e.g., `sdqctl hygiene queue-stats`)

**Scope**:
- Parser extension (DirectiveType enum → extensible registry)
- Plugin loading for non-VERIFY types
- Execution pipeline integration
- CLI command generation

**Dependencies**: DIR-002, DIR-003

**References**:
- [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md) - Phase 4 ecosystem adoption
- [externals/rag-nightscout-ecosystem-alignment/.sdqctl/directives.yaml](../../externals/rag-nightscout-ecosystem-alignment/.sdqctl/directives.yaml) - HYGIENE example

---

### DIR-002: Extensible DirectiveType enum

**Problem**: `DirectiveType` is a Python Enum, which is static and cannot be extended at runtime.

**Approach options**:
1. **String-based types**: Use strings instead of enum for directive types
2. **Hybrid**: Keep enum for built-in, use string registry for plugins
3. **Dynamic enum**: Create enum class at load time with plugin types

**Recommended**: Option 2 (hybrid) - minimal disruption to existing code.

---

### DIR-003: Custom directive execution hooks

**Problem**: Even if parser recognizes custom directives, the iterate/run pipeline doesn't know how to execute them.

**Requirements**:
1. Hook system for plugin directive execution
2. Context passing (workspace, session state)
3. Output handling (inject into prompt, log, etc.)
4. Error handling consistent with VERIFY-ON-ERROR patterns

---

## Completed

| Item | Date | Notes |
|------|------|-------|
| **DIR-001: Parser integration** | 2026-01-29 | Custom directives in .conv files, pipeline execution, 13 tests |
| **DIR-003: Custom directive execution hooks** | 2026-01-29 | DirectiveExecutionContext, hooks registry, 17 tests |
| **DIR-002: Extensible DirectiveType** | 2026-01-29 | Hybrid approach: enum + string registry, 11 tests |
| **Directive discovery from manifest** | 2026-01-27 | WP-004 step 2: Created sdqctl/plugins.py. 21 tests. |
| **Define directives.yaml schema** | 2026-01-27 | WP-004 step 1: Created docs/directives-schema.json. |

*See also: main BACKLOG.md Recently Completed*

---

## References

- [docs/DIRECTIVE-REFERENCE.md](../../docs/DIRECTIVE-REFERENCE.md) - Directive catalog
- [PLUGIN-SYSTEM.md](../PLUGIN-SYSTEM.md) - Plugin proposal
- [docs/directives-schema.json](../../docs/directives-schema.json) - Plugin manifest schema
