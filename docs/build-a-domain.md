# Build a Domain

In this tutorial, we will build a simple "Wildfire" simulation. We'll define a forest as a graph of trees, implement fire spreading logic in a plugin, and add "Firefighter" agents to put it out.

## 1. Define the Environment (`config.yaml`)

First, we define our world. We'll create 3 nodes representing patches of forest.

```yaml
seed: 42
domain: wildfire
ticks: 100

nodes:
  - id: patch_a
    properties: { fuel: 100.0, heat: 0.0 }
  - id: patch_b
    properties: { fuel: 100.0, heat: 0.0 }
  - id: patch_c
    properties: { fuel: 100.0, heat: 0.0 }

edges:
  - { from: patch_a, to: patch_b, distance: 1.0 }
  - { from: patch_b, to: patch_c, distance: 1.0 }

agents:
  - id: ranger_1
    starting_location: patch_a
```

---

## 2. Implement the Plugin (`plugin.py`)

The plugin defines the "physics" of our world. We need to implement the `SimulationPlugin` protocol.

### Define the Events
We want to track when a fire starts and when it is extinguished.

```python
from dataclasses import dataclass
from constellation_core.engine.events import Event

@dataclass(frozen=True)
class FireUpdateEvent(Event):
    kind: str = "FIRE_UPDATE"
    node_id: str = ""
    heat: float = 0
```

### Create the Plugin Class
We'll implement three key methods: `get_tick_phases`, `run_phase`, and `execute_action`.

```python
class WildfirePlugin:
    def get_tick_phases(self):
        # We'll run fire physics, then let agents decide, then execute actions
        return ["fire_physics", "decisions", "actions"]

    def run_phase(self, phase, state, config):
        if phase == "fire_physics":
            return self._run_fire_physics(state)
        return []

    def _run_fire_physics(self, state):
        events = []
        for node in state.nodes.values():
            # If heat > 10, it starts consuming fuel
            if node.properties["heat"] > 10:
                node.properties["fuel"] -= 2
                node.properties["heat"] += 1

            events.append(FireUpdateEvent(
                tick=state.tick, node_id=node.id, heat=node.properties["heat"]
            ))
        return events

    def build_observation(self, agent_id, state):
        # The agent sees the heat at their current location
        agent = state.agents[agent_id]
        node = state.nodes[agent.location]
        return {"location": agent.location, "heat": node.properties["heat"]}

    def get_available_actions(self, agent_id, state):
        return ["wait", "extinguish"]

    def execute_action(self, agent_id, action, state, tick):
        if action["action"] == "extinguish":
            agent = state.agents[agent_id]
            node = state.nodes[agent.location]
            node.properties["heat"] = 0
        return []
```

---

## 3. Register and Run

To run your new domain, you need to tell the Constellation loader about it.

```python
from constellation_core.config.loader import register_plugin, load_config
from constellation_core.engine.simulation import Simulation

# 1. Register the plugin
register_plugin("wildfire", WildfirePlugin)

# 2. Load config and run
config = load_config("config.yaml")
sim = Simulation(WildfirePlugin(), config.to_engine_config())
sim.setup()
sim.run(ticks=100)
```

## Summary

You've just built a domain! To make it more realistic, you could:
1. **Spread Fire:** In `fire_physics`, look at `state.graph.neighbors(node_id)` and increase heat in neighboring nodes.
2. **Add LLM Rangers:** Use a `ModelBackend` to let an LLM decide which patch of forest to prioritize based on fuel levels.
3. **Visualize:** Add a `SnapshotEvent` to the "snapshots" phase so you can see the forest burning in the React viewer.

[See the Plugin Protocol reference &rarr;](plugin-protocol.md)
