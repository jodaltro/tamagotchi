"""
Test suite for Autobiographical Memory (ABM) system.

This module tests the ABM functionality including:
- ABM item creation and retrieval
- PET-CANON generation and updates
- Echo-Trace pattern extraction
- Self-Consistency Guard contradiction detection
- Integration with VirtualPet and persistence
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagotchi.autobiographical_memory import AutobiographicalMemory, ABMType, ABMItem
from tamagotchi.pet_canon import PetCanon
from tamagotchi.echo_trace import EchoTrace, PatternContext
from tamagotchi.self_consistency_guard import SelfConsistencyGuard
from tamagotchi.memory_store import MemoryStore
from tamagotchi.pet_state import PetState
from tamagotchi.firestore_store import pet_state_to_dict, dict_to_pet_state
from tamagotchi.virtual_pet import VirtualPet


def test_abm_basic():
    """Test basic ABM functionality."""
    print('\n=== Test: ABM Basic Functionality ===')
    
    abm = AutobiographicalMemory()
    assert abm is not None, "ABM should be created"
    
    # Add a claim
    claim = abm.add_claim(
        'Eu posso te ajudar com lembretes',
        ABMType.C_PET,
        'test_event_1',
        importance=0.8
    )
    assert claim.canonical_text == 'Eu posso te ajudar com lembretes'
    assert claim.type == ABMType.C_PET
    
    # Check active items
    active = abm.get_active_items()
    assert len(active) == 1, "Should have 1 active item"
    
    # Test reinforcement
    claim2 = abm.add_claim(
        'Eu posso te ajudar com lembretes',  # Same claim
        ABMType.C_PET,
        'test_event_2',
        importance=0.7
    )
    # Should reinforce existing, not create new
    active = abm.get_active_items()
    assert len(active) == 1, "Should still have 1 active item (reinforced)"
    assert active[0].importance > 0.8, "Importance should increase"
    
    print('✅ ABM basic functionality working')


def test_canon_generation():
    """Test PET-CANON generation."""
    print('\n=== Test: PET-CANON Generation ===')
    
    abm = AutobiographicalMemory()
    canon = PetCanon()
    
    # Add various claims
    abm.add_claim('Sou um pet virtual amigável', ABMType.C_PET, 'e1', importance=0.9)
    abm.add_claim('Eu posso te ajudar com tarefas', ABMType.TOOLS, 'e2', importance=0.8)
    abm.add_claim('Eu não posso acessar a internet', ABMType.C_PET, 'e3', importance=0.9)
    abm.add_claim('Nunca vou compartilhar suas informações', ABMType.POLICY, 'e4', importance=0.95)
    
    # Update canon
    updated = canon.update_from_abm(abm)
    assert updated, "Canon should be updated"
    
    # Check canon text
    canon_text = canon.to_prompt_text()
    assert len(canon_text) > 0, "Canon text should not be empty"
    assert 'pet virtual amigável' in canon_text.lower(), "Canon should include role"
    
    print(f'✅ Canon generated: {canon_text[:100]}...')


def test_echo_trace():
    """Test Echo-Trace pattern extraction."""
    print('\n=== Test: Echo-Trace Pattern Extraction ===')
    
    echo = EchoTrace()
    
    # Add patterns
    pattern1 = echo.add_pattern(
        'Olá! Como você está hoje?',
        PatternContext.GREETING,
        success_signal=0.8
    )
    assert pattern1 is not None
    
    pattern2 = echo.add_pattern(
        'Entendo como você se sente',
        PatternContext.EMPATHY,
        success_signal=0.7
    )
    assert pattern2 is not None
    
    # Get patterns by context
    greetings = echo.get_patterns_for_context(PatternContext.GREETING)
    assert len(greetings) == 1, "Should have 1 greeting pattern"
    
    # Extract from response
    response = "Olá! Que legal isso! Como você está?"
    extracted = echo.extract_from_response(response, user_reaction_positive=True)
    assert len(extracted) > 0, "Should extract patterns from response"
    
    print(f'✅ Echo-Trace working, extracted {len(extracted)} patterns')


def test_consistency_guard():
    """Test Self-Consistency Guard."""
    print('\n=== Test: Self-Consistency Guard ===')
    
    abm = AutobiographicalMemory()
    canon = PetCanon()
    
    # Add capability claim
    abm.add_claim('Eu posso te ajudar com lembretes', ABMType.C_PET, 'e1', importance=0.9)
    abm.add_claim('Eu não posso acessar a internet', ABMType.C_PET, 'e2', importance=0.9)
    canon.update_from_abm(abm)
    
    scg = SelfConsistencyGuard()
    
    # Test consistent response
    consistent_draft = 'Eu vou te ajudar com isso!'
    is_consistent, issues = scg.check_response(consistent_draft, abm, canon)
    assert is_consistent, "Consistent draft should pass"
    assert len(issues) == 0, "No issues for consistent draft"
    
    # Test contradictory response (claims ability pet doesn't have)
    contradictory_draft = 'Eu não posso te ajudar com lembretes'
    is_consistent, issues = scg.check_response(contradictory_draft, abm, canon)
    assert not is_consistent, "Contradictory draft should fail"
    assert len(issues) > 0, "Should detect contradiction"
    
    # Test another contradiction (negative claim becoming positive)
    contradictory_draft2 = 'Eu posso acessar a internet em tempo real'
    is_consistent2, issues2 = scg.check_response(contradictory_draft2, abm, canon)
    assert not is_consistent2, "Should detect this contradiction too"
    assert len(issues2) > 0, "Should detect contradiction"
    
    # Test auto-correction (works when ABM has "não posso" pattern)
    corrected = scg.correct_response(contradictory_draft2, issues2)
    # Auto-correction works for "não posso" claims
    if any('não posso' in issue.conflicting_abm_item.canonical_text.lower() for issue in issues2 if issue.conflicting_abm_item):
        assert corrected != contradictory_draft2, "Should auto-correct when possible"
    
    print(f'✅ Consistency guard working, detected {len(issues)} + {len(issues2)} issues')


def test_persistence():
    """Test ABM persistence (serialization/deserialization)."""
    print('\n=== Test: ABM Persistence ===')
    
    # Create state with ABM
    state = PetState()
    state.memory.abm.add_claim('Sou um pet virtual', ABMType.C_PET, 'e1', importance=0.9)
    state.memory.canon.update_from_abm(state.memory.abm)
    state.memory.echo.add_pattern('Olá!', PatternContext.GREETING, 0.8)
    
    # Serialize
    data = pet_state_to_dict(state)
    assert 'abm' in data, "Serialized data should contain ABM"
    assert 'canon' in data, "Serialized data should contain Canon"
    assert 'echo' in data, "Serialized data should contain Echo"
    
    # Deserialize
    restored_state = dict_to_pet_state(data)
    assert restored_state.memory.abm is not None, "ABM should be restored"
    assert restored_state.memory.canon is not None, "Canon should be restored"
    assert restored_state.memory.echo is not None, "Echo should be restored"
    
    # Verify content
    restored_claims = restored_state.memory.abm.get_active_items()
    assert len(restored_claims) == 1, "Should restore ABM claims"
    assert restored_claims[0].canonical_text == 'Sou um pet virtual'
    
    print('✅ Persistence working correctly')


def test_virtual_pet_integration():
    """Test ABM integration with VirtualPet."""
    print('\n=== Test: VirtualPet ABM Integration ===')
    
    pet = VirtualPet(user_id='test_user')
    
    # Check ABM initialization
    assert pet.state.memory.abm is not None, "ABM should be initialized"
    assert pet.state.memory.canon is not None, "Canon should be initialized"
    assert pet.state.memory.echo is not None, "Echo should be initialized"
    
    # Simulate response with ABM claims
    test_response = 'Eu sou um pet virtual que pode te ajudar. Eu não posso acessar dados externos.'
    pet._process_response_for_abm(test_response)
    
    # Check extraction
    active_claims = pet.state.memory.abm.get_active_items()
    assert len(active_claims) > 0, "Should extract claims from response"
    
    # Test consistency check
    contradictory = 'Eu posso acessar dados externos'
    corrected = pet.run_consistency_check(contradictory)
    assert corrected != contradictory, "Should correct contradiction"
    
    # Test reflection pass
    pet.reflection_pass()  # Should complete without error
    
    print('✅ VirtualPet integration working')


def run_all_tests():
    """Run all ABM tests."""
    print('🧪 Running ABM Test Suite...')
    
    try:
        test_abm_basic()
        test_canon_generation()
        test_echo_trace()
        test_consistency_guard()
        test_persistence()
        test_virtual_pet_integration()
        
        print('\n' + '='*50)
        print('🎉 All ABM tests passed!')
        print('='*50)
        return True
    except AssertionError as e:
        print(f'\n❌ Test failed: {e}')
        return False
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
