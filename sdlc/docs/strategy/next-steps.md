---
id: next-steps
kind: strategy
project: constellation-core
verified-on: 2026-05-06
sources: []
tags: [strategy, roadmap, known-issues]
---

# Next Steps

## Known Issues (Tier 1)

### Supply chain economy dies
The consumption rates still outpace what the logistics network can deliver. After ~150 ticks, stocks hit zero and stay there. Needs:
- Further rebalancing of production/consumption/capacity ratios
- Possibly demand-responsive production (produce more when prices high)
- More couriers or faster speeds to match throughput to demand
- Consider adding a second ocean freighter or increasing capacity

### Tick counter off-by-one
The viewer shows tick N but the snapshot may be from tick N-1 due to the engine incrementing before the snapshot is emitted. Minor but visible.

### Viewer improvements needed
- Node sizes could reflect stock levels (visual indicator of health)
- Edge thickness could reflect traffic/usage
- Courier labels overlap when multiple couriers on same edge
- No event log or activity feed in the viewer
- Stock market example needs a different view (price charts, not topology map)

---

## Tier 2: Platform-grade

From the spec (`docs/CONSTELLATION-CORE-SPEC.md`):

### Information asymmetry (visibility layer)
The highest-value addition. Each agent's observation is filtered through a `VisibilityRule` before being sent. The domain defines the filter.
- `OmniscientVisibility` (default) — agents see everything
- `LocalVisibility` — agents see their node + neighbours
- `HierarchicalVisibility` — CEO sees all, department heads see neighbours only
- **Needed for**: the company restructure example (reorg)
- **Effort**: 3-5 days

### ModelBackend multi-provider support
Currently just a protocol stub + DummyBackend. Need real implementations:
- Anthropic (Claude)
- OpenAI
- Ollama (local)
- Semaphore-gated async inference for scaling multiple LLM agents
- **Effort**: 1-2 days per provider, 2-3 days for async scaling

### Company restructure example (reorg)
Design doc is in `examples/reorg/README.md`. Needs the visibility layer to be meaningful. 5 departments, agents as department heads, AI automation and budget reallocation shocks.
- **Blocked by**: visibility layer
- **Effort**: 2-3 days once visibility is done

### "Build your own domain" guide
Step-by-step documentation for creating a new domain plugin from scratch. The README has a basic example but needs a full walkthrough with testing, viewer integration, and deployment.

---

## Tier 3: Commercial-grade

### ModalDeployment backend (closed)
Run simulations on Modal cloud compute instead of localhost. The `DeploymentBackend` protocol is defined; needs a Modal implementation.

### SignalStrata integration
Map real company financial data to simulation parameters. Parameter mapping uses ratios not absolutes — map relative to tuned baselines.

### LLM-controlled agent policy decisions
Agents that use LLM reasoning to make complex decisions (not just buy/sell). Needs ModelBackend + visibility layer working well.

### Multi-scenario batch runner
Run N variations of a scenario, compare outcomes. Useful for stress-testing and sensitivity analysis.

### Agentic blueprint export
The commercial endpoint: tested agent configurations as a deliverable. Prompts, decision logic, interaction patterns — 50-70% ready to deploy.

---

## Technical debt

- **No `common/` shared library** — this is intentional (each domain carries its own logic) but if patterns emerge across 3+ domains, extract shared utilities
- **Plugin discovery** — currently hardcoded in `server/app.py` (`if domain == "supply_chain"`). Need proper entry point or registry-based discovery
- **Tests for server** — no automated tests for the FastAPI server or SSE streaming
- **Viewer build integration** — viewer must be built separately (`cd viewer && npx vite build`). Could integrate into `make serve` or add a dev proxy mode
- **No CI/CD** — no GitHub Actions for tests, linting, or builds yet
