"""Progressive MCP mode — tool schemas are injected dynamically.

Instead of sending all ~101 tool schemas upfront, the progressive mode sends
only a single ``search_tools`` schema to the LLM.  After the LLM calls
``search_tools``, the system performs a keyword search over all tool
definitions and injects only the top-k matching tool schemas into the next
API call.

Flow:
    1. Fetch all tools from the MCP server (to build the search index).
    2. Send only the ``search_tools`` schema + user message to the LLM.
    3. LLM calls ``search_tools(query=…)``.
    4. Search locally for the top-k matching tools.
    5. Inject candidate tool schemas and let the LLM call a tool.
    6. LLM generates a final answer using the tool result.

The schema-token count is dramatically lower than the naive mode because
only one small schema is sent in the initial request.
"""

import json
from backend.mcp_client import list_all_tools, call_tool
from backend.llm_client import chat_completion, extract_tool_call, extract_content
from backend.tool_search import search
from backend.token_counter import count_schema_tokens, count_message_tokens


#: Schema for the single ``search_tools`` tool that the LLM sees initially.
SEARCH_TOOL_SCHEMA = {
    "name": "search_tools",
    "description": (
        "Search the tool catalog for tools relevant to the user's query. "
        "This is the ONLY tool you have. You MUST call it first. "
        "After calling it, the system will return matching tools that "
        "you can then use to answer the user's question."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search query. Use keywords from the user's request. "
                    "For example: 'weather', 'customer', 'order', 'invoice'. "
                    "Both English and German keywords are supported."
                ),
            },
        },
        "required": ["query"],
    },
}

#: System prompt for the search phase.  Forces the LLM to call
#: ``search_tools`` before attempting to answer.
SEARCH_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a large catalog of tools "
    "(weather, customers, orders, finance, and more). However, you cannot "
    "see all tools at once.\n\n"
    "You have ONE tool available right now: search_tools. "
    "You MUST call search_tools with a relevant query to discover the "
    "actual tools you need. This is mandatory — do NOT answer the user's "
    "question directly without first calling search_tools.\n\n"
    "Example: If the user asks 'Wie ist das Wetter in Leipzig?', call "
    "search_tools(query='Wetter Leipzig'). The system will then provide "
    "you with the relevant weather tools.\n\n"
    "Always respond in the same language as the user's query."
)

#: System prompt for the execution phase.  The LLM now sees a small set
#: of candidate tools and must call one of them.
EXECUTE_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a few relevant tools. "
    "You MUST call the most appropriate tool to answer the user's question. "
    "Do not refuse or say you cannot access data — you have the tools. "
    "Always respond in the same language as the user's query."
)


async def run_progressive_mode(user_message: str) -> dict:
    """Execute the progressive MCP mode for a single user message.

    Only a ``search_tools`` schema is sent initially.  After the LLM
    searches, matching candidate tools are injected dynamically.

    Args:
        user_message: The user's input prompt.

    Returns:
        A result dict containing ``mode``, ``tools_available``,
        ``tools_sent_to_llm``, ``schema_tokens``, ``message_tokens``,
        ``total_tokens``, ``answer``, and ``steps``.
    """
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

    # Step 3: LLM calls search_tools (forced via tool_choice)
    llm_response = await chat_completion(
        messages,
        tools=search_tools,
        tool_choice="required",
    )
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

    llm_response = await chat_completion(
        messages,
        tools=candidates,
        tool_choice="required",
    )
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
