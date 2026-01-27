"""
Benchmarks for ConversationFile parsing.

Measures:
- Parse time for various .conv sizes
- Directive processing overhead
- Memory usage patterns
"""

import statistics
import time
from pathlib import Path
from typing import NamedTuple

from sdqctl.core.conversation import ConversationFile


class BenchmarkResult(NamedTuple):
    """Result of a single benchmark."""

    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float


def _time_ms(func, iterations: int = 100, name: str | None = None) -> BenchmarkResult:
    """Time a function over multiple iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult(
        name=name or (func.__name__ if hasattr(func, "__name__") else "anonymous"),
        iterations=iterations,
        mean_ms=statistics.mean(times),
        std_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
    )


# Fixture: minimal .conv content
MINIMAL_CONV = """\
MODEL gpt-4
ADAPTER copilot

PROMPT Hello world
"""

# Fixture: small .conv with typical directives
SMALL_CONV = """\
MODEL claude-sonnet-4-20250514
ADAPTER copilot
MODE audit
MAX-CYCLES 3

CONTEXT @src/main.py
CONTEXT @lib/utils.py

PROMPT Analyze the code for issues.
PROMPT Generate a report.
"""

# Fixture: medium .conv with many directives
MEDIUM_CONV = """\
MODEL claude-sonnet-4-20250514
ADAPTER copilot
MODE refactor
MAX-CYCLES 5
SESSION-NAME medium-benchmark

CONTEXT @src/main.py
CONTEXT @src/utils.py
CONTEXT @src/config.py
CONTEXT @tests/test_main.py

PROLOGUE @prompts/system-context.md

RUN-ENV PATH=/usr/bin
RUN-ENV NODE_ENV=test

PROMPT Analyze the codebase structure.
RUN echo "Step 1 complete"
PROMPT Identify refactoring opportunities.
RUN echo "Step 2 complete"
PROMPT Generate implementation plan.
CHECKPOINT plan

PROMPT Implement changes.
VERIFY refs
CHECKPOINT complete
"""


def _generate_large_conv(num_contexts: int = 50, num_prompts: int = 20) -> str:
    """Generate a large .conv file for stress testing."""
    lines = [
        "MODEL claude-sonnet-4-20250514",
        "ADAPTER copilot",
        "MODE analyze",
        f"MAX-CYCLES {num_prompts}",
        "",
    ]

    # Add many context files
    for i in range(num_contexts):
        lines.append(f"CONTEXT @src/module_{i:03d}.py")

    lines.append("")

    # Add many prompts with intermixed commands
    for i in range(num_prompts):
        lines.append(f"PROMPT Analyze module {i} for issues.")
        if i % 5 == 0:
            lines.append(f"RUN echo 'Checkpoint {i}'")
        if i % 10 == 0:
            lines.append(f"CHECKPOINT step_{i}")

    return "\n".join(lines)


LARGE_CONV = _generate_large_conv()


def bench_parse_minimal() -> BenchmarkResult:
    """Benchmark parsing minimal .conv."""
    def parse():
        ConversationFile.parse(MINIMAL_CONV)

    return _time_ms(parse, iterations=1000, name="parse_minimal")


def bench_parse_small() -> BenchmarkResult:
    """Benchmark parsing small .conv."""
    def parse():
        ConversationFile.parse(SMALL_CONV)

    return _time_ms(parse, iterations=500, name="parse_small")


def bench_parse_medium() -> BenchmarkResult:
    """Benchmark parsing medium .conv."""
    def parse():
        ConversationFile.parse(MEDIUM_CONV)

    return _time_ms(parse, iterations=200, name="parse_medium")


def bench_parse_large() -> BenchmarkResult:
    """Benchmark parsing large .conv (50 contexts, 20 prompts)."""
    def parse():
        ConversationFile.parse(LARGE_CONV)

    return _time_ms(parse, iterations=50, name="parse_large")


def bench_parse_from_file(tmp_path: Path) -> BenchmarkResult:
    """Benchmark parsing from filesystem."""
    conv_file = tmp_path / "benchmark.conv"
    conv_file.write_text(MEDIUM_CONV)

    def parse():
        ConversationFile.from_file(conv_file)

    return _time_ms(parse, iterations=200, name="parse_from_file")


def run_all(tmp_path: Path | None = None) -> list[BenchmarkResult]:
    """Run all parsing benchmarks."""
    results = [
        bench_parse_minimal(),
        bench_parse_small(),
        bench_parse_medium(),
        bench_parse_large(),
    ]

    if tmp_path:
        results.append(bench_parse_from_file(tmp_path))

    return results


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        results = run_all(Path(tmp))
        print("\n=== Parsing Benchmarks ===\n")
        for r in results:
            print(f"{r.name}:")
            print(f"  mean: {r.mean_ms:.3f}ms (±{r.std_ms:.3f}ms)")
            print(f"  range: [{r.min_ms:.3f}ms, {r.max_ms:.3f}ms]")
            print(f"  iterations: {r.iterations}")
            print()
