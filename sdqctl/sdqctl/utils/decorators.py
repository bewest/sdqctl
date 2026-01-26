"""
Decorator utilities for common error handling patterns.

Provides decorators for wrapping functions with consistent error handling,
particularly for I/O operations that may raise FileNotFoundError,
PermissionError, or OSError.
"""

import functools
import sys
from typing import Callable, ParamSpec, TypeVar

import click

P = ParamSpec("P")
R = TypeVar("R")


def handle_io_errors(
    exit_code: int = 1,
    json_errors: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for consistent I/O error handling in CLI commands.

    Catches common file I/O exceptions and converts them to user-friendly
    error messages. Supports both regular output and JSON error format.

    Args:
        exit_code: Exit code to use on error (default: 1)
        json_errors: If True, output errors as JSON (default: False)

    Returns:
        Decorated function with I/O error handling

    Example:
        @click.command()
        @handle_io_errors()
        def my_command():
            content = Path("file.txt").read_text()  # May raise
            ...

        @click.command()
        @click.option("--json", is_flag=True)
        @handle_io_errors(json_errors=True)
        def my_json_command(json: bool):
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                _handle_error(
                    f"File not found: {_extract_path(e)}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
            except PermissionError as e:
                _handle_error(
                    f"Permission denied: {_extract_path(e)}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
            except OSError as e:
                _handle_error(
                    f"I/O error: {e}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
        return wrapper
    return decorator


def handle_io_errors_async(
    exit_code: int = 1,
    json_errors: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Async variant of handle_io_errors for async CLI commands.

    Args:
        exit_code: Exit code to use on error (default: 1)
        json_errors: If True, output errors as JSON (default: False)

    Returns:
        Decorated async function with I/O error handling

    Example:
        @click.command()
        @handle_io_errors_async()
        async def my_async_command():
            content = await aiofiles.open("file.txt").read()
            ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except FileNotFoundError as e:
                _handle_error(
                    f"File not found: {_extract_path(e)}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
            except PermissionError as e:
                _handle_error(
                    f"Permission denied: {_extract_path(e)}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
            except OSError as e:
                _handle_error(
                    f"I/O error: {e}",
                    exit_code,
                    json_errors or kwargs.get("json", False),
                )
        return wrapper
    return decorator


def _extract_path(exc: OSError) -> str:
    """Extract path from OSError for user-friendly messages."""
    if exc.filename is not None:
        return str(exc.filename)
    # Try to extract from error message
    msg = str(exc)
    if ":" in msg:
        # Format: "[Errno N] Message: path"
        parts = msg.rsplit(":", 1)
        if len(parts) == 2:
            path = parts[1].strip().strip("'\"")
            if path:
                return path
    return msg


def _handle_error(message: str, exit_code: int, json_output: bool) -> None:
    """Handle error with consistent output format."""
    if json_output:
        import json
        error_obj = {"error": message, "exit_code": exit_code}
        click.echo(json.dumps(error_obj))
    else:
        click.echo(f"Error: {message}", err=True)
    sys.exit(exit_code)
