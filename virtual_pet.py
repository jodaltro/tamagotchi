"""
High-level interface to the organic virtual pet.

The `VirtualPet` class wraps a `PetState` instance and provides methods to
process user messages (updating state) and generate responses based on the
selected action. When run directly, this module runs a simple simulation for
manual testing.
"""

import json
import random
from datetime import datetime
from typing import Optional

from .pet_state import PetState
from .language_generation import generate_text
from .image_recognition import extract_features, classify_image
from .nerve_integration import load_agent_config

class VirtualPet:
    def __init__(self) -> None:
        self.state = PetState()
        # Load Nerve‑style configuration on initialization. This allows
        # non‑developers to modify the pet's behavior (e.g. tone) via YAML.
        try:
            config = load_agent_config()
        except Exception:
            config = {}
        # Extract system prompt if available; default to empty string.
        self.system_prompt: str = ""
        if isinstance(config, dict):
            agent_section = config.get("agent") or {}
            if isinstance(agent_section, dict):
                self.system_prompt = agent_section.get("system_prompt") or ""

    def user_message(self, text: str, delay: Optional[float] = None) -> None:
        """Process a user message and update the pet state."""
        if delay is None:
            # simulate a random delay in minutes for testing
            delay = random.uniform(1, 20)
        self.state.update_from_interaction(text, delay)

    def user_image(self, image_bytes: bytes, delay: Optional[float] = None) -> None:
        """Process an image sent by the user and update the pet state.

        This method extracts visual features from the image, attempts to
        classify it using the Vision API (if available), and stores the
        information in the pet's memory. It also updates the pet's drives
        slightly to reflect the stimulation from visual input.

        Args:
            image_bytes: Raw bytes of the image sent by the user.
            delay: Optional simulated response delay in minutes; if not
                provided, a random delay is used for testing. This has no
                effect on visual memory but keeps the API consistent.
        """
        if delay is None:
            delay = random.uniform(1, 20)
        # Extract compact features
        features = extract_features(image_bytes)
        labels = classify_image(image_bytes)
        # Store in photographic memory
        self.state.memory.add_image(features, labels)
        # Add an episodic entry describing the image
        if labels:
            description = ", ".join(labels)
        else:
            description = "uma imagem interessante"
        self.state.memory.add_episode(f"viu {description}", salience=0.7)
        # Lightly boost curiosity and sociability due to visual stimulation
        self.state.drives["curiosity"] = min(1.0, self.state.drives["curiosity"] + 0.05)
        self.state.drives["sociability"] = min(1.0, self.state.drives["sociability"] + 0.02)

    def pet_response(self) -> str:
        """Generate the pet's response based on the selected action."""
        action = self.state.select_action()
        # Build a prompt based on the selected action and available memories
        if action == "ask_question":
            recents = self.state.memory.recall()
            context = f"Memórias recentes: {', '.join(recents)}." if recents else "Sem memórias recentes."
            prompt = "Faça uma pergunta curiosa e gentil ao usuário para saber mais sobre ele."
        elif action == "share_fact":
            facts = list(self.state.memory.semantic.keys())
            context = f"Fatos conhecidos: {', '.join(facts)}." if facts else "Ainda não sei muito sobre o usuário."
            prompt = "Compartilhe um fato interessante ou algo que você lembra sobre o usuário de forma amigável."
        elif action == "tell_joke":
            context = ""
            prompt = "Conte uma piada curta e divertida que seja apropriada para todas as idades."
        elif action == "request_game":
            context = ""
            prompt = "Convide o usuário para jogar um mini jogo de adivinhação ou brincadeira simples."
        elif action == "express_affection":
            context = ""
            prompt = "Expresse carinho e aprecie o tempo com o usuário de forma calorosa."
        else:
            context = ""
            prompt = "Responda de forma neutra e educada."
        # Prepend the system prompt to the context if defined. This allows
        # global instructions (e.g. tone) to influence the generated reply.
        full_context = context or ""
        if self.system_prompt:
            if full_context:
                full_context = f"{self.system_prompt}\n{full_context}"
            else:
                full_context = self.system_prompt
        # Use the language generation utility; it falls back gracefully
        return generate_text(prompt, full_context)

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
