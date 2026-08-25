# Reflection Lab #2 — SQL over an Event Log

**Live dashboard → [arunasivaram.github.io/agentic-ai-labs/02-reflection-with-sqlquery](https://arunasivaram.github.io/agentic-ai-labs/02-reflection-with-sqlquery/)**

Same self-critique loop as [`01-reflection-lab`](../01-reflection-lab/), but
the artifact under review is a **SQL result set**, not a rendered chart. A
cheap model drafts SQL from an English question, SQLite executes it, and a
stronger model critiques the *answer* — first with only the query text, then
with the returned rows — and rewrites the query.

## The point of the two critic variants

The `events` table is an event log: current stock is `SUM(qty_delta)`, and
revenue is `SUM(-qty_delta * unit_price) WHERE action='sale'` because sales
store negative deltas. A naive query looks fine on paper and returns
*negative* revenue. The two critic variants demonstrate why external
feedback matters:

- `refine_sql_text_only` — sees only the SQL. Often approves buggy queries.
- `refine_sql_with_rows` — sees the returned rows. Catches the sign bug.

## Run it

```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-..." > .env
python make_data.py               # seeds inventory.db (deterministic)
python reflect.py                 # default: sales-by-color (sign-bug case)
python reflect.py "Which brand generated the most revenue?"
python reflect.py "What is the current on-hand stock for each product?"
```

Each run prints: v1 SQL and rows, then v2a (text-only critic) SQL + rows,
then v2b (rows-aware critic) SQL + rows. The contrast between v2a and v2b
is the lab.

## Files

- `make_data.py` — seeded synthetic product-events generator (May–Aug 2025)
- `utils.py` — SQLite connection, LLM call helper, `<execute_sql>` tag extractor, tabulate output
- `critic.py` — both refinement variants
- `reflect.py` — CLI driver
