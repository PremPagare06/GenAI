import operator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, add_messages, END
from langgraph.prebuilt import ToolNode, InjectedState
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime

from researcher import ResearchReport

load_dotenv()


class CopywriterState(BaseModel):
    messages: Annotated[list, add_messages] = []
    research_reports: Annotated[list[ResearchReport], operator.add] = []


COPYWRITER_PROMPT = """You are a professional copywriter who produces compelling, \
high-engagement content.

Available tools
---------------
review_research_reports – inspect any research reports already gathered
generate_linkedin_post  – write and save a LinkedIn post
generate_blog_post      – write and save a blog article

Instructions
------------
1. Always call review_research_reports first to check for available research.
2. Use that research to ground your writing in real facts and data.
3. Match the tone and structure shown in the examples below.
4. Call the appropriate generation tool to save the final content.

--- LinkedIn post example ---
{linkedin_example}

--- Blog post example ---
{blog_example}

Today's date: {current_datetime}
"""

try:
    _linkedin_example = open("example_content/linkedin.md").read()
    _blog_example = open("example_content/blog.md").read()
except FileNotFoundError:
    _linkedin_example = "(no example available)"
    _blog_example = "(no example available)"


@tool
async def review_research_reports(
    state: Annotated[CopywriterState, InjectedState],
) -> list[str]:
    """Return all available research reports as serialised JSON strings."""
    return [r.model_dump_json() for r in state.research_reports]


@tool
async def generate_linkedin_post(title: str, content: str) -> str:
    """Save a LinkedIn post to disk.

    Args:
        title:   Post title (used as filename).
        content: Post body in Markdown format.

    Returns:
        Path where the file was saved.
    """
    path = f"ai_files/{title}.md"
    with open(path, "w") as fh:
        fh.write(content)
    return f"LinkedIn post saved to {path}"


@tool
async def generate_blog_post(title: str, content: str) -> str:
    """Save a blog post to disk.

    Args:
        title:   Post title (used as filename).
        content: Post body in Markdown format.

    Returns:
        Path where the file was saved.
    """
    path = f"ai_files/{title}.md"
    with open(path, "w") as fh:
        fh.write(content)
    return f"Blog post saved to {path}"


tools = [review_research_reports, generate_linkedin_post, generate_blog_post]
llm = ChatGroq(model="llama-3.3-70b-versatile").bind_tools(
    tools, tool_choice="required"
)


def copywriter_node(state: CopywriterState):
    system = SystemMessage(
        content=COPYWRITER_PROMPT.format(
            current_datetime=datetime.now(),
            linkedin_example=_linkedin_example,
            blog_example=_blog_example,
        )
    )
    response = llm.invoke([system] + state.messages)
    return {"messages": [response]}


def _route(state: CopywriterState) -> str:
    if state.messages[-1].tool_calls:
        return "tools"
    return END


builder = StateGraph(CopywriterState)
builder.add_node("copywriter", copywriter_node)
builder.add_node("tools", ToolNode(tools))
builder.set_entry_point("copywriter")
builder.add_conditional_edges("copywriter", _route, {"tools": "tools", END: END})
builder.add_edge("tools", "copywriter")

graph = builder.compile()
