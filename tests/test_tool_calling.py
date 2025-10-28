import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Get credentials
databricks_token = os.getenv("DATABRICKS_TOKEN")
databricks_base_url = os.getenv("DATABRICKS_BASE_URL")

# Ensure base URL has /serving-endpoints
if databricks_base_url and not databricks_base_url.endswith("/serving-endpoints"):
    databricks_base_url = databricks_base_url.rstrip("/") + "/serving-endpoints"

print(f"Testing tool calling support at: {databricks_base_url}\n")

# Define a simple tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current stock price for a given ticker symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g., AAPL, TSLA"
                    }
                },
                "required": ["ticker"]
            }
        }
    }
]

# Test both models
models = [
    "databricks-claude-sonnet-4-5",
    "llama_v3_3_70b_instruct_pro"
]

client = OpenAI(
    api_key=databricks_token,
    base_url=databricks_base_url
)

for model in models:
    print(f"Testing tool calling with model: {model}")
    print("-" * 80)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "What is the stock price for NVDA?"}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=500
        )

        message = response.choices[0].message

        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f"✓ SUCCESS: {model} supports tool calling!")
            print(f"  Tool calls made: {len(message.tool_calls)}")
            for tool_call in message.tool_calls:
                print(f"    - {tool_call.function.name}({tool_call.function.arguments})")
        else:
            print(f"⚠ PARTIAL: {model} accepted tools parameter but didn't call any tools")
            print(f"  Response: {message.content}")

    except Exception as e:
        print(f"✗ ERROR: {model} failed with tool calling")
        print(f"  Error: {str(e)}")

    print()
