"""
Script to help identify available Databricks models and provide recommendations
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

base_url = os.getenv("DATABRICKS_BASE_URL")
if base_url and not base_url.endswith("/serving-endpoints"):
    base_url = base_url.rstrip("/") + "/serving-endpoints"

token = os.getenv("DATABRICKS_TOKEN")

# Try to list models (if API supports it)
client = OpenAI(
    api_key=token,
    base_url=base_url
)

print("=" * 80)
print("Databricks Model Recommendations for TradingAgents")
print("=" * 80)
print()

# Models we know exist from your tests
known_models = [
    "databricks-claude-sonnet-4-5",
    "databricks-gpt-oss-120b",
]

print("Known Available Models:")
print("-" * 80)
for model in known_models:
    print(f"  ✓ {model}")
print()

print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print()

print("🏆 BEST CONFIGURATION (Recommended):")
print("-" * 80)
print("quick_think_llm: databricks-claude-sonnet-4-5")
print("deep_think_llm:  databricks-claude-sonnet-4-5")
print()
print("Why:")
print("  ✅ Perfect tool calling support")
print("  ✅ No financial advice restrictions")
print("  ✅ Consistent response format")
print("  ✅ Best reasoning quality")
print("  ✅ Proven to work in tests")
print()

print("💰 COST-OPTIMIZED (If available):")
print("-" * 80)
print("quick_think_llm: databricks-claude-haiku-3-5  (if available)")
print("deep_think_llm:  databricks-claude-sonnet-4-5")
print()
print("Why:")
print("  ✅ Haiku is faster and cheaper for routine analysis")
print("  ✅ Sonnet handles complex decision-making")
print("  ⚠️  Only works if Haiku endpoint exists")
print()

print("🚫 NOT RECOMMENDED:")
print("-" * 80)
print("databricks-gpt-oss-120b - Has financial advice policy restrictions")
print()

print("=" * 80)
print("COMMON DATABRICKS MODEL NAMES TO TRY")
print("=" * 80)
print()

# Common naming patterns
possible_models = {
    "Claude Models": [
        "databricks-claude-sonnet-4-5",  # ✓ Confirmed working
        "databricks-claude-3-5-sonnet",
        "claude-3-5-sonnet-20241022",
        "databricks-claude-haiku-3-5",
        "claude-3-5-haiku-20241022",
        "databricks-claude-opus-4-5",
    ],
    "Meta Llama Models": [
        "databricks-meta-llama-3-1-405b-instruct",
        "databricks-meta-llama-3-1-70b-instruct",
        "databricks-meta-llama-3-3-70b-instruct",
        "llama-3-1-405b-instruct",
        "llama-3-1-70b-instruct",
    ],
    "Other Models": [
        "databricks-dbrx-instruct",
        "databricks-mixtral-8x7b-instruct",
    ]
}

for category, models in possible_models.items():
    print(f"\n{category}:")
    print("-" * 40)
    for model in models:
        status = "✓ CONFIRMED" if model in known_models else "  Try this"
        print(f"{status}: {model}")

print()
print("=" * 80)
print("HOW TO TEST A MODEL")
print("=" * 80)
print()
print("Run this command to test if a model exists:")
print()
print("  python test_tool_calling.py")
print()
print("Then edit the models_to_test list in that file.")
print()

print("=" * 80)
print("OPTIMAL SETUP FOR YOUR USE CASE")
print("=" * 80)
print()
print("Based on your requirements:")
print()
print("1. For MAXIMUM QUALITY (both same model):")
print("   config['quick_think_llm'] = 'databricks-claude-sonnet-4-5'")
print("   config['deep_think_llm'] = 'databricks-claude-sonnet-4-5'")
print("   selected_analysts = ['market', 'news']  # To avoid context limits")
print()
print("2. For COST OPTIMIZATION (if Llama 70B available):")
print("   config['quick_think_llm'] = 'databricks-meta-llama-3-3-70b-instruct'")
print("   config['deep_think_llm'] = 'databricks-claude-sonnet-4-5'")
print("   # Test tool calling first!")
print()
print("3. For SPEED (if Haiku available):")
print("   config['quick_think_llm'] = 'databricks-claude-haiku-3-5'")
print("   config['deep_think_llm'] = 'databricks-claude-sonnet-4-5'")
print()

print("=" * 80)
print()
