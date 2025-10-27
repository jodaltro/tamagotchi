#!/usr/bin/env python3
"""
Demo: Adaptive Communication System
Shows how the pet learns and adapts to different communication styles.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagotchi.virtual_pet import VirtualPet


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def demo_informal_user():
    """Demonstrate how the pet adapts to an informal user."""
    print_header("DEMO 1: Usuário Informal (Gírias e Emojis)")
    
    pet = VirtualPet()
    
    conversations = [
        ("E aí mano, blz?", "Primeiro contato - informal"),
        ("Cara, eu curto mt música 🎵 e jogar tbm 🎮", "Compartilhando hobbies com gírias"),
        ("Pô, da hora demais! vc curte o que?", "Pergunta informal"),
    ]
    
    for user_msg, description in conversations:
        print(f"\n[{description}]")
        print(f"👤 Usuário: {user_msg}")
        pet.user_message(user_msg)
        response = pet.pet_response()
        print(f"🐾 Pet: {response}")
    
    # Show learned style
    style = pet.state.memory.communication_style
    print(f"\n📊 Estilo aprendido: {style.get_style_description()}")
    print(f"   • Formalidade: {style.formality:.2f} (0=informal, 1=formal)")
    print(f"   • Uso de gírias: {style.slang_usage:.2f}")
    print(f"   • Uso de emojis: {style.emoji_usage:.2f}")
    print(f"   • Expressividade: {style.expressiveness:.2f}")


def demo_formal_user():
    """Demonstrate how the pet adapts to a formal user."""
    print_header("DEMO 2: Usuário Formal (Educado e Completo)")
    
    pet = VirtualPet()
    
    conversations = [
        ("Olá, tudo bem com você?", "Saudação formal"),
        ("Gostaria de saber mais sobre suas funcionalidades.", "Pergunta formal"),
        ("Obrigado pela informação prestada.", "Agradecimento formal"),
    ]
    
    for user_msg, description in conversations:
        print(f"\n[{description}]")
        print(f"👤 Usuário: {user_msg}")
        pet.user_message(user_msg)
        response = pet.pet_response()
        print(f"🐾 Pet: {response}")
    
    # Show learned style
    style = pet.state.memory.communication_style
    print(f"\n📊 Estilo aprendido: {style.get_style_description()}")
    print(f"   • Formalidade: {style.formality:.2f} (0=informal, 1=formal)")
    print(f"   • Uso de gírias: {style.slang_usage:.2f}")
    print(f"   • Uso de emojis: {style.emoji_usage:.2f}")


def demo_mixed_style():
    """Demonstrate how the pet adapts to evolving communication style."""
    print_header("DEMO 3: Usuário que Muda de Estilo")
    
    pet = VirtualPet()
    
    print("\n📝 Fase 1: Usuário começa formal")
    for user_msg in ["Olá, como vai?", "Tudo bem, obrigado."]:
        print(f"👤 Usuário: {user_msg}")
        pet.user_message(user_msg)
        print(f"🐾 Pet: {pet.pet_response()}")
    
    style = pet.state.memory.communication_style
    print(f"   Formalidade: {style.formality:.2f}")
    
    print("\n📝 Fase 2: Usuário fica mais informal")
    for user_msg in ["E aí, blz?", "Cara, mt legal isso!", "kkkk show demais"]:
        print(f"👤 Usuário: {user_msg}")
        pet.user_message(user_msg)
        print(f"🐾 Pet: {pet.pet_response()}")
    
    style = pet.state.memory.communication_style
    print(f"\n📊 Estilo final: {style.get_style_description()}")
    print(f"   Formalidade: {style.formality:.2f} (diminuiu!)")
    print(f"   Uso de gírias: {style.slang_usage:.2f} (aumentou!)")


def demo_persistence():
    """Demonstrate that style is persisted across sessions."""
    print_header("DEMO 4: Persistência do Estilo Entre Sessões")
    
    from tamagotchi.firestore_store import pet_state_to_dict, dict_to_pet_state
    
    # Session 1: Learn style
    print("\n📝 Sessão 1: Aprendendo o estilo")
    pet1 = VirtualPet()
    for msg in ["E aí mano", "Cara, mt legal", "kkk show"]:
        pet1.user_message(msg)
    
    style1 = pet1.state.memory.communication_style
    print(f"   Estilo aprendido: {style1.get_style_description()}")
    print(f"   Gírias: {style1.slang_usage:.2f}")
    
    # Serialize
    data = pet_state_to_dict(pet1.state)
    print("\n💾 Salvando estado...")
    
    # Session 2: Restore and continue
    print("\n📝 Sessão 2: Restaurando e continuando")
    restored_state = dict_to_pet_state(data)
    pet2 = VirtualPet()
    pet2.state = restored_state
    
    style2 = pet2.state.memory.communication_style
    print(f"   Estilo restaurado: {style2.get_style_description()}")
    print(f"   Gírias: {style2.slang_usage:.2f}")
    
    # Continue conversation
    pet2.user_message("Opa, lembrou de mim?")
    print(f"👤 Usuário: Opa, lembrou de mim?")
    print(f"🐾 Pet: {pet2.pet_response()}")
    print("\n✅ Estilo foi mantido entre sessões!")


def main():
    """Run all demos."""
    print("\n" + "🎭 "*20)
    print("   DEMONSTRAÇÃO: SISTEMA DE COMUNICAÇÃO ADAPTATIVA")
    print("   O pet aprende SEU jeito de falar e se adapta!")
    print("🎭 "*20)
    
    try:
        demo_informal_user()
        input("\n\n▶ Pressione ENTER para continuar para o próximo demo...")
        
        demo_formal_user()
        input("\n\n▶ Pressione ENTER para continuar para o próximo demo...")
        
        demo_mixed_style()
        input("\n\n▶ Pressione ENTER para continuar para o próximo demo...")
        
        demo_persistence()
        
        print_header("CONCLUSÃO")
        print("""
O sistema agora:
✅ Detecta automaticamente seu estilo de comunicação
✅ Adapta respostas para combinar com você
✅ Usa gírias quando você usa gírias
✅ É formal quando você é formal
✅ Lembra do seu estilo entre conversas
✅ É muito menos robótico e mais natural!

Para usar com API do Gemini para respostas ainda melhores:
  export GOOGLE_API_KEY="sua-chave-aqui"
        """)
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrompida. Até logo!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
