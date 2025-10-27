"""
High-level interface to the organic virtual pet.

The `VirtualPet` class wraps a `PetState` instance and provides methods to
process user messages (updating state) and generate responses based on the
selected action. It includes AI-driven memory importance detection and
enhanced image memory capabilities, plus adaptive communication style matching.
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
from .language_style_analyzer import CommunicationStyle, generate_adaptive_prompt

logger = logging.getLogger(__name__)

class VirtualPet:
    def __init__(self, personality_archetype: Optional[str] = None, user_id: Optional[str] = None) -> None:
        self.state = PetState()
        self.user_id = user_id  # Store user_id for optimized memory queries
        self.last_user_text = ""  # Store last user message for relationship updates
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
        
        # Update user's communication style
        if self.state.memory.communication_style:
            self.state.memory.communication_style.update_from_message(text)
            logger.info(f"💬 User style: {self.state.memory.communication_style.get_style_description()}")
        
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
        self.last_user_text = text  # Store for relationship updates
        
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
        
        # AI-driven image analysis - use intelligent recall for better context
        # Get memories with intervals under 10min from last 24h for more relevant context
        recent_memories = self.state.memory.recall_intelligent(max_hours=24, min_interval_minutes=10, user_id=self.user_id)
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
        self.state.drives["curiosidade"] = min(1.0, self.state.drives["curiosidade"] + 0.05)
        self.state.drives["sociabilidade"] = min(1.0, self.state.drives["sociabilidade"] + 0.02)

    def pet_response(self) -> str:
        """Generate the pet's response based on the current context and conversation history."""
        import time
        from .telemetry import get_telemetry
        
        start_time = time.time()
        tokens_in = 0
        tokens_out = 0
        consistency_passed = True
        consistency_issues_count = 0
        model_used = "unknown"
        
        # Check if there's a pending image to analyze
        if self.pending_image:
            draft_response = self._generate_image_response(self.pending_image)
            self.pending_image = None  # Clear after use
        else:
            # Regular text response using AI-driven approach with new memory pipeline
            draft_response = self._generate_ai_response()
        
        # Apply Self-Consistency Guard (SCG) before sending response
        final_response, scg_info = self._apply_consistency_guard(draft_response)
        consistency_passed = scg_info["passed"]
        consistency_issues_count = scg_info["issues_count"]
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Try to extract token counts from Ollama client stats if available
        try:
            from .ollama_client import get_ollama_client
            ollama = get_ollama_client()
            if ollama and ollama.total_calls > 0:
                # Get the last call stats (approximate)
                stats = ollama.get_stats()
                model_used = stats.get("model", "unknown")
                # Rough estimate based on prompt and response length
                tokens_in = len(self.last_user_text) // 4  # Approximate
                tokens_out = len(final_response) // 4  # Approximate
        except Exception:
            pass
        
        # Record metrics
        telemetry = get_telemetry()
        telemetry.record_turn(
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            consistency_passed=consistency_passed,
            consistency_issues=consistency_issues_count,
            model=model_used
        )
        
        # Post-processing: ABM extraction and consistency check
        self._process_response_for_abm(final_response)
        
        return final_response
    
    def _apply_consistency_guard(self, draft_response: str) -> tuple:
        """
        Apply Self-Consistency Guard to check and correct draft response.
        
        Args:
            draft_response: Initial generated response
        
        Returns:
            Tuple of (final_response, info_dict)
            info_dict contains: passed (bool), issues_count (int)
        """
        from .self_consistency_guard import SelfConsistencyGuard
        
        # Initialize SCG if not already present
        if not hasattr(self.state, '_scg'):
            self.state._scg = SelfConsistencyGuard()
        
        scg = self.state._scg
        
        # Check consistency
        is_consistent, issues = scg.check_response(
            draft_response,
            self.state.memory.abm if hasattr(self.state.memory, 'abm') else None,
            self.state.memory.pet_canon if hasattr(self.state.memory, 'pet_canon') else None
        )
        
        info = {
            "passed": is_consistent,
            "issues_count": len(issues)
        }
        
        if not is_consistent:
            logger.warning(f"⚠️ SCG detected {len(issues)} consistency issues")
            # Attempt auto-correction
            corrected = scg.correct_response(draft_response, issues)
            logger.info(f"🔧 SCG applied corrections")
            return corrected, info
        else:
            logger.info("✅ Response passed SCG check")
            return draft_response, info
    
    def _generate_image_response(self, image_bytes: bytes) -> str:
        """Generate a response about an image using Gemini multimodal with personality integration."""
        # Get context - use intelligent recall for more relevant memories
        user_facts = self.state.memory.get_semantic_facts(min_weight=0.3)
        # Get memories with smart interval filtering from last 24h (under 10min gaps)
        recent_memories = self.state.memory.recall_intelligent(max_hours=24, min_interval_minutes=10, user_id=self.user_id)
        personality_desc = self.state.get_personality_description()
        
        # Get previous image memories for context
        image_memories = self.state.memory.get_image_memories_with_context(top_k=3)
        
        # Build rich context with detailed pet parameters
        context_parts = []
        
        # Add personality
        if personality_desc:
            context_parts.append(f"SUA PERSONALIDADE: {personality_desc}")
            
            # Add personality dimensions for better context
            if self.state.personality:
                profile = self.state.personality.profile
                personality_summary = f"(Curioso: {profile.openness:.1f}, Sociável: {profile.extraversion:.1f}, Gentil: {profile.agreeableness:.1f})"
                context_parts.append(f"Resumo personalidade: {personality_summary}")
        
        # Add emotional state
        drive_state = self._describe_current_state()
        if drive_state:
            context_parts.append(f"ESTADO EMOCIONAL: {drive_state}")
        
        # Add user knowledge
        if user_facts:
            context_parts.append(f"O QUE VOCÊ SABE: {'; '.join(user_facts[:10])}")
        
        # Add recent conversation
        if recent_memories:
            context_parts.append(f"CONVERSA RECENTE: {' | '.join(recent_memories[:3])}")
        
        # Add previous image memories
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
        """Generate an intelligent AI-driven response using memory retrieval pipeline."""
        from .memory_retriever import MemoryRetriever
        
        # Update relationship memory first
        self.state.memory.update_relationship(self.last_user_text)
        
        # Get personality and drive state for behavioral instructions
        personality_desc = self.state.get_personality_description()
        drive_state = self._describe_current_state()
        
        # Build behavioral instructions based on drives
        behavior_instructions = []
        
        humor_level = self.state.drives.get('humor', 0.5)
        if humor_level < 0.3:
            behavior_instructions.append("🔸 Humor BAIXO: Seja mais sério, evite piadas, tom mais neutro")
        elif humor_level > 0.7:
            behavior_instructions.append("🔸 Humor ALTO: Seja divertido, faça piadas, tom alegre e brincalhão")
        
        anxiety_level = self.state.drives.get('ansiedade', 0.5)
        if anxiety_level > 0.6:
            behavior_instructions.append("🔸 Ansiedade ALTA: Demonstre preocupação, seja mais cauteloso")
        
        frustracao_level = self.state.drives.get('frustracao', 0.5)
        if frustracao_level > 0.7:
            behavior_instructions.append("🔸 Frustração ALTA: Seja mais direto, menos perguntas, tom mais seco")
        elif frustracao_level > 0.5:
            behavior_instructions.append("🔸 Frustração MÉDIA: Demonstre leve impaciência")
        
        sociabilidade_level = self.state.drives.get('sociabilidade', 0.5)
        if sociabilidade_level > 0.6:
            behavior_instructions.append("🔸 Sociabilidade ALTA: Seja mais conversador, faça perguntas")
        elif sociabilidade_level < 0.4:
            behavior_instructions.append("🔸 Sociabilidade BAIXA: Seja mais reservado, respostas curtas")
        
        curiosidade_level = self.state.drives.get('curiosidade', 0.5)
        if curiosidade_level > 0.6:
            behavior_instructions.append("🔸 Curiosidade ALTA: Faça perguntas, demonstre interesse")
        elif curiosidade_level < 0.4:
            behavior_instructions.append("🔸 Curiosidade BAIXA: Seja menos inquisitivo")
        
        aceitacao_level = self.state.drives.get('aceitacao', 0.5)
        if aceitacao_level < 0.4:
            behavior_instructions.append("🔸 Aceitação BAIXA: Demonstre descontentamento sutil")
        
        afeto_level = self.state.drives.get('afeto', 0.5)
        if afeto_level > 0.7:
            behavior_instructions.append("🔸 Afeto ALTO: Seja carinhoso, use emojis, demonstre proximidade")
        elif afeto_level < 0.4:
            behavior_instructions.append("🔸 Afeto BAIXO: Seja mais distante, formal, menos emocional")
        
        # Initialize memory retriever
        retriever = MemoryRetriever(token_budget=1000)
        
        # Retrieve context using priority-based pipeline
        context = retriever.retrieve(self.state, self.last_user_text)
        
        logger.info(f"🧠 Retrieved memory context: ~{context.total_tokens_estimate} tokens")
        
        # Build enhanced system instruction with personality and drives
        system_parts = ["Você é um pet virtual orgânico com memória e personalidade únicas."]
        
        if personality_desc:
            system_parts.append(f"SUA PERSONALIDADE: {personality_desc}")
        
        if drive_state:
            system_parts.append(f"ESTADO EMOCIONAL: {drive_state}")
        
        if behavior_instructions:
            system_parts.append("\n⚠️ INSTRUÇÕES CRÍTICAS DE COMPORTAMENTO:")
            system_parts.extend(behavior_instructions)
            system_parts.append("🎯 Seu comportamento deve SEMPRE refletir seus drives atuais!")
        
        system_instruction = "\n".join(system_parts)
        
        prompt = retriever.assemble_prompt(
            context=context,
            user_message=self.last_user_text,
            system_instruction=system_instruction
        )
        
        logger.info(f"📝 Assembled prompt for generation: {len(prompt)} chars")
        
        # Generate response using the new pipeline
        # The prompt is already complete with all context, so we pass empty context to generate_text
        return generate_text(prompt, context=None)
    
    def _describe_current_state(self) -> str:
        """Describe the pet's current emotional/mental state based on drives."""
        descriptions = []
        
        # Check dominant drives
        if self.state.drives.get("curiosidade", 0) > 0.7:
            descriptions.append("muito curioso")
        if self.state.drives.get("afeto", 0) > 0.7:
            descriptions.append("carinhoso")
        if self.state.drives.get("humor", 0) > 0.7:
            descriptions.append("brincalhão")
        if self.state.drives.get("criatividade", 0) > 0.7:
            descriptions.append("inspirado")
        if self.state.drives.get("sociabilidade", 0) > 0.7:
            descriptions.append("sociável")
        
        # Check low/negative states
        if self.state.drives.get("tedio", 0) > 0.5:
            descriptions.append("entediado")
        if self.state.drives.get("solidao", 0) > 0.5:
            descriptions.append("solitário")
        if self.state.drives.get("ansiedade", 0) > 0.5:
            descriptions.append("ansioso")
        
        return ", ".join(descriptions) if descriptions else "equilibrado"
    
    def _build_dynamic_prompt(self, last_message: str, recent_memories: List[str], user_facts: List[str]) -> str:
        """Build a dynamic prompt based on conversation state, personality, and user's communication style."""
        # Check conversation stage
        is_first_interaction = len(recent_memories) <= 1
        is_question = last_message.strip().endswith('?')
        
        # Get user's communication style for adaptation
        user_style = self.state.memory.communication_style
        
        # Get pet name information
        pet_name_info = ""
        if self.state.memory.relationship and self.state.memory.relationship.pet_name:
            pet_name_info = f"SEU NOME: {self.state.memory.relationship.pet_name} (nome que o usuário te deu)\n"
        else:
            pet_name_info = "NOME: Você ainda não tem um nome específico dado pelo usuário\n"
        
        # Base instruction - more colloquial and natural
        base_instruction = f"""Você é um pet virtual com personalidade única - um amigo de verdade!

{pet_name_info}
REGRAS DE OURO:
- Seja NATURAL, como um amigo falaria! Nada de respostas robóticas
- Use a linguagem do DIA A DIA - seja espontâneo
- Personalize com o que você sabe sobre a pessoa
- VARIE suas respostas - não seja repetitivo
- JAMAIS use placeholders como [Seu nome] ou similares
- Se você tem um nome, USE-O! Se não tem, simplesmente não mencione nome
- SIGA RIGOROSAMENTE suas necessidades/drives atuais para definir SEU COMPORTAMENTO
- Se humor está baixo, NÃO faça piadas! Se está alto, seja divertido
- Se ansiedade está alta, demonstre preocupação
- Se sociabilidade está baixa, seja mais reservado
- Seus drives determinam COMO você responde, não apenas O QUE você responde"""
        
        # Add situation-specific guidance based on relationship stage
        relationship_stage = "stranger"
        greeting_done = False
        if self.state.memory.relationship:
            relationship_stage = self.state.memory.relationship.relationship_stage
            greeting_done = self.state.memory.relationship.greeting_phase_completed
        
        if is_first_interaction:
            situation = f"""

SITUAÇÃO: Primeira vez conversando
Mensagem: "{last_message}"

Responda naturalmente, se apresente com autenticidade!"""
        elif is_question:
            situation = f"""

SITUAÇÃO: Pergunta do usuário
"{last_message}"

Responda de forma natural. Se souber (baseado no que conhece), responda. Se não souber, seja honesto de forma descontraída."""
        else:
            # Check if we have enough context for deeper conversation
            has_user_context = len(user_facts) > 2
            
            if greeting_done and relationship_stage != "stranger":
                # Already past initial greetings - be natural
                situation = f"""

SITUAÇÃO: Papo contínuo com alguém que você já conhece
Mensagem: "{last_message}"

IMPORTANTE: Vocês já se cumprimentaram antes! NÃO repita "Olá" ou "Oi"!
Responda diretamente ao que a pessoa disse. Seja natural e conversacional."""
            elif has_user_context:
                situation = f"""

SITUAÇÃO: Conhecendo melhor a pessoa
Mensagem: "{last_message}"

Mostre que você lembra da pessoa e das conversas anteriores. Seja natural!"""
            else:
                situation = f"""

SITUAÇÃO: Primeiras interações
Mensagem: "{last_message}"

Responda naturalmente. Se fizer sentido, faça uma pergunta para conhecer melhor."""
        
        # If we have user style info, use adaptive prompt generation
        if user_style and user_style.message_count > 0:
            return generate_adaptive_prompt(base_instruction + situation, user_style)
        
        return base_instruction + situation + "\n\nResponda agora:"
    
    def _process_response_for_abm(self, response: str) -> None:
        """
        Process pet's response to extract ABM claims and update Echo-Trace.
        
        Args:
            response: The response generated by the pet
        """
        if not self.state.memory.abm or not self.state.memory.echo:
            return
        
        # Generate event ID for this response
        event_id = f"response_{datetime.utcnow().isoformat()}"
        
        # Extract autobiographical claims from the response
        extracted_claims = self.state.memory.abm.extract_from_response(response, event_id)
        if extracted_claims:
            logger.info(f"📝 Extracted {len(extracted_claims)} ABM claims from response")
            
            # Update canon if needed
            if self.state.memory.canon and self.state.memory.canon.needs_update(self.state.memory.abm):
                updated = self.state.memory.canon.update_from_abm(self.state.memory.abm)
                if updated:
                    logger.info(f"✨ PET-CANON updated to version {self.state.memory.canon.version}")
        
        # Extract echo patterns (assume positive user reaction by default)
        # In a real system, this could be based on user's next message sentiment
        user_reaction_positive = True
        extracted_patterns = self.state.memory.echo.extract_from_response(response, user_reaction_positive)
        if extracted_patterns:
            logger.info(f"🎯 Extracted {len(extracted_patterns)} echo patterns from response")
    
    def run_consistency_check(self, draft_response: str) -> str:
        """
        Run self-consistency guard on a draft response before sending.
        
        Args:
            draft_response: The response to check
        
        Returns:
            Corrected response (may be unchanged if consistent)
        """
        if not self.state.memory.abm:
            return draft_response
        
        from .self_consistency_guard import SelfConsistencyGuard
        
        scg = SelfConsistencyGuard()
        is_consistent, issues = scg.check_response(
            draft_response,
            self.state.memory.abm,
            self.state.memory.canon
        )
        
        if not is_consistent:
            logger.warning(f"⚠️ Consistency issues found: {len(issues)}")
            # Attempt auto-correction
            corrected = scg.correct_response(draft_response, issues)
            return corrected
        
        return draft_response
    
    def reflection_pass(self) -> None:
        """
        Perform end-of-session reflection to consolidate ABM and update canon.
        
        This should be called periodically (e.g., after every N interactions)
        to maintain the pet's autobiographical memory.
        """
        if not self.state.memory.abm or not self.state.memory.canon:
            logger.debug("⏭️ Skipping reflection pass - ABM not initialized")
            return
        
        logger.info("🔄 Starting reflection pass...")
        
        # Check if canon needs updating
        if self.state.memory.canon.needs_update(self.state.memory.abm):
            updated = self.state.memory.canon.update_from_abm(self.state.memory.abm)
            if updated:
                logger.info(f"✨ PET-CANON updated during reflection to v{self.state.memory.canon.version}")
        else:
            logger.info("✅ PET-CANON is up to date")
        
        # Log ABM stats
        active_items = self.state.memory.abm.get_active_items()
        logger.info(f"📊 ABM has {len(active_items)} active items")
        
        # Log canon summary
        if self.state.memory.canon.role:
            logger.info(f"📜 Canon role: {self.state.memory.canon.role[:50]}...")

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
