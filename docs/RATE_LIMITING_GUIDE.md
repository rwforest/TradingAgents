# Rate Limiting Guide for Databricks Integration

## Overview

Automatic rate limiting has been added to prevent hitting Databricks Foundation Model API limits and avoid `429 Too Many Requests` errors.

---

## Databricks Rate Limits

According to [Microsoft Azure Databricks documentation](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/foundation-model-apis/limits):

### Pay-per-token Endpoints (Default)
- **150 requests per minute (RPM)**
- **300,000 tokens per minute (TPM)**

### Provisioned Throughput Endpoints
- Custom limits based on provisioned capacity
- Contact Databricks for specific limits

---

## How Rate Limiting Works

### Automatic Delays
The system adds intelligent delays between API calls:

| Model Type | RPM Limit | Min Delay Between Calls |
|-----------|-----------|------------------------|
| Claude Models | 150 | 400ms (~2.5 calls/sec) |
| Llama Models | 150 | 400ms (~2.5 calls/sec) |
| DBRX Models | 150 | 400ms (~2.5 calls/sec) |
| BGE Embeddings | 300 | 200ms (~5 calls/sec) |

### Token Tracking
- Estimates input + output tokens for each request
- Tracks cumulative tokens over rolling 1-minute window
- Automatically waits if approaching 300K token limit

### Request Tracking
- Tracks number of requests over rolling 1-minute window
- Automatically waits if approaching 150 request limit

---

## Usage

### Enabled by Default (Recommended)

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "databricks"
config["deep_think_llm"] = "databricks-claude-sonnet-4-5"
config["quick_think_llm"] = "databricks-claude-sonnet-4-5"

# Rate limiting is ON by default
ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2025-10-27")
```

### Disable Rate Limiting (Not Recommended)

```python
# Only disable if you have provisioned throughput with custom limits
ta = TradingAgentsGraph(
    debug=True,
    config=config,
    enable_rate_limiting=False  # Turn OFF rate limiting
)
```

---

## What Gets Rate Limited

### Quick Think LLM Calls (Most frequent)
- Market Analyst
- Social Media Analyst
- News Analyst
- Fundamentals Analyst
- Bull Researcher
- Bear Researcher
- Trader
- Risk Debators (Risky, Neutral, Safe)

### Deep Think LLM Calls (Less frequent)
- Research Manager (Investment Judge)
- Risk Manager

---

## Performance Impact

### With Rate Limiting (Recommended)
- **Pros:**
  - ✅ Prevents 429 errors
  - ✅ Consistent, predictable performance
  - ✅ Respects API quotas
  - ✅ No failed requests

- **Cons:**
  - ⏱️ Adds ~0.4s delay per LLM call
  - ⏱️ Total analysis time: +3-5 seconds

### Without Rate Limiting (Risky)
- **Pros:**
  - ⚡ Slightly faster

- **Cons:**
  - ❌ May hit rate limits
  - ❌ Causes 429 errors
  - ❌ Requires retry logic
  - ❌ Unpredictable failures

### Example Timing

| Scenario | With Rate Limiting | Without Rate Limiting |
|----------|-------------------|----------------------|
| Market Analyst only | ~8s | ~6s |
| Market + News | ~15s | ~12s |
| All 4 Analysts | ~30s | ~25s |

**Verdict:** The ~5s overhead is worth the reliability.

---

## Rate Limit Monitoring

### Debug Mode
When `debug=True`, you'll see rate limiting logs:

```
[Rate Limiter] Enabled for Databricks API calls
[Rate Limiter] Delay 0.4s between calls for databricks-claude-sonnet-4-5
[Rate Limiter] Delay 0.4s between calls for databricks-claude-sonnet-4-5
...
```

### Verbose Mode
For detailed monitoring, check rate limiter internals:

```python
from tradingagents.agents.utils.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# After running some analyses
print(f"Call history: {limiter.call_history}")
print(f"Token history: {limiter.token_history}")
```

---

## Advanced Configuration

### Custom Rate Limits

If you have custom Databricks limits (e.g., provisioned throughput):

```python
from tradingagents.agents.utils.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Update limits for your model
limiter.rate_limits["your-model-name"] = {
    "rpm": 300,  # Your custom RPM
    "tpm": 600000,  # Your custom TPM
    "delay_between_calls": 0.2,  # Custom delay
}
```

### Per-Model Configuration

Different models can have different limits:

```python
limiter = get_rate_limiter()

# Higher limits for provisioned throughput
limiter.rate_limits["my-provisioned-model"] = {
    "rpm": 500,
    "tpm": 1000000,
    "delay_between_calls": 0.1,
}

# Lower limits for shared endpoints
limiter.rate_limits["shared-endpoint"] = {
    "rpm": 100,
    "tpm": 200000,
    "delay_between_calls": 0.6,
}
```

---

## Troubleshooting

### Still Getting 429 Errors

**Possible causes:**

1. **Multiple processes:** Running multiple TradingAgents instances
   - **Solution:** Rate limiter tracks per-process. Use orchestration layer.

2. **Other API usage:** Other apps using same Databricks workspace
   - **Solution:** Lower the rate limits or coordinate usage.

3. **Burst requests:** Initial burst exceeds limits
   - **Solution:** Already handled by rate limiter, but check logs.

### Rate Limiting Too Aggressive

If you have higher limits (provisioned throughput):

```python
# In your script
from tradingagents.agents.utils.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()
limiter.rate_limits["databricks-claude-sonnet-4-5"]["delay_between_calls"] = 0.2  # Faster
```

### Want Even Safer Limits

For very conservative behavior:

```python
limiter = get_rate_limiter()
limiter.rate_limits["default"]["rpm"] = 100  # Lower from 150
limiter.rate_limits["default"]["delay_between_calls"] = 0.6  # Higher from 0.4
```

---

## Testing Rate Limiting

### Run the Test Script

```bash
source .venv/bin/activate
python test_rate_limiting.py
```

**Expected output:**
```
With rate limiting:    15.2s
Without rate limiting: 12.1s
Difference:            3.1s

Rate limiting added ~3.1s of delays
This prevents hitting Databricks rate limits (150 RPM, 300K TPM)
```

### Manual Testing

```python
import time
from tradingagents.agents.utils.rate_limiter import wait_for_rate_limit

# Test manual rate limiting
for i in range(5):
    print(f"Call {i+1}...")
    wait_for_rate_limit(
        "databricks-claude-sonnet-4-5",
        estimated_tokens=2000,
        verbose=True
    )
    # Your API call here
    time.sleep(0.1)  # Simulate API call
```

---

## Implementation Details

### Files Created

1. **`rate_limiter.py`** - Core rate limiting logic
   - Token estimation
   - Request tracking
   - Delay calculation

2. **`rate_limited_llm.py`** - LLM wrapper
   - Transparent rate limiting
   - Automatic token estimation
   - Compatible with LangChain

3. **`trading_graph.py`** (updated) - Integration
   - Wraps Databricks LLMs automatically
   - Configurable via `enable_rate_limiting` parameter

### Architecture

```
User Request
    ↓
TradingAgentsGraph
    ↓
RateLimitedLLM (wrapper)
    ↓
[Check rate limit] → Wait if needed (400ms min)
    ↓
ChatOpenAI (Databricks)
    ↓
Databricks API
```

---

## Best Practices

### ✅ DO

- Keep rate limiting **enabled** for production
- Use `debug=True` to monitor delays
- Test with sample data before bulk processing
- Plan for the extra 3-5 seconds per analysis

### ❌ DON'T

- Disable rate limiting unless you have provisioned throughput
- Run multiple instances without coordination
- Ignore 429 errors (they indicate rate limit issues)
- Set aggressive custom limits without testing

---

## Migration Guide

### Updating Existing Code

**Before:**
```python
ta = TradingAgentsGraph(debug=True, config=config)
```

**After (no changes needed!):**
```python
# Rate limiting is now automatic
ta = TradingAgentsGraph(debug=True, config=config)
```

**To disable (if needed):**
```python
ta = TradingAgentsGraph(
    debug=True,
    config=config,
    enable_rate_limiting=False
)
```

---

## FAQ

**Q: Does this affect other LLM providers (OpenAI, Anthropic)?**
A: No. Rate limiting only applies when `llm_provider="databricks"`.

**Q: Can I see the rate limiting in action?**
A: Yes! Run with `debug=True` and watch for `[Rate Limiter]` logs.

**Q: What if I have provisioned throughput?**
A: Update the rate limits in `rate_limiter.py` or via `get_rate_limiter()`.

**Q: Does this cost extra?**
A: No. It just spaces out requests. Total API usage is the same.

**Q: Can I customize delays per analyst?**
A: The rate limiter works at the model level, not analyst level. All analysts using the same model share the same rate limit.

---

## Summary

✅ **Automatic rate limiting is now enabled by default**
✅ **Prevents 429 errors from Databricks API**
✅ **Adds minimal overhead (~0.4s per call)**
✅ **Configurable for custom limits**
✅ **No code changes required for existing users**

The rate limiter makes your TradingAgents integration more reliable and production-ready!

---

## References

- [Databricks Foundation Model API Limits](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/foundation-model-apis/limits)
- [Rate Limiting Best Practices](https://learn.microsoft.com/en-us/azure/architecture/patterns/rate-limiting-pattern)
