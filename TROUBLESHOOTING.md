# Troubleshooting Databricks Integration

## Common Issues and Solutions

### 1. ChromaDB Collection Already Exists

**Error:** `InternalError: Collection [bull_memory] already exists`

**Solution:** This has been fixed in the latest code. The memory module now tries to get the existing collection first before creating a new one.

If you still encounter this issue, you can reset ChromaDB by deleting the in-memory collections between runs or restarting your Python session.

---

### 2. Input Too Long for Model

**Error:** `openai.BadRequestError: Error code: 400 - {'error_code': 'BAD_REQUEST', 'message': '{"message":"Input is too long for requested model."}'}`

**Cause:** The Databricks Claude model has a context window limit, and the trading agents framework can generate very large contexts when analyzing stocks with extensive data (price history, news, fundamentals, etc.).

**Solutions:**

#### Option A: Reduce the Date Range
Limit the amount of historical data being analyzed:

```python
# In test_databricks.py or notebook
# Instead of analyzing from 2025-01-01 to 2025-10-27 (10 months)
# Use a shorter period, e.g., last 3 months

trade_date = "2025-10-27"
# The framework will automatically adjust the lookback period
```

#### Option B: Use a Larger Context Model
If available, switch to a Databricks model with a larger context window:

```python
config["deep_think_llm"] = "databricks-claude-sonnet-4-5-large"  # If available
config["quick_think_llm"] = "databricks-claude-sonnet-4-5-large"
```

#### Option C: Modify the Default Config
Reduce the amount of data fetched by modifying `default_config.py`:

```python
# Reduce debate rounds to minimize context
config["max_debate_rounds"] = 1  # Default is 1
config["max_risk_discuss_rounds"] = 1  # Default is 1
```

#### Option D: Disable Certain Analysts
If you don't need all types of analysis:

```python
# Only use market and news analysts (skip social and fundamentals)
ta = TradingAgentsGraph(
    debug=True,
    config=config,
    selected_analysts=["market", "news"]  # Skip "social" and "fundamentals"
)
```

---

### 3. 404 Not Found Error

**Error:** `openai.NotFoundError: Error code: 404`

**Cause:** The model endpoint name doesn't exist or the base URL is incorrect.

**Solution:**

1. Verify your Databricks serving endpoint name:
   ```python
   # Make sure this exactly matches your endpoint
   config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
   ```

2. Check your base URL includes the workspace correctly:
   ```python
   # Should look like this
   DATABRICKS_BASE_URL=https://adb-8333330282859393.13.azuredatabricks.net
   ```

3. The `/serving-endpoints` path is automatically appended by the code.

---

### 4. Environment Variables Not Loading

**Error:** `ERROR: DATABRICKS_TOKEN environment variable is not set`

**Solution:**

Make sure you're running with the virtual environment activated:

```bash
source .venv/bin/activate
python test_databricks.py
```

Or use the venv Python directly:

```bash
.venv/bin/python test_databricks.py
```

Check your `.env` file contains:
```bash
DATABRICKS_TOKEN=your_token_here
DATABRICKS_BASE_URL=https://your-workspace.azuredatabricks.net
```

---

### 5. Recommended Configuration for Databricks

To avoid context length issues, here's a recommended configuration:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"

# Optimize for smaller context
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1

# Use only essential analysts to reduce context
ta = TradingAgentsGraph(
    debug=True,
    config=config,
    selected_analysts=["market", "news"]  # Start with these two
)

# Use recent dates to limit historical data
_, decision = ta.propagate("NVDA", "2025-10-27")
```

---

### 6. Testing Connection

To test if your Databricks connection works before running the full analysis:

```python
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DATABRICKS_TOKEN"),
    base_url=os.getenv("DATABRICKS_BASE_URL") + "/serving-endpoints"
)

response = client.chat.completions.create(
    model="databricks-claude-sonnet-4-5",
    messages=[{"role": "user", "content": "Hello, are you working?"}],
    max_tokens=100
)

print(response.choices[0].message.content)
```

If this works, your Databricks configuration is correct.
