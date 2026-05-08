# Agents

Agents are the active participants in a Constellation simulation. They observe the environment, make decisions, and take actions to achieve their objectives.

---

## The Agent Protocol

Constellation uses a simple "JSON-in, JSON-out" protocol. Any object that implements the `AgentDecision` protocol can be used as an agent.

```python
class AgentDecision(Protocol):
    def choose_action(self, observation: dict) -> dict:
        ...
```

- **Observation:** A dictionary provided by the plugin's `build_observation` method. It typically contains information about the agent's current location and its immediate surroundings.
- **Action:** A dictionary returned by the agent. The format must match what the plugin's `validate_action` method expects.

---

## Heuristic Agents

For many simulations, simple rule-based (heuristic) agents are sufficient.

```python
class SimpleCourier:
    def choose_action(self, observation):
        if observation["cargo_quantity"] > 0:
            return {"action": "travel", "destination": "warehouse_b"}
        else:
            return {"action": "load", "item": "raw_materials"}
```

---

## LLM-Driven Agents

Constellation provides built-in support for LLM-driven agents via the `LLMAgent` class and `ModelBackend` protocol.

### `LLMAgent`
The `LLMAgent` takes a `ModelBackend` and a `system_prompt`. It automatically:
1. Converts the observation dict to a JSON string.
2. Sends it to the LLM.
3. Parses the LLM's response back into an action dictionary.

### `ModelBackend` Protocol
To use an LLM provider (OpenAI, Anthropic, local models), you simply implement a small wrapper:

```python
class MyOpenAIBackend:
    def complete(self, system_prompt: str, user_message: str) -> str:
        # Call OpenAI API here...
        return '{"action": "wait"}'

backend = MyOpenAIBackend()
agent = LLMAgent(backend, system_prompt="You are a logistics coordinator...")
```

---

## Information Asymmetry

One of the key features of Constellation is the ability to simulate **information asymmetry**.

Because the plugin defines the observation, you can control exactly what each agent knows. For example:
- A "CEO" agent might see the entire graph state.
- A "Truck Driver" agent might only see the node they are currently at.
- A "Market Trader" might see price history but not the inventory levels of other traders.

This allows researchers to study how different information levels impact system-wide efficiency and stability.
