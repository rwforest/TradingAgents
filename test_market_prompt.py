"""Test the exact market analyst prompt to see if it produces structured tool calls"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

# Mock tools
@tool
def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """Get stock price data for a symbol between start and end dates."""
    return "Stock data CSV"

@tool
def get_indicators(csv_data: str, indicators: list) -> str:
    """Calculate technical indicators from stock data."""
    return "Indicator values"

# Setup Databricks LLM
base_url = os.getenv("DATABRICKS_BASE_URL")
if base_url and not base_url.endswith("/serving-endpoints"):
    base_url = base_url.rstrip("/") + "/serving-endpoints"

llm = ChatOpenAI(
    model="databricks-claude-sonnet-4-5",
    api_key=os.getenv("DATABRICKS_TOKEN"),
    base_url=base_url,
)

tools = [get_stock_data, get_indicators]
llm_with_tools = llm.bind_tools(tools)

# The NEW simplified system message
system_message = """You are a market analyst. Use tools to gather data, then write your analysis.

Available tools:
- get_stock_data: Retrieves price data for a ticker symbol
- get_indicators: Calculates technical indicators (rsi, macd, macds, macdh, close_50_sma, close_200_sma, close_10_ema, boll, boll_ub, boll_lb, atr, vwma)

Instructions:
1. Call get_stock_data first to retrieve CSV data
2. Call get_indicators with CSV and a list of 5-8 complementary indicators
3. Write a detailed technical analysis report with specific values from tool outputs
4. Include a markdown table summary at the end

CRITICAL RULE: Only cite exact values from tool responses. Do not estimate or round numbers.

For your reference, the current date is 2025-10-31. The company we want to look at is MSFT"""

# User message
user_message = "Analyze the market conditions for MSFT stock. Focus on technical indicators and price trends."

print("="*80)
print("TESTING MARKET ANALYST PROMPT")
print("="*80)
print(f"\nModel: databricks-claude-sonnet-4-5")
print(f"Tools bound: {[t.name for t in tools]}")

messages = [
    SystemMessage(content=system_message),
    HumanMessage(content=user_message)
]

print("\nInvoking model...")
result = llm_with_tools.invoke(messages)

print(f"\n{'='*80}")
print("RESULT")
print(f"{'='*80}")
print(f"Type: {type(result)}")
print(f"Tool calls: {len(result.tool_calls)}")
print(f"Content length: {len(result.content) if result.content else 0}")

if result.tool_calls:
    print("\n✓ SUCCESS: Model made structured tool calls!")
    for i, tc in enumerate(result.tool_calls):
        print(f"\nTool call {i+1}:")
        print(f"  Name: {tc['name']}")
        print(f"  Args: {tc['args']}")
else:
    print("\n✗ FAILURE: No structured tool calls")
    print(f"\nContent (first 1000 chars):")
    print("-"*80)
    content_preview = result.content[:1000] if result.content else "No content"
    print(content_preview)
    print("-"*80)

    if "<function=" in result.content:
        print("\n⚠ WARNING: Model outputted pseudo-XML tool syntax!")
    elif "get_stock_data" in result.content[:500] or "get_indicators" in result.content[:500]:
        print("\n⚠ WARNING: Model mentioned tools in text but didn't call them!")
