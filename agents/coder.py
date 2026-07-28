"""
Coder agent: writes the code for the current task in the plan.
If there's review feedback from a previous failed attempt, it uses that
to fix the code instead of writing from scratch.

CHANGED FOR TRACEWATCH: `llm.invoke(messages)` became
`traced_invoke(llm, messages, name="coder", run_id=...)`. Every retry
attempt on this task gets its own span, still grouped under the same
run_id — this is what lets the dashboard's waterfall show every retry
as a separate bar.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from agents.llm import get_llm
from tracewatch import traced_invoke

CODER_SYSTEM_PROMPT = """You are an expert Python software engineer.
Write clean, working, well-commented code for the given task.

Rules:
- Output ONLY the code, no explanations, no markdown fences
- Include necessary imports
- Follow PEP8
- If given review feedback, fix exactly what it flags
"""


def coder_node(state: AgentState) -> dict:
    task = state["plan"][state["current_task_index"]]
    filename = task.split(":")[0].strip()

    llm = get_llm(temperature=0.3)

    prompt = f"Task: {task}\n\nFull project context (other files already written):\n"
    for fname, code in state["code_files"].items():
        prompt += f"\n--- {fname} ---\n{code}\n"

    if state.get("review_feedback"):
        prompt += f"\n\nPrevious attempt was rejected. Reviewer feedback:\n{state['review_feedback']}\n"
        prompt += "Rewrite the file addressing this feedback."

    messages = [
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = traced_invoke(llm, messages, name="coder", run_id=state["run_id"])
    code = response.content.strip()

    # Strip accidental markdown fences if the model adds them anyway
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:-1])

    updated_files = dict(state["code_files"])
    updated_files[filename] = code

    return {
        "code_files": updated_files,
        "status": "reviewing",
        "history": [f" Coder wrote {filename} ({'fix attempt' if state.get('review_feedback') else 'first draft'})"],
    }