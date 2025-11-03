#!/usr/bin/env python3
"""
Evaluate Market Analyst performance on a dataset.

This script:
1. Loads a validation dataset
2. Runs the Market Analyst on each task
3. Calculates accuracy and reward metrics
4. Generates evaluation report

Usage:
    python evaluate_market_analyst.py --dataset ./training_data/market_analyst_val_*.json
    python evaluate_market_analyst.py --dataset ./training_data/market_analyst_val_*.json --sample 10
"""

import argparse
import json
from pathlib import Path
import sys
from typing import List, Dict, Any
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tradingagents.agents.optimizable.market_analyst_agent import LitMarketAnalyst


def evaluate_dataset(
    agent: LitMarketAnalyst,
    tasks: List[Dict[str, Any]],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Evaluate agent on a list of tasks.

    Args:
        agent: LitMarketAnalyst instance
        tasks: List of evaluation tasks
        verbose: Print detailed results for each task

    Returns:
        Dictionary with evaluation metrics
    """
    results = []
    rewards = []
    correct_directions = 0
    total_tasks = len(tasks)

    print(f"\nEvaluating {total_tasks} tasks...")
    print("=" * 80)

    for i, task in enumerate(tasks):
        if verbose or (i + 1) % 10 == 0:
            print(f"Task {i+1}/{total_tasks}: {task['symbol']} on {task['trade_date']}")

        try:
            # Run agent
            reward = agent.rollout(task)

            # Calculate if direction was correct
            expected_return = task["expected_return"]
            direction_correct = reward > 0  # Positive reward means correct direction

            result = {
                "symbol": task["symbol"],
                "trade_date": task["trade_date"],
                "expected_return": expected_return,
                "reward": reward,
                "direction_correct": direction_correct
            }

            results.append(result)
            rewards.append(reward)

            if direction_correct:
                correct_directions += 1

            if verbose:
                print(f"  Expected return: {expected_return:+.4f}")
                print(f"  Reward: {reward:+.4f}")
                print(f"  Correct: {'✓' if direction_correct else '✗'}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "symbol": task["symbol"],
                "trade_date": task["trade_date"],
                "error": str(e),
                "reward": -0.5
            })
            rewards.append(-0.5)

    # Calculate metrics
    accuracy = correct_directions / total_tasks if total_tasks > 0 else 0
    mean_reward = statistics.mean(rewards) if rewards else 0
    median_reward = statistics.median(rewards) if rewards else 0
    std_reward = statistics.stdev(rewards) if len(rewards) > 1 else 0

    # Categorize performance
    high_rewards = sum(1 for r in rewards if r >= 0.7)
    medium_rewards = sum(1 for r in rewards if 0 < r < 0.7)
    low_rewards = sum(1 for r in rewards if -0.5 <= r <= 0)
    negative_rewards = sum(1 for r in rewards if r < -0.5)

    metrics = {
        "total_tasks": total_tasks,
        "correct_directions": correct_directions,
        "accuracy": accuracy,
        "mean_reward": mean_reward,
        "median_reward": median_reward,
        "std_reward": std_reward,
        "min_reward": min(rewards) if rewards else 0,
        "max_reward": max(rewards) if rewards else 0,
        "high_rewards": high_rewards,
        "medium_rewards": medium_rewards,
        "low_rewards": low_rewards,
        "negative_rewards": negative_rewards,
        "results": results
    }

    return metrics


def print_report(metrics: Dict[str, Any]):
    """Print evaluation report."""
    print("\n" + "=" * 80)
    print("Evaluation Report")
    print("=" * 80)
    print(f"Total tasks evaluated: {metrics['total_tasks']}")
    print(f"Correct directions: {metrics['correct_directions']} / {metrics['total_tasks']}")
    print(f"Accuracy: {metrics['accuracy'] * 100:.2f}%")
    print()

    print("Reward Statistics:")
    print(f"  Mean:   {metrics['mean_reward']:+.4f}")
    print(f"  Median: {metrics['median_reward']:+.4f}")
    print(f"  Std:    {metrics['std_reward']:.4f}")
    print(f"  Min:    {metrics['min_reward']:+.4f}")
    print(f"  Max:    {metrics['max_reward']:+.4f}")
    print()

    print("Reward Distribution:")
    print(f"  High (≥0.7):      {metrics['high_rewards']} ({metrics['high_rewards']/metrics['total_tasks']*100:.1f}%)")
    print(f"  Medium (0-0.7):   {metrics['medium_rewards']} ({metrics['medium_rewards']/metrics['total_tasks']*100:.1f}%)")
    print(f"  Low (0 to -0.5):  {metrics['low_rewards']} ({metrics['low_rewards']/metrics['total_tasks']*100:.1f}%)")
    print(f"  Negative (<-0.5): {metrics['negative_rewards']} ({metrics['negative_rewards']/metrics['total_tasks']*100:.1f}%)")
    print()

    # Show baseline comparison
    baseline_accuracy = 0.50  # Random guessing
    improvement = (metrics['accuracy'] - baseline_accuracy) / baseline_accuracy * 100

    print("Baseline Comparison:")
    print(f"  Baseline (random): 50.0%")
    print(f"  Current accuracy:  {metrics['accuracy'] * 100:.2f}%")
    print(f"  Improvement:       {improvement:+.1f}%")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Market Analyst performance"
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to validation dataset JSON file"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Evaluate only N random samples (for quick testing)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results for each task"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Save results to JSON file"
    )

    args = parser.parse_args()

    # Load dataset
    print(f"Loading dataset from {args.dataset}...")
    with open(args.dataset, 'r') as f:
        tasks = json.load(f)

    print(f"Loaded {len(tasks)} tasks")

    # Sample if requested
    if args.sample:
        import random
        random.seed(42)
        tasks = random.sample(tasks, min(args.sample, len(tasks)))
        print(f"Sampled {len(tasks)} tasks for evaluation")

    # Create agent
    agent = LitMarketAnalyst()

    # Evaluate
    metrics = evaluate_dataset(
        agent=agent,
        tasks=tasks,
        verbose=args.verbose
    )

    # Print report
    print_report(metrics)

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove detailed results for cleaner output
        save_metrics = {k: v for k, v in metrics.items() if k != "results"}

        with open(output_path, 'w') as f:
            json.dump(save_metrics, f, indent=2)

        print(f"\n✓ Results saved to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
