"""Directive application logic for ConversationFile parsing."""

import re
import warnings

from .types import ConversationStep, Directive, DirectiveType


def apply_directive(conv, directive: Directive) -> None:
    """Apply a parsed directive to the ConversationFile.

    Args:
        conv: The ConversationFile being built
        directive: The parsed directive to apply
    """
    match directive.type:
        case DirectiveType.MODEL:
            conv.model = directive.value
        case DirectiveType.ADAPTER:
            conv.adapter = directive.value
        case DirectiveType.MODE:
            conv.mode = directive.value
        case DirectiveType.MAX_CYCLES:
            conv.max_cycles = int(directive.value)
        case DirectiveType.CWD:
            conv.cwd = directive.value
        case DirectiveType.SESSION_NAME:
            conv.session_name = directive.value

        # Model requirements (abstract model selection)
        case DirectiveType.MODEL_REQUIRES:
            from ..models import ModelRequirements
            if conv.model_requirements is None:
                conv.model_requirements = ModelRequirements()
            conv.model_requirements.add_requirement(directive.value)
        case DirectiveType.MODEL_PREFERS:
            from ..models import ModelRequirements
            if conv.model_requirements is None:
                conv.model_requirements = ModelRequirements()
            conv.model_requirements.add_preference(directive.value)
        case DirectiveType.MODEL_POLICY:
            from ..models import ModelRequirements
            if conv.model_requirements is None:
                conv.model_requirements = ModelRequirements()
            conv.model_requirements.set_policy(directive.value)

        case DirectiveType.CONTEXT:
            # DEPRECATED: Use REFCAT instead
            warnings.warn(
                f"CONTEXT directive is deprecated. Use REFCAT instead: REFCAT {directive.value}",
                DeprecationWarning,
                stacklevel=2
            )
            conv.context_files.append(directive.value)
        case DirectiveType.CONTEXT_OPTIONAL:
            conv.context_files_optional.append(directive.value)
        case DirectiveType.CONTEXT_EXCLUDE:
            conv.context_exclude.append(directive.value)
        case DirectiveType.CONTEXT_LIMIT:
            # Parse "80%" -> 0.8
            value = directive.value.rstrip("%")
            conv.context_limit = float(value) / 100
        case DirectiveType.ON_CONTEXT_LIMIT:
            conv.on_context_limit = directive.value
        case DirectiveType.VALIDATION_MODE:
            conv.validation_mode = directive.value.lower()

        # REFCAT - line-level file excerpts
        case DirectiveType.REFCAT:
            # REFCAT can have multiple refs separated by spaces
            # REFCAT @file.py#L10-L50 @other.py#L1-L20
            refs = directive.value.split()
            conv.refcat_refs.extend(refs)

        # File restrictions
        case DirectiveType.ALLOW_FILES:
            conv.file_restrictions.allow_patterns.append(directive.value)
        case DirectiveType.DENY_FILES:
            conv.file_restrictions.deny_patterns.append(directive.value)
        case DirectiveType.ALLOW_DIR:
            conv.file_restrictions.allow_dirs.append(directive.value)
        case DirectiveType.DENY_DIR:
            conv.file_restrictions.deny_dirs.append(directive.value)

        # Prompt injection (prepend/append to each prompt)
        case DirectiveType.PROLOGUE:
            conv.prologues.append(directive.value)
        case DirectiveType.EPILOGUE:
            conv.epilogues.append(directive.value)

        # Help injection - inject help topics into prologues
        case DirectiveType.HELP:
            # HELP can have multiple topics: HELP directives workflow
            topics = directive.value.split()
            conv.help_topics.extend(topics)

        # Help inline - inject help as step that merges with next prompt
        case DirectiveType.HELP_INLINE:
            # HELP-INLINE topic1 topic2 - creates step merged with next prompt
            topics = directive.value.split()
            conv.steps.append(ConversationStep(
                type="help_inline",
                content=" ".join(topics),
                merge_with_next=True
            ))

        # Pre-flight requirements
        case DirectiveType.REQUIRE:
            # REQUIRE can have multiple items: REQUIRE @file.py cmd:git @other.md
            items = directive.value.split()
            conv.requirements.extend(items)

        # File inclusion (handled in parse loop, no-op here)
        case DirectiveType.INCLUDE:
            pass  # Processed inline during parsing

        # Prompts - add to both flat list and steps
        case DirectiveType.PROMPT:
            conv.prompts.append(directive.value)
            conv.steps.append(ConversationStep(type="prompt", content=directive.value))
        case DirectiveType.ON_CONTEXT_LIMIT_PROMPT:
            conv.on_context_limit_prompt = directive.value

        # Conversation control directives
        case DirectiveType.COMPACT:
            # COMPACT with optional preserve list
            preserve = [x.strip() for x in directive.value.split(",")] if directive.value else []
            conv.steps.append(ConversationStep(type="compact", preserve=preserve))
        case DirectiveType.NEW_CONVERSATION:
            conv.steps.append(ConversationStep(type="new_conversation"))
        case DirectiveType.CHECKPOINT:
            conv.steps.append(ConversationStep(type="checkpoint", content=directive.value))

        # Legacy compaction settings
        case DirectiveType.COMPACT_PRESERVE:
            # Parse "findings, recommendations" -> ["findings", "recommendations"]
            conv.compact_preserve = [x.strip() for x in directive.value.split(",")]
        case DirectiveType.COMPACT_SUMMARY:
            conv.compact_summary = directive.value
        case DirectiveType.COMPACT_PROLOGUE:
            conv.compact_prologue = directive.value
        case DirectiveType.COMPACT_EPILOGUE:
            conv.compact_epilogue = directive.value

        # Infinite sessions (SDK native compaction)
        case DirectiveType.INFINITE_SESSIONS:
            value_lower = directive.value.lower()
            if value_lower in ("enabled", "true", "yes", "on", "1"):
                conv.infinite_sessions = True
            elif value_lower in ("disabled", "false", "no", "off", "0"):
                conv.infinite_sessions = False
            else:
                raise ValueError(
                    f"Invalid INFINITE-SESSIONS value: {directive.value} "
                    "(expected enabled/disabled)"
                )
        case DirectiveType.COMPACTION_MIN:
            # Parse "30" or "30%" -> 0.30
            value = directive.value.rstrip("%")
            conv.compaction_min = float(value) / 100
        case DirectiveType.COMPACTION_THRESHOLD:
            # Parse "80" or "80%" -> 0.80
            value = directive.value.rstrip("%")
            conv.compaction_threshold = float(value) / 100
        case DirectiveType.COMPACTION_MAX:
            # Parse "95" or "95%" -> 0.95
            value = directive.value.rstrip("%")
            conv.compaction_max = float(value) / 100

        # Elision - merge adjacent elements
        case DirectiveType.ELIDE:
            conv.steps.append(ConversationStep(type="elide", content=directive.value))

        case DirectiveType.CHECKPOINT_AFTER:
            conv.checkpoint_after = directive.value
        case DirectiveType.CHECKPOINT_NAME:
            conv.checkpoint_name = directive.value

        # Output (with template variable support)
        case DirectiveType.OUTPUT:
            conv.output_file = directive.value
        case DirectiveType.OUTPUT_FORMAT:
            conv.output_format = directive.value
        case DirectiveType.OUTPUT_FILE:
            conv.output_file = directive.value
        case DirectiveType.OUTPUT_DIR:
            conv.output_dir = directive.value

        # Output injection (prepend/append to output)
        case DirectiveType.HEADER:
            conv.headers.append(directive.value)
        case DirectiveType.FOOTER:
            conv.footers.append(directive.value)

        # Command execution settings
        case DirectiveType.RUN:
            conv.steps.append(ConversationStep(type="run", content=directive.value))
        case DirectiveType.RUN_RETRY:
            # RUN-RETRY modifies the previous RUN step to enable retry-with-AI-fix
            # Format: N "prompt" or N 'prompt' where N is retry count
            # Examples: RUN-RETRY 3 "Fix the failing tests"
            #           RUN-RETRY 2 'Analyze and fix errors'
            value = directive.value.strip()
            match = re.match(r'^(\d+)\s+["\'](.+)["\']$', value, re.DOTALL)
            if match:
                retry_count = int(match.group(1))
                retry_prompt = match.group(2)
            else:
                # Fallback: first word is count, rest is prompt
                parts = value.split(None, 1)
                retry_count = int(parts[0]) if parts else 3
                retry_prompt = parts[1] if len(parts) > 1 else "Fix the error and try again"

            # Find the last RUN step and attach retry config to it
            for i in range(len(conv.steps) - 1, -1, -1):
                if conv.steps[i].type == "run":
                    conv.steps[i].retry_count = retry_count
                    conv.steps[i].retry_prompt = retry_prompt
                    break
            else:
                # No preceding RUN - create standalone (will fail at execution if no command)
                conv.steps.append(ConversationStep(
                    type="run",
                    content="",
                    retry_count=retry_count,
                    retry_prompt=retry_prompt
                ))
        case DirectiveType.RUN_ASYNC:
            conv.steps.append(ConversationStep(type="run_async", content=directive.value))
        case DirectiveType.RUN_WAIT:
            conv.steps.append(ConversationStep(type="run_wait", content=directive.value))
        case DirectiveType.RUN_ON_ERROR:
            conv.run_on_error = directive.value.lower()
        case DirectiveType.RUN_OUTPUT:
            conv.run_output = directive.value.lower()
        case DirectiveType.RUN_OUTPUT_LIMIT:
            # Parse limit: "10K", "50K", "100000", "none"
            value = directive.value.strip().lower()
            if value in ("none", "unlimited", ""):
                conv.run_output_limit = None
            elif value.endswith("k"):
                conv.run_output_limit = int(value[:-1]) * 1000
            elif value.endswith("m"):
                conv.run_output_limit = int(value[:-1]) * 1000000
            else:
                conv.run_output_limit = int(value)
        case DirectiveType.ALLOW_SHELL:
            # Parse "true", "yes", "1" as True, anything else as False
            conv.allow_shell = directive.value.lower() in ("true", "yes", "1", "")
        case DirectiveType.RUN_ENV:
            # Parse "KEY=value" format
            if "=" in directive.value:
                key, value = directive.value.split("=", 1)
                conv.run_env[key.strip()] = value.strip()
        case DirectiveType.RUN_CWD:
            # Set working directory for RUN commands
            conv.run_cwd = directive.value.strip()
        case DirectiveType.RUN_TIMEOUT:
            # Parse timeout in seconds (supports "30", "30s", "2m")
            value = directive.value.strip().lower()
            if value.endswith("m"):
                conv.run_timeout = int(value[:-1]) * 60
            elif value.endswith("s"):
                conv.run_timeout = int(value[:-1])
            else:
                conv.run_timeout = int(value)

        # Verification directives
        case DirectiveType.VERIFY:
            # VERIFY <type> [options]
            # Examples: VERIFY refs, VERIFY links --external, VERIFY all
            parts = directive.value.strip().split(None, 1)
            verify_type = parts[0].lower() if parts else "all"
            options = {}
            if len(parts) > 1:
                # Parse --key=value or --key options
                for opt_match in re.finditer(r'--(\w+)(?:=(\S+))?', parts[1]):
                    key = opt_match.group(1)
                    value = opt_match.group(2) if opt_match.group(2) else "true"
                    options[key] = value
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type=verify_type,
                verify_options=options
            ))
        case DirectiveType.VERIFY_ON_ERROR:
            conv.verify_on_error = directive.value.strip().lower()
        case DirectiveType.VERIFY_OUTPUT:
            conv.verify_output = directive.value.strip().lower()
        case DirectiveType.VERIFY_LIMIT:
            # Parse limit: "5K", "10K", "50K", "none"
            value = directive.value.strip().lower()
            if value in ("none", "unlimited", ""):
                conv.verify_limit = None
            elif value.endswith("k"):
                conv.verify_limit = int(value[:-1]) * 1000
            elif value.endswith("m"):
                conv.verify_limit = int(value[:-1]) * 1000000
            else:
                conv.verify_limit = int(value)
        case DirectiveType.VERIFY_TRACE:
            # Parse trace link: "UCA-001 -> REQ-020" or "UCA-001 → REQ-020"
            value = directive.value.strip()
            # Support both -> and → as arrow
            trace_pattern = r'^([A-Z]+-[A-Z0-9-]+[a-z]?)\s*(?:->|→)\s*([A-Z]+-[A-Z0-9-]+[a-z]?)$'
            match = re.match(trace_pattern, value)
            if match:
                from_id = match.group(1)
                to_id = match.group(2)
                conv.verify_trace_links.append((from_id, to_id))
                # Also add as a verify step so it runs during execution
                conv.steps.append(ConversationStep(
                    type="verify_trace",
                    content=f"{from_id} -> {to_id}",
                    verify_type="trace",
                    verify_options={"from": from_id, "to": to_id}
                ))
            else:
                # Invalid format - will be caught during validation
                pass
        case DirectiveType.VERIFY_COVERAGE:
            # Parse coverage check: "metric >= threshold" or empty for report
            # Examples: "uca_to_sc >= 80", "overall >= 50", ""
            value = directive.value.strip()
            if value:
                # Parse metric comparison: metric op threshold
                match = re.match(r'^(\w+)\s*(>=|<=|>|<|==)\s*(\d+(?:\.\d+)?)%?$', value)
                if match:
                    metric = match.group(1)
                    op = match.group(2)
                    threshold = float(match.group(3))
                    conv.verify_coverage_checks.append((metric, op, threshold))
                    conv.steps.append(ConversationStep(
                        type="verify_coverage",
                        content=value,
                        verify_type="coverage",
                        verify_options={"metric": metric, "op": op, "threshold": threshold}
                    ))
                else:
                    # Invalid format - will be caught during validation
                    pass
            else:
                # Empty value = just run coverage report (no threshold check)
                conv.steps.append(ConversationStep(
                    type="verify_coverage",
                    content="coverage report",
                    verify_type="coverage",
                    verify_options={"report_only": True}
                ))

        # CHECK-* aliases for common VERIFY types
        case DirectiveType.CHECK_REFS:
            # Alias for VERIFY refs
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="refs",
                verify_options={}
            ))
        case DirectiveType.CHECK_LINKS:
            # Alias for VERIFY links
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="links",
                verify_options={}
            ))
        case DirectiveType.CHECK_TRACEABILITY:
            # Alias for VERIFY traceability
            conv.steps.append(ConversationStep(
                type="verify",
                verify_type="traceability",
                verify_options={}
            ))

        case DirectiveType.PAUSE:
            # PAUSE after the last prompt added so far
            pause_index = len(conv.prompts) - 1 if conv.prompts else 0
            conv.pause_points.append((pause_index, directive.value))

        case DirectiveType.CONSULT:
            # CONSULT after the last prompt - like PAUSE but with proactive question presentation
            consult_index = len(conv.prompts) - 1 if conv.prompts else 0
            conv.consult_points.append((consult_index, directive.value))

        case DirectiveType.CONSULT_TIMEOUT:
            # Timeout for CONSULT (e.g., "1h", "30m", "7d")
            conv.consult_timeout = directive.value.strip()

        # LSP - Language Server Protocol queries
        case DirectiveType.LSP:
            # LSP type <name> [-p path] [-l lang]
            # Creates a step that injects type definition into context
            conv.steps.append(ConversationStep(
                type="lsp",
                content=directive.value.strip()
            ))

        # Debug directives
        case DirectiveType.DEBUG:
            # Comma-separated debug categories
            categories = [c.strip().lower() for c in directive.value.split(",")]
            conv.debug_categories.extend(categories)
        case DirectiveType.DEBUG_INTENTS:
            # Boolean flag for intent tracking
            conv.debug_intents = directive.value.strip().lower() in ("true", "1", "yes", "on")
        case DirectiveType.EVENT_LOG:
            # Path for event log (supports template variables)
            conv.event_log = directive.value.strip()


def apply_directive_to_block(steps: list[ConversationStep], directive: Directive) -> None:
    """Apply a directive inside an ON-FAILURE/ON-SUCCESS block.

    Only a subset of directives are allowed inside blocks:
    - PROMPT - send a prompt to the AI
    - RUN - execute a shell command (no nested RUN-RETRY or ON-FAILURE)
    - CHECKPOINT - save state
    - COMPACT - compress context

    Configuration directives (MODEL, ADAPTER, etc.) are not allowed in blocks.
    """
    match directive.type:
        case DirectiveType.PROMPT:
            steps.append(ConversationStep(type="prompt", content=directive.value))
        case DirectiveType.RUN:
            steps.append(ConversationStep(type="run", content=directive.value))
        case DirectiveType.CHECKPOINT:
            steps.append(ConversationStep(type="checkpoint", content=directive.value))
        case DirectiveType.COMPACT:
            steps.append(ConversationStep(type="compact", preserve=[]))
        case DirectiveType.COMPACT_PRESERVE:
            # Modify the last COMPACT step if present
            for i in range(len(steps) - 1, -1, -1):
                if steps[i].type == "compact":
                    steps[i].preserve.append(directive.value)
                    break
        case DirectiveType.PAUSE:
            steps.append(ConversationStep(type="pause"))
        case DirectiveType.CONSULT:
            steps.append(ConversationStep(type="consult", content=directive.value))
        case DirectiveType.NEW_CONVERSATION:
            steps.append(ConversationStep(type="new_conversation"))
        case _:
            # Silently ignore configuration directives in blocks
            # This allows blocks to contain only execution-oriented directives
            pass


# Aliases for backward compatibility
_apply_directive = apply_directive
_apply_directive_to_block = apply_directive_to_block
