# Core Concepts

Constellation is built on a "thin core, thick plugin" philosophy. This ensures the platform remains domain-agnostic while allowing for complex, specialized simulations.

## 1. The Core vs. The Plugin

The most important concept in Constellation is the separation of concerns between the engine and the domain.

### The Engine (Core)
The engine is the "clock" and the "map." It handles:
- **The Graph:** Managing nodes and edges.
- **The Event Loop:** Advancing time (ticks) and running phases.
- **Agent Orchestration:** Passing observations to agents and collecting their actions.
- **Scenario Scheduling:** Triggering external shocks at specific times.
- **Persistence:** Saving events to a database.

### The Plugin (Domain)
The plugin is the "physics." It defines:
- **Phases:** What happens during a tick (e.g., "production", "pricing", "consumption").
- **State Mutation:** How node and agent properties change over time.
- **Agent Logic:** What an agent "sees" (observations) and what it can "do" (actions).

---

## 2. The Simulation Loop (Ticks and Phases)

Time in Constellation is discrete, measured in **ticks**. Each tick consists of a series of **phases** defined by the plugin.

A typical tick might look like this:
1. **Scenario Phase:** The engine applies any scheduled shocks (e.g., "Earthquake at Node A").
2. **Physics Phase:** The plugin updates world state (e.g., "Crops grow by 5 units").
3. **Decision Phase:** Agents receive observations and return actions.
4. **Action Phase:** The plugin executes the agents' chosen actions.
5. **Snapshot Phase:** The engine captures the state for the viewer.

---

## 3. The Graph (Topology)

The world is a directed graph of **Nodes** and **Edges**.

- **Nodes:** Have a unique ID, metadata (labels, types), and `properties`. Properties are a dictionary of floats where all your domain data (wealth, stock, temperature) lives.
- **Edges:** Connect nodes and have a `distance`. The engine provides built-in Dijkstra pathfinding so agents can navigate the graph without the plugin needing to handle geometry.

---

## 4. Agents

Agents are entities that live on the graph.

- **Identity:** Every agent has a location (node ID).
- **Protocol:** Agents follow a simple loop: `Observation -> Action`.
- **Agnosticism:** The engine doesn't care if an agent is a 5-line Python script or a call to GPT-4. As long as it implements the `AgentDecision` protocol, it can participate.

---

## 5. Events

Everything that happens in Constellation is an **Event**.
- Production is an event.
- Movement is an event.
- Price changes are events.

This event-driven architecture allows for perfect replayability, easy debugging, and real-time streaming to the viewer.

---

## Why this architecture?

By keeping the core domain-agnostic, we can use the exact same engine to simulate:
- **Logistics:** Where nodes are warehouses and agents are trucks.
- **Finance:** Where nodes are exchanges and agents are traders.
- **Sociology:** Where nodes are cities and agents are citizens.

---

- **[Next: Build a Domain](build-a-domain.md)**
- **[Back to Home](index.md)**
