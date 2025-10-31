from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_news, get_global_news, get_company_info, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.context_limiter import trim_messages_for_model


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # First trim messages to prevent context overflow
        messages = trim_messages_for_model(
            state["messages"],
            model_name="claude-sonnet",
            summarize=False
        )

        # Then ensure messages properly alternate between user and assistant roles
        # This prevents "Chat message input roles must alternate" errors
        messages = ensure_message_alternation(messages)

        tools = [
            get_company_info,
            get_news,
            get_global_news,
        ]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_company_info(ticker) to get fundamental context like fiscal year end, earnings dates, current price, and 52-week high/low; get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + """

CRITICAL RULE: You MUST ONLY cite specific facts, events, dates, and data points that are EXPLICITLY STATED in the news articles you fetch. DO NOT make up, estimate, assume, or infer information that is not directly mentioned in the retrieved news. If you don't have specific information from news articles (e.g., exact earnings dates, specific performance metrics), do not make claims about it - instead describe what the news articles actually discuss.

TIMELINE SYNTHESIS: When analyzing news, pay attention to timing and tense:
- If news articles mention "earnings beat" or "Q1 results released" or "reported revenue of X", earnings ALREADY HAPPENED (use past tense)
- If articles say "expected to report" or "analysts anticipate" or "upcoming earnings", earnings HAVE NOT HAPPENED YET (use future tense)
- Cross-reference with get_company_info to verify earnings dates if available
- Compare article publication dates with the current date ({current_date}) and earnings dates to determine correct timing
- Be precise: don't say "expected to release" when articles clearly discuss already-released results

IMPORTANT: When discussing company earnings and fiscal calendars:
- Many companies use fiscal years that differ from calendar years
- For example, Microsoft's fiscal year ends in June, so:
  * FY26 Q1 = July-September 2025 (calendar Q3 2025)
  * FY26 Q2 = October-December 2025 (calendar Q4 2025)
- Always check the company's fiscal calendar before making assumptions about earnings timing
- Be explicit about whether you're referring to fiscal quarters or calendar quarters
- When you see earnings scheduled for a specific date, determine which fiscal quarter it represents based on the company's fiscal year"""
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
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node