"""
Run TradingAgents analysis with full logging to logs/ folder.
Logs are saved with timestamps for easy tracking.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import md_to_pdf

# Load .env BEFORE importing config so environment variables are available
load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Create logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"analysis_{timestamp}.log"

# Redirect stdout and stderr to log file AND console
class TeeOutput:
    def __init__(self, *files):
        self.files = files
    
    def write(self, message):
        for f in self.files:
            f.write(message)
            f.flush()
    
    def flush(self):
        for f in self.files:
            f.flush()

# Open log file
log_handle = open(log_file, 'w')
tee = TeeOutput(sys.stdout, log_handle)
sys.stdout = tee
sys.stderr = tee

try:
    ######## Main Analysis ########
    # Analyze a stock
    symbols = ["INTC"]
    # "AAPL", "MSFT", "NVDA", 
    trade_date = datetime.today().strftime('%Y-%m-%d')

    # Configure
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "databricks"
    config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
    config["quick_think_llm"] = "llama_v3_3_70b_instruct_pro"  # Use Claude for both

    # Fix base URL - check if it's set
    if config.get("databricks_base_url") and not config["databricks_base_url"].endswith("/serving-endpoints"):
        config["databricks_base_url"] = config["databricks_base_url"].rstrip("/") + "/serving-endpoints"
    
    print(f"Log file: {log_file}")
    print("="*80)
    print(f"Analysis started at {datetime.now()}")
    print("="*80)
    print()
    
    print("Initializing TradingAgentsGraph...")
    ta = TradingAgentsGraph(debug=True, config=config, enable_rate_limiting=False)
    print("✓ Initialized successfully!\n")
        
    for symbol in symbols:
        print(f"Running analysis for {symbol} on {trade_date}...")
        print("="*80)
        print()
        
        final_state, decision = ta.propagate(symbol, trade_date)

        print()
        print("="*80)
        print("FINAL DECISION:")
        print("="*80)
        print(decision)
        print("="*80)
        print()
        print(f"Analysis completed at {datetime.now()}")
        print(f"Full log saved to: {log_file}")

        # Create output directories
        output_dir_base = Path("analysis_results") / symbol
        output_dir_md = output_dir_base / "md"
        output_dir_pdf = output_dir_base / "pdf"
        output_dir_png = output_dir_base / "png"
        output_dir_md.mkdir(parents=True, exist_ok=True)
        output_dir_pdf.mkdir(parents=True, exist_ok=True)
        output_dir_png.mkdir(parents=True, exist_ok=True)

        # File paths
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file_md = output_dir_md / f"{symbol}_{timestamp_str}.md"
        report_file_pdf = output_dir_pdf / f"{symbol}_{timestamp_str}.pdf"
        chart_file = output_dir_png / f"{symbol}_{timestamp_str}_chart.png"

        chart_created = False
        try:
            print("\nCreating price chart...")
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
                
                current_price = df['Close'].iloc[-1]
                ax.annotate(f'${current_price:.2f}',
                           xy=(df.index[-1], current_price),
                           xytext=(10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                           fontsize=11, fontweight='bold')
                
                plt.tight_layout()
                plt.savefig(chart_file, dpi=150, bbox_inches='tight')
                print(f"✓ Chart saved: {chart_file}")
                chart_created = True
            else:
                print("⚠ Could not fetch price data for chart")
        except Exception as e:
            print(f"⚠ Chart creation failed: {e}")

        # Extract reports from final state
        market_report = final_state.get("market_report", "No market report available")
        fundamentals_report = final_state.get("fundamentals_report", "No fundamentals report available")
        news_report = final_state.get("news_report", "No news report available")
        social_media_report = final_state.get("social_media_report", "No social media report available")
        sentiment_report = final_state.get("sentiment_report", "No sentiment report available")
        final_decision = final_state.get("final_trade_decision", decision)

        # Write clean markdown report
        print(f"\nWriting markdown report...")
        with open(report_file_md, 'w') as f:
            f.write(f"# Trading Analysis Report\n\n")
            f.write(f"**Symbol:** {symbol}\n")
            f.write(f"**Trade Date:** {trade_date}\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**LLM Provider:** {config['llm_provider']}\n")
            f.write(f"**Models:** Deep Think: {config['deep_think_llm']}, Quick Think: {config['quick_think_llm']}\n\n")

            if chart_created:
                f.write(f"## Price Chart\n\n")
                f.write(f"![{symbol} Price Chart](../png/{chart_file.name})\n\n")

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

            f.write(f"## Social Media Sentiment\n\n")
            f.write(social_media_report if social_media_report != "No social media report available" else sentiment_report)
            f.write(f"\n\n---\n\n")

            f.write(f"## Final Trading Decision\n\n")
            f.write(f"**{final_decision}**\n\n")

        print(f"✓ Report saved: {report_file_md}")

        # Convert markdown to PDF
        try:
            print(f"\nConverting report to PDF...")
            md_to_pdf.md_to_pdf(str(report_file_md), str(report_file_pdf))
            print(f"✓ PDF report saved: {report_file_pdf}")
        except Exception as e:
            print(f"⚠ PDF conversion failed: {e}")
            print("Please install md-to-pdf: pip install md-to-pdf")

except Exception as e:
    print(f"\n{'='*80}")
    print(f"ERROR: {e}")
    print(f"{ '='*80}")
    import traceback
    traceback.print_exc()
    
finally:
    log_handle.close()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print(f"\nLog saved to: {log_file}")
