"""
Context limiter to prevent token overflow in TradingAgents
"""
from typing import List
import tiktoken
from langchain_core.messages import SystemMessage

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

def _summarize_messages(messages: List, model_name: str) -> str:
    """
    Summarize a list of messages using a quick model.
    """
    if not messages:
        return ""

    llm = get_llm(model_name)
    
    prompt = "Summarize the following conversation. Condense the key information, decisions, and data points into a concise paragraph. The summary will be used as context for a follow-up conversation, so it should be self-contained and easy to understand."
    
    summary_prompt = f"{prompt}\n\n---\n\n" + "\n".join([str(m.content) if hasattr(m, 'content') else str(m) for m in messages])

    response = llm.invoke(summary_prompt)
    return response.content

def trim_messages_to_token_limit(
    messages: List,
    max_tokens: int = 100000,
    preserve_first: bool = True,
    preserve_last: int = 10,
    summarize: bool = False,
    model_name: str = "claude-sonnet"
) -> List:
    """
    Trim messages to stay under a token limit, with optional summarization.

    Args:
        messages: List of messages to trim
        max_tokens: Maximum number of tokens to keep (default: 100K)
        preserve_first: Always keep the first message (typically the initial query)
        preserve_last: Number of most recent messages to always keep
        summarize: Whether to summarize dropped messages
        model_name: Model to use for summarization

    Returns:
        Trimmed list of messages
    """
    if not messages:
        return messages

    current_tokens = estimate_message_tokens(messages)

    if current_tokens <= max_tokens:
        return messages

    # Identify messages to keep vs. drop
    first_message = [messages[0]] if preserve_first and messages else []
    last_messages = messages[-preserve_last:] if preserve_last > 0 else []
    middle_messages = messages[len(first_message):-len(last_messages) if last_messages else len(messages)]

    # Summarize dropped messages if requested
    summary_message = []
    if summarize and middle_messages:
        summary_text = _summarize_messages(middle_messages, model_name)
        summary_message = [SystemMessage(content=f"[Summary of dropped messages]:\n{summary_text}")]

    # Assemble the trimmed list and re-calculate tokens
    trimmed_messages = first_message + summary_message + last_messages
    
    # Final trim if summary + preserved messages are still too long
    final_trimmed = []
    tokens_used = 0
    
    # Add first message
    if first_message:
        final_trimmed.append(first_message[0])
        tokens_used += estimate_message_tokens(first_message)
        
    # Add summary
    if summary_message:
        final_trimmed.extend(summary_message)
        tokens_used += estimate_message_tokens(summary_message)

    # Add last messages until token limit is reached
    for msg in reversed(last_messages):
        msg_tokens = estimate_message_tokens([msg])
        if tokens_used + msg_tokens <= max_tokens:
            final_trimmed.insert(len(first_message) + len(summary_message), msg)
            tokens_used += msg_tokens
        else:
            break

    return final_trimmed

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
    custom_limit: int = None,
    summarize: bool = False
) -> List:
    """
    Trim messages based on model capabilities.

    Args:
        messages: List of messages to trim
        model_name: Name of the model (to determine context limit)
        custom_limit: Optional custom token limit (overrides model default)
        summarize: Whether to summarize dropped messages

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
        preserve_last=15,  # Preserve more messages to avoid breaking tool call pairs
        summarize=summarize,
        model_name=model_name
    )