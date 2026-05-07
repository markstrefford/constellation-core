# Concepts

## Why constellation-core

If you want to simulate something — a logistics network, a market, a power grid, an organisation, a colony of spaceships — most existing tools force a choice. On one side: rich domain-specific frameworks (logistics-only, market-only, RL-environments-only) that solve your problem if it fits the framework's mould. On the other: low-level numerical libraries where you build the simulation, the agents, the persistence, and the visualisation from scratch.

constellation-core sits in between. It gives you a generic simulation substrate — a graph of nodes and edges, an engine that drives time, an agent protocol, scenario events, persistence, and a real-time viewer — and stays out of the way of your domain. You add the rules. You add the agents. You add the analysis. The platform supplies the structure that all of those pieces plug into.

The pay-off: when your simulation outgrows its first domain, you don't rebuild the platform. The same engine that runs a global supply chain runs a stock market with no core code changes — only a new plugin.

This page explains how constellation-core is layered, what each layer is responsible for, and the rule for deciding where new code belongs. It uses a small worked example — a tick-based space simulation — to ground the abstractions.

---

## The five layers

constellation-core is structured as five layers. The bottom two are the platform. The top three are yours (or a plugin you depend on).

### Layer 1 — Engine

The engine drives time. Today, that means a tick loop: on every tick, the engine asks a plugin which phases to run, then runs each phase in order. A "phase" is a piece of plugin logic — production, pricing, decisions, snapshots — whatever the domain requires. The engine has no opinions on phase count, phase order, or phase content.

A planned event-driven engine extension will let the same core host turn-based and message-driven simulations alongside ticking ones, but as of v0.2 the loop is tick-only.

### Layer 2 — Topology

The topology layer is the structure of your simulation's universe. constellation-core provides a generic graph: nodes connected by edges. Nodes carry mutable state in a property dictionary; edges carry distance and type. The platform supplies pathfinding (Dijkstra, with optional filters by edge type and allowed node set) and the `EnvironmentState` object that the engine threads through every plugin call.

What a node *means* — a planet, a port, a market venue, a department — is decided by the layers above. The platform doesn't interpret node properties.

### Layer 3 — Domain rules

The domain rules describe what your universe does. Production. Pricing. Cargo movement. Capacity limits. Scenario shocks. This is the layer where a plugin defines its physics, its economics, its behavioural laws.

A space-economy plugin's domain rules look very different from a stock-market plugin's. But they share the same shape: each tick, the engine asks the plugin which phases to run, and the domain rules execute inside those phases.

### Layer 4 — Agentic behaviour

Agents observe a slice of the environment and choose an action. The platform defines a single protocol: `choose_action(observation: dict) -> dict`. Algorithmic agents, LLM-driven agents, and hybrid agents all conform to it.

Crucially, the *content* of the observation and the *schema* of the action are domain-defined. The plugin builds the observation (deciding what each agent sees), declares which actions are available right now, validates returned actions, and executes them.

### Layer 5 — Analysis

Whatever you do with the simulation's output: metrics, narrative reports, charts, downstream feeds. The core persists events; the analysis layer reads them and turns them into something useful for a human or a system.

### Where each layer lives

| Layer | Provided by | Code surface |
|---|---|---|
| 1. Engine | constellation-core | `constellation_core.engine` |
| 2. Topology | constellation-core | `constellation_core.topology` |
| 3. Domain rules | Your plugin | `your_plugin.run_phase()` |
| 4. Agentic behaviour | Your plugin | `your_plugin.build_observation()`, `validate_action()`, `execute_action()`, plus your `AgentDecision` classes |
| 5. Analysis | Your plugin or downstream code | reads `constellation_core.persistence` event store |

Layers 1 and 2 ship in the open-source platform. Layers 3–5 are what you write, or what a plugin you depend on writes for you. The bundled `examples/supply_chain` and `examples/stock_market` are full implementations of layers 3 and 4 against the same Layer 1 + 2 substrate.

---

## A worked example: a tiny tick-based space simulation

To make the layers concrete, here is what each one does in a small simulation. The example isn't runnable as written — for runnable code, see [Build a domain](build-a-domain.md). The point here is to show what each layer's code is *about*.

### The scenario

Three planets in a triangle: `earth`, `mars`, `belt`. A single freighter shuttles cargo between them.

- `earth` produces 5 units of cargo per tick.
- `mars` consumes 3 units per tick.
- `belt` consumes 2 units per tick.
- All three planets are connected by lanes; the freighter moves along them.
- At tick 100, an asteroid strike doubles the distance of the `earth → belt` lane. Watch the cargo balance shift to favour `mars`.

```
        [earth]
       /        \
   lane         lane
     /            \
 [mars] -- lane -- [belt]
```

### Layer 1 — Engine

You configure the engine in YAML: `ticks: 200`, the three nodes, the lanes, the freighter agent, and a `scenario_events:` block scheduling the asteroid event at tick 100. The engine reads the config, sets up state, and starts the loop. From this point on, the engine's job is to call your plugin once per tick per phase, and persist whatever events come back.

### Layer 2 — Topology

```yaml
nodes:
  - id: earth
    properties:
      cargo_stock: 100
      production_rate: 5
  - id: mars
    properties:
      cargo_stock: 50
      consumption_rate: 3
  - id: belt
    properties:
      cargo_stock: 30
      consumption_rate: 2

edges:
  - from: earth
    to: mars
    distance: 10
  - from: earth
    to: belt
    distance: 12
  - from: mars
    to: belt
    distance: 8
```

That's the entire universe. constellation-core builds a `Graph` from this, and the freighter agent will use the platform's pathfinding to decide how to move. The platform doesn't know what `cargo_stock` means — those keys are domain-defined.

### Layer 3 — Domain rules

Your plugin declares four phases:

```python
def get_tick_phases(self):
    return ["production", "consumption", "decisions", "snapshots"]
```

In `production`, every node with a `production_rate` adds that to its `cargo_stock`. In `consumption`, every node with a `consumption_rate` subtracts. In `decisions`, the engine calls each agent's `choose_action`. In `snapshots`, the plugin emits a `CargoSnapshot` event for each node so downstream consumers (the viewer, the persistence store, your analysis) can render it.

The domain rules are about ten lines of Python per phase. The asteroid event is a few more lines: when the scenario event fires, mutate the `earth → belt` edge's `distance`. The platform handles the scheduling.

### Layer 4 — Agentic behaviour

The freighter is an agent. Each tick, your plugin's `build_observation(freighter, state)` constructs the observation it sees:

```json
{
  "agent_id": "freighter_1",
  "location": "earth",
  "cargo_held": 0,
  "node_stocks": {"earth": 105, "mars": 47, "belt": 28},
  "available_actions": ["travel", "load", "wait"]
}
```

The freighter's `choose_action` returns a JSON action — `{"action": "load", "quantity": 50}` or `{"action": "travel", "destination": "mars"}`. The plugin validates the action (do you have room? is the destination reachable?) and executes it (mutate cargo, mutate location).

The decision logic is yours. A simple policy: if empty, load up at `earth`; if loaded, travel to whichever consumer has the lowest stock. A more sophisticated policy could weigh production rates, lane distances, and current stock to plan multi-tick routes — and an LLM-driven freighter receives the same observation and returns the same action shape, but generates the choice via a prompt.

### Layer 5 — Analysis

After the run, you read the event store. Plot `cargo_stock` per node over time. Identify when each consumer ran dry. Measure the impact of the asteroid event — how many ticks did `belt` spend below its consumption threshold? How much did `mars` benefit from the redirected freighter capacity?

The platform persists the events; the analysis is yours to write.

---

## What that buys you

The five-layer split is what makes constellation-core domain-agnostic. The same engine + topology that ran the space simulation above runs the bundled supply-chain example (five nodes, three agents, a Suez Canal disruption) and the bundled stock-market example (one exchange, twenty traders, an earnings surprise and a market panic). The pieces that change are layers 3, 4, and 5. Layers 1 and 2 are constant.

This is also why constellation-core can host turn-based games (planned, via the event-driven engine extension), reorganisation simulations (planned, via the visibility extension), and simulations driven by real financial data (planned, via downstream tooling) on the same base. The base doesn't need to know about any of those domains.

---

## What crosses between the layers

Three things move between core (layers 1–2) and plugin (layers 3–5) at runtime.

1. **The state object** (`EnvironmentState`). Owned by the engine, passed into every plugin call. The plugin reads it freely (`state.tick`, `state.graph`, `state.nodes`, `state.agents`) and mutates the parts the platform exposes (node properties, agent properties, agent location). Domain-only state — anything that isn't a node, an agent, or topology — lives in plugin-private attributes.
2. **The graph** (`Graph`). Built from the YAML config (or by the plugin programmatically) at startup. The engine owns it after construction. Plugins read the graph at any time and project domain information into `Node.properties` so that pathfinding can filter on it.
3. **Events.** `run_phase()` returns a list of `Event` instances. The engine collects them, persists them, and streams them to clients over SSE. Events are append-only and one-way: plugin → core → consumers. Plugins define their own event subclasses; the core never inspects payloads beyond serialisation.

Everything else — domain entities, decision algorithms, pricing math, narrative analysis — stays in the plugin. Core never sees it.

---

## Why properties are dicts

`Node.properties` and `AgentData.properties` are typed `dict[str, Any]`. This is a deliberate choice with a real trade-off.

The alternative — strongly-typed property classes per domain — would give static type-checking and IDE autocomplete, but would require the core to know about each domain. That breaks the "core is domain-agnostic" rule: the platform would either need a generic mechanism for plugins to register their own typed schemas (significant complexity) or would force each domain to fork core (no portability).

`dict[str, Any]` keeps core ignorant. Plugins read and write properties using the keys they define; type discipline is enforced inside the plugin, not by the platform. If a plugin wants stricter typing internally, it can wrap reads and writes in helper methods that validate against a Pydantic model — a pattern that costs about twenty lines per domain and stays opt-in.

---

## Where this fits in the ecosystem

A few honest distinctions against tools that occupy adjacent space.

- **Mesa, AgentPy** — mature Python frameworks for classical agent-based modelling. Excellent if your simulation is in-process, single-machine, and benefits from a rich library of pre-built schedulers and chart components. constellation-core's JSON-based agent protocol is the better starting point if your agents may be remote, LLM-driven, or distributed.
- **SimPy** — discrete-event simulation. The natural unit is "next event" rather than "next tick". constellation-core uses fixed ticks today; if your model is fundamentally event-driven, SimPy is the better fit (or wait for the planned event-driven engine extension).
- **CAMEL, AutoGen, OASIS** — multi-agent LLM frameworks. They focus on the agents and are largely agnostic about the world. constellation-core is the inverse: it focuses on the world and provides a minimal protocol for any agent — algorithmic or LLM — to plug in.
- **Gymnasium, PettingZoo** — RL environments. Formalised observation/action/reward loops for *training* learning agents. constellation-core does not enforce a reward channel and has no built-in episode/step abstraction; it is for *running* simulations with already-defined agents, not training them.

---

## The boundary rule

When deciding whether new code belongs in constellation-core or in a plugin, apply one test:

> **Could a completely different domain — a wheat market, a logistics network, a traffic model, a board game — reuse this code unchanged?**
>
> - **Yes** → it belongs in constellation-core (layer 1 or 2).
> - **No** → it belongs in a plugin (layer 3, 4, or 5).

That rule is the constitution of the platform. Everything in [the capability table above](#where-each-layer-lives) passes the test. Everything that doesn't pass — pricing math, action types, agent strategies, domain entities — lives in plugins.

When in doubt, default to the plugin side. Code can always be promoted to core later if a third domain proves the abstraction is general; code that gets prematurely added to core is much harder to remove without breaking downstream plugins.

---

## Where to go next

- **[Build a domain](build-a-domain.md)** — apply the five layers: write your own `SimulationPlugin` end-to-end, with runnable code.
- **[Plugin protocol](plugin-protocol.md)** — the full reference for the methods that span the seam, including the per-tick call sequence.
- **[Configuration](configuration.md)** — the YAML schema that initialises a topology, agents, and scenario events.
- **[Examples](examples.md)** — read the bundled supply-chain and stock-market plugins as concrete instances of the model.
