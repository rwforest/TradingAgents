from langchain_core.messages import AIMessage
from tradingagents.agents.utils.agent_utils import get_news, get_global_news, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.context_limiter import trim_messages_for_model
from tradingagents.agents.analysts.dspy_prompt_optimizer import AnalystModule
from dspy.predict.langchain import LangChain
import dspy

def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        messages = trim_messages_for_model(
            state["messages"],
            model_name="claude-sonnet",
            summarize=True
        )
        messages = ensure_message_alternation(messages)

        # Convert messages to a string format for DSPy
        message_string = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
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
            "news_report": report,
        }

    return news_analyst_node
