"""Plumbing for the reflection lab.

Nothing agentic lives here - just the boring parts: loading data,
talking to the API, encoding images, pulling code out of tags.
Keeping them separate makes the workflow file readable as a workflow.
"""

import base64
import mimetypes
import os
import re
import subprocess
import sys

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()                 # reads .env into the environment
client = Anthropic()          # picks up ANTHROPIC_API_KEY automatically


# --- data ------------------------------------------------------------------

def load_and_prepare_data(path: str) -> pd.DataFrame:
    """Load the CSV and add the derived columns the model is allowed to assume.

    Deriving year/quarter/month HERE rather than in generated code is a
    deliberate choice: it shrinks what the model has to get right.
    """
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    return df


# --- model calls -----------------------------------------------------------

def get_response(model: str, prompt: str, max_tokens: int = 2000) -> str:
    """Plain text-in, text-out call."""
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


# --- text wrangling --------------------------------------------------------

CODE_TAG = re.compile(r"<execute_python>([\s\S]*?)</execute_python>")


def extract_code(text: str) -> str:
    """Pull the body out of <execute_python> tags. Empty string if absent."""
    m = CODE_TAG.search(text)
    return m.group(1).strip() if m else ""


def ensure_execute_python_tags(code: str) -> str:
    """Put the tags back on a bare code body, so everything downstream
    can assume the same shape."""
    code = code.strip()
    if not code:
        return ""
    if code.startswith("<execute_python>"):
        return code
    return f"<execute_python>\n{code}\n</execute_python>"


# --- display ---------------------------------------------------------------

def banner(title: str) -> None:
    print(f"\n{'=' * 68}\n  {title}\n{'=' * 68}")


def show_image(path: str) -> None:
    """Open the chart in the system viewer (macOS: Preview)."""
    print(f"[saved] {path}")
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)


# --- images ---------------------------------------------------------------

def encode_image_b64(path: str) -> tuple[str, str]:
    """Read an image off disk as (media_type, base64 string)."""
    media_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return media_type, base64.standard_b64encode(f.read()).decode("utf-8")


def image_anthropic_call(model: str, prompt: str, media_type: str, b64: str,
                         max_tokens: int = 3000) -> str:
    """Send an image plus a prompt. This is the call that makes reflection real:
    the model looks at the rendered chart, not at the code that drew it."""
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=("You are a meticulous data-visualization reviewer. "
                "Follow the requested output format exactly, with no extra prose."),
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return "".join(b.text for b in msg.content if b.type == "text")
