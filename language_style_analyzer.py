"""
Language style analyzer for adaptive communication.

This module analyzes how the user communicates and helps the pet adapt its
responses to match the user's style, making conversations more natural and
less robotic. It detects:
- Formality level (formal vs informal)
- Use of emojis and emoticons
- Slang and colloquial expressions
- Sentence length and complexity
- Punctuation patterns
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CommunicationStyle:
    """Represents a user's communication style."""
    
    # Formality: 0.0 = very informal, 1.0 = very formal
    formality: float = 0.5
    
    # Emoji usage: 0.0 = no emojis, 1.0 = many emojis
    emoji_usage: float = 0.0
    
    # Slang usage: 0.0 = no slang, 1.0 = lots of slang
    slang_usage: float = 0.0
    
    # Expressiveness: 0.0 = monotone, 1.0 = very expressive (exclamations, questions)
    expressiveness: float = 0.5
    
    # Average message length (words)
    avg_message_length: float = 5.0
    
    # Question tendency: 0.0 = rarely asks, 1.0 = asks often
    question_tendency: float = 0.0
    
    # Message samples for learning
    message_count: int = 0
    
    def update_from_message(self, message: str) -> None:
        """Update style metrics based on a new message."""
        if not message or not message.strip():
            return
        
        # Increment message count
        self.message_count += 1
        learning_rate = min(0.3, 1.0 / self.message_count)  # Adaptive learning rate
        
        # Analyze formality
        formality = self._analyze_formality(message)
        self.formality = self.formality * (1 - learning_rate) + formality * learning_rate
        
        # Analyze emoji usage
        emoji_score = self._analyze_emoji_usage(message)
        self.emoji_usage = self.emoji_usage * (1 - learning_rate) + emoji_score * learning_rate
        
        # Analyze slang usage
        slang_score = self._analyze_slang(message)
        self.slang_usage = self.slang_usage * (1 - learning_rate) + slang_score * learning_rate
        
        # Analyze expressiveness
        expr_score = self._analyze_expressiveness(message)
        self.expressiveness = self.expressiveness * (1 - learning_rate) + expr_score * learning_rate
        
        # Update average message length
        words = len(message.split())
        self.avg_message_length = self.avg_message_length * (1 - learning_rate) + words * learning_rate
        
        # Update question tendency
        is_question = 1.0 if message.strip().endswith('?') else 0.0
        self.question_tendency = self.question_tendency * (1 - learning_rate) + is_question * learning_rate
        
        logger.info(f"📊 Updated communication style: formality={self.formality:.2f}, emoji={self.emoji_usage:.2f}, slang={self.slang_usage:.2f}")
    
    def _analyze_formality(self, message: str) -> float:
        """Analyze formality level of a message."""
        lower = message.lower()
        formality_score = 0.5  # Start neutral
        
        # Formal indicators
        formal_words = ["senhor", "senhora", "prezado", "gostaria", "poderia", "desculpe"]
        if any(word in lower for word in formal_words):
            formality_score += 0.3
        
        # Informal indicators
        informal_words = ["oi", "e aí", "beleza", "cara", "mano", "vlw", "valeu", "falou", "blz"]
        if any(word in lower for word in informal_words):
            formality_score -= 0.3
        
        # Proper capitalization suggests formality
        if message and message[0].isupper() and not message.isupper():
            formality_score += 0.1
        
        # All lowercase suggests informality
        if message.islower():
            formality_score -= 0.2
        
        return max(0.0, min(1.0, formality_score))
    
    def _analyze_emoji_usage(self, message: str) -> float:
        """Analyze emoji and emoticon usage."""
        # Count emojis (Unicode emoji ranges)
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+', message))
        
        # Count text emoticons
        emoticon_patterns = [':)', ':(', ':D', ';)', ':P', '^^', '^_^', 'XD', ':3', '<3']
        emoticon_count = sum(1 for pattern in emoticon_patterns if pattern in message)
        
        total = emoji_count + emoticon_count
        words = len(message.split())
        
        if words == 0:
            return 0.0
        
        # Normalize to 0-1 (assume 1 emoji per 3 words is max)
        return min(1.0, (total / max(1, words)) * 3)
    
    def _analyze_slang(self, message: str) -> float:
        """Analyze use of slang and colloquial expressions."""
        lower = message.lower()
        
        # Brazilian Portuguese slang and colloquial expressions
        slang_terms = [
            "pô", "né", "tá", "pra", "vc", "tb", "tbm", "tmj", "blz", "vlw",
            "mano", "cara", "vei", "kkkk", "rsrs", "haha", "kk", "kkkkk",
            "mo", "mt", "mto", "d+", "sla", "slk", "pfv", "pf", "fds",
            "msg", "cmg", "ctg", "dps", "hj", "td bem", "sussa", "massa",
            "da hora", "show", "top", "demais", "firmeza", "tranquilo"
        ]
        
        # Abbreviated words
        abbreviated = re.findall(r'\b[a-z]{1,3}\b', lower)
        
        # Count slang occurrences
        slang_count = sum(1 for term in slang_terms if term in lower)
        
        # Check for internet abbreviations
        internet_slang = len([a for a in abbreviated if a in slang_terms])
        
        words = len(message.split())
        if words == 0:
            return 0.0
        
        total_slang = slang_count + internet_slang
        
        # Normalize (assume 1 slang per 5 words is high)
        return min(1.0, (total_slang / max(1, words)) * 5)
    
    def _analyze_expressiveness(self, message: str) -> float:
        """Analyze expressiveness (exclamations, questions, emphasis)."""
        score = 0.5  # Neutral
        
        # Count exclamation marks
        exclamations = message.count('!')
        if exclamations > 0:
            score += min(0.3, exclamations * 0.1)
        
        # Count questions
        questions = message.count('?')
        if questions > 0:
            score += min(0.2, questions * 0.1)
        
        # Check for ALL CAPS (shows excitement/emotion)
        if message.isupper() and len(message) > 3:
            score += 0.2
        
        # Check for repeated letters (e.g., "muuuito", "nããão")
        if re.search(r'(.)\1{2,}', message):
            score += 0.15
        
        # Check for laughter
        if re.search(r'(kkkk|haha|rsrs|kkk|kk|hehe)', message.lower()):
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def get_style_description(self) -> str:
        """Get a natural language description of the communication style."""
        descriptions = []
        
        if self.formality < 0.3:
            descriptions.append("muito informal e descontraído")
        elif self.formality > 0.7:
            descriptions.append("formal e educado")
        else:
            descriptions.append("casual")
        
        if self.emoji_usage > 0.3:
            descriptions.append("usa bastante emoji")
        
        if self.slang_usage > 0.4:
            descriptions.append("usa muitas gírias e abreviações")
        elif self.slang_usage > 0.2:
            descriptions.append("usa algumas gírias")
        
        if self.expressiveness > 0.7:
            descriptions.append("muito expressivo e animado")
        elif self.expressiveness < 0.3:
            descriptions.append("mais discreto")
        
        if self.question_tendency > 0.5:
            descriptions.append("curioso, faz muitas perguntas")
        
        if self.avg_message_length < 3:
            descriptions.append("mensagens curtas")
        elif self.avg_message_length > 10:
            descriptions.append("mensagens longas e detalhadas")
        
        return ", ".join(descriptions) if descriptions else "equilibrado"
    
    def to_dict(self) -> Dict[str, float]:
        """Export style as dictionary."""
        return {
            'formality': self.formality,
            'emoji_usage': self.emoji_usage,
            'slang_usage': self.slang_usage,
            'expressiveness': self.expressiveness,
            'avg_message_length': self.avg_message_length,
            'question_tendency': self.question_tendency,
            'message_count': self.message_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'CommunicationStyle':
        """Create style from dictionary."""
        return cls(
            formality=data.get('formality', 0.5),
            emoji_usage=data.get('emoji_usage', 0.0),
            slang_usage=data.get('slang_usage', 0.0),
            expressiveness=data.get('expressiveness', 0.5),
            avg_message_length=data.get('avg_message_length', 5.0),
            question_tendency=data.get('question_tendency', 0.0),
            message_count=int(data.get('message_count', 0))
        )


def generate_adaptive_prompt(
    base_prompt: str,
    user_style: CommunicationStyle,
    context: Optional[str] = None
) -> str:
    """
    Generate a prompt that instructs the AI to match the user's communication style.
    
    Args:
        base_prompt: The base instruction/prompt
        user_style: The user's detected communication style
        context: Optional additional context
        
    Returns:
        Enhanced prompt with style adaptation instructions
    """
    # Build style adaptation instructions
    style_instructions = ["IMPORTANTE - ADAPTE SEU ESTILO DE COMUNICAÇÃO:"]
    
    # Formality adaptation
    if user_style.formality < 0.3:
        style_instructions.append("- Seja MUITO informal e descontraído, use gírias brasileiras naturalmente")
        style_instructions.append("- Use 'vc', 'pra', 'tá', 'né' e outras contrações")
    elif user_style.formality > 0.7:
        style_instructions.append("- Mantenha um tom mais formal e educado")
        style_instructions.append("- Use linguagem completa e correta")
    else:
        style_instructions.append("- Use uma linguagem casual e natural do dia a dia")
    
    # Emoji adaptation
    if user_style.emoji_usage > 0.3:
        style_instructions.append(f"- O usuário usa muitos emojis! Use emojis com frequência nas respostas (1-2 por mensagem)")
    elif user_style.emoji_usage > 0.1:
        style_instructions.append("- Use emojis ocasionalmente para dar vida às respostas")
    else:
        style_instructions.append("- Evite ou use emojis com moderação")
    
    # Slang adaptation
    if user_style.slang_usage > 0.4:
        style_instructions.append("- Use MUITAS gírias e linguagem da internet (tipo: 'pô', 'massa', 'da hora', 'top', 'demais')")
        style_instructions.append("- Use abreviações naturalmente: 'vc', 'tb', 'mt', 'pra', 'tá'")
    elif user_style.slang_usage > 0.2:
        style_instructions.append("- Use algumas gírias brasileiras para soar mais natural")
    
    # Expressiveness adaptation
    if user_style.expressiveness > 0.7:
        style_instructions.append("- Seja MUITO expressivo! Use pontos de exclamação, repetição de letras (tipo 'muuuito')")
        style_instructions.append("- Mostre empolgação e energia nas respostas")
    elif user_style.expressiveness < 0.3:
        style_instructions.append("- Seja mais contido e discreto nas respostas")
    
    # Message length adaptation
    if user_style.avg_message_length < 4:
        style_instructions.append("- Mensagens CURTAS! 1-2 frases no máximo, direto ao ponto")
    elif user_style.avg_message_length > 10:
        style_instructions.append("- Pode elaborar mais nas respostas, o usuário gosta de conversar")
    else:
        style_instructions.append("- Mensagens concisas de 1-2 frases")
    
    # Add user style description
    style_desc = user_style.get_style_description()
    if style_desc:
        style_instructions.append(f"\nO USUÁRIO SE COMUNICA ASSIM: {style_desc}")
        style_instructions.append("COPIE O ESTILO DELE para criar conexão e soar mais natural!")
    
    # Combine everything
    parts = [base_prompt]
    parts.append("\n" + "\n".join(style_instructions))
    
    if context:
        parts.append(f"\nCONTEXTO ADICIONAL:\n{context}")
    
    return "\n".join(parts)


def get_style_modifiers_for_fallback(user_style: CommunicationStyle) -> Dict[str, any]:
    """
    Get modifiers for fallback response generation.
    
    Returns parameters to adjust fallback responses to match user style.
    """
    return {
        'use_emojis': user_style.emoji_usage > 0.2,
        'emoji_frequency': user_style.emoji_usage,
        'use_slang': user_style.slang_usage > 0.2,
        'slang_level': user_style.slang_usage,
        'formality': user_style.formality,
        'expressiveness': user_style.expressiveness,
        'max_words': int(user_style.avg_message_length * 1.5) if user_style.avg_message_length < 10 else 30
    }
