#!/usr/bin/env python
"""
Demo script for Advanced Memory System.

This script demonstrates the key features of the advanced memory system:
- Event segmentation
- Commitment tracking
- User correction detection
- Hierarchical consolidation
- Metrics tracking
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagotchi.advanced_memory_manager import AdvancedMemoryManager
from tamagotchi.memory_integration import format_context_for_prompt
from datetime import datetime


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_commitment_tracking():
    """Demonstrate commitment detection and tracking."""
    print_section("1. COMMITMENT TRACKING")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    # Conversation with commitment
    print("Usuário: Você pode me lembrar de comprar leite amanhã?")
    result = manager.process_turn(
        user_message="Você pode me lembrar de comprar leite amanhã?",
        pet_response="Claro! Vou te lembrar amanhã de comprar leite."
    )
    print(f"Pet: Claro! Vou te lembrar amanhã de comprar leite.")
    print(f"\n✅ Commitment detected: {result['commitment_detected']}")
    
    # Show active commitments
    commitments = [c.desc for c in manager.commitments_cache if c.status == "active"]
    print(f"📋 Active commitments: {commitments}")
    
    # Show reactivation schedule
    if manager.commitments_cache:
        commitment = manager.commitments_cache[0]
        print(f"⏰ Reactivation schedule: {[d.strftime('%Y-%m-%d') for d in commitment.reactivation_schedule]}")


def demo_user_corrections():
    """Demonstrate user correction detection."""
    print_section("2. USER CORRECTION DETECTION")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    # Initial conversation
    print("Usuário: Olá!")
    manager.process_turn("Olá!", "Oi! Tudo bem?")
    print("Pet: Oi! Tudo bem?")
    
    # User correction
    print("\nUsuário: Na verdade, meu nome é Maria.")
    result = manager.process_turn(
        user_message="Na verdade, meu nome é Maria.",
        pet_response="Ah, prazer em te conhecer, Maria!"
    )
    print("Pet: Ah, prazer em te conhecer, Maria!")
    print(f"\n✅ Correction detected: {result['correction_detected']}")
    
    # Show stored facts
    if manager.semantic_cache:
        print(f"📝 Stored facts:")
        for fact in manager.semantic_cache[:3]:
            print(f"   - {fact.triple[0]} {fact.triple[1]} {fact.triple[2]} (confidence: {fact.confidence:.2f})")


def demo_event_segmentation():
    """Demonstrate event segmentation."""
    print_section("3. EVENT SEGMENTATION")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    print("Simulating conversation with 5 turns...")
    conversations = [
        ("Vamos falar sobre música?", "Adoraria! Que tipo de música você gosta?"),
        ("Eu gosto de rock", "Rock é ótimo! Bandas favoritas?"),
        ("Beatles e Pink Floyd", "Clássicos! 'Dark Side of the Moon' é incrível."),
        ("Sim! E você gosta de filmes?", "Amo! Vamos falar de filmes!"),
        ("Qual seu gênero favorito?", "Gosto de ficção científica e aventura.")
    ]
    
    for i, (user_msg, pet_msg) in enumerate(conversations, 1):
        print(f"\nTurn {i}:")
        print(f"  Usuário: {user_msg}")
        print(f"  Pet: {pet_msg}")
        manager.process_turn(user_msg, pet_msg)
    
    # Force consolidation
    print("\n⚙️ Running session consolidation...")
    summary = manager.consolidate_session()
    print(f"✅ Events created: {len(manager.events_cache)}")
    
    # Show events
    if manager.events_cache:
        print(f"\n📦 Event summaries:")
        for event in manager.events_cache:
            print(f"   - {event.title}")
            print(f"     Summary: {event.summary[:100]}...")
            print(f"     Salience: {event.salience:.2f}")


def demo_hybrid_retrieval():
    """Demonstrate hybrid retrieval system."""
    print_section("4. HYBRID RETRIEVAL")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    # Populate with some data
    print("Setting up conversation history...")
    manager.process_turn("Meu nome é João", "Prazer, João!")
    manager.process_turn("Eu gosto de programar", "Interessante! Que linguagens?")
    manager.process_turn("Python e JavaScript", "Ótimas escolhas!")
    manager.process_turn("Pode me lembrar de estudar amanhã?", "Vou te lembrar!")
    
    # Retrieve context
    print("\n🔍 Retrieving context for query: 'lembrar'")
    context = manager.retrieve_context(query="lembrar", max_tokens=1200)
    
    print(f"\n📊 Retrieved context:")
    print(f"   Commitments: {len(context['commitments'])}")
    print(f"   Semantic facts: {len(context['semantic_facts'])}")
    print(f"   Recent events: {len(context['recent_events'])}")
    print(f"   Estimated tokens: {context['estimated_tokens']}")
    
    # Format for prompt
    formatted = format_context_for_prompt(context)
    print(f"\n📝 Formatted context:\n{formatted}")


def demo_salience_scoring():
    """Demonstrate salience scoring."""
    print_section("5. SALIENCE SCORING")
    
    from tamagotchi.advanced_memory import SalienceScorer
    
    scorer = SalienceScorer()
    
    print("Calculating salience for different scenarios:\n")
    
    # Recent event
    recent_score = scorer.calculate_salience(
        timestamp=datetime.utcnow(),
        repetition_count=1,
        is_novel=False,
        emotion_intensity=0.5,
        is_explicit=False
    )
    print(f"1. Recent casual event: {recent_score:.3f}")
    
    # Explicit correction
    explicit_score = scorer.calculate_salience(
        timestamp=datetime.utcnow(),
        repetition_count=1,
        is_novel=False,
        emotion_intensity=0.0,
        is_explicit=True
    )
    print(f"2. User correction (explicit): {explicit_score:.3f}")
    
    # Novel information
    novel_score = scorer.calculate_salience(
        timestamp=datetime.utcnow(),
        repetition_count=1,
        is_novel=True,
        emotion_intensity=0.3,
        is_explicit=False
    )
    print(f"3. Novel information: {novel_score:.3f}")
    
    # Repeated with emotion
    repeated_score = scorer.calculate_salience(
        timestamp=datetime.utcnow(),
        repetition_count=5,
        is_novel=False,
        emotion_intensity=0.8,
        is_explicit=False
    )
    print(f"4. Repeated emotional event: {repeated_score:.3f}")
    
    print(f"\n💡 Higher scores = higher priority in memory")


def demo_metrics():
    """Demonstrate metrics tracking."""
    print_section("6. METRICS TRACKING")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    print("Simulating conversation with commitments...\n")
    
    # Create commitments
    manager.process_turn("Ajude-me com isso", "Vou te ajudar!")
    manager.process_turn("Me lembre depois", "Vou te lembrar!")
    
    # Mark one as done
    if manager.commitments_cache:
        manager.mark_commitment_done(manager.commitments_cache[0].commitment_id)
    
    # Get metrics
    metrics = manager.get_metrics()
    
    print("📈 Current Metrics:")
    print(f"   Commitment Resolution Rate: {metrics['commitment_resolution_rate']:.2%}")
    print(f"   Turns Processed: {metrics['turns_processed']}")
    print(f"   Commitments Made: {metrics['commitments_made']}")
    print(f"   Commitments Fulfilled: {metrics['commitments_fulfilled']}")
    print(f"   Open Loops Active: {metrics['open_loops_active']}")
    print(f"   Avg Tokens/Turn: {metrics['avg_tokens_per_turn']:.1f}")


def demo_daily_digest():
    """Demonstrate daily digest generation."""
    print_section("7. DAILY DIGEST")
    
    manager = AdvancedMemoryManager(user_id="demo_user", firestore_client=None)
    
    print("Building conversation history...\n")
    
    # Populate with conversation
    conversations = [
        ("Meu nome é Ana", "Prazer, Ana!"),
        ("Gosto de dançar", "Que legal! Que estilos?"),
        ("Ballet e jazz", "Maravilhoso!"),
        ("Me ajude a treinar?", "Vou te ajudar a criar um plano!")
    ]
    
    for user_msg, pet_msg in conversations:
        manager.process_turn(user_msg, pet_msg)
    
    # Generate digest
    manager.consolidate_session()
    digest = manager.generate_daily_digest()
    
    print("📅 Daily Digest:")
    print(f"\n   Card: {digest.daily_card}")
    print(f"\n   New Facts: {digest.new_facts}")
    print(f"\n   Active Commitments: {digest.active_commitments}")
    print(f"\n   Open Topics: {digest.open_topics}")
    print(f"\n   Next Step: {digest.next_step}")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("  ADVANCED MEMORY SYSTEM - DEMONSTRATION")
    print("="*60)
    
    demos = [
        demo_commitment_tracking,
        demo_user_corrections,
        demo_event_segmentation,
        demo_hybrid_retrieval,
        demo_salience_scoring,
        demo_metrics,
        demo_daily_digest
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ Error in {demo.__name__}: {e}")
    
    print("\n" + "="*60)
    print("  DEMO COMPLETED")
    print("="*60)
    print("\nFor more information, see ADVANCED_MEMORY.md\n")


if __name__ == "__main__":
    main()
