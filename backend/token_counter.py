"""Token-counting utilities for schema, message, and plain-text estimation.

Uses ``tiktoken`` (GPT-4 encoding) when available for accurate counts. Falls
back to a character-based approximation (~4 chars/token) if tiktoken cannot be
imported — for example, on Python 3.14 where native wheels may not yet exist.
"""

import json

try:
    import tiktoken
    _ENCODER = tiktoken.encoding_for_model("gpt-4")
except Exception:
    _ENCODER = None


def _count_tokens(text: str) -> int:
    """Count tokens in *text* using tiktoken, or approximate if unavailable."""
    if _ENCODER is not None:
        return len(_ENCODER.encode(text))
    return len(text) // 4


def count_schema_tokens(tools: list[dict]) -> int:
    """Count the total tokens across all tool schema JSON representations.

    Args:
        tools: List of tool dicts (each will be JSON-serialised and counted).

    Returns:
        The sum of token counts for every tool schema.
    """
    total = 0
    for tool in tools:
        tool_json = json.dumps(tool, ensure_ascii=False)
        total += _count_tokens(tool_json)
    return total


def count_message_tokens(messages: list[dict]) -> int:
    """Count the total tokens across all conversation messages.

    Args:
        messages: List of message dicts (each will be JSON-serialised and counted).

    Returns:
        The sum of token counts for every message.
    """
    total = 0
    for msg in messages:
        msg_json = json.dumps(msg, ensure_ascii=False)
        total += _count_tokens(msg_json)
    return total


def count_tokens(text: str) -> int:
    """Count tokens in an arbitrary string."""
    return _count_tokens(text)
