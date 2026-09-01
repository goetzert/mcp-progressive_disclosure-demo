"""Thin HTTP client for the ScaDS.AI chat-completion API.

Provides async functions to send a chat-completion request (optionally with
tool definitions) and helper functions to extract tool calls and plain text
content from the API response.
"""

import json
import httpx
from backend.config import settings


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
    tool_choice: str | None = None,
) -> dict:
    """Send a chat-completion request to the ScaDS.AI API.

    Args:
        messages: Conversation messages following the OpenAI format.
        tools: Optional list of tool schemas (OpenAI function-calling format).
        model: Override the configured chat model.
        tool_choice: Control tool selection (``"auto"``, ``"required"``, or ``None``).

    Returns:
        The raw JSON response from the API.
    """
    headers = {
        "Authorization": f"Bearer {settings.scadsai_api_key}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "model": model or settings.scadsai_chat_model,
        "messages": messages,
    }

    if tools:
        payload["tools"] = [
            {"type": "function", "function": t} for t in tools
        ]
        if tool_choice:
            payload["tool_choice"] = tool_choice

    async with httpx.AsyncClient(timeout=settings.scadsai_request_timeout) as client:
        response = await client.post(
            f"{settings.scadsai_api_base}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def extract_tool_call(response: dict) -> dict | None:
    """Extract the first tool call from an API response.

    Args:
        response: The JSON response returned by :func:`chat_completion`.

    Returns:
        A dict with ``id``, ``name``, and ``arguments`` keys, or ``None`` if
        the response contains no tool calls.
    """
    choices = response.get("choices", [])
    if not choices:
        return None

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        return None

    tc = tool_calls[0]
    function = tc.get("function", {})
    return {
        "id": tc.get("id"),
        "name": function.get("name"),
        "arguments": json.loads(function.get("arguments", "{}")),
    }


def extract_content(response: dict) -> str:
    """Extract the plain-text content from an API response.

    Args:
        response: The JSON response returned by :func:`chat_completion`.

    Returns:
        The content string, or an empty string if no content is present.
    """
    choices = response.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")
