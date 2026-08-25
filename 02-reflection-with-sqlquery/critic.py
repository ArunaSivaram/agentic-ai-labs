"""The critic. Two flavors, on purpose.

`refine_sql_text_only` sees the SQL and the schema. It behaves like a code
reviewer with no data - it catches obvious structural mistakes but often
misses semantic bugs (a valid-looking query returning wrong-signed totals,
empty result sets, off-by-one groupings).

`refine_sql_with_rows` sees the same SQL PLUS the rows that came back.
That is where reflection earns its keep in this lab: a query that looks
right and *is* SELECT-valid can still be semantically wrong, and the
answer itself is the cheapest evidence of that.

Both functions return (feedback, sql_tagged) so the driver can treat them
interchangeably.
"""

import json
import re

import utils


SYSTEM = (
    "You are a meticulous SQL reviewer for SQLite. "
    "Follow the requested output format exactly, with no extra prose."
)


# --- shared prompt scaffolding --------------------------------------------

OUTPUT_CONTRACT = """OUTPUT FORMAT - exactly two parts, nothing else:

1) A single line of JSON with one field:
{"feedback": "what was wrong (or 'ok' if unchanged) and what you changed, 2-4 sentences"}

2) Then a newline, then the refined SQL:
<execute_sql>
-- SELECT ... (SQLite)
</execute_sql>

Constraints on the SQL:
- SELECT or WITH only. No writes.
- Use the documented schema below verbatim.
- Prefer set-based SQL over anything that would need post-processing in Python.
- If the original is already correct, return it unchanged inside the tags.
"""


def _parse(content: str, fallback_sql: str) -> tuple[str, str]:
    """Extract (feedback, tagged_sql) from the model's reply.

    Same trust-but-verify shape as 01-reflection-lab: try the first line as
    JSON, fall back to a regex sweep, fall back to the raw content.
    """
    feedback = ""
    first_line = (content.strip().splitlines() or [""])[0]
    try:
        feedback = json.loads(first_line).get("feedback", "")
    except Exception:
        pass
    if not feedback:
        m = re.search(r"\{[^{}]*\"feedback\"[\s\S]*?\}", content)
        if m:
            try:
                feedback = json.loads(m.group(0)).get("feedback", "")
            except Exception:
                feedback = m.group(0)
    if not feedback:
        feedback = "(could not parse feedback - see raw output)"

    sql_body = utils.extract_sql(content) or fallback_sql
    return feedback, utils.ensure_execute_sql_tags(sql_body)


# --- variant 1: text-only --------------------------------------------------

def refine_sql_text_only(question: str, sql: str, schema: str,
                         model: str) -> tuple[str, str]:
    """Critique the SQL against the question and schema alone.

    The critic does NOT see any rows. This variant exists to demonstrate
    what reflection misses when it has no ground truth to check against.
    """
    prompt = f"""Review the SQL below against the user's question and the schema.
Judge only the query text - you do not have the execution results.

User question:
{question}

SQL to review:
{sql}

Schema:
{schema}

{OUTPUT_CONTRACT}
"""
    content = utils.get_response(model, prompt, system=SYSTEM)
    return _parse(content, fallback_sql=sql)


# --- variant 2: with execution rows ---------------------------------------

def refine_sql_with_rows(question: str, sql: str, rows: list[tuple],
                         cols: list[str], schema: str,
                         model: str) -> tuple[str, str]:
    """Critique the SQL AND the rows it returned.

    This is the version that catches sign-inversion, empty results, wrong
    grouping - anything that looks fine on paper but is wrong in the data.
    """
    rendered = utils.rows_as_text(rows, cols, max_rows=20)

    prompt = f"""Review the SQL AND its output against the user's question.
The rows below are the actual result of running the SQL. If the rows do
not answer the question (wrong sign, empty, wrong grain, missing filter,
etc.), rewrite the SQL.

User question:
{question}

SQL that was executed:
{sql}

Rows returned ({len(rows)} total; showing up to 20):
{rendered}

Schema:
{schema}

{OUTPUT_CONTRACT}
"""
    content = utils.get_response(model, prompt, system=SYSTEM)
    return _parse(content, fallback_sql=sql)
