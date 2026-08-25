"""Render the project dashboard: index.html.

Self-contained HTML: pulls the current revenue rollups from inventory.db,
so the numbers on the page always match what `reflect.py` would see.

Run:
    python make_index.py
"""

import html as _html
import os
import subprocess
import sys

import utils

DB_PATH = "inventory.db"
OUT     = "index.html"

CSS = """
:root {
  --bg:#faf7f2; --ink:#2b1d13; --muted:#6b5847; --accent:#8b4513;
  --accent-2:#c47a3d; --card:#ffffff; --line:#e8dfd4; --code-bg:#2b1d13;
  --code-ink:#f5efe6; --good:#2e7d32; --warn:#c62828;
}
* { box-sizing: border-box; }
html, body { margin:0; padding:0; }
body {
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--ink); background: var(--bg);
}
main { max-width: 1080px; margin: 0 auto; padding: 48px 32px 96px; }
header { border-bottom: 1px solid var(--line); padding-bottom: 24px; margin-bottom: 40px; }
h1 { margin: 0 0 8px; font-size: 32px; letter-spacing: -0.01em; }
header p { margin: 0; color: var(--muted); font-size: 17px; }
h2 { font-size: 22px; margin: 48px 0 16px; letter-spacing: -0.01em; }
h3 { font-size: 15px; margin: 0 0 6px; text-transform: uppercase;
     letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }
p { margin: 0 0 12px; }
.lede { font-size: 17px; color: var(--ink); }
.lede strong { color: var(--accent); }

.diagram {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 32px; margin: 8px 0 32px; overflow-x: auto;
}
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
         align-items: stretch; }
.step {
  background: #fff; border: 1px solid var(--line); border-radius: 10px;
  padding: 16px; position: relative; text-align: center;
}
.step .num {
  display: inline-block; width: 24px; height: 24px; line-height: 24px;
  border-radius: 50%; background: var(--accent); color: #fff;
  font-size: 12px; font-weight: 700; margin-bottom: 8px;
}
.step h4 { margin: 0 0 4px; font-size: 15px; }
.step p { margin: 0; font-size: 13px; color: var(--muted); }
.step .model { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
               font-size: 11px; color: var(--accent-2); margin-top: 8px;
               display: block; }

.compare {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 8px 0 24px;
}
.frame {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 16px 20px; display: flex; flex-direction: column;
}
.frame .cap { margin-top: 8px; font-size: 13px; color: var(--muted); }
.frame .cap strong { color: var(--ink); }
.badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 999px; margin-bottom: 8px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.badge.v1 { background: #e8dfd4; color: var(--muted); }
.badge.v2 { background: var(--accent); color: #fff; }

.notes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.note {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 20px;
}
.note.warn { border-left: 4px solid var(--warn); }
.note.good { border-left: 4px solid var(--good); }
.note p { font-size: 14px; color: var(--muted); margin: 0; }
.note p + p { margin-top: 8px; }

pre {
  background: var(--code-bg); color: var(--code-ink); padding: 20px;
  border-radius: 10px; overflow-x: auto; font-size: 13px; line-height: 1.5;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.k { color: #ffb86c; }
.s { color: #a5d6a7; }
.c { color: #90a4ae; font-style: italic; }
.n { color: #f78ac2; }

table.data {
  width: 100%; border-collapse: collapse; font-size: 13px;
  background: #fff; border-radius: 8px; overflow: hidden;
}
table.data th, table.data td {
  padding: 7px 12px; border-bottom: 1px solid var(--line); text-align: left;
}
table.data th { background: #f2ead9; font-weight: 600; font-size: 11px;
  text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
table.data td.num, table.data th.num { text-align: right;
  font-variant-numeric: tabular-nums; }
table.data tr:last-child td { border-bottom: none; }

.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
        margin: 8px 0 24px; }
.kpi { background: #fff; border: 1px solid var(--line); border-radius: 10px;
       padding: 16px 18px; text-align: center; }
.kpi .num { font-size: 26px; font-weight: 700; color: var(--accent);
            font-variant-numeric: tabular-nums; }
.kpi .lbl { font-size: 11px; text-transform: uppercase;
            letter-spacing: 0.05em; color: var(--muted); margin-top: 4px; }

footer {
  margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 13px;
}
@media (max-width: 720px) {
  .steps, .compare, .notes, .kpis { grid-template-columns: 1fr; }
}
"""


# --- table rendering (reuses the utils HTML helper's cell logic) ----------

def render_table(rows: list[tuple], cols: list[str]) -> str:
    num_cols = {i for i in range(len(cols)) if utils._is_num_col(rows, i)}
    head = "".join(
        f'<th class="num">{_html.escape(c)}</th>' if i in num_cols
        else f"<th>{_html.escape(c)}</th>"
        for i, c in enumerate(cols)
    )
    body_rows = []
    for r in rows:
        cells = "".join(
            f'<td class="num">{utils._fmt_cell(v)}</td>' if i in num_cols
            else f"<td>{utils._fmt_cell(v)}</td>"
            for i, v in enumerate(r)
        )
        body_rows.append(f"<tr>{cells}</tr>")
    return (f"<table class='data'><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>")


# --- data pulls -----------------------------------------------------------

def pull(conn, sql):
    return utils.run_sql(conn, sql)


def build():
    conn = utils.open_db(DB_PATH)

    kpi_rows, _ = pull(conn, """
        SELECT COUNT(*) AS events,
               COUNT(DISTINCT product_id) AS skus,
               (SELECT COUNT(*) FROM events WHERE action='sale') AS sales,
               ROUND((SELECT SUM(-qty_delta*unit_price) FROM events
                      WHERE action='sale'), 0) AS revenue
        FROM events
    """)
    events, skus, sales, revenue = kpi_rows[0]

    by_product = pull(conn, """
        SELECT product_name,
               COUNT(DISTINCT product_id) AS variants,
               COUNT(*) AS units_sold,
               ROUND(SUM(-qty_delta * unit_price), 2) AS revenue
        FROM events WHERE action='sale'
        GROUP BY product_name
        ORDER BY revenue DESC
    """)

    by_sku_top10 = pull(conn, """
        SELECT product_name, color, brand, category,
               COUNT(*) AS units_sold,
               ROUND(SUM(-qty_delta * unit_price), 2) AS revenue
        FROM events WHERE action='sale'
        GROUP BY product_id
        ORDER BY revenue DESC LIMIT 10
    """)

    v1_result = pull(conn, """
        SELECT color
        FROM events
        WHERE action = 'sale'
        GROUP BY color
        ORDER BY SUM(qty_delta * unit_price) DESC
        LIMIT 1
    """)
    v2_result = pull(conn, """
        SELECT color, ROUND(SUM(-qty_delta * unit_price), 2) AS total_sales
        FROM events
        WHERE action = 'sale'
        GROUP BY color
        ORDER BY total_sales DESC
        LIMIT 1
    """)

    return {
        "kpi": (events, skus, sales, int(revenue)),
        "by_product": by_product,
        "by_sku_top10": by_sku_top10,
        "v1_result": v1_result,
        "v2_result": v2_result,
    }


# --- page -----------------------------------------------------------------

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SQL Reflection Lab &mdash; a self-critiquing query agent</title>
<style>{css}</style>
</head>
<body>
<main>

<header>
  <h1>SQL Reflection Lab</h1>
  <p>A self-critiquing query agent: cheap model drafts SQL from a plain-English
     question, SQLite runs it, a stronger model judges the <em>rows that came
     back</em> and rewrites the query.</p>
</header>

<p class="lede">
  Second lab in the agentic-AI series. <strong>01-reflection-lab</strong>
  reflected on rendered chart pixels; this one reflects on
  <strong>SQL result rows</strong>. Same draft&nbsp;&rarr;&nbsp;run&nbsp;&rarr;
  critique&nbsp;&rarr;&nbsp;redraft loop, different artifact under review.
</p>

<h2>The dataset at a glance</h2>
<div class="kpis">
  <div class="kpi"><div class="num">{events:,}</div><div class="lbl">events</div></div>
  <div class="kpi"><div class="num">{skus}</div><div class="lbl">SKUs</div></div>
  <div class="kpi"><div class="num">{sales:,}</div><div class="lbl">sales</div></div>
  <div class="kpi"><div class="num">&euro;{revenue:,}</div><div class="lbl">revenue</div></div>
</div>

<h2>The loop</h2>
<div class="diagram">
  <div class="steps">
    <div class="step">
      <span class="num">1</span>
      <h4>Draft SQL</h4>
      <p>Cheap model writes a first-pass query from the question and schema.</p>
      <span class="model">claude-haiku-4-5</span>
    </div>
    <div class="step">
      <span class="num">2</span>
      <h4>Run</h4>
      <p>SQLite executes it. The rows are the ground truth for the critic.</p>
      <span class="model">sqlite3</span>
    </div>
    <div class="step">
      <span class="num">3</span>
      <h4>Critique</h4>
      <p>Stronger model judges the answer against the question, then rewrites the query.</p>
      <span class="model">claude-sonnet-5</span>
    </div>
    <div class="step">
      <span class="num">4</span>
      <h4>Re-run</h4>
      <p>Refined SQL runs against the same DB. Compare v1 and v2 side-by-side.</p>
      <span class="model">sqlite3</span>
    </div>
  </div>
</div>

<h2>Before &amp; after &mdash; a real run</h2>
<p>Question: <em>&ldquo;Which color of product has the highest total sales?&rdquo;</em></p>
<div class="compare">
  <div class="frame">
    <span class="badge v1">v1 &mdash; naive</span>
    <pre><span class="k">SELECT</span> color
<span class="k">FROM</span> events
<span class="k">WHERE</span> action = <span class="s">'sale'</span>
<span class="k">GROUP BY</span> color
<span class="k">ORDER BY</span> <span class="n">SUM</span>(qty_delta * unit_price) <span class="k">DESC</span>
<span class="k">LIMIT</span> <span class="n">1</span>;</pre>
    {v1_table}
    <div class="cap"><strong>Wrong.</strong> Sales store negative qty_delta,
      so <code>SUM(qty_delta*unit_price)</code> is negative and DESC picks the
      <em>least-bad</em> seller.</div>
  </div>
  <div class="frame">
    <span class="badge v2">v2 &mdash; reflected</span>
    <pre><span class="k">SELECT</span> color, <span class="n">SUM</span>(-qty_delta * unit_price) <span class="k">AS</span> total_sales
<span class="k">FROM</span> events
<span class="k">WHERE</span> action = <span class="s">'sale'</span>
<span class="k">GROUP BY</span> color
<span class="k">ORDER BY</span> total_sales <span class="k">DESC</span>
<span class="k">LIMIT</span> <span class="n">1</span>;</pre>
    {v2_table}
    <div class="cap"><strong>Right.</strong> Negating <code>qty_delta</code>
      flips the sign; total is now a real revenue figure the critic can defend.</div>
  </div>
</div>

<h2>The event log, explained</h2>
<div class="notes">
  <div class="note">
    <h3>State is derived, not stored</h3>
    <p>Every row is one event: <code>insert</code>, <code>restock</code>,
       <code>sale</code>, or <code>price_update</code>. Current stock,
       current price, revenue &mdash; all are aggregations across time.</p>
    <p>Great for auditability. Awkward for the LLM: a query that looks
       simple (&ldquo;what's the price?&rdquo;) needs non-trivial SQL.</p>
  </div>
  <div class="note warn">
    <h3>The sign trap</h3>
    <p>Sales record <code>qty_delta = -1</code>. Restocks record positive
       numbers. A first-pass revenue query almost always sums the raw
       delta and gets a negative total.</p>
    <p>This is the class of bug reflection exists to catch.</p>
  </div>
  <div class="note">
    <h3>Two critic variants</h3>
    <p>The lab ships <code>refine_sql_text_only</code> (critic sees only
       the SQL) and <code>refine_sql_with_rows</code> (critic also sees
       the returned rows).</p>
    <p>The rows-aware critic is the one that reliably catches semantic
       bugs the text-only critic waves through.</p>
  </div>
  <div class="note good">
    <h3>SELECT-only guardrail</h3>
    <p><code>utils.run_sql</code> rejects anything that isn't <code>SELECT</code>
       or <code>WITH</code>. The LLM cannot mutate the database even if it
       tries.</p>
  </div>
</div>

<h2>Revenue rollup, right now</h2>
<p>Numbers pulled live from <code>inventory.db</code> at build time.</p>

<h3>By product name (color variants summed)</h3>
{by_product_table}

<h3>Top 10 SKUs (each color variant separately)</h3>
{by_sku_table}

<h2>The critic call, in one snippet</h2>
<pre><span class="c"># The move that makes it reflection rather than a second guess:</span>
<span class="c"># hand the model the ROWS THAT CAME BACK, not just the SQL that produced them.</span>
<span class="k">def</span> <span class="n">refine_sql_with_rows</span>(question, sql, rows, cols, schema, model):
    rendered = utils.rows_as_text(rows, cols, max_rows=<span class="n">20</span>)
    prompt = <span class="s">f&quot;&quot;&quot;Review the SQL AND its output against the user's question.
The rows below are the actual result of running the SQL. If the rows do
not answer the question (wrong sign, empty, wrong grain, missing filter,
etc.), rewrite the SQL.

User question:
{{question}}

SQL that was executed:
{{sql}}

Rows returned ({{len(rows)}} total; showing up to 20):
{{rendered}}
&quot;&quot;&quot;</span>
    <span class="k">return</span> _parse(utils.get_response(model, prompt, system=SYSTEM),
                  fallback_sql=sql)</pre>

<footer>
  <p>Series: agentic-AI reflection labs. Code is in the repo alongside this
     page. Numbers regenerate deterministically from
     <code>make_data.py</code> (seed = 11).</p>
</footer>

</main>
</body>
</html>
"""


def main() -> int:
    data = build()

    v1_table = render_table(*data["v1_result"])
    v2_table = render_table(*data["v2_result"])
    by_product_table = render_table(*data["by_product"])
    by_sku_table = render_table(*data["by_sku_top10"])

    events, skus, sales, revenue = data["kpi"]

    page = HTML.format(
        css=CSS,
        events=events, skus=skus, sales=sales, revenue=revenue,
        v1_table=v1_table, v2_table=v2_table,
        by_product_table=by_product_table,
        by_sku_table=by_sku_table,
    )

    with open(OUT, "w") as f:
        f.write(page)
    abs_path = os.path.abspath(OUT)
    print(f"[wrote] {abs_path}")

    if sys.platform == "darwin":
        subprocess.run(["open", abs_path], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
