# Build a Domain

In this tutorial, we will build a "Wildfire" simulation from scratch. We'll define a forest as a graph of trees, implement fire spreading logic (physics), and add "Ranger" agents who move around to extinguish the flames.

## 1. Define the Environment (`config.yaml`)

We'll create 3 nodes representing patches of forest. We also include a `scenario_event` to start the fire at tick 10.

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

scenario_events:
  - tick: 10
    type: lightning_strike
    parameters: { node_id: patch_c }

domain_config:
  burn_rate: 2.0
  spread_threshold: 50.0
```

---

## 2. Implement the Plugin (`plugin.py`)

The plugin is the "brain" of the simulation. It handles physics, agent observations, and actions.

### Step A: Define the Events
Constellation is event-driven. Let's define an event to track heat levels.

```python
from dataclasses import dataclass, field
from constellation_core.engine.events import Event

@dataclass(frozen=True)
class FireUpdateEvent(Event):
    kind: str = "FIRE_UPDATE"
    node_id: str = ""
    heat: float = 0

@dataclass(frozen=True)
class SnapshotEvent(Event):
    kind: str = "SNAPSHOT"
    nodes: dict = field(default_factory=dict)
    agents: dict = field(default_factory=dict)
```

### Step B: The Plugin Logic
Now we implement the `SimulationPlugin` protocol.

```python
class WildfirePlugin:
    def get_tick_phases(self):
        return ["physics", "decisions", "actions", "snapshots"]

    def setup(self, state, config):
        # We can store domain config for easy access
        self.burn_rate = config.get("burn_rate", 1.0)
        self.spread_threshold = config.get("spread_threshold", 50.0)

    def run_phase(self, phase, state, config):
        if phase == "physics":
            return self._run_physics(state)
        elif phase == "snapshots":
            return self._run_snapshots(state)
        return []

    def _run_physics(self, state):
        events = []
        # 1. Fire consumes fuel and generates heat
        for node in state.nodes.values():
            if node.properties["heat"] > 0:
                node.properties["fuel"] -= self.burn_rate
                node.properties["heat"] += 5.0

            # 2. Fire spreads to neighbors if hot enough
            if node.properties["heat"] > self.spread_threshold:
                for neighbor_id in state.graph.neighbors(node.id):
                    state.nodes[neighbor_id].properties["heat"] += 2.0

            events.append(FireUpdateEvent(
                tick=state.tick, node_id=node.id, heat=node.properties["heat"]
            ))
        return events

    def _run_snapshots(self, state):
        # Emit a snapshot so the React viewer can see the state
        nodes_snap = {nid: dict(n.properties) for nid, n in state.nodes.items()}
        agents_snap = {aid: {"location": a.location} for aid, a in state.agents.items()}
        return [SnapshotEvent(tick=state.tick, nodes=nodes_snap, agents=agents_snap)]

    def build_observation(self, agent_id, state):
        # Rangers see the heat at their location and neighboring patches
        agent = state.agents[agent_id]
        visible = {agent.location: state.nodes[agent.location].properties["heat"]}
        for n in state.graph.neighbors(agent.location):
            visible[n] = state.nodes[n].properties["heat"]
        return {"current_location": agent.location, "surroundings": visible}

    def get_available_actions(self, agent_id, state):
        return ["wait", "extinguish", "move"]

    def validate_action(self, agent_id, action, state):
        if action.get("action") == "move" and "target" not in action:
            return False, "Move action requires a 'target'"
        return True, ""

    def execute_action(self, agent_id, action, state, tick):
        agent = state.agents[agent_id]
        if action["action"] == "extinguish":
            state.nodes[agent.location].properties["heat"] = 0
        elif action["action"] == "move":
            agent.location = action["target"]
        return []
```

---

## 3. Implement the Agent

Let's write a simple heuristic agent that moves toward the nearest fire.

```python
class RangerAgent:
    def choose_action(self, observation):
        loc = observation["current_location"]
        heat_map = observation["surroundings"]

        # If it's hot here, put it out!
        if heat_map[loc] > 0:
            return {"action": "extinguish"}

        # Otherwise, move to the hottest neighbor
        hottest_neighbor = max(heat_map, key=heat_map.get)
        if heat_map[hottest_neighbor] > 0:
            return {"action": "move", "target": hottest_neighbor}

        return {"action": "wait"}
```

---

## 4. Putting it all together

Finally, we register the plugin and run the simulation.

```python
from constellation_core.config.loader import register_plugin, load_config
from constellation_core.engine.simulation import Simulation

# 1. Register
register_plugin("wildfire", WildfirePlugin)

# 2. Load and Setup
config = load_config("config.yaml")
sim = Simulation(WildfirePlugin(), config.to_engine_config())
sim.setup()

# 3. Inject our Ranger agent
sim.state.agents["ranger_1"].decision_model = RangerAgent()

# 4. Run!
sim.run(ticks=100)
print("Simulation complete. Check the events to see if the Ranger saved the forest!")
```

## Next Steps

- **Visualize:** Run this with `python -m constellation_core serve` to see the heat levels change in the viewer.
- **LLMs:** Replace `RangerAgent` with an `LLMAgent` to see if GPT-4 is a better firefighter than our heuristic script.
- **Scenarios:** Add more lightning strikes in `config.yaml` to test the Ranger's efficiency under pressure.

---

- **[Next: Plugin Protocol Reference](plugin-protocol.md)**
- **[Back to Home](index.md)**
