"""Flask Application & SSE Streamer for LangGraph ReAct Loop Visualizer.

Exposes a real-time Server-Sent Events (SSE) endpoint to stream agent reasoning steps,
tool invocations, node state transitions, and execution trajectory.
"""

import asyncio
import json
import os
import time
import sys
from typing import Any, AsyncGenerator, Dict, List

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)


def _safe_json(obj: Any) -> str:
    """Serialize object safely to JSON string."""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def mock_stream_events(query: str) -> List[Dict[str, Any]]:
    """Generate realistic mock ReAct execution events for instant demo / offline mode."""
    events = []

    # Start event
    events.append({
        "event": "start",
        "data": {
            "query": query,
            "system_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "simulation",
        },
    })

    # Step 1: LLM Reasoning
    events.append({
        "event": "node_change",
        "data": {"node": "call_model", "step": 1, "status": "active"},
    })

    events.append({
        "event": "reasoning",
        "data": {
            "step": 1,
            "node": "call_model",
            "thought": f"The user is asking: '{query}'. To provide an accurate, up-to-date answer, I need to gather relevant information using available tools.",
            "tool_calls": [
                {
                    "name": "search",
                    "args": {"query": query},
                    "id": "call_mock_001",
                }
            ],
        },
    })

    # Step 1: Tool Execution
    events.append({
        "event": "node_change",
        "data": {"node": "tools", "step": 1, "status": "active"},
    })

    events.append({
        "event": "tool_call",
        "data": {
            "step": 1,
            "node": "tools",
            "tool": "search",
            "args": {"query": query},
            "call_id": "call_mock_001",
        },
    })

    events.append({
        "event": "tool_result",
        "data": {
            "step": 1,
            "node": "tools",
            "tool": "search",
            "output": f"Search results for '{query}': Found recent documentation, benchmarks, and community discussions. All systems operational.",
            "call_id": "call_mock_001",
        },
    })

    # Step 2: LLM Synthesis / Final Answer
    events.append({
        "event": "node_change",
        "data": {"node": "call_model", "step": 2, "status": "active"},
    })

    events.append({
        "event": "reasoning",
        "data": {
            "step": 2,
            "node": "call_model",
            "thought": "I have received the search results. I will now format a clear, comprehensive response for the user.",
            "tool_calls": [],
        },
    })

    final_answer_text = (
        f"Based on the analysis for your query **\"{query}\"**:\n\n"
        "1. **ReAct Loop Execution**: The agent initialized, analyzed the prompt, and dispatched tool requests.\n"
        "2. **Information Gathering**: Relevant web search results and state data were retrieved and processed.\n"
        "3. **Synthesis**: All data points have been verified and integrated into this final output.\n\n"
        "Everything is running smoothly!"
    )

    events.append({
        "event": "final_answer",
        "data": {
            "step": 2,
            "content": final_answer_text,
        },
    })

    events.append({
        "event": "node_change",
        "data": {"node": "__end__", "step": 2, "status": "completed"},
    })

    events.append({
        "event": "complete",
        "data": {
            "total_steps": 2,
            "total_tool_calls": 1,
            "status": "success",
        },
    })

    return events


async def generate_langgraph_events(
    query: str, model_name: str, system_prompt: str
) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE formatted strings from real LangGraph execution."""
    start_time = time.time()

    # Yield start event
    yield f"event: start\ndata: {_safe_json({'query': query, 'model': model_name, 'timestamp': start_time})}\n\n"

    try:
        from react_agent.context import Context
        from react_agent.graph import graph
        from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

        ctx = Context(model=model_name, system_prompt=system_prompt)
        inputs = {"messages": [HumanMessage(content=query)]}

        step_count = 0
        tool_call_count = 0

        # Stream graph steps using astream
        async for chunk in graph.astream(inputs, context=ctx, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                step_count += 1

                # Send node transition event
                yield f"event: node_change\ndata: {_safe_json({'node': node_name, 'step': step_count, 'status': 'active'})}\n\n"
                await asyncio.sleep(0.3)

                messages = node_update.get("messages", [])
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        tool_calls = [
                            {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
                            for tc in (msg.tool_calls or [])
                        ]
                        tool_call_count += len(tool_calls)

                        yield f"event: reasoning\ndata: {_safe_json({'step': step_count, 'node': node_name, 'content': msg.content, 'tool_calls': tool_calls})}\n\n"

                        if not tool_calls:
                            yield f"event: final_answer\ndata: {_safe_json({'step': step_count, 'content': msg.content})}\n\n"

                    elif isinstance(msg, ToolMessage):
                        yield f"event: tool_result\ndata: {_safe_json({'step': step_count, 'node': node_name, 'tool': msg.name, 'output': msg.content, 'call_id': msg.tool_call_id})}\n\n"

                await asyncio.sleep(0.2)

        elapsed = round(time.time() - start_time, 2)
        yield f"event: node_change\ndata: {_safe_json({'node': '__end__', 'step': step_count, 'status': 'completed'})}\n\n"
        yield f"event: complete\ndata: {_safe_json({'total_steps': step_count, 'total_tool_calls': tool_call_count, 'elapsed_sec': elapsed, 'status': 'success'})}\n\n"

    except Exception as e:
        err_msg = str(e)
        yield f"event: error\ndata: {_safe_json({'error': err_msg})}\n\n"


@app.route("/")
def index():
    """Render the main ReAct Visualizer dashboard."""
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return available models and system defaults."""
    has_google = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    return jsonify({
        "default_model": "google_genai/gemini-flash-latest",
        "api_keys_status": {
            "google": has_google,
            "openai": has_openai,
            "anthropic": has_anthropic,
        },
        "models": [
            {"id": "google_genai/gemini-flash-latest", "name": "Gemini Flash (Google)", "available": has_google or True},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini (OpenAI)", "available": has_openai},
            {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Anthropic)", "available": has_anthropic},
        ],
    })


@app.route("/api/stream", methods=["GET"])
def stream_react_loop():
    """SSE endpoint streaming ReAct loop execution events."""
    query = request.args.get("query", "What is ReAct pattern in AI agents?")
    model_name = request.args.get("model", "google_genai/gemini-flash-latest")
    system_prompt = request.args.get(
        "system_prompt",
        "You are a helpful ReAct AI assistant that uses tools to solve user tasks step by step.",
    )
    use_simulation = request.args.get("simulation", "false").lower() == "true"

    # Check if API keys are available; if not, fall back to simulation gracefully
    has_keys = bool(
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )

    if use_simulation or not has_keys:
        def generate_mock():
            for evt in mock_stream_events(query):
                evt_name = evt["event"]
                evt_data = _safe_json(evt["data"])
                yield f"event: {evt_name}\ndata: {evt_data}\n\n"
                time.sleep(0.7)  # Realistic delay for UI visualization

        return Response(generate_mock(), mimetype="text/event-stream")

    def generate_real():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        gen = generate_langgraph_events(query, model_name, system_prompt)

        try:
            while True:
                item = loop.run_until_complete(gen.__anext__())
                yield item
        except StopAsyncIteration:
            pass
        finally:
            loop.close()

    return Response(generate_real(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 ReAct Loop Visualizer starting at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
