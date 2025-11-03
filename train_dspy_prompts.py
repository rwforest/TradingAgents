"""
Train DSPy Prompt Optimizer using historical trading reports.

This script:
1. Loads high-quality historical reports as training examples
2. Uses DSPy's BootstrapFewShot to optimize prompts
3. Saves optimized prompts for use in production

Usage:
    python train_dspy_prompts.py --analyst market --examples 10
"""

import argparse
import dspy
from pathlib import Path
from tradingagents.agents.dspy_optimizer import (
    AnalystPromptOptimizer,
    create_training_example_from_report
)
from tradingagents.dataflows.config import get_config


def create_sample_training_data(analyst_type: str, num_examples: int = 5):
    """
    Create sample training data for demonstration.

    In production, this would load from historical reports.
    """
    examples = []

    # Sample high-quality reports (these would come from analysis_results/)
    sample_contexts = {
        "market": [
            {
                "ticker": "MSFT",
                "date": "2025-10-29",
                "system_instructions": "Analyze market trends using technical indicators",
                "tool_names": "get_stock_data, get_indicators",
                "context": "Previous analysis shows uptrend",
                "report": """Based on the 50-day and 200-day moving averages, MSFT is showing a golden cross pattern with the 50-day MA ($513.15) crossing above the 200-day MA ($460.13). The RSI at 65 indicates bullish momentum without being overbought. Volume analysis shows institutional accumulation with average volume up 15% over the past week.

Key Technical Levels:
- Support: $500 (50-day MA)
- Resistance: $555 (52-week high)
- Entry Zone: $510-520
- Stop Loss: $485

The MACD histogram is expanding positively, confirming the uptrend strength."""
            }
        ],
        "fundamentals": [
            {
                "ticker": "MSFT",
                "date": "2025-10-29",
                "system_instructions": "Analyze company fundamentals and financials",
                "tool_names": "get_company_info, get_fundamentals, get_balance_sheet",
                "context": "Q1 earnings recently announced",
                "report": """Company Info Analysis:
- Current Price: $541.55
- P/E Ratio: 39.67 (above sector average of 28, suggesting premium valuation)
- Analyst Consensus: Strong Buy (1.22/5.0)
- Target Price Range: $483-730 (mean $621)

Financial Health (Q1 2025):
- Revenue Growth: +16% YoY ($61.9B)
- Net Income Margin: 36.15% (excellent profitability)
- Earnings Growth: +23.6% YoY
- Free Cash Flow: $23.2B (strong cash generation)

Balance Sheet Strength:
- Cash & Equivalents: $80.2B
- Total Debt: $97.1B (manageable at 1.2x)
- Debt-to-Equity: 0.42 (healthy leverage)

The premium P/E is justified by: (1) strong 23.6% earnings growth, (2) expanding margins in cloud segment, (3) leadership in AI infrastructure."""
            }
        ]
    }

    # Get samples for this analyst type
    samples = sample_contexts.get(analyst_type, [])

    for i, sample in enumerate(samples[:num_examples]):
        example = create_training_example_from_report(
            ticker=sample["ticker"],
            date=sample["date"],
            system_instructions=sample["system_instructions"],
            tool_names=sample["tool_names"],
            context=sample["context"],
            expected_report=sample["report"]
        )
        examples.append(example)

    return examples


def quality_metric(example, prediction, trace=None):
    """
    Evaluate the quality of a generated report.

    Args:
        example: The training example
        prediction: The model's prediction
        trace: Optional execution trace

    Returns:
        Score between 0 and 1
    """
    report = prediction.report if hasattr(prediction, 'report') else ""

    score = 0.0

    # Check length (good reports are detailed)
    if len(report) > 300:
        score += 0.2

    # Check for key analysis elements
    analysis_keywords = ['analysis', 'trend', 'indicator', 'support', 'resistance']
    if any(kw in report.lower() for kw in analysis_keywords):
        score += 0.2

    # Check for specific numbers/data (shows it used tools)
    if any(char.isdigit() for char in report):
        score += 0.2

    # Check for actionable insights
    action_keywords = ['recommend', 'suggest', 'buy', 'sell', 'hold', 'entry', 'exit']
    if any(kw in report.lower() for kw in action_keywords):
        score += 0.2

    # Check for structured formatting (tables, bullet points)
    if '|' in report or '-' in report or '*' in report:
        score += 0.2

    return score


def train_analyst_optimizer(analyst_type: str, num_examples: int = 5):
    """
    Train the DSPy optimizer for a specific analyst type.

    Args:
        analyst_type: Type of analyst (market, fundamentals, news, social_media)
        num_examples: Number of training examples to use
    """
    config = get_config()

    # Get LLM model name from config
    llm_model = config.get("quick_think_llm", "gpt-4o-mini")

    print(f"\n{'='*60}")
    print(f"Training DSPy Optimizer for {analyst_type.upper()} Analyst")
    print(f"{'='*60}\n")

    # Initialize optimizer
    optimizer = AnalystPromptOptimizer(
        llm_model_name=llm_model,
        analyst_type=analyst_type
    )

    # Load or create training data
    print(f"Loading training examples...")
    training_examples = create_sample_training_data(analyst_type, num_examples)
    print(f"✓ Loaded {len(training_examples)} training examples\n")

    if len(training_examples) == 0:
        print(f"⚠ No training examples found for {analyst_type} analyst")
        print("  Create high-quality example reports first.")
        return

    # Optimize prompts
    print("Starting prompt optimization...")
    print("This may take several minutes...\n")

    try:
        optimized_module = optimizer.optimize_with_examples(
            training_examples=training_examples,
            metric_fn=quality_metric
        )

        print(f"\n{'='*60}")
        print(f"✓ Optimization Complete!")
        print(f"{'='*60}\n")
        print(f"Optimized prompts saved to: data/dspy_cache/{analyst_type}_optimized.json")
        print(f"\nTo use optimized prompts, set environment variable:")
        print(f"  export USE_DSPY_OPTIMIZATION=true")

    except Exception as e:
        print(f"\n❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Train DSPy prompt optimizer for trading analysts"
    )
    parser.add_argument(
        "--analyst",
        type=str,
        choices=["market", "fundamentals", "news", "social_media", "all"],
        default="market",
        help="Which analyst to optimize (default: market)"
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=5,
        help="Number of training examples to use (default: 5)"
    )

    args = parser.parse_args()

    if args.analyst == "all":
        analysts = ["market", "fundamentals", "news", "social_media"]
    else:
        analysts = [args.analyst]

    for analyst_type in analysts:
        train_analyst_optimizer(analyst_type, args.examples)
        print("\n")


if __name__ == "__main__":
    main()
