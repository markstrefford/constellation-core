# Constellation

**Build, evaluate, and stress-test multi-agent systems.**

Constellation is a domain-agnostic platform for running large-scale multi-agent simulations. It allows you to define an environment as a graph, drop in agents (algorithmic or LLM-driven), and observe how their individual decisions aggregate into systemic behavior.

## Why Constellation?

Most agent frameworks focus on the "vertical" stack: how a single agent thinks, uses tools, and completes a task. Constellation focuses on the "horizontal" stack: **how hundreds of agents interact within a shared environment.**

| Feature | Individual Agent Frameworks (e.g., LangChain) | Constellation |
|---------|----------------------------------------------|---------------|
| **Focus** | Task completion, tool use, reasoning. | Systemic behavior, emergent phenomena, risk. |
| **Environment** | Usually a static API or a single database. | A dynamic graph-based world with its own physics. |
| **Interaction** | Sequential or small-group orchestration. | Massively parallel agents competing/collaborating. |
| **Goal** | Get the "right" answer from one agent. | Understand how the *system* responds to shocks. |

### Key Capabilities

- **Domain-Agnostic Core:** The engine knows about graphs and ticks; your plugin defines the physics (prices, cargo, sentiment, etc.).
- **Scenario Shocks:** Inject events mid-simulation—like a supply chain disruption or a market crash—to see how your agents adapt.
- **Agent Agnostic:** Mix simple heuristic bots with state-of-the-art LLM agents in the same environment.
- **Real-Time Visibility:** Use the React-based viewer to watch simulations unfold and track system-level metrics in real-time.

---

## Where to start?

- **[Getting started](getting-started.md)** — Install and run your first simulation in 5 minutes.
- **[Concepts](concepts.md)** — Learn about the core-plugin split and the simulation loop.
- **[Build a domain](build-a-domain.md)** — Step-by-step guide to creating your own simulation.
- **[Examples](examples.md)** — Explore the built-in Supply Chain and Stock Market simulations.

---

## Project Status

Constellation is currently in **Alpha (v0.2.1)**. It is being used to research systemic risk in autonomous systems.

The project is open source under the [Apache 2.0 license](https://github.com/markstrefford/constellation-core/blob/main/LICENSE). We welcome contributions from researchers and engineers interested in the frontier of multi-agent systems.
