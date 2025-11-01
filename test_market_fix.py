"""Quick test to verify market analyst doesn't loop infinitely"""
import os
import sys
from datetime import datetime
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Setup config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = os.getenv("LLM_PROVIDER", config.get("llm_provider", "databricks"))
config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", config.get("deep_think_llm", "databricks-claude-sonnet-4-5"))
config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", config.get("quick_think_llm", "llama_v3_3_70b_instruct_pro"))

print("="*80)
print("TESTING MARKET ANALYST FIX")
print("="*80)
print(f"Provider: {config['llm_provider']}")
print(f"Deep think: {config['deep_think_llm']}")
print()

# Initialize graph
print("Initializing TradingAgentsGraph...")
ta = TradingAgentsGraph(
    selected_analysts=["market"],  # Only test market analyst
    debug=True,
    config=config,
    enable_rate_limiting=False
)

# Run analysis
symbol = "MSFT"
trade_date = "2025-10-31"

print(f"\nRunning market analysis for {symbol} on {trade_date}...")
print("="*80)

try:
    final_state, decision = ta.propagate(symbol, trade_date)

    print("\n" + "="*80)
    print("✓ SUCCESS - Analysis completed without hitting recursion limit!")
    print("="*80)

    market_report = final_state.get('market_report', '')
    if market_report:
        print(f"\nMarket report length: {len(market_report)} chars")
        print(f"\nMarket report preview (first 500 chars):")
        print("-"*80)
        print(market_report[:500])
        print("-"*80)
    else:
        print("\n⚠ WARNING: Market report is empty!")

except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
