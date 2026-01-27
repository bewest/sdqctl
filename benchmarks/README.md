# Performance Benchmarks

Comprehensive benchmarking suite for sdqctl covering code performance, workflow timing, and SDK latency.

## Quick Start

```bash
# Run all benchmarks
python -m benchmarks.run

# Quick mode (reduced iterations)
python -m benchmarks.run --quick

# JSON output
python -m benchmarks.run --json

# Save to file
python -m benchmarks.run -o reports/benchmark-$(date +%Y-%m-%d).md
```

## Benchmark Categories

### Parsing (`bench_parsing.py`)

Measures `.conv` file parsing performance:

| Benchmark | Description | Iterations |
|-----------|-------------|------------|
| `parse_minimal` | 4-line minimal workflow | 1000 |
| `parse_small` | Typical workflow (~10 lines) | 500 |
| `parse_medium` | Complex workflow (~30 lines) | 200 |
| `parse_large` | Stress test (50 contexts, 20 prompts) | 50 |
| `parse_from_file` | Filesystem I/O overhead | 200 |

### Rendering (`bench_rendering.py`)

Measures prompt assembly and template expansion:

| Benchmark | Description | Iterations |
|-----------|-------------|------------|
| `render_simple` | Plain prompt, no templates | 500 |
| `render_template` | Template variable substitution | 500 |
| `render_structured` | Prologue/epilogue injection | 300 |
| `render_with_context` | File context loading | 100 |
| `render_multiple` | 10 prompts in sequence | 50 |

### Workflow (`bench_workflow.py`)

Measures step execution and verification:

| Benchmark | Description | Iterations |
|-----------|-------------|------------|
| `step_iteration` | Iterate 70 workflow steps | 1000 |
| `verify_refs` | Reference verification | 50 |
| `verify_links` | Link verification | 50 |
| `verify_traceability` | Traceability matrix | 30 |
| `verify_all` | All verifiers combined | 20 |

### SDK (`bench_sdk.py`)

Measures adapter/session overhead (using MockAdapter):

| Benchmark | Description | Iterations |
|-----------|-------------|------------|
| `session_create` | Session creation overhead | 200 |
| `session_reuse` | Session access patterns | 100 |
| `message_send` | Single message latency | 50 |
| `message_burst` | 10 messages sequential | 20 |
| `adapter_lifecycle` | Full start/send/stop | 100 |
| `multiple_sessions` | 5 concurrent sessions | 30 |

## Output Formats

### Markdown (default)

```markdown
| Category | Benchmark | Mean (ms) | Std (ms) | Min | Max | Iterations |
|----------|-----------|-----------|----------|-----|-----|------------|
| parsing | parse_minimal | 0.014 | 0.038 | 0.012 | 1.226 | 1000 |
```

### JSON (`--json`)

```json
{
  "timestamp": "2026-01-27T10:53:37.709205",
  "results": [
    {
      "category": "parsing",
      "name": "parse_minimal",
      "iterations": 1000,
      "mean_ms": 0.014,
      "std_ms": 0.038,
      "min_ms": 0.012,
      "max_ms": 1.226
    }
  ]
}
```

## Interpreting Results

### Performance Baselines

| Operation | Expected | Warning |
|-----------|----------|---------|
| Parse minimal | <0.05ms | >0.1ms |
| Parse large | <0.5ms | >1ms |
| Render prompt | <0.01ms | >0.05ms |
| Verify (single) | <2ms | >5ms |
| SDK session | <0.01ms | >0.05ms |

### Common Issues

- **High parse times**: Check for complex directive nesting
- **High render times**: Template variable count, file I/O
- **High verify times**: Large file count, deep directory trees
- **High SDK times**: Async overhead, event handling

## Adding Benchmarks

Create a new benchmark function in the appropriate file:

```python
def bench_my_operation() -> BenchmarkResult:
    """Benchmark description."""
    def operation():
        # Code to benchmark
        pass
    
    return _time_ms(operation, iterations=100, name="my_operation")
```

Add to `run_all()`:

```python
def run_all(tmp_path: Path | None = None) -> list[BenchmarkResult]:
    results = [
        bench_existing(),
        bench_my_operation(),  # Add here
    ]
    return results
```

## CI Integration

```yaml
# .github/workflows/benchmarks.yml
- name: Run benchmarks
  run: python -m benchmarks.run --json -o benchmark-results.json

- name: Check regression
  run: |
    # Compare against baseline
    python scripts/check_benchmark_regression.py benchmark-results.json
```

## References

- [OQ-005](docs/OPEN-QUESTIONS.md) - Benchmark scope decision
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Module structure
