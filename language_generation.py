"""
Language generation utilities for the organic virtual pet.

This module wraps text generation functionality so the virtual pet can
respond in a more natural and varied way. It attempts to use the Google
Generative AI client when available; if the client is not configured or
installed, it falls back to a simple template-based approach.

The function ``generate_text`` takes a prompt and optional context and
returns a generated string. For production use, you should provide your
Vertex AI or Gemini API credentials by setting the appropriate
environment variables (e.g., ``GOOGLE_API_KEY``) and installing the
``google-generativeai`` package. When running locally without
credentials, the fallback produces a polite echo or a default response.

Example usage::

    from .language_generation import generate_text
    response = generate_text("Tell me a joke about cats")

Note: This is a lightweight wrapper and does not expose all features of
the underlying generative models. You can customize or extend it to
support more advanced parameters (e.g., temperature, top_k).
"""

from __future__ import annotations

import os
from typing import Optional

try:
    # The google-generativeai package provides access to the Gemini API.
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # type: ignore


def _get_generative_model() -> Optional[object]:
    """Initialize and return a generative model client if available.

    Returns ``None`` when the ``google-generativeai`` package is not
    installed or no API key is configured. The API key should be set via
    the ``GOOGLE_API_KEY`` or ``GENAI_API_KEY`` environment variable.
    """
    global genai
    if genai is None:
        return None
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # Use the default generative model (e.g., gemini-pro) for text.
        model = genai.GenerativeModel("gemini-pro")
        return model
    except Exception:
        return None


def generate_text(prompt: str, context: Optional[str] = None) -> str:
    """Generate a natural language response based on the given prompt.

    If a generative model is configured, this function sends the prompt
    (prefixed by any context) to the model and returns the generated
    content. Otherwise, it produces a simple deterministic response by
    echoing the prompt or using a fallback message.

    Args:
        prompt: The main prompt or instruction for the model.
        context: Optional additional context to prime the model. When
            provided, the context is prepended to the prompt separated
            by a newline.

    Returns:
        A generated string suitable as a conversational reply.
    """
    model = _get_generative_model()
    full_prompt = prompt if context is None else f"{context}\n{prompt}"
    if model is not None:
        try:
            # The Gemini API expects a list of strings for the prompt.
            result = model.generate_content([full_prompt])
            # Extract the text from the first candidate
            text = result.text if hasattr(result, "text") else str(result)
            return text.strip()
        except Exception:
            pass
    # Fallback: simple heuristic-based response
    # If the prompt ends with a question mark, answer affirmatively
    stripped = prompt.strip()
    if stripped.endswith("?"):
        return "Claro! Isso soa divertido."
    # Generic echo with a friendly twist
    return f"Você mencionou: '{prompt}'. Conte-me mais sobre isso!"