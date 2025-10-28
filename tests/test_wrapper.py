import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from tradingagents.agents.utils.rate_limited_llm import wrap_with_rate_limiting

load_dotenv()

databricks_token = os.getenv("DATABRICKS_TOKEN")
databricks_base_url = os.getenv("DATABRICKS_BASE_URL")

if databricks_base_url and not databricks_base_url.endswith("/serving-endpoints"):
    databricks_base_url = databricks_base_url.rstrip("/") + "/serving-endpoints"

# Create base LLM
base_llm = ChatOpenAI(
    model="llama_v3_3_70b_instruct_pro",
    api_key=databricks_token,
    base_url=databricks_base_url
)

print("Base LLM attributes:")
print(f"  model_name: {base_llm.model_name}")

# Wrap with rate limiting
wrapped_llm = wrap_with_rate_limiting(
    base_llm,
    "llama_v3_3_70b_instruct_pro",
    enable=True,
    verbose=True
)

print("\nWrapped LLM attributes:")
print(f"  model_name: {wrapped_llm.model_name}")
print(f"  Type: {type(wrapped_llm)}")

# Test bind_tools (what agents do)
from langchain_core.tools import tool

@tool
def test_tool(x: int) -> int:
    """A simple test tool"""
    return x * 2

print("\nBinding tools...")
llm_with_tools = wrapped_llm.bind_tools([test_tool])
print(f"  Type after bind_tools: {type(llm_with_tools)}")
print(f"  model_name after bind_tools: {llm_with_tools.model_name}")

# Test invoke
print("\nTesting invoke...")
try:
    result = wrapped_llm.invoke([{"role": "user", "content": "Say hello"}])
    print(f"Success: {result.content}")
except Exception as e:
    print(f"Error: {e}")
