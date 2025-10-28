from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# How to get your Databricks token: https://docs.databricks.com/en/dev-tools/auth/pat.html
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
# Alternatively in a Databricks notebook you can use this:
# DATABRICKS_TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

print("Testing Databricks Connection...")
print(f"Token: {'*' * 20 if DATABRICKS_TOKEN else 'NOT SET'}")
print(f"Base URL: https://adb-8333330282859393.13.azuredatabricks.net/serving-endpoints")
print(f"Model: databricks-claude-sonnet-4-5")
print()

client = OpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url="https://adb-8333330282859393.13.azuredatabricks.net/serving-endpoints"
)

try:
    response = client.chat.completions.create(
        model="databricks-claude-sonnet-4-5",
        messages=[
            {
                "role": "user",
                "content": "What is an LLM agent?"
            }
        ],
        max_tokens=5000
    )

    print("✓ SUCCESS! Connection works!")
    print()
    print("Response:")
    print("=" * 80)
    print(response.choices[0].message.content)
    print("=" * 80)

except Exception as e:
    print("✗ ERROR!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print()
    print("This likely means:")
    print("1. The endpoint name 'databricks-claude-sonnet-4-5' doesn't exist")
    print("2. Check your Databricks Serving endpoints for the correct name")
    print("3. Go to: Databricks > Serving > Endpoints")
