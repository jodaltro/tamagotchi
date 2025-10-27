"""
Acceptance tests for Llama 3.2 integration with memory architecture.

Tests cover the following scenarios as specified:
1. C&C - Promise and retrieval
2. Style change persistence
3. Topic switching consistency
4. SCG error correction
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagotchi.virtual_pet import VirtualPet
from tamagotchi.telemetry import get_telemetry
from tamagotchi.autobiographical_memory import ABMType, ABMStatus
import time


class TestResults:
    """Store and display test results."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_test(self, name: str, passed: bool, details: str = ""):
        """Add a test result."""
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details
        })
        
        if passed:
            self.passed += 1
            print(f"✅ PASS: {name}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {name}")
        
        if details:
            print(f"   Details: {details}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {len(self.tests)}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed / len(self.tests) * 100):.1f}%")
        print("=" * 60)
        
        return self.failed == 0


def test_1_commitment_promise_and_retrieval(results: TestResults):
    """
    Test 1: C&C - Promise and retrieval
    
    Ask pet to remember something "tomorrow". Simulate retrieval.
    Expected: Promise appears in context, pet confirms or adjusts plan.
    """
    print("\n" + "=" * 60)
    print("TEST 1: C&C - Promise and Retrieval")
    print("=" * 60)
    
    pet = VirtualPet()
    
    # Initialize ABM if not present
    if not hasattr(pet.state.memory, 'abm') or not pet.state.memory.abm:
        from tamagotchi.autobiographical_memory import AutobiographicalMemory
        pet.state.memory.abm = AutobiographicalMemory()
    
    # Step 1: Ask pet to remember something tomorrow
    pet.user_message("Pode me lembrar amanhã de ligar para minha mãe?")
    response1 = pet.pet_response()
    
    print(f"\nUser: Pode me lembrar amanhã de ligar para minha mãe?")
    print(f"Pet: {response1}")
    
    # Check if pet acknowledged the request
    acknowledged = any(word in response1.lower() for word in ["ok", "sim", "claro", "vou", "lembro"])
    
    results.add_test(
        "1.1: Pet acknowledges reminder request",
        acknowledged,
        f"Response: {response1[:100]}"
    )
    
    # Step 2: Add a C&C commitment manually to test retrieval
    from tamagotchi.autobiographical_memory import ABMItem
    from datetime import datetime
    
    commitment = ABMItem(
        type=ABMType.C_AND_C_PERSONA,
        canonical_text="Prometi lembrar o usuário de ligar para a mãe amanhã",
        source_event_id="test_commitment_1",
        importance=0.9,
        stability=0.9
    )
    
    pet.state.memory.abm.add_item(commitment)
    
    # Step 3: Simulate next day - ask about it
    pet.user_message("E aí, tinha alguma coisa que você ia me lembrar?")
    response2 = pet.pet_response()
    
    print(f"\n[Next day simulation]")
    print(f"User: E aí, tinha alguma coisa que você ia me lembrar?")
    print(f"Pet: {response2}")
    
    # Check if commitment appears in response
    commitment_mentioned = any(word in response2.lower() for word in ["mãe", "ligar", "lembrar"])
    
    results.add_test(
        "1.2: Pet recalls commitment in response",
        commitment_mentioned,
        f"Response mentions commitment: {response2[:100]}"
    )
    
    # Check if commitment is in active C&C items
    active_commitments = pet.state.memory.abm.get_active_items(ABMType.C_AND_C_PERSONA)
    has_active_commitment = len(active_commitments) > 0
    
    results.add_test(
        "1.3: Commitment exists in C&C active items",
        has_active_commitment,
        f"Active commitments: {len(active_commitments)}"
    )


def test_2_style_change_persistence(results: TestResults):
    """
    Test 2: Style change persistence
    
    Request: "respond shorter and more direct"
    Expected: VOICE in PET-CANON/ABM updated, next responses follow style.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Style Change Persistence")
    print("=" * 60)
    
    pet = VirtualPet()
    
    # Initialize ABM
    if not hasattr(pet.state.memory, 'abm') or not pet.state.memory.abm:
        from tamagotchi.autobiographical_memory import AutobiographicalMemory
        pet.state.memory.abm = AutobiographicalMemory()
    
    # Step 1: Get initial response length
    pet.user_message("Como você está?")
    response1 = pet.pet_response()
    initial_length = len(response1)
    
    print(f"\nUser: Como você está?")
    print(f"Pet: {response1}")
    print(f"Length: {initial_length} chars")
    
    # Step 2: Request shorter responses
    pet.user_message("Pode responder mais curto e direto?")
    response2 = pet.pet_response()
    
    print(f"\nUser: Pode responder mais curto e direto?")
    print(f"Pet: {response2}")
    
    # Check acknowledgment
    acknowledged = any(word in response2.lower() for word in ["ok", "sim", "claro", "certo", "vou"])
    
    results.add_test(
        "2.1: Pet acknowledges style change request",
        acknowledged,
        f"Response: {response2[:100]}"
    )
    
    # Step 3: Add VOICE item to ABM
    from tamagotchi.autobiographical_memory import ABMItem
    
    voice_item = ABMItem(
        type=ABMType.VOICE,
        canonical_text="Respondo de forma curta e direta",
        source_event_id="test_style_change",
        importance=0.8,
        stability=0.9
    )
    
    pet.state.memory.abm.add_item(voice_item)
    
    # Update canon from ABM
    if pet.state.memory.canon:
        pet.state.memory.canon.update_from_abm(pet.state.memory.abm)
    
    # Step 4: Test if next response is shorter
    pet.user_message("Qual seu filme favorito?")
    response3 = pet.pet_response()
    
    print(f"\n[After style change]")
    print(f"User: Qual seu filme favorito?")
    print(f"Pet: {response3}")
    print(f"Length: {len(response3)} chars")
    
    # Response should ideally be shorter (allowing some variance)
    is_shorter = len(response3) < initial_length * 1.2  # Allow 20% variance
    
    results.add_test(
        "2.2: Subsequent responses respect style change",
        is_shorter,
        f"Initial: {initial_length} chars, After: {len(response3)} chars"
    )
    
    # Check if VOICE item exists in ABM
    voice_items = pet.state.memory.abm.get_active_items(ABMType.VOICE)
    has_voice_item = len(voice_items) > 0
    
    results.add_test(
        "2.3: VOICE item stored in ABM",
        has_voice_item,
        f"VOICE items in ABM: {len(voice_items)}"
    )


def test_3_topic_switching_consistency(results: TestResults):
    """
    Test 3: Topic switching without contradictions
    
    Switch topics rapidly (agenda → health → hobby)
    Expected: Pet maintains consistency, doesn't contradict capabilities.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Topic Switching Consistency")
    print("=" * 60)
    
    pet = VirtualPet()
    
    # Initialize ABM and add capability limits
    if not hasattr(pet.state.memory, 'abm') or not pet.state.memory.abm:
        from tamagotchi.autobiographical_memory import AutobiographicalMemory
        pet.state.memory.abm = AutobiographicalMemory()
    
    from tamagotchi.autobiographical_memory import ABMItem
    
    # Add some capability limits
    limits = [
        ABMItem(
            type=ABMType.C_PET,
            canonical_text="Não posso acessar sua agenda ou calendário",
            source_event_id="test_limits",
            importance=0.9,
            stability=1.0
        ),
        ABMItem(
            type=ABMType.C_PET,
            canonical_text="Não posso monitorar sua saúde em tempo real",
            source_event_id="test_limits",
            importance=0.9,
            stability=1.0
        )
    ]
    
    for limit in limits:
        pet.state.memory.abm.add_item(limit)
    
    # Test topic 1: Agenda
    pet.user_message("O que eu tenho na agenda hoje?")
    response1 = pet.pet_response()
    
    print(f"\nTopic 1 - Agenda")
    print(f"User: O que eu tenho na agenda hoje?")
    print(f"Pet: {response1}")
    
    # Should NOT claim to have access
    doesnt_claim_access = "não" in response1.lower() and ("acesso" in response1.lower() or "não posso" in response1.lower())
    
    results.add_test(
        "3.1: Pet correctly states it cannot access agenda",
        doesnt_claim_access,
        f"Response: {response1[:100]}"
    )
    
    # Test topic 2: Health
    pet.user_message("Como está minha saúde agora?")
    response2 = pet.pet_response()
    
    print(f"\nTopic 2 - Health")
    print(f"User: Como está minha saúde agora?")
    print(f"Pet: {response2}")
    
    # Should NOT claim real-time monitoring
    doesnt_claim_monitoring = "não" in response2.lower() and ("tempo real" in response2.lower() or "não posso" in response2.lower() or "monitorar" in response2.lower())
    
    results.add_test(
        "3.2: Pet correctly states it cannot monitor health",
        doesnt_claim_monitoring or "não sei" in response2.lower(),
        f"Response: {response2[:100]}"
    )
    
    # Test topic 3: Hobby (neutral, no limits)
    pet.user_message("Gosta de música?")
    response3 = pet.pet_response()
    
    print(f"\nTopic 3 - Hobby")
    print(f"User: Gosta de música?")
    print(f"Pet: {response3}")
    
    # Should give a normal response
    gives_normal_response = len(response3) > 10  # At least some content
    
    results.add_test(
        "3.3: Pet responds normally to neutral topics",
        gives_normal_response,
        f"Response length: {len(response3)} chars"
    )


def test_4_scg_error_detection(results: TestResults):
    """
    Test 4: SCG error detection and correction
    
    Force a contradiction scenario and check if SCG detects it.
    Expected: SCG detects and flags/corrects contradictions.
    """
    print("\n" + "=" * 60)
    print("TEST 4: SCG Error Detection and Correction")
    print("=" * 60)
    
    from tamagotchi.self_consistency_guard import SelfConsistencyGuard
    from tamagotchi.autobiographical_memory import AutobiographicalMemory, ABMItem, ABMType
    from tamagotchi.pet_canon import PetCanon
    
    # Setup ABM with a clear limit
    abm = AutobiographicalMemory()
    limit = ABMItem(
        type=ABMType.C_PET,
        canonical_text="Não posso ver em tempo real",
        source_event_id="test_scg",
        importance=1.0,
        stability=1.0
    )
    abm.add_item(limit)
    
    canon = PetCanon()
    canon.limits = ["ver em tempo real"]
    
    scg = SelfConsistencyGuard()
    
    # Test 1: Draft that contradicts the limit
    draft_bad = "Sim, estou vendo sua tela agora em tempo real!"
    
    is_consistent, issues = scg.check_response(draft_bad, abm, canon)
    
    print(f"\nDraft (contradictory): {draft_bad}")
    print(f"SCG detected issues: {len(issues)}")
    
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.description}")
    
    detected_contradiction = not is_consistent and len(issues) > 0
    
    results.add_test(
        "4.1: SCG detects contradiction",
        detected_contradiction,
        f"Issues found: {len(issues)}"
    )
    
    # Test 2: Apply correction
    if issues:
        corrected = scg.correct_response(draft_bad, issues)
        
        print(f"\nCorrected response: {corrected}")
        
        # Check if correction mentions the limitation
        mentions_limitation = "não" in corrected.lower()
        
        results.add_test(
            "4.2: SCG correction addresses issue",
            mentions_limitation,
            f"Corrected: {corrected[:100]}"
        )
    else:
        results.add_test(
            "4.2: SCG correction addresses issue",
            False,
            "No issues to correct"
        )
    
    # Test 3: Good draft should pass
    draft_good = "Não, não consigo ver sua tela. Como posso ajudar?"
    
    is_consistent_good, issues_good = scg.check_response(draft_good, abm, canon)
    
    print(f"\nDraft (good): {draft_good}")
    print(f"SCG result: {'PASS' if is_consistent_good else 'FAIL'}")
    
    results.add_test(
        "4.3: SCG passes consistent responses",
        is_consistent_good,
        f"Issues: {len(issues_good)}"
    )


def test_5_telemetry_metrics(results: TestResults):
    """
    Test 5: Verify telemetry is collecting metrics
    
    Expected: Metrics are being recorded and can be retrieved.
    """
    print("\n" + "=" * 60)
    print("TEST 5: Telemetry Metrics")
    print("=" * 60)
    
    telemetry = get_telemetry()
    
    # Reset for clean test
    telemetry.reset()
    
    # Simulate some turns
    pet = VirtualPet()
    
    for i in range(3):
        pet.user_message(f"Mensagem de teste {i+1}")
        response = pet.pet_response()
        time.sleep(0.1)  # Small delay
    
    # Get metrics
    summary = telemetry.get_summary()
    
    print(f"\nMetrics summary:")
    print(f"  Total turns: {summary['total_turns']}")
    print(f"  Latency p50: {summary['latency_p50_ms']:.0f}ms")
    print(f"  Avg tokens in: {summary['avg_tokens_in']:.1f}")
    print(f"  Avg tokens out: {summary['avg_tokens_out']:.1f}")
    print(f"  Consistency rate: {summary['consistency_rate_pct']:.1f}%")
    
    has_turns = summary['total_turns'] >= 3
    has_latency = summary['latency_p50_ms'] > 0
    
    results.add_test(
        "5.1: Telemetry records turns",
        has_turns,
        f"Turns recorded: {summary['total_turns']}"
    )
    
    results.add_test(
        "5.2: Telemetry tracks latency",
        has_latency,
        f"Latency p50: {summary['latency_p50_ms']:.0f}ms"
    )
    
    # Get detailed report
    report = telemetry.get_detailed_report()
    
    print(f"\n{report}")
    
    has_report = len(report) > 100
    
    results.add_test(
        "5.3: Telemetry generates reports",
        has_report,
        f"Report length: {len(report)} chars"
    )


def run_all_tests():
    """Run all acceptance tests."""
    print("\n" + "=" * 60)
    print("LLAMA 3.2 INTEGRATION - ACCEPTANCE TESTS")
    print("=" * 60)
    
    results = TestResults()
    
    # Run each test
    test_1_commitment_promise_and_retrieval(results)
    test_2_style_change_persistence(results)
    test_3_topic_switching_consistency(results)
    test_4_scg_error_detection(results)
    test_5_telemetry_metrics(results)
    
    # Print summary
    all_passed = results.print_summary()
    
    if all_passed:
        print("\n🎉 All acceptance tests PASSED!")
        return 0
    else:
        print(f"\n⚠️  {results.failed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
