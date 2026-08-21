import json
from backend.mcp_client import list_all_tools, call_tool
from backend.llm_client import chat_completion, extract_tool_call, extract_content
from backend.token_counter import count_schema_tokens, count_message_tokens


SYSTEM_PROMPT = (
    "You are a helpful assistant with access to various tools. "
    "When the user asks a question, select the most appropriate tool "
    "and call it. Use the tool results to formulate your answer. "
    "Always respond in the same language as the user's query."
)


async def run_naive_mode(user_message: str) -> dict:
    steps = []
    total_schema_tokens = 0
    total_message_tokens = 0

    # Step 1: Get all tools from MCP server
    all_tools = await list_all_tools()
    steps.append({
        "step": 1,
        "description": "Fetch all tools from MCP server",
        "tools_count": len(all_tools),
        "tools_sent_to_llm": len(all_tools),
    })

    # Step 2: Send all tools to LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    schema_tokens = count_schema_tokens(all_tools)
    message_tokens = count_message_tokens(messages)
    total_schema_tokens += schema_tokens
    total_message_tokens += message_tokens

    steps.append({
        "step": 2,
        "description": f"Send all {len(all_tools)} tool schemas to LLM",
        "schema_tokens": schema_tokens,
        "message_tokens": message_tokens,
        "tools_sent_to_llm": len(all_tools),
    })

    # Step 3: LLM selects and calls a tool
    llm_response = await chat_completion(messages, tools=all_tools)
    tool_call = extract_tool_call(llm_response)

    if tool_call:
        tool_result = await call_tool(tool_call["name"], tool_call["arguments"])

        # Add tool call and result to messages
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call["id"],
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": json.dumps(tool_call["arguments"]),
                },
            }],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(tool_result),
        })

        # Step 4: LLM generates final answer with tool result
        final_response = await chat_completion(messages, tools=all_tools)
        answer = extract_content(final_response)

        message_tokens = count_message_tokens(messages)
        total_message_tokens += message_tokens

        steps.append({
            "step": 3,
            "description": f"LLM calls tool: {tool_call['name']}({tool_call['arguments']})",
            "tool_name": tool_call["name"],
            "tool_arguments": tool_call["arguments"],
            "tool_result": tool_result,
        })
        steps.append({
            "step": 4,
            "description": "LLM generates final answer",
            "answer": answer,
        })
    else:
        answer = extract_content(llm_response)
        steps.append({
            "step": 3,
            "description": "LLM generates answer (no tool call)",
            "answer": answer,
        })

    total_tokens = total_schema_tokens + total_message_tokens

    return {
        "mode": "normal",
        "tools_available": len(all_tools),
        "tools_sent_to_llm": len(all_tools),
        "schema_tokens": total_schema_tokens,
        "message_tokens": total_message_tokens,
        "total_tokens": total_tokens,
        "answer": answer,
        "steps": steps,
    }
