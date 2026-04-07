# constellation-core

A domain-agnostic simulation platform for running multi-agent simulations. Define an environment as a graph of nodes and edges, drop in agents that observe and act, and let the engine run. All domain logic lives in plugins -- the core never assumes what your simulation is about.

The same engine runs a **global supply chain** with freighters, factories, and disruption cascading across continents, and a **stock market** with 20 traders exhibiting emergent herd behaviour and market crashes. No code changes to the core -- just different plugins.

## What it does

- **Generic graph topology** -- nodes with arbitrary properties, edges with distances and types, Dijkstra pathfinding
- **Plugin-driven event loop** -- your domain plugin defines what phases run each tick and what they do
- **Agent protocol** -- agents receive a JSON observation, return a JSON action. Algorithmic or LLM-driven.
- **Scenario events** -- schedule mid-simulation shocks (supply disruptions, market panics, policy changes) from config
- **Real-time viewer** -- React frontend connects via SSE, renders topology, properties, and time series charts
- **Persistence** -- SQLite event storage for replay and analysis

## Architecture

```
engine/       Event loop, SimulationPlugin protocol, scenario scheduling
topology/     Graph (nodes, edges, pathfinding), EnvironmentState
agent/        AgentData, AgentDecision protocol, ModelBackend for LLMs
config/       YAML loading with Pydantic validation
persistence/  StorageBackend protocol, SQLite implementation
server/       FastAPI with SSE streaming
viewer/       React + Vite + TypeScript
```

The core is deliberately thin. It knows about graphs, agents, ticks, and events. It does not know about prices, cargo, portfolios, headcount, or any other domain concept. Your plugin defines all of that.

## Installation

**Requirements:** Python 3.11+, Node.js 18+ (for the viewer)

```bash
# Clone
git clone https://github.com/markstrefford/constellation-core.git
cd constellation-core

# Install Python package (core + dev tools + server)
pip install -e ".[dev,server]"

# Install viewer dependencies
cd viewer && npm install && cd ..
```

Or install just the core (no server/viewer):

```bash
pip install -e .
```

### Dependencies

**Core** (always installed):
- `pydantic` -- config validation
- `pyyaml` -- YAML config loading

**Server** (optional, `pip install -e ".[server]"`):
- `fastapi` -- HTTP API and SSE streaming
- `uvicorn` -- ASGI server
- `sse-starlette` -- Server-Sent Events support

**Dev** (optional, `pip install -e ".[dev]"`):
- `pytest` -- testing
- `ruff` -- linting
- `mypy` -- type checking

## Running the examples

### Headless (no viewer)

```bash
# Global supply chain -- 5 nodes, 3 agents, Suez disruption at tick 200
python -m constellation_core run examples/supply_chain/config.yaml --ticks 500

# Stock market -- 1 node, 20 traders, earnings surprise + market panic
python -m constellation_core run examples/stock_market/config.yaml --ticks 500
```

### With the viewer

Start the backend and frontend in separate terminals:

```bash
# Terminal 1: start the API server
python -m constellation_core serve examples/supply_chain/config.yaml

# Terminal 2: start the viewer dev server
cd viewer && npx vite
```

Open http://localhost:5173, click **Start Simulation**, and click nodes to see live property updates and time series charts.

### Example: Global Supply Chain

Five nodes representing a supply chain from Shanghai to European retail hubs. Raw materials are produced in Shanghai, shipped by ocean freighter to Rotterdam, trucked to a factory in Stuttgart where they become finished goods, then distributed to Munich and Berlin.

At tick 200, a Suez Canal blockage doubles the Shanghai-Rotterdam shipping distance. Watch the disruption cascade: Rotterdam runs dry, Stuttgart's production drops, retail prices spike.

**Topology:**
```
Shanghai --ocean(20)--> Rotterdam --road(5)--> Stuttgart Factory
                                                    |
                                              road(3)  road(4)
                                                    |       |
                                            Munich Hub   Berlin Hub
```

### Example: Mini Stock Market

A single exchange node with 20 agents trading 5 stocks. 10 momentum traders (buy rising, sell falling), 5 contrarians (buy falling, sell rising), and 5 random traders providing noise.

At tick 100, an earnings surprise boosts one stock 20%. At tick 300, a market panic drops sentiment to 0.1. The interesting finding: when too many agents follow the same momentum strategy, prices become volatile and crash -- diversity of strategy matters.

### Example: Company Restructure (coming soon)

A company with 5 departments, agents representing department heads, and scenario shocks like AI automation and budget reallocation. This example needs the information asymmetry layer (Tier 2) -- the CEO sees everything, department heads see only their neighbours. Design doc is in [`examples/reorg/README.md`](examples/reorg/README.md).

## Building your own domain

A domain plugin is a Python class implementing the `SimulationPlugin` protocol. The core engine calls your plugin each tick -- you define what happens.

### 1. Define your config

```yaml
seed: 42
ticks: 300
domain: my_domain

nodes:
  - id: node_a
    properties:
      temperature: 20.0
      pressure: 1.0
    metadata:
      label: "Sensor A"
      type: sensor

  - id: node_b
    properties:
      temperature: 22.0
      pressure: 1.1
    metadata:
      label: "Sensor B"

edges:
  - from: node_a
    to: node_b
    distance: 10.0

agents:
  - id: monitor_1
    starting_location: node_a
    properties:
      alert_threshold: 30.0
    metadata:
      role: monitor

scenario_events:
  - tick: 100
    type: heat_spike
    parameters:
      node: node_a
      temperature: 50.0

domain_config:
  cooling_rate: 0.5
```

### 2. Implement the plugin

```python
from constellation_core.engine.events import Event
from constellation_core.topology.state import EnvironmentState
from dataclasses import dataclass

@dataclass(frozen=True)
class TemperatureEvent(Event):
    kind: str = "TEMPERATURE"
    node_id: str = ""
    value: float = 0

class MyDomainPlugin:
    def get_tick_phases(self):
        return ["physics", "decisions", "snapshots"]

    def setup(self, state, config):
        pass  # Initialize domain-specific state if needed

    def run_phase(self, phase, state, config):
        if phase == "physics":
            return self._run_physics(state, config)
        elif phase == "decisions":
            return []  # Agent decisions handled here
        elif phase == "snapshots":
            return []  # Emit state for viewer
        return []

    def _run_physics(self, state, config):
        events = []
        cooling = config.get("cooling_rate", 0.1)
        for node in state.nodes.values():
            temp = node.properties.get("temperature", 20)
            # Cool toward 20 degrees
            node.properties["temperature"] = temp + (20 - temp) * cooling
            events.append(TemperatureEvent(
                tick=state.tick, node_id=node.id,
                value=node.properties["temperature"],
            ))
        return events

    def build_observation(self, agent_id, state):
        agent = state.agents[agent_id]
        node = state.nodes[agent.location]
        return {
            "agent_id": agent_id,
            "location": agent.location,
            "temperature": node.properties.get("temperature", 0),
            "pressure": node.properties.get("pressure", 0),
        }

    def get_available_actions(self, agent_id, state):
        return ["alert", "wait"]

    def validate_action(self, agent_id, action, state):
        if "action" not in action:
            return False, "Missing 'action' field"
        return True, ""

    def execute_action(self, agent_id, action, state, tick):
        return []
```

### 3. Run it

```python
from constellation_core.engine.simulation import Simulation
from constellation_core.config.loader import load_config

config = load_config("my_config.yaml")
plugin = MyDomainPlugin()
sim = Simulation(plugin, config.to_engine_config())
sim.setup()
events = sim.run(ticks=300)
```

Or register it for CLI use:

```python
from constellation_core.config.loader import register_plugin
register_plugin("my_domain", MyDomainPlugin)
```

Then: `python -m constellation_core run my_config.yaml`

### The plugin protocol

Your plugin defines everything domain-specific:

| Method | What it does |
|--------|-------------|
| `get_tick_phases()` | List of phase names run each tick, in order |
| `setup(state, config)` | One-time initialization before the first tick |
| `run_phase(phase, state, config)` | Execute one phase -- mutate state, return events |
| `build_observation(agent_id, state)` | Build the JSON observation an agent receives |
| `get_available_actions(agent_id, state)` | What actions this agent can take right now |
| `validate_action(agent_id, action, state)` | Check if an action is valid |
| `execute_action(agent_id, action, state, tick)` | Execute a validated action |

The engine never looks inside `node.properties` or `agent.properties` -- those are `dict[str, float]` that your plugin reads and writes however it wants.

### Agent protocol

Agents implement a single method:

```python
class AgentDecision(Protocol):
    def choose_action(self, observation: dict) -> dict: ...
```

The observation is whatever your plugin's `build_observation()` returns. The action dict is whatever your plugin's `validate_action()` accepts. The core doesn't interpret either.

For LLM-driven agents, use the `ModelBackend` protocol:

```python
from constellation_core.agent.backends import LLMAgent

class MyLLMBackend:
    def complete(self, system_prompt: str, user_message: str) -> str:
        # Call your LLM here, return JSON string
        ...

agent = LLMAgent(MyLLMBackend(), system_prompt="You are a trading agent...")
```

## Project structure

```
constellation-core/
  src/constellation_core/    Core platform (domain-agnostic)
    engine/                  Event loop, plugin protocol, scenarios
    topology/                Graph, nodes, edges, environment state
    agent/                   Agent model, decision protocol, LLM backend
    config/                  YAML loading, Pydantic validation
    persistence/             Storage protocol, SQLite
    server/                  FastAPI, SSE streaming
    deployment/              Deployment backend protocol
  examples/
    supply_chain/            Global logistics example
    stock_market/            Herd behaviour example
    reorg/                   Company restructure (design doc)
  viewer/                    React + Vite frontend
  tests/                     78 tests mirroring source layout
  docs/                      Specs and design documents
```

## Running tests

```bash
python -m pytest tests/ -v
```

Tests mirror the source layout. Each module has its own test directory, plus integration tests for the example domains.

## Contributing

Contributions are welcome. If you find a bug or have a feature request, please [open an issue](https://github.com/markstrefford/constellation-core/issues).

For code contributions:

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass (`python -m pytest tests/ -v`)
5. Submit a pull request

Please keep the core domain-agnostic. If your change involves domain-specific logic (pricing models, specific action types, agent strategies), it belongs in an example plugin, not in the core.

## License

Apache 2.0 -- see [LICENSE](LICENSE) for details.
