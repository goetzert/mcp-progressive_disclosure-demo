import json
import httpx
from backend.config import settings


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
) -> dict:
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

    async with httpx.AsyncClient(timeout=settings.scadsai_request_timeout) as client:
        response = await client.post(
            f"{settings.scadsai_api_base}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def extract_tool_call(response: dict) -> dict | None:
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
    choices = response.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")
