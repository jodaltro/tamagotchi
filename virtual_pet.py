"""
High-level interface to the organic virtual pet.

The `VirtualPet` class wraps a `PetState` instance and provides methods to
process user messages (updating state) and generate responses based on the
selected action. It includes AI-driven memory importance detection and
enhanced image memory capabilities.
"""

import json
import random
from datetime import datetime
from typing import Optional, List
import logging

from .pet_state import PetState
from .language_generation import generate_text, generate_text_with_image
from .image_recognition import extract_features, classify_image
from .nerve_integration import load_agent_config
from .ai_memory_analyzer import analyze_conversation_importance, analyze_image_memory

logger = logging.getLogger(__name__)

class VirtualPet:
    def __init__(self, personality_archetype: Optional[str] = None) -> None:
        self.state = PetState()
        self.pending_image = None  # Store image bytes temporarily for multimodal response
        
        # Initialize personality engine based on configuration or random
        try:
            config = load_agent_config()
        except Exception:
            config = {}
        
        # Check if personality archetype is specified in config
        if isinstance(config, dict):
            agent_section = config.get("agent") or {}
            if isinstance(agent_section, dict):
                self.system_prompt = agent_section.get("system_prompt") or ""
                # Get personality archetype from config if not provided
                if not personality_archetype:
                    personality_archetype = agent_section.get("personality_archetype")
            else:
                self.system_prompt = ""
        else:
            self.system_prompt = ""
        
        # Initialize personality (random if no archetype specified)
        self.state.initialize_personality(archetype=personality_archetype)

    def user_message(self, text: str, delay: Optional[float] = None) -> None:
        """Process a user message and update the pet state with AI-driven importance analysis."""
        if delay is None:
            # simulate a random delay in minutes for testing
            delay = random.uniform(1, 20)
        
        # AI-driven importance analysis
        existing_facts = self.state.memory.get_semantic_facts(min_weight=0.3)
        importance_score, extracted_facts = analyze_conversation_importance(text, existing_facts)
        
        logger.info(f"💡 Message importance: {importance_score:.2f}, extracted {len(extracted_facts)} facts")
        
        # Add extracted facts to semantic memory
        current_time = datetime.utcnow()
        for fact in extracted_facts:
            fact_key = fact.lower().strip()
            # Check if this reinforces existing memory
            if not self.state.memory.reinforce_memory(fact_key, boost=0.3):
                # New fact
                self.state.memory.semantic[fact_key] = (importance_score, current_time, 1)
                logger.info(f"🆕 New fact learned: {fact}")
        
        # Update pet state with interaction
        self.state.update_from_interaction(text, delay)
        
        # Override the default importance score with AI-determined one
        if self.state.memory.episodic:
            # Update the most recent episodic memory with AI importance
            latest_memory = self.state.memory.episodic[-1]
            latest_memory.importance_score = importance_score

    def user_image(self, image_bytes: bytes, delay: Optional[float] = None) -> None:
        """Process an image sent by the user with AI-driven analysis.

        This method analyzes the image using AI to extract detailed information,
        detect entities (people, animals, objects), and determine importance.
        The enhanced image memory will be used when generating the next response.

        Args:
            image_bytes: Raw bytes of the image sent by the user.
            delay: Optional simulated response delay in minutes.
        """
        logger.info("📷 Received image: %d bytes", len(image_bytes))
        
        # Store image for multimodal response
        self.pending_image = image_bytes
        
        if delay is None:
            delay = random.uniform(1, 20)
        
        # Extract features for similarity matching
        features = extract_features(image_bytes)
        
        # Get labels (if Vision API available)
        labels = classify_image(image_bytes)
        
        # AI-driven image analysis
        recent_memories = self.state.memory.recall(top_k=5)
        existing_facts = self.state.memory.get_semantic_facts(min_weight=0.3)
        user_message = recent_memories[0] if recent_memories else ""
        
        ai_analysis = analyze_image_memory(
            image_bytes,
            user_message,
            existing_facts,
            recent_memories
        )
        
        logger.info(f"🤖 AI image analysis: {ai_analysis['description'][:50]}...")
        logger.info(f"🏷️ Detected entities: {ai_analysis['entities']}")
        logger.info(f"💯 Image importance: {ai_analysis['importance']:.2f}")
        
        # Store enhanced image memory
        self.state.memory.add_image_memory(
            features=features,
            labels=ai_analysis.get('labels', labels),
            ai_description=ai_analysis.get('description', ''),
            detected_entities=ai_analysis.get('entities', {}),
            context=user_message,
            importance_score=ai_analysis.get('importance', 0.5)
        )
        
        # Add episodic memory with AI importance
        episode_text = f"recebeu uma imagem: {ai_analysis.get('description', 'imagem do usuário')}"
        self.state.memory.add_episode(
            episode_text,
            salience=0.8,
            importance_score=ai_analysis.get('importance', 0.5)
        )
        
        # Extract facts from entities (e.g., "tem pet: gato laranja")
        current_time = datetime.utcnow()
        for entity_type, entity_desc in ai_analysis.get('entities', {}).items():
            if entity_type in ['person', 'animal']:
                fact_key = f"imagem {entity_type}: {entity_desc}"
                self.state.memory.semantic[fact_key] = (ai_analysis['importance'], current_time, 1)
                logger.info(f"🖼️ Stored image fact: {fact_key}")
        
        logger.info("🧠 Stored enhanced image memory")
        
        # Lightly boost curiosity and sociability due to visual stimulation
        self.state.drives["curiosity"] = min(1.0, self.state.drives["curiosity"] + 0.05)
        self.state.drives["sociability"] = min(1.0, self.state.drives["sociability"] + 0.02)

    def pet_response(self) -> str:
        """Generate the pet's response based on the current context and conversation history."""
        # Check if there's a pending image to analyze
        if self.pending_image:
            response = self._generate_image_response(self.pending_image)
            self.pending_image = None  # Clear after use
            return response
        
        # Regular text response using AI-driven approach
        return self._generate_ai_response()
    
    def _generate_image_response(self, image_bytes: bytes) -> str:
        """Generate a response about an image using Gemini multimodal with personality integration."""
        # Get context
        user_facts = self.state.memory.get_semantic_facts(min_weight=0.3)
        recent_memories = self.state.memory.recall(top_k=5)
        personality_desc = self.state.get_personality_description()
        
        # Get previous image memories for context
        image_memories = self.state.memory.get_image_memories_with_context(top_k=3)
        
        # Build rich context
        context_parts = []
        if personality_desc:
            context_parts.append(f"SUA PERSONALIDADE: {personality_desc}")
        if user_facts:
            context_parts.append(f"O QUE VOCÊ SABE: {'; '.join(user_facts[:10])}")
        if recent_memories:
            context_parts.append(f"CONVERSA RECENTE: {' | '.join(recent_memories[:3])}")
        if image_memories:
            img_context = [f"Imagem anterior: {img['description']}" 
                          for img in image_memories if img.get('description')]
            if img_context:
                context_parts.append(f"MEMÓRIAS VISUAIS: {' | '.join(img_context[:2])}")
        
        context = "\n".join(context_parts) if context_parts else None
        
        # Get the user's message that came WITH the image
        user_message = recent_memories[0] if recent_memories else ""
        
        # Create personality-driven prompt for image analysis
        prompt = f"""Você é um pet virtual orgânico com personalidade única. O usuário enviou uma imagem junto com: "{user_message}"

INSTRUÇÕES - Responda de acordo com SUA personalidade:
- Descreva o que você vê de forma natural e autêntica (não robótica)
- CONECTE com o que você sabe sobre o usuário
- Se reconhecer algo familiar, mencione
- Seja genuíno e conciso (1-2 frases)
- Deixe sua personalidade brilhar na resposta

Responda sobre a imagem:"""
        
        logger.info("🖼️ Generating personality-driven multimodal response")
        return generate_text_with_image(prompt, image_bytes, context)
    
    def _generate_ai_response(self) -> str:
        """Generate an intelligent AI-driven response based on personality and context."""
        # Get conversation context
        recent_memories = self.state.memory.recall(top_k=5)
        user_facts = self.state.memory.get_semantic_facts(min_weight=0.3)
        last_message = recent_memories[0] if recent_memories else "Primeira interação"
        
        # Get personality and current emotional state
        personality_desc = self.state.get_personality_description()
        
        # Build emotional/drive state description
        drive_state = self._describe_current_state()
        
        logger.info(f"🤖 Generating AI response for: '{last_message[:50]}...'")
        logger.info(f"🧠 User facts: {len(user_facts)}, Recent memories: {len(recent_memories)}")
        
        # Build comprehensive context for AI
        context_parts = []
        
        # Add personality
        if personality_desc:
            context_parts.append(f"SUA PERSONALIDADE: {personality_desc}")
        
        # Add what we know about the user
        if user_facts:
            facts_text = "; ".join(user_facts[:10])
            context_parts.append(f"O QUE VOCÊ SABE SOBRE O USUÁRIO: {facts_text}")
        
        # Add conversation history
        if len(recent_memories) > 1:
            history = " → ".join(recent_memories[-3:])  # Last 3 exchanges
            context_parts.append(f"HISTÓRICO DA CONVERSA: {history}")
        
        # Add current emotional state
        if drive_state:
            context_parts.append(f"ESTADO ATUAL: {drive_state}")
        
        context = "\n".join(context_parts) if context_parts else None
        
        # Create intelligent dynamic prompt
        prompt = self._build_dynamic_prompt(last_message, recent_memories, user_facts)
        
        return generate_text(prompt, context)
    
    def _describe_current_state(self) -> str:
        """Describe the pet's current emotional/mental state based on drives."""
        descriptions = []
        
        # Check dominant drives
        if self.state.drives.get("curiosity", 0) > 0.7:
            descriptions.append("muito curioso")
        if self.state.drives.get("affection", 0) > 0.7:
            descriptions.append("carinhoso")
        if self.state.drives.get("humor", 0) > 0.7:
            descriptions.append("brincalhão")
        if self.state.drives.get("creativity", 0) > 0.7:
            descriptions.append("inspirado")
        if self.state.drives.get("sociability", 0) > 0.7:
            descriptions.append("sociável")
        
        # Check low/negative states
        if self.state.drives.get("boredom", 0) > 0.5:
            descriptions.append("entediado")
        if self.state.drives.get("loneliness", 0) > 0.5:
            descriptions.append("solitário")
        if self.state.drives.get("anxiety", 0) > 0.5:
            descriptions.append("ansioso")
        
        return ", ".join(descriptions) if descriptions else "equilibrado"
    
    def _build_dynamic_prompt(self, last_message: str, recent_memories: List[str], user_facts: List[str]) -> str:
        """Build a dynamic prompt based on conversation state and personality."""
        # Check conversation stage
        is_first_interaction = len(recent_memories) <= 1
        is_question = last_message.strip().endswith('?')
        
        # Base instruction - always natural and personality-driven
        base_instruction = """Você é um pet virtual orgânico com personalidade única.

IMPORTANTE:
- Responda de forma NATURAL e autêntica, de acordo com SUA personalidade
- Use o que você sabe sobre o usuário para personalizar suas respostas
- NÃO seja robótico ou formulaico
- Seja conciso (1-2 frases no máximo)
- Varie suas respostas - não seja repetitivo
"""
        
        # Add situation-specific guidance
        if is_first_interaction:
            situation = f"""
SITUAÇÃO: Primeira interação com o usuário
Mensagem dele: "{last_message}"

Responda de forma calorosa e autêntica, apresentando-se de acordo com sua personalidade.
"""
        elif is_question:
            situation = f"""
SITUAÇÃO: O usuário fez uma pergunta
Pergunta: "{last_message}"

Responda de forma útil e natural. Se você souber a resposta (baseado nos fatos que conhece sobre o usuário), responda com confiança. Se não souber, seja honesto.
"""
        else:
            # Check if we have enough context for deeper conversation
            has_user_context = len(user_facts) > 2
            
            if has_user_context:
                situation = f"""
SITUAÇÃO: Conversando com alguém que você conhece
Última mensagem: "{last_message}"

Responda de forma natural, mostrando que você se lembra dele e do que já conversaram. Seja autêntico de acordo com sua personalidade.
"""
            else:
                situation = f"""
SITUAÇÃO: Conhecendo o usuário
Mensagem: "{last_message}"

Responda de forma natural e, se fizer sentido com sua personalidade, faça uma pergunta para conhecê-lo melhor.
"""
        
        return base_instruction + situation + "\nResponda agora:"

    def simulate_conversation(self, turns: int = 5) -> None:
        """Run a simple simulation of user and pet interactions."""
        for i in range(turns):
            user_input = random.choice([
                "Vamos ouvir música?",
                "Jogue comigo!",
                "Fale sobre filmes",
                "Conta uma piada",
                "Nada agora",
            ])
            print(f"Usuário: {user_input}")
            self.user_message(user_input)
            response = self.pet_response()
            # Print the pet's response on its own line
            print(f"Pet: {response}")
            self.state.tick(minutes=30)
            if i % 3 == 2:
                self.state.memory.consolidate()

        # Print final state summary
        print("\nEstado final:")
        print(json.dumps({
            "drives": self.state.drives,
            "traits": self.state.traits,
            "habits": self.state.habits,
            "episodic": [m.text for m in self.state.memory.episodic],
            "semantic": self.state.memory.semantic,
        }, indent=2))


if __name__ == "__main__":
    pet = VirtualPet()
    print("Simulação de conversa:")
    pet.simulate_conversation(turns=8)
