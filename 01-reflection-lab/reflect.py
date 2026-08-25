"""The reflection loop: draft -> render -> critique the render -> redraft.

Run it:
    python reflect.py
    python reflect.py "Which coffee sells best in the morning vs afternoon?"
"""

import json
import sys

import utils

GEN_MODEL = "claude-haiku-4-5"      # cheap, fast: writes the first draft
REFLECT_MODEL = "claude-sonnet-5"   # stronger eyes: looks at the picture

SCHEMA = """
    - date        (datetime64, already parsed)
    - time        (string 'HH:MM' - never concatenate it with date)
    - cash_type   (string: 'card' or 'cash')
    - card        (string, anonymised id; empty for cash sales)
    - price       (float, EUR, the value of one cup)
    - coffee_name (string)
    - year        (int)  already computed - use directly
    - quarter     (int, 1-4) already computed - use directly
    - month       (int, 1-12) already computed - use directly
"""


# --- step 1: draft ---------------------------------------------------------

def generate_chart_code(instruction: str, model: str, out_path: str) -> str:
    prompt = f"""You are a data visualization expert.

Write Python that answers this request by drawing one matplotlib chart:

    {instruction}

The DataFrame `df` is already loaded, with these columns:
{SCHEMA}

Rules for the code:
1. Assume `df` exists. Do not read any files.
2. matplotlib only. No seaborn.
3. Include every import the code needs.
4. Give the chart a title, axis labels, and a legend if there is more than one series.
5. Save to '{out_path}' with dpi=300.
6. No plt.show(). End with plt.close().
7. `date` is datetime64 - never do string operations on it. Filter with the
   integer `year` / `quarter` columns.

Return ONLY the code, wrapped exactly like this, with no explanation:

<execute_python>
# code here
</execute_python>
"""
    return utils.get_response(model, prompt)


# --- steps 2 and 4: run the generated code ---------------------------------

def run_generated_code(tagged: str, df) -> bool:
    """Execute code the model wrote. See the note in the guide about exec()."""
    code = utils.extract_code(tagged)
    if not code:
        print("!! No <execute_python> block found - nothing to run.")
        return False
    try:
        exec(code, {"df": df})
        return True
    except Exception as e:
        print(f"!! Generated code failed: {type(e).__name__}: {e}")
        return False


# --- step 3: critique the rendered image -----------------------------------

def reflect_and_regenerate(chart_path: str, instruction: str, model: str,
                           out_path: str, code_v1: str) -> tuple[str, str]:
    """Show the model the chart it drew and ask it to do better.

    Returns (feedback, code_with_tags).
    """
    media_type, b64 = utils.encode_image_b64(chart_path)

    prompt = f"""Critique the attached chart against the request below, then
return improved matplotlib code.

Request: {instruction}

The code that produced it:
{code_v1}

Judge the IMAGE, not the code: is the message readable at a glance, are the
labels legible and non-overlapping, is the chart type right for the comparison,
are the numbers findable, is anything misleading or missing?

OUTPUT FORMAT - exactly two parts, nothing else:

1) A single line of JSON with one field:
{{"feedback": "what is wrong and what you changed, in 2-4 sentences"}}

2) Then a newline, then the improved code:
<execute_python>
# code here
</execute_python>

Constraints on the code:
- pandas and matplotlib only. Include all imports; assume nothing carries over.
- `df` already exists. Do not read files.
- Save to '{out_path}' with dpi=300. No plt.show(). End with plt.close().
- `date` is datetime64. Filter with the integer `year` / `quarter` columns.

Columns available:
{SCHEMA}
No markdown fences. No prose outside the two parts.
"""

    content = utils.image_anthropic_call(model, prompt, media_type, b64)

    # The model was told to lead with a JSON line. Trust it, but do not rely on it.
    feedback = ""
    for candidate in (content.strip().splitlines() or [""])[:1]:
        try:
            feedback = json.loads(candidate).get("feedback", "")
        except Exception:
            pass
    if not feedback:
        import re
        m = re.search(r"\{[^{}]*\"feedback\"[\s\S]*?\}", content)
        if m:
            try:
                feedback = json.loads(m.group(0)).get("feedback", "")
            except Exception:
                feedback = m.group(0)
    if not feedback:
        feedback = "(could not parse feedback - see raw output)"

    return feedback, utils.ensure_execute_python_tags(utils.extract_code(content))


# --- driver ---------------------------------------------------------------

DEFAULT_INSTRUCTION = "Create a plot comparing Q1 coffee sales in 2024 and 2025."


def main() -> int:
    instruction = " ".join(sys.argv[1:]).strip() or DEFAULT_INSTRUCTION
    df = utils.load_and_prepare_data("coffee_sales.csv")

    utils.banner("v1: draft")
    print(f"instruction: {instruction}")
    tagged_v1 = generate_chart_code(instruction, GEN_MODEL, "coffee_v1.png")
    if not run_generated_code(tagged_v1, df):
        return 1
    utils.show_image("coffee_v1.png")

    utils.banner("v2: reflect on the rendered chart, then redraw")
    feedback, tagged_v2 = reflect_and_regenerate(
        "coffee_v1.png", instruction, REFLECT_MODEL,
        "coffee_v2.png", utils.extract_code(tagged_v1),
    )
    print(f"feedback: {feedback}")
    if not run_generated_code(tagged_v2, df):
        return 1
    utils.show_image("coffee_v2.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
