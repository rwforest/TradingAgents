"""
Agent Lightning wrapper for Market Analyst.

This module provides a LitAgent wrapper around the TradingAgents Market Analyst
to enable reinforcement learning optimization via Agent Lightning.
"""

from typing import Dict, Any, Optional
import re


class LitMarketAnalyst:
    """
    Agent Lightning wrapper for Market Analyst.

    This agent learns to make better BUY/HOLD/SELL recommendations by
    optimizing technical indicator usage and interpretation.

    Note: This is a simplified version that doesn't require agentlightning
    to be installed yet. It provides the structure for future integration.
    """

    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LitMarketAnalyst.

        Args:
            llm_config: Optional LLM configuration override
        """
        self.llm_config = llm_config or {}

    def rollout(
        self,
        task: Dict[str, Any],
        resources: Optional[Dict[str, Any]] = None,
        rollout: Optional[Any] = None
    ) -> float:
        """
        Execute a single rollout of the market analyst.

        Args:
            task: Task dictionary containing:
                - symbol: Stock ticker (e.g., "MSFT")
                - trade_date: Date of analysis (e.g., "2025-10-29")
                - expected_return: Actual future return (ground truth)
            resources: Named resources provided by Agent Lightning
            rollout: Rollout context from Agent Lightning

        Returns:
            Reward signal (float) based on recommendation quality
        """
        # For now, use standard TradingAgents workflow
        # When Agent Lightning is integrated, we'll use optimized LLM from resources
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        config = DEFAULT_CONFIG.copy()

        # Create graph with only market analyst
        ta = TradingAgentsGraph(
            debug=False,
            config=config,
            selected_analysts=["market"]
        )

        # Run analysis
        try:
            final_state, decision = ta.propagate(
                symbol=task["symbol"],
                trade_date=task["trade_date"]
            )

            # Extract market report
            market_report = final_state.get("market_report", "")

            # Calculate reward based on recommendation quality
            reward = self._calculate_reward(
                market_report=market_report,
                expected_return=task["expected_return"]
            )

            return reward

        except Exception as e:
            print(f"Error in rollout for {task['symbol']} on {task['trade_date']}: {e}")
            return -0.5  # Penalty for failures

    def _extract_recommendation(self, report: str) -> str:
        """
        Extract BUY/HOLD/SELL recommendation from market report.

        Args:
            report: Market analyst report text

        Returns:
            "BUY", "HOLD", "SELL", or "UNKNOWN"
        """
        if not report:
            return "UNKNOWN"

        report_upper = report.upper()

        # Look for explicit recommendation patterns
        patterns = [
            r'FINAL TRANSACTION PROPOSAL:\s*\*\*([A-Z]+)\*\*',
            r'RECOMMENDATION:\s*\*\*([A-Z]+)\*\*',
            r'DECISION:\s*\*\*([A-Z]+)\*\*',
            r'\*\*([A-Z]+)\*\*(?:\s*(?:RECOMMENDATION|DECISION))?'
        ]

        for pattern in patterns:
            match = re.search(pattern, report_upper)
            if match:
                rec = match.group(1).strip()
                if rec in ["BUY", "SELL", "HOLD"]:
                    return rec

        # Fallback: count sentiment keywords
        buy_keywords = report_upper.count("BUY") + report_upper.count("BULLISH") + report_upper.count("STRONG MOMENTUM")
        sell_keywords = report_upper.count("SELL") + report_upper.count("BEARISH") + report_upper.count("WEAK MOMENTUM")

        if buy_keywords > sell_keywords and buy_keywords > 0:
            return "BUY"
        elif sell_keywords > buy_keywords and sell_keywords > 0:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_reward(
        self,
        market_report: str,
        expected_return: float
    ) -> float:
        """
        Calculate reward based on recommendation accuracy.

        Reward structure:
        - Correct BUY (return > 2%): +1.0
        - Correct HOLD (|return| < 2%): +0.7
        - Correct SELL (return < -2%): +0.8
        - Wrong BUY (return < 0): -1.0
        - Wrong SELL (return > 0): -0.8
        - Marginal cases: -0.3

        Args:
            market_report: The analyst's report text
            expected_return: Actual future return (e.g., 0.05 for 5% gain)

        Returns:
            Reward value between -1.0 and +1.0
        """
        recommendation = self._extract_recommendation(market_report)

        # Define thresholds
        strong_positive = 0.02  # 2% gain
        strong_negative = -0.02  # 2% loss

        if recommendation == "BUY":
            if expected_return > strong_positive:
                return 1.0  # Correct buy, strong gain
            elif expected_return > 0:
                return 0.5  # Correct direction, modest gain
            else:
                return -1.0  # Wrong, loss

        elif recommendation == "SELL":
            if expected_return < strong_negative:
                return 0.8  # Correct sell, avoided loss
            elif expected_return < 0:
                return 0.4  # Correct direction, modest loss avoided
            else:
                return -0.8  # Wrong, missed gain

        elif recommendation == "HOLD":
            if abs(expected_return) < abs(strong_positive):
                return 0.7  # Correct hold, low volatility
            else:
                return -0.3  # Missed opportunity (should have bought/sold)

        else:  # UNKNOWN
            return -0.5  # Penalty for indecisiveness

    def __call__(self, task: Dict[str, Any]) -> float:
        """Allow direct calling of the agent."""
        return self.rollout(task)


# Future integration point for full Agent Lightning support
try:
    import agentlightning as agl

    class LitMarketAnalystFull(agl.LitAgent[Dict[str, Any]]):
        """
        Full Agent Lightning integration (requires agentlightning package).

        This will be the production version once Agent Lightning is installed.
        """

        def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
            super().__init__()
            self.llm_config = llm_config or {}

        def rollout(
            self,
            task: Dict[str, Any],
            resources: agl.NamedResources,
            rollout: agl.Rollout
        ) -> float:
            """Execute rollout with Agent Lightning resources."""
            # Extract optimized LLM from resources
            llm: agl.LLM = resources.get("main_llm")

            if llm:
                # Use optimized LLM endpoint
                from langchain_openai import ChatOpenAI

                optimized_llm = ChatOpenAI(
                    base_url=llm.get_base_url(
                        rollout.rollout_id,
                        rollout.attempt.attempt_id
                    ),
                    model=llm.model,
                    api_key=llm.api_key or "dummy-key",
                    **llm.sampling_parameters
                )

                # TODO: Inject optimized_llm into market analyst
                # For now, fall back to standard implementation

            # Use the base implementation
            agent = LitMarketAnalyst(self.llm_config)
            return agent.rollout(task, resources, rollout)

except ImportError:
    # Agent Lightning not installed yet
    LitMarketAnalystFull = None
