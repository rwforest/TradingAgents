"""Test script to diagnose market analyst tool calling issue"""
import os
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.llm import create_llm
from tradingagents.agents.utils.agent_utils import get_stock_data, get_indicators
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

# Setup config
config = get_config()
config["llm_provider"] = os.getenv("LLM_PROVIDER", config.get("llm_provider", "databricks"))
config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", config.get("deep_think_llm", "databricks-claude-sonnet-4-5"))
config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", config.get("quick_think_llm", "llama_v3_3_70b_instruct_pro"))

print(f"Testing with provider: {config['llm_provider']}")
print(f"Deep think model: {config['deep_think_llm']}")

# Create LLM
llm = create_llm(config, is_deep_thinking=True)

# Bind tools
tools = [get_stock_data, get_indicators]
llm_with_tools = llm.bind_tools(tools)

# Simple test prompt
prompt = """You are a market analyst. Use the get_stock_data tool to retrieve stock data for MSFT from 2025-10-01 to 2025-10-31.

DO NOT explain what you're going to do. Just call the tool directly."""

print("\n" + "="*80)
print("TESTING TOOL CALLING")
print("="*80)

result = llm_with_tools.invoke([HumanMessage(content=prompt)])

print(f"\nResult type: {type(result)}")
print(f"Number of tool calls: {len(result.tool_calls)}")
print(f"Content length: {len(result.content) if result.content else 0}")

if result.tool_calls:
    print("\n✓ SUCCESS: Model made structured tool calls")
    for i, tc in enumerate(result.tool_calls):
        print(f"\nTool call {i+1}:")
        print(f"  Name: {tc['name']}")
        print(f"  Args: {tc['args']}")
else:
    print("\n✗ FAILURE: No structured tool calls made")
    print(f"\nContent preview (first 500 chars):")
    print(result.content[:500] if result.content else "No content")

    if "<function=" in result.content:
        print("\n⚠ WARNING: Model outputted pseudo-XML tool call syntax as text!")
