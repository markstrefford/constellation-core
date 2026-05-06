# constellation-core

A domain-agnostic simulation platform for running multi-agent simulations.

Define an environment as a graph of nodes and edges, drop in agents that observe and act, and let the engine run. All domain logic lives in plugins — the core never assumes what your simulation is about. The same engine runs a global supply chain, a stock market, and (in principle) anything else you can describe as agents acting on a graph.

---

## Where to go next

- **[Getting started](getting-started.md)** — install, run an example, see something happen.
- **[Concepts](concepts.md)** — what's in the core, what's in plugins, why it's split this way.
- **[Build a domain](build-a-domain.md)** — write your own `SimulationPlugin` end-to-end.
- **[Plugin protocol](plugin-protocol.md)** — full reference for the seam between core and plugins.

---

## Project status

constellation-core is at version **0.2.1** — early but functional.

Two example domains ship with the repo: a global supply chain (5 nodes, 3 logistics agents, a Suez Canal disruption event) and a mini stock market (1 exchange, 20 traders with mixed strategies, an earnings surprise and a market panic). Both demonstrate the plugin model end-to-end. Both have rough edges that are documented honestly in [Examples](examples.md).

The platform is open source under the [Apache 2.0 license](https://github.com/markstrefford/constellation-core/blob/main/LICENSE). Source code, issues, and contributions: [github.com/markstrefford/constellation-core](https://github.com/markstrefford/constellation-core).
