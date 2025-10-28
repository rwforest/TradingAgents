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

print(f"Testing endpoints at: {databricks_base_url}\n")

# Test all models from notebook
models = [
    "databricks-claude-sonnet-4-5",
    "llama_v3_3_70b_instruct_pro",
    "meta_llama_v3_1_405b_instruct_fp8_pro"  # From notebook quick_think_llm
]

client = OpenAI(
    api_key=databricks_token,
    base_url=databricks_base_url
)

for model in models:
    print(f"Testing model: {model}")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        print(f"✓ SUCCESS: {model} is accessible")
        print(f"  Response: {response.choices[0].message.content}\n")
    except Exception as e:
        print(f"✗ ERROR: {model} failed")
        print(f"  Error: {str(e)}\n")
