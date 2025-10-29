# Progressive Summarization System

## Overview

This system automatically prevents context overflow through **progressive summarization** instead of hard truncation. It preserves original analyst reports while compressing conversation history intelligently.

## Architecture

### 3-Level Compression Strategy

```
Level 1: LLM Summary (1200 words)
   ↓ Still too long?
Level 2: Aggressive LLM Summary (500 words, bullet points)
   ↓ Still too long?
Level 3: Key Phrase Extraction (30 phrases max)
```

### Key Components

#### 1. `summarize_analyst_report()`
- **Purpose**: Condenses individual analyst reports
- **Strategy**: Progressive compression with automatic retry
- **Fallback**: Key phrase extraction if LLM fails

#### 2. `check_and_summarize_messages()`
- **Purpose**: Compresses entire message history
- **Strategy**: Preserve first (query) + last 2-3 (recent context) + summarize middle
- **Levels**:
  - Level 1: Keep last 3, LLM-summarize middle
  - Level 2: Keep last 2, extract key phrases from middle
  - Level 3: Keep only first + last message

#### 3. `safe_invoke_with_retry()`
- **Purpose**: Automatic retry on context overflow errors
- **Strategy**: Catch token limit errors, progressively compress, retry
- **Max Retries**: 3 attempts with 30% reduction each time

## How It Works

### Before an Analyst Runs

```python
# 1. Trim messages to target limit
messages = trim_messages_for_model(
    state["messages"],
    model_name="claude-sonnet",
    custom_limit=60000  # Conservative limit
)

# 2. Invoke with automatic retry
result = safe_invoke_with_retry(
    chain,
    messages,
    max_retries=3,
    llm_config=config
)
```

### When Context Overflows

```
Attempt 1: 135K tokens → Error!
├─> Reduce limit to 94K (70% of 135K)
├─> Apply Level 1 compression
└─> Retry

Attempt 2: 95K tokens → Still Error!
├─> Reduce limit to 66K (70% of 95K)
├─> Apply Level 2 compression
└─> Retry

Attempt 3: 65K tokens → Success! ✓
```

### After an Analyst Finishes

```python
# 1. Check report length
if len(report) > 5000:
    # 2. Summarize for conversation (appended to messages)
    summarized = summarize_analyst_report(
        analyst_name="Market Analyst",
        full_report=report,
        max_summary_length=2000,
        llm_config=config,
        compression_level=1
    )

    # 3. Keep FULL report for final markdown file
    return {
        "messages": [AIMessage(content=summarized)],  # Compressed
        "market_report": report  # Original preserved!
    }
```

## Key Features

### ✅ Original Content Preservation
- Full reports saved in `final_state["{analyst}_report"]`
- Only conversation messages are compressed
- Markdown reports get full analyst outputs

### ✅ Progressive Compression
- Tries gentlest compression first
- Escalates only if needed
- Never fails due to context limits

### ✅ Intelligent Phrase Extraction
- Extracts key financial terms
- Preserves numbers, percentages, dates
- Maintains recommendations

### ✅ Automatic Error Handling
- Catches token limit errors
- Retries with compression
- Falls back to phrase extraction

## Configuration

### Token Limits

```python
# Context limiter settings
custom_limit = 60000  # Per analyst (was 100K)
preserve_last = 15     # Recent messages to keep

# Summarization thresholds
report_threshold = 5000   # Chars before summarizing
summary_target = 2000     # Target summary length
```

### Compression Levels

| Level | Strategy | Output Size | Use Case |
|-------|----------|-------------|----------|
| 1 | LLM Summary | ~1200 words | Normal operation |
| 2 | Aggressive LLM | ~500 words | High token usage |
| 3 | Key Phrases | ~30 phrases | Emergency fallback |

## Example Output

### Level 1: LLM Summary
```markdown
[Market Analyst - SUMMARY]

**Key Insights:**
- AAPL price at $357.80, down 7.1% from 200 SMA
- MACD bullish crossover confirmed (+0.111)
- RSI at 58.4 indicates neutral momentum
- Recommendation: HOLD with caution
```

### Level 2: Aggressive Summary
```markdown
[Market Analyst - LEVEL 2 SUMMARY]

- Price: $357.80 (-7.1% vs 200 SMA)
- MACD: +0.111 (bullish)
- RSI: 58.4 (neutral)
- Rec: HOLD
```

### Level 3: Key Phrases
```markdown
[Market Analyst - KEY INSIGHTS]

- $357.80
- 7.1% below
- bullish crossover
- MACD +0.111
- RSI 58.4
- neutral momentum
- HOLD recommendation
```

## File Structure

```
tradingagents/agents/utils/
├── summarizer.py              # Progressive summarization logic
├── context_limiter.py         # Token estimation & trimming
└── agent_utils.py             # Tool implementations

tradingagents/agents/analysts/
├── fundamentals_analyst.py    # Uses safe_invoke_with_retry
├── market_analyst.py          # Uses safe_invoke_with_retry
├── news_analyst.py           # Uses safe_invoke_with_retry
└── social_media_analyst.py   # Uses safe_invoke_with_retry

Output:
├── logs/                      # Full debug logs
│   └── analysis_YYYYMMDD_HHMMSS.log
└── analysis_results/SYMBOL/   # Clean markdown reports
    └── SYMBOL_YYYYMMDD_HHMMSS.md
```

## Benefits

1. **Never Fails**: Automatic retry with compression
2. **Preserves Quality**: Full reports saved for final output
3. **Adaptive**: Compresses only as much as needed
4. **Transparent**: Logs show compression levels applied
5. **Graceful Degradation**: Falls back to phrase extraction

## Monitoring

Watch for these log messages:

```
[Fundamentals Analyst] Report is 15000 chars, summarizing...
[Summarizer Level 1] Context at 95,234 tokens (limit: 80,000)
[Summarizer] Reduced from 95,234 to 62,418 tokens
[Safe Invoke] Attempt 1, tokens: 62,418
[Safe Invoke] Context overflow detected: Prompt token count exceeds limit
[Safe Invoke] Retrying with reduced limit: 43,692
[Summarizer Level 2] Context at 43,692 tokens (limit: 43,692)
[Market Analyst] Level 2 compression: extracting key phrases...
```

## Chart Generation (TODO)

The chart reference exists but image generation is not yet implemented:

```markdown
![AAPL Price Chart](./AAPL_20251028_132724_chart.png)
```

**Next Steps**:
1. Add matplotlib/plotly chart generation
2. Save to `analysis_results/{SYMBOL}/` folder
3. Reference in markdown report

---

## Summary

Progressive summarization ensures TradingAgents **never fails due to context limits** while **preserving full analyst reports** for the final markdown output. It's automatic, adaptive, and transparent.
