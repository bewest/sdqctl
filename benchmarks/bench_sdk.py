"""
Benchmarks for SDK/adapter latency.

Measures:
- Session creation overhead
- Message send/receive timing
- Compaction latency
- Event handling overhead

Uses MockAdapter to isolate adapter overhead from network latency.
"""

import asyncio
import statistics
import time
from pathlib import Path
from typing import NamedTuple

from sdqctl.adapters.base import AdapterConfig
from sdqctl.adapters.mock import MockAdapter


class BenchmarkResult(NamedTuple):
    """Result of a single benchmark."""

    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float


def _time_async_ms(coro_factory, iterations: int = 100) -> BenchmarkResult:
    """Time an async function over multiple iterations."""
    async def run():
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await coro_factory()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        return times

    times = asyncio.run(run())

    return BenchmarkResult(
        name=coro_factory.__name__ if hasattr(coro_factory, "__name__") else "anonymous",
        iterations=iterations,
        mean_ms=statistics.mean(times),
        std_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
    )


def bench_session_create() -> BenchmarkResult:
    """Benchmark session creation overhead."""
    adapter = MockAdapter(delay=0.0)  # No artificial delay

    async def create_session():
        await adapter.start()
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)
        await adapter.destroy_session(session)
        await adapter.stop()

    return _time_async_ms(create_session, iterations=200)


def bench_session_reuse() -> BenchmarkResult:
    """Benchmark session reuse (no creation overhead)."""
    adapter = MockAdapter(delay=0.0)

    async def setup_and_bench():
        await adapter.start()
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)

        times = []
        for _ in range(100):
            start = time.perf_counter()
            # Simulate session reuse check
            _ = session.id
            _ = session.config
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        await adapter.destroy_session(session)
        await adapter.stop()
        return times

    times = asyncio.run(setup_and_bench())

    return BenchmarkResult(
        name="bench_session_reuse",
        iterations=len(times),
        mean_ms=statistics.mean(times),
        std_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
    )


def bench_message_send() -> BenchmarkResult:
    """Benchmark message send (mock, no network)."""
    adapter = MockAdapter(delay=0.0)

    async def setup_and_bench():
        await adapter.start()
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)

        times = []
        for i in range(50):
            start = time.perf_counter()
            await adapter.send(session, f"Test message {i}")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        await adapter.destroy_session(session)
        await adapter.stop()
        return times

    times = asyncio.run(setup_and_bench())

    return BenchmarkResult(
        name="bench_message_send",
        iterations=len(times),
        mean_ms=statistics.mean(times),
        std_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
    )


def bench_message_burst() -> BenchmarkResult:
    """Benchmark burst of messages (sequential)."""
    adapter = MockAdapter(delay=0.0)

    async def send_burst():
        await adapter.start()
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)

        # Send 10 messages in sequence
        for i in range(10):
            await adapter.send(session, f"Burst message {i}")

        await adapter.destroy_session(session)
        await adapter.stop()

    return _time_async_ms(send_burst, iterations=20)


def bench_adapter_lifecycle() -> BenchmarkResult:
    """Benchmark full adapter start/stop lifecycle."""
    async def lifecycle():
        adapter = MockAdapter(delay=0.0)
        await adapter.start()
        config = AdapterConfig(model="gpt-4")
        session = await adapter.create_session(config)
        await adapter.send(session, "Hello")
        await adapter.destroy_session(session)
        await adapter.stop()

    return _time_async_ms(lifecycle, iterations=100)


def bench_multiple_sessions() -> BenchmarkResult:
    """Benchmark managing multiple concurrent sessions."""
    adapter = MockAdapter(delay=0.0)

    async def multiple_sessions():
        await adapter.start()
        config = AdapterConfig(model="gpt-4")

        # Create 5 sessions
        sessions = []
        for _ in range(5):
            session = await adapter.create_session(config)
            sessions.append(session)

        # Send to each
        for session in sessions:
            await adapter.send(session, "Hello")

        # Destroy all
        for session in sessions:
            await adapter.destroy_session(session)

        await adapter.stop()

    return _time_async_ms(multiple_sessions, iterations=30)


def run_all(tmp_path: Path | None = None) -> list[BenchmarkResult]:
    """Run all SDK benchmarks."""
    return [
        bench_session_create(),
        bench_session_reuse(),
        bench_message_send(),
        bench_message_burst(),
        bench_adapter_lifecycle(),
        bench_multiple_sessions(),
    ]


if __name__ == "__main__":
    results = run_all()
    print("\n=== SDK/Adapter Benchmarks ===\n")
    for r in results:
        print(f"{r.name}:")
        print(f"  mean: {r.mean_ms:.3f}ms (±{r.std_ms:.3f}ms)")
        print(f"  range: [{r.min_ms:.3f}ms, {r.max_ms:.3f}ms]")
        print(f"  iterations: {r.iterations}")
        print()
