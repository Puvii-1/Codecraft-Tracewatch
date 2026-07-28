"""
Shared state that flows through every node in the LangGraph.
Every agent (planner, coder, reviewer, fixer) reads from and writes to this.

CHANGED FOR TRACEWATCH: added `run_id`, generated once per CodeCraft
session, so every traced LLM call in this run can be grouped together
in the dashboard's waterfall view.
"""
from typing import TypedDict, List, Dict, Annotated
import operator


class AgentState(TypedDict):
    # The original ask from the user, e.g. "Build a REST API for a todo app"
    user_request: str

    # NEW: identifies this CodeCraft session so TraceWatch can group all
    # of its LLM calls (planner + every coder/reviewer attempt) together.
    run_id: str

    # List of tasks the planner breaks the request into, e.g.
    # ["Create FastAPI app skeleton", "Add Todo model", "Add CRUD endpoints"]
    plan: List[str]

    # Which task index we are currently working on
    current_task_index: int

    # filename -> code content, accumulates as tasks complete
    code_files: Dict[str, str]

    # Latest reviewer feedback for the current file
    review_feedback: str

    # Whether the reviewer approved the current file
    approved: bool

    # How many fix attempts we've made on the current task
    iteration: int
    max_iterations: int

    # Human-readable log of what happened, useful for the Streamlit UI.
    # `operator.add` means new entries get appended, not overwritten,
    # every time a node returns a "history" key.
    history: Annotated[List[str], operator.add]

    # "planning" | "coding" | "reviewing" | "fixing" | "done" | "failed"
    status: str