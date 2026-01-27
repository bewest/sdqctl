"""
Verification step handlers for workflow execution.

Handles VERIFY, VERIFY-TRACE, and VERIFY-COVERAGE directives during runs.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..core.conversation import ConversationFile
    from ..core.session import Session

logger = logging.getLogger("sdqctl.commands.verify_steps")


def execute_verify_step(
    step: Any,
    conv: "ConversationFile",
    session: "Session",
    progress: Callable[[str], None],
) -> None:
    """Execute a VERIFY step.

    Args:
        step: ConversationStep with verify_type and verify_options
        conv: ConversationFile for settings
        session: Session for context injection
        progress: Progress callback
    """
    from ..verifiers import VERIFIERS
    from .utils import truncate_output

    verify_type = getattr(step, 'verify_type', step.get('verify_type', 'all'))
    verify_options = getattr(step, 'verify_options', step.get('verify_options', {}))

    logger.info(f"🔍 VERIFY: {verify_type}")
    progress(f"  🔍 Verifying: {verify_type}")

    # Determine path to verify (workflow dir by default)
    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
    if 'path' in verify_options:
        verify_path = Path(verify_options['path'])

    # Run appropriate verifier(s)
    verification_results = []
    if verify_type == "all":
        verifier_names = list(VERIFIERS.keys())
    else:
        verifier_names = [verify_type]

    all_passed = True
    for name in verifier_names:
        if name in VERIFIERS:
            verifier = VERIFIERS[name]()
            result = verifier.verify(verify_path)
            verification_results.append((name, result))
            if not result.passed:
                all_passed = False
                logger.warning(f"  ✗ {name}: {len(result.errors)} errors")
            else:
                logger.info(f"  ✓ {name}: passed")
        else:
            logger.warning(f"  ⚠ Unknown verifier: {name}")

    # Format output for context injection
    verify_output_lines = ["## Verification Results\n"]
    for name, result in verification_results:
        status = "✅ Passed" if result.passed else "❌ Failed"
        verify_output_lines.append(f"### {name}\n{status}: {result.summary}\n")
        if result.errors and conv.verify_output in ("always", "on-error"):
            for err in result.errors[:10]:  # Limit to first 10 errors
                err_line = f"- ERROR {err.file}:{err.line}: {err.message}"
                verify_output_lines.append(err_line)
            if len(result.errors) > 10:
                extra = len(result.errors) - 10
                verify_output_lines.append(f"- ... and {extra} more errors")

    verify_output = "\n".join(verify_output_lines)

    # Apply output limit if set
    if conv.verify_limit:
        verify_output = truncate_output(verify_output, conv.verify_limit)

    # Inject into session context based on verify_output setting
    should_inject = (
        conv.verify_output == "always" or
        (conv.verify_output == "on-error" and not all_passed)
    )
    if should_inject and conv.verify_output != "never":
        session.add_message("system", verify_output)

    # Handle failure based on verify_on_error setting
    if not all_passed:
        if conv.verify_on_error == "fail":
            raise RuntimeError(f"Verification failed: {verify_type}")
        elif conv.verify_on_error == "warn":
            progress(f"  ⚠ Verification warning: {verify_type}")


def execute_verify_trace_step(
    step: Any,
    conv: "ConversationFile",
    progress: Callable[[str], None],
) -> None:
    """Execute a VERIFY-TRACE step.

    Args:
        step: ConversationStep with verify_options containing from/to
        conv: ConversationFile for settings
        progress: Progress callback
    """
    from ..verifiers.traceability import TraceabilityVerifier

    opts = getattr(step, 'verify_options', step.get('verify_options', {}))
    from_id = opts.get('from', '')
    to_id = opts.get('to', '')

    logger.info(f"🔍 VERIFY-TRACE: {from_id} -> {to_id}")
    progress(f"  🔍 Verifying trace: {from_id} -> {to_id}")

    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
    verifier = TraceabilityVerifier()
    result = verifier.verify_trace(from_id, to_id, verify_path)

    if result.passed:
        logger.info(f"  ✓ Trace verified: {result.summary}")
    else:
        logger.warning(f"  ✗ Trace failed: {result.summary}")
        if conv.verify_on_error == "fail":
            raise RuntimeError(f"VERIFY-TRACE failed: {from_id} -> {to_id}")
        elif conv.verify_on_error == "warn":
            progress("  ⚠ Trace verification warning")


def execute_verify_coverage_step(
    step: Any,
    conv: "ConversationFile",
    progress: Callable[[str], None],
) -> None:
    """Execute a VERIFY-COVERAGE step.

    Args:
        step: ConversationStep with verify_options for coverage check
        conv: ConversationFile for settings
        progress: Progress callback
    """
    from ..verifiers.traceability import TraceabilityVerifier

    opts = getattr(step, 'verify_options', step.get('verify_options', {}))
    report_only = opts.get('report_only', False)
    metric = opts.get('metric')
    op = opts.get('op')
    threshold = opts.get('threshold')

    mode = 'report' if report_only else f'{metric} {op} {threshold}'
    logger.info(f"🔍 VERIFY-COVERAGE: {mode}")
    progress("  🔍 Verifying coverage")

    verify_path = conv.source_path.parent if conv.source_path else Path.cwd()
    verifier = TraceabilityVerifier()

    if report_only:
        result = verifier.verify_coverage(verify_path)
    else:
        result = verifier.verify_coverage(
            verify_path, metric=metric, op=op, threshold=threshold
        )

    if result.passed:
        logger.info(f"  ✓ Coverage: {result.summary}")
    else:
        logger.warning(f"  ✗ Coverage failed: {result.summary}")
        if conv.verify_on_error == "fail":
            raise RuntimeError(f"VERIFY-COVERAGE failed: {result.summary}")
        elif conv.verify_on_error == "warn":
            progress("  ⚠ Coverage verification warning")
