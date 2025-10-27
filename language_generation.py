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
            logger.info("🔄 Falling back to smart response")
    else:
        logger.info("🔄 Using smart fallback response (no Gemini API available)")
    
    # Intelligent fallback - parse the prompt to understand what's needed
    return _generate_smart_fallback(prompt, context)


def _generate_smart_fallback(prompt: str, context: Optional[str] = None) -> str:
    """Generate an intelligent, colloquial fallback response when AI is not available."""
    import re
    import random
    
    # Extract user message from prompt
    user_msg_match = re.search(r'[Mm]ensagem.*?[":]\s*"([^"]+)"', prompt)
    if not user_msg_match:
        user_msg_match = re.search(r'[Pp]ergunta.*?[":]\s*"([^"]+)"', prompt)
    if not user_msg_match:
        user_msg_match = re.search(r'[Úú]ltima mensagem.*?[":]\s*"([^"]+)"', prompt)
    
    user_message = user_msg_match.group(1) if user_msg_match else ""
    
    # Try to extract facts from context
    user_facts = {}
    hobbies = []
    if context:
        # Extract name
        name_match = re.search(r'nome:\s*(\w+)', context, re.IGNORECASE)
        if name_match:
            user_facts['name'] = name_match.group(1)
        
        # Extract age
        age_match = re.search(r'idade:\s*(\d+)', context, re.IGNORECASE)
        if age_match:
            user_facts['age'] = age_match.group(1)
        
        # Extract profession
        prof_match = re.search(r'profissão:\s*([^;,\n]+)', context, re.IGNORECASE)
        if prof_match:
            user_facts['profession'] = prof_match.group(1).strip()
        
        # Extract hobbies
        hobby_matches = re.findall(r'gosta de:\s*([^;,\n]+)', context, re.IGNORECASE)
        if hobby_matches:
            hobbies = [h.strip() for h in hobby_matches]
    
    # Determine response type based on prompt situation
    lower_msg = user_message.lower()
    
    # First interaction - greeting (more colloquial)
    if "Primeira" in prompt and ("interação" in prompt or "vez" in prompt):
        greetings = [
            "Oi! Que massa te conhecer! 😊",
            "E aí! Tudo bem?",
            "Opa! Prazer! ✨",
            "Olá! Fico feliz que veio falar comigo!",
            "Hey! Como vai? 😄",
        ]
        return random.choice(greetings)
    
    # Question detection
    if user_message.endswith('?'):
        # Question about name
        if 'nome' in lower_msg:
            if 'name' in user_facts:
                return random.choice([
                    f"Seu nome é {user_facts['name']}! 😊",
                    f"Vc é o {user_facts['name']}, né?",
                    f"{user_facts['name']}! Lembro sim 😄"
                ])
            else:
                return random.choice([
                    "Hmm, não lembro do seu nome ainda... pode me dizer?",
                    "Opa, esqueci! Qual é seu nome mesmo?",
                    "Pô, não me lembro... me fala aí?"
                ])
        
        # Question about age
        if 'idade' in lower_msg:
            if 'age' in user_facts:
                return random.choice([
                    f"Vc tem {user_facts['age']} anos! 🎂",
                    f"{user_facts['age']} anos, né?",
                    f"Tem {user_facts['age']} anos! 😊"
                ])
            else:
                return random.choice([
                    "Não lembro da sua idade... quantos anos vc tem?",
                    "Opa, não sei! Me fala quantos anos vc tem?",
                    "Esqueci! Qual sua idade?"
                ])
        
        # Question about work/profession
        if 'trabalho' in lower_msg or 'profissão' in lower_msg:
            if 'profession' in user_facts:
                return random.choice([
                    f"Vc trabalha como {user_facts['profession']}, né? 💼",
                    f"Você é {user_facts['profession']}!",
                    f"{user_facts['profession']}! Massa! 😊"
                ])
            else:
                return random.choice([
                    "Não sei o que vc faz ainda... me conta?",
                    "Opa, não lembro! Qual seu trampo?",
                    "Esqueci! O que vc faz?"
                ])
        
        # Question about hobbies
        if 'hobby' in lower_msg or 'hobbies' in lower_msg or 'gosta' in lower_msg or 'gosto' in lower_msg:
            if hobbies:
                if len(hobbies) == 1:
                    return f"Vc gosta de {hobbies[0]}! 🎮"
                else:
                    return f"Vc gosta de {', '.join(hobbies[:-1])} e {hobbies[-1]}!"
            else:
                return random.choice([
                    "Não sei ainda do que vc gosta... me conta!",
                    "Opa, não sei! Do que vc gosta?",
                    "Esqueci! Me fala suas paradas!"
                ])
        
        # Generic question
        return random.choice([
            "Boa pergunta! Deixa eu pensar... 🤔",
            "Hmm... interessante! Não sei bem, mas posso aprender!",
            "Pô, não sei... o que vc acha?",
            "Boa! Não tenho certeza... 🤔"
        ])
    
    # User introducing themselves
    if any(word in lower_msg for word in ['sou', 'me chamo', 'meu nome']):
        responses = [
            "Prazer em te conhecer! 😊",
            "Massa te conhecer melhor!",
            "Que legal saber mais sobre vc! ✨",
            "Show! Prazer! 😄"
        ]
        return random.choice(responses)
    
    # Greeting from user
    if any(word in lower_msg for word in ['oi', 'olá', 'ola', 'hey', 'e aí', 'eai']):
        responses = [
            "Oi! Como vai? 😊",
            "E aí! Tudo certo?",
            "Hey! Que bom te ver!",
            "Opa! Tudo bem? 😄",
            "Olá! Como tá?",
        ]
        return random.choice(responses)
    
    # Gratitude
    if any(word in lower_msg for word in ['obrigado', 'obrigada', 'valeu', 'thanks', 'vlw']):
        responses = [
            "De nada! Tô aqui pra isso! 😊",
            "Nada! Fico feliz em ajudar!",
            "Sempre! ✨",
            "Tmj! 😄",
            "Magina! Por nada! 😊"
        ]
        return random.choice(responses)
    
    # Talking about music
    if any(word in lower_msg for word in ['música', 'musica', 'cantar', 'canção']):
        responses = [
            "Adoro música! Que tipo vc curte?",
            "Música é tudo! Qual seu estilo?",
            "Show! Me conta mais! 🎵",
            "Massa! Que música vc gosta?"
        ]
        return random.choice(responses)
    
    # Talking about games
    if any(word in lower_msg for word in ['jogo', 'game', 'jogar', 'brincar']):
        responses = [
            "Jogos são demais! Qual vc gosta?",
            "Legal! Que jogo vc joga?",
            "Adoro! Me fala mais! 🎮",
            "Show! Qual seu game favorito?"
        ]
        return random.choice(responses)
    
    # Default conversational responses (more colloquial)
    responses = [
        "Entendi! Me conta mais!",
        "Show! Como vc se sente sobre isso?",
        "Legal! O que mais vc quer compartilhar?",
        "Hmm, massa! Continua...",
        "Que interessante! Me fala mais!",
        "Saquei! E aí?",
        "Opa, legal! Me conta mais! 😊",
        "Dahora! Como assim?",
    ]
    
    return random.choice(responses)