import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

databricks_token = os.getenv("DATABRICKS_TOKEN")
databricks_base_url = os.getenv("DATABRICKS_BASE_URL")

if databricks_base_url and not databricks_base_url.endswith("/serving-endpoints"):
    databricks_base_url = databricks_base_url.rstrip("/") + "/serving-endpoints"

print(f"Testing embedding models at: {databricks_base_url}\n")

# Common Databricks embedding models
embedding_models = [
    "databricks-gte-large-en",
    "databricks-bge-large-en",
    "text-embedding-3-small",  # OpenAI model (won't work)
]

client = OpenAI(api_key=databricks_token, base_url=databricks_base_url)

for model in embedding_models:
    print(f"Testing: {model}")
    try:
        response = client.embeddings.create(
            model=model,
            input="test embedding"
        )
        print(f"  ✓ SUCCESS - Embedding dimension: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"  ✗ FAILED - {str(e)}")
    print()
