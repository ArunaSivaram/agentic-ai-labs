# Reflection Lab

**Live dashboard → [arunasivaram.github.io/agentic-ai-01-reflection-lab](https://arunasivaram.github.io/agentic-ai-01-reflection-lab/)**

A self-critiquing chart agent: a cheap model drafts matplotlib code from an
English request, `exec()` renders it to disk, a stronger model looks at the
*rendered pixels* (not the code) and rewrites it. Two-model split keeps
drafting cheap and reviewing capable. Custom `<execute_python>` tags make
code extraction unambiguous. Pre-computing `year`/`quarter`/`month` in Python
removes the date-arithmetic failure mode before prompting. First in an
agentic AI series.

## Run it

```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-..." > .env
python make_data.py                # generates coffee_sales.csv (seeded, deterministic)
python reflect.py                  # runs the loop with the default Q1-comparison prompt
python reflect.py "Which coffee sells best in the morning vs afternoon?"
```

Produces `coffee_v1.png` (the draft) and `coffee_v2.png` (the reflected redraw)
in the working directory.

## The dashboard

Live at
**[arunasivaram.github.io/agentic-ai-01-reflection-lab](https://arunasivaram.github.io/agentic-ai-01-reflection-lab/)** —
architecture diagram, before/after chart comparison, and design notes.
Source lives in [`index.html`](./index.html) (self-contained, PNGs
base64-embedded) if you want to open it locally.

## Files

- `make_data.py` — seeded synthetic coffee-sales generator (Jan 2024 – Mar 2025)
- `utils.py` — data loader, API call helpers (text + image), tag extractor
- `reflect.py` — the loop (generate → run → reflect → run) + CLI driver
- `index.html` — self-contained dashboard
