"""
AI-driven memory importance detection and analysis.

This module uses AI (Gemini) to analyze conversations and images to determine
what information is important to remember, extract structured facts, and
provide detailed descriptions for image memories.
"""

import logging
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from PIL import Image
    import io
except ImportError:
    genai = None
    logger.warning("google-generativeai or PIL not available for AI memory analysis")


def _get_ai_model():
    """Get configured AI model for memory analysis."""
    global genai
    if genai is None:
        return None
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")
    if not api_key:
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize AI model: {e}")
        return None


def analyze_conversation_importance(text: str, existing_facts: List[str]) -> Tuple[float, List[str]]:
    """
    Analyze a conversation message to determine importance and extract facts.
    
    Args:
        text: The conversation text to analyze
        existing_facts: List of already known facts about the user
        
    Returns:
        Tuple of (importance_score, extracted_facts)
        - importance_score: 0.0 to 1.0, how important this message is
        - extracted_facts: List of structured facts extracted from the text
    """
    model = _get_ai_model()
    
    if model is None:
        # Fallback: simple heuristic-based importance
        importance = 0.5
        lower = text.lower()
        
        # Increase importance for personal information
        if any(word in lower for word in ["nome", "chamo", "sou", "tenho", "anos", "trabalho", "moro"]):
            importance = 0.9
        elif any(word in lower for word in ["gosto", "adoro", "amo", "odeio", "prefiro"]):
            importance = 0.8
        elif "?" in text:
            importance = 0.6
        
        return importance, []
    
    try:
        # Build prompt for AI analysis
        existing_context = "\n".join(existing_facts[:10]) if existing_facts else "Nenhum fato conhecido ainda"
        
        prompt = f"""Você é um assistente de análise de memória para um pet virtual.

MENSAGEM DO USUÁRIO: "{text}"

FATOS JÁ CONHECIDOS SOBRE O USUÁRIO:
{existing_context}

TAREFAS:
1. Determine a IMPORTÂNCIA desta mensagem (0.0 a 1.0):
   - 0.9-1.0: Informação pessoal crítica (nome, idade, família, saúde)
   - 0.7-0.9: Informação importante (trabalho, hobbies, preferências)
   - 0.5-0.7: Informação moderada (opiniões, experiências)
   - 0.3-0.5: Conversa casual
   - 0.0-0.3: Mensagens triviais
   
2. Extraia FATOS ESTRUTURADOS no formato "categoria: valor":
   - Apenas fatos novos que não estão nos fatos já conhecidos
   - Exemplos: "nome: João", "idade: 25 anos", "profissão: engenheiro", "tem pet: gato chamado Miau"
   
RESPONDA EM JSON:
{{
  "importance": 0.0-1.0,
  "facts": ["fato1", "fato2", ...]
}}

Seja preciso e objetivo. Se não há fatos novos, retorne lista vazia."""

        response = model.generate_content(prompt)
        
        if hasattr(response, 'text'):
            import json
            import re
            
            # Extract JSON from response
            text_response = response.text.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', text_response)
            if json_match:
                data = json.loads(json_match.group())
                importance = float(data.get("importance", 0.5))
                facts = data.get("facts", [])
                
                logger.info(f"🤖 AI analysis: importance={importance:.2f}, facts={len(facts)}")
                return importance, facts
            
    except Exception as e:
        logger.error(f"AI importance analysis failed: {e}")
    
    # Fallback
    return 0.5, []


def analyze_image_memory(
    image_bytes: bytes,
    user_message: str,
    existing_facts: List[str],
    conversation_context: List[str]
) -> Dict[str, any]:
    """
    Analyze an image to extract detailed information for memory storage.
    
    Args:
        image_bytes: Raw image bytes
        user_message: Message sent with the image
        existing_facts: Known facts about the user
        conversation_context: Recent conversation history
        
    Returns:
        Dictionary with:
        - description: Detailed AI description of the image
        - entities: Detected entities (people, animals, objects)
        - importance: Importance score
        - labels: Simple labels for the image
    """
    model = _get_ai_model()
    
    if model is None:
        return {
            "description": "Imagem recebida",
            "entities": {},
            "importance": 0.5,
            "labels": []
        }
    
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Build context
        facts_context = "\n".join(existing_facts[:10]) if existing_facts else "Nenhum"
        conv_context = " | ".join(conversation_context[-5:]) if conversation_context else "Primeira imagem"
        
        prompt = f"""Você é um assistente de análise de imagens para um pet virtual com memória.

MENSAGEM DO USUÁRIO COM A IMAGEM: "{user_message}"

O QUE VOCÊ JÁ SABE SOBRE O USUÁRIO:
{facts_context}

CONVERSA RECENTE:
{conv_context}

ANALISE A IMAGEM E FORNEÇA:

1. DESCRIÇÃO DETALHADA (2-3 frases sobre o que vê)

2. ENTIDADES DETECTADAS com características:
   Para PESSOAS:
   - Quem é (inferir se é o usuário com base no contexto)
   - Aparência (cor de cabelo, estilo de roupa, idade aparente)
   - Características marcantes
   
   Para ANIMAIS:
   - Tipo de animal
   - Características (cor, tamanho, raça se identificável)
   - Dono (inferir com base no contexto)
   - Nome (se mencionado na conversa)
   
   Para OBJETOS/LUGARES importantes:
   - O que é
   - Relevância para o usuário

3. IMPORTÂNCIA (0.0-1.0):
   - 0.9-1.0: Foto do usuário, família, pet
   - 0.7-0.9: Eventos importantes, conquistas
   - 0.5-0.7: Lugares visitados, atividades
   - 0.3-0.5: Objetos casuais
   
4. LABELS SIMPLES: 3-5 palavras-chave

RESPONDA EM JSON:
{{
  "description": "descrição detalhada da imagem",
  "entities": {{
    "entity_type": "entity_description",
    "person": "usuário, cabelo castanho, camiseta azul",
    "animal": "gato laranja, pelo curto, raça desconhecida, dono: usuário"
  }},
  "importance": 0.0-1.0,
  "labels": ["label1", "label2", "label3"]
}}"""

        response = model.generate_content([prompt, image])
        
        if hasattr(response, 'text'):
            import json
            import re
            
            text_response = response.text.strip()
            json_match = re.search(r'\{[\s\S]*\}', text_response)
            
            if json_match:
                data = json.loads(json_match.group())
                logger.info(f"🖼️ AI image analysis: {data.get('description', '')[:50]}...")
                return {
                    "description": data.get("description", ""),
                    "entities": data.get("entities", {}),
                    "importance": float(data.get("importance", 0.5)),
                    "labels": data.get("labels", [])
                }
    
    except Exception as e:
        logger.error(f"AI image analysis failed: {e}")
    
    # Fallback
    return {
        "description": "Imagem recebida do usuário",
        "entities": {},
        "importance": 0.5,
        "labels": []
    }
