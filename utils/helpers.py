"""Shared utilities for the resume optimization pipeline."""
import os
import re
from typing import Optional


def get_api_key() -> str:
    """Get Gemini API key from environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in the environment.")
    return api_key


def track_tokens(response, tracker, model_type: str = "text"):
    """Extract and track tokens from a Gemini API response."""
    in_tokens = 0
    out_tokens = 0
    if response.usage_metadata:
        in_tokens = response.usage_metadata.prompt_token_count
        out_tokens = response.usage_metadata.candidates_token_count
    tracker.track(model_type, in_tokens, out_tokens)


def extract_bullets(latex_content: str) -> list[str]:
    """
    Parses out the exact content strings inside all \\validatedbullet{...} macros.
    Handles nested curly braces up to arbitrary depths.
    """
    bullets = []
    pattern = r'\\\\validatedbullet\\{'
    for match in re.finditer(pattern, latex_content):
        start = match.end()
        brace_count = 1
        i = start
        while i < len(latex_content) and brace_count > 0:
            if latex_content[i] == '{':
                brace_count += 1
            elif latex_content[i] == '}':
                brace_count -= 1
            i += 1
        if brace_count == 0:
            bullet_text = latex_content[start:i-1]
            if bullet_text not in bullets:
                bullets.append(bullet_text)
    return bullets
