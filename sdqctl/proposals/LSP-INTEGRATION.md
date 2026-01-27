# Proposal: LSP Integration for Semantic Code Context

> **Status**: In Progress (Phase 2: 2/3 items complete)  
> **Date**: 2026-01-27  
> **Author**: sdqctl development  
> **Scope**: Language Server Protocol integration for type-aware code analysis  
> **Supersedes**: "LSP support for refcat" backlog item

---

## Implementation Progress

### Phase 1: Foundation ✅ Complete
- [x] `sdqctl/lsp/__init__.py` module structure
- [x] `LSPClient` base interface with TypeDefinition, SymbolInfo, LSPError
- [x] `lsp` subcommand with status, detect, type, symbol placeholders
- [x] TypeScript server detection (local node_modules + global PATH)
- [x] `sdqctl lsp status` command

### Phase 2: TypeScript Type Extraction 🔄 In Progress
- [x] `sdqctl lsp type <name>` - pattern-based type lookup
- [x] JSON output mode (`--json`) for type definitions
- [ ] `LSP type` directive for .conv workflows

### Phase 3: Future
- [ ] Symbol lookup implementation
- [ ] Additional language support (Swift, Kotlin, Python)
- [ ] Cross-project type comparison

---

## Problem Statement

Current code context injection (`REFCAT`, `sdqctl refcat`) is text-based:
- Extracts raw source lines by file:line range
- No semantic understanding of types, signatures, or relationships
- Cross-file analysis requires manual navigation
- Verification limited to "file exists" checks

**Nightscout ecosystem pain points**:
- 16+ repos in multiple languages (Swift, Kotlin, TypeScript, Python)
- Analysis docs manually extract type information from source
- Type drift between projects goes undetected
- Cross-project comparisons require reading many files

**Example**: To compare `Treatment` types across Loop (Swift) and AAPS (Kotlin), analysts must:
1. Find relevant files manually
2. Extract type definitions by reading source
3. Manually cross-reference fields
4. Hope types haven't changed since last analysis

With LSP, this could be: `sdqctl lsp types Treatment --repos Loop,AndroidAPS`

---

## Proposed Solution

### New Subcommand: `sdqctl lsp`

Dedicated command for LSP-powered semantic queries:

```bash
# Get type definition with full signature
sdqctl lsp type Treatment --repo externals/Loop

# Get function signature and doc comment
sdqctl lsp symbol deliverBolus --repo externals/AndroidAPS

# Find all implementations of an interface
sdqctl lsp implementations NightscoutUploader

# Get call hierarchy (who calls this?)
sdqctl lsp callers processRemoteCommand

# Cross-project type comparison
sdqctl lsp compare-types Treatment --repos Loop,AndroidAPS,Trio
```

### New Directive: `LSP`

Inject semantic context into workflows:

```dockerfile
# Inject type definition into prompt context
LSP type Treatment FROM externals/Loop/LoopCore/Models/

# Inject function signature
LSP symbol deliverBolus FROM externals/AndroidAPS

# Inject interface + all implementations
LSP implementations NightscoutUploader

# Multi-repo type comparison table
LSP compare Treatment ACROSS Loop,AndroidAPS,Trio
```

### Relationship to REFCAT

| Feature | REFCAT | LSP |
|---------|--------|-----|
| **Scope** | Text extraction | Semantic queries |
| **Input** | File:line ranges | Symbol names, types |
| **Output** | Raw source lines | Structured definitions |
| **Cross-file** | Manual | Automatic (follows references) |
| **Verification** | File exists | Symbol exists, type-correct |
| **Languages** | Any text | Supported by language server |

**REFCAT remains valuable** for:
- Comments and documentation blocks
- Configuration files (YAML, JSON)
- Files without language server support
- Precise line-range extraction

**LSP adds value** for:
- Type definitions and signatures
- Cross-file reference following
- Semantic search ("all classes implementing X")
- Type comparison across projects

---

## Architecture

### Language Server Management

```
┌─────────────────────────────────────────────────────────────┐
│                     sdqctl lsp command                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Swift     │  │   Kotlin    │  │ TypeScript  │  ...     │
│  │ sourcekit   │  │ kotlin-ls   │  │  tsserver   │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│              ┌───────────▼───────────┐                       │
│              │   LSP Client Layer    │                       │
│              │  (unified interface)  │                       │
│              └───────────────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Language Server Discovery

Option A: **Bundled servers** (simpler, larger install)
```yaml
# .sdqctl/lsp-config.yaml
servers:
  swift: sourcekit-lsp  # bundled or PATH
  kotlin: kotlin-language-server
  typescript: typescript-language-server
```

Option B: **Project detection** (flexible, requires setup)
```bash
# Auto-detect from project files
sdqctl lsp init externals/Loop        # Detects Swift, configures sourcekit
sdqctl lsp init externals/AndroidAPS  # Detects Kotlin, configures kotlin-ls
```

Option C: **Hybrid** (recommended)
- Auto-detect common setups
- Allow override via config
- Provide helpful error when server not found

---

## Implementation Phases

### Phase 1: Foundation (1-2 iterations) ✅ COMPLETE

- [x] Define LSP client interface in `sdqctl/lsp/` ✅ 2026-01-27
- [x] Add `lsp` CLI subcommand with status/detect ✅ 2026-01-27
- [x] Language detection (TypeScript, Swift, Kotlin, Python) ✅ 2026-01-27
- [x] TypeScript server detection (tsserver in PATH or node_modules) ✅ 2026-01-27

**Deliverables**:
- `sdqctl/lsp/__init__.py` - LSPClient protocol, TypeDefinition, detect_language() ✅
- `sdqctl/lsp/__init__.py` - TypeScriptClient, detect_tsserver() ✅
- `sdqctl/commands/lsp.py` - CLI with status, detect, type, symbol ✅
- `tests/test_lsp.py` - 30 tests ✅

### Phase 2: TypeScript Type Extraction (1-2 iterations)

- [ ] Implement TypeScript language server client
- [ ] Implement `sdqctl lsp type <name>` for TypeScript
- [ ] Add JSON output mode for type definitions
- [ ] Add `LSP type` directive for .conv workflows

**Deliverables**:
- Working TypeScript type extraction
- Directive support for workflows

### Phase 3: Multi-Language (1-2 iterations)

- [ ] Add Swift support (sourcekit-lsp)
- [ ] Add Kotlin support (kotlin-language-server)
- [ ] Add Python support (pyright or pylsp)
- [ ] Language server lifecycle management (start/stop/cache)

**Deliverables**:
- Support for Nightscout ecosystem primary languages
- Efficient server management

### Phase 4: Cross-Project Analysis (1 iteration)

- [ ] Implement `sdqctl lsp compare-types` across repos
- [ ] Add `LSP compare` directive
- [ ] Type diff visualization (table format)
- [ ] Integration with terminology matrix

**Deliverables**:
- Cross-project type comparison
- Integration with ecosystem analysis workflows

### Phase 4: Advanced Queries (1 iteration)

- [ ] Call hierarchy (callers/callees)
- [ ] Implementation finding
- [ ] Reference search
- [ ] Hover information extraction

**Deliverables**:
- Full semantic query suite
- Documentation

---

## Nightscout Ecosystem Use Cases

### UC1: Type Alignment Verification

**Current process** (manual):
1. Open Loop Treatment.swift
2. Read and document fields
3. Open AAPS Treatment.kt
4. Read and document fields
5. Manually compare
6. Write findings in terminology-matrix.md

**With LSP**:
```bash
sdqctl lsp compare-types Treatment --repos Loop,AndroidAPS,Trio \
  --output mapping/cross-project/treatment-comparison.md
```

### UC2: API Surface Extraction

**Current process**: Manually read source files, extract function signatures

**With LSP**:
```dockerfile
# In extract-spec.conv workflow
LSP type NightscoutAPI FROM externals/cgm-remote-monitor/lib/api3/
PROMPT Document all public methods and their parameters.
```

### UC3: Drift Detection

**Current process**: Re-read source when updating docs, hope to catch changes

**With LSP**:
```bash
# Compare current types to documented types
sdqctl lsp diff-types specs/treatment-schema.md externals/Loop
```

### UC4: Deep Dive Acceleration

**Current process**: Analyst reads multiple files to understand a feature

**With LSP**:
```dockerfile
# In deep-dive.conv workflow
LSP symbol processBolus FROM externals/Loop
LSP callers processBolus FROM externals/Loop
PROMPT Analyze this function and its call sites. Document the bolus flow.
```

---

## Open Questions

| ID | Question | Options | Status |
|----|----------|---------|--------|
| OQ-LSP-001 | Language server lifecycle | On-demand vs persistent vs hybrid | ✅ Answered |
| OQ-LSP-002 | Multi-repo indexing | Per-repo vs unified workspace | Open |
| OQ-LSP-003 | Caching strategy | In-memory vs disk cache | Open |
| OQ-LSP-004 | Error handling | Fallback to REFCAT vs fail | ✅ Answered |
| OQ-LSP-005 | Output format | Markdown vs JSON vs both | Open |

### OQ-LSP-001: Language Server Lifecycle (Answered 2026-01-27)

**Decision**: Hybrid approach with join capability

- **On-demand with idle timeout**: Start server when needed, keep alive for 5 minutes of idle
- **Join existing server**: Detect and connect to already-running LSP servers (e.g., from VS Code)
- **Rationale**: Balances resource efficiency with query performance; joining existing servers avoids duplicate indexing

### OQ-LSP-004: Error Handling (Answered 2026-01-27)

**Decision**: Fail fast by default, configurable fallback via CLI switch

- **Default**: Fail with clear error when LSP query fails (server unavailable, symbol not found)
- **Fallback**: `--lsp-fallback refcat` to attempt REFCAT text extraction as backup
- **Rationale**: Users need explicit control over failure behavior; silent fallbacks hide problems

---

## Lessons Learned (Informing Design)

From recent sdqctl development and ecosystem work:

1. **Process over domain**: LSP queries should be generic (`lsp type X`) not domain-specific (`lsp treatment`)
2. **Direction injection**: Allow `--prologue` style context: `sdqctl lsp type X --context "Focus on sync fields"`
3. **Typesetting metaphor**: Command naming should follow established patterns (lsp/refcat like prologue/epilogue)
4. **Agent output visibility**: LSP results should stream to stdout for observability
5. **Plugin system compatibility**: LSP could be a plugin, or plugins could extend LSP queries

---

## Success Criteria

1. **Semantic extraction**: Can get type definition without knowing file/line
2. **Cross-project**: Can compare same type across multiple repos
3. **Workflow integration**: LSP directive works in .conv files
4. **Performance**: Queries return in <5 seconds for indexed repos
5. **Ecosystem adoption**: Used in at least 2 ecosystem analysis workflows

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Language server complexity | High | Medium | Start with TypeScript (mature tooling) |
| Multi-language maintenance | Medium | High | Use established servers, don't build custom |
| Performance at scale | Medium | Medium | Index on-demand, cache results |
| Server availability | Low | High | Graceful fallback to REFCAT |

---

## References

### LSP Resources
- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [sourcekit-lsp](https://github.com/apple/sourcekit-lsp) (Swift)
- [kotlin-language-server](https://github.com/fwcd/kotlin-language-server)
- [typescript-language-server](https://github.com/typescript-language-server/typescript-language-server)

### sdqctl Proposals
- [REFCAT-DESIGN.md](REFCAT-DESIGN.md) - Text-based code extraction
- [PLUGIN-SYSTEM.md](PLUGIN-SYSTEM.md) - Extension mechanism
- [VERIFICATION-DIRECTIVES.md](VERIFICATION-DIRECTIVES.md) - Verification patterns

---

**Document Version**: 0.1  
**Last Updated**: 2026-01-27
