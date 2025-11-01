from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
import time
import json
from tradingagents.agents.utils.agent_utils import get_indicators, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report
from tradingagents.agents.utils.context_limiter import trim_messages_for_model


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        stock_data = state["stock_data"]
        messages = state["messages"]

        # Trim messages to prevent context overflow
        messages = trim_messages_for_model(
            messages,
            model_name="claude-sonnet",
            summarize=False
        )

        tool_call_count = state.get("market_analyst_tool_call_count", 0)
        called_indicators = state.get("market_analyst_called_indicators", set())

        # Update state from the last message
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_count += len(last_message.tool_calls)
            for tc in last_message.tool_calls:
                if tc.get("name") == "get_indicators":
                    args = tc.get("args", {})
                    if "indicator" in args:
                        called_indicators.add(args["indicator"])

        tools = [get_indicators]

        if tool_call_count >= 5 or len(called_indicators) >= 5:
            system_prompt = (
                "You are a market analyst. You have already collected stock data and technical indicators. "
                "Write a comprehensive technical analysis report NOW using the data from previous tool results. "
                "Include price trends, indicator analysis, and a final Market Outlook (Bullish/Bearish/Neutral). "
                "Do NOT call any more tools. Write the report directly."
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="messages"),
                    (
                        "human",
                        "Write your final technical analysis report now using the indicator data you collected. Do NOT call more tools.",
                    ),
                ]
            )
            # Invoke without tool binding to prevent more calls
            result = (prompt | llm).invoke({"messages": messages})
        else:
            # Normal flow with tools
            system_message = (
                "You are a market analyst. You have been provided with the following stock price data:\n\n"
                "{stock_data}\n\n"
                "Your task is to gather additional technical indicators and then write a comprehensive technical analysis report.\n\n"
                "You have already called the following indicators: {called_indicators}\n\n"
                "Available tools:\n"
                "- get_indicators: Get ONE indicator at a time (call separately for each: rsi, macd, close_50_sma, boll, atr)\n\n"
                "Steps:\n"
                "1. Analyze the provided stock price data.\n"
                "2. Call get_indicators for a new indicator that you have not called before.\n"
                "3. After gathering 3-5 indicators, write your technical analysis report.\n\n"
                "RULES:\n"
                "- Do NOT call the same indicator twice.\n"
                "- After 3-5 indicator calls, write your report.\n"
                "- Only cite exact values from tool responses."
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful AI assistant, collaborating with other assistants. "
                        "Use the provided tools to progress towards answering the question. "
                        "If you are unable to fully answer, that's OK; another assistant with different tools "
                        "will help where you left off. Execute what you can to make progress. "
                        "You have access to the following tools: {tool_names}.\n{system_message}\n"
                        "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            prompt = prompt.partial(
                system_message=system_message.format(
                    stock_data=stock_data, called_indicators=", ".join(called_indicators) if called_indicators else "None"
                )
            )

            available_tools = [get_indicators]

            prompt = prompt.partial(tool_names=", ".join([tool.name for tool in available_tools]))
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)

            chain = prompt | llm.bind_tools(available_tools)
            result = chain.invoke(messages)

        # Extract report
        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

            if len(report) > 5000:
                config = get_config()
                summarized_report = summarize_analyst_report(
                    analyst_name="Market Analyst",
                    full_report=report,
                    max_summary_length=2000,
                    llm_config=config
                )
                result = AIMessage(content=summarized_report)
                report = summarized_report

        return {
            "messages": [result],
            "market_report": report,
            "market_analyst_tool_call_count": tool_call_count,
            "market_analyst_called_indicators": called_indicators,
        }

    return market_analyst_node
