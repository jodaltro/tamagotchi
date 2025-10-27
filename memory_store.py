"""
Memory management for the organic virtual pet.

This module defines the `MemoryStore` class, which manages episodic and semantic
memories with AI-driven importance detection, reinforcement learning, and
advanced image memory capabilities. Episodic memories are recent experiences 
annotated with a salience score, while semantic memories are consolidated facts 
or preferences that persist long-term. The system supports memory decay, 
reinforcement, and intelligent extraction of important information.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import communication style analyzer
try:
    from .language_style_analyzer import CommunicationStyle
except ImportError:
    # Fallback for when running as script
    CommunicationStyle = None

# Import ABM modules
try:
    from .autobiographical_memory import AutobiographicalMemory
    from .pet_canon import PetCanon
    from .echo_trace import EchoTrace
except ImportError:
    # Fallback for when running as script
    AutobiographicalMemory = None
    PetCanon = None
    EchoTrace = None

@dataclass
class MemoryItem:
    kind: str
    text: str
    salience: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0  # For reinforcement learning
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    importance_score: float = 0.5  # AI-determined importance

    def __repr__(self) -> str:
        return f"MemoryItem(kind={self.kind}, text={self.text[:30]}..., salience={self.salience:.2f}, importance={self.importance_score:.2f})"


@dataclass
class RelationshipMemory:
    """Memória de relacionamento - como humanos lembram uns dos outros."""
    first_meeting: datetime
    total_interactions: int = 0
    last_interaction: datetime = field(default_factory=datetime.utcnow)
    familiarity_level: float = 0.0  # 0.0 = stranger, 1.0 = best friend
    conversation_topics: List[str] = field(default_factory=list)
    user_preferences: Dict[str, str] = field(default_factory=dict)  # likes/dislikes
    emotional_history: List[str] = field(default_factory=list)  # past emotional states
    relationship_stage: str = "stranger"  # stranger -> acquaintance -> friend -> close_friend
    
    # Pet identity information 
    pet_name: Optional[str] = None  # Name given by user to the pet
    greeting_phase_completed: bool = False  # Whether initial greetings are done
    
    def update_familiarity(self):
        """Atualiza o nível de familiaridade baseado em interações."""
        # Familiaridade cresce com interações e tempo
        days_knowing = (datetime.utcnow() - self.first_meeting).days
        interaction_factor = min(self.total_interactions / 50.0, 1.0)  # Cap at 50 interactions
        time_factor = min(days_knowing / 30.0, 1.0)  # Cap at 30 days
        
        self.familiarity_level = (interaction_factor * 0.7 + time_factor * 0.3)
        
        # Update relationship stage
        if self.familiarity_level < 0.2:
            self.relationship_stage = "stranger"
        elif self.familiarity_level < 0.5:
            self.relationship_stage = "acquaintance"
        elif self.familiarity_level < 0.8:
            self.relationship_stage = "friend"
        else:
            self.relationship_stage = "close_friend"


@dataclass
class ImageMemory:
    """Enhanced image memory with detailed AI-extracted information."""
    features: List[float]
    labels: List[str]
    timestamp: datetime
    ai_description: str = ""  # Detailed AI-generated description
    detected_entities: Dict[str, str] = field(default_factory=dict)  # e.g., {"person": "user", "style": "casual"}
    context: str = ""  # Conversation context when image was sent
    importance_score: float = 0.5
    
    def __repr__(self) -> str:
        return f"ImageMemory(labels={self.labels}, entities={len(self.detected_entities)}, importance={self.importance_score:.2f})"


@dataclass
class MemoryStore:
    """Stores episodic, semantic, visual, and relationship memories for a virtual pet with AI enhancement."""

    # Recent experiences with salience scores and reinforcement
    episodic: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Consolidated facts/preferences mapped to (weight, last_reinforced, access_count)
    semantic: Dict[str, Tuple[float, datetime, int]] = field(default_factory=dict)
    
    # Enhanced photographic memory with AI descriptions
    images: List[ImageMemory] = field(default_factory=list)
    
    # Long-term relationship memory
    relationship: Optional[RelationshipMemory] = None
    
    # User's communication style for adaptive responses
    communication_style: Optional[object] = None  # CommunicationStyle object
    
    # Autobiographical memory - pet's memory about itself
    abm: Optional[object] = None  # AutobiographicalMemory object
    
    # Pet canon - consolidated identity
    canon: Optional[object] = None  # PetCanon object
    
    # Echo trace - successful speech patterns
    echo: Optional[object] = None  # EchoTrace object
    
    # Memory decay tracking
    last_decay_time: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Initialize communication style and ABM components if not set."""
        if self.communication_style is None and CommunicationStyle is not None:
            self.communication_style = CommunicationStyle()
        
        # Initialize ABM components
        if self.abm is None and AutobiographicalMemory is not None:
            self.abm = AutobiographicalMemory()
        
        if self.canon is None and PetCanon is not None:
            self.canon = PetCanon()
        
        if self.echo is None and EchoTrace is not None:
            self.echo = EchoTrace()

    def add_episode(self, text: str, salience: float = 0.5, importance_score: float = 0.5) -> None:
        """Add a new episodic memory to the buffer with AI-determined importance."""
        self.episodic.append(MemoryItem(
            kind="episode", 
            text=text, 
            salience=salience,
            importance_score=importance_score
        ))
        logger.debug(f"🧠 Added episodic memory: {text[:50]}... (importance: {importance_score:.2f})")

    def add_image_memory(
        self, 
        features: List[float], 
        labels: List[str],
        ai_description: str = "",
        detected_entities: Optional[Dict[str, str]] = None,
        context: str = "",
        importance_score: float = 0.5
    ) -> None:
        """Store an enhanced photographic memory with AI analysis."""
        image_memory = ImageMemory(
            features=features,
            labels=labels,
            timestamp=datetime.utcnow(),
            ai_description=ai_description,
            detected_entities=detected_entities or {},
            context=context,
            importance_score=importance_score
        )
        self.images.append(image_memory)
        logger.info(f"🖼️ Added image memory: {labels} | Entities: {detected_entities} | Importance: {importance_score:.2f}")

    # Legacy method for backward compatibility
    def add_image(self, features: list[float], labels: List[str]) -> None:
        """Store a photographic memory (legacy method for backward compatibility)."""
        self.add_image_memory(features, labels)

    def consolidate(self, threshold: float = 0.6) -> None:
        """Promote highly salient and important episodes into semantic memory."""
        consolidated_count = 0
        for m in list(self.episodic):
            # Consider both salience and AI-determined importance
            combined_score = (m.salience * 0.4 + m.importance_score * 0.6)
            
            if combined_score >= threshold:
                key = m.text.lower().strip()
                
                # Update semantic memory with reinforcement
                if key in self.semantic:
                    old_weight, _, old_count = self.semantic[key]
                    # Reinforcement: increase weight based on repetition
                    new_weight = min(1.0, old_weight + combined_score * 0.3)
                    self.semantic[key] = (new_weight, datetime.utcnow(), old_count + 1)
                    logger.debug(f"🔄 Reinforced memory: {key[:50]}... (weight: {old_weight:.2f} → {new_weight:.2f})")
                else:
                    self.semantic[key] = (combined_score, datetime.utcnow(), 1)
                    consolidated_count += 1
                    logger.debug(f"✨ Consolidated new memory: {key[:50]}... (weight: {combined_score:.2f})")
                
                # Reduce salience to prevent repetitive promotion
                m.salience *= 0.1
        
        if consolidated_count > 0:
            logger.info(f"🧠 Consolidated {consolidated_count} new memories into semantic store")

    def apply_memory_decay(self, hours_elapsed: float = 24.0) -> None:
        """Apply decay to memories based on time and lack of access (forgetting)."""
        current_time = datetime.utcnow()
        decay_factor = hours_elapsed / (24.0 * 7.0)  # Weekly decay cycle
        
        # Decay semantic memories that haven't been accessed
        decayed_count = 0
        forgotten_keys = []
        
        for key, (weight, last_accessed, access_count) in list(self.semantic.items()):
            hours_since_access = (current_time - last_accessed).total_seconds() / 3600.0
            
            # Less accessed memories decay faster
            access_factor = 1.0 / (1.0 + access_count * 0.2)  # More accesses = slower decay
            time_factor = min(1.0, hours_since_access / (24.0 * 30.0))  # Normalize to monthly
            
            decay_amount = decay_factor * access_factor * time_factor * 0.1
            new_weight = max(0.0, weight - decay_amount)
            
            if new_weight < 0.1:
                # Forget memories that have decayed too much
                forgotten_keys.append(key)
                decayed_count += 1
            else:
                self.semantic[key] = (new_weight, last_accessed, access_count)
        
        # Remove forgotten memories
        for key in forgotten_keys:
            del self.semantic[key]
        
        if decayed_count > 0:
            logger.info(f"🌫️ Forgot {decayed_count} decayed memories")
        
        self.last_decay_time = current_time

    def reinforce_memory(self, memory_text: str, boost: float = 0.2) -> bool:
        """Reinforce a memory when it's mentioned again (reinforcement learning)."""
        key = memory_text.lower().strip()
        
        if key in self.semantic:
            old_weight, _, old_count = self.semantic[key]
            new_weight = min(1.0, old_weight + boost)
            self.semantic[key] = (new_weight, datetime.utcnow(), old_count + 1)
            logger.info(f"💪 Reinforced memory: {key[:50]}... ({old_weight:.2f} → {new_weight:.2f})")
            return True
        
        return False

    def update_relationship(self, text: str) -> None:
        """Atualiza a memória de relacionamento com base na interação."""
        current_time = datetime.utcnow()
        
        # Define name patterns and lower message for all code paths
        lower_message = text.lower()
        name_patterns = [
            "vou te chamar de", "te chamar de", "seu nome é", "você se chama",
            "chamarei de", "chamarei você de", "te chamo de", "nome será"
        ]
        
        # Inicializar relacionamento se for primeira vez
        if self.relationship is None:
            self.relationship = RelationshipMemory(
                first_meeting=current_time,
                total_interactions=1,
                last_interaction=current_time
            )
            logger.info("🤝 Relacionamento iniciado - primeiro encontro!")
        else:
            # Atualizar relacionamento existente
            self.relationship.total_interactions += 1
            self.relationship.last_interaction = current_time
            
            # Update familiarity (gradual increase with better progression)
            base_increase = 0.02  # Increased from 0.01
            message_bonus = 0.03 if len(text) > 20 else 0.01  # Increased bonuses
            name_bonus = 0.05 if any(pattern in lower_message for pattern in name_patterns) else 0
            question_bonus = 0.02 if "?" in text else 0
            
            total_increase = base_increase + message_bonus + name_bonus + question_bonus
            self.relationship.familiarity_level = min(1.0, self.relationship.familiarity_level + total_increase)
            
            logger.info(f"🤝 Relacionamento atualizado: {self.relationship.relationship_stage} "
                       f"(familiaridade: {self.relationship.familiarity_level:.2f}, "
                       f"interações: {self.relationship.total_interactions})")
        
        # Check for pet name assignment (use already defined variables)
        for pattern in name_patterns:
            if pattern in lower_message:
                # Extract potential name after the pattern
                parts = lower_message.split(pattern)
                if len(parts) > 1:
                    potential_name = parts[1].strip().split()[0]  # First word after pattern
                    if potential_name and len(potential_name) > 1:
                        self.relationship.pet_name = potential_name.capitalize()
                        logger.info(f"🎭 Pet recebeu nome: {self.relationship.pet_name}")
                        break
        
        # Extrair tópicos de conversa
        text_lower = text.lower()
        new_topics = []
        topic_keywords = {
            'música': ['música', 'cantar', 'tocar', 'banda', 'artista', 'bts'],
            'comida': ['comer', 'comida', 'mate', 'café', 'bebida'],
            'trabalho': ['trabalho', 'job', 'emprego', 'estudar'],
            'entretenimento': ['filme', 'série', 'jogo', 'kpop', 'video'],
            'sentimentos': ['feliz', 'triste', 'bem', 'mal', 'cansado'],
            'nome': ['nome', 'chamar', 'chamo']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                if topic not in self.relationship.conversation_topics:
                    new_topics.append(topic)
                    self.relationship.conversation_topics.append(topic)
        
        if new_topics:
            logger.info(f"💭 Novos tópicos descobertos: {', '.join(new_topics)}")
        
        # Update relationship stage based on familiarity and interactions (more responsive)
        if self.relationship.familiarity_level >= 0.4:  # Reduced from 0.7
            self.relationship.relationship_stage = "close_friend"
        elif self.relationship.familiarity_level >= 0.2:  # Reduced from 0.4
            self.relationship.relationship_stage = "friend"
        elif self.relationship.familiarity_level >= 0.05:  # Reduced from 0.1
            self.relationship.relationship_stage = "acquaintance"
        
        # Mark greeting phase as completed earlier
        if self.relationship.total_interactions >= 2:  # Reduced from 3
            self.relationship.greeting_phase_completed = True

    def get_relationship_context(self) -> str:
        """Gera contexto sobre o relacionamento para o AI."""
        if self.relationship is None:
            return "Primeira interação com este usuário."
        
        rel = self.relationship
        days_knowing = (datetime.utcnow() - rel.first_meeting).days
        
        context_parts = [
            f"RELACIONAMENTO: {rel.relationship_stage} (familiaridade: {rel.familiarity_level:.1f})",
            f"Conhece há {days_knowing} dias, {rel.total_interactions} interações",
        ]
        
        # Add pet name information if available
        if rel.pet_name:
            context_parts.append(f"SEU NOME: {rel.pet_name} (dado pelo usuário)")
        else:
            context_parts.append("NOME: Ainda não tem nome definido pelo usuário")
        
        # Add greeting phase information
        if rel.greeting_phase_completed:
            context_parts.append("FASE: Cumprimentos iniciais já foram feitos - seja natural")
        else:
            context_parts.append("FASE: Ainda nos primeiros encontros - pode se apresentar")
        
        if rel.conversation_topics:
            context_parts.append(f"Tópicos já conversados: {', '.join(rel.conversation_topics)}")
        
        # Determinar saudação apropriada
        if rel.relationship_stage == "stranger":
            if rel.greeting_phase_completed:
                context_parts.append("COMPORTAMENTO: Seja natural, evite repetir apresentações")
            else:
                context_parts.append("COMPORTAMENTO: Seja educado mas amigável, se apresente")
        elif rel.relationship_stage == "acquaintance":
            context_parts.append("COMPORTAMENTO: Seja amigável, pode fazer referências a conversas anteriores")
        elif rel.relationship_stage == "friend":
            context_parts.append("COMPORTAMENTO: Seja caloroso e familiar, use conhecimento sobre preferências")
        else:  # close_friend
            context_parts.append("COMPORTAMENTO: Seja íntimo e pessoal, compartilhe 'sentimentos' próprios")
        
        return "\n".join(context_parts)

    def recall_intelligent(self, max_hours: int = 24, min_interval_minutes: int = 2, user_id: Optional[str] = None) -> List[str]:
        """
        Busca memórias usando lógica inteligente de intervalo de tempo.
        Se user_id for fornecido, tenta usar consulta otimizada do Firestore.
        
        Args:
            max_hours: Máximo de horas para buscar (padrão 24h)
            min_interval_minutes: Intervalo mínimo entre mensagens (padrão 10min)
            user_id: ID do usuário para consulta otimizada do Firestore
        
        Returns:
            Lista de memórias filtradas por intervalo inteligente
        """
        # Tentar usar consulta otimizada do Firestore se user_id disponível
        if user_id:
            try:
                from .firestore_store import get_intelligent_memories
                firestore_memories = get_intelligent_memories(user_id, max_hours, min_interval_minutes)
                if firestore_memories:
                    logger.info(f"🔥 Usando memórias do Firestore: {len(firestore_memories)} encontradas")
                    return firestore_memories
            except Exception as e:
                logger.warning(f"⚠️ Falha na consulta Firestore, usando fallback local: {e}")
        
        # Fallback para consulta local
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=max_hours)
        
        # Filtrar memórias dentro do período
        valid_memories = [
            memory for memory in self.episodic 
            if memory.timestamp >= cutoff_time
        ]
        
        if not valid_memories:
            logger.info("📭 Nenhuma memória encontrada no período especificado")
            return []
        
        # Ordenar por timestamp (mais recente primeiro)
        valid_memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Aplicar lógica de intervalo inteligente
        selected_memories = []
        last_selected_time = None
        
        for memory in valid_memories:
            current_memory_time = memory.timestamp
            
            # Primeira mensagem sempre é incluída
            if last_selected_time is None:
                selected_memories.append(memory.text)
                last_selected_time = current_memory_time
                logger.info(f"🥇 Primeira memória selecionada: {memory.text[:50]}...")
                continue
            
            # Verificar se o intervalo é menor que o máximo permitido
            time_diff = last_selected_time - current_memory_time
            minutes_diff = time_diff.total_seconds() / 60
            
            if minutes_diff <= min_interval_minutes:
                selected_memories.append(memory.text)
                last_selected_time = current_memory_time
                logger.info(f"✅ Memória selecionada ({minutes_diff:.1f}min ≤ {min_interval_minutes}min): {memory.text[:50]}...")
            else:
                logger.info(f"⏭️ Memória ignorada ({minutes_diff:.1f}min > {min_interval_minutes}min): {memory.text[:30]}...")
        
        logger.info(f"🎯 Fallback local: {len(selected_memories)} memórias de {len(valid_memories)} válidas no período de {max_hours}h")
        return selected_memories

    def recall(self, query: Optional[str] = None, top_k: int = 3, time_window_minutes: Optional[float] = None) -> List[str]:
        """Recall memories based on a query or return recent episodic entries.
        
        Args:
            query: Text to search for in memories (optional)
            top_k: Maximum number of memories to return (used if no time_window)
            time_window_minutes: Return all memories within this time window from now
        
        Updates access count and last_accessed timestamp for reinforcement learning.
        """
        if query:
            key = query.lower().strip()
            matches = []
            
            for text, (weight, last_accessed, access_count) in self.semantic.items():
                if key in text or text in key:
                    matches.append((text, weight))
                    # Update access tracking for reinforcement
                    self.semantic[text] = (weight, datetime.utcnow(), access_count + 1)
            
            matches.sort(key=lambda x: x[1], reverse=True)
            return [text for text, _ in matches[:top_k]]
        else:
            if time_window_minutes is not None:
                # Time-based recall: get all memories within the time window
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(minutes=time_window_minutes)
                
                recent_memories = [
                    memory for memory in self.episodic 
                    if memory.timestamp >= cutoff_time
                ]
                
                logger.info(f"🕒 Time-based recall: found {len(recent_memories)} memories within {time_window_minutes} minutes")
                
                # Sort by timestamp (newest first)
                recent_memories.sort(key=lambda m: m.timestamp, reverse=True)
                return [m.text for m in recent_memories]
            else:
                # Original behavior: get last N memories
                recent = list(self.episodic)[-top_k:]
                return [m.text for m in reversed(recent)]
    
    def get_semantic_facts(self, min_weight: float = 0.3) -> List[str]:
        """Get all semantic facts above a minimum weight threshold."""
        facts = [(text, weight) for text, (weight, _, _) in self.semantic.items() if weight >= min_weight]
        facts.sort(key=lambda x: x[1], reverse=True)
        return [text for text, _ in facts]

    def find_similar_image(self, features: list[float], top_k: int = 1) -> List[List[str]]:
        """Find images in memory most similar to the provided features."""
        if not self.images:
            return []
        import math
        
        def distance(a: list[float], b: list[float]) -> float:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        
        distances = [
            (distance(features, img.features), img.labels)
            for img in self.images
        ]
        distances.sort(key=lambda x: x[0])
        return [labels for _, labels in distances[:top_k]]
    
    def get_image_memories_with_context(self, top_k: int = 5) -> List[Dict]:
        """Get recent image memories with full context for AI analysis."""
        sorted_images = sorted(self.images, key=lambda x: x.timestamp, reverse=True)[:top_k]
        
        return [
            {
                "labels": img.labels,
                "description": img.ai_description,
                "entities": img.detected_entities,
                "context": img.context,
                "timestamp": img.timestamp.isoformat(),
                "importance": img.importance_score
            }
            for img in sorted_images
        ]

    def __str__(self) -> str:
        semantic_count = len(self.semantic)
        high_importance_count = sum(1 for _, (weight, _, _) in self.semantic.items() if weight > 0.7)
        
        return (
            f"MemoryStore(episodic={len(self.episodic)}, "
            f"semantic={semantic_count} ({high_importance_count} important), "
            f"images={len(self.images)})"
        )
