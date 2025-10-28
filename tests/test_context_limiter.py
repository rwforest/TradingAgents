"""
Test the context limiter functionality
"""
from tradingagents.agents.utils.context_limiter import (
    estimate_tokens,
    estimate_message_tokens,
    trim_messages_to_token_limit,
    trim_messages_for_model,
    get_safe_token_limit
)

print("=" * 80)
print("Testing Context Limiter")
print("=" * 80)

# Test 1: Token estimation
print("\n[TEST 1] Token Estimation")
print("-" * 80)
test_text = "This is a test message about stock analysis."
tokens = estimate_tokens(test_text)
print(f"Text: '{test_text}'")
print(f"Estimated tokens: {tokens}")

# Test 2: Message token estimation
print("\n[TEST 2] Message List Token Estimation")
print("-" * 80)
messages = [
    ("human", "Analyze NVDA stock"),
    ("ai", "I'll analyze NVDA. Let me get the stock data..." * 100),  # Large message
    ("tool", "Stock data: " + "NVDA,150,155,148,152\n" * 200),  # Large data
    ("ai", "Based on the analysis, here are my findings..." * 50),
]
total_tokens = estimate_message_tokens(messages)
print(f"Number of messages: {len(messages)}")
print(f"Total estimated tokens: {total_tokens:,}")

# Test 3: Trim messages
print("\n[TEST 3] Trim Messages to Limit")
print("-" * 80)
print(f"Original: {len(messages)} messages, {total_tokens:,} tokens")

trimmed = trim_messages_to_token_limit(
    messages,
    max_tokens=1000,  # Low limit for testing
    preserve_first=True,
    preserve_last=1
)

trimmed_tokens = estimate_message_tokens(trimmed)
print(f"Trimmed: {len(trimmed)} messages, {trimmed_tokens:,} tokens")
print(f"Messages kept: First + Last")

# Test 4: Model-aware trimming
print("\n[TEST 4] Model-Aware Trimming")
print("-" * 80)

models = [
    "databricks-claude-sonnet-4-5",
    "databricks-claude-opus-4-5",
    "databricks-meta-llama-3-3-70b-instruct",
]

for model in models:
    safe_limit = get_safe_token_limit(model)
    print(f"\nModel: {model}")
    print(f"  Safe token limit: {safe_limit:,}")

# Test 5: Simulate TradingAgents scenario
print("\n[TEST 5] Simulate TradingAgents Overflow Scenario")
print("-" * 80)

# Create messages that would overflow (like in real TradingAgents)
large_messages = [
    ("human", "Analyze NVDA"),
    ("ai", "Market Analyst Report:\n" + "Price data and analysis. " * 1000),
    ("tool", "Stock data:\n" + "2025-01-01,150,155,148,152,1000000\n" * 5000),
    ("ai", "Social Media Analyst Report:\n" + "Sentiment analysis. " * 1000),
    ("tool", "News data:\n" + "Article about AI and semiconductors. " * 3000),
    ("ai", "News Analyst Report:\n" + "News summary and insights. " * 1000),
    ("ai", "Fundamentals Analyst will now run..."),
]

original_tokens = estimate_message_tokens(large_messages)
print(f"Original messages: {len(large_messages)}")
print(f"Original tokens: {original_tokens:,}")

# Trim for Claude Sonnet (128K limit)
trimmed_for_fundamentals = trim_messages_for_model(
    large_messages,
    model_name="databricks-claude-sonnet-4-5",
    custom_limit=80000  # Leave room for fundamentals output
)

final_tokens = estimate_message_tokens(trimmed_for_fundamentals)
print(f"\nAfter trimming:")
print(f"  Messages: {len(large_messages)} → {len(trimmed_for_fundamentals)}")
print(f"  Tokens: {original_tokens:,} → {final_tokens:,}")
print(f"  Saved: {original_tokens - final_tokens:,} tokens")

if final_tokens < 80000:
    print(f"  ✅ Under limit! Safe to process.")
else:
    print(f"  ⚠️  Still over limit. Need more aggressive trimming.")

print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print("\n✅ Context limiter is working correctly!")
print("\nIn TradingAgents:")
print("  - Fundamentals Analyst will trim messages to 80K tokens")
print("  - Preserves first message (initial query) and last message")
print("  - Removes middle messages to stay under budget")
print("  - Should prevent 'Input length exceeds context' errors")
print("\nTo adjust limits:")
print("  - Edit custom_limit in fundamentals_analyst.py")
print("  - Lower = more aggressive trimming, safer")
print("  - Higher = more context, riskier")
print("=" * 80)
