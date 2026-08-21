import json

try:
    import tiktoken
    _ENCODER = tiktoken.encoding_for_model("gpt-4")
except Exception:
    _ENCODER = None


def _count_tokens(text: str) -> int:
    if _ENCODER is not None:
        return len(_ENCODER.encode(text))
    return len(text) // 4


def count_schema_tokens(tools: list[dict]) -> int:
    total = 0
    for tool in tools:
        tool_json = json.dumps(tool, ensure_ascii=False)
        total += _count_tokens(tool_json)
    return total


def count_message_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        msg_json = json.dumps(msg, ensure_ascii=False)
        total += _count_tokens(msg_json)
    return total


def count_tokens(text: str) -> int:
    return _count_tokens(text)
