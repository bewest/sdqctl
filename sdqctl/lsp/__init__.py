"""
LSP (Language Server Protocol) integration for sdqctl.

Provides semantic code context through language servers:
- Type definitions and signatures
- Symbol lookup and navigation
- Cross-file reference following
- Type comparison across projects

See: proposals/LSP-INTEGRATION.md

Usage:
    from sdqctl.lsp import LSPClient, get_client

    client = get_client("typescript", project_root)
    type_def = client.get_type("Treatment")
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class Language(Enum):
    """Supported languages for LSP integration."""

    TYPESCRIPT = "typescript"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    PYTHON = "python"


@dataclass
class TypeDefinition:
    """Structured type definition from language server."""

    name: str
    language: Language
    kind: str  # class, interface, struct, type, enum
    file_path: Path
    line: int
    signature: str  # Full type signature
    doc_comment: str | None = None
    fields: list[dict[str, Any]] = field(default_factory=list)
    methods: list[dict[str, Any]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render type definition as markdown."""
        lines = [
            f"## {self.name}",
            f"**Kind**: {self.kind}",
            f"**File**: `{self.file_path}:{self.line}`",
            "",
            "```" + self.language.value,
            self.signature,
            "```",
        ]
        if self.doc_comment:
            lines.extend(["", self.doc_comment])
        return "\n".join(lines)


@dataclass
class SymbolInfo:
    """Information about a code symbol."""

    name: str
    kind: str  # function, method, variable, constant, etc.
    file_path: Path
    line: int
    signature: str
    doc_comment: str | None = None


@dataclass
class LSPError:
    """Error from LSP operation."""

    message: str
    code: str | None = None
    file_path: Path | None = None


class LSPClient(Protocol):
    """Protocol for language server clients.

    Implementations must provide semantic queries for their language.
    """

    @property
    def language(self) -> Language:
        """The language this client handles."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the language server is available."""
        ...

    def initialize(self, project_root: Path) -> bool:
        """Initialize connection to language server.

        Args:
            project_root: Root directory of the project to analyze

        Returns:
            True if initialization succeeded
        """
        ...

    def shutdown(self) -> None:
        """Shutdown the language server connection."""
        ...

    def get_type(self, name: str) -> TypeDefinition | LSPError:
        """Get type definition by name.

        Args:
            name: Type name to look up

        Returns:
            TypeDefinition if found, LSPError otherwise
        """
        ...

    def get_symbol(self, name: str) -> SymbolInfo | LSPError:
        """Get symbol information by name.

        Args:
            name: Symbol name to look up

        Returns:
            SymbolInfo if found, LSPError otherwise
        """
        ...

    def find_references(self, name: str) -> list[Path] | LSPError:
        """Find all references to a symbol.

        Args:
            name: Symbol name to search for

        Returns:
            List of file paths containing references, or LSPError
        """
        ...


# Registry of available LSP clients
_CLIENTS: dict[Language, type] = {}


def register_client(language: Language):
    """Decorator to register an LSP client implementation."""

    def decorator(cls: type) -> type:
        _CLIENTS[language] = cls
        return cls

    return decorator


def get_client(language: str | Language, project_root: Path) -> LSPClient | None:
    """Get an LSP client for the specified language.

    Args:
        language: Language name or Language enum
        project_root: Root directory of the project

    Returns:
        Initialized LSPClient, or None if not available
    """
    if isinstance(language, str):
        try:
            lang = Language(language.lower())
        except ValueError:
            return None
    else:
        lang = language

    client_cls = _CLIENTS.get(lang)
    if client_cls is None:
        return None

    client = client_cls()
    if client.initialize(project_root):
        return client
    return None


def detect_language(project_root: Path) -> Language | None:
    """Detect primary language of a project.

    Args:
        project_root: Root directory to analyze

    Returns:
        Detected Language, or None if unknown
    """
    # Check for language-specific marker files
    markers = {
        Language.TYPESCRIPT: ["tsconfig.json", "package.json"],
        Language.SWIFT: ["Package.swift", "*.xcodeproj"],
        Language.KOTLIN: ["build.gradle.kts", "build.gradle"],
        Language.PYTHON: ["pyproject.toml", "setup.py", "requirements.txt"],
    }

    for lang, files in markers.items():
        for pattern in files:
            if "*" in pattern:
                if list(project_root.glob(pattern)):
                    return lang
            elif (project_root / pattern).exists():
                return lang

    return None


def list_available_servers() -> dict[Language, bool]:
    """List all supported languages and their availability.

    Returns:
        Dict mapping Language to whether server is available
    """
    result = {}
    for lang in Language:
        client_cls = _CLIENTS.get(lang)
        if client_cls:
            client = client_cls()
            result[lang] = client.is_available
        else:
            result[lang] = False
    return result


def detect_tsserver(project_root: Path | None = None) -> Path | None:
    """Detect TypeScript server (tsserver) location.

    Checks in order:
    1. Local node_modules/.bin/tsserver (if project_root provided)
    2. Global tsserver in PATH

    Args:
        project_root: Optional project directory to check for local install

    Returns:
        Path to tsserver executable, or None if not found
    """
    import shutil

    # Check local node_modules first
    if project_root:
        local_tsserver = project_root / "node_modules" / ".bin" / "tsserver"
        if local_tsserver.exists():
            return local_tsserver

    # Check global PATH
    global_tsserver = shutil.which("tsserver")
    if global_tsserver:
        return Path(global_tsserver)

    return None


@register_client(Language.TYPESCRIPT)
class TypeScriptClient:
    """TypeScript language server client using tsserver."""

    def __init__(self):
        self._tsserver_path: Path | None = None
        self._project_root: Path | None = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if tsserver is available."""
        return detect_tsserver(self._project_root) is not None

    @property
    def server_path(self) -> Path | None:
        """Get the detected tsserver path."""
        if self._tsserver_path is None:
            self._tsserver_path = detect_tsserver(self._project_root)
        return self._tsserver_path

    @property
    def version(self) -> str | None:
        """Get TypeScript version."""
        if not self.server_path:
            return None
        # tsserver doesn't have --version, check typescript package
        if self._project_root:
            pkg_json = self._project_root / "node_modules" / "typescript" / "package.json"
            if pkg_json.exists():
                import json
                try:
                    data = json.loads(pkg_json.read_text())
                    return data.get("version")
                except (json.JSONDecodeError, OSError):
                    pass
        return "unknown"

    def initialize(self, project_root: Path) -> bool:
        """Initialize client for a project.

        Args:
            project_root: Root directory of the TypeScript project

        Returns:
            True if initialization successful
        """
        self._project_root = project_root
        self._tsserver_path = detect_tsserver(project_root)
        self._initialized = self._tsserver_path is not None
        return self._initialized

    def shutdown(self) -> None:
        """Shutdown the client."""
        self._initialized = False

    def _find_type_definition(self, name: str) -> TypeDefinition | LSPError:
        """Find type definition using pattern matching.

        Searches TypeScript files for interface, type, class, and enum declarations.
        """
        import re
        import subprocess

        # Patterns for TypeScript type declarations
        patterns = [
            (r'^(?:export\s+)?interface\s+' + re.escape(name) + r'\b', 'interface'),
            (r'^(?:export\s+)?type\s+' + re.escape(name) + r'\s*=', 'type'),
            (r'^(?:export\s+)?class\s+' + re.escape(name) + r'\b', 'class'),
            (r'^(?:export\s+)?enum\s+' + re.escape(name) + r'\b', 'enum'),
        ]

        # Search TypeScript files
        ts_files = list(self._project_root.rglob("*.ts"))
        ts_files.extend(self._project_root.rglob("*.tsx"))

        # Skip node_modules and dist
        ts_files = [
            f for f in ts_files
            if "node_modules" not in str(f) and "dist" not in str(f)
        ]

        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, start=1):
                    for pattern, kind in patterns:
                        if re.match(pattern, line.strip()):
                            # Extract the full signature (multiline support)
                            signature = self._extract_signature(lines, line_num - 1)
                            doc_comment = self._extract_doc_comment(lines, line_num - 1)

                            return TypeDefinition(
                                name=name,
                                language=Language.TYPESCRIPT,
                                kind=kind,
                                file_path=ts_file.relative_to(self._project_root),
                                line=line_num,
                                signature=signature,
                                doc_comment=doc_comment,
                                fields=self._extract_fields(signature, kind),
                                methods=self._extract_methods(signature, kind),
                            )
            except (OSError, UnicodeDecodeError):
                continue

        return LSPError(
            message=f"Type '{name}' not found in {len(ts_files)} TypeScript files",
            code="NOT_FOUND",
        )

    def _extract_signature(self, lines: list[str], start_idx: int, max_lines: int = 50) -> str:
        """Extract full type signature including body."""
        result = []
        brace_count = 0
        started = False
        first_line = lines[start_idx].strip()

        # For type aliases (no braces), just return the single line
        if first_line.startswith("export type") or first_line.startswith("type "):
            return lines[start_idx]

        for i in range(start_idx, min(start_idx + max_lines, len(lines))):
            line = lines[i]
            result.append(line)

            brace_count += line.count("{") - line.count("}")

            if "{" in line:
                started = True

            if started and brace_count <= 0:
                break

        return "\n".join(result)

    def _extract_doc_comment(self, lines: list[str], start_idx: int) -> str | None:
        """Extract JSDoc comment above the definition."""
        if start_idx == 0:
            return None

        # Look for /** ... */ above
        doc_lines = []
        for i in range(start_idx - 1, max(start_idx - 20, -1), -1):
            line = lines[i].strip()
            if line.endswith("*/"):
                doc_lines.insert(0, line)
            elif line.startswith("*") or line.startswith("/**"):
                doc_lines.insert(0, line)
                if line.startswith("/**"):
                    return "\n".join(doc_lines)
            elif doc_lines:
                break
            elif line and not line.startswith("//"):
                break

        return None

    def _extract_fields(self, signature: str, kind: str) -> list[dict[str, Any]]:
        """Extract field definitions from signature."""
        import re

        fields = []
        if kind not in ("interface", "type", "class"):
            return fields

        # Simple field pattern: name: type or name?: type
        field_pattern = r'^\s*(?:readonly\s+)?(\w+)(\?)?:\s*([^;]+);?'

        for line in signature.split("\n"):
            match = re.match(field_pattern, line.strip())
            if match:
                fields.append({
                    "name": match.group(1),
                    "optional": match.group(2) == "?",
                    "type": match.group(3).strip().rstrip(";"),
                })

        return fields

    def _extract_methods(self, signature: str, kind: str) -> list[dict[str, Any]]:
        """Extract method definitions from signature."""
        import re

        methods = []
        if kind not in ("interface", "class"):
            return methods

        # Method pattern: name(params): returnType or name(params) =>
        method_pattern = r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*([^{;]+))?'

        for line in signature.split("\n"):
            match = re.match(method_pattern, line.strip())
            if match and match.group(1) not in ("if", "for", "while", "switch"):
                methods.append({
                    "name": match.group(1),
                    "return_type": (match.group(2) or "void").strip(),
                })

        return methods

    def get_type(self, name: str) -> TypeDefinition | LSPError:
        """Get type definition by name.

        Uses grep-based search to find type definitions in TypeScript files.
        Searches for: interface, type, class, enum declarations.

        Args:
            name: Type name to look up (case-sensitive)

        Returns:
            TypeDefinition if found, LSPError otherwise
        """
        if not self._initialized:
            return LSPError(message="Client not initialized", code="NOT_INITIALIZED")

        if not self._project_root:
            return LSPError(message="No project root set", code="NO_PROJECT")

        return self._find_type_definition(name)

    def get_symbol(self, name: str) -> SymbolInfo | LSPError:
        """Get symbol information by name.

        Note: Full implementation coming in Phase 2.
        """
        if not self._initialized:
            return LSPError(message="Client not initialized", code="NOT_INITIALIZED")
        return LSPError(message="Symbol lookup coming in Phase 2", code="NOT_IMPLEMENTED")

    def find_references(self, name: str) -> list[Path] | LSPError:
        """Find all references to a symbol.

        Note: Full implementation coming in Phase 2.
        """
        if not self._initialized:
            return LSPError(message="Client not initialized", code="NOT_INITIALIZED")
        return LSPError(message="Reference search coming in Phase 2", code="NOT_IMPLEMENTED")


__all__ = [
    "Language",
    "TypeDefinition",
    "SymbolInfo",
    "LSPError",
    "LSPClient",
    "register_client",
    "get_client",
    "detect_language",
    "list_available_servers",
    "detect_tsserver",
    "TypeScriptClient",
]
