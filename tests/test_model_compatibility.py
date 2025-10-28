"""
Comprehensive test to check model compatibility with TradingAgents workflow
Tests both tool calling and decision-making scenarios
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Test configuration
base_url = os.getenv("DATABRICKS_BASE_URL")
if base_url and not base_url.endswith("/serving-endpoints"):
    base_url = base_url.rstrip("/") + "/serving-endpoints"

token = os.getenv("DATABRICKS_TOKEN")

# Define test tools (similar to TradingAgents)
@tool
def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """Get historical stock price data.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    return f"Stock data for {symbol} from {start_date} to {end_date}"

@tool
def get_indicators(symbol: str, indicators: list) -> str:
    """Get technical indicators for a stock.

    Args:
        symbol: Stock ticker symbol
        indicators: List of indicators (e.g., ['RSI', 'MACD'])
    """
    return f"Indicators for {symbol}: {', '.join(indicators)}"

# Models to test
test_configs = [
    {
        "name": "Claude for Both",
        "quick_think": "databricks-claude-sonnet-4-5",
        "deep_think": "databricks-claude-sonnet-4-5",
    },
    {
        "name": "OSS for Deep, Claude for Quick",
        "quick_think": "databricks-claude-sonnet-4-5",
        "deep_think": "databricks-gpt-oss-120b",
    },
    {
        "name": "OSS for Both (Test Only)",
        "quick_think": "databricks-gpt-oss-120b",
        "deep_think": "databricks-gpt-oss-120b",
    },
]

print("=" * 80)
print("Testing Model Compatibility with TradingAgents Workflow")
print("=" * 80)

for config in test_configs:
    print(f"\n{'=' * 80}")
    print(f"Configuration: {config['name']}")
    print(f"  Quick Think: {config['quick_think']}")
    print(f"  Deep Think: {config['deep_think']}")
    print(f"{'=' * 80}")

    # Test 1: Quick Think with Tools (Analyst scenario)
    print("\n[TEST 1] Quick Think with Tools (Analyst Role)")
    print("-" * 80)
    try:
        quick_llm = ChatOpenAI(
            model=config['quick_think'],
            api_key=token,
            base_url=base_url,
        )

        quick_llm_with_tools = quick_llm.bind_tools([get_stock_data, get_indicators])

        analyst_prompt = """You are a Market Analyst. Analyze NVDA stock for 2025-10-27.
Use the available tools to gather stock data and technical indicators."""

        print(f"Prompt: {analyst_prompt[:100]}...")
        response = quick_llm_with_tools.invoke(analyst_prompt)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"✅ Successfully generated {len(response.tool_calls)} tool calls")
            for tc in response.tool_calls:
                print(f"   - {tc.get('name', 'unknown')}: {tc.get('args', {})}")
        else:
            print(f"⚠️  No tool calls, but no error")
            print(f"   Response: {response.content[:100]}...")

    except Exception as e:
        print(f"❌ Error in Quick Think with Tools:")
        print(f"   {type(e).__name__}: {str(e)[:200]}")
        if "<|channel|>" in str(e):
            print("   ⚠️  Detected channel token issue!")

    # Test 2: Deep Think without Tools (Decision-making scenario)
    print("\n[TEST 2] Deep Think without Tools (Decision Maker Role)")
    print("-" * 80)
    try:
        deep_llm = ChatOpenAI(
            model=config['deep_think'],
            api_key=token,
            base_url=base_url,
        )

        decision_prompt = """You are the Investment Judge. Based on the following analysis:

Bull Argument: NVDA shows strong growth potential in AI sector.
Bear Argument: NVDA is overvalued with high P/E ratio.

Make a final investment decision: BUY, HOLD, or SELL. Provide your reasoning."""

        print(f"Prompt: {decision_prompt[:100]}...")
        response = deep_llm.invoke(decision_prompt)

        if response.content:
            print(f"✅ Successfully generated decision")
            print(f"   Preview: {response.content[:150]}...")
        else:
            print(f"⚠️  Empty response")

    except Exception as e:
        print(f"❌ Error in Deep Think without Tools:")
        print(f"   {type(e).__name__}: {str(e)[:200]}")

    # Test 3: Context Size Test
    print("\n[TEST 3] Context Size Test (Large Input)")
    print("-" * 80)
    try:
        # Create a large context (similar to what happens in TradingAgents)
        large_context = "Stock data:\n" + ("Date,Open,High,Low,Close,Volume\n" + "2025-01-01,150,155,148,152,1000000\n") * 50
        large_context += "\nNews:\n" + ("Article about AI and semiconductors. " * 100)

        prompt = f"Analyze this data and provide insights:\n\n{large_context}"

        response = quick_llm.invoke(prompt)
        print(f"✅ Successfully handled large context ({len(large_context)} chars)")

    except Exception as e:
        error_msg = str(e)
        if "too long" in error_msg.lower():
            print(f"❌ Context length error:")
            print(f"   Input size: {len(large_context)} characters")
            print(f"   Error: {error_msg[:150]}")
        else:
            print(f"❌ Unexpected error: {type(e).__name__}")

print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)
print("\nRecommendations:")
print("-" * 80)
print("✅ Best for TradingAgents:")
print("   quick_think_llm: databricks-claude-sonnet-4-5 (needs tools)")
print("   deep_think_llm: databricks-claude-sonnet-4-5 or databricks-gpt-oss-120b")
print()
print("⚠️  To avoid context length errors:")
print("   - Use selected_analysts=['market', 'news'] (skip 'fundamentals')")
print("   - Set max_debate_rounds=1 and max_risk_discuss_rounds=1")
print("-" * 80)
