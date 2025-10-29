import os
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

load_dotenv()

# Configure
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"

if not config["databricks_base_url"].endswith("/serving-endpoints"):
    config["databricks_base_url"] = config["databricks_base_url"].rstrip("/") + "/serving-endpoints"

print("Initializing with rate limiting enabled...")
ta = TradingAgentsGraph(debug=True, config=config, enable_rate_limiting=True)
print("✓ Initialized successfully!\n")

print("Running quick test for AAPL...")
final_state, decision = ta.propagate("AAPL", "2025-10-28")

print("\n" + "="*80)
print("FINAL DECISION:")
print("="*80)
print(decision)
print("="*80)
