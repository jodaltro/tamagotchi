"""
High-level interface to the organic virtual pet.

The `VirtualPet` class wraps a `PetState` instance and provides methods to
process user messages (updating state) and generate responses based on the
selected action. When run directly, this module runs a simple simulation for
manual testing.
"""

import json
import random
from datetime import datetime
from typing import Optional

from .pet_state import PetState
from .language_generation import generate_text, generate_text_with_image
from .image_recognition import extract_features, classify_image
from .nerve_integration import load_agent_config

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
        """Process a user message and update the pet state."""
        if delay is None:
            # simulate a random delay in minutes for testing
            delay = random.uniform(1, 20)
        self.state.update_from_interaction(text, delay)

    def user_image(self, image_bytes: bytes, delay: Optional[float] = None) -> None:
        """Process an image sent by the user and update the pet state.

        This method stores the image for multimodal analysis with Gemini.
        The image will be analyzed when generating the next response.

        Args:
            image_bytes: Raw bytes of the image sent by the user.
            delay: Optional simulated response delay in minutes.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("📷 Received image: %d bytes", len(image_bytes))
        
        # Store image for multimodal response
        self.pending_image = image_bytes
        
        if delay is None:
            delay = random.uniform(1, 20)
        
        # Add an episodic entry
        self.state.memory.add_episode("recebeu uma imagem do usuário", salience=0.8)
        logger.info("🧠 Stored image for multimodal analysis")
        
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
        
        # Regular text response
        return self._generate_text_response()
    
    def _generate_image_response(self, image_bytes: bytes) -> str:
        """Generate a response about an image using Gemini multimodal."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get context - CRITICAL: get recent conversation INCLUDING the message sent WITH the image
        user_facts = list(self.state.memory.semantic.keys())
        recent_memories = self.state.memory.recall(top_k=5)  # Get more context
        personality_desc = self.state.get_personality_description()
        
        # Build rich context
        context_parts = []
        if personality_desc:
            context_parts.append(f"Sua personalidade: {personality_desc}")
        if user_facts:
            context_parts.append(f"O que você sabe sobre o usuário: {'; '.join(user_facts[:5])}")
        if recent_memories:
            context_parts.append(f"Conversa recente: {' | '.join(recent_memories)}")
        
        context = "\n".join(context_parts) if context_parts else None
        
        # Get the user's message that came WITH the image (should be the most recent memory)
        user_message = recent_memories[0] if recent_memories else ""
        
        # Create intelligent prompt for image analysis
        prompt = f"""Você é um pet virtual orgânico. O usuário enviou uma imagem junto com esta mensagem: "{user_message}"

CONTEXTO DA CONVERSA:
- Você conhece bem o usuário e sua história
- Use o que você sabe sobre ele para dar uma resposta mais personalizada
- Se você já conhece algo relacionado à imagem (ex: ele tem um gato), mencione isso naturalmente

INSTRUÇÕES:
- Descreva o que você vê na imagem de forma natural e empolgada
- RELACIONE com o que você sabe sobre o usuário (muito importante!)
- Se ele mencionou algo na mensagem, comente sobre isso
- Seja conciso (1-2 frases)
- Pode fazer uma pergunta sobre a imagem
- Seja autêntico e demonstre que você se lembra das conversas anteriores

Responda sobre a imagem:"""
        
        logger.info("🖼️ Generating multimodal response with context: %d facts, %d memories", 
                    len(user_facts), len(recent_memories))
        return generate_text_with_image(prompt, image_bytes, context)
    
    def _generate_text_response(self) -> str:
        """Generate a regular text response."""
        # Get recent conversation history
        recent_memories = self.state.memory.recall(top_k=8)  # More context
        
        # Get semantic facts about the user
        user_facts = list(self.state.memory.semantic.keys())
        
        # Get personality description
        personality_desc = self.state.get_personality_description()
        
        # Build intelligent context for the AI
        context_parts = []
        
        # Add personality
        if personality_desc:
            context_parts.append(f"Sua personalidade: {personality_desc}")
        
        # Add what you know about the user - ALL facts, not just 3
        if user_facts:
            context_parts.append(f"O que você sabe sobre o usuário: {'; '.join(user_facts)}")
        
        # Add recent conversation - show ALL recent memories
        if recent_memories:
            context_parts.append(f"Conversa recente (do mais antigo ao mais novo): {' | '.join(recent_memories)}")
        
        # Add current drives/mood
        dominant_drives = sorted(self.state.drives.items(), key=lambda x: x[1], reverse=True)[:2]
        mood_desc = f"Você está se sentindo {dominant_drives[0][0]} ({dominant_drives[0][1]:.1f}) e {dominant_drives[1][0]} ({dominant_drives[1][1]:.1f})"
        context_parts.append(mood_desc)
        
        # Create the full context
        full_context = "\n".join(context_parts)
        
        # Get the most recent user message
        last_message = recent_memories[0] if recent_memories else "Primeira interação"
        
        # Create an intelligent prompt
        prompt = f"""Você é um pet virtual orgânico com uma personalidade única e memória. Analise TODO o contexto da conversa e responda de forma natural e inteligente.

ÚLTIMA MENSAGEM DO USUÁRIO: "{last_message}"

IMPORTANTE - MEMÓRIA E CONTEXTO:
- Você TEM memória de todas as conversas anteriores
- Use o que você sabe sobre o usuário para personalizar sua resposta
- Se o usuário mencionou algo antes (ex: tem um gato, nome, idade), você DEVE se lembrar disso
- Seja consistente com o que já foi conversado
- Demonstre que você se lembra das interações anteriores

COMO RESPONDER:
- Se é continuação de uma conversa, continue naturalmente
- Se o usuário perguntou algo, responda usando seu conhecimento sobre ele
- Se o usuário contou algo novo, demonstre interesse E relacione com o que já sabe
- Seja conciso (1-2 frases, máximo 3)
- Seja autêntico, amigável e demonstre memória

Responda naturalmente (lembrando-se de tudo que foi conversado):"""
        
        # Use the language generation utility
        return generate_text(prompt, full_context)

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
