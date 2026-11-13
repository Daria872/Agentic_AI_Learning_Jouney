from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
import yfinance as yf

#Creating Agent
def get_stock_price(ticker:str): #Ticker is a shorthand form 
    #EG: APPL for apple
    stock=yf.Ticker(ticker) #display the stock info corresponding to the ticker
    price=stock.info.get("Current Price","Price Not available")
    return {"price":price, "ticker":ticker}

root_agent = Agent(
    model='gemini-3.8-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='You are a stock price assistant. Always use get_stock_price tool.',
    tools=[get_stock_price]
)

#Take a ticket and save it under tool context's state 

def remember_ticker(ticker: str, tool_context: ToolContext) -> str:
    tool_context.state["last_ticker"] = ticker
    return f"Saved {ticker}."

#From the tool context fetch the previous Ticker using the state 
def get_last_ticker(tool_context: ToolContext) -> str:
    return tool_context.state.get("last_ticker", "No ticker saved yet.")

#Agent contains: Model, name, description, instruction, tools

#Milti-Agent

researcher = Agent(
    name="researcher",
    model="gemini-3.8-flash",
    description="Finds relevant facts.",
    instruction="Research the user's question and summarize key facts.",
)

writer = Agent(
    name="writer",
    model="gemini-3.8-flash",
    description="Writes clear answers.",
    instruction="Turn the provided facts into a concise answer.",
)

#Root agent has to be there by default, and it uses functions(tools) or sub_agents to inherit capabilities of another agent
root_agent = Agent(
    name="manager",
    model="gemini-3.8-flash",
    instruction="Delegate research, then ask the writer to prepare the answer.",
    sub_agents=[researcher, writer],
)

#Structured output using pydantic
from pydantic import BaseModel
class StockAnswer(BaseModel):
    ticker: str
    price: float
    summary: str

root_agent = Agent(
    name="stock_agent",
    model="gemini-3.8-flash",
    instruction="Answer with the stock details in the required format.",
    #The pydantic output format is used for structuring outputs. It can be specified by using output_schema while creating the agents
    output_schema=StockAnswer,
    output_key="stock_answer")


#The callback runs before the agent; it records the agent’s name in session state. Returning None lets the agent proceed.

from google.adk.agents.callback_context import CallbackContext
def before_agent(ctx: CallbackContext):
    ctx.state["last_agent"] = ctx.agent_name
    return None  # Continue with the agent

root_agent = Agent(
    name="assistant",
    model="gemini-3.8-flash",
    instruction="Help the user.",
    before_agent_callback=before_agent,
)