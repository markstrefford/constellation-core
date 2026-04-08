"""Supply chain domain plugin — global logistics simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from constellation_core.engine.events import Event, ScenarioEvent
from constellation_core.topology.graph import Edge
from constellation_core.topology.state import EnvironmentState, Node


# --- Domain events ---


@dataclass(frozen=True)
class ProductionEvent(Event):
    kind: str = "PRODUCTION"
    node_id: str = ""
    resource: str = ""
    amount: float = 0


@dataclass(frozen=True)
class ConsumptionEvent(Event):
    kind: str = "CONSUMPTION"
    node_id: str = ""
    resource: str = ""
    amount: float = 0
    rationing: float = 1.0  # 1.0 = full, <1 = rationed


@dataclass(frozen=True)
class PriceUpdateEvent(Event):
    kind: str = "PRICE_UPDATE"
    node_id: str = ""
    resource: str = ""
    old_price: float = 0
    new_price: float = 0


@dataclass(frozen=True)
class CargoLoadEvent(Event):
    kind: str = "CARGO_LOAD"
    agent_id: str = ""
    node_id: str = ""
    resource: str = ""
    quantity: float = 0


@dataclass(frozen=True)
class CargoDeliverEvent(Event):
    kind: str = "CARGO_DELIVER"
    agent_id: str = ""
    node_id: str = ""
    resource: str = ""
    quantity: float = 0


@dataclass(frozen=True)
class AgentMoveEvent(Event):
    kind: str = "AGENT_MOVE"
    agent_id: str = ""
    from_node: str = ""
    to_node: str = ""
    eta: int = 0


@dataclass(frozen=True)
class AgentArriveEvent(Event):
    kind: str = "AGENT_ARRIVE"
    agent_id: str = ""
    node_id: str = ""


@dataclass(frozen=True)
class ShortageEvent(Event):
    kind: str = "SHORTAGE"
    node_id: str = ""
    resource: str = ""
    needed: float = 0
    available: float = 0


@dataclass(frozen=True)
class SnapshotEvent(Event):
    kind: str = "SNAPSHOT"
    nodes: dict = field(default_factory=dict)
    agents: dict = field(default_factory=dict)


# --- Helpers ---


def _elasticity_multiplier(current: float, target: float, elasticity: float = 1.0) -> float:
    """Price/production scaling: e^(elasticity * (1 - current/target))."""
    if target <= 0:
        return 1.0
    ratio = max(0.2, min(current / target, 5.0))
    return math.exp(elasticity * (1 - ratio))


def _consumption_ratio(stock: float, rate: float, critical_ticks: float = 10.0) -> float:
    """
    Elastic consumption: when stock is low relative to consumption,
    consumption throttles smoothly rather than cliff-edging to zero.

    Returns a multiplier in [0, 1].
    - Stock >= critical threshold: consume at full rate (1.0)
    - Stock approaching zero: consumption drops toward 0
    """
    if rate <= 0:
        return 1.0
    critical_stock = rate * critical_ticks
    if stock >= critical_stock:
        return 1.0
    if stock <= 0:
        return 0.0
    # Smooth curve: (stock / critical) ^ 0.5 — bends gently
    return (stock / critical_stock) ** 0.5


# --- Plugin ---


class SupplyChainPlugin:
    """
    Global logistics simulation.

    Nodes are ports, factories, and retail hubs. Couriers (agents) move
    cargo between them. Production, consumption, and pricing are all
    domain logic living here, not in the core.
    """

    def get_tick_phases(self) -> list[str]:
        return [
            "scenario",
            "production",
            "pricing",
            "decisions",
            "movement",
            "consumption",
            "snapshots",
        ]

    def setup(self, state: EnvironmentState, config: dict[str, Any]) -> None:
        for agent in state.agents.values():
            agent.properties.setdefault("cargo_quantity", 0)
            agent.properties.setdefault("cargo_capacity", 50)
            agent.properties.setdefault("speed", 1)
            agent.properties.setdefault("eta", 0)
            agent.properties.setdefault("eta_total", 0)
            agent.properties.setdefault("status", 0)  # 0=idle, 1=in_transit
            agent.metadata.setdefault("destination", "")
            agent.metadata.setdefault("origin", "")
            # Direction: 0 = outbound (toward end of route), 1 = return (toward start)
            agent.metadata.setdefault("direction", 0)

        self._pending_scenarios: list[ScenarioEvent] = []

    def run_phase(
        self,
        phase: str,
        state: EnvironmentState,
        config: dict[str, Any],
    ) -> list[Event]:
        if phase == "scenario":
            return self._run_scenario(state, config)
        elif phase == "production":
            return self._run_production(state, config)
        elif phase == "pricing":
            return self._run_pricing(state, config)
        elif phase == "decisions":
            return self._run_decisions(state, config)
        elif phase == "movement":
            return self._run_movement(state, config)
        elif phase == "consumption":
            return self._run_consumption(state, config)
        elif phase == "snapshots":
            return self._run_snapshots(state)
        return []

    def _run_scenario(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        for se in self._pending_scenarios:
            handle_scenario_event(se, state)
        self._pending_scenarios.clear()
        return []

    def notify_scenario_event(self, event: ScenarioEvent) -> None:
        self._pending_scenarios.append(event)

    def _run_production(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick

        for node in state.nodes.values():
            # Raw materials production (ports/mines)
            rate = node.properties.get("raw_materials_production", 0)
            if rate > 0:
                node.properties["raw_materials_stock"] = (
                    node.properties.get("raw_materials_stock", 0) + rate
                )
                events.append(ProductionEvent(
                    tick=tick, node_id=node.id, resource="raw_materials", amount=rate,
                ))

            # Factory: convert raw materials to finished goods
            fg_rate = node.properties.get("finished_goods_production", 0)
            rm_needed = node.properties.get("raw_materials_consumption", 0)
            if fg_rate > 0 and rm_needed > 0:
                rm_stock = node.properties.get("raw_materials_stock", 0)
                if rm_stock >= rm_needed:
                    production = fg_rate
                    node.properties["raw_materials_stock"] = rm_stock - rm_needed
                elif rm_stock > 0:
                    ratio = rm_stock / rm_needed
                    production = fg_rate * ratio
                    node.properties["raw_materials_stock"] = 0
                else:
                    production = 0

                if production > 0:
                    node.properties["finished_goods_stock"] = (
                        node.properties.get("finished_goods_stock", 0) + production
                    )
                    events.append(ProductionEvent(
                        tick=tick, node_id=node.id,
                        resource="finished_goods", amount=production,
                    ))

        return events

    def _run_pricing(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick
        elasticity = config.get("price_elasticity", 1.0)
        base_raw = config.get("base_price_raw", 10)
        base_finished = config.get("base_price_finished", 50)

        for node in state.nodes.values():
            if "price_raw" in node.properties:
                stock = node.properties.get("raw_materials_stock", 0)
                target = 150
                old_price = node.properties["price_raw"]
                multiplier = _elasticity_multiplier(stock, target, elasticity)
                new_price = max(1.0, base_raw * multiplier)
                node.properties["price_raw"] = old_price * 0.7 + new_price * 0.3
                events.append(PriceUpdateEvent(
                    tick=tick, node_id=node.id, resource="raw_materials",
                    old_price=old_price, new_price=node.properties["price_raw"],
                ))

            if "price_finished" in node.properties:
                stock = node.properties.get("finished_goods_stock", 0)
                target = 100
                old_price = node.properties["price_finished"]
                multiplier = _elasticity_multiplier(stock, target, elasticity)
                new_price = max(1.0, base_finished * multiplier)
                node.properties["price_finished"] = old_price * 0.7 + new_price * 0.3
                events.append(PriceUpdateEvent(
                    tick=tick, node_id=node.id, resource="finished_goods",
                    old_price=old_price, new_price=node.properties["price_finished"],
                ))

        return events

    def _run_decisions(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        """
        Courier decisions: simple shuttle pattern.
        Each courier has a route [A, B] (or [A, B, C]).
        Outbound: load at first stop, deliver at last stop.
        Return: head back empty (or could carry return cargo in future).
        """
        events: list[Event] = []
        tick = state.tick

        for agent in state.agents.values():
            if agent.properties.get("status", 0) == 1:
                continue  # in transit

            route = agent.metadata.get("route", [])
            if len(route) < 2:
                continue

            cargo_type = agent.metadata.get("cargo_type", "raw_materials")
            stock_key = f"{cargo_type}_stock"
            cargo_qty = agent.properties.get("cargo_quantity", 0)
            capacity = agent.properties.get("cargo_capacity", 50)
            direction = agent.metadata.get("direction", 0)

            if cargo_qty > 0:
                # Has cargo — deliver at current location (must be a delivery point)
                node = state.nodes.get(agent.location)
                if node:
                    node.properties[stock_key] = node.properties.get(stock_key, 0) + cargo_qty
                    events.append(CargoDeliverEvent(
                        tick=tick, agent_id=agent.id, node_id=agent.location,
                        resource=cargo_type, quantity=cargo_qty,
                    ))
                    agent.properties["cargo_quantity"] = 0

                # After delivery, reverse direction and head back
                agent.metadata["direction"] = 1 - direction
                dest = route[0] if direction == 0 else route[-1]
                self._depart(agent, dest, state, events, tick)

            else:
                # No cargo — try to load at current location
                source = route[0] if direction == 0 else route[-1]
                dest = route[-1] if direction == 0 else route[0]

                if agent.location == source:
                    # At source — load cargo
                    node = state.nodes.get(agent.location)
                    if node:
                        available = node.properties.get(stock_key, 0)
                        # Leave a small reserve so the node isn't stripped bare
                        reserve = 20
                        loadable = max(0, available - reserve)
                        load_qty = min(capacity, loadable)
                        if load_qty > 0:
                            node.properties[stock_key] = available - load_qty
                            agent.properties["cargo_quantity"] = load_qty
                            events.append(CargoLoadEvent(
                                tick=tick, agent_id=agent.id, node_id=agent.location,
                                resource=cargo_type, quantity=load_qty,
                            ))

                    # Head to destination (even if empty — don't get stuck)
                    if agent.properties.get("cargo_quantity", 0) > 0:
                        self._depart(agent, dest, state, events, tick)
                    elif available <= reserve:
                        # Nothing to load, wait for stock to build up
                        pass
                    else:
                        self._depart(agent, dest, state, events, tick)
                else:
                    # Not at source — head to source
                    self._depart(agent, source, state, events, tick)

        return events

    def _depart(
        self, agent: Any, destination: str,
        state: EnvironmentState, events: list[Event], tick: int,
    ) -> None:
        """Send a courier toward a destination."""
        if destination == agent.location:
            return
        dist = state.graph.shortest_path_distance(agent.location, destination)
        if dist is None:
            return
        eta = max(1, math.ceil(dist / max(agent.properties.get("speed", 1), 0.1)))
        agent.metadata["origin"] = agent.location
        agent.metadata["destination"] = destination
        agent.properties["eta"] = eta
        agent.properties["eta_total"] = eta
        agent.properties["status"] = 1
        events.append(AgentMoveEvent(
            tick=tick, agent_id=agent.id,
            from_node=agent.location, to_node=destination, eta=eta,
        ))

    def _run_movement(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick

        for agent in state.agents.values():
            if agent.properties.get("status", 0) != 1:
                continue

            eta = agent.properties.get("eta", 0)
            if eta > 1:
                agent.properties["eta"] = eta - 1
            else:
                dest = agent.metadata.get("destination", "")
                if dest:
                    agent.location = dest
                    agent.properties["status"] = 0
                    agent.properties["eta"] = 0
                    agent.properties["eta_total"] = 0
                    agent.metadata["origin"] = ""
                    agent.metadata["destination"] = ""
                    events.append(AgentArriveEvent(
                        tick=tick, agent_id=agent.id, node_id=dest,
                    ))

        return events

    def _run_consumption(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        """Elastic consumption: throttle when stock is low instead of cliff-edge to zero."""
        events: list[Event] = []
        tick = state.tick

        for node in state.nodes.values():
            rate = node.properties.get("finished_goods_consumption", 0)
            if rate > 0:
                stock = node.properties.get("finished_goods_stock", 0)
                ratio = _consumption_ratio(stock, rate)
                actual = rate * ratio

                if actual > stock:
                    actual = stock

                if actual > 0:
                    node.properties["finished_goods_stock"] = stock - actual
                    events.append(ConsumptionEvent(
                        tick=tick, node_id=node.id,
                        resource="finished_goods", amount=actual, rationing=ratio,
                    ))

                if ratio < 0.8:
                    events.append(ShortageEvent(
                        tick=tick, node_id=node.id, resource="finished_goods",
                        needed=rate, available=stock,
                    ))

        return events

    def _run_snapshots(self, state: EnvironmentState) -> list[Event]:
        nodes_snapshot = {
            nid: dict(node.properties)
            for nid, node in state.nodes.items()
        }
        agents_snapshot = {}
        for aid, a in state.agents.items():
            agent_data: dict[str, Any] = {
                "location": a.location,
                "origin": a.metadata.get("origin", ""),
                "destination": a.metadata.get("destination", ""),
                **{k: v for k, v in a.properties.items()},
            }
            agents_snapshot[aid] = agent_data
        return [SnapshotEvent(
            tick=state.tick, nodes=nodes_snapshot, agents=agents_snapshot,
        )]

    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict[str, Any]:
        agent = state.agents[agent_id]
        visible_nodes = {}
        neighbors = [agent.location] + state.graph.neighbors(agent.location)
        for nid in neighbors:
            if nid in state.nodes:
                visible_nodes[nid] = dict(state.nodes[nid].properties)

        return {
            "agent_id": agent_id,
            "location": agent.location,
            "properties": dict(agent.properties),
            "metadata": dict(agent.metadata),
            "visible_nodes": visible_nodes,
        }

    def get_available_actions(self, agent_id: str, state: EnvironmentState) -> list[str]:
        agent = state.agents[agent_id]
        if agent.properties.get("status", 0) == 1:
            return ["wait"]
        actions = ["wait", "load", "travel"]
        if agent.properties.get("cargo_quantity", 0) > 0:
            actions.append("deliver")
        return actions

    def validate_action(
        self, agent_id: str, action: dict[str, Any], state: EnvironmentState
    ) -> tuple[bool, str]:
        if "action" not in action:
            return False, "Missing 'action' field"
        return True, ""

    def execute_action(
        self, agent_id: str, action: dict[str, Any], state: EnvironmentState, tick: int
    ) -> list[Event]:
        return []


def handle_scenario_event(event: ScenarioEvent, state: EnvironmentState) -> None:
    """Apply a scenario event to the environment state."""
    if event.event_type == "edge_disruption":
        from_node = event.parameters.get("from", "")
        to_node = event.parameters.get("to", "")
        new_distance = event.parameters.get("new_distance", 0)

        new_edges = []
        for edge in state.graph.edges:
            if edge.origin == from_node and edge.destination == to_node:
                new_edges.append(Edge(
                    origin=edge.origin,
                    destination=edge.destination,
                    distance=new_distance,
                    edge_type=edge.edge_type,
                ))
            else:
                new_edges.append(edge)

        from constellation_core.topology.graph import Graph
        state.graph = Graph(node_ids=state.graph.node_ids, edges=new_edges)
