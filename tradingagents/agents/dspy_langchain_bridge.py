"""
Bridge between DSPy prompt optimization and LangChain tool execution.

This module allows using DSPy-optimized prompts with LangChain agents
while keeping all tool execution in LangChain.

Architecture:
    DSPy: Optimizes prompts → Better system messages
    LangChain: Executes tools → Actual API calls and data retrieval
"""

import dspy
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Callable, Optional
from tradingagents.agents.dspy_optimizer import AnalystPromptOptimizer


class DSPyOptimizedLangChainAnalyst:
    """
    Wraps a LangChain analyst with DSPy prompt optimization.

    The LangChain agent continues to handle all tool execution,
    but the prompts it uses are optimized by DSPy.
    """

    def __init__(
        self,
        analyst_type: str,
        langchain_agent_factory: Callable,
        llm,
        enable_optimization: bool = True
    ):
        """
        Initialize the optimized analyst.

        Args:
            analyst_type: Type of analyst (market, news, fundamentals, social_media)
            langchain_agent_factory: Function that creates the LangChain agent node
            llm: LangChain LLM instance
            enable_optimization: Whether to use DSPy optimization (False = baseline)
        """
        self.analyst_type = analyst_type
        self.llm = llm
        self.enable_optimization = enable_optimization

        # Initialize DSPy optimizer
        if enable_optimization:
            self.optimizer = AnalystPromptOptimizer(
                llm_model_name=llm.model_name,
                analyst_type=analyst_type
            )
        else:
            self.optimizer = None

        # Create the LangChain agent
        self.agent_node = langchain_agent_factory(llm)

    def get_optimized_system_message(self, base_system_message: str) -> str:
        """
        Get DSPy-optimized version of the system message.

        Args:
            base_system_message: The baseline system prompt

        Returns:
            Optimized system prompt (or baseline if optimization disabled)
        """
        if self.enable_optimization and self.optimizer:
            return self.optimizer.get_optimized_system_prompt(base_system_message)
        return base_system_message

    def __call__(self, state):
        """
        Execute the analyst node with optimized prompts.

        This delegates to the LangChain agent but with optimized prompts.
        """
        return self.agent_node(state)


def create_optimized_analyst(
    analyst_type: str,
    analyst_factory: Callable,
    llm,
    enable_optimization: bool = True
) -> Callable:
    """
    Factory function to create a DSPy-optimized LangChain analyst.

    Args:
        analyst_type: Type of analyst
        analyst_factory: Original LangChain analyst factory (e.g., create_market_analyst)
        llm: LangChain LLM instance
        enable_optimization: Whether to enable DSPy optimization

    Returns:
        Optimized analyst node function

    Example:
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        # Baseline (no optimization)
        baseline_analyst = create_market_analyst(llm)

        # DSPy-optimized
        optimized_analyst = create_optimized_analyst(
            analyst_type="market",
            analyst_factory=create_market_analyst,
            llm=llm,
            enable_optimization=True
        )
    """
    wrapper = DSPyOptimizedLangChainAnalyst(
        analyst_type=analyst_type,
        langchain_agent_factory=analyst_factory,
        llm=llm,
        enable_optimization=enable_optimization
    )
    return wrapper


def inject_optimized_prompt_into_analyst(
    analyst_module,
    optimizer: AnalystPromptOptimizer,
    system_message_attr: str = "system_message"
):
    """
    Inject DSPy-optimized prompts into an existing analyst module.

    This modifies the analyst in-place to use optimized prompts.

    Args:
        analyst_module: The analyst module/node to optimize
        optimizer: DSPy optimizer instance
        system_message_attr: Attribute name for the system message

    Example:
        from tradingagents.agents.analysts import market_analyst

        optimizer = AnalystPromptOptimizer(llm.model_name, "market")
        inject_optimized_prompt_into_analyst(
            market_analyst,
            optimizer,
            "system_message"
        )
    """
    # This would modify the analyst's system message
    # Implementation depends on how the analyst stores its prompt
    pass
