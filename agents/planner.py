"""
Planner agent: takes the raw user request and breaks it into an ordered
list of concrete coding tasks. This is the "architect" of the system.

CHANGED FOR TRACEWATCH: `llm.invoke(messages)` became
`traced_invoke(llm, messages, name="planner", run_id=...)` — the only
change needed to start tracing this call. Everything else is identical
to the original CodeCraft planner.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from agents.llm import get_llm
from tracewatch import traced_invoke

PLANNER_SYSTEM_PROMPT = """You are a senior software architect.
Break the user's request into a short, ordered list of concrete coding
tasks. Each task should describe ONE file to create.

Rules:
- 3 to 6 tasks maximum
- Each task must be a single line, plain text, no numbering
- Format: "<filename>: <what it should contain>"
- Keep the whole project small enough to build in one sitting

Example output for "build a todo REST API":
main.py: FastAPI app instance and startup config
models.py: Pydantic Todo model with id, title, done fields
routes.py: CRUD endpoints for /todos using an in-memory list
"""


def planner_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {state['user_request']}"),
    ]
    response = traced_invoke(llm, messages, name="planner", run_id=state["run_id"])

    tasks = [line.strip() for line in response.content.strip().split("\n") if line.strip()]

    return {
        "plan": tasks,
        "current_task_index": 0,
        "code_files": {},
        "status": "coding",
        "history": [f" Planner created {len(tasks)} tasks:\n" + "\n".join(f"  - {t}" for t in tasks)],
    }