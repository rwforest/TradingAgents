"""
Dataset builder for Market Analyst training.

Creates training and validation datasets by:
1. Fetching historical stock data
2. Calculating future returns as ground truth labels
3. Creating tasks in the format expected by LitMarketAnalyst
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from pathlib import Path
import json


class MarketAnalystDatasetBuilder:
    """Builds training datasets for Market Analyst optimization."""

    def __init__(
        self,
        lookback_days: int = 30,
        future_days: int = 5,
        min_data_points: int = 100
    ):
        """
        Initialize dataset builder.

        Args:
            lookback_days: Days of history needed before a trade date
            future_days: Days ahead to calculate return (ground truth)
            min_data_points: Minimum data points needed for a symbol
        """
        self.lookback_days = lookback_days
        self.future_days = future_days
        self.min_data_points = min_data_points

    def build(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        cache_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Build training dataset from historical data.

        Args:
            symbols: List of stock tickers (e.g., ["MSFT", "NVDA"])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            cache_dir: Optional directory to cache downloaded data

        Returns:
            List of task dictionaries, each containing:
                - symbol: Stock ticker
                - trade_date: Analysis date
                - expected_return: Actual return over future_days
        """
        tasks = []

        for symbol in symbols:
            print(f"Building dataset for {symbol}...")

            try:
                # Get historical data
                df = self._get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    cache_dir=cache_dir
                )

                if df is None or len(df) < self.min_data_points:
                    print(f"  ⚠ Skipping {symbol}: insufficient data")
                    continue

                # Generate tasks
                symbol_tasks = self._create_tasks_from_dataframe(symbol, df)
                tasks.extend(symbol_tasks)

                print(f"  ✓ Created {len(symbol_tasks)} tasks for {symbol}")

            except Exception as e:
                print(f"  ✗ Error processing {symbol}: {e}")
                continue

        print(f"\nTotal tasks created: {len(tasks)}")
        return tasks

    def _get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        cache_dir: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a symbol.

        Args:
            symbol: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            cache_dir: Optional cache directory

        Returns:
            DataFrame with OHLCV data, or None if failed
        """
        # Try cache first
        if cache_dir:
            cache_path = Path(cache_dir) / f"{symbol}_historical.csv"
            if cache_path.exists():
                try:
                    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                    return df
                except Exception as e:
                    print(f"  Warning: Cache read failed: {e}")

        # Fetch from Yahoo Finance
        try:
            # Add buffer for lookback and future returns
            buffer_start = (
                datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=self.lookback_days + 10)
            ).strftime("%Y-%m-%d")

            buffer_end = (
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=self.future_days + 10)
            ).strftime("%Y-%m-%d")

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=buffer_start, end=buffer_end)

            if df.empty:
                return None

            # Save to cache
            if cache_dir:
                cache_path = Path(cache_dir)
                cache_path.mkdir(parents=True, exist_ok=True)
                df.to_csv(cache_path / f"{symbol}_historical.csv")

            return df

        except Exception as e:
            print(f"  Error fetching data: {e}")
            return None

    def _create_tasks_from_dataframe(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Create training tasks from historical dataframe.

        Args:
            symbol: Stock ticker
            df: Historical OHLCV dataframe

        Returns:
            List of tasks
        """
        tasks = []

        # Ensure we have enough data for lookback and future returns
        for i in range(self.lookback_days, len(df) - self.future_days):
            current_date = df.index[i]
            future_date_idx = i + self.future_days

            # Calculate future return
            current_price = df.iloc[i]["Close"]
            future_price = df.iloc[future_date_idx]["Close"]
            expected_return = (future_price - current_price) / current_price

            task = {
                "symbol": symbol,
                "trade_date": current_date.strftime("%Y-%m-%d"),
                "expected_return": float(expected_return),
                # Additional metadata for analysis
                "current_price": float(current_price),
                "future_price": float(future_price),
                "future_days": self.future_days
            }

            tasks.append(task)

        return tasks

    def save_dataset(
        self,
        tasks: List[Dict[str, Any]],
        output_path: str
    ):
        """
        Save dataset to JSON file.

        Args:
            tasks: List of task dictionaries
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(tasks, f, indent=2)

        print(f"Dataset saved to {output_path}")

    def load_dataset(self, input_path: str) -> List[Dict[str, Any]]:
        """
        Load dataset from JSON file.

        Args:
            input_path: Path to JSON file

        Returns:
            List of tasks
        """
        with open(input_path, 'r') as f:
            tasks = json.load(f)

        print(f"Loaded {len(tasks)} tasks from {input_path}")
        return tasks

    def split_train_val(
        self,
        tasks: List[Dict[str, Any]],
        val_split: float = 0.2,
        random_seed: int = 42
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split dataset into train and validation sets.

        Args:
            tasks: List of all tasks
            val_split: Fraction for validation (default 0.2 = 20%)
            random_seed: Random seed for reproducibility

        Returns:
            Tuple of (train_tasks, val_tasks)
        """
        import random
        random.seed(random_seed)

        # Shuffle tasks
        shuffled = tasks.copy()
        random.shuffle(shuffled)

        # Split
        split_idx = int(len(shuffled) * (1 - val_split))
        train_tasks = shuffled[:split_idx]
        val_tasks = shuffled[split_idx:]

        print(f"Split: {len(train_tasks)} train, {len(val_tasks)} validation")
        return train_tasks, val_tasks


def create_market_analyst_dataset(
    symbols: List[str],
    start_date: str,
    end_date: str,
    lookback_days: int = 30,
    future_days: int = 5,
    cache_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to create a market analyst dataset.

    Args:
        symbols: List of stock tickers
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        lookback_days: Days of history needed
        future_days: Days ahead for return calculation
        cache_dir: Optional cache directory

    Returns:
        List of training tasks
    """
    builder = MarketAnalystDatasetBuilder(
        lookback_days=lookback_days,
        future_days=future_days
    )

    return builder.build(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        cache_dir=cache_dir
    )
