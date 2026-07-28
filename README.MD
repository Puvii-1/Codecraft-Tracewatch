# TraceWatch — LLM Observability Toolkit

A small, dependency-light observability SDK for LLM applications, plus a
dashboard to visualize what it captures. Built and demonstrated by
instrumenting [CodeCraft](../codecraft), a multi-agent code generator —
but the SDK itself doesn't know or care what it's wrapping.

## Why this exists

Once an LLM app has more than one call in it (an agent with multiple
steps, a RAG pipeline with retries), "did it work" stops being a single
yes/no question. You need to see: which step is slow, which step is
expensive, which step fails most often, and how a single request's
calls relate to each other in time. That's what this project builds —
a miniature version of tools like LangSmith or Helicone.

## Architecture

```
Your LLM app (e.g. CodeCraft)
        │
        │  response = traced_invoke(llm, messages, name="coder", run_id=run_id)
        ▼
┌─────────────────┐
│  tracewatch SDK   │  times the call, extracts token usage,
│  (tracer.py)        │  estimates cost, catches errors
└────────┬─────────┘
         │  writes a Span
         ▼
┌─────────────────┐
│  SQLite            │  spans table: one row per LLM call
│  (storage.py)        │  grouped by run_id
└────────┬─────────┘
         │  read by
         ▼
┌─────────────────┐
│  Dashboard          │  FastAPI + vanilla HTML/CSS/JS
│  (dashboard/)         │  summary stats, charts, waterfall timeline
└─────────────────┘
```

## The core integration point

Wherever your code currently does:

```python
response = llm.invoke(messages)
```

you change it to:

```python
from tracewatch import traced_invoke
response = traced_invoke(llm, messages, name="coder", run_id=run_id)
```

That's it. `traced_invoke` calls the LLM exactly as before, times it,
pulls out token usage from the response, estimates cost, and writes a
record — then returns the _exact same response object_, so nothing
downstream needs to change.

To group multiple calls from one session together (e.g. one full
CodeCraft run's Planner + Coder + Reviewer calls), generate one
`run_id` per session and thread it through:

```python
from tracewatch import new_run_id
run_id = new_run_id()   # once, at the start of a session
```

## What got changed in CodeCraft to add this

See `integration_example/agents/` for the actual modified files, each
with a comment block explaining the change. Summary:

- `state.py` — added a `run_id` field to the shared state
- `graph.py` — generates one `run_id` per `run_codecraft()` call
- `planner.py`, `coder.py`, `reviewer.py` — each `llm.invoke(messages)`
  became `traced_invoke(llm, messages, name=..., run_id=state["run_id"])`

That's the entire diff. No other logic changed.

## Setup

**1. Install the SDK + dashboard dependencies:**

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. See it working immediately with simulated data:**

```powershell
python -m scripts.seed_demo_data
uvicorn dashboard.api:app --reload
```

Open `http://127.0.0.1:8000/` — you'll see ~40 simulated CodeCraft runs
already populated, including a few with transient failures, so every
chart and the waterfall view have real (if synthetic) data to show.

**3. To trace your actual CodeCraft runs instead:**

- Copy `integration_example/agents/` over your CodeCraft project's
  `agents/` folder (or apply the same small diffs shown there to your
  own copy)
- Install `tracewatch` so CodeCraft can import it — either copy the
  `tracewatch/` folder into your CodeCraft project root, or install it
  with `pip install -e .` from this repo if you set up a `pyproject.toml`
- Run CodeCraft as usual (`streamlit run app.py`) — every request now
  writes real spans into `tracewatch.db`
- Point the dashboard at that same database file (set
  `TRACEWATCH_DB_PATH` to wherever CodeCraft is writing it, or run the
  dashboard from the same working directory)

## Dashboard features

- **Summary cards** — total calls, total cost, average latency, error rate
- **Requests over time** — volume chart, bucketed by time window
- **Cost by call type** — which step (planner/coder/reviewer) is
  actually driving spend
- **Latency percentiles** — p50/p95/p99, since averages hide the slow
  outliers that actually hurt user experience
- **Runs list + waterfall timeline** — click any run to see exactly how
  its calls unfolded in time, including retries (shown as extra bars for
  the same step) and failures (shown with a diagonal-stripe pattern)
- **Recent errors** — a running log of what failed and why

## Running tests

```powershell
pytest tests/ -v
```

22 tests covering: cost calculation, storage/query correctness, the
tracer's success/error/list-content-response handling, and all
dashboard API endpoints.
