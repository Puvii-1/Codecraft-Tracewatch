"""
Reviewer agent: checks the most recently written file in two passes.
1. A hard syntax check (py_compile) - catches broken code for free,
   no LLM call needed.
2. An LLM review for logic/quality issues, only if syntax passes.

CHANGED FOR TRACEWATCH: `llm.invoke(messages)` became
`traced_invoke(llm, messages, name="reviewer", run_id=...)`. Note the
free syntax check above is NOT traced — it costs no LLM call, so there's
nothing to observe there. Only actual model calls get spans.
"""
import ast
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from agents.llm import get_llm
from tracewatch import traced_invoke

REVIEWER_SYSTEM_PROMPT = """You are a strict senior code reviewer.
Review the given Python file for correctness, obvious bugs, and whether
it fulfills its stated task.

Respond in EXACTLY this format:
VERDICT: APPROVED or REJECTED
FEEDBACK: <one or two sentences. If approved, say "Looks good." If
rejected, be specific and actionable so the coder can fix it.>
"""


def _syntax_ok(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def reviewer_node(state: AgentState) -> dict:
    task = state["plan"][state["current_task_index"]]
    filename = task.split(":")[0].strip()
    code = state["code_files"][filename]

    ok, syntax_error = _syntax_ok(code)
    if not ok:
        return {
            "approved": False,
            "review_feedback": syntax_error,
            "status": "fixing",
            "history": [f" Reviewer REJECTED {filename}: {syntax_error}"],
        }

    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=f"Task: {task}\n\nCode:\n{code}"),
    ]
    response = traced_invoke(llm, messages, name="reviewer", run_id=state["run_id"])
    text = response.content.strip()

    approved = "VERDICT: APPROVED" in text.upper()
    feedback_line = next((l for l in text.split("\n") if l.upper().startswith("FEEDBACK")), "FEEDBACK: none")
    feedback = feedback_line.split(":", 1)[-1].strip()

    verdict_emoji = "✅" if approved else "🔍"
    return {
        "approved": approved,
        "review_feedback": feedback,
        "status": "coding" if approved else "fixing",
        "history": [f"{verdict_emoji} Reviewer {'APPROVED' if approved else 'REJECTED'} {filename}: {feedback}"],
    }