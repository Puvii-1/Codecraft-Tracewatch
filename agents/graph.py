"""
Wires planner -> coder -> reviewer -> advance into a loop, using
LangGraph's StateGraph. This is the "orchestration" layer.

Flow:
    START -> planner -> coder -> reviewer -> advance --+
                            ^                            |
                            |____ (if fixing/coding) _____|
                                                           |
                                                (if done/failed) -> END

CHANGED FOR TRACEWATCH: `run_codecraft()` now generates one run_id per
session (via tracewatch.new_run_id()) and puts it in the initial state.
Every node downstream reads state["run_id"] when it calls traced_invoke,
so the whole session's LLM calls end up grouped under one run in the
dashboard.
"""
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import planner_node
from agents.coder import coder_node
from agents.reviewer import reviewer_node
from tracewatch import new_run_id


def advance_node(state: AgentState) -> dict:
    """Bookkeeping node: decides whether to move to the next task,
    retry the current one, or stop."""
    if state["approved"]:
        next_index = state["current_task_index"] + 1
        if next_index >= len(state["plan"]):
            return {"status": "done", "history": [" All tasks completed!"]}
        return {
            "current_task_index": next_index,
            "iteration": 0,
            "review_feedback": "",
            "status": "coding",
            "history": [f" Moving to task {next_index + 1}/{len(state['plan'])}"],
        }

    iteration = state["iteration"] + 1
    if iteration >= state["max_iterations"]:
        return {
            "status": "failed",
            "iteration": iteration,
            "history": [f"❌ Gave up after {iteration} attempts on this task"],
        }
    return {
        "status": "fixing",
        "iteration": iteration,
        "history": [f"🔁 Retry attempt {iteration}/{state['max_iterations']}"],
    }


def route_after_advance(state: AgentState) -> str:
    if state["status"] in ("done", "failed"):
        return "end"
    return "coder"  # covers both "coding" (next task) and "fixing" (retry)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("advance", advance_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "reviewer")
    graph.add_edge("reviewer", "advance")
    graph.add_conditional_edges("advance", route_after_advance, {"coder": "coder", "end": END})

    return graph.compile()


def run_codecraft(user_request: str, max_iterations: int = 3):
    """Convenience entry point used by both the CLI and Streamlit UI."""
    app = build_graph()
    initial_state: AgentState = {
        "user_request": user_request,
        "run_id": new_run_id(),
        "plan": [],
        "current_task_index": 0,
        "code_files": {},
        "review_feedback": "",
        "approved": False,
        "iteration": 0,
        "max_iterations": max_iterations,
        "history": [],
        "status": "planning",
    }
    return app.invoke(initial_state)