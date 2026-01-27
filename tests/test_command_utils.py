"""Tests for sdqctl command utilities."""

import asyncio

import pytest

from sdqctl.commands.utils import run_async

pytestmark = pytest.mark.unit


class TestRunAsync:
    """Test run_async utility function."""

    def test_executes_simple_coroutine(self):
        """Executes a basic async function and returns result."""
        async def simple():
            return 42

        result = run_async(simple())
        assert result == 42

    def test_executes_async_with_await(self):
        """Executes coroutine that awaits other async calls."""
        async def with_sleep():
            await asyncio.sleep(0.001)
            return "completed"

        result = run_async(with_sleep())
        assert result == "completed"

    def test_returns_none_from_void_coroutine(self):
        """Handles coroutines that return None."""
        async def void_func():
            pass

        result = run_async(void_func())
        assert result is None

    def test_returns_complex_types(self):
        """Returns complex data structures from coroutines."""
        async def complex_return():
            return {"key": "value", "list": [1, 2, 3]}

        result = run_async(complex_return())
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_propagates_exceptions(self):
        """Exceptions from coroutines are propagated."""
        async def raises():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async(raises())

    def test_propagates_custom_exceptions(self):
        """Custom exception types are preserved."""
        class CustomError(Exception):
            pass

        async def raises_custom():
            raise CustomError("custom message")

        with pytest.raises(CustomError, match="custom message"):
            run_async(raises_custom())

    def test_handles_async_generator_consumed(self):
        """Can handle async functions that use async iterators."""
        async def with_async_iteration():
            results = []
            async def async_gen():
                for i in range(3):
                    yield i
            async for item in async_gen():
                results.append(item)
            return results

        result = run_async(with_async_iteration())
        assert result == [0, 1, 2]

    def test_multiple_sequential_calls(self):
        """Can be called multiple times sequentially."""
        async def counter(n):
            return n * 2

        results = [run_async(counter(i)) for i in range(5)]
        assert results == [0, 2, 4, 6, 8]

    def test_handles_nested_async_calls(self):
        """Handles coroutines that call other coroutines."""
        async def inner():
            return 10

        async def outer():
            val = await inner()
            return val + 5

        result = run_async(outer())
        assert result == 15

    def test_handles_async_with_gather(self):
        """Handles asyncio.gather for concurrent execution."""
        async def task(n):
            await asyncio.sleep(0.001)
            return n

        async def with_gather():
            results = await asyncio.gather(task(1), task(2), task(3))
            return list(results)

        result = run_async(with_gather())
        assert result == [1, 2, 3]

    def test_timeout_propagates(self):
        """asyncio.TimeoutError is propagated."""
        async def slow():
            await asyncio.sleep(10)
            return "done"

        async def with_timeout():
            return await asyncio.wait_for(slow(), timeout=0.001)

        with pytest.raises(asyncio.TimeoutError):
            run_async(with_timeout())

    def test_cancellation_error_propagates(self):
        """CancelledError is propagated when task is cancelled."""
        async def cancellable():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        async def cancel_self():
            task = asyncio.current_task()
            task.cancel()
            await asyncio.sleep(0)  # Allow cancellation to take effect

        with pytest.raises(asyncio.CancelledError):
            run_async(cancel_self())


class TestRunAsyncReturnTypes:
    """Test run_async handles various return types correctly."""

    def test_returns_string(self):
        """Returns string from coroutine."""
        async def string_func():
            return "hello"

        assert run_async(string_func()) == "hello"

    def test_returns_list(self):
        """Returns list from coroutine."""
        async def list_func():
            return [1, 2, 3]

        assert run_async(list_func()) == [1, 2, 3]

    def test_returns_tuple(self):
        """Returns tuple from coroutine."""
        async def tuple_func():
            return (1, "two", 3.0)

        assert run_async(tuple_func()) == (1, "two", 3.0)

    def test_returns_dataclass(self):
        """Returns dataclass instance from coroutine."""
        from dataclasses import dataclass

        @dataclass
        class Result:
            value: int
            message: str

        async def dataclass_func():
            return Result(value=42, message="success")

        result = run_async(dataclass_func())
        assert result.value == 42
        assert result.message == "success"

    def test_returns_exception_as_value(self):
        """Can return exception as value (not raise it)."""
        async def exception_value():
            return ValueError("not raised")

        result = run_async(exception_value())
        assert isinstance(result, ValueError)
        assert str(result) == "not raised"


class TestResolveRunDirectory:
    """Test resolve_run_directory utility function."""

    def test_returns_cwd_when_no_overrides(self):
        """Returns current working directory when no overrides specified."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        result = resolve_run_directory(None, None, None)
        assert result == Path.cwd()

    def test_uses_cwd_directive(self):
        """Uses CWD directive when specified."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        result = resolve_run_directory(None, "/tmp", None)
        assert result == Path("/tmp")

    def test_run_cwd_overrides_cwd(self):
        """RUN-CWD takes priority over CWD."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        result = resolve_run_directory("/opt", "/tmp", None)
        assert result == Path("/opt")

    def test_relative_run_cwd_resolved_to_source(self, tmp_path):
        """Relative RUN-CWD is resolved relative to source file."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        source_path = tmp_path / "workflow.conv"
        result = resolve_run_directory("subdir", None, source_path)
        assert result == tmp_path / "subdir"

    def test_relative_run_cwd_no_source_uses_cwd(self):
        """Relative RUN-CWD uses CWD when no source file."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        result = resolve_run_directory("subdir", None, None)
        assert result == Path.cwd() / "subdir"

    def test_absolute_run_cwd_not_modified(self):
        """Absolute RUN-CWD is used as-is."""
        from pathlib import Path
        from sdqctl.commands.utils import resolve_run_directory

        result = resolve_run_directory("/absolute/path", None, Path("/some/source.conv"))
        assert result == Path("/absolute/path")
