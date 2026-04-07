# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

constellation-core is a domain-agnostic simulation platform. Open source base for running multi-agent simulations across any domain. All domain logic lives in plugins — the core never interprets node properties, agent states, or action types.

## Quick Reference

```bash
# Install
pip install -e ".[dev,server]"
cd viewer && npm install

# Test
python -m pytest tests/ -v

# Run examples headless
python -m constellation_core run examples/supply_chain/config.yaml --ticks 200
python -m constellation_core run examples/stock_market/config.yaml --ticks 200

# Serve with viewer (start backend, then viewer dev server separately)
python -m constellation_core serve examples/supply_chain/config.yaml
cd viewer && npx vite  # in another terminal, proxies API to :8000
```

## Architecture

5-layer architecture. The core is domain-agnostic.

```
engine/       L1: Event loop, SimulationPlugin protocol, ScenarioEvent scheduling
topology/     L2: Graph (nodes, edges, Dijkstra pathfinding), EnvironmentState
agent/        L4: AgentData, AgentDecision protocol, ModelBackend, AgentRunner
config/       YAML loading, Pydantic schema
persistence/  StorageBackend protocol, SQLite
server/       FastAPI (SSE streaming, observe/act endpoints)
deployment/   DeploymentBackend protocol, LocalDeployment
```

Domain plugins implement `SimulationPlugin` protocol:
- `get_tick_phases()` — define what phases run each tick
- `run_phase()` — execute domain logic per phase
- `build_observation()` / `get_available_actions()` / `validate_action()` / `execute_action()` — agent interface

## Key Design Decisions

- **No domain logic in core.** No elasticity math, no trade execution, no predefined actions or agent states.
- **Properties are dicts.** `Node.properties` and `AgentData.properties` are `dict[str, float]`. The core never interprets them.
- **Actions are dicts.** The core knows actions are `dict`. Plugins validate and execute.
- **Plugin defines phases.** The engine calls `get_tick_phases()` — no hardcoded phase count.

## Examples

- `examples/supply_chain/` — Global logistics: 5 nodes, 3 agents, Suez disruption
- `examples/stock_market/` — Mini exchange: 1 node, 20 agents, herd behaviour
- `examples/reorg/` — Company restructure (design doc only, needs Tier 2 visibility layer)

## Coding Standards

- Python 3.11+, type hints throughout
- Frozen dataclasses for events, mutable dataclasses for state
- Tests mirror source layout: `tests/test_topology/`, `tests/test_engine/`, etc.
- Viewer: React + Vite + TypeScript, connects via SSE to `/api/events`

## Git Workflow

- Never use git rebase — always merge
- Never skip hooks — no `--no-verify`
