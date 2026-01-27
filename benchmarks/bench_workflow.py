"""
Benchmarks for workflow execution timing.

Measures:
- Step execution overhead
- Verification timing
- Compaction impact
"""

import statistics
import time
from pathlib import Path
from typing import NamedTuple

from sdqctl.core.conversation import ConversationFile
from sdqctl.verifiers import VERIFIERS


class BenchmarkResult(NamedTuple):
    """Result of a single benchmark."""

    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float


def _time_ms(func, iterations: int = 100) -> BenchmarkResult:
    """Time a function over multiple iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return BenchmarkResult(
        name=func.__name__ if hasattr(func, "__name__") else "anonymous",
        iterations=iterations,
        mean_ms=statistics.mean(times),
        std_ms=statistics.stdev(times) if len(times) > 1 else 0,
        min_ms=min(times),
        max_ms=max(times),
    )


def bench_step_iteration() -> BenchmarkResult:
    """Benchmark iterating through workflow steps."""
    conv_text = "\n".join([
        "MODEL gpt-4",
        "ADAPTER copilot",
        "",
    ] + [f"PROMPT Step {i}" for i in range(50)] + [
        f"RUN echo step_{i}" for i in range(20)
    ])

    conv = ConversationFile.parse(conv_text)

    def iterate():
        for step in conv.steps:
            _ = step.type
            _ = step.content

    return _time_ms(iterate, iterations=1000)


def bench_verify_refs(tmp_path: Path) -> BenchmarkResult:
    """Benchmark refs verification."""
    # Create test directory structure
    docs = tmp_path / "docs_refs"
    docs.mkdir(exist_ok=True)
    for i in range(10):
        (docs / f"doc_{i}.md").write_text(f"# Doc {i}\n\nContent here.\n")

    # Create file with references
    readme = docs / "README.md"
    refs = "\n".join([f"See @docs_refs/doc_{i}.md" for i in range(5)])
    readme.write_text(f"# Project\n\n{refs}\n")

    verifier = VERIFIERS["refs"]()

    def verify():
        verifier.verify(docs)

    return _time_ms(verify, iterations=50)


def bench_verify_links(tmp_path: Path) -> BenchmarkResult:
    """Benchmark links verification."""
    docs = tmp_path / "docs_links"
    docs.mkdir(exist_ok=True)

    # Create files with internal links
    for i in range(5):
        links = "\n".join([f"[Link {j}](doc_{j}.md)" for j in range(5) if j != i])
        (docs / f"doc_{i}.md").write_text(f"# Doc {i}\n\n{links}\n")

    verifier = VERIFIERS["links"]()

    def verify():
        verifier.verify(docs)

    return _time_ms(verify, iterations=50)


def bench_verify_traceability(tmp_path: Path) -> BenchmarkResult:
    """Benchmark traceability verification."""
    docs = tmp_path / "docs_trace"
    docs.mkdir(exist_ok=True)

    # Create file with trace artifacts
    trace_content = "\n".join([
        "# Requirements",
        "",
        "## REQ-001: User Authentication",
        "Users must authenticate before accessing the system.",
        "Traced by: SPEC-001, TEST-001",
        "",
        "## SPEC-001: Auth Implementation",
        "Implements REQ-001 using OAuth2.",
        "",
        "## TEST-001: Auth Test",
        "Verifies REQ-001 authentication flow.",
        "",
    ] + [f"## UCA-{i:03d}: Unsafe action {i}\nMitigated by SC-{i:03d}.\n" for i in range(10)]
    + [f"## SC-{i:03d}: Safety constraint {i}\nAddresses UCA-{i:03d}.\n" for i in range(10)])

    (docs / "traceability.md").write_text(trace_content)

    verifier = VERIFIERS["traceability"]()

    def verify():
        verifier.verify(docs)

    return _time_ms(verify, iterations=30)


def bench_verify_all(tmp_path: Path) -> BenchmarkResult:
    """Benchmark running all verifiers."""
    docs = tmp_path / "docs_all"
    docs.mkdir(exist_ok=True)

    # Create minimal test content
    (docs / "README.md").write_text("# Docs\n\nSee [guide](guide.md).\n")
    (docs / "guide.md").write_text("# Guide\n\nContent here.\n")

    def verify_all():
        for name, verifier_cls in VERIFIERS.items():
            verifier = verifier_cls()
            verifier.verify(docs)

    return _time_ms(verify_all, iterations=20)


def run_all(tmp_path: Path | None = None) -> list[BenchmarkResult]:
    """Run all workflow benchmarks."""
    results = [bench_step_iteration()]

    if tmp_path:
        results.extend([
            bench_verify_refs(tmp_path),
            bench_verify_links(tmp_path),
            bench_verify_traceability(tmp_path),
            bench_verify_all(tmp_path),
        ])

    return results


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        results = run_all(Path(tmp))
        print("\n=== Workflow Benchmarks ===\n")
        for r in results:
            print(f"{r.name}:")
            print(f"  mean: {r.mean_ms:.3f}ms (±{r.std_ms:.3f}ms)")
            print(f"  range: [{r.min_ms:.3f}ms, {r.max_ms:.3f}ms]")
            print(f"  iterations: {r.iterations}")
            print()
