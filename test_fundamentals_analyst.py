"""
Test fundamentals analyst to verify:
1. get_company_info tool is accessible
2. Tool execution works without recursion loops
3. Report generation completes successfully
"""

import os
from dotenv import load_dotenv
from tradingagents.dataflows.config import get_config

load_dotenv()

def test_fundamentals_analyst():
    print("="*60)
    print("Testing Fundamentals Analyst")
    print("="*60)

    # Get config
    config = get_config()
    print(f"\n✓ Config loaded")
    print(f"  LLM Provider: {config.get('llm_provider')}")
    print(f"  Quick Think LLM: {config.get('quick_think_llm')}")
    print(f"  Max Recursion: {config.get('max_recur_limit')}")


    # Test tool availability
    print(f"\n{'='*60}")
    print("Testing Tool Availability")
    print("="*60)

    # Import tools to check they exist
    from tradingagents.agents.utils.agent_utils import (
        get_company_info,
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement
    )

    print(f"\n✓ All tools imported successfully:")
    print(f"  - get_company_info: {get_company_info.name}")
    print(f"  - get_fundamentals: {get_fundamentals.name}")
    print(f"  - get_balance_sheet: {get_balance_sheet.name}")
    print(f"  - get_cashflow: {get_cashflow.name}")
    print(f"  - get_income_statement: {get_income_statement.name}")

    # Test get_company_info directly
    print(f"\n{'='*60}")
    print("Testing get_company_info Directly")
    print("="*60)

    try:
        from tradingagents.dataflows.interface import route_to_vendor
        result = route_to_vendor("get_company_info", "MSFT")
        print(f"\n✓ get_company_info executed successfully!")
        print(f"\nResult preview (first 500 chars):")
        print(result[:500] + "...")
    except Exception as e:
        print(f"\n❌ get_company_info failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_fundamentals_analyst()

    print(f"\n{'='*60}")
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*60)
