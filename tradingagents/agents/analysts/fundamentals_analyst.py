from collections import defaultdict
from typing import List, Dict
 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import time
import json
from tradingagents.agents.utils.agent_utils import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_insider_sentiment,
    get_insider_transactions,
    get_company_info,
)
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.summarizer import summarize_analyst_report
from tradingagents.agents.utils.context_limiter import trim_messages_for_model
 
KEY_FIELDS = {
    "get_company_info": [
        "companyName",
        "exchange",
        "currency",
        "currentPrice",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
        "marketCap",
        "fiscalYearEnd",
        "nextEarningsDate",
    ],
    "get_income_statement": [
        "fiscalDateEnding",
        "reportedCurrency",
        "totalRevenue",
        "grossProfit",
        "operatingIncome",
        "netIncome",
        "dilutedEPS",
    ],
    "get_balance_sheet": [
        "fiscalDateEnding",
        "reportedCurrency",
        "totalAssets",
        "totalLiabilities",
        "totalShareholderEquity",
        "cashAndCashEquivalentsAtCarryingValue",
    ],
    "get_cashflow": [
        "fiscalDateEnding",
        "reportedCurrency",
        "operatingCashflow",
        "capitalExpenditures",
        "cashflowFromInvestment",
        "cashflowFromFinancing",
        "freeCashFlow",
    ],
    "get_fundamentals": [
        "date",
        "peRatio",
        "pbRatio",
        "dividendYield",
        "roe",
        "roa",
    ],
}
 
def _extract_fundamental_tool_outputs(messages: List, allowed_tools) -> Dict[str, List[str]]:
    """Group tool outputs by tool name for fundamental analysis."""
    tool_name_by_id: Dict[str, str] = {}
    outputs: Dict[str, List[str]] = defaultdict(list)
 
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
            tool_name = tool_name_by_id.get(call_id)
            if tool_name in allowed_tools:
                content = getattr(msg, "content", "")
                if content:
                    outputs[tool_name].append(content)
 
    return outputs
 
def _truncate_text(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."
 
def _summarize_tool_entry(
    tool_name: str,
    raw_text: str,
    max_items: int = 5,
    max_len: int = 600,
) -> str:
    """Condense a raw tool output into a compact human-readable summary."""
    cleaned = raw_text.strip()
    if not cleaned:
        return ""
 
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return _truncate_text(cleaned, max_len)
 
    fields = KEY_FIELDS.get(tool_name)
    summary_lines: List[str] = []
 
    if isinstance(parsed, list):
        items = parsed[:max_items]
        for item in items:
            if isinstance(item, dict):
                if fields:
                    parts = [
                        f"{field}: {item[field]}"
                        for field in fields
                        if field in item and item[field] not in (None, "")
                    ]
                else:
                    parts = [
                        f"{k}: {v}" for k, v in list(item.items())[:6]
                    ]
                if parts:
                    summary_lines.append(", ".join(parts))
            else:
                summary_lines.append(str(item))
    elif isinstance(parsed, dict):
        if fields:
            parts = [
                f"{field}: {parsed[field]}"
                for field in fields
                if field in parsed and parsed[field] not in (None, "")
            ]
        else:
            parts = [f"{k}: {v}" for k, v in list(parsed.items())[:8]]
        if parts:
            summary_lines.append(", ".join(parts))
    else:
        summary_lines.append(str(parsed))
 
    summary = " | ".join(summary_lines)
    if summary:
        return _truncate_text(summary, max_len)
    return _truncate_text(cleaned, max_len)
 
def _format_tool_context(tool_outputs: Dict[str, List[str]], max_chars: int = 2400) -> str:
    """Format tool outputs into a compact context block within a char budget."""
    ordered_tools = [
        "get_company_info",
        "get_fundamentals",
        "get_balance_sheet",
        "get_cashflow",
        "get_income_statement",
    ]
 
    def _truncate(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[: limit - 3] + "..."
 
    sections: List[str] = []
    remaining = max_chars
 
    for name in ordered_tools:
        entries = tool_outputs.get(name)
        if not entries or remaining <= 0:
            continue
 
        latest_entry = entries[-1].strip()
        if not latest_entry:
            continue
 
        header = f"{name} output:\n"
        header_len = len(header)
        if header_len >= remaining:
            break
 
        body_limit = remaining - header_len
        body = _summarize_tool_entry(
            name,
            latest_entry,
            max_len=min(body_limit, 600),
        )
        section = header + body
 
        section_len = len(section) + 2  # account for separating newline
        if section_len > remaining:
            break
 
        sections.append(section)
        remaining -= section_len
 
    if not sections:
        return "No financial tool outputs captured yet. Summarize available insights."
 
    return "\n\n".join(sections)
 
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
        if not isinstance(called_tools, set):
            called_tools = set(called_tools)
 
        tools = [
            get_company_info,
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]
 
        allowed_tool_names = {tool.name for tool in tools}
        tool_outputs = _extract_fundamental_tool_outputs(messages, allowed_tool_names)
 
        # After 4 tool calls, force report generation
        if tool_call_count >= 4:
            context_block = _format_tool_context(tool_outputs)
 
            system_prompt = (
                "You are a fundamental analyst. You have already gathered data for {ticker} as of {current_date}. "
                "Write a comprehensive analytical report NOW using the data from previous tool results. "
                "Do NOT call any more tools. Write the report directly.\n\n"
                f"Use these tool results as your primary evidence:\n{context_block}"
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Write your final analysis report now."),
            ])
            prompt = prompt.partial(current_date=current_date, ticker=ticker)
            result = (prompt | llm).invoke({})
        else:
            system_message = (
                "You are a fundamental analyst. Call the available tools to gather data, then write a comprehensive analytical report. "
                "DO NOT explain what you're about to do or narrate your process - just use the tools and report your analysis. "
                "\n\n"
                "You have already called the following tools: {called_tools}\n\n"
                "Available tools: `get_company_info`, `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`. "
                "Call get_company_info first for context (fiscal year, earnings dates, price ranges), then use other tools to gather comprehensive financial data. "
                "When calling financial statements, prefer `freq=\"annual\"` and focus on the last 5 fiscal years unless the query requires quarterly granularity. "
                "If a tool returns a long JSON payload, summarize the key figures (revenue, margins, cash flow, debt) and keep the analysis concise. "
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
 
        previous_report = state.get("fundamentals_report", "")
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