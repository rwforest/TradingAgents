"""
Rate limiter for Databricks Foundation Model APIs
Based on: https://learn.microsoft.com/en-us/azure/databricks/machine-learning/foundation-model-apis/limits
"""
import time
from functools import wraps
from threading import Lock
from datetime import datetime, timedelta
from typing import Dict, Optional


class RateLimiter:
    """
    Rate limiter that respects Databricks Foundation Model API limits.

    Databricks Rate Limits (as of 2024):
    - Pay-per-token endpoints:
      * 150 requests per minute (RPM)
      * 300,000 tokens per minute (TPM)
    - Provisioned throughput endpoints:
      * Custom limits based on provisioned capacity
    """

    def __init__(self):
        self.call_history: Dict[str, list] = {}  # model_name -> [timestamp, timestamp, ...]
        self.token_history: Dict[str, list] = {}  # model_name -> [(timestamp, tokens), ...]
        self.lock = Lock()

        # Rate limits per model
        # Provisioned throughput endpoints (_pro suffix) have much higher limits
        self.rate_limits = {
            # === PROVISIONED THROUGHPUT ENDPOINTS (_pro suffix) ===
            # Up to 200 queries per second per workspace
            # No TPM restrictions - capacity based on provisioned resources
            "provisioned": {
                "rpm": 12000,  # 200 queries/sec * 60 = 12000/min (workspace limit)
                "tpm": 999999999,  # No TPM limit for provisioned
                "delay_between_calls": 0.005,  # 5ms (much faster than pay-per-token)
            },

            # === PAY-PER-TOKEN ENDPOINTS (standard) ===
            # Claude models (pay-per-token)
            "databricks-claude-sonnet-4-5": {
                "rpm": 150,  # requests per minute
                "tpm": 300000,  # tokens per minute
                "delay_between_calls": 0.4,  # 400ms (150 RPM = ~2.5 RPS)
            },
            "databricks-claude-3-5-sonnet": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            "databricks-claude-haiku-3-5": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            "databricks-claude-opus-4-5": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            # Llama models (pay-per-token)
            "databricks-meta-llama-3-3-70b-instruct": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            "databricks-meta-llama-3-1-405b-instruct": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            "databricks-meta-llama-3-1-70b-instruct": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            # DBRX models
            "databricks-dbrx-instruct": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            # Mixtral models
            "databricks-mixtral-8x7b-instruct": {
                "rpm": 150,
                "tpm": 300000,
                "delay_between_calls": 0.4,
            },
            # BGE embedding models (higher limits)
            "databricks-bge-large-en": {
                "rpm": 300,
                "tpm": 500000,
                "delay_between_calls": 0.2,
            },
            # Default fallback
            "default": {
                "rpm": 100,  # Conservative
                "tpm": 200000,
                "delay_between_calls": 0.6,
            }
        }

    def get_model_limits(self, model_name: str) -> dict:
        """Get rate limits for a specific model."""
        # Check if this is a provisioned throughput endpoint (_pro suffix)
        if model_name.endswith("_pro") or "_pro" in model_name.lower():
            return self.rate_limits["provisioned"]

        # Try exact match first
        if model_name in self.rate_limits:
            return self.rate_limits[model_name]

        # Try partial match
        for key in self.rate_limits.keys():
            if key in model_name.lower() and key != "provisioned":
                return self.rate_limits[key]

        # Return default
        return self.rate_limits["default"]

    def _clean_old_history(self, model_name: str):
        """Remove history older than 1 minute."""
        cutoff = datetime.now() - timedelta(minutes=1)

        with self.lock:
            if model_name in self.call_history:
                self.call_history[model_name] = [
                    ts for ts in self.call_history[model_name]
                    if ts > cutoff
                ]

            if model_name in self.token_history:
                self.token_history[model_name] = [
                    (ts, tokens) for ts, tokens in self.token_history[model_name]
                    if ts > cutoff
                ]

    def check_rate_limit(self, model_name: str, estimated_tokens: int = 1000) -> Optional[float]:
        """
        Check if we're at rate limit and return how long to wait.

        Args:
            model_name: Name of the model
            estimated_tokens: Estimated tokens for this request

        Returns:
            Seconds to wait, or None if no wait needed
        """
        self._clean_old_history(model_name)
        limits = self.get_model_limits(model_name)

        with self.lock:
            # Check RPM limit
            if model_name in self.call_history:
                recent_calls = len(self.call_history[model_name])
                if recent_calls >= limits["rpm"]:
                    # We're at RPM limit, need to wait
                    oldest_call = min(self.call_history[model_name])
                    wait_until = oldest_call + timedelta(minutes=1)
                    wait_seconds = (wait_until - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        return wait_seconds

            # Check TPM limit
            if model_name in self.token_history:
                recent_tokens = sum(tokens for _, tokens in self.token_history[model_name])
                if recent_tokens + estimated_tokens > limits["tpm"]:
                    # We're at TPM limit, need to wait
                    oldest_token_call = min(ts for ts, _ in self.token_history[model_name])
                    wait_until = oldest_token_call + timedelta(minutes=1)
                    wait_seconds = (wait_until - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        return wait_seconds

        return None

    def record_call(self, model_name: str, tokens_used: int = 1000):
        """Record a successful API call."""
        now = datetime.now()

        with self.lock:
            if model_name not in self.call_history:
                self.call_history[model_name] = []
            if model_name not in self.token_history:
                self.token_history[model_name] = []

            self.call_history[model_name].append(now)
            self.token_history[model_name].append((now, tokens_used))

    def wait_if_needed(self, model_name: str, estimated_tokens: int = 1000, verbose: bool = False):
        """
        Wait if we're at rate limit, then record the call.

        Args:
            model_name: Name of the model
            estimated_tokens: Estimated tokens for this request
            verbose: Whether to print wait messages
        """
        wait_seconds = self.check_rate_limit(model_name, estimated_tokens)

        if wait_seconds and wait_seconds > 0:
            if verbose:
                print(f"[Rate Limiter] Waiting {wait_seconds:.1f}s for {model_name} (rate limit)")
            time.sleep(wait_seconds)

        # Add minimum delay between calls
        limits = self.get_model_limits(model_name)
        min_delay = limits["delay_between_calls"]

        if verbose:
            print(f"[Rate Limiter] Delay {min_delay}s between calls for {model_name}")

        time.sleep(min_delay)
        self.record_call(model_name, estimated_tokens)


# Global rate limiter instance
_global_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _global_rate_limiter


def rate_limited(model_name_arg: str = "model", estimated_tokens: int = 1000, verbose: bool = False):
    """
    Decorator to add rate limiting to a function.

    Args:
        model_name_arg: Name of the argument that contains the model name
        estimated_tokens: Default estimated tokens
        verbose: Whether to print rate limit messages

    Example:
        @rate_limited(model_name_arg="model", estimated_tokens=2000)
        def call_llm(model, prompt):
            return llm.invoke(prompt)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()

            # Try to extract model name from args/kwargs
            model_name = kwargs.get(model_name_arg, "default")

            # Estimate tokens if possible
            tokens = estimated_tokens
            if "prompt" in kwargs and isinstance(kwargs["prompt"], str):
                # Rough estimate: 1 token ≈ 4 characters
                tokens = len(kwargs["prompt"]) // 4

            # Wait if needed
            limiter.wait_if_needed(model_name, tokens, verbose)

            # Call the function
            return func(*args, **kwargs)

        return wrapper
    return decorator


# Convenience function for manual rate limiting
def wait_for_rate_limit(model_name: str, estimated_tokens: int = 1000, verbose: bool = True):
    """
    Manually wait for rate limit before making an API call.

    Example:
        wait_for_rate_limit("databricks-claude-sonnet-4-5", estimated_tokens=5000)
        response = llm.invoke(prompt)
    """
    limiter = get_rate_limiter()
    limiter.wait_if_needed(model_name, estimated_tokens, verbose)
