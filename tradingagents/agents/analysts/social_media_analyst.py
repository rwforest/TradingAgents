from typing import List, Dict
 
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_social_media_mentions
from tradingagents.agents.utils.context_limiter import trim_messages_for_model
 
def _extract_social_tool_outputs(messages: List) -> List[str]:
    """Return only tool outputs produced by get_social_media_mentions."""
    tool_name_by_id: Dict[str, str] = {}
    outputs: List[str] = []
 
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                if isinstance(tc, dict):
                    call_id = tc.get("id")
                    name = tc.get("name")
                else:
                    call_id = getattr(tc, "id", None)
                    name = getattr(tc, "name", None)
                if call_id:
                    tool_name_by_id[call_id] = name
 
        if isinstance(msg, ToolMessage):
            call_id = getattr(msg, "tool_call_id", None)
            if call_id and tool_name_by_id.get(call_id) == "get_social_media_mentions":
                content = getattr(msg, "content", "")
                if content:
                    outputs.append(content)
 
    return outputs
 
def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        messages = state["messages"]
 
        # Trim messages to prevent context overflow
        messages = trim_messages_for_model(
            messages,
            model_name="claude-sonnet",
            summarize=True
        )
 
        # Capture tool outputs so the analyst can reference them when writing the report
        tool_outputs = _extract_social_tool_outputs(messages)
 
        tool_call_count = state.get("social_media_analyst_tool_call_count", 0)
        called_tools = state.get("social_media_analyst_called_tools", set())
        if not isinstance(called_tools, set):
            called_tools = set(called_tools)
 
        tools = [
            get_social_media_mentions,
        ]
 
        # After 1 tool call, force report generation
        if tool_call_count >= 1:
            context_block = "\n\n".join(tool_outputs[-3:]) if tool_outputs else "No tool results available. Summarize any insights you can."  # noqa: E501
            system_prompt = (
                "You are a social media analyst. You have already gathered data. "
                "Write a comprehensive report NOW using the data from previous tool results. "
                "Do NOT call any more tools. Write the report directly.\n\n"
                f"Use these tool results as your primary evidence:\n{context_block}"
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                ("human", "Write your final analysis report now.")
            ])
            result = (prompt | llm).invoke({"messages": messages})
        else:
            system_message = (
                "You are a social media analyst tasked with analyzing social media posts and public sentiment for a specific company over the past week. "
                "Your objective is to write a comprehensive report detailing your analysis of public sentiment, key themes in social media discussions, and the implications for traders and investors. "
                "Use the get_social_media_mentions(ticker, start_date, end_date) tool to search for social media discussions. "
                "Do not simply state the trends are mixed; provide detailed and fine-grained analysis and insights that may help traders make decisions."
                + ''' Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.'''
            )
 
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful AI assistant, collaborating with other assistants."
                        " Use the provided tools to progress towards answering the question."
                        " If you are unable to fully answer, that's OK; another assistant with different tools"
                        " will help where you left off. Execute what you can to make progress."
                        " You have access to the following tools: {tool_names}.\n{system_message}"
                        "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )
 
            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)
 
            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(messages)
 
        previous_report = state.get("sentiment_report", "")
        report = ""
 
        if hasattr(result, "tool_calls") and result.tool_calls:
            tool_call_count += len(result.tool_calls)
            for tc in result.tool_calls:
                tool_name = None
                if isinstance(tc, dict):
                    tool_name = tc.get("name")
                else:
                    tool_name = getattr(tc, "name", None)
                if tool_name:
                    called_tools.add(tool_name)
 
        if len(result.tool_calls) == 0:
            report = result.content or previous_report
 
        return {
            "messages": [result],
            "sentiment_report": report,
            "social_media_analyst_tool_call_count": tool_call_count,
            "social_media_analyst_called_tools": called_tools,
        }
 
    return social_media_analyst_node