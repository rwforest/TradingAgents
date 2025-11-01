from langchain_core.messages import HumanMessage, RemoveMessage, AIMessage, ToolMessage, SystemMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_company_info
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news    
)

def ensure_message_alternation(messages):
    """
    Ensure messages alternate between user/human and assistant/AI roles.
    Fixes the Databricks/OpenAI API error: "Chat message input roles must alternate"

    This function:
    1. Filters out orphaned ToolMessages (without preceding AIMessage with tool_calls)
    2. Removes consecutive messages of the same role (keeps the last one WITH its ToolMessages)
    3. Ensures proper user->assistant->user->assistant flow
    4. Maintains tool_call_id integrity

    Args:
        messages: List of messages (can be tuples, dict, or Message objects)

    Returns:
        Filtered list of messages that properly alternate roles
    """
    if not messages:
        return messages

    # First pass: group messages with their tool responses
    # Format: [(role, [msg, toolmsg1, toolmsg2, ...]), ...]
    grouped = []
    current_group = []
    current_role = None

    for msg in messages:
        # Handle ToolMessages - attach to previous group
        if isinstance(msg, ToolMessage):
            if current_group:
                current_group.append(msg)
            continue

        # Determine role
        if isinstance(msg, tuple):
            role = "user" if msg[0] in ["human", "user"] else "assistant" if msg[0] == "system" else msg[0]
        elif isinstance(msg, dict):
            role = "user" if msg.get("role") in ["human", "user"] else msg.get("role", "assistant")
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, SystemMessage):
            role = "system"
        else:
            role = "assistant"

        # Start new group
        if current_group:
            grouped.append((current_role, current_group))
        current_group = [msg]
        current_role = role

    # Add last group
    if current_group:
        grouped.append((current_role, current_group))

    # Second pass: filter out consecutive same-role groups, keeping the last one
    filtered_groups = []
    last_role = None

    for role, group in grouped:
        # System messages at start don't count
        if role == "system" and (not filtered_groups or last_role is None):
            filtered_groups.append((role, group))
            continue

        # If same role as last, replace the last group
        if role == last_role and role != "system":
            if filtered_groups:
                filtered_groups[-1] = (role, group)
        else:
            filtered_groups.append((role, group))
            last_role = role

    # Third pass: validate tool messages and flatten back to list
    result = []
    for role, group in filtered_groups:
        # Add the main message
        main_msg = group[0]
        result.append(main_msg)

        # Add tool messages only if main message has tool_calls
        if len(group) > 1:
            if isinstance(main_msg, AIMessage) and hasattr(main_msg, 'tool_calls') and main_msg.tool_calls:
                # Get valid tool_call_ids
                valid_ids = {tc['id'] if isinstance(tc, dict) else tc.id for tc in main_msg.tool_calls}
                # Only add ToolMessages with matching tool_call_ids
                for tool_msg in group[1:]:
                    if isinstance(tool_msg, ToolMessage):
                        if hasattr(tool_msg, 'tool_call_id') and tool_msg.tool_call_id in valid_ids:
                            result.append(tool_msg)

    return result


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


