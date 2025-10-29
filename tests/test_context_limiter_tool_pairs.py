"""
Test to reproduce and fix the tool call pairing issue with context limiter.

Issue: When context limiter trims messages, it can remove tool_use blocks while
keeping tool_result blocks, which breaks Claude's API format.
"""

def test_tool_call_pairing():
    """Test that context limiter preserves tool call/result pairs"""
    from tradingagents.agents.utils.context_limiter import trim_messages_to_token_limit
    
    # Simulate a conversation with tool calls
    messages = [
        ("human", "Get stock data for AAPL"),  # First message
        ("ai", "I'll fetch that data for you"),  # AI response with tool_use
        ("tool", "Stock data: AAPL $150..."),  # Tool result
        ("ai", "Here's the analysis..."),  # AI processes result
        ("human", "Now get news"),  # Another request
        ("ai", "I'll get the news"),  # AI response with tool_use
        ("tool", "News: Apple announces..."),  # Tool result
        ("ai", "Based on the news..."),  # AI processes result
    ]
    
    # Trim to a small limit that would cut in the middle
    trimmed = trim_messages_to_token_limit(
        messages, 
        max_tokens=100,  # Very small to force trimming
        preserve_first=True,
        preserve_last=3
    )
    
    print(f"Original messages: {len(messages)}")
    print(f"Trimmed messages: {len(trimmed)}")
    print("\nTrimmed conversation:")
    for i, msg in enumerate(trimmed):
        print(f"  {i}: {msg[0][:6]:6s} - {msg[1][:50]}...")
    
    # Check that we don't have orphan tool results
    has_orphan_tool = False
    for i, msg in enumerate(trimmed):
        if msg[0] == "tool":
            # Check if previous message has tool_use
            if i == 0 or trimmed[i-1][0] != "ai":
                has_orphan_tool = True
                print(f"\n⚠ ORPHAN TOOL RESULT at index {i}!")
                print(f"   Previous: {trimmed[i-1] if i > 0 else 'None'}")
                print(f"   Current: {msg}")
    
    if not has_orphan_tool:
        print("\n✓ No orphan tool results found")
    
    return not has_orphan_tool


def test_with_langchain_messages():
    """Test with actual LangChain message objects"""
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from tradingagents.agents.utils.context_limiter import trim_messages_to_token_limit
    
    # Create realistic message sequence
    messages = [
        HumanMessage(content="Analyze NVDA"),
        AIMessage(content="I'll get the stock data", 
                 tool_calls=[{"id": "call_1", "name": "get_stock_data", "args": {"symbol": "NVDA"}}]),
        ToolMessage(content="Stock data: NVDA $140...", tool_call_id="call_1"),
        AIMessage(content="Now let me get fundamentals",
                 tool_calls=[{"id": "call_2", "name": "get_fundamentals", "args": {"symbol": "NVDA"}}]),
        ToolMessage(content="Fundamentals data...", tool_call_id="call_2"),
        AIMessage(content="Based on analysis..."),
    ]
    
    print("\n" + "="*60)
    print("Testing with LangChain messages")
    print("="*60)
    
    trimmed = trim_messages_to_token_limit(
        messages,
        max_tokens=500,  # Small limit
        preserve_last=2  # Only keep last 2
    )
    
    print(f"\nOriginal: {len(messages)} messages")
    print(f"Trimmed: {len(trimmed)} messages")
    
    # Check for orphan ToolMessages
    for i, msg in enumerate(trimmed):
        if isinstance(msg, ToolMessage):
            # Find corresponding AIMessage with tool_calls
            found_tool_use = False
            for j in range(max(0, i-3), i):
                if isinstance(trimmed[j], AIMessage) and hasattr(trimmed[j], 'tool_calls') and trimmed[j].tool_calls:
                    for tc in trimmed[j].tool_calls:
                        if tc.get('id') == msg.tool_call_id:
                            found_tool_use = True
                            break
            
            if not found_tool_use:
                print(f"\n⚠ ORPHAN ToolMessage at index {i}!")
                print(f"   tool_call_id: {msg.tool_call_id}")
                return False
    
    print("\n✓ All ToolMessages have corresponding tool_use blocks")
    return True


if __name__ == "__main__":
    print("="*60)
    print("Context Limiter Tool Pair Test")
    print("="*60)
    
    test1 = test_tool_call_pairing()
    test2 = test_with_langchain_messages()
    
    print("\n" + "="*60)
    if test1 and test2:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ TESTS FAILED - Context limiter breaks tool pairs")
    print("="*60)
