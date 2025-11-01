from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import time
import json
from tradingagents.agents.utils.agent_utils import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_insider_sentiment, get_insider_transactions, get_company_info
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report
from tradingagents.agents.utils.context_limiter import trim_messages_for_model


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        messages = state["messages"]

        # Trim messages to prevent context overflow
        messages = trim_messages_for_model(
            messages,
            model_name="claude-sonnet",
            summarize=False
        )

        tool_call_count = state.get("fundamentals_analyst_tool_call_count", 0)
        called_tools = state.get("fundamentals_analyst_called_tools", set())

        # Update state from the last message
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_count += len(last_message.tool_calls)
            for tc in last_message.tool_calls:
                called_tools.add(tc.get("name"))

        tools = [
            get_company_info,
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        # After 4 tool calls, force report generation
        if tool_call_count >= 4:
            system_prompt = (
                "You are a fundamental analyst. You have already gathered data using the available tools. "
                "Write a comprehensive analytical report NOW using the data from previous tool results. "
                "Do NOT call any more tools. Write the report directly."
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                ("human", "Write your final analysis report now.")
            ])
            result = (prompt | llm).invoke({"messages": messages})
        else:
            system_message = (
                "You are a fundamental analyst. Call the available tools to gather data, then write a comprehensive analytical report. "
                "DO NOT explain what you're about to do or narrate your process - just use the tools and report your analysis. "
                "\n\n"
                "You have already called the following tools: {called_tools}\n\n"
                "Available tools: `get_company_info`, `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`. "
                "Call get_company_info first for context (fiscal year, earnings dates, price ranges), then use other tools to gather comprehensive financial data. "
                "\n\n"
                "After gathering data via tools, write your report with: "
                "- Company profile and recent performance "
                "- Financial health analysis (balance sheet strength, cash flow, profitability) "
                "- Growth trends and year-over-year comparisons "
                "- Key metrics and ratios with actual values "
                "- Detailed, specific insights (not generic statements like 'trends are mixed') "
                "- A summary table at the end organizing key metrics "
                "\n\n"
                "CRITICAL RULE: You MUST ONLY cite specific numbers, metrics, and data points that are EXPLICITLY STATED in the data returned by the tools. DO NOT make up, estimate, round, or infer numerical values. Report exact values from tool responses."
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful AI assistant, collaborating with other assistants."
                        " Use the provided tools to progress towards answering the question."
                        " If you are unable to fully answer, that's OK; another assistant with different tools"
                        " will help where you left off. Execute what you can to make progress."
                        " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                        " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                        " You have access to the following tools: {tool_names}.\n{system_message}"
                        " For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            prompt = prompt.partial(system_message=system_message.format(called_tools=", ".join(called_tools) if called_tools else "None"))
            prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)

            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(messages)

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

            if len(report) > 5000:
                config = get_config()
                summarized_report = summarize_analyst_report(
                    analyst_name="Fundamentals Analyst",
                    full_report=report,
                    max_summary_length=2000,
                    llm_config=config
                )
                # Replace the result content with summarized version
                result = AIMessage(content=summarized_report)

        return {
            "messages": [result],
            "fundamentals_report": report,
            "fundamentals_analyst_tool_call_count": tool_call_count,
            "fundamentals_analyst_called_tools": called_tools,
        }

    return fundamentals_analyst_node