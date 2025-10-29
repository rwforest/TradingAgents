# Chat Endpoints & API Configuration

This document provides a comprehensive overview of all Chat endpoints, API configurations, and API key requirements in the TradingAgents codebase.

## Chat Endpoint Implementations

### Main Chat Endpoint Table

| Endpoint | File | Class/Function Name | Key Required? |
|----------|------|---------------------|---------------|
| ChatOpenAI | [tradingagents/graph/trading_graph.py](tradingagents/graph/trading_graph.py#L76-L77) | `ChatOpenAI` | Yes - `OPENAI_API_KEY` |
| ChatAnthropic | [tradingagents/graph/trading_graph.py](tradingagents/graph/trading_graph.py#L79-L80) | `ChatAnthropic` | Yes - Environment variable |
| ChatGoogleGenerativeAI | [tradingagents/graph/trading_graph.py](tradingagents/graph/trading_graph.py#L82-L83) | `ChatGoogleGenerativeAI` | Yes - Environment variable |
| ChatOpenAI (Reflection) | [tradingagents/graph/reflection.py](tradingagents/graph/reflection.py#L4) | `ChatOpenAI` | Yes - `OPENAI_API_KEY` |
| ChatOpenAI (Signals) | [tradingagents/graph/signal_processing.py](tradingagents/graph/signal_processing.py#L3) | `ChatOpenAI` | Yes - `OPENAI_API_KEY` |
| ChatOpenAI (Setup) | [tradingagents/graph/setup.py](tradingagents/graph/setup.py#L4) | `ChatOpenAI` | Yes - `OPENAI_API_KEY` |

## API Provider Configuration

### Supported Providers & Endpoints

| Provider | Provider Key | Default Endpoint URL | Custom URL Support | Model Examples |
|----------|--------------|---------------------|-------------------|----------------|
| **OpenAI** | `"openai"` | `https://api.openai.com/v1` | Yes (via `base_url`) | gpt-4o, o1, o3, o4-mini, gpt-4o-mini |
| **Anthropic** | `"anthropic"` | `https://api.anthropic.com/` | Yes (via `base_url`) | claude-3-5-sonnet, claude-opus-4, claude-3-5-haiku |
| **Google** | `"google"` | `https://generativelanguage.googleapis.com/v1` | No (hardcoded) | gemini-2.0-flash, gemini-2.5-pro |
| **OpenRouter** | `"openrouter"` | `https://openrouter.ai/api/v1` | Yes (via `base_url`) | deepseek-chat-v3, meta-llama models |
| **Ollama** | `"ollama"` | `http://localhost:11434/v1` | Yes (via `base_url`) | llama3.1, llama3.2, qwen3 |

### Default Configuration

**Configuration File:** [tradingagents/default_config.py](tradingagents/default_config.py#L11-L15)

```python
"llm_provider": "openai",
"deep_think_llm": "o4-mini",
"quick_think_llm": "gpt-4o-mini",
"backend_url": "https://api.openai.com/v1",
```

## API Key Configuration

### Required Environment Variables

| Environment Variable | Purpose | Required For | Example File |
|---------------------|---------|--------------|--------------|
| `OPENAI_API_KEY` | OpenAI API authentication | ChatOpenAI instances | [.env.example](.env.example#L2) |
| `ALPHA_VANTAGE_API_KEY` | Market data fetching | Data vendor operations | [.env.example](.env.example#L1) |

### Environment Setup

Create a `.env` file based on `.env.example`:

```bash
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
OPENAI_API_KEY=your_openai_key_here
```

## Chat Endpoint Instantiation

### Provider Selection Logic

**File:** [tradingagents/graph/trading_graph.py](tradingagents/graph/trading_graph.py#L75-L85)

The system selects the appropriate Chat endpoint based on the `llm_provider` configuration:

- **OpenAI/Ollama/OpenRouter:** Uses `ChatOpenAI` with custom `base_url`
- **Anthropic:** Uses `ChatAnthropic` with custom `base_url`
- **Google:** Uses `ChatGoogleGenerativeAI` (no custom URL support)

### Example Instantiation

```python
# OpenAI/Ollama/OpenRouter
self.deep_thinking_llm = ChatOpenAI(
    model=self.config["deep_think_llm"],
    base_url=self.config["backend_url"]
)

# Anthropic
self.deep_thinking_llm = ChatAnthropic(
    model=self.config["deep_think_llm"],
    base_url=self.config["backend_url"]
)

# Google
self.deep_thinking_llm = ChatGoogleGenerativeAI(
    model=self.config["deep_think_llm"]
)
```

## Files Using Chat Endpoints

### Core Implementation Files

| File | Purpose | Chat Endpoint Used | Lines |
|------|---------|-------------------|-------|
| [tradingagents/graph/trading_graph.py](tradingagents/graph/trading_graph.py) | Main LLM orchestrator | ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI | 75-85 |
| [tradingagents/graph/setup.py](tradingagents/graph/setup.py) | Quick/deep thinking setup | ChatOpenAI | 4, 19-20 |
| [tradingagents/graph/reflection.py](tradingagents/graph/reflection.py) | Reflective analysis | ChatOpenAI | 4, 10 |
| [tradingagents/graph/signal_processing.py](tradingagents/graph/signal_processing.py) | Signal processing | ChatOpenAI | 3, 9 |

### Agent Files (Receive LLM as Parameter)

| Agent | File | LLM Parameter |
|-------|------|---------------|
| Market Analyst | [tradingagents/agents/analysts/market_analyst.py](tradingagents/agents/analysts/market_analyst.py) | Passed from trading_graph |
| News Analyst | [tradingagents/agents/analysts/news_analyst.py](tradingagents/agents/analysts/news_analyst.py) | Passed from trading_graph |
| Social Media Analyst | [tradingagents/agents/analysts/social_media_analyst.py](tradingagents/agents/analysts/social_media_analyst.py) | Passed from trading_graph |
| Fundamentals Analyst | [tradingagents/agents/analysts/fundamentals_analyst.py](tradingagents/agents/analysts/fundamentals_analyst.py) | Passed from trading_graph |
| Bull Researcher | [tradingagents/agents/researchers/bull_researcher.py](tradingagents/agents/researchers/bull_researcher.py) | Passed from trading_graph |
| Bear Researcher | [tradingagents/agents/researchers/bear_researcher.py](tradingagents/agents/researchers/bear_researcher.py) | Passed from trading_graph |

## CLI Integration

### Provider Selection

**File:** [cli/utils.py](cli/utils.py#L242-L276)

The CLI provides interactive provider selection with predefined base URLs for each provider.

### Configuration Assembly

**File:** [cli/main.py](cli/main.py#L742-L749)

The CLI assembles the final configuration:

```python
config = DEFAULT_CONFIG.copy()
config["max_debate_rounds"] = selections["research_depth"]
config["quick_think_llm"] = selections["shallow_thinker"]
config["deep_think_llm"] = selections["deep_thinker"]
config["backend_url"] = selections["backend_url"]
config["llm_provider"] = selections["llm_provider"].lower()
```

## Configuration Management

### Global Config System

**File:** [tradingagents/dataflows/config.py](tradingagents/dataflows/config.py)

Functions:
- `get_config()` - Retrieve current configuration
- `set_config(config)` - Update configuration
- `initialize_config()` - Initialize with default config

## Additional API Endpoints

### OpenAI REST API (Non-Chat)

**File:** [tradingagents/dataflows/openai.py](tradingagents/dataflows/openai.py)

| Function | Purpose | API Endpoint | Key Required? |
|----------|---------|--------------|---------------|
| `get_stock_news_openai()` | Fetch stock news | `client.responses.create()` | Yes - `OPENAI_API_KEY` |
| `get_global_news_openai()` | Fetch global news | `client.responses.create()` | Yes - `OPENAI_API_KEY` |
| `get_fundamentals_openai()` | Fetch fundamentals | `client.responses.create()` | Yes - `OPENAI_API_KEY` |

## Summary

- **3 main Chat endpoint classes** are used: `ChatOpenAI`, `ChatAnthropic`, `ChatGoogleGenerativeAI`
- **5 provider options** are supported with different API endpoints
- **All Chat endpoints require API keys** set via environment variables
- **Dynamic provider selection** allows runtime switching between providers
- **Centralized configuration** in `trading_graph.py` manages all LLM instantiation

For more details on configuration, see [tradingagents/default_config.py](tradingagents/default_config.py).
