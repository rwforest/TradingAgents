"""
DSPy Prompt Optimization Layer for Trading Analysts

This module provides prompt optimization using DSPy while keeping LangChain
for tool execution. The architecture is:

1. LangChain agents execute tools and handle orchestration
2. DSPy optimizes the prompts used by those agents
3. Optimized prompts are saved and reused

Usage:
    optimizer = AnalystPromptOptimizer(llm, analyst_type="market")
    optimized_prompt = optimizer.get_optimized_prompt()
"""

import dspy
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime


class TradingAnalystSignature(dspy.Signature):
    """Signature for trading analyst reports."""
    system_instructions = dspy.InputField(desc="The system instructions for the analyst")
    tool_names = dspy.InputField(desc="Available tools")
    current_date = dspy.InputField(desc="Current trading date")
    ticker = dspy.InputField(desc="Stock ticker symbol")
    context = dspy.InputField(desc="Previous messages and context")

    report = dspy.OutputField(desc="Comprehensive analyst report with insights and recommendations")


class AnalystReportModule(dspy.Module):
    """DSPy module for generating analyst reports."""

    def __init__(self):
        super().__init__()
        self.generate_report = dspy.ChainOfThought(TradingAnalystSignature)

    def forward(self, system_instructions, tool_names, current_date, ticker, context):
        """Generate an optimized analyst report."""
        prediction = self.generate_report(
            system_instructions=system_instructions,
            tool_names=tool_names,
            current_date=current_date,
            ticker=ticker,
            context=context
        )
        return dspy.Prediction(report=prediction.report)


class AnalystPromptOptimizer:
    """
    Optimizes prompts for trading analysts using DSPy.

    This keeps LangChain for tool execution while using DSPy to improve
    the prompts through techniques like BootstrapFewShot.
    """

    def __init__(
        self,
        llm_model_name: str,
        analyst_type: str,
        cache_dir: str = "data/dspy_cache"
    ):
        """
        Initialize the optimizer.

        Args:
            llm_model_name: Name of the LLM model to use
            analyst_type: Type of analyst (market, news, fundamentals, social_media)
            cache_dir: Directory to cache optimized prompts
        """
        self.analyst_type = analyst_type
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configure DSPy with the LLM
        # Add provider prefix if not present
        import os
        if '/' not in llm_model_name:
            provider = os.getenv("LLM_PROVIDER", "openai")
            if provider == "databricks":
                llm_model_name = f"databricks/{llm_model_name}"
            elif provider == "anthropic":
                llm_model_name = f"anthropic/{llm_model_name}"

        self.lm = dspy.LM(model=llm_model_name)
        dspy.configure(lm=self.lm)

        # Create the module
        self.module = AnalystReportModule()

        # Load optimized prompts if available
        self.optimized_prompts = self._load_cached_prompts()

    def _load_cached_prompts(self) -> Optional[Dict]:
        """Load previously optimized prompts from cache."""
        cache_file = self.cache_dir / f"{self.analyst_type}_optimized.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None

    def _save_optimized_prompts(self, prompts: Dict):
        """Save optimized prompts to cache."""
        cache_file = self.cache_dir / f"{self.analyst_type}_optimized.json"
        with open(cache_file, 'w') as f:
            json.dump(prompts, f, indent=2)

    def optimize_with_examples(
        self,
        training_examples: List[dspy.Example],
        metric_fn=None
    ):
        """
        Optimize prompts using training examples.

        Args:
            training_examples: List of dspy.Example with inputs and expected outputs
            metric_fn: Optional metric function to evaluate quality
        """
        # Default metric: check if report contains key elements
        if metric_fn is None:
            def default_metric(example, prediction, trace=None):
                # Check if report has minimum length and key sections
                report = prediction.report if hasattr(prediction, 'report') else ""
                has_length = len(report) > 200
                has_analysis = any(keyword in report.lower() for keyword in
                                 ['analysis', 'recommend', 'insight', 'trend'])
                return has_length and has_analysis
            metric_fn = default_metric

        # Use BootstrapFewShot optimizer
        optimizer = dspy.BootstrapFewShot(
            metric=metric_fn,
            max_bootstrapped_demos=4,
            max_labeled_demos=4
        )

        # Compile the module with optimization
        print(f"Optimizing {self.analyst_type} analyst prompts...")
        compiled_module = optimizer.compile(
            self.module,
            trainset=training_examples
        )

        # Save the optimized prompts
        self.module = compiled_module
        self._save_optimized_prompts({
            'analyst_type': self.analyst_type,
            'optimized_at': datetime.now().isoformat(),
            'num_examples': len(training_examples)
        })

        print(f"✓ Optimized prompts saved for {self.analyst_type} analyst")
        return compiled_module

    def get_optimized_system_prompt(self, base_prompt: str) -> str:
        """
        Get an optimized version of the system prompt.

        Args:
            base_prompt: The base system prompt

        Returns:
            Optimized prompt (or base prompt if not yet optimized)
        """
        if self.optimized_prompts:
            # If we have optimized prompts, they're embedded in the module
            # For now, return the base prompt with optimization metadata
            return f"{base_prompt}\n\n<!-- DSPy Optimized: {self.optimized_prompts.get('optimized_at', 'unknown')} -->"
        return base_prompt

    def generate_report(
        self,
        system_instructions: str,
        tool_names: str,
        current_date: str,
        ticker: str,
        context: str
    ) -> str:
        """
        Generate a report using the optimized module.

        This can be used to test the optimization before integrating
        with LangChain.
        """
        prediction = self.module(
            system_instructions=system_instructions,
            tool_names=tool_names,
            current_date=current_date,
            ticker=ticker,
            context=context
        )
        return prediction.report


def create_training_example_from_report(
    ticker: str,
    date: str,
    system_instructions: str,
    tool_names: str,
    context: str,
    expected_report: str
) -> dspy.Example:
    """
    Create a DSPy training example from a historical report.

    Args:
        ticker: Stock ticker
        date: Trading date
        system_instructions: System prompt used
        tool_names: Available tools
        context: Context/messages
        expected_report: The high-quality report to learn from

    Returns:
        A DSPy Example for training
    """
    return dspy.Example(
        system_instructions=system_instructions,
        tool_names=tool_names,
        current_date=date,
        ticker=ticker,
        context=context,
        report=expected_report
    ).with_inputs("system_instructions", "tool_names", "current_date", "ticker", "context")


def load_historical_reports_as_training_data(
    reports_dir: str = "analysis_results",
    analyst_type: str = "market",
    min_quality_score: float = 0.8
) -> List[dspy.Example]:
    """
    Load historical reports as training data for DSPy optimization.

    Args:
        reports_dir: Directory containing historical reports
        analyst_type: Type of analyst to load reports for
        min_quality_score: Minimum quality score for including reports

    Returns:
        List of DSPy Examples
    """
    # TODO: Implement loading logic
    # This would parse historical markdown reports and extract:
    # - The inputs (ticker, date, context)
    # - The outputs (the analyst section)
    # - Quality metrics (user ratings, trade outcomes, etc.)

    training_examples = []

    # Placeholder: In real implementation, scan reports_dir
    # and extract high-quality examples

    return training_examples
