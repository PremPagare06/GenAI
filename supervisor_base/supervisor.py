import operator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, add_messages, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import BaseModel
from typing import Annotated, Literal
from datetime import datetime

from researcher import graph as researcher_graph, ResearchReport
from copywriter import graph as copywriter_graph

load_dotenv()


class SupervisorState(BaseModel):
    messages: Annotated[list, add_messages] = []
    research_reports: Annotated[list[ResearchReport], operator.add] = []
    next_agent: str = "supervisor"


class RouteDecision(BaseModel):
    """Decide which agent to invoke next, or finish."""

    next: Literal["researcher", "copywriter", "FINISH"]
    instructions: str


SUPERVISOR_PROMPT = """You are a project coordinator managing a research-and-writing pipeline.

You have two specialist agents at your disposal:
  • researcher  – searches the web and produces structured research reports
  • copywriter  – writes LinkedIn posts and blog articles using those reports

Workflow
--------
1. Understand what the user wants to produce (a blog post, a LinkedIn post, etc.).
2. If the request needs up-to-date facts or real-world data, dispatch the researcher first.
3. Once research is available (or if none is needed), dispatch the copywriter.
4. When the content has been saved to disk, respond with FINISH.

Always include clear, specific instructions for the agent you are dispatching.

Today's date: {current_datetime}
"""


llm = ChatGroq(model="llama-3.3-70b-versatile").with_structured_output(RouteDecision)


def supervisor_node(state: SupervisorState):
    system = SystemMessage(
        content=SUPERVISOR_PROMPT.format(current_datetime=datetime.now())
    )
    decision: RouteDecision = llm.invoke([system] + state.messages)

    if decision.next == "FINISH":
        return Command(goto=END)

    instruction_msg = HumanMessage(content=decision.instructions)
    return Command(
        goto=decision.next,
        update={"messages": [instruction_msg], "next_agent": decision.next},
    )


def run_researcher(state: SupervisorState):
    """Invoke the researcher sub-graph and merge results back."""
    result = researcher_graph.invoke({"messages": state.messages})
    return {
        "messages": result["messages"],
        "research_reports": result.get("research_reports", []),
    }


def run_copywriter(state: SupervisorState):
    """Invoke the copywriter sub-graph and merge results back."""
    result = copywriter_graph.invoke(
        {
            "messages": state.messages,
            "research_reports": state.research_reports,
        }
    )
    return {"messages": result["messages"]}


builder = StateGraph(SupervisorState)

builder.add_node("supervisor", supervisor_node)
builder.add_node("researcher", run_researcher)
builder.add_node("copywriter", run_copywriter)

builder.set_entry_point("supervisor")

builder.add_edge("researcher", "supervisor")
builder.add_edge("copywriter", "supervisor")

graph = builder.compile()
