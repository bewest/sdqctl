"""
Event collection and recording for adapter sessions.

Provides infrastructure to capture and export SDK events during execution.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class EventRecord:
    """Record of a single SDK event for export."""
    event_type: str
    timestamp: str  # ISO format
    data: dict
    session_id: str
    turn: int
    ephemeral: bool = False


class EventCollector:
    """Accumulates SDK events during a session for export."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: list[EventRecord] = []

    def add(
        self, event_type: str, data: Any, turn: int, ephemeral: bool = False
    ) -> None:
        """Record an event."""
        # Convert data to dict for serialization
        if data is None:
            data_dict = {}
        elif hasattr(data, '__dict__'):
            data_dict = {
                k: str(v) for k, v in vars(data).items() if not k.startswith('_')
            }
        elif isinstance(data, dict):
            data_dict = {k: str(v) for k, v in data.items()}
        else:
            data_dict = {"value": str(data)}

        record = EventRecord(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data_dict,
            session_id=self.session_id,
            turn=turn,
            ephemeral=ephemeral,
        )
        self.events.append(record)

    def export_jsonl(self, path: str) -> int:
        """Export events to JSONL file. Returns count of events written."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for event in self.events:
                f.write(json.dumps(asdict(event)) + '\n')

        return len(self.events)

    def clear(self) -> None:
        """Clear accumulated events."""
        self.events.clear()
