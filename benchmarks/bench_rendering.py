"""
Benchmarks for prompt rendering.

Measures:
- Template expansion time
- Context assembly overhead
- Prompt building performance
"""

import statistics
import time
from pathlib import Path
from typing import NamedTuple

from sdqctl.core.conversation import ConversationFile
from sdqctl.core.renderer import render_prompt


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


# Simple prompt without templates
SIMPLE_PROMPT = """\
MODEL gpt-4
ADAPTER copilot

PROMPT Analyze the following code and suggest improvements.
"""

# Prompt with template variables
TEMPLATE_PROMPT = """\
MODEL gpt-4
ADAPTER copilot

PROMPT Analyze {{project}} in {{language}} for {{issue_type}}.
"""

# Prompt with prologue/epilogue
STRUCTURED_PROMPT = """\
MODEL gpt-4
ADAPTER copilot
MODE analyze

PROLOGUE You are an expert code reviewer.
EPILOGUE Format your response as markdown.

PROMPT Review the authentication module.
PROMPT Check for SQL injection vulnerabilities.
"""


def bench_render_simple() -> BenchmarkResult:
    """Benchmark rendering simple prompt."""
    conv = ConversationFile.parse(SIMPLE_PROMPT)

    def render():
        render_prompt(
            prompt=conv.prompts[0],
            prologues=[],
            epilogues=[],
            index=1,
            total_prompts=1,
            base_path=None,
            variables={},
        )

    return _time_ms(render, iterations=500)


def bench_render_template() -> BenchmarkResult:
    """Benchmark rendering prompt with templates."""
    conv = ConversationFile.parse(TEMPLATE_PROMPT)
    variables = {
        "project": "sdqctl",
        "language": "Python",
        "issue_type": "security vulnerabilities",
    }

    def render():
        render_prompt(
            prompt=conv.prompts[0],
            prologues=[],
            epilogues=[],
            index=1,
            total_prompts=1,
            base_path=None,
            variables=variables,
        )

    return _time_ms(render, iterations=500)


def bench_render_structured() -> BenchmarkResult:
    """Benchmark rendering prompt with prologue/epilogue."""
    conv = ConversationFile.parse(STRUCTURED_PROMPT)

    def render():
        render_prompt(
            prompt=conv.prompts[0],
            prologues=conv.prologues,
            epilogues=conv.epilogues,
            index=1,
            total_prompts=len(conv.prompts),
            base_path=None,
            variables={},
        )

    return _time_ms(render, iterations=300)


def bench_render_with_context(tmp_path: Path) -> BenchmarkResult:
    """Benchmark rendering with file context."""
    # Create test files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    for i in range(5):
        (src_dir / f"module_{i}.py").write_text(f"# Module {i}\ndef func_{i}(): pass\n" * 10)

    conv_text = f"""\
MODEL gpt-4
ADAPTER copilot

CONTEXT @{src_dir}/module_0.py
CONTEXT @{src_dir}/module_1.py
CONTEXT @{src_dir}/module_2.py

PROMPT Analyze these modules.
"""
    conv = ConversationFile.parse(conv_text)

    def render():
        render_prompt(
            prompt=conv.prompts[0],
            prologues=conv.prologues,
            epilogues=conv.epilogues,
            index=1,
            total_prompts=1,
            base_path=tmp_path,
            variables={},
        )

    return _time_ms(render, iterations=100)


def bench_render_multiple_prompts() -> BenchmarkResult:
    """Benchmark rendering multiple prompts in sequence."""
    conv_text = "\n".join([
        "MODEL gpt-4",
        "ADAPTER copilot",
        "",
    ] + [f"PROMPT Analyze aspect {i} of the system." for i in range(10)])

    conv = ConversationFile.parse(conv_text)
    total = len(conv.prompts)

    def render():
        for i, prompt in enumerate(conv.prompts, 1):
            render_prompt(
                prompt=prompt,
                prologues=[],
                epilogues=[],
                index=i,
                total_prompts=total,
                base_path=None,
                variables={},
            )

    return _time_ms(render, iterations=50)


def run_all(tmp_path: Path | None = None) -> list[BenchmarkResult]:
    """Run all rendering benchmarks."""
    results = [
        bench_render_simple(),
        bench_render_template(),
        bench_render_structured(),
        bench_render_multiple_prompts(),
    ]

    if tmp_path:
        results.append(bench_render_with_context(tmp_path))

    return results


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        results = run_all(Path(tmp))
        print("\n=== Rendering Benchmarks ===\n")
        for r in results:
            print(f"{r.name}:")
            print(f"  mean: {r.mean_ms:.3f}ms (±{r.std_ms:.3f}ms)")
            print(f"  range: [{r.min_ms:.3f}ms, {r.max_ms:.3f}ms]")
            print(f"  iterations: {r.iterations}")
            print()
