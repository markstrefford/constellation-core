# constellation-core: Tier 1 Implementation Plan (Revised)

## What Changed

The previous plan had domain-specific concepts leaking into the core: elasticity math, trade execution, specific action types (Buy/Sell/Travel), agent states (in_transit, arriving), production/consumption helpers. These belong in domain plugins, not the platform.

The core platform knows about: environments with nodes and edges, agents that observe and act, a tick loop that calls a plugin, config loading, persistence, and a viewer. That's it. Everything else is domain.

---

## Core Platform — What's In, What's Out

### IN the core (domain-agnostic)

| Module | Contents |
|---|---|
| `engine/` | Tick loop, SimulationPlugin protocol, ScenarioEvent scheduling, Simulation class |
| `topology/` | Graph (nodes, edges, pathfinding), EnvironmentState (tick, nodes, agents) |
| `agent/` | AgentData (id, location, properties dict), AgentDecision protocol, ModelBackend protocol, AgentRunner |
| `config/` | YAML loading, Pydantic schema (nodes, edges, agents, scenario_events, domain_config) |
| `persistence/` | StorageBackend protocol, SQLite implementation |
| `server/` | FastAPI app (observe, act, topology, SSE stream) |
| `deployment/` | DeploymentBackend protocol, LocalDeployment |

### OUT of the core (lives in domain plugins)

| Concept | Why it's domain-specific |
|---|---|
| Elasticity math | Not every domain has supply/demand curves. A stock market uses order books. An org restructure uses morale/productivity. |
| Trade execution (buy/sell) | Trade is a galaxy/supply-chain concept. Financial markets have bids/asks. Org restructure has budget allocation. |
| Specific action types (BuyAction, SellAction, TravelAction) | Each domain defines its own actions. The core only knows `dict` — the plugin validates. |
| Agent states (in_transit, arriving, docked) | Transport states. A stock market agent is never "in transit." An org agent might be "consulting" or "deciding." |
| Production/consumption helpers | Domain math. The core doesn't know what production means. |
| Cargo, fuel, refining | Galaxy-specific resource concepts. |

### The boundary

The core provides:
```python
class AgentData:
    id: str
    location: str          # which node
    properties: dict       # domain puts whatever it needs here
    metadata: dict         # domain puts whatever it needs here
```

The domain plugin interprets `properties["fuel"]` or `properties["portfolio_value"]` or `properties["morale"]`. The core never looks inside.

---

## SimulationPlugin Protocol (Revised)

```python
class SimulationPlugin(Protocol):
    # Setup
    def get_tick_phases(self) -> list[str]: ...
    def setup(self, state: EnvironmentState, config: dict) -> None: ...
    
    # Tick phases — the engine calls these in order
    def run_phase(self, phase: str, state: EnvironmentState, config: dict) -> list[Event]: ...
    
    # Agent interface — how agents interact with the domain
    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict: ...
    def get_available_actions(self, agent_id: str, state: EnvironmentState) -> list[str]: ...
    def validate_action(self, agent_id: str, action: dict, state: EnvironmentState) -> tuple[bool, str]: ...
    def execute_action(self, agent_id: str, action: dict, state: EnvironmentState, tick: int) -> list[Event]: ...
```

The engine's tick loop:
1. Fire scenario events for this tick
2. For each phase in `plugin.get_tick_phases()`: call `plugin.run_phase()`
3. One of those phases will be "decisions" where the plugin calls the AgentRunner
4. Increment tick

The plugin owns the phase list, the phase logic, the observation format, the action validation, and the action execution. The engine just calls them in order.

---

## Repository Structure (Revised)

```
constellation-core/
  src/
    constellation_core/
      engine/           # L1: tick loop, plugin protocol, scenarios
      topology/         # L2: graph, nodes, edges, environment state  
      agent/            # L4: AgentData, AgentDecision protocol, ModelBackend, runner
      config/           # YAML loading, Pydantic schema
      persistence/      # StorageBackend, SQLite
      server/           # FastAPI (observe, act, SSE)
      deployment/       # DeploymentBackend, LocalDeployment
  examples/
    supply_chain/       # Example 1: global logistics
    stock_market/       # Example 2: herd behaviour in markets
    reorg/              # Example 3: company restructure (coming soon)
  viewer/               # Basic React viewer
  tests/
  docs/
```

Note: no `common/` with elasticity/trade/actions. No `domain/` with helpers. Each example carries its own domain logic in its `plugin.py`.

---

## Example 1: Global Supply Chain

### The story
Raw materials ship from a port in Asia across the ocean to a port in Europe. Trucks carry them to a factory. The factory produces goods. Trucks distribute goods to retail hubs. If any link breaks, shortages cascade.

### Topology
```
[Shanghai Port] --ocean(20)--> [Rotterdam Port] --road(5)--> [Stuttgart Factory]
                                                                    |
                                                              road(3)  road(4)
                                                                    |       |
                                                            [Munich Hub] [Berlin Hub]
```

5 nodes, 4 edges (some one-directional for ocean shipping, bidirectional for road).

### Node properties
```yaml
nodes:
  - id: shanghai
    properties:
      raw_materials_stock: 500
      raw_materials_production: 20    # per tick
      price_raw: 10
    metadata:
      label: "Shanghai Port"
      type: port

  - id: rotterdam
    properties:
      raw_materials_stock: 50
      price_raw: 15                   # higher — transport cost priced in
    metadata:
      label: "Rotterdam Port"
      type: port

  - id: stuttgart
    properties:
      raw_materials_stock: 100
      finished_goods_stock: 200
      finished_goods_production: 8    # per tick, consumes raw_materials
      raw_materials_consumption: 12
      price_finished: 50
    metadata:
      label: "Stuttgart Factory"
      type: factory

  - id: munich
    properties:
      finished_goods_stock: 80
      finished_goods_consumption: 5
      price_finished: 65              # retail markup
    metadata:
      label: "Munich Distribution"
      type: retail

  - id: berlin
    properties:
      finished_goods_stock: 60
      finished_goods_consumption: 6
      price_finished: 68
    metadata:
      label: "Berlin Distribution"
      type: retail
```

### Agents
3 logistics agents:
- **ocean_freighter**: Large capacity (200), slow. Shuttles raw_materials Shanghai → Rotterdam.
- **truck_1**: Medium capacity (50), fast. Carries raw_materials Rotterdam → Stuttgart, finished_goods Stuttgart → Munich.
- **truck_2**: Medium capacity (50), fast. Carries finished_goods Stuttgart → Berlin.

### Plugin phases
`["production", "pricing", "decisions", "movement", "delivery", "consumption", "snapshots"]`

### Agent logic (algorithmic)
Simple greedy: look at destination stock levels, if low → load up and go. If already carrying cargo → deliver to destination. Return empty. The decision is based on the observation (visible node prices and stock levels).

### ScenarioEvent
- Tick 200: "Suez Canal blockage" — ocean edge distance doubles from 20 to 40 (Shanghai→Rotterdam slows dramatically)
- Watch: Rotterdam runs dry, Stuttgart's production drops, Munich/Berlin prices spike, trucks reroute if they can

### What it demonstrates
Topology-driven resource flows, cascading supply chain disruption from a single shock event, agent behaviour under constraint, the viewer showing goods moving across a global map.

---

## Example 2: Mini Stock Market

### The story
5 stocks trade on a simple exchange. 20 agents with different strategies (momentum, contrarian, random) trade each tick. The interesting finding: when too many agents follow the same momentum strategy, prices become volatile and crash. Mirrors the CONSTELLATION 27% finding — diversity of strategy matters.

### Topology
```
[Exchange]
```

1 node. The "exchange" holds all order book state. Agents don't travel — they're all "at" the exchange. The topology is trivial because the interesting dynamics are in the agent decisions, not the geography.

### Node properties
```yaml
nodes:
  - id: exchange
    properties:
      stock_a_price: 100
      stock_a_volume: 0
      stock_b_price: 50
      stock_c_price: 200
      stock_d_price: 75
      stock_e_price: 150
      # Order book state updated each tick
      total_buy_orders: 0
      total_sell_orders: 0
      market_sentiment: 0.5      # 0 = fear, 1 = greed
    metadata:
      label: "Exchange"
```

### Agents
20 traders with different strategies encoded in properties:
```yaml
agents:
  # 10 momentum traders — buy when price is rising, sell when falling
  - id: momentum_01
    starting_location: exchange
    properties:
      cash: 10000
      portfolio_value: 5000
      strategy: 1                 # 1=momentum, 2=contrarian, 3=random
      risk_tolerance: 0.7
      
  # 5 contrarian traders — buy when others sell, sell when others buy
  - id: contrarian_01
    starting_location: exchange
    properties:
      cash: 10000
      portfolio_value: 5000
      strategy: 2
      risk_tolerance: 0.5
      
  # 5 random traders — noise
  - id: random_01
    starting_location: exchange
    properties:
      cash: 10000
      portfolio_value: 5000
      strategy: 3
      risk_tolerance: 0.3
```

### Plugin phases
`["market_open", "decisions", "order_matching", "price_update", "sentiment", "snapshots"]`

- **market_open**: Reset tick's order book
- **decisions**: Agents observe prices + sentiment, submit buy/sell orders
- **order_matching**: Match buys to sells, execute trades, update agent portfolios
- **price_update**: Adjust prices based on net buy/sell pressure (simple: more buyers → price up, more sellers → price down)
- **sentiment**: Update market_sentiment based on price movements (rising prices → greed, falling → fear). This feeds back into momentum traders' decisions next tick.
- **snapshots**: Emit state for viewer

### Agent actions
```json
{"action": "buy", "stock": "stock_a", "quantity": 10}
{"action": "sell", "stock": "stock_b", "quantity": 5}
{"action": "hold"}
```

### Agent observation
```json
{
  "agent_id": "momentum_03",
  "cash": 8500,
  "portfolio": {"stock_a": 20, "stock_c": 5},
  "prices": {"stock_a": 105, "stock_b": 48, "stock_c": 210, "stock_d": 72, "stock_e": 155},
  "price_changes": {"stock_a": 0.05, "stock_b": -0.04, "stock_c": 0.02, ...},
  "sentiment": 0.65,
  "available_actions": ["buy", "sell", "hold"]
}
```

### ScenarioEvents
- Tick 100: "Earnings surprise" — stock_a price jumps 20%. Watch: momentum traders pile in, contrarians sell, price overshoots then corrects.
- Tick 300: "Market panic" — sentiment drops to 0.1. Watch: momentum traders all sell simultaneously, crash cascades, contrarians buy the dip.

### What it demonstrates
Emergent herd behaviour from simple individual strategies. The ratio of momentum vs contrarian traders determines market stability — too many followers and the system becomes fragile. This is the 27% finding in a different domain: diversity of agent strategy prevents systemic collapse.

### Viewer
Price chart lines for all 5 stocks over time. Agent portfolio values. Sentiment gauge. Buy/sell volume bars. This is the visual that will get attention — watching a market crash in real time from emergent agent behaviour.

---

## Example 3: Company Restructure (Coming Soon)

### The story
A company with 5 departments. Each department is a node with headcount, budget, productivity, and morale. Agents are department heads making decisions: hire, cut, invest in training, request budget. Internal communications flow between departments (edges). A restructuring event (AI automation) hits one department and cascades through the org.

### Topology
```
              [CEO Office]
             /      |      \
    [Engineering] [Sales] [Operations]
                    |
                [Marketing]
```

5 nodes. Edges represent reporting lines and information flow.

### Node properties
headcount, budget, productivity, morale, ai_adoption, backlog

### Agents
5 department heads. Each observes their own department's state plus limited visibility of adjacent departments (information asymmetry — the CEO sees everything, department heads see neighbours only).

### ScenarioEvents
- Tick 50: "AI automation" — engineering's ai_adoption jumps, headcount_target drops 30%
- Tick 100: "Budget reallocation" — operations budget cut, engineering budget increased
- Tick 200: "Morale crisis" — if morale below threshold in any department, attrition spikes

### Why "coming soon"
This is the SignalStrata use case. It needs the information asymmetry (visibility) layer working properly, and the agent decisions are more nuanced (policy decisions, not buy/sell). It's the right example to add when Tier 2 lands. Placeholder README with the design above ships with Tier 1.

---

## Revised Phase Plan

### Phase 1: Core Types + Topology (2 days)
- `topology/graph.py` — Graph, Edge, pathfinding (ported from galaxy/model.py, stripped of galaxy naming)
- `topology/state.py` — Node (id, properties dict, metadata dict), EnvironmentState (tick, graph, nodes, agents)
- `agent/model.py` — AgentData (id, location, properties dict, metadata dict). No predefined states, no cargo, no fuel. Domain puts what it needs in properties.
- `engine/plugin.py` — SimulationPlugin protocol
- Basic types only. No events, no config loading yet.
- **Tests**: Graph pathfinding, Node creation, AgentData creation

### Phase 2: Engine (2-3 days)
- `engine/tick.py` — Generic tick loop calling plugin phases
- `engine/scenario.py` — ScenarioEvent scheduling
- `engine/simulation.py` — Simulation class (setup, run, run_streaming)
- Events system (simple frozen dataclasses, domain adds its own event types)
- **Tests**: Mock plugin with 2 phases, scenario events fire at correct ticks, full run with trivial plugin

### Phase 3: Config + Persistence (1-2 days)
- `config/schema.py` — Pydantic models (SimulationConfig, NodeConfig, EdgeConfig, AgentConfig, ScenarioEventConfig)
- `config/loader.py` — YAML loading
- `persistence/protocol.py` + `persistence/sqlite.py` — Event storage
- `deployment/local.py` — LocalDeployment (in-process)
- Public API: `from constellation_core import Simulation`
- CLI: `python -m constellation_core run config.yaml`
- **Tests**: YAML roundtrip, SQLite write/read

### Phase 4: Supply Chain Example (2-3 days)
- `examples/supply_chain/plugin.py` — SupplyChainPlugin implementing SimulationPlugin
- `examples/supply_chain/agents.py` — GreedyLogisticsAgent (algorithmic)
- `examples/supply_chain/config.yaml` — 5 nodes, 3 agents, Suez blockage event
- All the domain-specific logic (production, consumption, pricing, movement, cargo) lives here, not in core
- **Tests**: Runs 500 ticks, agents move cargo, prices respond to shortage, Suez event causes disruption

### Phase 5: Stock Market Example (2-3 days)
- `examples/stock_market/plugin.py` — StockMarketPlugin
- `examples/stock_market/agents.py` — MomentumTrader, ContrarianTrader, RandomTrader
- `examples/stock_market/config.yaml` — 1 node (exchange), 20 agents, earnings surprise + panic events
- Domain logic: order matching, price impact, sentiment feedback loop
- **Tests**: Runs 500 ticks, prices move, herd behaviour produces identifiable crash pattern

### Phase 6: Server + Viewer (2-3 days)
- `server/app.py` — FastAPI with SSE, observe/act endpoints
- `viewer/` — React app: TopologyMap, NodeDetail, AgentList, TickBar
- Viewer works with both examples (supply chain shows geography, stock market shows price charts)
- **Tests**: Server starts, SSE stream works, viewer renders

### Phase 7: Reorg Placeholder + Polish (1-2 days)
- `examples/reorg/README.md` — Full design doc (the spec above), no code yet
- README.md with hero GIF, quickstart, architecture diagram
- CLAUDE.md, Makefile, LICENSE (Apache 2.0)

**Total: 12-18 days**

---

## Key Decisions

**No common/ directory.** There's no shared domain logic. Each example carries its own. If patterns emerge across examples, they get extracted later, not preemptively.

**No predefined action types.** The core knows actions are `dict`. The supply chain plugin validates `{"action": "load", "goods": "raw_materials", "quantity": 50}`. The stock market plugin validates `{"action": "buy", "stock": "stock_a", "quantity": 10}`. Different domains, different actions.

**No predefined agent states.** AgentData.properties is a dict. The supply chain plugin puts `status: "in_transit"` in there. The stock market plugin puts `position: "long"`. The core doesn't care.

**The stock market proves generality.** If the same platform runs a logistics simulation AND a financial market simulation, the architecture is genuinely domain-agnostic. Two radically different domains on one engine.

**The reorg example is the commercial bridge.** It's designed to be the SignalStrata use case — company data in, simulation out. Shipping it as a "coming soon" with a full design doc creates the narrative without requiring the visibility layer that Tier 2 delivers.
