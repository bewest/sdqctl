"""
LSP step execution for workflow directives.

Handles the LSP directive which injects type/symbol definitions into context.

Usage in .conv files:
    LSP type Treatment -p ./externals/Loop
    LSP type Bolus -l typescript
"""

import shlex
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

from ..core.logging import get_logger
from ..lsp import Language, LSPError, TypeDefinition, detect_language, get_client

logger = get_logger(__name__)


def execute_lsp_step(
    step: Any,
    conv: Any,
    session: Any,
    console: Console,
    progress_fn: Callable[[str], None],
) -> None:
    """Execute an LSP step, injecting type/symbol info into context.

    Args:
        step: The ConversationStep with type="lsp"
        conv: The ConversationFile
        session: The Session object
        console: Rich console for output
        progress_fn: Progress callback
    """
    content = step.content if hasattr(step, 'content') else step.get('content', '')

    if not content.strip():
        progress_fn("⚠ LSP: Empty directive")
        return

    # Parse the LSP command: type <name> [-p path] [-l lang]
    args = parse_lsp_args(content)

    if args.get("error"):
        progress_fn(f"⚠ LSP: {args['error']}")
        return

    subcommand = args.get("subcommand", "type")
    name = args.get("name", "")
    project_path = Path(args.get("path", ".")).resolve()
    language = args.get("language")

    # Use conv.cwd if set
    if conv.cwd:
        project_path = Path(conv.cwd).resolve()
        if args.get("path") and args["path"] != ".":
            project_path = project_path / args["path"]

    logger.info(f"LSP {subcommand}: {name} in {project_path}")
    progress_fn(f"🔍 LSP {subcommand}: {name}")

    if subcommand == "type":
        result = lookup_type(name, project_path, language)
    else:
        result = {"error": f"Unknown LSP subcommand: {subcommand}"}

    if "error" in result:
        progress_fn(f"⚠ LSP error: {result['error']}")
        # Still inject the error as context so the AI knows what happened
        error_msg = f"[LSP Error]\nFailed to look up {subcommand} '{name}': {result['error']}"
        session.add_message("system", error_msg)
        return

    # Inject the type definition into context
    type_def = result["type_definition"]
    context_msg = f"[LSP Type Definition]\n{type_def.to_markdown()}"
    session.add_message("system", context_msg)
    progress_fn(f"✓ LSP: Found {type_def.kind} {type_def.name}")


def parse_lsp_args(content: str) -> dict[str, Any]:
    """Parse LSP directive arguments.

    Format: type <name> [-p path] [-l lang]

    Returns:
        Dict with subcommand, name, path, language, or error
    """
    try:
        parts = shlex.split(content)
    except ValueError as e:
        return {"error": f"Invalid syntax: {e}"}

    if not parts:
        return {"error": "Empty LSP directive"}

    subcommand = parts[0].lower()
    if subcommand not in ("type", "symbol"):
        return {"error": f"Unknown LSP subcommand: {subcommand}"}

    result: dict[str, Any] = {
        "subcommand": subcommand,
        "path": ".",
        "language": None,
    }

    # Parse remaining args
    i = 1
    while i < len(parts):
        arg = parts[i]
        if arg in ("-p", "--path"):
            if i + 1 < len(parts):
                result["path"] = parts[i + 1]
                i += 2
            else:
                return {"error": "-p requires a path argument"}
        elif arg in ("-l", "--language"):
            if i + 1 < len(parts):
                result["language"] = parts[i + 1]
                i += 2
            else:
                return {"error": "-l requires a language argument"}
        elif not result.get("name"):
            result["name"] = arg
            i += 1
        else:
            # Extra positional arg
            i += 1

    if not result.get("name"):
        return {"error": f"LSP {subcommand} requires a name argument"}

    return result


def lookup_type(
    name: str,
    project_path: Path,
    language: str | None,
) -> dict[str, Any]:
    """Look up a type definition using LSP.

    Args:
        name: Type name to look up
        project_path: Project root directory
        language: Optional language hint

    Returns:
        Dict with type_definition or error
    """
    # Detect or use specified language
    if language:
        try:
            lang = Language(language.lower())
        except ValueError:
            return {"error": f"Unknown language: {language}"}
    else:
        lang = detect_language(project_path)
        if not lang:
            return {"error": f"Could not detect language in {project_path}"}

    # Get client
    client = get_client(lang, project_path)
    if not client:
        return {"error": f"No {lang.value} language server available"}

    # Look up type
    result = client.get_type(name)

    if isinstance(result, LSPError):
        return {"error": result.message}

    return {"type_definition": result}
