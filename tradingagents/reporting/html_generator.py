# TradingAgents HTML Report Generator
# Perplexity-inspired design for trading analysis reports

import re
import markdown
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

def generate_html_report(
    symbol: str,
    trade_date: str,
    final_state: Dict,
    decision: str,
    chart_file: Optional[Path] = None,
    urls: Optional[List[str]] = None,
    provider: str = "databricks"
) -> str:
    """Generate a Perplexity-inspired HTML report for trading analysis.

    Args:
        symbol: Stock symbol (e.g., "MSFT")
        trade_date: Analysis date (e.g., "2025-10-30")
        final_state: State dictionary containing all analysis reports
        decision: Final trading decision
        chart_file: Path to chart image file
        urls: List of source URLs
        provider: LLM provider name

    Returns:
        HTML string for the complete report
    """

    # Extract key data
    market_report = final_state.get('market_report', 'N/A')
    fundamentals_report = final_state.get('fundamentals_report', 'N/A')
    news_report = final_state.get('news_report', 'N/A')
    sentiment_report = final_state.get('social_media_report', final_state.get('sentiment_report', 'N/A'))

    investment_debate = final_state.get('investment_debate_state', {})
    judge_decision = investment_debate.get('judge_decision', 'N/A')
    bull_history = investment_debate.get('bull_history', 'N/A')
    bear_history = investment_debate.get('bear_history', 'N/A')

    trader_plan = final_state.get('trader_investment_plan', 'N/A')
    final_decision_text = final_state.get('final_trade_decision', decision)

    # Extract recommendations - improved to avoid "See Analysis"
    market_rec = extract_recommendation(market_report)
    fundamentals_rec = extract_recommendation(fundamentals_report)
    news_rec = extract_recommendation(news_report)
    social_rec = extract_recommendation(sentiment_report)
    investment_judge = extract_recommendation(judge_decision)
    trader_rec = extract_recommendation(trader_plan)

    # Extract final decision
    final_dec = extract_recommendation(final_decision_text)
    if final_dec == 'See Analysis':
        final_dec = decision.replace('FINAL TRANSACTION PROPOSAL: ', '').replace('**', '').strip()
        match = re.search(r'\b(BUY|SELL|HOLD)\b', final_dec.upper())
        if match:
            final_dec = match.group(1)

    # Decision color
    def get_decision_color(dec):
        return {
            'BUY': '#10b981',
            'SELL': '#ef4444',
            'HOLD': '#f59e0b'
        }.get(dec, '#6b7280')

    decision_color = get_decision_color(final_dec)

    # Convert markdown to HTML for reports
    def md_to_html(text):
        if text == 'N/A':
            return '<p class="text-gray-400">No data available</p>'
        return markdown.markdown(text, extensions=['tables', 'fenced_code'])

    # Decision badge HTML
    def decision_badge(rec):
        color = get_decision_color(rec)
        return f'<span class="decision-badge" style="background: {color}20; color: {color}; border: 1px solid {color}40;">{rec}</span>'

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - Trading Analysis</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #0a0a0a;
            color: #e5e7eb;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 24px 0;
            border-bottom: 1px solid #262626;
        }}

        .company-logo {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: white;
        }}

        .company-info h1 {{
            font-size: 28px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }}

        .company-meta {{
            display: flex;
            gap: 12px;
            align-items: center;
            font-size: 14px;
            color: #9ca3af;
        }}

        .badge {{
            background: #1f2937;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}

        .decision-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}

        .main-content {{
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
            margin-top: 24px;
        }}

        .left-column {{
            min-width: 0;
        }}

        .right-sidebar {{
            position: sticky;
            top: 20px;
            height: fit-content;
        }}

        .decision-card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}

        .decision-large {{
            font-size: 48px;
            font-weight: 700;
            color: {decision_color};
            margin: 16px 0;
            text-align: center;
        }}

        .decision-date {{
            text-align: center;
            color: #9ca3af;
            font-size: 14px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin: 24px 0;
        }}

        .metric-item {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 16px;
        }}

        .metric-label {{
            font-size: 13px;
            color: #9ca3af;
            margin-bottom: 8px;
        }}

        .metric-value {{
            font-size: 18px;
            font-weight: 600;
        }}

        .chart-container {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 0;
            margin-bottom: 24px;
            overflow: hidden;
        }}

        .chart-container iframe {{
            width: 100%;
            height: 500px;
            border: none;
            display: block;
        }}

        .chart-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}

        .section {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}

        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1f2937;
        }}

        .section h2 {{
            font-size: 20px;
            font-weight: 600;
            color: #fff;
        }}

        .section h3 {{
            font-size: 18px;
            font-weight: 600;
            color: #e5e7eb;
            margin: 20px 0 12px 0;
        }}

        .section h4 {{
            font-size: 16px;
            font-weight: 600;
            color: #d1d5db;
            margin: 16px 0 10px 0;
        }}

        .section p {{
            color: #d1d5db;
            margin-bottom: 12px;
        }}

        .section ul, .section ol {{
            color: #d1d5db;
            margin-left: 20px;
            margin-bottom: 12px;
        }}

        .section table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }}

        .section table th {{
            background: #1f2937;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            color: #9ca3af;
            border: 1px solid #262626;
        }}

        .section table td {{
            padding: 12px;
            border: 1px solid #262626;
            color: #d1d5db;
        }}

        .section table tr:hover {{
            background: #1a1a1a;
        }}

        .debate-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}

        .debate-column {{
            background: #1a1a1a;
            border: 1px solid #262626;
            border-radius: 8px;
            padding: 20px;
        }}

        .debate-column h4 {{
            margin-top: 0;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #262626;
        }}

        .bull-column {{
            border-top: 3px solid #10b981;
        }}

        .bear-column {{
            border-top: 3px solid #ef4444;
        }}

        .info-card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #1f2937;
        }}

        .info-row:last-child {{
            border-bottom: none;
        }}

        .info-label {{
            font-size: 13px;
            color: #9ca3af;
        }}

        .info-value {{
            font-size: 14px;
            font-weight: 500;
        }}

        .sources {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-top: 24px;
        }}

        .sources h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 16px;
        }}

        .sources ul {{
            list-style: none;
            padding: 0;
        }}

        .sources li {{
            margin-bottom: 8px;
        }}

        .sources a {{
            color: #60a5fa;
            text-decoration: none;
            font-size: 13px;
            word-break: break-all;
        }}

        .sources a:hover {{
            text-decoration: underline;
        }}

        .timestamp {{
            text-align: center;
            color: #6b7280;
            font-size: 13px;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #1f2937;
        }}

        @media (max-width: 1024px) {{
            .debate-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 968px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}

            .right-sidebar {{
                position: static;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="company-logo">{symbol[0]}</div>
            <div class="company-info">
                <h1>{symbol} Trading Analysis</h1>
                <div class="company-meta">
                    <span class="badge">NASDAQ</span>
                    <span>{trade_date}</span>
                    <span>Provider: {provider}</span>
                </div>
            </div>
        </header>

        <div class="main-content">
            <div class="left-column">
                <div class="decision-card">
                    <h2>Final Trading Decision</h2>
                    <div class="decision-large">{final_dec}</div>
                    <div class="decision-date">Analysis Date: {trade_date}</div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="metric-label">Market Analysis</div>
                        <div class="metric-value">{decision_badge(market_rec)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Fundamentals</div>
                        <div class="metric-value">{decision_badge(fundamentals_rec)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">News Sentiment</div>
                        <div class="metric-value">{decision_badge(news_rec)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Social Media</div>
                        <div class="metric-value">{decision_badge(social_rec)}</div>
                    </div>
                </div>

                <div class="chart-container">
                    <iframe src="https://www.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol={symbol}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en&utm_source=&utm_medium=widget&utm_campaign=chart&utm_term={symbol}" frameborder="0" allowtransparency="true" scrolling="no" allowfullscreen></iframe>
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Market Analysis</h2>
                        {decision_badge(market_rec)}
                    </div>
                    {md_to_html(market_report)}
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Fundamental Analysis</h2>
                        {decision_badge(fundamentals_rec)}
                    </div>
                    {md_to_html(fundamentals_report)}
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>News Analysis</h2>
                        {decision_badge(news_rec)}
                    </div>
                    {md_to_html(news_report)}
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Social Media Sentiment</h2>
                        {decision_badge(social_rec)}
                    </div>
                    {md_to_html(sentiment_report)}
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Investment Debate</h2>
                        {decision_badge(investment_judge)}
                    </div>
                    <h3>Research Manager Decision</h3>
                    {md_to_html(judge_decision)}

                    <div class="debate-grid">
                        <div class="debate-column bull-column">
                            <h4 style="color: #10b981;">🐂 Bull Arguments</h4>
                            {md_to_html(bull_history)}
                        </div>
                        <div class="debate-column bear-column">
                            <h4 style="color: #ef4444;">🐻 Bear Arguments</h4>
                            {md_to_html(bear_history)}
                        </div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Trader Analysis</h2>
                        {decision_badge(trader_rec)}
                    </div>
                    {md_to_html(trader_plan)}
                </div>

                <div class="section">
                    <div class="section-header">
                        <h2>Final Risk-Adjusted Decision</h2>
                        {decision_badge(final_dec)}
                    </div>
                    <div style="background: #1a1a1a; border-left: 4px solid {decision_color}; padding: 20px; margin-bottom: 20px; border-radius: 8px;">
                        <div style="font-size: 16px; font-weight: 600; color: {decision_color}; margin-bottom: 8px;">
                            FINAL RECOMMENDATION: {final_dec}
                        </div>
                        <div style="font-size: 14px; color: #9ca3af;">
                            Risk Manager's comprehensive analysis below
                        </div>
                    </div>
                    {md_to_html(final_decision_text)}
                </div>

                {generate_sources_section(urls) if urls else ''}
            </div>

            <div class="right-sidebar">
                <div class="info-card">
                    <h3 style="font-size: 16px; margin-bottom: 16px; color: #fff;">Decision Pipeline</h3>
                    <div class="info-row">
                        <div class="info-label">Research Manager</div>
                        <div class="info-value">{decision_badge(investment_judge)}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Trader</div>
                        <div class="info-value">{decision_badge(trader_rec)}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Risk Manager</div>
                        <div class="info-value">{decision_badge(final_dec)}</div>
                    </div>
                </div>

                <div class="info-card">
                    <h3 style="font-size: 16px; margin-bottom: 16px; color: #fff;">Analyst Consensus</h3>
                    <div class="info-row">
                        <div class="info-label">Market</div>
                        <div class="info-value">{decision_badge(market_rec)}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Fundamentals</div>
                        <div class="info-value">{decision_badge(fundamentals_rec)}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">News</div>
                        <div class="info-value">{decision_badge(news_rec)}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Social</div>
                        <div class="info-value">{decision_badge(social_rec)}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="timestamp">
            Analysis generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""

    return html


def extract_recommendation(text: str) -> str:
    """Extract BUY/SELL/HOLD recommendation from text."""
    if not text or text == 'N/A':
        return 'N/A'

    # Look for explicit recommendation patterns
    patterns = [
        r'FINAL TRANSACTION PROPOSAL:\s*\*\*([A-Z]+)\*\*',
        r'Recommendation:\s*\*\*([A-Z]+)\*\*',
        r'My Recommendation:\s*\*\*([A-Z]+)\*\*',
        r'\*\*Recommendation\*\*:\s*([A-Z]+)',
        r'Final Decision:\s*\*\*([A-Z]+)\*\*',
        r'Decision:\s*\*\*([A-Z]+)\*\*',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    # Look for standalone BUY/SELL/HOLD mentions
    match = re.search(r'\b(BUY|SELL|HOLD)\b', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return 'See Analysis'


def generate_sources_section(urls: List[str]) -> str:
    """Generate HTML for sources section."""
    if not urls:
        return ''

    urls_html = '\n'.join([f'<li><a href="{url}" target="_blank">{url}</a></li>' for url in sorted(urls)])

    return f"""
    <div class="sources">
        <h2>Sources</h2>
        <p style="color: #9ca3af; margin-bottom: 12px; font-size: 14px;">This analysis referenced the following sources:</p>
        <ul>
            {urls_html}
        </ul>
    </div>
    """
