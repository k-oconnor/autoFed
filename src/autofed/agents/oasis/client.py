"""OpenAI chat completion returning JSON text."""

from __future__ import annotations

import json
import os
from typing import Any


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def complete_json_object(
    *,
    system_prompt: str,
    user_content: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    """Call OpenAI chat completions with JSON object mode; return parsed dict."""
    _load_dotenv_if_available()
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            'OpenAI integration requires the "openai" package. '
            'Install with: pip install "autofed[openai]" or pip install openai'
        ) from e

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to a gitignored .env file (see .env.example) "
            "or export it in your shell."
        )

    base_url = os.environ.get("OPENAI_BASE_URL")
    client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    choice = resp.choices[0].message.content
    if not choice:
        return {}
    return json.loads(choice)
