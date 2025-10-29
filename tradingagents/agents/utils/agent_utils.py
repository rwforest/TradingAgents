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
    get_income_statement
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
    2. Removes consecutive messages of the same role (keeps the last one)
    3. Ensures proper user->assistant->user->assistant flow

    Args:
        messages: List of messages (can be tuples, dict, or Message objects)

    Returns:
        Filtered list of messages that properly alternate roles
    """
    if not messages:
        return messages

    filtered = []
    last_role = None

    for i, msg in enumerate(messages):
        # Handle ToolMessages specially
        if isinstance(msg, ToolMessage):
            # Check if the last message in filtered list has tool_calls
            if filtered:
                last_msg = filtered[-1]
                if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                    # Valid tool message, append it (doesn't count toward alternation)
                    filtered.append(msg)
            # Skip orphaned ToolMessages
            continue

        # Determine the role of the current message
        if isinstance(msg, tuple):
            current_role = "user" if msg[0] in ["human", "user"] else "assistant" if msg[0] == "system" else msg[0]
        elif isinstance(msg, dict):
            current_role = "user" if msg.get("role") in ["human", "user"] else msg.get("role", "assistant")
        elif isinstance(msg, HumanMessage):
            current_role = "user"
        elif isinstance(msg, AIMessage):
            current_role = "assistant"
        elif isinstance(msg, SystemMessage):
            current_role = "system"
        else:
            current_role = "assistant"

        # System messages can appear at the start, don't count toward alternation
        if current_role == "system":
            if not filtered or last_role is None:
                filtered.append(msg)
            continue

        # Skip consecutive messages of the same role (except system)
        if current_role == last_role:
            # Replace the last message with the current one (keep the most recent)
            if filtered and last_role is not None:
                # Find the last message with this role (skip over ToolMessages)
                for j in range(len(filtered) - 1, -1, -1):
                    if not isinstance(filtered[j], ToolMessage):
                        filtered[j] = msg
                        break
        else:
            filtered.append(msg)
            last_role = current_role

    return filtered


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


