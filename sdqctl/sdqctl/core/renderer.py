"""
Renderer for ConversationFile workflows.

Produces fully-resolved prompts with all context, templates, prologues,
and epilogues expanded. Useful for:
- Debugging template issues before AI calls
- Using sdqctl as a prompt templating engine
- CI/CD validation of workflow content
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .context import ContextFile, ContextManager
from .conversation import (
    ConversationFile,
    build_prompt_with_injection,
    get_standard_variables,
    resolve_content_reference,
    substitute_template_variables,
)


@dataclass
class RenderedPrompt:
    """A single rendered prompt with all components."""
    
    index: int  # 1-based
    raw: str  # Original prompt text
    prologues: list[str]  # Resolved prologue contents
    epilogues: list[str]  # Resolved epilogue contents
    resolved: str  # Fully assembled prompt (prologues + prompt + epilogues)


@dataclass
class RenderedCycle:
    """A rendered cycle with context and prompts."""
    
    number: int  # 1-based cycle number
    context_files: list[ContextFile]
    context_content: str  # Formatted context for injection
    prompts: list[RenderedPrompt]
    variables: dict[str, str]  # Template variables used


@dataclass
class RenderedWorkflow:
    """Complete rendered workflow output."""
    
    workflow_path: Optional[Path]
    workflow_name: str
    session_mode: str
    adapter: str
    model: str
    max_cycles: int
    cycles: list[RenderedCycle]
    base_variables: dict[str, str]  # Variables without cycle-specific ones


def render_prompt(
    prompt: str,
    prologues: list[str],
    epilogues: list[str],
    index: int,
    base_path: Optional[Path],
    variables: dict[str, str],
) -> RenderedPrompt:
    """Render a single prompt with its prologues and epilogues.
    
    Args:
        prompt: The raw prompt text
        prologues: List of prologue strings (may include @file refs)
        epilogues: List of epilogue strings (may include @file refs)
        index: 1-based prompt index
        base_path: Base path for resolving @file references
        variables: Template variables for substitution
        
    Returns:
        RenderedPrompt with all content resolved
    """
    # Resolve prologues
    resolved_prologues = []
    for p in prologues:
        content = resolve_content_reference(p, base_path)
        content = substitute_template_variables(content, variables)
        resolved_prologues.append(content)
    
    # Resolve epilogues
    resolved_epilogues = []
    for e in epilogues:
        content = resolve_content_reference(e, base_path)
        content = substitute_template_variables(content, variables)
        resolved_epilogues.append(content)
    
    # Build full prompt
    full_prompt = build_prompt_with_injection(
        prompt, prologues, epilogues, base_path, variables
    )
    
    return RenderedPrompt(
        index=index,
        raw=prompt,
        prologues=resolved_prologues,
        epilogues=resolved_epilogues,
        resolved=full_prompt,
    )


def render_cycle(
    conv: ConversationFile,
    cycle_number: int,
    max_cycles: int,
    context_manager: ContextManager,
    base_variables: dict[str, str],
    include_context: bool = True,
) -> RenderedCycle:
    """Render a single cycle of a workflow.
    
    Args:
        conv: The conversation file
        cycle_number: 1-based cycle number
        max_cycles: Total number of cycles
        context_manager: Context manager with loaded files
        base_variables: Base template variables (without cycle-specific)
        include_context: Whether to include context file contents
        
    Returns:
        RenderedCycle with all prompts resolved
    """
    # Build cycle-specific variables
    variables = base_variables.copy()
    variables["CYCLE_NUMBER"] = str(cycle_number)
    variables["CYCLE_TOTAL"] = str(max_cycles)
    variables["MAX_CYCLES"] = str(max_cycles)
    
    # Get context
    context_files = list(context_manager.files) if include_context else []
    context_content = context_manager.get_context_content() if include_context else ""
    
    # Render all prompts
    base_path = conv.source_path.parent if conv.source_path else None
    rendered_prompts = []
    
    for i, prompt in enumerate(conv.prompts, 1):
        rendered = render_prompt(
            prompt=prompt,
            prologues=conv.prologues,
            epilogues=conv.epilogues,
            index=i,
            base_path=base_path,
            variables=variables,
        )
        rendered_prompts.append(rendered)
    
    return RenderedCycle(
        number=cycle_number,
        context_files=context_files,
        context_content=context_content,
        prompts=rendered_prompts,
        variables=variables,
    )


def render_workflow(
    conv: ConversationFile,
    session_mode: str = "accumulate",
    max_cycles: Optional[int] = None,
    include_context: bool = True,
) -> RenderedWorkflow:
    """Render a complete workflow with all cycles.
    
    Args:
        conv: The conversation file to render
        session_mode: Session mode (fresh, compact, accumulate)
        max_cycles: Override for max cycles (uses conv.max_cycles if None)
        include_context: Whether to include context file contents
        
    Returns:
        RenderedWorkflow with all cycles and prompts resolved
    """
    cycles_to_render = max_cycles if max_cycles is not None else conv.max_cycles
    
    # Get base variables
    base_variables = get_standard_variables(conv.source_path)
    
    # Setup context manager
    base_path = Path(conv.cwd) if conv.cwd else Path.cwd()
    if conv.source_path:
        base_path = conv.source_path.parent
    
    # Build path filter if restrictions exist
    path_filter = None
    if (conv.file_restrictions.allow_patterns or conv.file_restrictions.deny_patterns or
        conv.file_restrictions.allow_dirs or conv.file_restrictions.deny_dirs):
        path_filter = conv.file_restrictions.is_path_allowed
    
    context_manager = ContextManager(
        base_path=base_path,
        limit_threshold=conv.context_limit,
        path_filter=path_filter,
    )
    
    # Load context files
    for pattern in conv.context_files:
        context_manager.add_pattern(pattern)
    
    # Render cycles
    rendered_cycles = []
    for cycle_num in range(1, cycles_to_render + 1):
        # For fresh mode, we'd reload context here in actual execution
        # For render, we show what would be loaded (same files currently)
        rendered_cycle = render_cycle(
            conv=conv,
            cycle_number=cycle_num,
            max_cycles=cycles_to_render,
            context_manager=context_manager,
            base_variables=base_variables,
            include_context=include_context,
        )
        rendered_cycles.append(rendered_cycle)
    
    return RenderedWorkflow(
        workflow_path=conv.source_path,
        workflow_name=conv.source_path.stem if conv.source_path else "inline",
        session_mode=session_mode,
        adapter=conv.adapter,
        model=conv.model,
        max_cycles=cycles_to_render,
        cycles=rendered_cycles,
        base_variables=base_variables,
    )


def format_rendered_markdown(
    rendered: RenderedWorkflow,
    show_sections: bool = True,
    include_context: bool = True,
) -> str:
    """Format rendered workflow as markdown.
    
    Args:
        rendered: The rendered workflow
        show_sections: Whether to add section headers
        include_context: Whether to include context file contents
        
    Returns:
        Markdown-formatted string
    """
    from datetime import datetime
    
    lines = []
    
    # Header
    lines.append(f"# Rendered Workflow: {rendered.workflow_name}")
    lines.append("")
    lines.append(f"**Session Mode:** {rendered.session_mode}")
    lines.append(f"**Adapter:** {rendered.adapter}")
    lines.append(f"**Model:** {rendered.model}")
    lines.append(f"**Cycles:** {rendered.max_cycles}")
    lines.append(f"**Rendered:** {datetime.now().isoformat()}")
    lines.append("")
    
    # Template variables
    if show_sections:
        lines.append("## Template Variables")
        lines.append("")
        for key, value in sorted(rendered.base_variables.items()):
            lines.append(f"- `{{{{{key}}}}}` = `{value}`")
        lines.append("")
    
    # Cycles
    for cycle in rendered.cycles:
        lines.append("---")
        lines.append("")
        lines.append(f"## Cycle {cycle.number}")
        lines.append("")
        
        # Context files
        if include_context and cycle.context_files:
            lines.append("### Context Files")
            lines.append("")
            for ctx_file in cycle.context_files:
                rel_path = ctx_file.path.name
                try:
                    rel_path = str(ctx_file.path.relative_to(Path.cwd()))
                except ValueError:
                    rel_path = str(ctx_file.path)
                
                # Detect language for syntax highlighting
                ext = ctx_file.path.suffix.lstrip(".")
                lang = _extension_to_language(ext)
                
                lines.append(f"#### {rel_path}")
                lines.append(f"```{lang}")
                lines.append(ctx_file.content.rstrip())
                lines.append("```")
                lines.append("")
        
        # Prompts
        for prompt in cycle.prompts:
            lines.append(f"### Prompt {prompt.index} of {len(cycle.prompts)}")
            lines.append("")
            
            if show_sections and prompt.prologues:
                lines.append("**Prologues:**")
                for i, p in enumerate(prompt.prologues, 1):
                    # Truncate long prologues in summary
                    preview = p[:200] + "..." if len(p) > 200 else p
                    preview = preview.replace("\n", " ")
                    lines.append(f"- [{i}] {preview}")
                lines.append("")
            
            lines.append("**Resolved Prompt:**")
            lines.append("")
            lines.append("```")
            lines.append(prompt.resolved)
            lines.append("```")
            lines.append("")
            
            if show_sections and prompt.epilogues:
                lines.append("**Epilogues:**")
                for i, e in enumerate(prompt.epilogues, 1):
                    preview = e[:200] + "..." if len(e) > 200 else e
                    preview = preview.replace("\n", " ")
                    lines.append(f"- [{i}] {preview}")
                lines.append("")
    
    return "\n".join(lines)


def format_rendered_json(rendered: RenderedWorkflow) -> dict:
    """Format rendered workflow as JSON-serializable dict.
    
    Args:
        rendered: The rendered workflow
        
    Returns:
        Dict suitable for json.dumps()
    """
    return {
        "workflow": str(rendered.workflow_path) if rendered.workflow_path else None,
        "workflow_name": rendered.workflow_name,
        "session_mode": rendered.session_mode,
        "adapter": rendered.adapter,
        "model": rendered.model,
        "max_cycles": rendered.max_cycles,
        "template_variables": rendered.base_variables,
        "cycles": [
            {
                "number": cycle.number,
                "variables": cycle.variables,
                "context_files": [
                    {
                        "path": str(cf.path),
                        "content": cf.content,
                        "tokens_estimate": cf.tokens_estimate,
                    }
                    for cf in cycle.context_files
                ],
                "prompts": [
                    {
                        "index": p.index,
                        "raw": p.raw,
                        "prologues": p.prologues,
                        "epilogues": p.epilogues,
                        "resolved": p.resolved,
                    }
                    for p in cycle.prompts
                ],
            }
            for cycle in rendered.cycles
        ],
    }


def _extension_to_language(ext: str) -> str:
    """Map file extension to markdown code block language."""
    mapping = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
        "jsx": "javascript",
        "md": "markdown",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "sh": "bash",
        "bash": "bash",
        "rs": "rust",
        "go": "go",
        "rb": "ruby",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "h": "c",
        "hpp": "cpp",
        "sql": "sql",
        "html": "html",
        "css": "css",
        "xml": "xml",
        "toml": "toml",
        "ini": "ini",
        "conf": "ini",
        "conv": "dockerfile",  # .conv files use dockerfile-like syntax
    }
    return mapping.get(ext, ext or "text")
