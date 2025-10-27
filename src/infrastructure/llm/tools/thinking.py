"""Thinking Tool for Working Memory and Multi-Hop Reasoning.

This tool provides a simple note-taking capability for the agent to support
multi-hop reasoning by recording intermediate thoughts and planning steps.

Async Support:
- When used with dspy.Tool wrapper, supports async execution via acall()
- Example: tool = dspy.Tool(jot); await tool.acall(note="...")
"""

import logging

logger = logging.getLogger(__name__)

def jot(note: str) -> str:
    """Record a thought, plan, or intermediate finding for multi-hop reasoning.

    This tool serves as a scratchpad for documenting your reasoning process
    during complex tasks. Use it to break down problems, plan sequential steps,
    track intermediate results, or note key observations.

    The tool validates the input and returns the recorded note for confirmation.

    Args:
        note: The thought, plan, or finding to record

    Returns:
        The recorded note, or an error message if the note is empty

    Examples:
        >>> jot("User needs help with complex analysis. Will break this into smaller steps.")
        "User needs help with complex analysis. Will break this into smaller steps."

        >>> jot("Step 1: Gather data. Step 2: Analyze patterns. Step 3: Generate insights.")
        "Step 1: Gather data. Step 2: Analyze patterns. Step 3: Generate insights."

        >>> jot("Found correlation between variables A and B. Next: examine variable C.")
        "Found correlation between variables A and B. Next: examine variable C."
    """
    if not note or not note.strip():
        logger.warning("Empty note provided to jot tool")
        return "Error: Cannot record empty thought."

    logger.info("Recording thought in working memory")
    logger.debug("Thought content: %s", note)

    return note
