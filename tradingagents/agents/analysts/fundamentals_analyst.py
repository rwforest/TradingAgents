from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import time
import json
from tradingagents.agents.utils.agent_utils import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_insider_sentiment, get_insider_transactions
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report, safe_invoke_with_retry


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Filter messages to only keep valid tool call/response pairs
        # This prevents "tool message without tool_calls" errors
        messages = []
        raw_messages = state["messages"]

        for i, msg in enumerate(raw_messages):
            # If it's a tool message, check if previous message has tool_calls
            if isinstance(msg, ToolMessage):
                if i > 0 and hasattr(raw_messages[i-1], 'tool_calls') and raw_messages[i-1].tool_calls:
                    messages.append(msg)
                # else: skip orphaned tool message
            else:
                messages.append(msg)

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements.",
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
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        # Use safe invoke with automatic retry on context overflow
        config = get_config()
        result = safe_invoke_with_retry(chain, messages, max_retries=3, llm_config=config)

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

            # Summarize if report is too long (>5000 chars)
            if len(report) > 5000:
                print(f"[Fundamentals Analyst] Report is {len(report)} chars, summarizing...")
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
        }

    return fundamentals_analyst_node