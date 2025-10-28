"""
Test rate limiting functionality with Databricks models
"""
import os
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import time

load_dotenv()

print("=" * 80)
print("Testing Rate Limiting for Databricks Models")
print("=" * 80)
print()

# Configuration
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"

print("Test Configuration:")
print(f"  Provider: {config['llm_provider']}")
print(f"  Deep Think: {config['deep_think_llm']}")
print(f"  Quick Think: {config['quick_think_llm']}")
print()

print("=" * 80)
print("Test 1: Rate Limiting ENABLED (default)")
print("=" * 80)
print()

start_time = time.time()

ta_with_limiting = TradingAgentsGraph(
    debug=True,
    config=config,
    selected_analysts=["market"],  # Just market to keep it fast
    enable_rate_limiting=True  # ENABLED
)

print("\nRunning quick analysis...")
_, decision1 = ta_with_limiting.propagate("AAPL", "2025-10-27")

elapsed_with_limiting = time.time() - start_time

print(f"\n✓ Completed with rate limiting in {elapsed_with_limiting:.1f}s")
print(f"Decision preview: {decision1[:100]}...")
print()

print("=" * 80)
print("Test 2: Rate Limiting DISABLED")
print("=" * 80)
print()

start_time = time.time()

ta_without_limiting = TradingAgentsGraph(
    debug=False,  # Less verbose
    config=config,
    selected_analysts=["market"],
    enable_rate_limiting=False  # DISABLED
)

print("\nRunning quick analysis without rate limiting...")
_, decision2 = ta_without_limiting.propagate("MSFT", "2025-10-27")

elapsed_without_limiting = time.time() - start_time

print(f"\n✓ Completed without rate limiting in {elapsed_without_limiting:.1f}s")
print(f"Decision preview: {decision2[:100]}...")
print()

print("=" * 80)
print("Summary")
print("=" * 80)
print()
print(f"With rate limiting:    {elapsed_with_limiting:.1f}s")
print(f"Without rate limiting: {elapsed_without_limiting:.1f}s")
print(f"Difference:            {elapsed_with_limiting - elapsed_without_limiting:.1f}s")
print()

if elapsed_with_limiting > elapsed_without_limiting:
    overhead = elapsed_with_limiting - elapsed_without_limiting
    print(f"Rate limiting added ~{overhead:.1f}s of delays")
    print("This prevents hitting Databricks rate limits (150 RPM, 300K TPM)")
else:
    print("No significant overhead from rate limiting")

print()
print("=" * 80)
print("Rate Limit Details")
print("=" * 80)
print()
print("Databricks Foundation Model API Limits:")
print("  - Pay-per-token endpoints:")
print("    * 150 requests per minute (RPM)")
print("    * 300,000 tokens per minute (TPM)")
print()
print("Rate limiting strategy:")
print("  - Minimum 400ms delay between calls (~2.5 calls/second)")
print("  - Tracks both request count and token usage")
print("  - Automatically waits if approaching limits")
print("  - Prevents 429 'Too Many Requests' errors")
print()
print("To disable rate limiting:")
print("  ta = TradingAgentsGraph(..., enable_rate_limiting=False)")
print()
print("=" * 80)
