"""Flask Application & SSE Streamer for LangGraph ReAct Loop Visualizer.

Exposes a real-time Server-Sent Events (SSE) endpoint to stream agent reasoning steps,
tool invocations, node state transitions, and execution trajectory.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, AsyncGenerator, Dict, Generator, List

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
)


def _safe_json(obj: Any) -> str:
    """Serialize object safely to JSON string."""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def mock_stream_events(query: str) -> List[Dict[str, Any]]:
    """Generate realistic mock ReAct execution events in classic User/Thought/Action/Observation format."""
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

    # Step 1: LLM Reasoning + Action
    events.append({
        "event": "node_change",
        "data": {"node": "call_model", "step": 1, "status": "active"},
    })

    events.append({
        "event": "reasoning",
        "data": {
            "step": 1,
            "node": "call_model",
            "thought": f"QUERY: What is the main context and background regarding '{query}'?",
            "tool_calls": [
                {
                    "name": "search_emails" if "email" in query.lower() else "search",
                    "args": {"query": query},
                    "id": "call_mock_001",
                }
            ],
        },
    })

    # Step 1: Tool Execution & Observation
    events.append({
        "event": "node_change",
        "data": {"node": "tools", "step": 1, "status": "active"},
    })

    tool_used = "search_emails" if "email" in query.lower() else "search"
    events.append({
        "event": "tool_result",
        "data": {
            "step": 1,
            "node": "tools",
            "tool": tool_used,
            "output": f"Found key records for '{query}': All details retrieved, verified, and ready for synthesis.",
            "call_id": "call_mock_001",
        },
    })

    # Step 2: Final Thought & Output
    events.append({
        "event": "node_change",
        "data": {"node": "call_model", "step": 2, "status": "active"},
    })

    events.append({
        "event": "reasoning",
        "data": {
            "step": 2,
            "node": "call_model",
            "thought": "I have gathered enough information.",
            "tool_calls": [],
        },
    })

    final_answer_text = (
        f"Based on the analysis for your request **\"{query}\"**:\n\n"
        "1. **Primary Findings**: The information was retrieved and verified through available tools.\n"
        "2. **Summary**: All details have been structured and processed step-by-step in the ReAct loop.\n\n"
        "Execution completed successfully!"
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
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        from react_agent.context import Context
        from react_agent.graph import graph
        from react_agent.state import InputState

        ctx = Context(model=model_name, system_prompt=system_prompt)
        inputs = InputState(messages=[HumanMessage(content=query)])

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
def index() -> str:
    """Render the main ReAct Visualizer dashboard."""
    return str(render_template("index.html"))


@app.route("/api/config", methods=["GET"])
def get_config() -> Response:
    """Return available models and system defaults."""
    has_google = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    return jsonify({
        "default_model": "google_genai/gemini-3.5-flash-lite",
        "api_keys_status": {
            "google": has_google,
            "openai": has_openai,
            "anthropic": has_anthropic,
        },
        "models": [
            {"id": "google_genai/gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite (Google)", "available": has_google or True},
            {"id": "google_genai/gemini-flash-latest", "name": "Gemini Flash (Google)", "available": has_google or True},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini (OpenAI)", "available": has_openai},
            {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Anthropic)", "available": has_anthropic},
        ],
    })


@app.route("/api/stream", methods=["GET"])
def stream_react_loop() -> Response:
    """SSE endpoint streaming ReAct loop execution events."""
    query = request.args.get("query", "What is ReAct pattern in AI agents?")
    model_name = request.args.get("model", "google_genai/gemini-3.5-flash-lite")
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
        def generate_mock() -> Generator[str, None, None]:
            for evt in mock_stream_events(query):
                evt_name = evt["event"]
                evt_data = _safe_json(evt["data"])
                yield f"event: {evt_name}\ndata: {evt_data}\n\n"
                time.sleep(0.7)  # Realistic delay for UI visualization

        return Response(generate_mock(), mimetype="text/event-stream")

    def generate_real() -> Generator[str, None, None]:
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
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
