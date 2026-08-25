# Agentic AI Labs

Portfolio series exploring **agentic AI patterns**, one lab at a time. Each
lab is a small, runnable project that isolates a single pattern and shows
how it changes the behavior of an LLM-driven workflow.

**Live dashboard: [arunasivaram.github.io/agentic-ai-labs](https://arunasivaram.github.io/agentic-ai-labs/)**

## Labs

### [`01-reflection-lab`](./01-reflection-lab/) — reflection over rendered pixels
A cheap model drafts matplotlib code from an English request, `exec()`
renders it to a PNG, a stronger model looks at the *rendered image* (not
the code) and rewrites. The reflection artifact is a chart.

### [`02-reflection-with-sqlquery`](./02-reflection-with-sqlquery/) — reflection over SQL result rows
Same loop, different artifact: cheap model drafts SQL from an English
question, SQLite runs it, the critic judges the *rows that came back* and
rewrites the query. Two critic variants (text-only vs rows-aware) make
the value of grounded feedback visible.

## Common shape across labs

Every lab follows the same skeleton so patterns are easy to compare:

- `make_data.py` — deterministic synthetic data generator (seeded)
- `utils.py` — LLM plumbing + artifact helpers
- `reflect.py` (or equivalent) — the workflow itself, kept short
- `index.html` — self-contained dashboard, published via GitHub Pages
- `README.md` — pitch and run instructions

## Setup

Each lab has its own `requirements.txt` and can be run standalone:

```bash
cd 02-reflection-with-sqlquery/
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-..." > .env
python make_data.py       # seed the local dataset
python reflect.py         # run the loop
```

`requirements-shared.txt` at the repo root is the superset used across
labs — safe to install once into a shared venv if you plan to work on
multiple labs.
