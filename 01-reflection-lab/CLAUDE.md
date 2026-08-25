# Reflection Lab — context for Claude

A four-step reflection loop: cheap model drafts matplotlib code from an
English request → `exec()` renders the PNG → capable model looks at the
rendered pixels (not the code) and rewrites → same executor produces v2.
First in a portfolio `agentic-ai-XX-<name>` series.

## Files

- `make_data.py` — seeded synthetic coffee-sales CSV (Jan 2024–Mar 2025, SEED=7). CSV is gitignored; regenerable via `python make_data.py`.
- `utils.py` — data loader (`load_and_prepare_data`), text call (`get_response`), image call (`image_anthropic_call`), image encoder (`encode_image_b64`), `<execute_python>` extractor + wrapper, display helpers.
- `reflect.py` — the loop: `generate_chart_code` (draft) → `run_generated_code` (exec) → `reflect_and_regenerate` (critique+redraw) → `run_generated_code`. CLI driver in `main()`.
- `index.html` — self-contained portfolio dashboard (PNGs base64-embedded). Published via GitHub Pages.
- `README.md` — public-facing pitch + run instructions. Not the same as this file.

## Models

- Draft: `GEN_MODEL = "claude-haiku-4-5"`
- Reflect: `REFLECT_MODEL = "claude-sonnet-5"` — **flag**: this may not be a valid model ID. API accepted it in testing but the latest real Sonnet is `claude-sonnet-4-6`. Pin if issues arise.

## Design decisions worth preserving

**Custom `<execute_python>` tags, not markdown fences.** `​`​`​`python` fences are ambiguous — models emit variants (`​`​`py`, `​`​`Python`), nest fences inside docstrings, or wrap prose accidentally. `<execute_python>` is a token the model has no other reason to emit; one regex (`[\s\S]*?` for cross-line non-greedy) catches it every time.

**Pre-compute `year`, `quarter`, `month` in `load_and_prepare_data`.** Removes the "don't concatenate datetime with time string" failure mode *structurally* instead of via a longer prompt. Structure beats instruction. The model gets a schema that already answers the hard question.

**Image-grounded critique.** `reflect_and_regenerate` sends the rendered PNG to the reviewer, not the code that drew it. Critiquing code = model tells you what it intended. Critiquing the image = model confronts what came out. This is the single line that makes it *reflection* rather than a second guess.

**Image first, text second in `image_anthropic_call`.** Content order matters — models attend better to instructions that come after the artifact they're about.

**Two-model split.** Haiku drafts (cheap, fast), Sonnet reviews (capable, expensive). Reflection is the costly step; drafting doesn't have to be.

## Known gaps (deliberately unaddressed for now)

**`exec()` is a write tool.** `run_generated_code` runs arbitrary model-generated Python with full filesystem, network, and API-key access. Fine on synthetic data on a laptop. **Not safe for deployment.** Biggest blocker to shipping.

**Failure returns `False`, but nothing consumes it.** `run_generated_code` catches exceptions and returns `False`. The driver in `main()` short-circuits with exit code 1 instead of doing anything useful (like feeding the traceback back to the model). Most useful next iteration inside the loop.

## Next planned work (in priority order)

1. **Consume the `False`**: on generated-code failure, send the traceback back to the model and ask for a fix. Same reflection pattern, applied to errors instead of aesthetics. Cheapest and highest-value change.
2. **Sandbox `exec()`**: subprocess in a temp dir with timeout + resource limits, or (better) Modal Sandboxes / a container. Non-negotiable before any deployment.
3. **Streamlit wrapper**: text input → run loop → show v1/v2 side-by-side with the critique text. Deploy to Hugging Face Spaces or Streamlit Community Cloud for a live portfolio demo.
4. **Not Vercel**: serverless duration limits (10s hobby / 60s pro), ephemeral filesystem, and the `exec()` problem all fight the platform. Streamlit + HF Spaces or Modal are the right fits.

## Git identity (critical)

Global git config on this machine is set to work identity (`aruna@comchord.com`). Personal projects MUST override locally, otherwise commits get attributed to the work GitHub account. This repo already has:

```
git config user.email '4616780+ArunaSivaram@users.noreply.github.com'
```

The noreply address (not `aruna.sivaram@gmail.com`) is required because GitHub's *"block command-line pushes that expose my email"* is enabled on the personal account. Direct pushes with the Gmail address will be rejected with GH007.

If commits were made with the wrong identity, rewrite with:
```
git rebase --root --exec 'git commit --amend --no-edit --reset-author'
git push --force-with-lease
```
Safe on this repo (solo, no collaborators, no forks).

## Repo + deployment

- **GitHub**: https://github.com/ArunaSivaram/agentic-ai-01-reflection-lab (public)
- **Pages**: https://arunasivaram.github.io/agentic-ai-01-reflection-lab/ — main branch, root path
- **Branch**: `main` tracks `origin/main`
- **Not deployed as a service** yet — dashboard is static only

## Conventions

- No emojis in code or docs unless explicitly asked.
- Terse commit messages: subject + short "why" body. `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- `coffee_v1.png` / `coffee_v2.png` are gitignored (non-deterministic model output; regenerable via `python reflect.py`).
- `coffee_sales.csv` is gitignored (deterministic; regenerable via `python make_data.py`).
