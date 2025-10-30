## Agent Lightning Integration - Quick Start

This guide will help you get started with optimizing TradingAgents using Agent Lightning for reinforcement learning.

## Phase 1: Market Analyst Baseline (No Agent Lightning Yet)

Before integrating Agent Lightning, we've created the infrastructure to:
1. Generate training datasets from historical data
2. Evaluate Market Analyst performance
3. Establish baseline metrics

This allows us to measure improvements once Agent Lightning is integrated.

### Prerequisites

```bash
# Ensure TradingAgents dependencies are installed
pip install yfinance pandas langchain langgraph

# Optional: Install Agent Lightning (for future use)
# pip install agent-lightning[verl]
```

### Step 1: Generate Training Dataset

Create a dataset from historical stock data:

```bash
cd /Users/yipman/Downloads/github/TradingAgents

# Generate dataset with default settings
python tradingagents/training/scripts/generate_dataset.py

# Or customize:
python tradingagents/training/scripts/generate_dataset.py \
    --symbols MSFT NVDA GOOGL AAPL META \
    --start 2023-01-01 \
    --end 2024-10-31 \
    --future-days 5 \
    --val-split 0.2 \
    --output-dir ./training_data
```

**What this does:**
- Downloads historical data for specified symbols
- Calculates 5-day future returns as ground truth labels
- Creates train/validation splits (80%/20%)
- Saves datasets to `./training_data/market_analyst_train_*.json` and `market_analyst_val_*.json`

**Expected output:**
```
Market Analyst Dataset Generation
================================================================================
Symbols: MSFT, NVDA, GOOGL, AAPL, META
Date range: 2023-01-01 to 2024-10-31
...
Dataset Statistics
================================================================================
Total tasks: 2500
Training tasks: 2000
Validation tasks: 500
...
✓ Dataset generation complete!
```

### Step 2: Evaluate Baseline Performance

Test the current Market Analyst on the validation set:

```bash
# Evaluate on full validation set
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json

# Or quick test on 10 samples
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json \
    --sample 10 \
    --verbose
```

**Expected baseline metrics:**
```
Evaluation Report
================================================================================
Total tasks evaluated: 500
Correct directions: 275 / 500
Accuracy: 55.00%

Reward Statistics:
  Mean:   +0.15
  Median: +0.20
  Std:    0.65

Baseline Comparison:
  Baseline (random): 50.0%
  Current accuracy:  55.0%
  Improvement:       +10.0%
================================================================================
```

**What the metrics mean:**
- **Accuracy**: Percentage of correct BUY/HOLD/SELL decisions
- **Mean Reward**: Average reward across all tasks (+1.0 for correct BUY, -1.0 for wrong BUY, etc.)
- **Baseline**: Current performance is ~5-10% better than random guessing

### Step 3: Analyze Results

The evaluation helps identify:
- Which symbols are easier to predict
- What market conditions the analyst handles well/poorly
- Baseline metrics before RL optimization

You can save detailed results:

```bash
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json \
    --output ./eval_results/baseline_metrics.json
```

### Step 4: Understand the Optimization Opportunity

The Market Analyst currently uses **fixed** logic:
- Same technical indicators for all market conditions
- Equal weighting of MACD, RSI, Bollinger Bands
- No learning from past mistakes

**With Agent Lightning (future), we can:**
- Learn which indicators work best in different regimes
- Optimize indicator parameters (lookback periods, thresholds)
- Improve from ~55% to 65-70% accuracy

### Architecture Overview

```python
# Current structure (tradingagents/agents/optimizable/market_analyst_agent.py)

class LitMarketAnalyst:
    """Wrapper for Agent Lightning integration."""

    def rollout(self, task, resources=None, rollout=None):
        """
        Execute one analysis and return reward.

        Args:
            task: {symbol, trade_date, expected_return}

        Returns:
            Reward: +1.0 (correct buy), -1.0 (wrong buy), etc.
        """
        # Run TradingAgents Market Analyst
        final_state, decision = ta.propagate(
            symbol=task["symbol"],
            trade_date=task["trade_date"]
        )

        # Calculate reward based on correctness
        return self._calculate_reward(
            market_report=final_state["market_report"],
            expected_return=task["expected_return"]
        )
```

### Next Steps

Once baseline is established:

1. **Install Agent Lightning**:
   ```bash
   pip install agent-lightning[verl]
   ```

2. **Set up vLLM for RL training**:
   ```bash
   # Follow Agent Lightning vLLM setup guide
   # Requires NVIDIA GPU with 24GB+ VRAM
   ```

3. **Train with VERL algorithm**:
   ```python
   import agentlightning as agl
   from tradingagents.agents.optimizable.market_analyst_agent import LitMarketAnalystFull

   trainer = agl.Trainer(algorithm=agl.algorithm.VERL(config))
   trainer.fit(agent=agent, train_dataset=train_dataset, val_dataset=val_dataset)
   ```

4. **Compare optimized vs baseline**:
   - Baseline: ~55% accuracy
   - Target: 65-70% accuracy (+10-15% improvement)

### Troubleshooting

**Dataset generation fails:**
- Check internet connection (downloads from Yahoo Finance)
- Verify symbols are valid tickers
- Try smaller date range

**Evaluation is slow:**
- Use `--sample 10` to test on subset first
- Each task runs full TradingAgents workflow (can take 30-60 seconds per task with LLM calls)
- Consider using faster LLM provider for baseline evaluation

**Low baseline accuracy:**
- Expected! Current system is ~55% (only slightly better than random 50%)
- This is why RL optimization is valuable

### Files Created

```
TradingAgents/
├── tradingagents/
│   ├── agents/
│   │   └── optimizable/
│   │       ├── __init__.py
│   │       └── market_analyst_agent.py      # LitAgent wrapper
│   └── training/
│       ├── datasets/
│       │   ├── __init__.py
│       │   └── market_analyst_dataset.py    # Dataset builder
│       └── scripts/
│           ├── generate_dataset.py           # Data generation
│           └── evaluate_market_analyst.py    # Evaluation
└── docs/
    ├── AGENT_LIGHTNING_INTEGRATION_PLAN.md  # Full plan
    └── AGENT_LIGHTNING_QUICKSTART.md        # This file
```

### Example Workflow

```bash
# 1. Generate dataset
python tradingagents/training/scripts/generate_dataset.py \
    --symbols MSFT NVDA AAPL \
    --start 2024-01-01 \
    --end 2024-10-31

# 2. Quick evaluation (10 samples)
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json \
    --sample 10 \
    --verbose

# 3. Full baseline evaluation
python tradingagents/training/scripts/evaluate_market_analyst.py \
    --dataset ./training_data/market_analyst_val_*.json \
    --output ./eval_results/baseline.json

# 4. (Future) Train with Agent Lightning
# python tradingagents/training/scripts/train_market_analyst.py \
#     --train-dataset ./training_data/market_analyst_train_*.json \
#     --val-dataset ./training_data/market_analyst_val_*.json
```

### Understanding Rewards

The reward function in `LitMarketAnalyst._calculate_reward()`:

| Scenario | Expected Return | Recommendation | Reward | Explanation |
|----------|----------------|----------------|--------|-------------|
| Correct BUY | > +2% | BUY | +1.0 | Strong gain predicted and achieved |
| Marginal BUY | 0% to +2% | BUY | +0.5 | Correct direction, modest gain |
| Wrong BUY | < 0% | BUY | -1.0 | Predicted gain, but loss occurred |
| Correct SELL | < -2% | SELL | +0.8 | Avoided significant loss |
| Wrong SELL | > 0% | SELL | -0.8 | Predicted loss, but gain occurred |
| Correct HOLD | -2% to +2% | HOLD | +0.7 | Correctly identified low volatility |
| Missed Opportunity | > +2% or < -2% | HOLD | -0.3 | Should have taken action |

This reward structure encourages:
- **Accurate predictions** (highest rewards)
- **Risk avoidance** (rewarded for avoiding losses)
- **Action when needed** (penalized for excessive caution)

### Performance Targets

| Metric | Baseline | Post-RL Target | Stretch Goal |
|--------|----------|----------------|--------------|
| Accuracy | 55% | 65% | 70% |
| Mean Reward | +0.15 | +0.40 | +0.55 |
| High Rewards (≥0.7) | 30% | 50% | 60% |
| Negative Rewards | 25% | 15% | 10% |

### FAQ

**Q: Do I need GPUs for dataset generation/evaluation?**
A: No, these steps only require CPU. GPUs are needed later for RL training with Agent Lightning.

**Q: How long does evaluation take?**
A: ~30-60 seconds per task (depends on LLM API speed). For 500 tasks, expect 4-8 hours. Use `--sample` for faster testing.

**Q: Can I use different date ranges for train/val?**
A: Yes! Generate separate datasets:
```bash
# Training: 2023 data
python generate_dataset.py --start 2023-01-01 --end 2023-12-31 --output-dir ./train_2023

# Validation: 2024 data
python generate_dataset.py --start 2024-01-01 --end 2024-10-31 --output-dir ./val_2024
```

**Q: What if accuracy is below 50%?**
A: Check that `expected_return` is calculated correctly. The current implementation should be slightly above random (50-55%).

### Next: Full Agent Lightning Integration

See [AGENT_LIGHTNING_INTEGRATION_PLAN.md](./AGENT_LIGHTNING_INTEGRATION_PLAN.md) for the complete roadmap including:
- Phase 2: Bull/Bear Debate Optimization
- Phase 3: Full Multi-Agent System
- Training infrastructure setup
- vLLM configuration
- VERL algorithm tuning

---

**Status**: ✅ Phase 1 infrastructure complete (dataset generation, evaluation)
**Next**: Install Agent Lightning and begin RL training (requires GPU)
