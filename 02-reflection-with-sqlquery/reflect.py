"""The SQL reflection loop: draft -> run -> critique the answer -> redraft.

Runs both critic variants back-to-back so the pedagogical contrast is
visible: the text-only critic often misses semantic bugs (e.g. a negative
'total sales' from summing signed qty_delta values) while the with-rows
critic catches them because it sees the wrong-looking rows.

Run it:
    python reflect.py
    python reflect.py "Which brand generated the most revenue?"
"""

import sys

import critic
import utils

GEN_MODEL     = "claude-haiku-4-5"      # cheap, fast: writes v1
REFLECT_MODEL = "claude-sonnet-5"       # stronger eyes: critiques and rewrites

DB_PATH = "inventory.db"

SCHEMA = """
Table: events

  id            INTEGER
  product_id    INTEGER
  product_name  TEXT
  brand         TEXT
  category      TEXT
  color         TEXT
  action        TEXT     one of: 'insert', 'restock', 'sale', 'price_update'
  qty_delta     INTEGER
  unit_price    REAL     nullable
  notes         TEXT     nullable
  ts            TEXT     'YYYY-MM-DD HH:MM:SS'
"""


# --- step 1: draft ---------------------------------------------------------

def generate_sql(question: str, model: str) -> str:
    prompt = f"""You are a SQL assistant for SQLite.

Write a single SELECT (or WITH ... SELECT) that answers the user's question,
using only the `events` table described below.

User question:
{question}

Schema:
{SCHEMA}

Return ONLY the SQL, wrapped exactly like this, with no explanation:

<execute_sql>
-- your SELECT here
</execute_sql>
"""
    return utils.get_response(model, prompt)


# --- step 2: run -----------------------------------------------------------

def try_run(conn, tagged: str, label: str):
    """Extract SQL from tags, run it, print rows. Returns (rows, cols) or (None, None)."""
    sql = utils.extract_sql(tagged)
    if not sql:
        print(f"!! [{label}] no <execute_sql> block found")
        return None, None
    utils.print_sql(sql)
    try:
        rows, cols = utils.run_sql(conn, sql)
    except Exception as e:
        print(f"!! [{label}] SQL failed: {type(e).__name__}: {e}")
        return None, None
    utils.print_rows(rows, cols)
    return rows, cols


# --- driver ----------------------------------------------------------------

DEFAULT_QUESTION = "Which color of product has the highest total sales?"


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or DEFAULT_QUESTION
    conn = utils.open_db(DB_PATH)

    utils.banner("v1: draft SQL from the question")
    print(f"question: {question}")
    tagged_v1 = generate_sql(question, GEN_MODEL)
    rows_v1, cols_v1 = try_run(conn, tagged_v1, "v1")
    if rows_v1 is None:
        return 1
    sql_v1 = utils.extract_sql(tagged_v1)

    utils.banner("v2a: reflect on the SQL TEXT ONLY (no rows)")
    fb_a, tagged_v2a = critic.refine_sql_text_only(
        question, sql_v1, SCHEMA, REFLECT_MODEL
    )
    print(f"feedback: {fb_a}")
    try_run(conn, tagged_v2a, "v2a")

    utils.banner("v2b: reflect on the SQL AND the rows it returned")
    fb_b, tagged_v2b = critic.refine_sql_with_rows(
        question, sql_v1, rows_v1, cols_v1, SCHEMA, REFLECT_MODEL
    )
    print(f"feedback: {fb_b}")
    try_run(conn, tagged_v2b, "v2b")

    return 0


if __name__ == "__main__":
    sys.exit(main())
