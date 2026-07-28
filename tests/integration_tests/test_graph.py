import os

import pytest

from react_agent import graph
from react_agent.context import Context

pytestmark = pytest.mark.anyio

raw_key = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("ANTHROPIC_API_KEY")
    or ""
)

has_valid_key = bool(raw_key.strip()) and not raw_key.startswith("your_")


@pytest.mark.skipif(
    not has_valid_key,
    reason="Live integration test requires a valid LLM API Key in environment variables.",
)
async def test_react_agent_simple_passthrough() -> None:
    try:
        res = await graph.ainvoke(
            {"messages": [("user", "Who is the founder of LangChain?")]},  # type: ignore
            context=Context(system_prompt="You are a helpful AI assistant."),
        )

        assert "harrison" in str(res["messages"][-1].content).lower()
    except Exception as e:
        err_msg = str(e)
        if (
            "API key not valid" in err_msg
            or "INVALID_ARGUMENT" in err_msg
            or "400" in err_msg
            or "401" in err_msg
            or "403" in err_msg
        ):
            pytest.skip(f"Skipping live integration test due to unauthenticated API Key: {e}")
        else:
            raise
