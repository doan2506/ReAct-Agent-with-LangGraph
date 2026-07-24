import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def run():
    # Retrieve user query from command line argument or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Tổng hợp giúp tôi các email chưa đọc trong inbox của tôi"

    print("=" * 60)
    print("Running Gmail ReAct Agent")
    print(f"Query: {query}")
    print("=" * 60)

    # Check for LLM API Key
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("\nWARNING: No LLM API key detected in your .env file!")
        print("Please add GOOGLE_API_KEY (or OPENAI_API_KEY) to your .env file before running.\n")
        return

    from react_agent.graph import graph
    from react_agent.context import Context

    try:
        inputs = {"messages": [("user", query)]}
        print("Processing mailbox and analyzing unread emails...\n")

        # Invoke the ReAct agent graph with context
        result = await graph.ainvoke(inputs, context=Context())

        from react_agent.utils import get_message_text

        # Extract and display the final message text
        final_message = result["messages"][-1]
        text_content = get_message_text(final_message)
        print("=" * 60)
        print("Agent Response:")
        print("=" * 60)
        print(text_content)
        print("=" * 60)

    except Exception as e:
        print(f"\nError during graph execution: {e}")


if __name__ == "__main__":
    asyncio.run(run())
