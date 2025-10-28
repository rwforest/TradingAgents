"""
Rate-limited LLM wrapper for Databricks models
"""
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from .rate_limiter import get_rate_limiter
from .context_limiter import estimate_message_tokens


class RateLimitedLLM:
    """
    Wrapper around LLM that adds automatic rate limiting.
    """

    def __init__(self, llm: BaseChatModel, model_name: str, enable_rate_limiting: bool = True, verbose: bool = False):
        """
        Initialize rate-limited LLM wrapper.

        Args:
            llm: The underlying LLM to wrap
            model_name: Name of the model (for rate limiting)
            enable_rate_limiting: Whether to enable rate limiting
            verbose: Whether to print rate limiting messages
        """
        self.llm = llm
        self.model_name = model_name
        self.enable_rate_limiting = enable_rate_limiting
        self.verbose = verbose
        self.rate_limiter = get_rate_limiter() if enable_rate_limiting else None

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Invoke the LLM with rate limiting.

        Args:
            input: Input to the LLM (messages, prompt, etc.)
            config: Optional configuration
            **kwargs: Additional arguments

        Returns:
            LLM response
        """
        if self.enable_rate_limiting and self.rate_limiter:
            # Estimate tokens from input
            estimated_tokens = 1000  # Default estimate

            if isinstance(input, list):
                # List of messages
                estimated_tokens = estimate_message_tokens(input)
            elif isinstance(input, str):
                # String prompt
                estimated_tokens = len(input) // 4  # Rough estimate
            elif hasattr(input, 'messages'):
                # Has messages attribute
                estimated_tokens = estimate_message_tokens(input.messages)

            # Add safety margin for output tokens (assume 1K output)
            estimated_tokens += 1000

            # Wait if needed due to rate limit
            self.rate_limiter.wait_if_needed(
                self.model_name,
                estimated_tokens,
                verbose=self.verbose
            )

        # Call the actual LLM
        return self.llm.invoke(input, config, **kwargs)

    def generate(self, messages: List[List[BaseMessage]], stop: Optional[List[str]] = None, **kwargs) -> ChatResult:
        """
        Generate responses with rate limiting.

        Args:
            messages: List of message lists
            stop: Stop sequences
            **kwargs: Additional arguments

        Returns:
            Chat result
        """
        if self.enable_rate_limiting and self.rate_limiter:
            # Estimate tokens
            total_tokens = sum(estimate_message_tokens(msg_list) for msg_list in messages)
            total_tokens += 1000 * len(messages)  # Add output estimate

            self.rate_limiter.wait_if_needed(
                self.model_name,
                total_tokens,
                verbose=self.verbose
            )

        return self.llm.generate(messages, stop, **kwargs)

    def bind_tools(self, tools: list):
        """
        Bind tools to the LLM and return a new rate-limited instance.

        Args:
            tools: List of tools to bind

        Returns:
            New rate-limited LLM with tools bound
        """
        bound_llm = self.llm.bind_tools(tools)
        return RateLimitedLLM(
            bound_llm,
            self.model_name,
            self.enable_rate_limiting,
            self.verbose
        )

    def __getattr__(self, name):
        """
        Delegate other attributes to the underlying LLM.
        """
        return getattr(self.llm, name)


def wrap_with_rate_limiting(
    llm: BaseChatModel,
    model_name: str,
    enable: bool = True,
    verbose: bool = False
) -> BaseChatModel:
    """
    Wrap an LLM with rate limiting if enabled.

    Args:
        llm: The LLM to wrap
        model_name: Name of the model
        enable: Whether to enable rate limiting
        verbose: Whether to print rate limiting messages

    Returns:
        Rate-limited LLM or original LLM if not enabled
    """
    if enable:
        return RateLimitedLLM(llm, model_name, enable, verbose)
    return llm
