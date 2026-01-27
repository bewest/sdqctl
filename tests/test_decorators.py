"""Tests for error handling decorators."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from sdqctl.utils.decorators import (
    handle_io_errors,
    handle_io_errors_async,
    _extract_path,
)


class TestExtractPath:
    """Tests for _extract_path helper."""

    def test_extract_from_filename_attribute(self):
        """Extract path from OSError.filename."""
        exc = FileNotFoundError("No such file")
        exc.filename = "/path/to/file.txt"
        assert _extract_path(exc) == "/path/to/file.txt"

    def test_extract_from_message_colon_format(self):
        """Extract path from error message with colon format."""
        # Create error without setting filename (it stays None)
        exc = OSError("No such file or directory: '/path/to/file.txt'")
        assert _extract_path(exc) == "/path/to/file.txt"

    def test_fallback_to_message(self):
        """Return full message when path can't be extracted."""
        exc = OSError("Generic error without colon")
        assert _extract_path(exc) == "Generic error without colon"


class TestHandleIOErrors:
    """Tests for @handle_io_errors decorator."""

    def test_passes_through_on_success(self):
        """Decorator doesn't interfere with successful execution."""
        @handle_io_errors()
        def success_func():
            return "result"

        assert success_func() == "result"

    def test_catches_file_not_found(self):
        """FileNotFoundError is caught and exits."""
        @handle_io_errors()
        def raise_fnf():
            raise FileNotFoundError("test.txt")

        with pytest.raises(SystemExit) as exc_info:
            raise_fnf()
        assert exc_info.value.code == 1

    def test_catches_permission_error(self):
        """PermissionError is caught and exits."""
        @handle_io_errors()
        def raise_perm():
            exc = PermissionError("Access denied")
            exc.filename = "/etc/shadow"
            raise exc

        with pytest.raises(SystemExit) as exc_info:
            raise_perm()
        assert exc_info.value.code == 1

    def test_catches_os_error(self):
        """OSError is caught and exits."""
        @handle_io_errors()
        def raise_os():
            raise OSError("Disk full")

        with pytest.raises(SystemExit) as exc_info:
            raise_os()
        assert exc_info.value.code == 1

    def test_custom_exit_code(self):
        """Custom exit code is used."""
        @handle_io_errors(exit_code=42)
        def raise_fnf():
            raise FileNotFoundError("test.txt")

        with pytest.raises(SystemExit) as exc_info:
            raise_fnf()
        assert exc_info.value.code == 42

    def test_json_output_from_decorator(self, capsys):
        """JSON error output when json_errors=True in decorator."""
        @handle_io_errors(json_errors=True)
        def raise_fnf():
            exc = FileNotFoundError("File not found")
            exc.filename = "missing.txt"
            raise exc

        with pytest.raises(SystemExit):
            raise_fnf()

        captured = capsys.readouterr()
        error_data = json.loads(captured.out)
        assert "error" in error_data
        assert "missing.txt" in error_data["error"]
        assert error_data["exit_code"] == 1

    def test_json_output_from_kwarg(self, capsys):
        """JSON error output when json=True passed as kwarg."""
        @handle_io_errors()
        def raise_fnf(json=False):
            exc = FileNotFoundError("File not found")
            exc.filename = "missing.txt"
            raise exc

        with pytest.raises(SystemExit):
            raise_fnf(json=True)

        captured = capsys.readouterr()
        error_data = json.loads(captured.out)
        assert "error" in error_data

    def test_stderr_output_default(self, capsys):
        """Error message goes to stderr by default."""
        @handle_io_errors()
        def raise_fnf():
            exc = FileNotFoundError("File not found")
            exc.filename = "missing.txt"
            raise exc

        with pytest.raises(SystemExit):
            raise_fnf()

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "missing.txt" in captured.err

    def test_preserves_function_metadata(self):
        """Decorator preserves function name and docstring."""
        @handle_io_errors()
        def documented_func():
            """This is the docstring."""
            pass

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is the docstring."


class TestHandleIOErrorsAsync:
    """Tests for @handle_io_errors_async decorator."""

    @pytest.mark.asyncio
    async def test_passes_through_on_success(self):
        """Decorator doesn't interfere with successful async execution."""
        @handle_io_errors_async()
        async def success_func():
            return "async result"

        result = await success_func()
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_catches_file_not_found(self):
        """FileNotFoundError is caught in async function."""
        @handle_io_errors_async()
        async def raise_fnf():
            raise FileNotFoundError("async_test.txt")

        with pytest.raises(SystemExit) as exc_info:
            await raise_fnf()
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_custom_exit_code(self):
        """Custom exit code works in async."""
        @handle_io_errors_async(exit_code=99)
        async def raise_fnf():
            raise FileNotFoundError("test.txt")

        with pytest.raises(SystemExit) as exc_info:
            await raise_fnf()
        assert exc_info.value.code == 99

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Async decorator preserves function metadata."""
        @handle_io_errors_async()
        async def async_documented():
            """Async docstring."""
            pass

        assert async_documented.__name__ == "async_documented"
        assert async_documented.__doc__ == "Async docstring."
