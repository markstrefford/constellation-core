# constellation-core

A domain-agnostic simulation platform for running multi-agent simulations. Define an environment as a graph of nodes and edges, drop in agents that observe and act, and let the engine run. All domain logic lives in plugins — the core never assumes what your simulation is about.

The same engine runs a **global supply chain** with freighters, factories, and disruption cascading across continents, and a **stock market** with 20 traders exhibiting emergent herd behaviour and market crashes. No code changes to the core — just different plugins.

## What it does

- **Generic graph topology** — nodes with arbitrary properties, edges with distances and types, Dijkstra pathfinding
- **Plugin-driven event loop** — your domain plugin defines what phases run each tick and what they do
- **Agent protocol** — agents receive a JSON observation, return a JSON action; algorithmic or LLM-driven
- **Scenario events** — schedule mid-simulation shocks from config (supply disruptions, market panics, policy changes)
- **Real-time viewer** — React frontend connects via SSE, renders topology, properties, and time series
- **Persistence** — SQLite event storage for replay and analysis

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

**Requirements:** Python 3.11+, Node.js 18+ (for the viewer).

```bash
git clone https://github.com/markstrefford/constellation-core.git
cd constellation-core

# Core + dev tools + server
pip install -e ".[dev,server]"

# Viewer
cd viewer && npm install && cd ..
```

Or just the core (no server/viewer): `pip install -e .`

## Running the examples

Headless:

```bash
# Global supply chain — 5 nodes, 3 agents, Suez disruption
python -m constellation_core run examples/supply_chain/config.yaml --ticks 500

# Stock market — 1 node, 20 traders, earnings surprise + market panic
python -m constellation_core run examples/stock_market/config.yaml --ticks 500
```

With the viewer, in two terminals:

```bash
# Terminal 1
python -m constellation_core serve examples/supply_chain/config.yaml

# Terminal 2
cd viewer && npx vite
```

Open http://localhost:5173, click **Start Simulation**, and click nodes to see live property updates and time series charts.

The bundled examples are functional but rough — both have known limitations documented honestly in the docs site under [Examples](https://markstrefford.github.io/constellation-core/examples/).

## Documentation

**[Read the docs](https://markstrefford.github.io/constellation-core/)** for the full guide: tutorial, concepts, the plugin protocol reference, the configuration schema, the agent layer, the viewer, and FAQ.

## Building your own domain

A domain plugin is a Python class implementing the `SimulationPlugin` protocol. The core engine calls your plugin each tick — you define the phases, what each phase does, and how agents observe and act. See **[Build a domain](https://markstrefford.github.io/constellation-core/build-a-domain/)** for an end-to-end walkthrough, and **[Plugin protocol](https://markstrefford.github.io/constellation-core/plugin-protocol/)** for the full reference.

## Project structure

```
constellation-core/
  src/constellation_core/    Core platform (domain-agnostic)
  examples/                  Bundled example domains
  viewer/                    React + Vite frontend
  tests/                     Test suite (pytest)
  docs/                      Documentation source (mkdocs-material)
```

## Running tests

```bash
python -m pytest tests/ -v
```

## Contributing

Contributions are welcome. If you find a bug or have a feature request, please [open an issue](https://github.com/markstrefford/constellation-core/issues). For code contributions, fork the repo, write tests, ensure the suite passes, and submit a PR. See [Contributing](https://markstrefford.github.io/constellation-core/contributing/) in the docs for development setup details.

Please keep the core domain-agnostic. If your change involves domain-specific logic (pricing models, specific action types, agent strategies), it belongs in an example plugin, not the core.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
