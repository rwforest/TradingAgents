from langchain_core.messages import AIMessage
from tradingagents.agents.utils.agent_utils import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_company_info, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report
from tradingagents.agents.analysts.dspy_prompt_optimizer import AnalystModule
from tradingagents.agents.utils.safe_invoke import safe_invoke_with_retry
from dspy.predict.langchain import LangChain
import dspy

def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        messages = ensure_message_alternation(state["messages"])

        # Convert messages to a string format for DSPy
        message_string = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_company_info,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Use the `get_company_info` tool to fact-check company details like the fiscal year and to prioritize your analysis around key dates like earnings announcements."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements.",
        )

        # Configure DSPy with the LLM
        dspy.settings.configure(lm=LangChain(model=llm.model_name))

        # Create the DSPy module
        analyst_module = AnalystModule(tools=tools)

        # Use safe invoke with automatic retry on context overflow
        config = get_config()
        result = safe_invoke_with_retry(
            analyst_module,
            max_retries=3,
            llm_config=config,
            system_message=system_message,
            tool_names=", ".join([tool.name for tool in tools]),
            current_date=current_date,
            ticker=ticker,
            messages=message_string
        )

        report = result.report

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
            report = summarized_report

        return {
            "messages": [AIMessage(content=report)],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
