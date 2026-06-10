import asyncio
import textwrap
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.types import RunnableConfig

from supervisor import graph as supervisor_graph, SupervisorState

load_dotenv()

SEPARATOR = "-" * 60

AGENT_LABELS = {
    "researcher": " Researcher",
    "copywriter": "  Copywriter",
    "supervisor": " Supervisor",
}


def _print_header(label: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {label}")
    print(SEPARATOR)


def _print_message(agent: str, text: str) -> None:
    label = AGENT_LABELS.get(agent, agent.capitalize())
    _print_header(label)
    # Wrap long lines for readability
    for line in text.splitlines():
        print(textwrap.fill(line, width=80) if line.strip() else "")


def _detect_agent(namespace) -> str:
    """Derive which agent produced a chunk from its subgraph namespace."""
    ns = str(namespace)
    if "researcher" in ns:
        return "researcher"
    if "copywriter" in ns:
        return "copywriter"
    return "supervisor"


async def run_and_stream(user_text: str, config: RunnableConfig) -> None:
    """Feed a user message to the supervisor graph and print streamed output."""
    graph_input = SupervisorState(messages=[HumanMessage(content=user_text)])

    current_agent: str | None = None
    accumulated_text = ""
    accumulated_tool_args = ""
    current_tool_name = ""

    async for chunk in supervisor_graph.astream(
        input=graph_input,
        stream_mode="messages",
        subgraphs=True,
        config=config,
    ):
        namespace, (msg_chunk, _) = chunk

        from langchain_core.messages import AIMessageChunk

        if not isinstance(msg_chunk, AIMessageChunk):
            continue

        agent = _detect_agent(namespace)

        if current_agent != agent:
            if accumulated_text.strip():
                _print_message(current_agent, accumulated_text.strip())
            accumulated_text = ""
            current_agent = agent

        if msg_chunk.tool_call_chunks:
            chunk_data = msg_chunk.tool_call_chunks[0]
            tool_name = chunk_data.get("name", "")
            args_fragment = chunk_data.get("args", "")

            if tool_name and tool_name != current_tool_name:
                # New tool invocation
                if accumulated_tool_args.strip():
                    print(f"    args: {accumulated_tool_args.strip()}")
                print(f"\n   Tool call -> {tool_name}")
                current_tool_name = tool_name
                accumulated_tool_args = ""

            accumulated_tool_args += args_fragment

        if msg_chunk.response_metadata.get("finish_reason") == "tool_calls":
            if accumulated_tool_args.strip():
                print(f"    args: {accumulated_tool_args.strip()}")
                accumulated_tool_args = ""
            print("   Tool call complete\n")

        if msg_chunk.content:
            accumulated_text += msg_chunk.content

    # Flush the final agent's buffered text
    if accumulated_text.strip() and current_agent:
        _print_message(current_agent, accumulated_text.strip())

    print(f"\n{SEPARATOR}\n")


async def main() -> None:
    config = RunnableConfig(configurable={"thread_id": "1", "recursion_limit": 50})

    print("\n" + "=" * 60)
    print("   Multi-Agent Supervisor")
    print("  Type your request below.  'exit' or 'quit' to stop.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("\nGoodbye!")
            break

        await run_and_stream(user_input, config)


if __name__ == "__main__":
    asyncio.run(main())
