import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd

# Load environment variables
load_dotenv()

# Check credentials
if not os.getenv("DATABRICKS_TOKEN") or not os.getenv("DATABRICKS_BASE_URL"):
    print("ERROR: Missing DATABRICKS_TOKEN or DATABRICKS_BASE_URL in .env file")
    exit(1)

# Configure
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"

if config["databricks_base_url"] and not config["databricks_base_url"].endswith("/serving-endpoints"):
    config["databricks_base_url"] = config["databricks_base_url"].rstrip("/") + "/serving-endpoints"

print("Configuration:")
print(f"  LLM Provider: {config['llm_provider']}")
print(f"  Deep Think: {config['deep_think_llm']}")
print(f"  Quick Think: {config['quick_think_llm']}")
print()

# Initialize
print("Initializing TradingAgentsGraph...")
ta = TradingAgentsGraph(debug=False, config=config)  # debug=False to avoid verbose output
print("✓ Initialized!\n")

# Parameters
symbol = "NVDA"
trade_date = "2025-10-27"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create output directory
output_dir = Path("analysis_results") / symbol
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{symbol}_{timestamp}.md"
chart_file = output_dir / f"{symbol}_{timestamp}_chart.png"

print(f"Running analysis for {symbol} on {trade_date}...")
print(f"Output: {output_file}\n")

# Run analysis (capture stdout to suppress debug logs)
old_stdout = sys.stdout
sys.stdout = io.StringIO()  # Suppress debug output

try:
    final_state, decision = ta.propagate(symbol, trade_date)
finally:
    sys.stdout = old_stdout  # Restore stdout

print("✓ Analysis complete!\n")

# Extract reports from final state
market_report = final_state.get("market_report", "No market report available")
fundamentals_report = final_state.get("fundamentals_report", "No fundamentals report available")
news_report = final_state.get("news_report", "No news report available")
sentiment_report = final_state.get("sentiment_report", "No sentiment report available")
final_decision = final_state.get("final_trade_decision", decision)

# Create price chart
print("Creating price chart...")
try:
    import yfinance as yf

    # Get 6 months of data
    end_date = datetime.strptime(trade_date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=180)

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=trade_date)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['Close'], linewidth=2, color='#2E86AB')
        ax.fill_between(df.index, df['Close'], alpha=0.3, color='#2E86AB')

        ax.set_title(f'{symbol} Stock Price - Last 6 Months', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price ($)', fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add current price annotation
        current_price = df['Close'].iloc[-1]
        ax.annotate(f'${current_price:.2f}',
                   xy=(df.index[-1], current_price),
                   xytext=(10, 10), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                   fontsize=11, fontweight='bold')

        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✓ Chart saved: {chart_file}\n")
        chart_created = True
    else:
        print("⚠ Could not fetch price data for chart\n")
        chart_created = False
except Exception as e:
    print(f"⚠ Chart creation failed: {e}\n")
    chart_created = False

# Write clean markdown report
print("Writing markdown report...")
with open(output_file, 'w') as f:
    f.write(f"# Trading Analysis Report\n\n")
    f.write(f"**Symbol:** {symbol}\n")
    f.write(f"**Trade Date:** {trade_date}\n")
    f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"**LLM Provider:** {config['llm_provider']}\n")
    f.write(f"**Models:** Deep Think: {config['deep_think_llm']}, Quick Think: {config['quick_think_llm']}\n\n")

    if chart_created:
        f.write(f"## Price Chart\n\n")
        f.write(f"![{symbol} Price Chart](./{chart_file.name})\n\n")

    f.write(f"---\n\n")

    f.write(f"## Market Analysis\n\n")
    f.write(market_report)
    f.write(f"\n\n---\n\n")

    f.write(f"## Fundamental Analysis\n\n")
    f.write(fundamentals_report)
    f.write(f"\n\n---\n\n")

    f.write(f"## News Analysis\n\n")
    f.write(news_report)
    f.write(f"\n\n---\n\n")

    f.write(f"## Sentiment Analysis\n\n")
    f.write(sentiment_report)
    f.write(f"\n\n---\n\n")

    f.write(f"## Final Trading Decision\n\n")
    f.write(f"**{final_decision}**\n\n")

print(f"✓ Report saved: {output_file}\n")

# Preview
print("="*80)
print("FINAL DECISION PREVIEW")
print("="*80)
print(final_decision)
print("="*80)
