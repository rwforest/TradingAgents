import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Create a custom class to capture stdout
class OutputCapture:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log_file = open(filename, 'w')

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()
        sys.stdout = self.terminal

# Load environment variables from .env file
load_dotenv()

# Check if Databricks credentials are set
if not os.getenv("DATABRICKS_TOKEN"):
    print("ERROR: DATABRICKS_TOKEN environment variable is not set")
    print("Please set it with: export DATABRICKS_TOKEN='your-token-here'")
    exit(1)

if not os.getenv("DATABRICKS_BASE_URL"):
    print("ERROR: DATABRICKS_BASE_URL environment variable is not set")
    print("Please set it with: export DATABRICKS_BASE_URL='your-databricks-url'")
    exit(1)

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"  # Specify your Databricks model name here
config["quick_think_llm"] = "databricks-claude-sonnet-4-5" # And here

# Fix the base URL to include /serving-endpoints
if config["databricks_base_url"] and not config["databricks_base_url"].endswith("/serving-endpoints"):
    config["databricks_base_url"] = config["databricks_base_url"].rstrip("/") + "/serving-endpoints"

print("Configuration:")
print(f"  LLM Provider: {config['llm_provider']}")
print(f"  Deep Think Model: {config['deep_think_llm']}")
print(f"  Quick Think Model: {config['quick_think_llm']}")
print(f"  Databricks Base URL: {config['databricks_base_url']}")
print(f"  Databricks Token: {'*' * 20 if config['databricks_token'] else 'NOT SET'}")
print()

# Initialize with custom config
print("Initializing TradingAgentsGraph...")
ta = TradingAgentsGraph(debug=True, config=config)
print("Initialization successful!")
print()

# Set up parameters
symbol = "NVDA"
trade_date = "2025-10-27"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create output directory structure: analysis_results/{symbol}/
output_dir = Path("analysis_results") / symbol
output_dir.mkdir(parents=True, exist_ok=True)

# Create markdown filename: {symbol}_{timestamp}.md
output_file = output_dir / f"{symbol}_{timestamp}.md"

# Start capturing output
print(f"\nSaving output to: {output_file}")
print("="*80)

capture = OutputCapture(output_file)
sys.stdout = capture

try:
    # Write markdown header
    print(f"# Trading Analysis Report")
    print(f"\n**Symbol:** {symbol}")
    print(f"**Trade Date:** {trade_date}")
    print(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"**LLM Provider:** {config['llm_provider']}")
    print(f"**Model:** {config['quick_think_llm']}")
    print("\n" + "="*80 + "\n")

    # Run propagation
    print(f"## Running Analysis for {symbol} on {trade_date}")
    print("\n")

    _, decision = ta.propagate(symbol, trade_date)

    print("\n" + "="*80)
    print("\n## Final Trading Decision\n")
    print(decision)
    print("\n" + "="*80)

finally:
    # Restore stdout
    capture.close()

print(f"\n✓ Analysis complete! Results saved to: {output_file}")
print(f"\nFinal Decision Preview:")
print("-" * 80)
print(decision)
print("-" * 80)
