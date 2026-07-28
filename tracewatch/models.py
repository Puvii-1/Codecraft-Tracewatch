"""
A "span" is one traced LLM call — the fundamental unit TraceWatch records.
Multiple spans sharing a run_id form a "run" (e.g. one full CodeCraft
session: planner call, then several coder/reviewer calls).
"""
from dataclasses import dataclass, field
from typing import Optional
import uuid
import time


@dataclass
class Span:
    id: str
    run_id: str
    name: str                      # e.g. "planner", "coder", "reviewer"
    model: str
    start_time: float               # unix timestamp
    end_time: Optional[float] = None
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    status: str = "running"          # "running" | "success" | "error"
    error_message: Optional[str] = None
    prompt_preview: str = ""
    response_preview: str = ""

    @staticmethod
    def new(run_id: str, name: str, model: str, prompt_preview: str = "") -> "Span":
        return Span(
            id=str(uuid.uuid4()),
            run_id=run_id,
            name=name,
            model=model,
            start_time=time.time(),
            prompt_preview=prompt_preview[:500],
        )

    def finish_success(self, response_preview: str, input_tokens: Optional[int], output_tokens: Optional[int], cost_usd: Optional[float]):
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.status = "success"
        self.response_preview = response_preview[:500]
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_usd = cost_usd

    def finish_error(self, error_message: str):
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.status = "error"
        self.error_message = error_message[:1000]


def new_run_id() -> str:
    return str(uuid.uuid4())