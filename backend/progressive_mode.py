import json
from backend.mcp_client import list_all_tools, call_tool
from backend.llm_client import chat_completion, extract_tool_call, extract_content
from backend.tool_search import search
from backend.token_counter import count_schema_tokens, count_message_tokens


SEARCH_TOOL_SCHEMA = {
    "name": "search_tools",
    "description": (
        "Search for relevant tools by keyword. Use this to find tools "
        "that match the user's query. Returns a list of matching tool names."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to find relevant tools.",
            },
        },
        "required": ["query"],
    },
}

SEARCH_SYSTEM_PROMPT = (
    "You are a helpful assistant. You have access to a single tool: "
    "search_tools. Use it to find relevant tools for the user's query. "
    "Always respond in the same language as the user's query."
)

EXECUTE_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a few relevant tools. "
    "Select the most appropriate tool and call it. "
    "Always respond in the same language as the user's query."
)


async def run_progressive_mode(user_message: str) -> dict:
    steps = []
    total_schema_tokens = 0
    total_message_tokens = 0

    # Step 1: Get all tools from MCP server (for search index)
    all_tools = await list_all_tools()
    steps.append({
        "step": 1,
        "description": "Fetch all tools from MCP server (for search index)",
        "tools_count": len(all_tools),
        "tools_sent_to_llm": 1,
    })

    # Step 2: Send only search_tools schema to LLM
    search_tools = [SEARCH_TOOL_SCHEMA]
    messages = [
        {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    schema_tokens = count_schema_tokens(search_tools)
    message_tokens = count_message_tokens(messages)
    total_schema_tokens += schema_tokens
    total_message_tokens += message_tokens

    steps.append({
        "step": 2,
        "description": "Send only search_tools schema to LLM (1 tool)",
        "schema_tokens": schema_tokens,
        "message_tokens": message_tokens,
        "tools_sent_to_llm": 1,
    })

    # Step 3: LLM calls search_tools
    llm_response = await chat_completion(messages, tools=search_tools)
    tool_call = extract_tool_call(llm_response)

    if not tool_call or tool_call["name"] != "search_tools":
        answer = extract_content(llm_response)
        steps.append({
            "step": 3,
            "description": "LLM did not call search_tools",
            "answer": answer,
        })
        return {
            "mode": "progressive",
            "tools_available": len(all_tools),
            "tools_sent_to_llm": 1,
            "schema_tokens": total_schema_tokens,
            "message_tokens": total_message_tokens,
            "total_tokens": total_schema_tokens + total_message_tokens,
            "answer": answer,
            "steps": steps,
        }

    search_query = tool_call["arguments"].get("query", user_message)
    candidates = search(search_query, all_tools, top_k=5)

    steps.append({
        "step": 3,
        "description": f"LLM calls search_tools(query={search_query!r})",
        "search_query": search_query,
        "candidates_found": len(candidates),
        "candidate_names": [c["name"] for c in candidates],
    })

    # Step 4: Inject candidate tool schemas and let LLM call a tool
    messages = [
        {"role": "system", "content": EXECUTE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    schema_tokens = count_schema_tokens(candidates)
    message_tokens = count_message_tokens(messages)
    total_schema_tokens += schema_tokens
    total_message_tokens += message_tokens

    llm_response = await chat_completion(messages, tools=candidates)
    tool_call = extract_tool_call(llm_response)

    if tool_call:
        tool_result = await call_tool(tool_call["name"], tool_call["arguments"])

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

        steps.append({
            "step": 4,
            "description": f"LLM calls tool: {tool_call['name']}({tool_call['arguments']})",
            "tool_name": tool_call["name"],
            "tool_arguments": tool_call["arguments"],
            "tool_result": tool_result,
        })

        # Step 5: LLM generates final answer
        final_response = await chat_completion(messages, tools=candidates)
        answer = extract_content(final_response)

        message_tokens = count_message_tokens(messages)
        total_message_tokens += message_tokens

        steps.append({
            "step": 5,
            "description": "LLM generates final answer",
            "answer": answer,
        })
    else:
        answer = extract_content(llm_response)
        steps.append({
            "step": 4,
            "description": "LLM generates answer (no tool call)",
            "answer": answer,
        })

    total_tokens = total_schema_tokens + total_message_tokens

    return {
        "mode": "progressive",
        "tools_available": len(all_tools),
        "tools_sent_to_llm": 1,
        "schema_tokens": total_schema_tokens,
        "message_tokens": total_message_tokens,
        "total_tokens": total_tokens,
        "answer": answer,
        "steps": steps,
    }
