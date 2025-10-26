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
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # The google-generativeai package provides access to the Gemini API.
    import google.generativeai as genai  # type: ignore
    logger.info("✅ google-generativeai package imported successfully")
except Exception as e:
    genai = None  # type: ignore
    logger.warning(f"❌ Failed to import google-generativeai package: {e}")
    logger.warning("🔄 Will use fallback responses instead of Gemini API")


def _get_generative_model() -> Optional[object]:
    """Initialize and return a generative model client if available.

    Returns ``None`` when the ``google-generativeai`` package is not
    installed or no API key is configured. The API key should be set via
    the ``GOOGLE_API_KEY`` or ``GENAI_API_KEY`` environment variable.
    """
    global genai
    if genai is None:
        logger.warning("❌ google-generativeai package not available")
        return None
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")
    if not api_key:
        logger.warning("❌ No API key found. Set GOOGLE_API_KEY or GENAI_API_KEY environment variable")
        logger.info("💡 To get an API key, visit: https://makersuite.google.com/app/apikey")
        return None
    
    try:
        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash-lite for higher rate limits
        # This model supports multimodal (text + image) capabilities
        model_name = "gemini-2.0-flash-lite"
        model = genai.GenerativeModel(model_name)
        logger.info(f"✅ Gemini API configured successfully with model: {model_name}")
        return model
        
    except Exception as e:
        logger.error(f"❌ Failed to configure Gemini API with model gemini-2.0-flash-lite: {e}")
        logger.info("💡 Make sure you have a valid API key and the model is available in your region")
        return None


def generate_text_with_image(prompt: str, image_bytes: bytes, context: Optional[str] = None) -> str:
    """Generate a response about an image using Gemini's multimodal capabilities.
    
    Args:
        prompt: The main prompt or instruction for the model.
        image_bytes: Raw bytes of the image to analyze.
        context: Optional additional context to prime the model.
        
    Returns:
        A generated string describing and responding to the image.
    """
    logger.info(f"🖼️ Generating multimodal response for image ({len(image_bytes)} bytes)")
    
    model = _get_generative_model()
    if model is not None:
        try:
            # Import PIL for image processing
            from PIL import Image
            import io
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create the full prompt with context
            full_prompt = prompt if context is None else f"{context}\n{prompt}"
            
            logger.info("🚀 Calling Gemini API with image...")
            
            # Use Gemini's multimodal capabilities
            response = model.generate_content([full_prompt, image])
            
            if hasattr(response, 'text') and response.text:
                result = response.text.strip()
                logger.info(f"✅ Gemini multimodal response: '{result[:50]}{'...' if len(result) > 50 else ''}'")
                return result
            else:
                logger.warning("⚠️ Gemini returned empty response for image")
                
        except Exception as e:
            logger.error(f"❌ Gemini multimodal call failed: {e}")
            logger.info("🔄 Falling back to text-only response")
    
    # Fallback to text-only response
    logger.info("🔄 Using text-only fallback for image response")
    fallback_response = "Vejo que você enviou uma imagem! Infelizmente não consigo analisá-la no momento, mas obrigado por compartilhar!"
    return fallback_response


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
    logger.info(f"🤖 Generating text for prompt: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'")
    
    model = _get_generative_model()
    full_prompt = prompt if context is None else f"{context}\n{prompt}"
    
    if model is not None:
        try:
            logger.info("🚀 Calling Gemini API (gemini-2.0-flash-lite)...")
            # The Gemini API expects a list of strings for the prompt.
            result = model.generate_content([full_prompt])
            # Extract the text from the first candidate
            text = result.text if hasattr(result, "text") else str(result)
            response = text.strip()
            logger.info(f"✅ Gemini API response received: '{response[:50]}{'...' if len(response) > 50 else ''}'")
            return response
        except Exception as e:
            logger.error(f"❌ Gemini API call failed: {e}")
            logger.info("🔄 Falling back to default response")
    else:
        logger.info("🔄 Using fallback response (no Gemini API available)")
    
    # Fallback: simple heuristic-based response
    # If the prompt ends with a question mark, answer affirmatively
    stripped = prompt.strip()
    if stripped.endswith("?"):
        fallback_response = "Claro! Isso soa divertido."
        logger.info(f"💬 Fallback response (question): '{fallback_response}'")
        return fallback_response
    
    # Generic echo with a friendly twist
    fallback_response = f"Você mencionou: '{prompt}'. Conte-me mais sobre isso!"
    logger.info(f"💬 Fallback response (echo): '{fallback_response[:50]}{'...' if len(fallback_response) > 50 else ''}'")
    return fallback_response