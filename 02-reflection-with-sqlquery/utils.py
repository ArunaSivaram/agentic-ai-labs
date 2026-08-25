"""Plumbing for the SQL reflection lab.

Nothing agentic here - DB connection, LLM calls, tag extraction, pretty
printing. Keeping this out of reflect.py lets the workflow file read as a
workflow rather than as scaffolding.
"""

import html as _html
import os
import re
import sqlite3
import subprocess
import sys

from anthropic import Anthropic
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()
client = Anthropic()   # picks up ANTHROPIC_API_KEY from .env


# --- database --------------------------------------------------------------

def open_db(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python make_data.py` first."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def run_sql(conn: sqlite3.Connection, sql: str) -> tuple[list[tuple], list[str]]:
    """Execute a SELECT. Returns (rows, column_names).

    Guards against non-SELECT statements - the lab is read-only.
    """
    stripped = sql.strip().rstrip(";").lstrip()
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT / WITH statements are allowed in this lab.")

    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = [tuple(r) for r in cur.fetchall()]
    return rows, cols


# --- LLM calls -------------------------------------------------------------

def get_response(model: str, prompt: str, max_tokens: int = 2000,
                 system: str | None = None) -> str:
    """Text in, text out."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return "".join(b.text for b in msg.content if b.type == "text")


# --- tag extraction --------------------------------------------------------

SQL_TAG = re.compile(r"<execute_sql>([\s\S]*?)</execute_sql>")


def extract_sql(text: str) -> str:
    """Pull the SQL body out of <execute_sql> tags. Empty string if absent."""
    m = SQL_TAG.search(text)
    return m.group(1).strip() if m else ""


def ensure_execute_sql_tags(sql: str) -> str:
    """Wrap bare SQL back in tags so downstream code sees one shape."""
    sql = sql.strip()
    if not sql:
        return ""
    if sql.startswith("<execute_sql>"):
        return sql
    return f"<execute_sql>\n{sql}\n</execute_sql>"


# --- display ---------------------------------------------------------------

def banner(title: str) -> None:
    print(f"\n{'=' * 68}\n  {title}\n{'=' * 68}")


def print_sql(sql: str) -> None:
    print("SQL:")
    for line in sql.splitlines():
        print(f"  {line}")


TABLE_FMT = "psql"   # cleaner than 'github' in a plain terminal


def print_rows(rows: list[tuple], cols: list[str], max_rows: int = 20) -> None:
    if not rows:
        print("(no rows)")
        return
    shown = rows[:max_rows]
    print(tabulate(shown, headers=cols, tablefmt=TABLE_FMT,
                   floatfmt=",.2f", numalign="right", stralign="left"))
    if len(rows) > max_rows:
        print(f"... {len(rows) - max_rows} more rows")


def rows_as_text(rows: list[tuple], cols: list[str], max_rows: int = 20) -> str:
    """Same table the human sees, but as a string for the critic prompt."""
    if not rows:
        return "(no rows)"
    shown = rows[:max_rows]
    body = tabulate(shown, headers=cols, tablefmt=TABLE_FMT,
                    floatfmt=",.2f", numalign="right", stralign="left")
    if len(rows) > max_rows:
        body += f"\n... {len(rows) - max_rows} more rows"
    return body


# --- HTML rendering --------------------------------------------------------

_HTML_CSS = """
  body { font: 14px -apple-system, BlinkMacSystemFont, sans-serif;
         color: #222; background: #fafafa; margin: 40px; }
  h1 { font-size: 18px; margin: 24px 0 12px; color: #333; }
  h2 { font-size: 14px; margin: 20px 0 8px; color: #666; font-weight: 500; }
  table { border-collapse: collapse; margin-bottom: 24px;
          background: white; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  th, td { padding: 8px 14px; border-bottom: 1px solid #eee; text-align: left; }
  th { background: #f0f0f0; font-weight: 600; font-size: 12px;
       text-transform: uppercase; letter-spacing: .04em; color: #555; }
  tr:hover { background: #fafcff; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .empty { color: #999; font-style: italic; padding: 12px 0; }
"""


def _fmt_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return _html.escape(str(v))


def _is_num_col(rows: list[tuple], idx: int) -> bool:
    for r in rows:
        if r[idx] is None:
            continue
        return isinstance(r[idx], (int, float))
    return False


def render_html_table(rows: list[tuple], cols: list[str], title: str = "") -> str:
    """Return an HTML fragment (<h2> + <table>) for one result set."""
    parts = []
    if title:
        parts.append(f"<h2>{_html.escape(title)}</h2>")
    if not rows:
        parts.append('<div class="empty">(no rows)</div>')
        return "".join(parts)

    num_cols = {i for i in range(len(cols)) if _is_num_col(rows, i)}
    head = "".join(
        f'<th class="num">{_html.escape(c)}</th>' if i in num_cols
        else f"<th>{_html.escape(c)}</th>"
        for i, c in enumerate(cols)
    )
    body_rows = []
    for r in rows:
        cells = "".join(
            f'<td class="num">{_fmt_cell(v)}</td>' if i in num_cols
            else f"<td>{_fmt_cell(v)}</td>"
            for i, v in enumerate(r)
        )
        body_rows.append(f"<tr>{cells}</tr>")
    parts.append(
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )
    return "".join(parts)


def save_html(sections: list[tuple[str, list[tuple], list[str]]],
              path: str, page_title: str = "Query Results",
              open_browser: bool = True) -> str:
    """Write an HTML page containing multiple tables. Each `sections` entry is
    (title, rows, cols). Returns the absolute path written."""
    body = "\n".join(
        render_html_table(rows, cols, title) for title, rows, cols in sections
    )
    doc = (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{_html.escape(page_title)}</title>"
        f"<style>{_HTML_CSS}</style>"
        f"<h1>{_html.escape(page_title)}</h1>{body}"
    )
    with open(path, "w") as f:
        f.write(doc)
    abs_path = os.path.abspath(path)
    print(f"[saved] {abs_path}")
    if open_browser and sys.platform == "darwin":
        subprocess.run(["open", abs_path], check=False)
    return abs_path
