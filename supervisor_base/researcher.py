import operator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, add_messages, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime

load_dotenv()


class ResearchReport(BaseModel):
    topic: str
    report: str


class ResearcherState(BaseModel):
    messages: Annotated[list, add_messages] = []
    research_reports: Annotated[list[ResearchReport], operator.add] = []


RESEARCHER_PROMPT = """You are a research assistant. Answer every request by \
searching the web and compiling your findings into a structured report.

Available tools
---------------
search_web                  – keyword search; returns title, URL, and a snippet
extract_content_from_webpage – fetch the full text of a URL
generate_research_report    – persist your findings (MUST be called at the end)

Steps
-----
1. Run one or more searches to locate relevant sources.
2. Extract full content from the most useful pages.
3. Synthesise your findings and call generate_research_report.

Report format
-------------
Write in Markdown. End every report with a Citations section:
  [Source Name](URL)

Today's date: {current_datetime}
"""


@tool
def search_web(query: str) -> str:
    """Search the web for the given query and return results."""
    return f"[search_web] Results for: {query}"


@tool
def extract_content_from_webpage(url: str) -> str:
    """Extract the full text content from a webpage URL."""
    return f"[extract_content_from_webpage] Content from: {url}"


@tool
def generate_research_report(topic: str, report: str) -> str:
    """Save a research report to disk."""
    filename = f"ai_files/{topic.replace(' ', '_')}_report.md"
    with open(filename, "w") as fh:
        fh.write(report)
    return f"Research report saved to {filename}"


tools = [search_web, extract_content_from_webpage, generate_research_report]
llm = ChatGroq(model="llama-3.3-70b-versatile").bind_tools(
    tools, tool_choice="required"
)


def researcher_node(state: ResearcherState):
    system = SystemMessage(
        content=RESEARCHER_PROMPT.format(current_datetime=datetime.now())
    )
    response = llm.invoke([system] + state.messages)
    return {"messages": [response]}


def _route(state: ResearcherState) -> str:
    if state.messages[-1].tool_calls:
        return "tools"
    return END


builder = StateGraph(ResearcherState)
builder.add_node("researcher", researcher_node)
builder.add_node("tools", ToolNode(tools))
builder.set_entry_point("researcher")
builder.add_conditional_edges("researcher", _route, {"tools": "tools", END: END})
builder.add_edge("tools", "researcher")

graph = builder.compile()
