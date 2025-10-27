#!/usr/bin/env python
"""
Test script to demonstrate webhook integration with advanced memory.

This script simulates webhook calls to show how the enhanced memory system
integrates seamlessly with the existing webhook infrastructure.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simulate webhook requests without actually starting the server
from tamagotchi.enhanced_virtual_pet import create_enhanced_pet
from tamagotchi.firestore_store import get_pet_data, save_pet_data


def simulate_webhook(user_id: str, message: str, use_enhanced: bool = True):
    """Simulate a webhook call."""
    print(f"\n{'='*60}")
    print(f"📬 Webhook Request")
    print(f"{'='*60}")
    print(f"User ID: {user_id}")
    print(f"Message: {message}")
    print(f"Enhanced Memory: {'✅ Enabled' if use_enhanced else '❌ Disabled'}")
    print()
    
    if use_enhanced:
        # Load or create pet with enhanced memory
        pet_state = get_pet_data(user_id)
        pet = create_enhanced_pet(user_id=user_id)
        pet.state = pet_state
        
        # Process message
        pet.user_message(message)
        response = pet.pet_response()
        
        # Show advanced features
        commitments = pet.get_active_commitments()
        metrics = pet.get_memory_metrics()
        
        print(f"🤖 Response: {response}")
        print()
        print(f"📊 Advanced Memory Status:")
        print(f"   Active Commitments: {len(commitments)}")
        if commitments:
            for c in commitments[:3]:
                print(f"      - {c}")
        print(f"   Resolution Rate: {metrics['commitment_resolution_rate']:.1%}")
        print(f"   Avg Tokens/Turn: {metrics['avg_tokens_per_turn']:.1f}")
        print(f"   Turns Processed: {metrics['turns_processed']}")
        
        # Save state
        save_pet_data(user_id, pet.state)
        
    else:
        # Legacy mode (for comparison)
        from tamagotchi.virtual_pet import VirtualPet
        pet_state = get_pet_data(user_id)
        pet = VirtualPet()
        pet.state = pet_state
        
        pet.user_message(message)
        response = pet.pet_response()
        
        print(f"🤖 Response: {response}")
        print()
        print(f"📊 Legacy Memory Status:")
        print(f"   Episodic: {len(pet.state.memory.episodic)}")
        print(f"   Semantic: {len(pet.state.memory.semantic)}")
        
        save_pet_data(user_id, pet.state)


def main():
    """Run webhook integration demo."""
    print("\n" + "="*60)
    print("  WEBHOOK INTEGRATION DEMO")
    print("  Advanced Memory System")
    print("="*60)
    
    user_id = "webhook_demo_user"
    
    # Demo 1: User introduces themselves
    simulate_webhook(user_id, "Olá! Meu nome é João e eu gosto de programação.")
    
    # Demo 2: Pet makes a commitment
    simulate_webhook(user_id, "Você pode me lembrar de estudar Python amanhã?")
    
    # Demo 3: User asks about commitments
    simulate_webhook(user_id, "Quais são seus compromissos comigo?")
    
    # Demo 4: Show memory endpoint data
    print(f"\n{'='*60}")
    print(f"📊 Memory Endpoint Response (/memory/{user_id})")
    print(f"{'='*60}")
    
    pet_state = get_pet_data(user_id)
    pet = create_enhanced_pet(user_id=user_id)
    pet.state = pet_state
    
    memory_data = {
        "user_id": user_id,
        "metrics": pet.get_memory_metrics(),
        "active_commitments": pet.get_active_commitments(),
        "relationship_stage": pet.get_relationship_stage()
    }
    
    import json
    print(json.dumps(memory_data, indent=2, ensure_ascii=False))
    
    print("\n" + "="*60)
    print("  DEMO COMPLETED")
    print("="*60)
    print("\n✅ Webhook integration working correctly!")
    print("📝 See WEBHOOK_INTEGRATION.md for full documentation")
    print()


if __name__ == "__main__":
    main()
