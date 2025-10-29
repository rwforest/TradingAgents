"""
Progressive summarization to preserve context while preventing overflow.
Strategy: Summarize BEFORE trimming, then summarize again if still too long.
"""
from typing import Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, ToolMessage
import os
import re


def extract_key_phrases(text: str, max_phrases: int = 50) -> List[str]:
    """
    Extract important phrases from text for ultra-compression.

    Args:
        text: Text to extract from
        max_phrases: Maximum number of phrases

    Returns:
        List of key phrases
    """
    # Extract numbers with context (prices, percentages, dates)
    numbers = re.findall(r'\$[\d,]+\.?\d*|\d+\.?\d*%|\d{4}-\d{2}-\d{2}', text)

    # Extract sentences with key financial terms
    key_terms = [
        'revenue', 'profit', 'growth', 'decline', 'margin', 'earnings',
        'bullish', 'bearish', 'buy', 'sell', 'hold', 'risk', 'opportunity',
        'recommend', 'valuation', 'price target', 'forecast', 'outlook'
    ]

    key_sentences = []
    for sentence in text.split('.'):
        if any(term in sentence.lower() for term in key_terms):
            key_sentences.append(sentence.strip())

    # Combine and dedupe
    phrases = list(set(numbers + key_sentences[:max_phrases]))
    return phrases[:max_phrases]


def summarize_analyst_report(
    analyst_name: str,
    full_report: str,
    max_summary_length: int = 2000,
    llm_config: dict = None,
    compression_level: int = 1
) -> str:
    """
    Progressively summarize report - tries LLM first, then extraction if needed.

    Args:
        analyst_name: Name of the analyst (e.g., "Market Analyst")
        full_report: The full report text to summarize
        max_summary_length: Target max length for summary in characters
        llm_config: LLM configuration (provider, model, etc.)
        compression_level: 1=light summary, 2=aggressive summary, 3=key phrases only

    Returns:
        Condensed summary of the report
    """
    # If report is already short enough, return as-is
    if len(full_report) < max_summary_length * 2:
        return full_report

    # Level 3: Ultra compression - extract key phrases only
    if compression_level >= 3:
        print(f"[{analyst_name}] Level 3 compression: extracting key phrases...")
        phrases = extract_key_phrases(full_report, max_phrases=30)
        return f"[{analyst_name} - KEY INSIGHTS]\n\n" + "\n- ".join(phrases)

    # Create summarization LLM
    try:
        if llm_config and llm_config.get("llm_provider") == "databricks":
            llm = ChatOpenAI(
                model=llm_config.get("quick_think_llm", "databricks-claude-sonnet-4-5"),
                base_url=llm_config.get("databricks_base_url"),
                api_key=llm_config.get("databricks_token"),
                temperature=0.3
            )
        else:
            # Fallback to OpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=1000 if compression_level == 2 else 1500
            )

        # Adjust prompt based on compression level
        if compression_level == 2:
            prompt = f"""URGENT: Extreme compression needed. Summarize into BULLET POINTS ONLY (max 500 words):

**{analyst_name} Report:**
{full_report[:10000]}

**ULTRA-CONCISE SUMMARY (bullet points only):**"""
        else:
            prompt = f"""Summarize the following {analyst_name} report into KEY INSIGHTS (max 1200 words):

**REQUIREMENTS:**
1. Extract ONLY critical insights and recommendations
2. Keep key metrics and numbers
3. Maintain final recommendation
4. Use bullet points

**ORIGINAL REPORT:**
{full_report[:15000]}

**CONCISE SUMMARY:**"""

        response = llm.invoke([HumanMessage(content=prompt)])
        summary = response.content

        # Check if still too long
        if len(summary) > max_summary_length * 2 and compression_level < 2:
            print(f"[{analyst_name}] Summary still too long, compressing again...")
            return summarize_analyst_report(
                analyst_name, summary, max_summary_length, llm_config, compression_level + 1
            )

        header = f"[{analyst_name} - LEVEL {compression_level} SUMMARY]" if compression_level > 1 else f"[{analyst_name} - SUMMARY]"
        return f"{header}\n\n{summary}"

    except Exception as e:
        # If summarization fails, use key phrase extraction
        print(f"[{analyst_name}] LLM summarization failed ({e}), extracting key phrases...")
        phrases = extract_key_phrases(full_report, max_phrases=40)
        return f"[{analyst_name} - KEY INSIGHTS]\n\n" + "\n- ".join(phrases)


def check_and_summarize_messages(
    messages: list,
    max_total_tokens: int = 80000,
    llm_config: dict = None,
    compression_level: int = 1
) -> list:
    """
    Progressively summarize message history to stay under token limit.
    Applies multiple rounds of compression if needed.

    Args:
        messages: List of conversation messages
        max_total_tokens: Maximum total tokens before summarizing
        llm_config: LLM configuration
        compression_level: Current compression level (1-3)

    Returns:
        Summarized message list that fits within token budget
    """
    from tradingagents.agents.utils.context_limiter import estimate_message_tokens

    current_tokens = estimate_message_tokens(messages)

    if current_tokens < max_total_tokens:
        return messages

    print(f"[Summarizer Level {compression_level}] Context at {current_tokens:,} tokens (limit: {max_total_tokens:,})")

    if len(messages) <= 3:
        print(f"[Summarizer] Warning: Only {len(messages)} messages left, cannot compress further")
        return messages

    # Group messages into sets, keeping tool calls and responses together
    message_sets = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            tool_call_set = [msg]
            # Get valid tool_call_ids from this AIMessage
            valid_ids = {tc.id if hasattr(tc, 'id') else tc['id'] for tc in msg.tool_calls}
            j = i + 1
            # Collect all ToolMessages that belong to this AIMessage
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                if hasattr(messages[j], 'tool_call_id') and messages[j].tool_call_id in valid_ids:
                    tool_call_set.append(messages[j])
                    j += 1
                else:
                    break  # Stop if we hit a ToolMessage for a different AIMessage
            message_sets.append(tool_call_set)
            i = j
        else:
            message_sets.append([msg])
            i += 1

    # Summarize middle sets
    if len(message_sets) > 2:
        preserved_start = message_sets[0]
        preserved_end = message_sets[-1]
        to_summarize_sets = message_sets[1:-1]

        summary_parts = []
        for message_set in to_summarize_sets:
            for msg in message_set:
                if hasattr(msg, 'content'):
                    content = str(msg.content)
                    if len(content) > 1000:
                        analyst_name = "Previous Analysis"
                        summarized = summarize_analyst_report(
                            analyst_name, content, max_summary_length=500,
                            llm_config=llm_config, compression_level=compression_level
                        )
                        summary_parts.append(summarized[:500])
                    else:
                        summary_parts.append(content[:500])

        summary_text = "\n\n".join(summary_parts)
        summary_message = AIMessage(content=f"[CONVERSATION SUMMARY]\n\n{summary_text}")

        summarized_messages = preserved_start + [summary_message] + preserved_end
    else:
        summarized_messages = messages

    new_tokens = estimate_message_tokens(summarized_messages)
    print(f"[Summarizer] Reduced from {current_tokens:,} to {new_tokens:,} tokens")

    if new_tokens > max_total_tokens and compression_level < 3:
        print(f"[Summarizer] Still over limit, trying level {compression_level + 1}...")
        return check_and_summarize_messages(summarized_messages, max_total_tokens, llm_config, compression_level + 1)

    return summarized_messages


def safe_invoke_with_retry(chain, messages, max_retries: int = 3, llm_config: dict = None):
    """
    Invoke chain with automatic retry and progressive summarization on context overflow.

    Args:
        chain: LangChain chain to invoke
        messages: Messages to process
        max_retries: Maximum retry attempts
        llm_config: LLM configuration

    Returns:
        Chain response

    Raises:
        Exception if all retries fail
    """
    from tradingagents.agents.utils.context_limiter import estimate_message_tokens

    for attempt in range(max_retries):
        try:
            current_tokens = estimate_message_tokens(messages)
            print(f"[Safe Invoke] Attempt {attempt + 1}, tokens: {current_tokens:,}")

            return chain.invoke(messages)

        except Exception as e:
            error_msg = str(e).lower()

            # Check if it's a context length error
            if any(keyword in error_msg for keyword in ['context', 'token', 'length', 'exceed']):
                print(f"[Safe Invoke] Context overflow detected: {e}")

                if attempt < max_retries - 1:
                    # Progressively reduce token limit
                    new_limit = int(current_tokens * 0.7)  # Reduce by 30%
                    print(f"[Safe Invoke] Retrying with reduced limit: {new_limit:,}")

                    messages = check_and_summarize_messages(
                        messages,
                        max_total_tokens=new_limit,
                        llm_config=llm_config,
                        compression_level=attempt + 1
                    )
                else:
                    print(f"[Safe Invoke] All retries exhausted")
                    raise
            else:
                # Not a context error, raise immediately
                raise

    raise Exception(f"Failed after {max_retries} attempts")
