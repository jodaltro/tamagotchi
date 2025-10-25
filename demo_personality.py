#!/usr/bin/env python3
"""
Personality Engine Demonstration

This script demonstrates how different personality archetypes behave
differently in the same situations. It creates three pets with different
personalities and shows how they respond to the same prompts.
"""

from tamagotchi.virtual_pet import VirtualPet


def print_separator():
    print("\n" + "=" * 80 + "\n")


def demonstrate_archetype(archetype_name: str, messages: list):
    """Demonstrate a specific personality archetype."""
    print(f"🎭 PERSONALITY: {archetype_name.upper().replace('_', ' ')}")
    print("-" * 80)
    
    # Create pet with specific archetype
    pet = VirtualPet(personality_archetype=archetype_name)
    
    # Show personality description
    desc = pet.state.get_personality_description()
    print(f"Descrição: {desc}\n")
    
    # Process messages and show responses
    for i, message in enumerate(messages, 1):
        pet.user_message(message, delay=5.0)
        response = pet.pet_response()
        print(f"Usuário: {message}")
        print(f"Pet: {response}")
        if i < len(messages):
            print()
    
    print_separator()


def main():
    """Run the personality demonstration."""
    print_separator()
    print("🌟 DEMONSTRAÇÃO DO MOTOR DE PERSONALIDADE")
    print("Comparando 3 personalidades diferentes com as mesmas mensagens")
    print_separator()
    
    # Messages to test with all personalities
    test_messages = [
        "Olá! Como você está?",
        "Vamos aprender algo novo?",
        "Me conte uma história!",
    ]
    
    # Test three different archetypes
    archetypes = [
        "curious_explorer",
        "playful_companion", 
        "calm_philosopher",
    ]
    
    for archetype in archetypes:
        demonstrate_archetype(archetype, test_messages)
    
    # Show personality evolution
    print("🔄 DEMONSTRAÇÃO DE EVOLUÇÃO DE PERSONALIDADE")
    print("-" * 80)
    print("Simulando 50 interações positivas com um pet equilibrado...\n")
    
    pet = VirtualPet(personality_archetype="balanced_friend")
    
    # Show initial personality
    print("Personalidade inicial:")
    initial = pet.state.personality.profile
    print(f"  Agreeableness: {initial.agreeableness:.3f}")
    print(f"  Extraversion: {initial.extraversion:.3f}")
    print(f"  Neuroticism: {initial.neuroticism:.3f}")
    print()
    
    # Simulate many positive interactions
    for i in range(50):
        pet.user_message(f"Muito legal! #{i}", delay=3.0)
        pet.pet_response()
    
    # Show evolved personality
    print("Personalidade após 50 interações positivas:")
    evolved = pet.state.personality.profile
    print(f"  Agreeableness: {evolved.agreeableness:.3f} (mudança: {evolved.agreeableness - initial.agreeableness:+.3f})")
    print(f"  Extraversion: {evolved.extraversion:.3f} (mudança: {evolved.extraversion - initial.extraversion:+.3f})")
    print(f"  Neuroticism: {evolved.neuroticism:.3f} (mudança: {evolved.neuroticism - initial.neuroticism:+.3f})")
    
    print_separator()
    
    # Show all available archetypes
    print("📋 TODOS OS ARQUÉTIPOS DISPONÍVEIS")
    print("-" * 80)
    
    archetype_info = {
        "curious_explorer": "Explorador Curioso - Alta abertura, ama aprender",
        "playful_companion": "Companheiro Brincalhão - Energético e divertido",
        "gentle_caregiver": "Cuidador Gentil - Compassivo e acolhedor",
        "wise_observer": "Observador Sábio - Pensativo e introspectivo",
        "energetic_enthusiast": "Entusiasta Energético - Muito ativo e animado",
        "calm_philosopher": "Filósofo Calmo - Pacífico e reflexivo",
        "artistic_dreamer": "Sonhador Artístico - Criativo e imaginativo",
        "balanced_friend": "Amigo Equilibrado - Personalidade balanceada",
    }
    
    for archetype, description in archetype_info.items():
        print(f"  • {archetype:25} - {description}")
    
    print_separator()
    
    print("✅ Demonstração completa!")
    print("\nPara usar no seu código:")
    print("  pet = VirtualPet(personality_archetype='curious_explorer')")
    print("\nOu para personalidade aleatória única:")
    print("  pet = VirtualPet()  # archetype=None usa personalidade aleatória")
    print()


if __name__ == "__main__":
    main()
