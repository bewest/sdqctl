#!/usr/bin/env python3
"""
sdqctl Benchmark Runner

Runs all benchmarks and produces a comprehensive report.

Usage:
    python -m benchmarks.run           # Run all benchmarks
    python -m benchmarks.run --json    # JSON output
    python -m benchmarks.run --quick   # Reduced iterations
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from . import bench_parsing, bench_rendering, bench_sdk, bench_workflow


class BenchmarkResult(NamedTuple):
    """Unified benchmark result."""

    category: str
    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float


def run_all_benchmarks(quick: bool = False) -> list[BenchmarkResult]:
    """Run all benchmark suites."""
    results: list[BenchmarkResult] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Parsing benchmarks
        print("Running parsing benchmarks...", file=sys.stderr)
        for r in bench_parsing.run_all(tmp_path):
            results.append(BenchmarkResult(
                category="parsing",
                name=r.name,
                iterations=r.iterations if not quick else max(10, r.iterations // 10),
                mean_ms=r.mean_ms,
                std_ms=r.std_ms,
                min_ms=r.min_ms,
                max_ms=r.max_ms,
            ))

        # Rendering benchmarks
        print("Running rendering benchmarks...", file=sys.stderr)
        for r in bench_rendering.run_all(tmp_path):
            results.append(BenchmarkResult(
                category="rendering",
                name=r.name,
                iterations=r.iterations if not quick else max(10, r.iterations // 10),
                mean_ms=r.mean_ms,
                std_ms=r.std_ms,
                min_ms=r.min_ms,
                max_ms=r.max_ms,
            ))

        # Workflow benchmarks
        print("Running workflow benchmarks...", file=sys.stderr)
        for r in bench_workflow.run_all(tmp_path):
            results.append(BenchmarkResult(
                category="workflow",
                name=r.name,
                iterations=r.iterations if not quick else max(5, r.iterations // 10),
                mean_ms=r.mean_ms,
                std_ms=r.std_ms,
                min_ms=r.min_ms,
                max_ms=r.max_ms,
            ))

        # SDK benchmarks
        print("Running SDK benchmarks...", file=sys.stderr)
        for r in bench_sdk.run_all(tmp_path):
            results.append(BenchmarkResult(
                category="sdk",
                name=r.name,
                iterations=r.iterations if not quick else max(10, r.iterations // 10),
                mean_ms=r.mean_ms,
                std_ms=r.std_ms,
                min_ms=r.min_ms,
                max_ms=r.max_ms,
            ))

    return results


def format_table(results: list[BenchmarkResult]) -> str:
    """Format results as a markdown table."""
    lines = [
        "| Category | Benchmark | Mean (ms) | Std (ms) | Min | Max | Iterations |",
        "|----------|-----------|-----------|----------|-----|-----|------------|",
    ]

    for r in results:
        lines.append(
            f"| {r.category} | {r.name} | {r.mean_ms:.3f} | {r.std_ms:.3f} | "
            f"{r.min_ms:.3f} | {r.max_ms:.3f} | {r.iterations} |"
        )

    return "\n".join(lines)


def format_summary(results: list[BenchmarkResult]) -> str:
    """Format summary statistics by category."""
    categories: dict[str, list[float]] = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = []
        categories[r.category].append(r.mean_ms)

    lines = [
        "",
        "## Summary by Category",
        "",
        "| Category | Benchmarks | Avg Mean (ms) | Total (ms) |",
        "|----------|------------|---------------|------------|",
    ]

    for cat, means in sorted(categories.items()):
        avg = sum(means) / len(means)
        total = sum(means)
        lines.append(f"| {cat} | {len(means)} | {avg:.3f} | {total:.3f} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="sdqctl benchmark runner")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--quick", action="store_true", help="Reduced iterations")
    parser.add_argument("--output", "-o", type=Path, help="Output file")
    args = parser.parse_args()

    results = run_all_benchmarks(quick=args.quick)

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "results": [r._asdict() for r in results],
        }
        text = json.dumps(output, indent=2)
    else:
        text = "\n".join([
            "# sdqctl Performance Benchmarks",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            "",
            "## Results",
            "",
            format_table(results),
            format_summary(results),
            "",
        ])

    if args.output:
        args.output.write_text(text)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
