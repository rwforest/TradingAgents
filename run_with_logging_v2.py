"""
Run TradingAgents with quiet console output.
Shows only: stage, settings, and status.
Full logs saved to logs/ directory.
"""
import os, sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yfinance as yf

load_dotenv()
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Setup logging
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"analysis_{timestamp}.log"

# Quiet console output - only show important messages
class QuietOutput:
    def __init__(self, console, logfile):
        self.console = console
        self.logfile = logfile
        self.buffer = ""
        self.keywords = ["Log file:", "Analysis started", "Initializing", "Running analysis",
                        "FINAL DECISION:", "completed", "✓", "⚠", "ERROR:", "Provider:", "="*40]

    def write(self, msg):
        # Always write to log file
        self.logfile.write(msg)
        self.logfile.flush()

        # Buffer messages until we get a newline
        self.buffer += msg

        # Process complete lines
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            # Process all complete lines (all but the last, which might be incomplete)
            for line in lines[:-1]:
                if any(k in line for k in self.keywords):
                    self.console.write(line + '\n')
                    self.console.flush()
            # Keep the incomplete part
            self.buffer = lines[-1]

    def flush(self):
        # Flush any remaining buffer
        if self.buffer and any(k in self.buffer for k in self.keywords):
            self.console.write(self.buffer)
            self.console.flush()
        self.buffer = ""
        self.logfile.flush()
        self.console.flush()

log_handle = open(log_file, 'w')
orig_stdout, orig_stderr = sys.stdout, sys.stderr
sys.stdout = sys.stderr = QuietOutput(orig_stdout, log_handle)

try:
    symbols = ["MSFT", "NVDA", "META", "GOOGL", "INTC", "TSLA"]
    trade_date = datetime.today().strftime('%Y-%m-%d')
    
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "databricks"
    config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
    config["quick_think_llm"] = "llama_v3_3_70b_instruct_pro"
    if config.get("databricks_base_url") and not config["databricks_base_url"].endswith("/serving-endpoints"):
        config["databricks_base_url"] = config["databricks_base_url"].rstrip("/") + "/serving-endpoints"
    
    print(f"Log file: {log_file}")
    print("="*80)
    print(f"Analysis started: {datetime.now()}")
    print(f"Provider: {config['llm_provider']}, Deep: {config['deep_think_llm']}, Quick: {config['quick_think_llm']}")
    print("="*80)
    
    print("\nInitializing TradingAgentsGraph...")
    ta = TradingAgentsGraph(debug=True, config=config, enable_rate_limiting=False)
    print("✓ Initialized!\n")
    
    for symbol in symbols:
        print(f"\nRunning analysis: {symbol} on {trade_date}...")
        final_state, decision = ta.propagate(symbol, trade_date)
        
        print("="*80)
        print(f"FINAL DECISION: {decision}")
        print("="*80)
        print(f"✓ Analysis completed: {datetime.now()}\n")
        
        # Save outputs
        out_dir = Path("analysis_results") / symbol
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = out_dir / f"{symbol}_{ts}.md"
        pdf_file = out_dir / f"{symbol}_{ts}.pdf"
        chart_file = out_dir / f"{symbol}_{ts}_chart.png"
        
        # Chart
        chart_ok = False
        try:
            print("✓ Creating chart...")
            end = datetime.strptime(trade_date, "%Y-%m-%d")
            df = yf.Ticker(symbol).history(start=(end - timedelta(180)).strftime("%Y-%m-%d"), end=trade_date)
            if not df.empty:
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(df.index, df['Close'], linewidth=2, color='#2E86AB')
                ax.fill_between(df.index, df['Close'], alpha=0.3, color='#2E86AB')
                ax.set_title(f'{symbol} - Last 6 Months', fontsize=16, fontweight='bold')
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(chart_file, dpi=150, bbox_inches='tight')
                plt.close()
                print(f"✓ Chart: {chart_file.name}")
                chart_ok = True
        except Exception as e:
            print(f"⚠ Chart failed: {e}")
        
        # Extract URLs from log file
        print("✓ Extracting sources...")
        import re
        urls = set()
        log_handle.flush()
        with open(log_file, 'r') as lf:
            for line in lf:
                # Extract all URLs (http/https)
                found_urls = re.findall(r'https?://[^\s\'"<>)\]]+', line)
                for url in found_urls:
                    # Clean up URL (remove trailing punctuation)
                    url = re.sub(r'[,;.)\]]+$', '', url)
                    # Skip very long URLs (likely data dumps)
                    if len(url) < 200:
                        urls.add(url)

        # Helper function to extract recommendation from report
        def extract_recommendation(report_text):
            import re
            if not report_text or report_text == 'N/A':
                return 'N/A'
            # Look for common recommendation patterns (most specific first)
            patterns = [
                r'FINAL RECOMMENDATION:\s*\*\*([A-Z]+(?:\s*\([^)]+\))?)\*\*',  # Matches "BUY (Modified Conservative Approach)"
                r'FINAL RECOMMENDATION:\s*([A-Z]+(?:\s*\([^)]+\))?)',
                r'FINAL TRANSACTION PROPOSAL:\s*\*\*([A-Z]+)\*\*',
                r'RECOMMENDATION:\s*\*\*([A-Z]+)\*\*',
                r'Decision:\s*\*\*([A-Z]+)\*\*',
                r'\*\*([A-Z]+)\*\*\s*(?:recommendation|decision)',
            ]
            for pattern in patterns:
                match = re.search(pattern, report_text, re.IGNORECASE)
                if match:
                    rec = match.group(1).strip()
                    # Clean up - extract just the action if there's a parenthetical
                    if '(' in rec:
                        main_action = rec.split('(')[0].strip()
                        return main_action.upper()
                    return rec.upper()
            return 'See Analysis'

        # Extract recommendations from each report
        market_rec = extract_recommendation(final_state.get('market_report', ''))
        fundamentals_rec = extract_recommendation(final_state.get('fundamentals_report', ''))
        news_rec = extract_recommendation(final_state.get('news_report', ''))
        social_rec = extract_recommendation(final_state.get('social_media_report', final_state.get('sentiment_report', '')))

        # Extract intermediate decisions
        investment_judge = extract_recommendation(final_state.get('investment_debate_state', {}).get('judge_decision', ''))
        trader_plan = extract_recommendation(final_state.get('trader_investment_plan', ''))

        # Extract final decision - handle complex formats
        final_decision_text = final_state.get('final_trade_decision', decision)
        final_dec = extract_recommendation(final_decision_text)
        if final_dec == 'See Analysis':
            # Fallback: try to get from the decision variable
            final_dec = decision.replace('FINAL TRANSACTION PROPOSAL: ', '').replace('**', '').strip()
            # If still complex, extract first word that's BUY/SELL/HOLD
            import re
            match = re.search(r'\b(BUY|SELL|HOLD)\b', final_dec.upper())
            if match:
                final_dec = match.group(1)

        # Markdown
        print("✓ Writing markdown...")
        with open(md_file, 'w') as f:
            f.write(f"# Trading Analysis: {symbol}\n\n**Date:** {trade_date}\n**Provider:** {config['llm_provider']}\n\n")
            if chart_ok:
                f.write(f"![Chart](./{chart_file.name})\n\n")

            # Summary table with recommendations and links
            f.write("## Executive Summary\n\n")
            f.write("### Analyst Recommendations\n")
            f.write("| Analysis Section | Recommendation | Details |\n")
            f.write("|-----------------|----------------|----------|\n")
            f.write(f"| Market Analysis | {market_rec} | [View Analysis](#market-analysis) |\n")
            f.write(f"| Fundamental Analysis | {fundamentals_rec} | [View Analysis](#fundamental-analysis) |\n")
            f.write(f"| News Analysis | {news_rec} | [View Analysis](#news-analysis) |\n")
            f.write(f"| Social Media Sentiment | {social_rec} | [View Analysis](#social-media-sentiment) |\n")

            # Intermediate decisions
            f.write("\n### Decision Pipeline\n")
            f.write("| Decision Stage | Recommendation | Details |\n")
            f.write("|----------------|----------------|----------|\n")
            f.write(f"| Investment Research (Bull/Bear Debate) | {investment_judge} | [View Debate](#investment-debate) |\n")
            f.write(f"| Trader Analysis | {trader_plan} | [View Plan](#trader-analysis) |\n")
            f.write(f"| **Final Risk-Adjusted Decision** | **{final_dec}** | [View Decision](#final-trading-decision) |\n")
            f.write("\n---\n\n")

            f.write(f"## Market Analysis\n{final_state.get('market_report', 'N/A')}\n\n---\n\n")
            f.write(f"## Fundamental Analysis\n{final_state.get('fundamentals_report', 'N/A')}\n\n---\n\n")
            f.write(f"## News Analysis\n{final_state.get('news_report', 'N/A')}\n\n---\n\n")
            f.write(f"## Social Media Sentiment\n{final_state.get('social_media_report', final_state.get('sentiment_report', 'N/A'))}\n\n---\n\n")

            # Add intermediate decision sections
            f.write(f"## Investment Debate\n")
            f.write(f"### Research Manager Decision\n{final_state.get('investment_debate_state', {}).get('judge_decision', 'N/A')}\n\n")
            f.write(f"<details>\n<summary>View Bull/Bear Debate History</summary>\n\n")
            f.write(f"**Bull Arguments:**\n{final_state.get('investment_debate_state', {}).get('bull_history', 'N/A')}\n\n")
            f.write(f"**Bear Arguments:**\n{final_state.get('investment_debate_state', {}).get('bear_history', 'N/A')}\n\n")
            f.write(f"</details>\n\n---\n\n")

            f.write(f"## Trader Analysis\n{final_state.get('trader_investment_plan', 'N/A')}\n\n---\n\n")

            f.write(f"## Final Trading Decision\n{final_state.get('final_trade_decision', decision)}\n\n")

            # Add sources section at the end
            if urls:
                f.write(f"---\n\n## Sources\n\n")
                f.write(f"This analysis referenced the following sources:\n\n")
                for url in sorted(urls):
                    f.write(f"- {url}\n")
                f.write(f"\n*Analysis generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n")
        print(f"✓ Markdown: {md_file.name}")
        
        # PDF
        try:
            print("✓ Converting PDF...")
            from md2pdf.core import md2pdf
            md2pdf(str(pdf_file), md_file_path=str(md_file))
            print(f"✓ PDF: {pdf_file.name}")
        except ImportError:
            print("⚠ PDF skipped (pip install md2pdf)")
        except Exception as e:
            print(f"⚠ PDF failed: {e}")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    log_handle.close()
    sys.stdout, sys.stderr = orig_stdout, orig_stderr
    print(f"\n✓ Full log: {log_file}")
