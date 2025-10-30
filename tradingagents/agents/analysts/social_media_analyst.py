from langchain_core.messages import AIMessage
from tradingagents.agents.utils.agent_utils import get_news, get_company_info, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.analysts.dspy_prompt_optimizer import AnalystModule
from dspy.predict.langchain import LangChain
import dspy

def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        messages = ensure_message_alternation(state["messages"])

        # Convert messages to a string format for DSPy
        message_string = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        tools = [
            get_news,
            get_company_info,
        ]

        system_message = (
            "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Use the get_news(query, start_date, end_date) tool to search for company-specific news and social media discussions. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Use the `get_company_info` tool to fact-check company details like the fiscal year and to prioritize your analysis around key dates like earnings announcements."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.""",
        )

        # Configure DSPy with the LLM
        dspy.settings.configure(lm=LangChain(model=llm.model_name))

        # Create and run the DSPy module
        analyst_module = AnalystModule(tools=tools)
        result = analyst_module(
            system_message=system_message,
            tool_names=", ".join([tool.name for tool in tools]),
            current_date=current_date,
            ticker=ticker,
            messages=message_string
        )

        report = result.report

        return {
            "messages": [AIMessage(content=report)],
            "sentiment_report": report,
        }

    return social_media_analyst_node
