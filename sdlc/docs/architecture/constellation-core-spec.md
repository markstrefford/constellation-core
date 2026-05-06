# constellation-core: Implementation Spec

## What This Is

A new repo, built from scratch. Not a fork, not a branch of CONSTELLATION. The current CONSTELLATION monorepo stays untouched. BotArena keeps running. Nothing breaks.

constellation-core is the base platform, built clean with the right architecture from day one. Code is ported over from the CONSTELLATION monorepo piece by piece, placed into the correct layer as it arrives. No inherited boundary violations, no refactoring debt.

---

## The Base Platform

Three concepts. That's it.

```python
from constellation_core import Environment, Agent, run

env = Environment.from_config("scenario.yaml")
agents = Agent.from_config("agents.yaml")
results = run(env, agents, ticks=500)
```

**Environment**: A set of nodes and edges. Nodes have properties (stocks, production rates, consumption rates, wealth). Edges have properties (distance, cost). The environment ticks forward, applying rules each step. The environment is the shared state — it lives on a server and agents talk to it over API/JSON.

**Agent**: Something that observes part of the environment, makes a decision, and acts. Agents can be algorithmic (Python functions) or LLM-driven (via any model backend). Agents don't share memory. They get an observation (JSON), return an action (JSON). They can run anywhere — same machine, different machine, different continent.

**Config**: YAML or JSON defining the environment topology, agent profiles, business rules, and simulation parameters. Everything domain-specific lives in config and rule modules, not in the engine.

Business rules, metrics, and what each agent gets to see are all domain config — not platform code. The platform provides the hooks; the domain fills them in.

---

## The Layered Architecture

From the original 5-layer model, informed by the WS3 codebase audit of what worked and what was tangled:

```
Layer 5: Analysis & Reporting
Layer 4: Agent Framework (agents sit on top of domain rules)
Layer 3: Domain Rules (this is where the value lives)
Layer 2: Topology & Environment
Layer 1: Simulation Engine
```

**Layer 1 — Simulation Engine**: The tick loop. A plain `for` loop (no SimPy). The engine calls into a domain plugin each tick. The domain plugin defines what phases run and in what order — there is no fixed number of phases in the engine. The galaxy economy has 8 phases (production, pricing, decisions, movement, trading, consumption, treasury, snapshots). A supply chain domain might have 4. A company reorganisation might have 6. The engine provides the loop; the domain provides the content.

**Layer 2 — Topology & Environment** (`topology/`, not `galaxy/` — galaxy is a domain concept): Nodes, edges, connectivity, pathfinding. Generic graph structure. Also includes the environment API that agents call over HTTP/JSON to observe state and submit actions. The "galaxy" with planets and shipping lanes is a domain concept built on top of this generic topology.

**Layer 3 — Domain Rules**: This is everything specific to a scenario, and agents depend on it. For the galaxy economy: planets, couriers, food/fuel/refining, supply/demand curves, treasury management, shortage premiums, asymmetric smoothing. For a supply chain scenario: factories, transport, parts, assembly. For a Block-style company reorganisation: business units, headcount costs, productivity, restructuring charges. The domain implements a `SimulationPlugin` protocol that the engine calls. The domain also defines what actions are valid, what observations agents receive, and how actions are validated and executed.

**Layer 4 — Agent Framework**: Agent registration, decision protocol, action types, movement. Agents sit on top of domain rules because they need them — the domain tells agents what's possible, what's visible, and whether an action is valid. The decision protocol is the contract: agent receives an observation (JSON), returns an action (JSON). LLM integration via a lightweight ModelBackend protocol (WS1 recommendation — ~50 lines, not a framework dependency).

```json
{
  "agent_id": "courier_1",
  "location": "refiner",
  "cargo": {"ore_refined": 15},
  "wealth": 420,
  "fuel": 80,
  "visible_nodes": {
    "refiner": {"prices": {"ore_refined": 5, "food": 12}, "stocks": {"ore_refined": 200}},
    "city": {"prices": {"ore_refined": 18, "food": 3}, "stocks": {"ore_refined": 10}}
  },
  "available_actions": ["travel", "buy", "sell", "wait", "refuel"]
}
```

The agent returns:

```json
{
  "action": "travel",
  "destination": "city"
}
```

Layer 3 then validates and executes: does the agent have enough fuel? Is the route valid? Update the environment state.

**Important**: The agent needs enough domain awareness to make sensible decisions, otherwise Layer 3 will reject everything. This is handled two ways. First, `available_actions` in the observation tells the agent what it can do right now (you can't sell if you have no cargo). Second, the agent's decision logic — whether algorithmic or LLM-driven — needs to understand the domain it's operating in. For algorithmic agents, that's baked into the code. For LLM agents, that's the skill file / system prompt that explains the domain rules. The platform provides the observation with enough context for the agent to act sensibly; the domain provides the agent's understanding of what those actions mean.

**Layer 5 — Analysis & Reporting**: Metric collection, output formatting, narrative generation. Generic framework in the base platform; domain-specific analysis in the plugin.

### What goes where

| Base Platform (open source) | Domain Plugin (closed/proprietary) |
|---|---|
| Tick loop + plugin interface | SpaceEconomyPlugin implementation |
| Node/edge topology + pathfinding (`topology/`) | Galaxy configs with 20+ planets |
| Agent protocol (observe → decide → act) with available_actions | ProfitSeekerDecision (300+ lines of tuned heuristics) |
| ModelBackend protocol (LLM abstraction) | Tuned elasticity constants, shortage premiums, smoothing |
| Action type base classes | Treasury injection calibration |
| Generic metric collection | Full economic narrator |
| Persistence protocol + SQLite | BotArena platform (lobby, scoring, leaderboard) |
| Basic viewer (React real-time visualisation, SSE rendering) | Full BotArena viewer (auth, lobby, leaderboard) |
| Simplified example domains | SignalStrata integration |
| LocalDeployment backend | ModalDeployment backend |

---

## Information Asymmetry

What each agent gets to see is domain config, not platform code.

The platform provides the hook: each agent's observation is filtered through a visibility function before being sent. The domain defines the filter. In the galaxy economy, a local courier sees local prices but not galactic ones. In a Block scenario, the board sees the automation strategy, middle management sees the hiring freeze. In BotArena, current agents see everything (omniscient mode — the default, preserving backward compatibility).

WS1 identified this as the highest-value addition. Implementation is a `MarketVisibility` layer (5-8 days per WS1). But the key insight is that it's a configurable rule, not a platform feature. The platform just needs to support filtered observations.

```python
# Platform provides the hook
class VisibilityRule(Protocol):
    def filter_observation(self, agent_id: str, full_state: dict) -> dict: ...

# Domain provides the implementation
class OmniscientVisibility:
    """BotArena default — agents see everything."""
    def filter_observation(self, agent_id: str, full_state: dict) -> dict:
        return full_state

class HierarchicalVisibility:
    """Block scenario — board sees more than middle management."""
    def filter_observation(self, agent_id: str, full_state: dict) -> dict:
        role = self.agent_roles[agent_id]
        if role == "board": return full_state
        if role == "management": return self._filter_strategic(full_state)
        return self._filter_operational(full_state)
```

---

## Skills vs Code

Where's the line between a CLAUDE.md-style skill file that shapes agent reasoning and logic baked into Python?

This is a real question but not a step 1 question. For now, the split is:

- **Code**: The simulation engine, the tick loop, the economic rules (production, consumption, pricing, trade execution). These are deterministic and must be reliable.
- **Skills/prompts**: How an LLM-driven agent interprets its observation and decides what to do. This is the agent's "brain" and can be defined in markdown/prompt templates loaded from config.
- **The boundary**: The agent receives a structured observation (JSON). It returns a structured action (JSON). Everything between those two points could be code, could be an LLM with a skill file, could be a hybrid. The platform doesn't care.

Investigate properly when the base platform is stable. For now, the decision protocol is the contract.

---

## BotArena

BotArena stays on the current CONSTELLATION monorepo. Untouched. Games 1 and 2 run as-is. No refactoring, no risk.

Game 3 onward could run on constellation-core with the SpaceEconomyPlugin imported from the closed commercial layer. At that point, Game 3 is just a different set of rules and agents plugged into the same platform.

The monorepo (with arena/, production configs, tuned parameters) remains private. constellation-core is a completely separate repo.

---

## ARIA

Same base platform. Different domain plugin. The agents and business rules are about trust, governance, and multi-agent assurance rather than economic trading. The base platform is open-sourced, satisfying ARIA's open-source requirements. The proprietary Reimagined Industries work sits on top as a closed plugin.

This is the model: **open-source base platform + closed domain-specific plugins = multiple commercial applications from one foundation.**

---

## Example Domains (Open Source)

Three example rule sets that ship with the base platform. Simple enough to demonstrate capability. Not enough to replicate the production economy.

### 1. Two-Port Shipping Lane
Simplest possible scenario. Two nodes, one agent. The agent shuttles goods between ports to keep both alive. Demonstrates: tick loop, agent decisions, supply/demand basics.

### 2. Three-Node Supply Chain (Miner → Refiner → City)
From WS4. Three nodes, two agents, three resources. Demonstrates: topology, refining chains, agent trade decisions, supply chain dependencies, emergent behaviour from disruption.

```yaml
nodes:
  - id: miner
    production: {ore_raw: 10}
    consumption: {food: 3}
  - id: refiner
    production: {ore_refined: 8}
    consumption: {ore_raw: 10, food: 2}
  - id: city
    production: {food: 12}
    consumption: {ore_refined: 6}
```

### 3. Company Reorganisation (Block-style)
From WS2. Three-four nodes representing business units and competitors. Demonstrates: scenario shocks (mid-simulation parameter changes), competitive dynamics, the SignalStrata use case.

This one proves that the platform isn't just a space game. It's an economic simulation engine that can model real-world scenarios.

---

## The End Goal: Agentic Blueprints

This is where the real commercial value lands.

You simulate an organisation's structure. You configure agents representing business units, teams, functions. You plug in rules derived from real financial data (SignalStrata). You run the simulation, stress-test it, debug it.

The output isn't just a report. It's a **tested agent configuration** — an agentic blueprint that's already been through a simulated trial run. The prompts, the decision logic, the interaction patterns. 50-70% ready to deploy in the real world.

That's better than starting from scratch. That's what a PE operating partner or transformation programme would pay for. Not "here's what we think will happen" but "here's a working agent specification that we've already stress-tested against an economic model of your company."

The base platform is the engine that makes this possible. The domain plugins are the proprietary IP. The agentic blueprints are the deliverable.

---

## Implementation Approach

### Fresh start, informed by workstream findings

constellation-core is built from scratch with the right architecture from day one. The four workstream reports are reference material — they tell us what patterns to adopt, what to avoid, and where the hard problems are. But we're not refactoring the existing monorepo. We're building clean and porting code over as needed.

**WS1 (CAMEL/OASIS)**: Don't adopt any framework as a dependency. Adapt patterns only. Key patterns: ModelBackend protocol (~50 lines), semaphore-gated async inference, visibility/recommendation layer concept, declarative agent profile generation. All build-your-own.

**WS2 (SignalStrata scenarios)**: Build the ScenarioEvent system (mid-simulation shocks) into the engine from day one — it's a few lines in the tick loop. Parameter mapping from real financials uses ratios not absolutes — map relative to tuned baselines. Block worked example is fully specified and ready to implement as an example domain.

**WS3 (Generalisation)**: The boundary violations in the existing monorepo don't apply — we're not inheriting them. But the layer map and interface definitions are the blueprint for the new architecture. The `SimulationPlugin` protocol, `VisibilityRule`, `AgentContext`, and clean layer separation are built in from the start.

**WS4 (Open source)**: Apache 2.0 license. The viewer is the strongest demo asset — include a basic version in open source that shows the real-time visualisation pattern. Separate repo from the monorepo.

### What gets ported from the CONSTELLATION monorepo

| Port from monorepo | Into layer | Notes |
|---|---|---|
| Tick loop logic (not the 14 imports) | L1: Engine | Rewrite clean, plugin calls instead of direct imports |
| Elasticity math (`common/elasticity.py`) | L1: Engine (shared math) | Generic, not domain-specific |
| Graph model + pathfinding (`galaxy/model.py`) | L2: Topology | Rename, remove galaxy-specific naming |
| Persistence protocol + SQLite (`persistence/`) | L1: Infrastructure | Clean as-is per WS3 |
| Event structure (`common/events.py`) | L1: Engine | Clean as-is |
| Action base classes (`common/actions.py`) | L3: Agent | Clean as-is |
| Viewer (React) | Viewer | Basic version — strip BotArena-specific auth/lobby, keep SSE rendering |
| Narrator pattern (`analysis/narrator.py`) | L5: Analysis | Port the pattern, not the domain-specific content |

What does NOT get ported: ProfitSeekerDecision, tuned elasticity constants, shortage premiums, asymmetric smoothing, treasury injection calibration, production galaxy configs, BotArena platform code. These stay in the closed monorepo.

---

## Deployment Model

**Open-source (constellation-core)**: Local-only. Run everything on your laptop. `python run.py` starts the engine, the viewer connects to localhost. No cloud dependencies. This is the default experience for anyone who clones the repo.

**Commercial (closed plugins)**: Pluggable deployment architecture. The current BotArena pattern (central server orchestrates, Modal spins up simulation runs) is one deployment backend. The platform defines a deployment interface; the commercial layer implements it for Modal, RunPod, or whatever cloud compute is appropriate.

This doesn't need to be complex. The interface is roughly:

```python
class DeploymentBackend(Protocol):
    async def run_simulation(self, config: dict) -> SimulationHandle: ...
    async def get_status(self, handle: SimulationHandle) -> str: ...
    async def stream_events(self, handle: SimulationHandle) -> AsyncIterator[Event]: ...

class LocalDeployment:
    """Default — runs in-process. Ships with open source."""
    async def run_simulation(self, config: dict) -> SimulationHandle:
        sim = Simulation(config)
        sim.setup()
        # Run in background thread/process
        ...

class ModalDeployment:
    """Commercial — runs on Modal. Closed source."""
    async def run_simulation(self, config: dict) -> SimulationHandle:
        # Spin up Modal job, return handle
        ...
```

The open-source repo ships with `LocalDeployment` only. `ModalDeployment` lives in the closed commercial layer.

---

## Viewer

A basic version of the React viewer ships with constellation-core (open source). It shows the pattern: nodes on a graph, agents moving between them, stock levels changing, prices updating, all in real time via SSE.

The BotArena-specific code (authentication, lobby integration, leaderboard) is stripped out. What remains is the core rendering: topology visualisation + real-time state updates. This is the single strongest demo asset — most simulation frameworks are headless. This one looks good. That's what gets stars.

The full BotArena viewer stays in the private monorepo.

---

### Delivery tiers

**Tier 1 — Demo-grade (10-15 days)**
Get a working platform with examples and get the repo live.

| Step | Effort | Depends On |
|------|--------|-----------|
| Create constellation-core repo with clean layer structure | 1 day | — |
| Build engine (tick loop + plugin protocol + ScenarioEvent) | 3-4 days | Repo structure |
| Build topology layer (nodes, edges, pathfinding — ported from galaxy/) | 1-2 days | Engine |
| Build agent framework (observation/action protocol, available_actions) | 2-3 days | Engine + topology |
| Port and strip viewer (remove BotArena specifics, keep SSE rendering) | 1-2 days | — |
| Build 3-node supply chain example domain | 2-3 days | All layers |
| Build Block scenario example (with ScenarioEvent shock) | 1-2 days | All layers + ScenarioEvent |
| README with GIF, quickstart, live demo link | 1 day | Examples working |
| Deploy live demo | 0.5 day | Viewer + examples |

**Tier 2 — Platform-grade (7-12 days after Tier 1)**
Extensibility, visibility, and the "build your own domain" story.

| Step | Effort | Depends On |
|------|--------|-----------|
| Information Visibility layer (filtered observations per agent) | 3-5 days | Tier 1 |
| ModelBackend protocol + multi-provider support (Anthropic, OpenAI, Ollama) | 1-2 days | — |
| Semaphore-gated async inference for scaling | 2-3 days | ModelBackend |
| "Build your own domain" guide | 2 days | Tier 1 stable |

**Tier 3 — Commercial-grade (15-25 days after Tier 2)**
SignalStrata integration, deployment scaling, enterprise tooling.

| Step | Effort | Depends On |
|------|--------|-----------|
| ModalDeployment backend (commercial, closed) | 3-5 days | Deployment protocol |
| SignalStrata → scenario config generator | 3-5 days | ScenarioEvent + SignalStrata schema |
| LLM-controlled agent policy decisions | 3-5 days | ModelBackend + visibility |
| Multi-scenario batch runner (run N variations, compare) | 2-3 days | ScenarioEvent |
| Automated comparison narratives with business framing | 2-3 days | Analysis framework |
| Agentic blueprint export (tested agent configs as deliverable) | 3-5 days | All above |

### Recommended sequence

Tier 1 first. Ship the repo. Get attention. Prove the model.

The Block example demonstrates the SignalStrata→CONSTELLATION thesis as a content piece. Publish it alongside the repo launch.

Tier 2 when you need real extensibility — either for ARIA (different domain plugin), community contributions, or LLM-driven agents at scale.

Tier 3 when you have a customer or funded project that needs it. The agentic blueprint export is the commercial endpoint.

---

## Constraints

- **New repo, built from scratch.** Code ported from monorepo piece by piece into correct layers. BotArena stays untouched.
- **Distributed agents.** All agent ↔ environment communication over API/JSON. No shared filesystem, no shared database, no in-process memory sharing.
- **BotArena backward compatibility.** Current monorepo unchanged. Game 3+ migration to constellation-core is optional and future.
- **Licensing.** constellation-core is Apache 2.0. Domain plugins are proprietary. No CAMEL/OASIS code adopted as dependencies (patterns only). No MiroFish code referenced (AGPL).
- **Domain-determined tick phases.** The engine doesn't hardcode phase count or order. The domain plugin defines what happens each tick.
- **Agent domain awareness.** Agents must receive enough context (available_actions, domain-relevant observation data) to make valid decisions. The platform provides the delivery mechanism; the domain provides the content.
- **Local-first open source.** The open-source version runs entirely on localhost. Cloud deployment is a pluggable commercial layer.
