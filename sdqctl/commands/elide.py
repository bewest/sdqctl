"""
ELIDE processing for step merging.

Handles the ELIDE directive which merges adjacent steps into single prompts,
avoiding agent turns between them.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("sdqctl.commands.elide")


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
            # Combine prompts, run outputs become placeholders for later injection
            merged_contents = []
            merged_run_commands = []
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
                elif step_type in ("checkpoint", "compact", "new_conversation"):
                    # Control steps break the merge - shouldn't happen in valid ELIDE usage
                    logger.warning(f"ELIDE cannot merge control step type '{step_type}'")
                    # Add as-is for now
                    merged_steps.append(step)
                    continue

            if has_prompt or merged_contents:
                merged_step = ConversationStep(
                    type="merged_prompt",
                    content="\n\n".join(merged_contents),
                )
                # Attach run commands for later execution
                merged_step.run_commands = merged_run_commands  # type: ignore
                merged_steps.append(merged_step)

    logger.debug(f"Processed {len(steps)} steps with ELIDE into {len(merged_steps)} merged steps")
    return merged_steps
