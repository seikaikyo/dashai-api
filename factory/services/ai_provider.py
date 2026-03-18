"""LLM provider abstraction: OpenAI / Claude, switchable via AI_PROVIDER env var."""

import os
import json
import logging

logger = logging.getLogger(__name__)

AI_PROVIDER = os.getenv('AI_PROVIDER', 'claude')

SYSTEM_PROMPT = """You are DashAI Assistant, an AI agent that can query, analyze, AND control a smart factory system.
You have access to 54 subsystems (ERP, MES, QMS, WMS, TMS, SCADA, SRM, AGV) with real data.

CAPABILITIES (15 tools):
READ: query_orders, query_work_orders, get_dashboard_kpis, trace_order, search_quality_issues
WRITE: update_order_status, create_work_order, update_work_order, create_quality_issue, close_quality_issue, create_shipment
ANALYZE: analyze_impact (what-if), smart_schedule (auto-scheduling), factory_briefing (health check)
SYSTEM: reset_demo (reset to initial state, ask confirmation first)

IMPORTANT - You are an operations agent, not just a chatbot:
- When user describes a situation, take action. Don't just report - execute.
- Chain multiple tools in sequence for complex operations.
- For "what if" questions, use analyze_impact to show cascading effects.
- For scheduling, use smart_schedule to propose plans. Ask before executing.
- After write operations, summarize all changes made.

MULTI-STEP EXAMPLES:
- "Order SO-0001 is urgent" → trace_order → update_order_status(urgent note) → smart_schedule(execute=false) → propose plan
- "Line 3 yield dropped" → search_quality_issues → create_quality_issue → update_work_order(pause Line 3) → query_work_orders(find capacity)
- "Ship everything ready" → query_orders(status=confirmed) → create_shipment for each → report summary
- "What if we cancel SO-0003?" → analyze_impact(cancel) → present financial/KPI impact → suggest alternatives
- "Schedule this week's production" → smart_schedule(execute=false) → present plan → wait for confirmation → smart_schedule(execute=true)

Business process knowledge:
- Order flow: draft → confirmed → in_production → shipped → delivered
- Work order flow: created → in_progress → completed
- NCR flow: open → investigating → corrective_action → closed
- When creating shipment, order status auto-updates to shipped.
- For reset_demo, ALWAYS ask user to confirm before executing.

Rules:
- Use data to support answers, do not guess
- Proactively alert on anomalies
- Respond in the same language the user uses
- Be concise and actionable
- Format numbers with commas"""


def _convert_tools_for_claude(openai_tools: list) -> list:
    """Convert OpenAI tool format to Claude tool format."""
    claude_tools = []
    for t in openai_tools:
        f = t['function']
        claude_tools.append({
            'name': f['name'],
            'description': f['description'],
            'input_schema': f['parameters'],
        })
    return claude_tools


def chat_completion(
    messages: list,
    tools: list,
    user_api_key: str = '',
    user_provider: str = '',
) -> dict:
    """Send messages + tools to LLM, return response with possible tool calls.

    If user_api_key is provided, use that instead of server key (BYOK mode).
    """
    provider = user_provider or AI_PROVIDER
    if provider == 'claude':
        return _claude_chat(messages, tools, api_key=user_api_key)
    return _openai_chat(messages, tools, api_key=user_api_key)


def _openai_chat(messages: list, tools: list, api_key: str = '') -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    full_messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + messages

    kwargs = {
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o'),
        'messages': full_messages,
    }
    if tools:
        kwargs['tools'] = tools
        kwargs['tool_choice'] = 'auto'

    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message

    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append({
                'name': tc.function.name,
                'arguments': json.loads(tc.function.arguments),
            })

    return {
        'content': msg.content,
        'tool_calls': tool_calls,
    }


def _claude_chat(messages: list, tools: list, api_key: str = '') -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    claude_tools = _convert_tools_for_claude(tools)

    # Claude uses separate system param
    claude_messages = []
    for m in messages:
        if m['role'] == 'system':
            continue
        claude_messages.append(m)

    kwargs = {
        'model': os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
        'max_tokens': 2048,
        'system': SYSTEM_PROMPT,
        'messages': claude_messages,
    }
    if claude_tools:
        kwargs['tools'] = claude_tools

    resp = client.messages.create(**kwargs)

    content = None
    tool_calls = []
    for block in resp.content:
        if block.type == 'text':
            content = block.text
        elif block.type == 'tool_use':
            tool_calls.append({
                'name': block.name,
                'arguments': block.input,
            })

    return {
        'content': content,
        'tool_calls': tool_calls,
    }


def format_tool_result(
    messages: list, tool_calls: list, results: list,
    user_provider: str = '',
) -> list:
    """Append tool call + result messages for the second LLM call."""
    provider = user_provider or AI_PROVIDER
    if provider == 'claude':
        return _format_claude_tool_result(messages, tool_calls, results)
    return _format_openai_tool_result(messages, tool_calls, results)


def _format_openai_tool_result(messages: list, tool_calls: list, results: list) -> list:
    import uuid

    # Add assistant message with tool calls
    oai_tool_calls = []
    for i, tc in enumerate(tool_calls):
        call_id = f'call_{uuid.uuid4().hex[:24]}'
        oai_tool_calls.append({
            'id': call_id,
            'type': 'function',
            'function': {
                'name': tc['name'],
                'arguments': json.dumps(tc['arguments']),
            },
        })

    new_messages = messages + [
        {'role': 'assistant', 'tool_calls': oai_tool_calls},
    ]

    for i, result in enumerate(results):
        new_messages.append({
            'role': 'tool',
            'tool_call_id': oai_tool_calls[i]['id'],
            'content': json.dumps(result, default=str, ensure_ascii=False),
        })

    return new_messages


def _format_claude_tool_result(messages: list, tool_calls: list, results: list) -> list:
    import uuid

    # Assistant message with tool_use blocks
    assistant_content = []
    tool_ids = []
    for tc in tool_calls:
        tid = f'toolu_{uuid.uuid4().hex[:24]}'
        tool_ids.append(tid)
        assistant_content.append({
            'type': 'tool_use',
            'id': tid,
            'name': tc['name'],
            'input': tc['arguments'],
        })

    # User message with tool_result blocks
    result_content = []
    for i, result in enumerate(results):
        result_content.append({
            'type': 'tool_result',
            'tool_use_id': tool_ids[i],
            'content': json.dumps(result, default=str, ensure_ascii=False),
        })

    return messages + [
        {'role': 'assistant', 'content': assistant_content},
        {'role': 'user', 'content': result_content},
    ]
