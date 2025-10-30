import dspy
from pydantic import BaseModel
from dspy.dsp.utils.utils import dotdict
from dspy.adapters.types.tool import Tool
import os

def get_dspy_model_name(langchain_model_name: str) -> str:
    """
    Convert LangChain model name to DSPy/LiteLLM format.
    Adds provider prefix if not already present and sets required env vars.
    """
    # If model already has a provider prefix (contains /), return as-is
    if '/' in langchain_model_name:
        return langchain_model_name

    # Get provider from environment or config
    provider = os.getenv("LLM_PROVIDER", "openai")

    # Set up Databricks environment variables for LiteLLM
    if provider == "databricks":
        databricks_url = os.getenv("DATABRICKS_BASE_URL")
        databricks_token = os.getenv("DATABRICKS_TOKEN")

        # Remove trailing slash to avoid double slash in URL
        if databricks_url:
            databricks_url = databricks_url.rstrip('/')
            # Add /serving-endpoints path if not already present
            if not databricks_url.endswith('/serving-endpoints'):
                databricks_url = f"{databricks_url}/serving-endpoints"
            os.environ["DATABRICKS_API_BASE"] = databricks_url

        if databricks_token:
            os.environ["DATABRICKS_API_KEY"] = databricks_token

        model_name = f"databricks/{langchain_model_name}"
        print(f"DEBUG: Converting model '{langchain_model_name}' to '{model_name}'")
        print(f"DEBUG: DATABRICKS_API_BASE={os.environ.get('DATABRICKS_API_BASE')}")
        return model_name
    elif provider == "anthropic":
        return f"anthropic/{langchain_model_name}"
    elif provider == "openai":
        # OpenAI models don't need prefix in most cases
        return langchain_model_name
    else:
        # Default: add provider prefix
        return f"{provider}/{langchain_model_name}"

def langchain_to_dspy_tool(langchain_tool):
    """Converts a LangChain tool to a DSPy Tool."""
    try:
        # Try to use the built-in converter if available
        return Tool.from_langchain(langchain_tool)
    except AttributeError:
        # Fallback: create a simple wrapper function
        def tool_func(**kwargs):
            return langchain_tool.run(kwargs)
        tool_func.__name__ = langchain_tool.name
        tool_func.__doc__ = langchain_tool.description
        return tool_func

class AnalystSignature(dspy.Signature):
    """
You are a helpful AI assistant, collaborating with other assistants.
Use the provided tools to progress towards answering the question.
If you are unable to fully answer, that's OK; another assistant with different tools
will help where you left off. Execute what you can to make progress.
If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,
prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop.
You have access to the following tools: {tool_names}.

{system_message}

For your reference, the current date is {current_date}. The company we want to look at is {ticker}.

Here is the message history:
{messages}
    """
    system_message = dspy.InputField(desc="The system message for the analyst.")
    tool_names = dspy.InputField(desc="The names of the available tools.")
    current_date = dspy.InputField(desc="The current date.")
    ticker = dspy.InputField(desc="The company ticker.")
    messages = dspy.InputField(desc="The message history as a string.")

    report = dspy.OutputField(desc="The analyst's report.")

class AnalystModule(dspy.Module):
    """
    DSPy Module for the Analyst agents.
    This module uses the ReAct agent to generate a report using the provided tools.
    """
    def __init__(self, tools):
        super().__init__()
        dspy_tools = [langchain_to_dspy_tool(tool) for tool in tools]
        self.agent = dspy.ReAct(AnalystSignature, tools=dspy_tools)

    def forward(self, system_message, tool_names, current_date, ticker, messages):
        result = self.agent(
            system_message=system_message,
            tool_names=tool_names,
            current_date=current_date,
            ticker=ticker,
            messages=messages
        )
        return dotdict({"report": result.report})
