# Agent Lightning Integration Plan for TradingAgents

## Executive Summary

This document outlines a comprehensive plan to integrate **Agent Lightning** into TradingAgents to enable systematic reinforcement learning (RL) optimization of trading agents. Agent Lightning provides a framework-agnostic RL training platform with explicit LangGraph support, requiring minimal code changes.

## Current State Analysis

### Existing Learning Infrastructure

TradingAgents already has foundational learning components:

1. **Reflection System** ([graph/reflection.py](../tradingagents/graph/reflection.py))
   - Post-decision analysis using returns/losses as feedback
   - Component-specific reflectors for Bull, Bear, Trader, Judge, and Risk Manager
   - Memory updates via ChromaDB

2. **Memory System** (ChromaDB-based)
   - Bull researcher memory
   - Bear researcher memory
   - Trader memory
   - Investment judge memory
   - Risk manager memory

3. **Feedback Mechanism**
   - `returns_losses` signals available for learning
   - Can be converted to RL reward signals

### TradingAgents Architecture

**10 Specialized Agents:**

| Agent Type | Function | Optimization Opportunity |
|------------|----------|--------------------------|
| **Market Analyst** | Technical indicators (MACD, RSI, Bollinger) | Learn which indicators predict well in different market conditions |
| **News Analyst** | News sentiment & macroeconomic analysis | Optimize news source weighting & sentiment interpretation |
| **Social Media Analyst** | Reddit/Twitter sentiment analysis | Learn to filter signal from noise |
| **Fundamentals Analyst** | Financial statement analysis | Optimize which fundamentals are most predictive |
| **Bull Researcher** | Build buy case | Generate more data-driven, convincing arguments |
| **Bear Researcher** | Build sell/hold case | Improve risk identification and articulation |
| **Research Manager (Judge)** | Synthesize bull/bear debate | Better decision synthesis & conflict resolution |
| **Trader** | Create investment plan | Optimize position sizing, entry/exit timing |
| **Risk Analysts (3)** | Aggressive/Neutral/Conservative | Calibrate risk tolerance to historical outcomes |
| **Risk Manager** | Final risk assessment | Optimize risk/reward trade-offs |

## Integration Architecture

### Phase 1: Proof of Concept - Market Analyst

**Goal:** Train the Market Analyst to learn optimal technical indicator combinations.

#### 1.1 Wrap Market Analyst as LitAgent

```python
# tradingagents/agents/optimizable/market_analyst_agent.py
import agentlightning as agl
from typing import Dict, Any
from tradingagents.agents.analysts.market_analyst import create_market_analyst

class LitMarketAnalyst(agl.LitAgent[Dict[str, Any]]):
    """Agent Lightning wrapper for Market Analyst."""

    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config

    def rollout(
        self,
        task: Dict[str, Any],  # {symbol, trade_date, expected_return}
        resources: agl.NamedResources,
        rollout: agl.Rollout
    ) -> float:
        # Extract tunable LLM resource
        llm: agl.LLM = resources["main_llm"]

        # Create market analyst with optimized LLM
        from langchain_openai import ChatOpenAI
        optimized_llm = ChatOpenAI(
            base_url=llm.get_base_url(rollout.rollout_id, rollout.attempt.attempt_id),
            model=llm.model,
            api_key=llm.api_key or "dummy-key",
            **llm.sampling_parameters
        )

        analyst = create_market_analyst(optimized_llm)

        # Build minimal state for analyst
        state = {
            "messages": [],
            "trade_date": task["trade_date"],
            "company_of_interest": task["symbol"]
        }

        # Run analyst
        result = analyst(state)

        # Evaluate: Compare analyst's recommendation with actual returns
        # This is a simplified reward - real implementation would be more nuanced
        reward = self._calculate_reward(
            result["market_report"],
            task["expected_return"]
        )

        return reward

    def _calculate_reward(self, report: str, expected_return: float) -> float:
        """
        Calculate reward based on analyst's recommendation vs actual returns.

        Reward structure:
        - Correct BUY (positive return): +1.0
        - Correct SELL/HOLD (negative return): +0.5
        - Incorrect BUY (negative return): -1.0
        - Incorrect SELL/HOLD (positive return): -0.5
        """
        # Extract recommendation from report
        recommendation = self._extract_recommendation(report)

        if recommendation == "BUY":
            return 1.0 if expected_return > 0 else -1.0
        elif recommendation == "SELL":
            return 0.5 if expected_return < 0 else -0.5
        else:  # HOLD
            return 0.5 if abs(expected_return) < 0.05 else -0.3
```

#### 1.2 Create Training Dataset

```python
# tradingagents/training/datasets/market_analyst_dataset.py
from typing import List, Dict, Any
import pandas as pd

def create_market_analyst_dataset(
    symbols: List[str],
    start_date: str,
    end_date: str,
    lookback_days: int = 30
) -> List[Dict[str, Any]]:
    """
    Create training dataset for Market Analyst.

    Each task includes:
    - symbol: Stock ticker
    - trade_date: Date of analysis
    - expected_return: Actual return over next N days (ground truth)
    """
    tasks = []

    for symbol in symbols:
        # Get historical data
        df = get_historical_data(symbol, start_date, end_date)

        for i in range(lookback_days, len(df) - 5):  # -5 to have future returns
            task = {
                "symbol": symbol,
                "trade_date": df.index[i].strftime("%Y-%m-%d"),
                # Calculate actual 5-day return as ground truth
                "expected_return": (
                    df.iloc[i + 5]["Close"] / df.iloc[i]["Close"] - 1
                )
            }
            tasks.append(task)

    return tasks
```

#### 1.3 Training Script

```python
# tradingagents/training/train_market_analyst.py
import agentlightning as agl
from tradingagents.agents.optimizable.market_analyst_agent import LitMarketAnalyst
from tradingagents.training.datasets.market_analyst_dataset import create_market_analyst_dataset

# Create dataset
train_dataset = create_market_analyst_dataset(
    symbols=["MSFT", "NVDA", "GOOGL", "AAPL", "META"],
    start_date="2023-01-01",
    end_date="2024-12-31"
)

val_dataset = create_market_analyst_dataset(
    symbols=["TSLA", "AMZN"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Configure VERL algorithm
verl_config = {
    "algorithm": {
        "adv_estimator": "grpo",
        "use_kl_in_reward": False
    },
    "data": {
        "train_batch_size": 32,
        "max_prompt_length": 4096,
        "max_response_length": 2048,
    },
    "actor_rollout_ref": {
        "rollout": {
            "name": "vllm",
            "n": 4,  # GRPO group size
            "multi_turn": {"format": "hermes"},
        },
        "actor": {
            "ppo_mini_batch_size": 32,
            "optim": {"lr": 1e-6}
        },
        "model": {
            # Start with a smaller model for faster training
            "path": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        },
    },
    "trainer": {
        "n_gpus_per_node": 1,
        "val_before_train": True,
        "test_freq": 32,
        "save_freq": 64,
        "total_epochs": 3
    },
}

# Create agent
agent = LitMarketAnalyst(llm_config={})

# Initialize trainer with VERL
trainer = agl.Trainer(
    algorithm=agl.algorithm.VERL(verl_config)
)

# Train
trainer.fit(
    agent=agent,
    train_dataset=train_dataset,
    val_dataset=val_dataset
)
```

### Phase 2: Multi-Agent Optimization

#### 2.1 Optimize Bull/Bear Debate Quality

**Challenge:** The Bull and Bear researchers generate arguments, but we don't have direct reward signals for "argument quality."

**Solution:** Use **Judge Decision + Actual Returns** as composite reward.

```python
class LitDebateAgent(agl.LitAgent[Dict[str, Any]]):
    """Optimizes Bull/Bear debate generation."""

    def __init__(self, agent_type: str):  # "bull" or "bear"
        self.agent_type = agent_type

    def rollout(
        self,
        task: Dict[str, Any],
        resources: agl.NamedResources,
        rollout: agl.Rollout
    ) -> float:
        # Run full debate workflow
        bull_args = generate_bull_arguments(task, resources)
        bear_args = generate_bear_arguments(task, resources)
        judge_decision = run_judge(bull_args, bear_args, resources)

        # Reward structure:
        # - If judge agrees with agent type AND actual return matches: +1.0
        # - If judge agrees but return doesn't match: +0.3 (good argument, wrong outcome)
        # - If judge disagrees but return matches agent type: -0.3 (lost debate but was right)
        # - If judge disagrees and return doesn't match: -1.0 (wrong and lost)

        judge_agrees = self._judge_agrees_with_agent(judge_decision)
        outcome_correct = self._outcome_matches_agent(task["expected_return"])

        if judge_agrees and outcome_correct:
            return 1.0
        elif judge_agrees and not outcome_correct:
            return 0.3
        elif not judge_agrees and outcome_correct:
            return -0.3
        else:
            return -1.0
```

#### 2.2 Optimize Research Manager (Judge)

Train the judge to synthesize debates and make better buy/hold/sell decisions.

```python
class LitResearchManager(agl.LitAgent[Dict[str, Any]]):
    """Optimizes Research Manager decision making."""

    def rollout(
        self,
        task: Dict[str, Any],
        resources: agl.NamedResources,
        rollout: agl.Rollout
    ) -> float:
        # Run full analysis pipeline
        market_report = run_market_analyst(task, resources)
        news_report = run_news_analyst(task, resources)
        fundamentals_report = run_fundamentals_analyst(task, resources)
        social_report = run_social_analyst(task, resources)

        # Run debate
        bull_args = run_bull_researcher(task, resources)
        bear_args = run_bear_researcher(task, resources)

        # Judge makes decision (this is what we're optimizing)
        decision = run_research_manager(bull_args, bear_args, resources)

        # Reward based on decision quality vs actual returns
        return calculate_decision_reward(decision, task["expected_return"])
```

#### 2.3 Optimize Trader Position Sizing

```python
class LitTrader(agl.LitAgent[Dict[str, Any]]):
    """Optimizes Trader's position sizing and timing."""

    def rollout(
        self,
        task: Dict[str, Any],
        resources: agl.NamedResources,
        rollout: agl.Rollout
    ) -> float:
        # Get judge recommendation
        judge_decision = task["judge_decision"]  # BUY/HOLD/SELL

        # Trader creates investment plan
        investment_plan = run_trader(judge_decision, task, resources)

        # Extract position size, stop loss, take profit
        position_size = extract_position_size(investment_plan)
        stop_loss = extract_stop_loss(investment_plan)
        take_profit = extract_take_profit(investment_plan)

        # Simulate trade execution
        pnl = simulate_trade(
            decision=judge_decision,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            actual_price_path=task["price_path"]
        )

        # Reward = actual PnL (with risk-adjusted scaling)
        return pnl - 0.1 * position_size  # Penalize excessive position size
```

### Phase 3: Full System Integration

#### 3.1 LangGraph Workflow Wrapper

```python
# tradingagents/agents/optimizable/full_trading_workflow.py
from langgraph.graph import StateGraph, START, END
import agentlightning as agl

class LitTradingAgentsWorkflow(agl.LitAgent[Dict[str, Any]]):
    """
    Full TradingAgents workflow optimized end-to-end.

    Selectively optimizes specific agents while keeping others frozen.
    """

    def __init__(
        self,
        optimize_agents: List[str] = ["market", "judge", "trader"]
    ):
        self.optimize_agents = optimize_agents

    def rollout(
        self,
        task: Dict[str, Any],
        resources: agl.NamedResources,
        rollout: agl.Rollout
    ) -> float:
        # Build TradingAgents graph
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        # Create graph with optimized LLM for specific agents
        ta = TradingAgentsGraph(
            llm_override=self._get_llm_override(resources, rollout),
            optimize_agents=self.optimize_agents
        )

        # Run analysis
        final_state, decision = ta.propagate(
            symbol=task["symbol"],
            trade_date=task["trade_date"]
        )

        # Calculate reward based on decision quality
        reward = self._calculate_trading_reward(
            decision=decision,
            expected_return=task["expected_return"],
            volatility=task["volatility"]
        )

        return reward
```

## Optimization Opportunities by Agent

### 1. Market Analyst

**Current:** Uses fixed set of technical indicators with equal weighting

**Optimization Goal:** Learn which indicators (MACD, RSI, Bollinger, SMA) are most predictive for different market regimes

**Training Signal:** Accuracy of BUY/HOLD/SELL recommendation vs actual returns

**Hyperparameters to Tune:**
- Indicator selection strategy
- Lookback periods for indicators
- Threshold levels for signals

### 2. News Analyst

**Current:** Processes all news equally, may conflate fiscal quarters

**Optimization Goal:**
- Learn to weight different news sources appropriately
- Improve temporal reasoning (fiscal year awareness)
- Better macroeconomic indicator selection

**Training Signal:** How well news sentiment correlates with stock movement

**Improvements:**
- Better table formatting consistency
- Fiscal year calendar awareness (as we just fixed)

### 3. Bull/Bear Researchers

**Current:** Generate arguments based on analyst reports, but no direct quality metric

**Optimization Goal:** Generate more convincing, data-driven arguments that:
- Better identify key risk factors
- Quantify opportunities more precisely
- Use historical analogies more effectively

**Training Signal:** Composite of:
- Judge agreement rate (did they win the debate?)
- Outcome correctness (was their position right in hindsight?)

### 4. Research Manager (Judge)

**Current:** Synthesizes bull/bear debate using reflection memories

**Optimization Goal:** Make better buy/hold/sell decisions by:
- Better weighting bull vs bear arguments
- Improved risk/reward assessment
- More consistent decision making under uncertainty

**Training Signal:** Sharpe ratio of decisions over time

### 5. Trader

**Current:** Creates investment plan with position sizing, stop loss, etc.

**Optimization Goal:** Optimize:
- Position sizing based on conviction level
- Stop loss placement
- Entry/exit timing
- Risk management parameters

**Training Signal:** Risk-adjusted returns (PnL - risk penalty)

### 6. Risk Management Team

**Current:** Three debaters (Aggressive/Neutral/Conservative) with Risk Manager judge

**Optimization Goal:** Calibrate risk tolerance to historical volatility and returns

**Training Signal:** Drawdown avoidance + return maximization

## Implementation Roadmap

### Week 1-2: Environment Setup
- [ ] Install Agent Lightning
- [ ] Set up vLLM serving for RL training
- [ ] Create data pipeline for historical returns
- [ ] Build evaluation framework

### Week 3-4: Phase 1 - Market Analyst PoC
- [ ] Wrap Market Analyst as LitAgent
- [ ] Create training dataset (500-1000 tasks)
- [ ] Configure VERL algorithm
- [ ] Run first training experiment
- [ ] Evaluate on validation set

### Week 5-6: Phase 1 - Iteration & Debugging
- [ ] Analyze training metrics
- [ ] Debug reward signal issues
- [ ] Tune hyperparameters
- [ ] Compare optimized vs baseline

### Week 7-8: Phase 2 - Bull/Bear Debate
- [ ] Wrap Bull/Bear researchers
- [ ] Design composite reward function
- [ ] Create debate quality metrics
- [ ] Train and evaluate

### Week 9-10: Phase 2 - Research Manager
- [ ] Wrap Research Manager
- [ ] Integrate with optimized Bull/Bear
- [ ] Train on historical decisions
- [ ] Backtest on validation period

### Week 11-12: Phase 3 - Full System
- [ ] Integrate all optimized agents
- [ ] End-to-end training
- [ ] Ablation studies (which agents matter most?)
- [ ] Production deployment planning

## Technical Requirements

### Compute Resources

**Minimum:**
- 1x NVIDIA GPU with 24GB VRAM (e.g., RTX 4090, A100)
- 64GB system RAM
- 500GB SSD for checkpoints and data

**Recommended:**
- 4x NVIDIA A100 (40GB or 80GB)
- 256GB system RAM
- 2TB NVMe SSD

### Software Dependencies

```bash
pip install agent-lightning[verl]
pip install vllm>=0.3.0
pip install langchain langgraph
pip install torch>=2.0.0
```

### Data Requirements

**Training Data:**
- Historical stock prices (OHLCV): 2+ years
- News archives: 2+ years
- Social media sentiment: 1+ years
- Fundamental data: 2+ years

**Ground Truth Labels:**
- Future returns (5-day, 10-day, 30-day)
- Volatility realized
- Maximum drawdown

## Expected Improvements

### Quantitative Metrics

**Baseline (Current TradingAgents):**
- Accuracy: ~55-60% (better than random)
- Sharpe Ratio: ~0.8-1.2
- Max Drawdown: ~15-20%

**Post-Optimization Targets:**
- Accuracy: 65-70% (+10-15%)
- Sharpe Ratio: 1.5-2.0 (+50-100%)
- Max Drawdown: <12% (-3-8%)

### Qualitative Improvements

1. **More Consistent Analysis:** Less variance in agent outputs for similar market conditions

2. **Better Risk Calibration:** Stop losses and position sizing better matched to volatility

3. **Improved Debate Quality:** Bull/Bear arguments become more data-driven and specific

4. **Adaptive Strategy:** Agents learn to adjust to different market regimes (bull/bear/sideways)

## Risks & Mitigations

### Risk 1: Overfitting to Historical Data

**Mitigation:**
- Use walk-forward validation
- Train on multiple market regimes
- Regular retraining with recent data
- Ensemble multiple checkpoints

### Risk 2: Reward Signal Design

**Mitigation:**
- Start with simple rewards (BUY accuracy)
- Gradually add complexity (risk-adjusted returns)
- A/B test reward functions
- Use domain expert validation

### Risk 3: Computational Cost

**Mitigation:**
- Start with small models (1.5B parameters)
- Use prompt optimization before fine-tuning
- Selective agent optimization (not all at once)
- Cloud burst for training, local for inference

### Risk 4: Integration Complexity

**Mitigation:**
- Minimal code changes via `agl.emit_xxx()`
- Keep existing TradingAgents code unchanged
- Wrapper pattern for LitAgent integration
- Gradual rollout (one agent at a time)

## Success Metrics

### Phase 1 Success (Market Analyst)
- ✅ Training completes without errors
- ✅ Validation accuracy > baseline by 5%+
- ✅ Inference latency < 2x baseline

### Phase 2 Success (Debate + Judge)
- ✅ Judge decisions improve Sharpe ratio by 20%+
- ✅ Debate quality scores improve (human evaluation)
- ✅ Multi-agent coordination works

### Phase 3 Success (Full System)
- ✅ End-to-end optimization improves overall returns by 30%+
- ✅ Risk-adjusted metrics improve (Sharpe, Sortino, Calmar)
- ✅ System remains stable in production

## Next Steps

1. **Review and Approve Plan:** Stakeholder sign-off on roadmap and resource allocation

2. **Set Up Infrastructure:** Install Agent Lightning, configure vLLM, prepare data pipeline

3. **Start Phase 1:** Begin with Market Analyst PoC as proof of concept

4. **Iterate:** Use learnings from Phase 1 to refine approach for Phases 2 and 3

## Conclusion

Agent Lightning integration offers a systematic path to optimize TradingAgents through reinforcement learning. The modular architecture allows for incremental adoption, starting with a single agent (Market Analyst) and expanding to the full multi-agent system.

Key advantages:
- **Minimal code changes** via wrapper pattern
- **Selective optimization** of specific agents
- **Proven framework** with LangGraph support
- **Measurable improvements** via backtesting

The existing reflection mechanism and memory system provide a strong foundation that Agent Lightning can enhance with systematic RL training.
