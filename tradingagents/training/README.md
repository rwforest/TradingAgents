# TradingAgents Training & Optimization

This directory contains the infrastructure for optimizing TradingAgents using reinforcement learning via Agent Lightning.

## Directory Structure

```
training/
├── datasets/               # Dataset builders
│   ├── __init__.py
│   └── market_analyst_dataset.py
├── scripts/                # Training and evaluation scripts
│   ├── generate_dataset.py
│   └── evaluate_market_analyst.py
└── README.md              # This file
```

## Quick Start

### 1. Generate Training Data

```bash
python tradingagents/training/scripts/generate_dataset.py
```

This creates:
- `./training_data/market_analyst_train_*.json` - Training dataset
- `./training_data/market_analyst_val_*.json` - Validation dataset

### 2. Evaluate Baseline Performance

```bash
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json \
    --sample 10
```

## Scripts

### `generate_dataset.py`

Generates training/validation datasets from historical stock data.

**Options:**
- `--symbols`: Stock tickers (default: MSFT, NVDA, GOOGL, AAPL, META, AMZN, TSLA)
- `--start`: Start date in YYYY-MM-DD format
- `--end`: End date in YYYY-MM-DD format
- `--lookback-days`: History needed before each trade (default: 30)
- `--future-days`: Days ahead for return calculation (default: 5)
- `--val-split`: Validation fraction (default: 0.2)
- `--output-dir`: Output directory (default: ./training_data)
- `--cache-dir`: Cache for downloaded data (default: ./training_data/cache)

**Example:**
```bash
python tradingagents/training/scripts/generate_dataset.py \
    --symbols MSFT NVDA AAPL \
    --start 2024-01-01 \
    --end 2024-10-31 \
    --future-days 5
```

### `evaluate_market_analyst.py`

Evaluates Market Analyst performance on a dataset.

**Options:**
- `--dataset`: Path to validation dataset JSON (required)
- `--sample`: Evaluate only N random samples (optional)
- `--verbose`: Print detailed results
- `--output`: Save results to JSON file (optional)

**Example:**
```bash
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_20241029.json \
    --sample 10 \
    --verbose \
    --output ./eval_results/baseline.json
```

## Dataset Format

Each task in the dataset is a dictionary:

```json
{
  "symbol": "MSFT",
  "trade_date": "2024-06-15",
  "expected_return": 0.0347,
  "current_price": 430.50,
  "future_price": 445.43,
  "future_days": 5
}
```

**Fields:**
- `symbol`: Stock ticker
- `trade_date`: Date to run analysis on
- `expected_return`: Actual return over next N days (ground truth for reward)
- `current_price`: Price on trade_date
- `future_price`: Price N days later
- `future_days`: Number of days in the future

## Evaluation Metrics

- **Accuracy**: % of correct BUY/HOLD/SELL decisions
- **Mean Reward**: Average reward across all tasks
- **Reward Distribution**: Breakdown by reward ranges

**Baseline Performance:**
- Accuracy: ~55% (slightly better than random 50%)
- Mean Reward: ~+0.15

**Target After RL Optimization:**
- Accuracy: 65-70%
- Mean Reward: +0.40 to +0.55

## Next Steps

1. **Establish Baseline**: Run evaluation to measure current performance
2. **Install Agent Lightning**: `pip install agent-lightning[verl]`
3. **Train with RL**: Use VERL algorithm to optimize prompts/model
4. **Compare**: Re-evaluate to measure improvement

See [docs/AGENT_LIGHTNING_QUICKSTART.md](../../docs/AGENT_LIGHTNING_QUICKSTART.md) for detailed walkthrough.

## Extending to Other Agents

The same pattern can be applied to other analysts:

```python
# For Bull/Bear Debate optimization
from tradingagents.agents.optimizable.debate_agent import LitDebateAgent
from tradingagents.training.datasets.debate_dataset import create_debate_dataset

# For Trader optimization
from tradingagents.agents.optimizable.trader_agent import LitTrader
from tradingagents.training.datasets.trader_dataset import create_trader_dataset
```

See [docs/AGENT_LIGHTNING_INTEGRATION_PLAN.md](../../docs/AGENT_LIGHTNING_INTEGRATION_PLAN.md) for the full roadmap.
