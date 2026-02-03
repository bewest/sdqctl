"""
ELIDE processing for step merging.

Handles the ELIDE directive which merges adjacent steps into single prompts,
avoiding agent turns between them.

Extensibility:
    Any directive that generates context/output can be ELIDE-compatible.
    The processing uses placeholders ({{TYPE:N:value}}) that are replaced
    during execution with actual output.

    Context-generating directives (ELIDE-compatible):
    - PROMPT: Text content (merged directly)
    - RUN: Command output
    - VERIFY: Verification results
    - REFCAT: File excerpts (line-range references)
    - LSP: Language server type/symbol info
    - CONSULT: AI sub-conversation output
    - HELP-INLINE: Help topic content
    - custom_directive: Plugin-generated output

    Control directives (NOT ELIDE-compatible):
    - COMPACT: Context window management
    - CHECKPOINT: State persistence boundary
    - NEW-CONVERSATION: Session boundary
    - PAUSE: User interaction required
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("sdqctl.commands.elide")

# Step types that generate context and can be merged with ELIDE
CONTEXT_GENERATING_TYPES = frozenset({
    "prompt",           # Direct text content
    "run",              # Command output
    "verify",           # Verification results
    "refcat",           # File excerpts
    "lsp",              # Language server info
    "consult",          # AI sub-conversation output
    "help_inline",      # Help topic content
    "custom_directive", # Plugin-generated output
})

# Step types that are control flow and break ELIDE chains
CONTROL_TYPES = frozenset({
    "compact",
    "checkpoint",
    "new_conversation",
    "pause",
})


def get_step_type(step) -> str:
    """Get step type from ConversationStep or dict."""
    return step.type if hasattr(step, 'type') else step.get('type', '')


def get_step_content(step) -> str:
    """Get step content from ConversationStep or dict."""
    return step.content if hasattr(step, 'content') else step.get('content', '')


def process_elided_steps(steps: list) -> list:
    """Process ELIDE directives by merging adjacent steps into single prompts.

    ELIDE merges the element above with the element below into a single prompt,
    avoiding an agent turn between them. This is useful for combining test output
    with error-fixing instructions, or context with instructions.

    Example:
        PROMPT Analyze the test results below.
        RUN pytest tests/ -v
        ELIDE
        PROMPT Fix any failing tests you find.

    Becomes a single merged prompt with test output injected.

    Args:
        steps: List of ConversationStep objects or dicts

    Returns:
        List of merged steps with ELIDE markers removed
    """
    if not steps:
        return steps

    # Find ELIDE positions and build merged groups
    # A group is a list of consecutive steps connected by ELIDE
    groups = []
    current_group = []

    for step in steps:
        step_type = get_step_type(step)

        if step_type == "elide":
            # ELIDE marks that we should continue the current group
            # If current_group is empty, start with previous group's last item
            continue
        else:
            # Check if this step should be merged with the previous group
            # by looking back to see if the previous non-elide step was followed by ELIDE
            should_merge = False
            if current_group:
                # Look back in original steps to see if there was an ELIDE between
                for i, s in enumerate(steps):
                    if s is step:
                        # Found current step, look backwards for ELIDE
                        j = i - 1
                        while j >= 0:
                            if get_step_type(steps[j]) == "elide":
                                should_merge = True
                                break
                            elif get_step_type(steps[j]) != "elide":
                                break
                            j -= 1
                        break

            if should_merge:
                current_group.append(step)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [step]

    if current_group:
        groups.append(current_group)

    # Now merge each group into a single step
    from ..core.conversation import ConversationStep
    merged_steps = []

    for group in groups:
        if len(group) == 1:
            # No merging needed
            merged_steps.append(group[0])
        else:
            # Merge multiple steps into a single merged prompt step
            # Combine prompts, context-generating steps become placeholders for later injection
            merged_contents = []
            merged_run_commands = []
            merged_verify_commands = []
            merged_refcat_commands = []
            merged_lsp_commands = []
            merged_consult_commands = []
            merged_help_inline_commands = []
            merged_custom_directives = []
            has_prompt = False

            for step in group:
                step_type = get_step_type(step)
                content = get_step_content(step)

                if step_type == "prompt":
                    merged_contents.append(content)
                    has_prompt = True
                elif step_type == "run":
                    # Store RUN command to be executed and output injected
                    merged_run_commands.append(content)
                    # Add placeholder that will be replaced with output
                    merged_contents.append(f"{{{{RUN:{len(merged_run_commands) - 1}:{content}}}}}")
                elif step_type == "verify":
                    # Store VERIFY command to be executed and output injected
                    verify_type = getattr(step, 'verify_type', 'all')
                    verify_options = getattr(step, 'verify_options', {})
                    merged_verify_commands.append((verify_type, verify_options))
                    # Add placeholder that will be replaced with output
                    merged_contents.append(f"{{{{VERIFY:{len(merged_verify_commands) - 1}:{verify_type}}}}}")
                elif step_type == "refcat":
                    # Store REFCAT reference to be resolved and content injected
                    merged_refcat_commands.append(content)
                    merged_contents.append(f"{{{{REFCAT:{len(merged_refcat_commands) - 1}:{content}}}}}")
                elif step_type == "lsp":
                    # Store LSP query to be executed and output injected
                    lsp_query = getattr(step, 'lsp_query', content)
                    lsp_options = getattr(step, 'lsp_options', {})
                    merged_lsp_commands.append((lsp_query, lsp_options))
                    merged_contents.append(f"{{{{LSP:{len(merged_lsp_commands) - 1}:{lsp_query}}}}}")
                elif step_type == "consult":
                    # Store CONSULT to be executed and output injected
                    merged_consult_commands.append(content)
                    merged_contents.append(f"{{{{CONSULT:{len(merged_consult_commands) - 1}:{content[:50]}}}}}")
                elif step_type == "help_inline":
                    # Store HELP-INLINE topic(s) to be resolved and injected
                    merged_help_inline_commands.append(content)
                    merged_contents.append(f"{{{{HELP:{len(merged_help_inline_commands) - 1}:{content}}}}}")
                elif step_type == "custom_directive":
                    # Store custom directive to be executed via plugin hook
                    directive_name = getattr(step, 'directive_name', 'CUSTOM')
                    merged_custom_directives.append((directive_name, content, step))
                    merged_contents.append(f"{{{{CUSTOM:{len(merged_custom_directives) - 1}:{directive_name}}}}}")
                elif step_type in CONTROL_TYPES:
                    # Control steps break the merge - shouldn't happen in valid ELIDE usage
                    logger.warning(f"ELIDE cannot merge control step type '{step_type}'")
                    # Add as-is for now
                    merged_steps.append(step)
                    continue
                else:
                    # Unknown step type - warn and add content if available
                    if step_type not in ("elide",):  # elide is handled earlier
                        logger.warning(f"ELIDE: unhandled step type '{step_type}', adding content as-is")
                        if content:
                            merged_contents.append(f"[{step_type.upper()}]\n{content}")

            if has_prompt or merged_contents:
                merged_step = ConversationStep(
                    type="merged_prompt",
                    content="\n\n".join(merged_contents),
                )
                # Attach commands for later execution
                merged_step.run_commands = merged_run_commands  # type: ignore
                merged_step.verify_commands = merged_verify_commands  # type: ignore
                merged_step.refcat_commands = merged_refcat_commands  # type: ignore
                merged_step.lsp_commands = merged_lsp_commands  # type: ignore
                merged_step.consult_commands = merged_consult_commands  # type: ignore
                merged_step.help_inline_commands = merged_help_inline_commands  # type: ignore
                merged_step.custom_directives = merged_custom_directives  # type: ignore
                merged_steps.append(merged_step)

    logger.debug(f"Processed {len(steps)} steps with ELIDE into {len(merged_steps)} merged steps")
    return merged_steps
