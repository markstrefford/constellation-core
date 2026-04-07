"""Model backend protocol for LLM-driven agents."""

from __future__ import annotations

import json
from typing import Any, Protocol


class ModelBackend(Protocol):
    """Abstraction over LLM providers."""

    def complete(self, system_prompt: str, user_message: str) -> str:
        ...


class DummyBackend:
    """Returns a hold action. For testing."""

    def complete(self, system_prompt: str, user_message: str) -> str:
        return '{"action": "hold"}'


class LLMAgent:
    """
    An agent that uses an LLM backend to decide actions.

    Formats the observation as JSON in the user message, sends it
    to the backend with a system prompt, and parses the response
    as a JSON action dict.
    """

    def __init__(self, backend: ModelBackend, system_prompt: str) -> None:
        self.backend = backend
        self.system_prompt = system_prompt

    def choose_action(self, observation: dict[str, Any]) -> dict[str, Any]:
        user_message = json.dumps(observation)
        response = self.backend.complete(self.system_prompt, user_message)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"action": "hold", "error": "Failed to parse LLM response"}
