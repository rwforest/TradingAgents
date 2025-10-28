"""
Context limiter to prevent token overflow in TradingAgents
"""
from typing import List
import tiktoken


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate the number of tokens in a text string.

    Args:
        text: The text to count tokens for
        model: Model name for tokenizer (default: gpt-4, works for Claude too)

    Returns:
        Estimated token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for Claude/unknown models
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def estimate_message_tokens(messages: List) -> int:
    """
    Estimate total tokens in a list of messages.

    Args:
        messages: List of message tuples or objects

    Returns:
        Total estimated token count
    """
    total_tokens = 0

    for message in messages:
        # Handle different message formats
        if isinstance(message, tuple):
            # Format: ("role", "content")
            total_tokens += estimate_tokens(str(message[1]))
        elif hasattr(message, 'content'):
            # LangChain message object
            total_tokens += estimate_tokens(str(message.content))
        else:
            # Fallback: convert to string
            total_tokens += estimate_tokens(str(message))

    return total_tokens


def trim_messages_to_token_limit(
    messages: List,
    max_tokens: int = 100000,
    preserve_first: bool = True,
    preserve_last: int = 10
) -> List:
    """
    Trim messages to stay under a token limit.

    Args:
        messages: List of messages to trim
        max_tokens: Maximum number of tokens to keep (default: 100K)
        preserve_first: Always keep the first message (typically the initial query)
        preserve_last: Number of most recent messages to always keep (default: 10 to preserve tool call pairs)

    Returns:
        Trimmed list of messages
    """
    if not messages:
        return messages

    # Calculate current token count
    current_tokens = estimate_message_tokens(messages)

    # If under limit, return as-is
    if current_tokens <= max_tokens:
        return messages

    # Build trimmed message list
    trimmed = []

    # Always preserve first message if requested
    if preserve_first and len(messages) > 0:
        trimmed.append(messages[0])

    # Calculate available tokens
    tokens_used = estimate_message_tokens(trimmed)
    available_tokens = max_tokens - tokens_used

    # Reserve tokens for last N messages
    last_messages = messages[-preserve_last:] if preserve_last > 0 else []
    last_tokens = estimate_message_tokens(last_messages)
    available_tokens -= last_tokens

    # Add middle messages while staying under budget
    middle_start = 1 if preserve_first else 0
    middle_end = len(messages) - preserve_last if preserve_last > 0 else len(messages)

    for i in range(middle_end - 1, middle_start - 1, -1):  # Add most recent first
        msg = messages[i]
        msg_tokens = estimate_tokens(str(msg[1]) if isinstance(msg, tuple) else str(msg.content))

        if tokens_used + msg_tokens <= available_tokens:
            trimmed.insert(1 if preserve_first else 0, msg)  # Insert after first or at start
            tokens_used += msg_tokens
        else:
            break

    # Add preserved last messages
    trimmed.extend(last_messages)

    # Optionally log the trimming (commented out to reduce output noise)
    # final_tokens = estimate_message_tokens(trimmed)
    # print(f"[Context Limiter] Trimmed {len(messages)} → {len(trimmed)} messages")
    # print(f"[Context Limiter] Tokens: {current_tokens:,} → {final_tokens:,} (limit: {max_tokens:,})")

    return trimmed


def get_safe_token_limit(model_name: str) -> int:
    """
    Get a safe token limit for a given model, leaving room for output.

    Args:
        model_name: Name of the model

    Returns:
        Safe input token limit
    """
    # Model context limits (conservative estimates)
    model_limits = {
        "claude-sonnet": 131072,  # 128K
        "claude-opus": 200000,    # 200K
        "claude-haiku": 200000,   # 200K
        "gpt-4": 128000,          # 128K
        "gpt-3.5": 16384,         # 16K
        "llama-3": 128000,        # 128K
    }

    # Check if provisioned throughput (_pro suffix)
    is_provisioned = model_name.endswith("_pro") or "_pro" in model_name.lower()

    # Find matching model limit
    context_limit = 100000  # Default conservative limit

    for key, limit in model_limits.items():
        if key in model_name.lower():
            context_limit = limit
            break

    # Provisioned throughput has no TPM restrictions
    # Reserve less for output (10% vs 20%)
    if is_provisioned:
        safe_limit = int(context_limit * 0.9)
    else:
        safe_limit = int(context_limit * 0.8)

    return safe_limit


def trim_messages_for_model(
    messages: List,
    model_name: str,
    custom_limit: int = None
) -> List:
    """
    Trim messages based on model capabilities.

    Args:
        messages: List of messages to trim
        model_name: Name of the model (to determine context limit)
        custom_limit: Optional custom token limit (overrides model default)

    Returns:
        Trimmed messages
    """
    if custom_limit:
        max_tokens = custom_limit
    else:
        max_tokens = get_safe_token_limit(model_name)

    return trim_messages_to_token_limit(
        messages,
        max_tokens=max_tokens,
        preserve_first=True,
        preserve_last=1
    )
