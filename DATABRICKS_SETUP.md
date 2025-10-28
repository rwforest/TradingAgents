# Databricks Integration for TradingAgents

This guide explains how to use TradingAgents with Databricks Claude models.

## Setup

### 1. Environment Variables

Add these to your `.env` file:

```bash
DATABRICKS_TOKEN=your-databricks-token-here
DATABRICKS_BASE_URL=https://adb-8333330282859393.13.azuredatabricks.net
```

Note: The `/serving-endpoints` path will be automatically appended.

### 2. Install Dependencies

```bash
source .venv/bin/activate
pip install python-dotenv
```

## Running the Tests

### Option 1: Python Script

```bash
source .venv/bin/activate
python test_databricks.py
```

This will:
- Load your `.env` configuration
- Initialize TradingAgentsGraph with Databricks
- Run analysis on NVDA for 2025-10-27
- Save output to `trading_results/NVDA_{timestamp}.md`
- Display the final decision in the console

### Option 2: Jupyter Notebook

```bash
source .venv/bin/activate
jupyter notebook test_databricks.ipynb
```

Or open [test_databricks.ipynb](test_databricks.ipynb) in VS Code and:
1. Select the `.venv` Python kernel
2. Run cells sequentially

The notebook includes:
- Step-by-step execution
- Configuration validation
- Single symbol analysis
- Multiple symbol batch analysis

## Output Files

All analysis results are saved to markdown files in the `analysis_results/{SYMBOL}/` directory with the format:

```
analysis_results/{SYMBOL}/{SYMBOL}_{TIMESTAMP}.md
```

For example:
- `analysis_results/NVDA/NVDA_20251027_143052.md`
- `analysis_results/AAPL/AAPL_20251027_150234.md`

This structure organizes all analyses by symbol, making it easy to track historical analyses for each stock.

Each file contains:
- Analysis metadata (symbol, date, model, etc.)
- Full agent reasoning and conversations
- Technical analysis
- News and sentiment analysis
- Bull/bear debate
- Risk assessment
- Final trading decision

## Configuration

### Model Names

Update these in the config:

```python
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"
```

Replace with your actual Databricks serving endpoint names.

### Analyze Different Stocks

In `test_databricks.py`:

```python
symbol = "AAPL"  # Change this
trade_date = "2025-10-27"  # Change this
```

Or in the notebook, modify the corresponding cell.

### Batch Analysis

Use the last cell in the notebook to analyze multiple symbols:

```python
symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
trade_date = "2025-10-27"
```

## Troubleshooting

### Error: DATABRICKS_TOKEN not set

Make sure:
1. Your `.env` file exists in the project root
2. It contains `DATABRICKS_TOKEN=...`
3. You're running with `source .venv/bin/activate` first

### Error: 404 Not Found

Check that:
1. Your `DATABRICKS_BASE_URL` is correct
2. The model name matches your serving endpoint exactly
3. Your token has access to the endpoint

### Error: AttributeError on base_url

This has been fixed in the latest code. Make sure you're using the updated version.

## Files Modified

The following files were updated to support Databricks:

1. `tradingagents/graph/trading_graph.py` - Added Databricks LLM initialization
2. `tradingagents/agents/utils/memory.py` - Added Databricks client support
3. `tradingagents/dataflows/openai.py` - Added Databricks endpoint handling
4. `tradingagents/default_config.py` - Added Databricks configuration

All changes are backward compatible with existing OpenAI, Anthropic, and Google providers.
