import dspy
from pydantic import BaseModel
from dsp.utils.utils import dotdict

def pydantic_to_dspy_signature(pydantic_model: BaseModel, docstring: str) -> dspy.Signature:
    """Converts a Pydantic model to a dspy.Signature."""
    inputs = {}
    if pydantic_model:
        for field_name, field_model in pydantic_model.__fields__.items():
            inputs[field_name] = dspy.InputField(
                desc=field_model.description or ""
            )

    outputs = {"output": dspy.OutputField()}

    # Create a new signature class dynamically
    return type(
        f"{pydantic_model.__name__}Signature",
        (dspy.Signature,),
        {
            "__doc__": docstring,
            **inputs,
            **outputs
        }
    )

class LangChainTool(dspy.Tool):
    """A wrapper for LangChain tools to make them compatible with dspy."""
    def __init__(self, tool):
        self._tool = tool
        super().__init__(
            name=self._tool.name,
            description=self._tool.description,
            input_schema=pydantic_to_dspy_signature(self._tool.args_schema, self._tool.description),
        )

    def __call__(self, **kwargs):
        return self._tool.run(kwargs)

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
        dspy_tools = [LangChainTool(tool) for tool in tools]
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
