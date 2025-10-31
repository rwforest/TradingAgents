from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import time
import json
from tradingagents.agents.utils.agent_utils import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_insider_sentiment, get_insider_transactions, get_company_info, ensure_message_alternation
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report, safe_invoke_with_retry


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Fetch ALL fundamental data upfront - fundamentals are facts, not iterative
        print(f"[Fundamentals Analyst] Fetching all fundamental data for {ticker}...")

        try:
            company_info = get_company_info(ticker)
        except Exception as e:
            company_info = f"Error fetching company info: {e}"

        try:
            fundamentals = get_fundamentals(ticker)
        except Exception as e:
            fundamentals = f"Error fetching fundamentals: {e}"

        try:
            balance_sheet = get_balance_sheet(ticker)
        except Exception as e:
            balance_sheet = f"Error fetching balance sheet: {e}"

        try:
            income_statement = get_income_statement(ticker)
        except Exception as e:
            income_statement = f"Error fetching income statement: {e}"

        try:
            cashflow = get_cashflow(ticker)
        except Exception as e:
            cashflow = f"Error fetching cashflow: {e}"

        # Create comprehensive data package
        fundamental_data = f"""# Fundamental Data for {ticker}

## Company Information and Fact-Checking Data
{company_info}

## Comprehensive Fundamentals
{fundamentals}

## Balance Sheet
{balance_sheet}

## Income Statement
{income_statement}

## Cash Flow Statement
{cashflow}
"""

        # Now ask LLM to analyze this data WITHOUT tools - use simple message construction
        from langchain_core.messages import HumanMessage, SystemMessage

        system_message = (
            f"You are a financial analyst tasked with analyzing fundamental information about a company. "
            f"All the fundamental data has been provided below. Your job is to write a comprehensive report analyzing this data. "
            f"Focus on: financial health, growth trends, profitability, valuation metrics, and key risks/opportunities. "
            f"Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
            f"Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.\n\n"
            f"For your reference, the current date is {current_date}. The company we want to look at is {ticker}"
        )

        user_message_content = f"Here is all the fundamental data for {ticker}:\n\n{fundamental_data}\n\nPlease provide a comprehensive analysis."

        # Ensure messages properly alternate between user and assistant roles
        messages = ensure_message_alternation(state["messages"])

        # Build the final message list
        final_messages = [SystemMessage(content=system_message)] + messages + [HumanMessage(content=user_message_content)]

        # Invoke LLM without tools - just analysis
        result = llm.invoke(final_messages)

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
            result = AIMessage(content=summarized_report)
        else:
            result = AIMessage(content=report)

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node