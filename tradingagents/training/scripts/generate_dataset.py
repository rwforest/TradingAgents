#!/usr/bin/env python3
"""
Generate training dataset for Market Analyst optimization.

This script:
1. Downloads historical stock data
2. Calculates future returns as ground truth
3. Creates train/val splits
4. Saves datasets to JSON files

Usage:
    python generate_dataset.py
    python generate_dataset.py --symbols MSFT NVDA GOOGL --start 2023-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tradingagents.training.datasets.market_analyst_dataset import (
    MarketAnalystDatasetBuilder
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate training dataset for Market Analyst"
    )

    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["MSFT", "NVDA", "GOOGL", "AAPL", "META", "AMZN", "TSLA"],
        help="Stock symbols to include in dataset"
    )

    parser.add_argument(
        "--start",
        default="2023-01-01",
        help="Start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        default="2024-12-31",
        help="End date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Days of history needed before each trade date"
    )

    parser.add_argument(
        "--future-days",
        type=int,
        default=5,
        help="Days ahead to calculate return (ground truth)"
    )

    parser.add_argument(
        "--val-split",
        type=float,
        default=0.2,
        help="Fraction of data for validation (default: 0.2)"
    )

    parser.add_argument(
        "--output-dir",
        default="./training_data",
        help="Output directory for dataset files"
    )

    parser.add_argument(
        "--cache-dir",
        default="./training_data/cache",
        help="Cache directory for downloaded data"
    )

    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Print configuration
    print("=" * 80)
    print("Market Analyst Dataset Generation")
    print("=" * 80)
    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Date range: {args.start} to {args.end}")
    print(f"Lookback: {args.lookback_days} days")
    print(f"Future return: {args.future_days} days")
    print(f"Validation split: {args.val_split * 100}%")
    print(f"Output directory: {args.output_dir}")
    print(f"Cache directory: {args.cache_dir}")
    print("=" * 80)
    print()

    # Create builder
    builder = MarketAnalystDatasetBuilder(
        lookback_days=args.lookback_days,
        future_days=args.future_days
    )

    # Build dataset
    print("Downloading and processing data...")
    tasks = builder.build(
        symbols=args.symbols,
        start_date=args.start,
        end_date=args.end,
        cache_dir=args.cache_dir
    )

    if not tasks:
        print("\n✗ No tasks created! Check your symbols and date range.")
        return 1

    # Split into train/val
    print(f"\nSplitting dataset (validation: {args.val_split * 100}%)...")
    train_tasks, val_tasks = builder.split_train_val(
        tasks=tasks,
        val_split=args.val_split,
        random_seed=args.random_seed
    )

    # Save datasets
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    train_path = output_dir / f"market_analyst_train_{timestamp}.json"
    val_path = output_dir / f"market_analyst_val_{timestamp}.json"

    print(f"\nSaving datasets...")
    builder.save_dataset(train_tasks, str(train_path))
    builder.save_dataset(val_tasks, str(val_path))

    # Print statistics
    print("\n" + "=" * 80)
    print("Dataset Statistics")
    print("=" * 80)
    print(f"Total tasks: {len(tasks)}")
    print(f"Training tasks: {len(train_tasks)}")
    print(f"Validation tasks: {len(val_tasks)}")
    print()

    # Analyze return distribution
    import statistics
    train_returns = [t["expected_return"] for t in train_tasks]
    val_returns = [t["expected_return"] for t in val_tasks]

    print("Training set return distribution:")
    print(f"  Mean: {statistics.mean(train_returns):.4f}")
    print(f"  Median: {statistics.median(train_returns):.4f}")
    print(f"  Std Dev: {statistics.stdev(train_returns):.4f}")
    print(f"  Min: {min(train_returns):.4f}")
    print(f"  Max: {max(train_returns):.4f}")
    print()

    print("Validation set return distribution:")
    print(f"  Mean: {statistics.mean(val_returns):.4f}")
    print(f"  Median: {statistics.median(val_returns):.4f}")
    print(f"  Std Dev: {statistics.stdev(val_returns):.4f}")
    print(f"  Min: {min(val_returns):.4f}")
    print(f"  Max: {max(val_returns):.4f}")
    print()

    # Count positive/negative/neutral returns
    def count_return_categories(returns):
        positive = sum(1 for r in returns if r > 0.02)
        negative = sum(1 for r in returns if r < -0.02)
        neutral = len(returns) - positive - negative
        return positive, neutral, negative

    train_pos, train_neu, train_neg = count_return_categories(train_returns)
    val_pos, val_neu, val_neg = count_return_categories(val_returns)

    print("Training set categories (>2% / neutral / <-2%):")
    print(f"  Positive: {train_pos} ({train_pos/len(train_returns)*100:.1f}%)")
    print(f"  Neutral:  {train_neu} ({train_neu/len(train_returns)*100:.1f}%)")
    print(f"  Negative: {train_neg} ({train_neg/len(train_returns)*100:.1f}%)")
    print()

    print("Validation set categories (>2% / neutral / <-2%):")
    print(f"  Positive: {val_pos} ({val_pos/len(val_returns)*100:.1f}%)")
    print(f"  Neutral:  {val_neu} ({val_neu/len(val_returns)*100:.1f}%)")
    print(f"  Negative: {val_neg} ({val_neg/len(val_returns)*100:.1f}%)")

    print("\n" + "=" * 80)
    print("✓ Dataset generation complete!")
    print("=" * 80)
    print(f"\nTrain dataset: {train_path}")
    print(f"Val dataset:   {val_path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
