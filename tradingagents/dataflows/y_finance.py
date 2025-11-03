from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import os
from .stockstats_utils import StockstatsUtils

def get_YFin_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):

    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    # Create ticker object
    ticker = yf.Ticker(symbol.upper())

    # Fetch historical data for the specified date range
    data = ticker.history(start=start_date, end=end_date)

    # Check if data is empty
    if data.empty:
        return (
            f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        )

    # Remove timezone info from index for cleaner output
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Round numerical values to 2 decimal places for cleaner display
    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].round(2)

    # Convert DataFrame to CSV string
    csv_string = data.to_csv()

    # Add header information
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    return header + csv_string

def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:

    best_ind_params = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross setups. "
            "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
            "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
            "Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
            "Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )

    end_date = curr_date
    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    # Optimized: Get stock data once and calculate indicators for all dates
    try:
        indicator_data = _get_stock_stats_bulk(symbol, indicator, curr_date)
        
        # Generate the date range we need
        current_dt = curr_date_dt
        date_values = []
        
        while current_dt >= before:
            date_str = current_dt.strftime('%Y-%m-%d')
            
            # Look up the indicator value for this date
            if date_str in indicator_data:
                indicator_value = indicator_data[date_str]
            else:
                indicator_value = "N/A: Not a trading day (weekend or holiday)"
            
            date_values.append((date_str, indicator_value))
            current_dt = current_dt - relativedelta(days=1)
        
        # Build the result string
        ind_string = ""
        for date_str, value in date_values:
            ind_string += f"{date_str}: {value}\n"
        
    except Exception as e:
        print(f"Error getting bulk stockstats data: {e}")
        # Fallback to original implementation if bulk method fails
        ind_string = ""
        curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        while curr_date_dt >= before:
            indicator_value = get_stockstats_indicator(
                symbol, indicator, curr_date_dt.strftime("%Y-%m-%d")
            )
            ind_string += f"{curr_date_dt.strftime('%Y-%m-%d')}: {indicator_value}\n"
            curr_date_dt = curr_date_dt - relativedelta(days=1)

    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
        + ind_string
        + "\n\n"
        + best_ind_params.get(indicator, "No description available.")
    )

    return result_str


def _get_stock_stats_bulk(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to calculate"],
    curr_date: Annotated[str, "current date for reference"]
) -> dict:
    """
    Optimized bulk calculation of stock stats indicators.
    Fetches data once and calculates indicator for all available dates.
    Returns dict mapping date strings to indicator values.
    """
    from .config import get_config
    import pandas as pd
    from stockstats import wrap
    import os
    
    config = get_config()
    online = config["data_vendors"]["technical_indicators"] != "local"
    
    if not online:
        # Local data path
        try:
            data = pd.read_csv(
                os.path.join(
                    config.get("data_cache_dir", "data"),
                    f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                )
            )
            df = wrap(data)
        except FileNotFoundError:
            raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
    else:
        # Online data fetching with caching
        today_date = pd.Timestamp.today()
        curr_date_dt = pd.to_datetime(curr_date)
        
        end_date = today_date
        start_date = today_date - pd.DateOffset(years=15)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
        )
        
        if os.path.exists(data_file):
            data = pd.read_csv(data_file)
            data["Date"] = pd.to_datetime(data["Date"])
        else:
            data = yf.download(
                symbol,
                start=start_date_str,
                end=end_date_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
            data = data.reset_index()
            data.to_csv(data_file, index=False)
        
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    
    # Calculate the indicator for all rows at once
    df[indicator]  # This triggers stockstats to calculate the indicator
    
    # Create a dictionary mapping date strings to indicator values
    result_dict = {}
    for _, row in df.iterrows():
        date_str = row["Date"]
        indicator_value = row[indicator]
        
        # Handle NaN/None values
        if pd.isna(indicator_value):
            result_dict[date_str] = "N/A"
        else:
            result_dict[date_str] = str(indicator_value)
    
    return result_dict


def get_stockstats_indicator(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
) -> str:

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    curr_date = curr_date_dt.strftime("%Y-%m-%d")

    try:
        indicator_value = StockstatsUtils.get_stock_stats(
            symbol,
            indicator,
            curr_date,
        )
    except Exception as e:
        print(
            f"Error getting stockstats indicator data for indicator {indicator} on {curr_date}: {e}"
        )
        return ""

    return str(indicator_value)


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get balance sheet data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_balance_sheet
        else:
            data = ticker_obj.balance_sheet
            
        if data.empty:
            return f"No balance sheet data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Balance Sheet data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving balance sheet for {ticker}: {str(e)}"


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get cash flow data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_cashflow
        else:
            data = ticker_obj.cashflow
            
        if data.empty:
            return f"No cash flow data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Cash Flow data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving cash flow for {ticker}: {str(e)}"


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get income statement data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_income_stmt
        else:
            data = ticker_obj.income_stmt
            
        if data.empty:
            return f"No income statement data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Income Statement data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving income statement for {ticker}: {str(e)}"


def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol of the company"]
):
    """Get insider transactions data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        data = ticker_obj.insider_transactions
        
        if data is None or data.empty:
            return f"No insider transactions data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Insider Transactions data for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving insider transactions for {ticker}: {str(e)}"


def get_company_info(
    ticker: Annotated[str, "ticker symbol of the company"]
):
    """Get key company information from yfinance, such as fiscal year end, earnings dates, and price metrics."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info
        calendar = ticker_obj.calendar

        # Safely get fiscal year end and format it
        fiscal_year_end_ts = info.get('lastFiscalYearEnd')
        if fiscal_year_end_ts:
            fiscal_year_end = datetime.fromtimestamp(fiscal_year_end_ts).strftime('%Y-%m-%d')
        else:
            fiscal_year_end = 'N/A'

        # Safely get earnings dates and format them
        earnings_dates_str = 'N/A'
        try:
            if calendar is not None and hasattr(calendar, 'empty') and not calendar.empty and 'Earnings Date' in calendar.columns:
                # Assuming 'Earnings Date' column exists and contains datetime objects
                dates = calendar['Earnings Date'].dropna()
                if not dates.empty:
                    earnings_dates_str = ", ".join([d.strftime('%Y-%m-%d') for d in dates])
        except (AttributeError, KeyError, TypeError):
            pass  # Keep earnings_dates_str as 'N/A'

        # Get current price and 52-week high/low for fact-checking
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        fifty_two_week_high = info.get('fiftyTwoWeekHigh', 'N/A')
        fifty_two_week_low = info.get('fiftyTwoWeekLow', 'N/A')

        # Moving averages
        fifty_day_avg = info.get('fiftyDayAverage', 'N/A')
        two_hundred_day_avg = info.get('twoHundredDayAverage', 'N/A')

        # Valuation metrics
        trailing_pe = info.get('trailingPE', 'N/A')
        forward_pe = info.get('forwardPE', 'N/A')
        price_to_book = info.get('priceToBook', 'N/A')

        # Analyst consensus
        target_mean = info.get('targetMeanPrice', 'N/A')
        target_high = info.get('targetHighPrice', 'N/A')
        target_low = info.get('targetLowPrice', 'N/A')
        recommendation_mean = info.get('recommendationMean', 'N/A')
        num_analysts = info.get('numberOfAnalystOpinions', 'N/A')

        # Performance metrics
        fifty_two_week_change = info.get('52WeekChange', info.get('fiftyTwoWeekChangePercent', 'N/A'))
        market_cap = info.get('marketCap', 'N/A')

        # Profitability
        profit_margins = info.get('profitMargins', 'N/A')
        earnings_growth = info.get('earningsQuarterlyGrowth', 'N/A')

        # Format numbers
        def format_price(val):
            return f"${val:.2f}" if isinstance(val, (int, float)) else val

        def format_percent(val):
            return f"{val*100:.2f}%" if isinstance(val, (int, float)) else val

        def format_ratio(val):
            return f"{val:.2f}" if isinstance(val, (int, float)) else val

        def format_market_cap(val):
            if isinstance(val, (int, float)):
                if val >= 1e12:
                    return f"${val/1e12:.2f}T"
                elif val >= 1e9:
                    return f"${val/1e9:.2f}B"
                elif val >= 1e6:
                    return f"${val/1e6:.2f}M"
            return val

        # Map recommendation mean to text
        def format_recommendation(val):
            if isinstance(val, (int, float)):
                if val <= 1.5:
                    return f"{val:.2f} (Strong Buy)"
                elif val <= 2.5:
                    return f"{val:.2f} (Buy)"
                elif val <= 3.5:
                    return f"{val:.2f} (Hold)"
                elif val <= 4.5:
                    return f"{val:.2f} (Sell)"
                else:
                    return f"{val:.2f} (Strong Sell)"
            return val

        current_price = format_price(current_price)
        fifty_two_week_high = format_price(fifty_two_week_high)
        fifty_two_week_low = format_price(fifty_two_week_low)
        fifty_day_avg = format_price(fifty_day_avg)
        two_hundred_day_avg = format_price(two_hundred_day_avg)
        target_mean = format_price(target_mean)
        target_high = format_price(target_high)
        target_low = format_price(target_low)
        trailing_pe = format_ratio(trailing_pe)
        forward_pe = format_ratio(forward_pe)
        price_to_book = format_ratio(price_to_book)
        fifty_two_week_change = format_percent(fifty_two_week_change)
        profit_margins = format_percent(profit_margins)
        earnings_growth = format_percent(earnings_growth)
        market_cap = format_market_cap(market_cap)
        recommendation_mean = format_recommendation(recommendation_mean)

        # Build a summary string
        summary = (
            f"# Key Information for {ticker.upper()}\n"
            f"- **Last Fiscal Year End:** {fiscal_year_end}\n"
            f"- **Upcoming Earnings Dates:** {earnings_dates_str}\n"
            f"\n"
            f"## Price Metrics (for fact-checking price targets)\n"
            f"- **Current Price:** {current_price}\n"
            f"- **52-Week High:** {fifty_two_week_high}\n"
            f"- **52-Week Low:** {fifty_two_week_low}\n"
            f"- **52-Week Change:** {fifty_two_week_change}\n"
            f"- **50-Day Moving Average:** {fifty_day_avg}\n"
            f"- **200-Day Moving Average:** {two_hundred_day_avg}\n"
            f"\n"
            f"## Valuation Metrics (for fact-checking valuation claims)\n"
            f"- **Trailing P/E:** {trailing_pe}\n"
            f"- **Forward P/E:** {forward_pe}\n"
            f"- **Price-to-Book:** {price_to_book}\n"
            f"- **Market Cap:** {market_cap}\n"
            f"\n"
            f"## Analyst Consensus (for fact-checking recommendations)\n"
            f"- **Analyst Target Mean:** {target_mean}\n"
            f"- **Analyst Target Range:** {target_low} - {target_high}\n"
            f"- **Number of Analysts:** {num_analysts}\n"
            f"- **Recommendation Mean:** {recommendation_mean}\n"
            f"\n"
            f"## Profitability (for fact-checking fundamental claims)\n"
            f"- **Profit Margins:** {profit_margins}\n"
            f"- **Quarterly Earnings Growth:** {earnings_growth}\n"
            f"\n"
            f"## FACT-CHECKING GUIDELINES\n"
            f"**Price Targets:** Must be within reasonable range of current price and analyst targets. "
            f"Suggesting entry points above 52-week high needs strong justification.\n"
            f"\n"
            f"**Valuation Claims:** If claiming \"undervalued\", P/E should be below sector average. "
            f"If claiming \"overvalued\", P/E should be above average. Check price-to-book for asset-heavy companies.\n"
            f"\n"
            f"**Trend Analysis:** If price is below 200-day MA, don't claim \"strong uptrend\". "
            f"If 52-week change is negative, don't claim \"momentum\" without context.\n"
            f"\n"
            f"**Recommendation Consistency:** If analyst consensus is 4.0+ (Sell), recommending BUY needs "
            f"exceptional justification. If your target differs significantly from analyst mean, explain why.\n"
            f"\n"
            f"**Profitability Claims:** Don't claim \"strong fundamentals\" if profit margins are negative. "
            f"Don't claim \"growth story\" if earnings growth is negative.\n"
        )

        return summary

    except Exception as e:
        return f"Error retrieving company info for {ticker}: {str(e)}"