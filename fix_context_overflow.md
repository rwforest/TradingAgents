# Fix Context Overflow in TradingAgents

## Problem

The Fundamentals Analyst is receiving 169,776 tokens but the model only supports 131,072 tokens (128K context).

**Why this happens:**
- Each analyst receives ALL previous messages
- Messages accumulate: Market → Social → News → Fundamentals
- By the time Fundamentals runs, context is 170K tokens

## Solution 1: Skip Resource-Heavy Analysts (Easiest)

```python
# In your notebook/script
selected_analysts = ["market", "news"]  # Skip social and fundamentals
```

**Pros:**
- ✅ Immediate fix
- ✅ No code changes needed
- ✅ Still get market data + news analysis

**Cons:**
- ❌ Missing fundamental analysis
- ❌ Missing social sentiment

---

## Solution 2: Use Shorter Date Range

```python
# Reduce data volume by analyzing shorter period
# Instead of 10 months (2025-01-01 to 2025-10-27)
# Use last 2-3 months

trade_date = "2025-10-27"
# The analysts will automatically fetch less data for recent dates
```

---

## Solution 3: Implement Message Trimming (Requires Code Change)

Add a message trimming function that keeps only the last N messages:

### File: `tradingagents/agents/analysts/fundamentals_analyst.py`

```python
def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # TRIM MESSAGES TO PREVENT OVERFLOW
        messages = state["messages"]

        # Keep only the last 3 messages (most recent context)
        # This typically includes: initial query + last 2 analyst reports
        if len(messages) > 3:
            messages = [messages[0]] + messages[-2:]  # Keep first + last 2

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        # ... rest of the code stays the same

        result = chain.invoke(messages)  # Use trimmed messages
```

---

## Solution 4: Use Claude Opus (If Available)

Claude Opus has 200K context window (vs Sonnet's 128K):

```python
# Check if available in your Databricks
config["quick_think_llm"] = "databricks-claude-opus-4-5"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
```

---

## Recommended Approach

**For immediate use:**
```python
# Option A: Skip problematic analysts
selected_analysts = ["market", "news"]
```

**For better quality with all analysts:**
1. Implement Solution 3 (message trimming) in fundamentals_analyst.py
2. Also trim in social_media_analyst.py if needed
3. This keeps full functionality while managing context

---

## Testing

After making changes, test with:
```bash
source .venv/bin/activate
python test_databricks_optimized.py
```

Monitor for the error:
```
Input length of X tokens exceeds model context length
```

If X is close to limit (>120K), add more trimming.

---

## Token Budget by Analyst (Estimated)

| Analyst | Input Tokens | Output Tokens | Total |
|---------|--------------|---------------|-------|
| Market | 5K | 3K | 8K |
| Social | 8K + 8K prev | 4K | 20K |
| News | 20K + 20K prev | 5K | 45K |
| Fundamentals | 45K + 45K prev | 10K | **100K** |
| Bull/Bear Debate | 100K + analysis | 5K each | **120K** |
| Risk Debate | 120K + debate | 5K each | **130K+** ❌

Without trimming, you WILL hit the limit by Fundamentals or Risk Debate.
