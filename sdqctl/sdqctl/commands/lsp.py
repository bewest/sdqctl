"""
sdqctl lsp - Language Server Protocol commands.

Usage:
    sdqctl lsp status              # Show available language servers
    sdqctl lsp type <name>         # Get type definition (Phase 2)
    sdqctl lsp symbol <name>       # Get symbol info (Phase 2)
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group("lsp")
def lsp():
    """Language Server Protocol integration.

    Query semantic code context through language servers.
    Supports TypeScript, Swift, Kotlin, and Python.

    \b
    Examples:
      sdqctl lsp status                    # Show available servers
      sdqctl lsp type Treatment -p ./src   # Get type definition (Phase 2)
    """
    pass


@lsp.command("status")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def lsp_status(json_output: bool):
    """Show available language servers.

    Lists all supported languages and whether their
    language server is available on this system.

    \b
    Examples:
      sdqctl lsp status          # Table output
      sdqctl lsp status --json   # JSON output for scripts
    """
    from sdqctl.lsp import Language, list_available_servers

    servers = list_available_servers()

    if json_output:
        import json

        data = {lang.value: available for lang, available in servers.items()}
        console.print_json(json.dumps(data))
        return

    table = Table(title="Language Server Status")
    table.add_column("Language", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Server", style="dim")

    server_names = {
        Language.TYPESCRIPT: "typescript-language-server",
        Language.SWIFT: "sourcekit-lsp",
        Language.KOTLIN: "kotlin-language-server",
        Language.PYTHON: "pylsp / pyright",
    }

    for lang in Language:
        available = servers.get(lang, False)
        status = "✓ Available" if available else "✗ Not found"
        status_style = "green" if available else "red"
        table.add_row(
            lang.value.capitalize(),
            f"[{status_style}]{status}[/{status_style}]",
            server_names.get(lang, "unknown"),
        )

    console.print(table)
    console.print()
    console.print("[dim]Note: Language server implementations coming in Phase 2[/dim]")


@lsp.command("detect")
@click.argument("path", type=click.Path(exists=True), default=".")
def lsp_detect(path: str):
    """Detect primary language of a project.

    \b
    Examples:
      sdqctl lsp detect                    # Current directory
      sdqctl lsp detect ./externals/Loop   # Specific project
    """
    from sdqctl.lsp import detect_language

    project_path = Path(path).resolve()
    lang = detect_language(project_path)

    if lang:
        console.print(f"Detected: [cyan]{lang.value}[/cyan]")
    else:
        console.print("[yellow]No recognized project type found[/yellow]")
        console.print("Supported: TypeScript, Swift, Kotlin, Python")


@lsp.command("type")
@click.argument("name", required=True)
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Project root directory")
@click.option("--language", "-l", type=str, default=None,
              help="Language (auto-detected if not specified)")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def lsp_type(name: str, path: str, language: str | None, json_output: bool):
    """Get type definition by name.

    Queries the language server for a type definition and returns
    its full signature, fields, and documentation.

    \b
    Examples:
      sdqctl lsp type Treatment                    # Current directory
      sdqctl lsp type Treatment -p ./externals/Loop
      sdqctl lsp type Bolus -l typescript --json
    """
    import json as json_lib

    from sdqctl.lsp import Language, LSPError, get_client, detect_language

    project_path = Path(path).resolve()

    # Detect or use specified language
    if language:
        try:
            lang = Language(language.lower())
        except ValueError:
            console.print(f"[red]Unknown language: {language}[/red]")
            console.print(f"Supported: {', '.join(l.value for l in Language)}")
            raise SystemExit(1)
    else:
        lang = detect_language(project_path)
        if not lang:
            console.print("[yellow]Could not detect project language[/yellow]")
            console.print("Use --language to specify: typescript, swift, kotlin, python")
            raise SystemExit(1)

    # Get client and look up type
    client = get_client(lang, project_path)
    if not client:
        console.print(f"[red]No {lang.value} language server available[/red]")
        raise SystemExit(1)

    result = client.get_type(name)

    if isinstance(result, LSPError):
        if json_output:
            console.print_json(json_lib.dumps({
                "error": True,
                "code": result.code,
                "message": result.message,
            }))
        else:
            console.print(f"[red]Error: {result.message}[/red]")
            if result.code:
                console.print(f"[dim]Code: {result.code}[/dim]")
        raise SystemExit(1)

    # Success - output type definition
    if json_output:
        data = {
            "name": result.name,
            "kind": result.kind,
            "language": result.language.value,
            "file": str(result.file_path),
            "line": result.line,
            "signature": result.signature,
            "doc_comment": result.doc_comment,
            "fields": result.fields,
            "methods": result.methods,
        }
        console.print_json(json_lib.dumps(data))
    else:
        console.print(result.to_markdown())


@lsp.command("symbol")
@click.argument("name", required=True)
@click.option("--path", "-p", type=click.Path(exists=True), default=".",
              help="Project root directory")
@click.option("--language", "-l", type=str, default=None,
              help="Language (auto-detected if not specified)")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def lsp_symbol(name: str, path: str, language: str | None, json_output: bool):
    """Get symbol information by name.

    Queries the language server for a symbol (function, variable, constant)
    and returns its signature and documentation.

    \b
    Examples:
      sdqctl lsp symbol deliverBolus
      sdqctl lsp symbol processRemoteCommand -p ./externals/AAPS
    """
    console.print("[yellow]Symbol lookup not yet implemented[/yellow]")
    console.print("Coming in WP-006 Phase 2")
    console.print()
    console.print(f"Would look up: [cyan]{name}[/cyan]")
    raise SystemExit(1)
