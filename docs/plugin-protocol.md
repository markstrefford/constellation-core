# Plugin Protocol

The `SimulationPlugin` protocol is the contract between the Constellation engine and your domain logic. It is a `typing.Protocol`, meaning you can implement it using any class that provides the following methods.

## Overview

The engine treats your plugin as the source of truth for "physics" and agent interactions. It calls these methods in a strict order every tick.

---

## Method Reference

### `get_tick_phases() -> list[str]`
Called once per tick to determine which phases to run.
- **Returns:** An ordered list of strings representing the names of the phases.
- **Typical values:** `["physics", "decisions", "actions", "snapshots"]`.

### `setup(state, config)`
Called once before the first tick after the engine has initialized the environment state from the YAML config.
- **`state` (`EnvironmentState`):** The initial world state.
- **`config` (`dict`):** The `domain_config` section from the YAML.
- **Use for:** Initializing complex properties, pre-calculating paths, or setting up internal counters.

### `run_phase(phase, state, config) -> list[Event]`
Executed for every phase name returned by `get_tick_phases`.
- **`phase` (`str`):** The name of the current phase.
- **`state` (`EnvironmentState`):** The current world state (mutable).
- **`config` (`dict`):** The `domain_config` section from the YAML.
- **Returns:** A list of `Event` objects to be recorded and/or streamed.
- **Use for:** Implementing world physics (e.g., resource growth, price decay, fire spreading).

### `build_observation(agent_id, state) -> dict`
Called for each agent during the "decisions" phase to generate their input.
- **`agent_id` (`str`):** The ID of the agent.
- **`state` (`EnvironmentState`):** The current world state.
- **Returns:** A JSON-serializable dictionary.
- **Use for:** Implementing information asymmetry (e.g., an agent only sees their current node and neighbors).

### `get_available_actions(agent_id, state) -> list[str]`
Returns the list of high-level actions an agent *could* take.
- **Returns:** A list of action names.
- **Use for:** Constraining the agent's action space (e.g., you can only "sell" if you have stock).

### `validate_action(agent_id, action, state) -> tuple[bool, str]`
Checks if the action returned by the agent is valid.
- **`action` (`dict`):** The action dict returned by the agent.
- **Returns:** `(True, "")` if valid, or `(False, "Error message")` if invalid.
- **Use for:** Preventing cheating or impossible moves.

### `execute_action(agent_id, action, state, tick) -> list[Event]`
Applies the effects of a validated action to the world state.
- **`action` (`dict`):** The validated action.
- **Returns:** A list of `Event` objects.
- **Use for:** Mutating node or agent properties based on agent decisions.

---

## Example Implementation

```python
class MyPlugin:
    def get_tick_phases(self):
        return ["physics"]

    def setup(self, state, config):
        print(f"Simulation started with {len(state.nodes)} nodes")

    def run_phase(self, phase, state, config):
        if phase == "physics":
            for node in state.nodes.values():
                node.properties["stock"] += 1.0
        return []

    # ... implement other methods ...
```

---

- **[Next: Configuration Reference](configuration.md)**
- **[Back to Home](index.md)**
