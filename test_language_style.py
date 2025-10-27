"""
Tests for the language style analyzer and adaptive communication.

Run from the parent directory:
    cd /path/to/parent
    python -m tamagotchi.test_language_style
"""

from tamagotchi.language_style_analyzer import CommunicationStyle, generate_adaptive_prompt
from tamagotchi.virtual_pet import VirtualPet
from tamagotchi.firestore_store import pet_state_to_dict, dict_to_pet_state
import sys


def test_style_detection_informal():
    """Test that informal messages are correctly detected."""
    style = CommunicationStyle()
    
    # Send some informal messages
    style.update_from_message("E aí mano, blz?")
    style.update_from_message("Cara, mt legal isso 🎮")
    style.update_from_message("Pô, não sei kkk")
    
    print("Test: Informal style detection")
    print(f"  Style description: {style.get_style_description()}")
    assert style.formality < 0.5, "Should detect informal style"
    assert style.slang_usage > 0.3, "Should detect high slang usage"
    print("  ✅ Passed")


def test_style_detection_formal():
    """Test that formal messages are correctly detected."""
    style = CommunicationStyle()
    
    # Send some formal messages
    style.update_from_message("Olá, tudo bem com você?")
    style.update_from_message("Gostaria de saber mais informações.")
    style.update_from_message("Obrigado pela atenção.")
    
    print("\nTest: Formal style detection")
    print(f"  Style description: {style.get_style_description()}")
    assert style.formality > 0.5, "Should detect formal style"
    assert style.slang_usage < 0.2, "Should detect low slang usage"
    print("  ✅ Passed")


def test_emoji_detection():
    """Test that emoji usage is correctly detected."""
    style = CommunicationStyle()
    
    # Send messages with emojis
    style.update_from_message("Oi! 😊")
    style.update_from_message("Que legal! 🎉🎊")
    style.update_from_message("Adorei! ❤️✨")
    
    print("\nTest: Emoji detection")
    print(f"  Emoji usage: {style.emoji_usage:.2f}")
    assert style.emoji_usage > 0.2, "Should detect emoji usage"
    print("  ✅ Passed")


def test_adaptive_prompt_generation():
    """Test that adaptive prompts are generated correctly."""
    style = CommunicationStyle(
        formality=0.2,
        emoji_usage=0.7,
        slang_usage=0.8,
        expressiveness=0.9
    )
    
    base_prompt = "Você é um pet virtual."
    adaptive_prompt = generate_adaptive_prompt(base_prompt, style)
    
    print("\nTest: Adaptive prompt generation")
    assert "informal" in adaptive_prompt.lower(), "Should include informality instruction"
    assert "emoji" in adaptive_prompt.lower(), "Should include emoji instruction"
    assert "gíria" in adaptive_prompt.lower(), "Should include slang instruction"
    print("  ✅ Passed")


def test_style_persistence():
    """Test that communication style is persisted correctly."""
    # Create a pet and train its style
    pet = VirtualPet()
    pet.user_message("E aí mano, blz?")
    pet.user_message("Cara, eu curto mt música 🎵")
    
    # Get style before serialization
    style_before = pet.state.memory.communication_style
    formality_before = style_before.formality
    slang_before = style_before.slang_usage
    
    # Serialize and deserialize
    data = pet_state_to_dict(pet.state)
    restored_state = dict_to_pet_state(data)
    
    # Check if style was restored
    style_after = restored_state.memory.communication_style
    
    print("\nTest: Style persistence")
    assert style_after is not None, "Style should be restored"
    assert abs(style_after.formality - formality_before) < 0.01, "Formality should match"
    assert abs(style_after.slang_usage - slang_before) < 0.01, "Slang usage should match"
    print("  ✅ Passed")


def test_pet_learns_user_style():
    """Test that the pet learns and adapts to user's communication style."""
    pet = VirtualPet()
    
    # Send informal messages
    messages = [
        "E aí mano, blz?",
        "Cara, mt legal isso",
        "Pô, da hora demais",
    ]
    
    for msg in messages:
        pet.user_message(msg)
    
    style = pet.state.memory.communication_style
    
    print("\nTest: Pet learns user style")
    print(f"  Learned style: {style.get_style_description()}")
    assert style.formality < 0.5, "Should learn informal style"
    assert style.slang_usage > 0.3, "Should detect slang"
    assert style.message_count == len(messages), f"Should have processed {len(messages)} messages"
    print("  ✅ Passed")


if __name__ == "__main__":
    print("Running Language Style Analyzer Tests\n" + "="*50)
    
    try:
        test_style_detection_informal()
        test_style_detection_formal()
        test_emoji_detection()
        test_adaptive_prompt_generation()
        test_style_persistence()
        test_pet_learns_user_style()
        
        print("\n" + "="*50)
        print("✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
