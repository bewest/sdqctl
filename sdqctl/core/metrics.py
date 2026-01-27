"""
Metrics collection for sdqctl iterations.

Collects and emits metrics following docs/metrics-schema.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def emit_metrics(
    session_id: str,
    session_dir: Path,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    cycles_completed: int = 0,
    items_completed: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Path:
    """Emit metrics to session directory.

    Args:
        session_id: Unique session identifier
        session_dir: Directory to write metrics.json
        started_at: When session started
        ended_at: When session ended (None if ongoing)
        cycles_completed: Number of iteration cycles completed
        items_completed: Number of backlog items completed
        input_tokens: Total input tokens consumed
        output_tokens: Total output tokens generated

    Returns:
        Path to the written metrics.json file
    """
    # Calculate derived metrics
    total_tokens = input_tokens + output_tokens
    total_seconds = (
        (ended_at - started_at).total_seconds()
        if ended_at
        else (datetime.now(timezone.utc) - started_at).total_seconds()
    )

    io_ratio = output_tokens / input_tokens if input_tokens > 0 else 0
    tokens_per_item = total_tokens / items_completed if items_completed > 0 else None
    seconds_per_cycle = total_seconds / cycles_completed if cycles_completed > 0 else None
    seconds_per_item = total_seconds / items_completed if items_completed > 0 else None

    metrics: dict[str, Any] = {
        "schema_version": "1.0",
        "session_id": session_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat() if ended_at else None,
        "work_output": {
            "items_completed": items_completed,
            "lines_changed": 0,  # Would need git integration
        },
        "token_efficiency": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "io_ratio": round(io_ratio, 3),
            "tokens_per_item": round(tokens_per_item, 1) if tokens_per_item else None,
            "estimated_cost_usd": None,  # Pricing not available
        },
        "duration": {
            "total_seconds": round(total_seconds, 2),
            "cycles": cycles_completed,
            "seconds_per_cycle": round(seconds_per_cycle, 2) if seconds_per_cycle else None,
            "seconds_per_item": round(seconds_per_item, 2) if seconds_per_item else None,
        },
    }

    # Ensure directory exists
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write metrics
    metrics_path = session_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics_path
