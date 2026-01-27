"""
Session management for AI workflows.

Handles:
- Conversation state
- Checkpoint/restore
- Adapter lifecycle
- ExecutionContext for unified command execution
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from rich.console import Console

from .context import ContextManager
from .conversation import ConversationFile

if TYPE_CHECKING:
    from ..adapters.base import AdapterBase, AdapterConfig, AdapterSession


@dataclass
class ExecutionContext:
    """Unified context for workflow execution across commands.

    Encapsulates the common state needed by run, iterate, and apply commands,
    reducing code duplication and ensuring consistent initialization.

    Attributes:
        adapter: The AI adapter instance (e.g., CopilotAdapter)
        adapter_config: Configuration for the adapter
        adapter_session: The active session from the adapter
        session: Session instance for checkpointing and state
        conv: The loaded ConversationFile
        verbosity: Logging verbosity level (0=quiet, 1=normal, 2=verbose)
        console: Rich console for output
        show_prompt: Whether to display prompts to stderr
        json_errors: Whether to format errors as JSON
    """

    adapter: "AdapterBase"
    adapter_config: "AdapterConfig"
    adapter_session: "AdapterSession"
    session: "Session"
    conv: ConversationFile
    verbosity: int = 0
    console: Console = field(default_factory=Console)
    show_prompt: bool = False
    json_errors: bool = False

    @property
    def is_verbose(self) -> bool:
        """True if verbosity >= 1."""
        return self.verbosity >= 1

    @property
    def is_debug(self) -> bool:
        """True if verbosity >= 2."""
        return self.verbosity >= 2


async def create_execution_context(
    conv: ConversationFile,
    adapter_name: Optional[str] = None,
    model: Optional[str] = None,
    session_name: Optional[str] = None,
    session_dir: Optional[Path] = None,
    event_log_path: Optional[str] = None,
    verbosity: int = 0,
    console: Optional[Console] = None,
    show_prompt: bool = False,
    json_errors: bool = False,
    infinite_sessions_config: Optional[Any] = None,
) -> ExecutionContext:
    """Create an ExecutionContext with initialized adapter and session.

    This factory function consolidates the common adapter initialization
    pattern used across run.py, iterate.py, and apply.py.

    Args:
        conv: The loaded ConversationFile
        adapter_name: Override adapter name (defaults to conv.adapter)
        model: Override model name (defaults to conv.model)
        session_name: Named session for resumability
        session_dir: Directory for checkpoints
        event_log_path: Path for SDK event log
        verbosity: Logging verbosity (0=quiet, 1=normal, 2=debug)
        console: Rich console for output (defaults to new Console)
        show_prompt: Whether to display prompts to stderr
        json_errors: Whether to format errors as JSON
        infinite_sessions_config: InfiniteSessionConfig for SDK compaction

    Returns:
        Initialized ExecutionContext ready for workflow execution

    Raises:
        ValueError: If adapter is not available
    """
    from ..adapters import get_adapter
    from ..adapters.base import AdapterConfig

    # Use console or create new
    effective_console = console or Console()

    # Get adapter
    effective_adapter_name = adapter_name or conv.adapter or "copilot"
    adapter = get_adapter(effective_adapter_name)

    # Start adapter
    await adapter.start()

    # Build adapter config
    adapter_config = AdapterConfig(
        model=model or conv.model,
        streaming=True,
        debug_categories=getattr(conv, 'debug_categories', None),
        debug_intents=getattr(conv, 'debug_intents', False),
        event_log=event_log_path,
        infinite_sessions=infinite_sessions_config,
    )

    # Create session for checkpointing
    session = Session(conv, session_dir=session_dir)

    # Create or resume adapter session
    effective_session_name = session_name or conv.session_name
    if effective_session_name:
        try:
            adapter_session = await adapter.resume_session(effective_session_name, adapter_config)
        except Exception:
            adapter_session = await adapter.create_session(adapter_config)
    else:
        adapter_session = await adapter.create_session(adapter_config)

    # Store SDK session ID for resume (Q-018 fix)
    session.sdk_session_id = adapter_session.sdk_session_id

    return ExecutionContext(
        adapter=adapter,
        adapter_config=adapter_config,
        adapter_session=adapter_session,
        session=session,
        conv=conv,
        verbosity=verbosity,
        console=effective_console,
        show_prompt=show_prompt,
        json_errors=json_errors,
    )


@dataclass
class Message:
    """A message in the conversation."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


@dataclass
class Checkpoint:
    """A saved session state."""

    id: str
    name: Optional[str]
    timestamp: datetime
    messages: list[Message]
    context_status: dict
    cycle_number: int
    metadata: dict


@dataclass
class SessionState:
    """Current state of a session."""

    id: str
    conversation: ConversationFile
    messages: list[Message] = field(default_factory=list)
    cycle_number: int = 0
    prompt_index: int = 0
    checkpoints: list[Checkpoint] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, paused, completed, failed


class Session:
    """Manages a single workflow session."""

    def __init__(
        self,
        conversation: ConversationFile,
        adapter: Optional[Any] = None,
        session_dir: Optional[Path] = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.conversation = conversation
        self.adapter = adapter
        self.session_dir = session_dir or Path.home() / ".sdqctl" / "sessions" / self.id
        self.sdk_session_id: Optional[str] = None  # SDK's session UUID for resume (Q-018)

        # Initialize state
        self.state = SessionState(
            id=self.id,
            conversation=conversation,
        )

        # Context manager
        # Setup context with file restriction filter
        path_filter = None
        restrictions = conversation.file_restrictions
        has_restrictions = (
            restrictions.allow_patterns or restrictions.deny_patterns or
            restrictions.allow_dirs or restrictions.deny_dirs
        )
        if has_restrictions:
            path_filter = conversation.file_restrictions.is_path_allowed

        self.context = ContextManager(
            base_path=Path(conversation.cwd) if conversation.cwd else Path.cwd(),
            limit_threshold=conversation.context_limit,
            path_filter=path_filter,
        )

        # Load context files
        for pattern in conversation.context_files:
            self.context.add_pattern(pattern)

    def reload_context(self) -> None:
        """Reload CONTEXT files from disk.

        Used by fresh mode to pick up file changes between cycles.
        Preserves ContextManager config (base_path, limit_threshold, path_filter).
        """
        # Clear existing files (preserves conversation token count)
        self.context.clear_files()

        # Re-load from disk using stored patterns
        for pattern in self.conversation.context_files:
            self.context.add_pattern(pattern)

    def add_message(self, role: str, content: str, **metadata) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, metadata=metadata)
        self.state.messages.append(msg)
        self.context.add_conversation_turn(content)
        return msg

    def get_current_prompt(self) -> Optional[str]:
        """Get the current prompt to execute."""
        if self.state.prompt_index >= len(self.conversation.prompts):
            return None
        return self.conversation.prompts[self.state.prompt_index]

    def advance_prompt(self) -> bool:
        """Move to next prompt. Returns True if more prompts available."""
        self.state.prompt_index += 1
        return self.state.prompt_index < len(self.conversation.prompts)

    def advance_cycle(self) -> bool:
        """Start next cycle. Returns True if more cycles allowed."""
        self.state.cycle_number += 1
        self.state.prompt_index = 0  # Reset to first prompt
        return self.state.cycle_number < self.conversation.max_cycles

    def should_checkpoint(self) -> bool:
        """Check if we should create a checkpoint now."""
        policy = self.conversation.checkpoint_after
        if not policy:
            return False

        if policy == "each-cycle":
            return self.state.prompt_index == 0 and self.state.cycle_number > 0
        elif policy == "each-prompt":
            return True
        elif policy == "never":
            return False

        return False

    def create_checkpoint(self, name: Optional[str] = None) -> Checkpoint:
        """Create a checkpoint of current state."""
        default_name = f"checkpoint-{len(self.state.checkpoints)}"
        checkpoint_name = name or self.conversation.checkpoint_name or default_name

        conv_path = self.conversation.source_path
        checkpoint = Checkpoint(
            id=str(uuid.uuid4())[:8],
            name=checkpoint_name,
            timestamp=datetime.now(timezone.utc),
            messages=list(self.state.messages),  # Copy
            context_status=self.context.get_status(),
            cycle_number=self.state.cycle_number,
            metadata={
                "prompt_index": self.state.prompt_index,
                "conversation_file": str(conv_path) if conv_path else None,
            },
        )

        self.state.checkpoints.append(checkpoint)

        # Save to disk
        self._save_checkpoint(checkpoint)

        return checkpoint

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to disk."""
        self.session_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = self.session_dir / f"checkpoint-{checkpoint.id}.json"
        data = {
            "id": checkpoint.id,
            "name": checkpoint.name,
            "timestamp": checkpoint.timestamp.isoformat(),
            "cycle_number": checkpoint.cycle_number,
            "metadata": checkpoint.metadata,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in checkpoint.messages
            ],
            "context_status": checkpoint.context_status,
        }

        checkpoint_file.write_text(json.dumps(data, indent=2))

    def save_pause_checkpoint(
        self, message: str, expires_at: Optional[str] = None
    ) -> Path:
        """Save a checkpoint for PAUSE directive and return the file path.

        Args:
            message: Pause/consult message
            expires_at: Optional ISO timestamp when this checkpoint expires

        Returns:
            Path to the checkpoint file
        """
        self.session_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = self.session_dir / "pause.json"
        data = {
            "type": "pause",
            "message": message,
            "status": self.state.status,  # Include session status (e.g., "consulting")
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,  # CONSULT-TIMEOUT expiration
            "session_id": self.id,
            "sdk_session_id": self.sdk_session_id,  # SDK's UUID for resume (Q-018)
            "conversation_file": (
                str(self.conversation.source_path) if self.conversation.source_path else None
            ),
            "conversation_inline": (
                self.conversation.to_string() if not self.conversation.source_path else None
            ),
            "cycle_number": self.state.cycle_number,
            "prompt_index": self.state.prompt_index,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.state.messages
            ],
            "context_status": self.context.get_status(),
        }

        checkpoint_file.write_text(json.dumps(data, indent=2))
        return checkpoint_file

    @classmethod
    def load_from_pause(cls, checkpoint_path: Path) -> "Session":
        """Load a session from a pause checkpoint file."""
        data = json.loads(checkpoint_path.read_text())

        # Load the original conversation file or inline content
        conv_path = data.get("conversation_file")
        conv_inline = data.get("conversation_inline")

        if conv_path and Path(conv_path).exists():
            conv = ConversationFile.from_file(Path(conv_path))
        elif conv_inline:
            conv = ConversationFile.parse(conv_inline)
        else:
            # Provide diagnostic info about what was expected
            msg = "Checkpoint missing conversation_file reference or inline content"
            if conv_path:
                msg = f"Conversation file not found: {conv_path} (checkpoint: {checkpoint_path})"
            raise ValueError(msg)

        # Create session
        session = cls(conv, session_dir=checkpoint_path.parent)
        session.id = data["session_id"]
        session.sdk_session_id = data.get("sdk_session_id")  # Restore SDK UUID (Q-018)
        session.state.cycle_number = data["cycle_number"]
        session.state.prompt_index = data["prompt_index"]

        # Restore status: keep "consulting" for CONSULT, otherwise set "resumed"
        saved_status = data.get("status", "pending")
        session.state.status = saved_status if saved_status == "consulting" else "resumed"

        # Restore messages
        for m in data["messages"]:
            msg = Message(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {}),
            )
            session.state.messages.append(msg)

        return session

    def needs_compaction(self, min_density: float = 0) -> bool:
        """Check if context window is near limit and above minimum density.

        Args:
            min_density: Minimum context usage (0-100%) below which compaction
                        is skipped. E.g., min_density=30 means skip compaction
                        if context is less than 30% full.

        Returns:
            True if compaction should occur (near limit AND above min density)
        """
        if min_density > 0:
            # Convert to 0-1 range if given as percentage
            min_threshold = min_density / 100 if min_density > 1 else min_density
            current_usage = self.context.window.usage_percent
            if current_usage < min_threshold:
                return False
        return self.context.window.is_near_limit

    def get_compaction_prompt(self) -> str:
        """Generate prompt for compaction."""
        preserve = self.conversation.compact_preserve
        summary_instruction = (
            self.conversation.compact_summary or "Summarize the key findings and progress."
        )
        default_preserve = 'key findings, decisions, remaining work'
        preserve_items = ', '.join(preserve) if preserve else default_preserve

        prompt = f"""Compact this conversation for continuation.

PRESERVE these key items: {preserve_items}

{summary_instruction}

Format the summary so it can be used to continue the work in a new context window.
"""
        return prompt

    def get_status(self) -> dict:
        """Get current session status."""
        return {
            "id": self.id,
            "status": self.state.status,
            "cycle": f"{self.state.cycle_number + 1}/{self.conversation.max_cycles}",
            "prompt": f"{self.state.prompt_index + 1}/{len(self.conversation.prompts)}",
            "messages": len(self.state.messages),
            "checkpoints": len(self.state.checkpoints),
            "context": self.context.get_status(),
            "adapter": self.conversation.adapter,
            "model": self.conversation.model,
        }

    def to_dict(self) -> dict:
        """Serialize session for JSON output."""
        conv_path = self.conversation.source_path
        return {
            "id": self.id,
            "conversation_file": str(conv_path) if conv_path else None,
            "state": {
                "status": self.state.status,
                "cycle_number": self.state.cycle_number,
                "prompt_index": self.state.prompt_index,
                "started_at": (
                    self.state.started_at.isoformat() if self.state.started_at else None
                ),
                "finished_at": (
                    self.state.finished_at.isoformat() if self.state.finished_at else None
                ),
            },
            "context": self.context.get_status(),
            "checkpoints": [
                {"id": c.id, "name": c.name, "timestamp": c.timestamp.isoformat()}
                for c in self.state.checkpoints
            ],
        }
