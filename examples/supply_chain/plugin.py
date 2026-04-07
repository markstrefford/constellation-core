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


# --- Plugin ---


class SupplyChainPlugin:
    """
    Global logistics simulation.

    Nodes are ports, factories, and retail hubs. Agents are freighters
    and trucks that move cargo between them. Production, consumption,
    and pricing are all domain logic living here, not in the core.
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
        # Initialize agent transit state
        for agent in state.agents.values():
            agent.properties.setdefault("cargo_quantity", 0)
            agent.properties.setdefault("cargo_capacity", 50)
            agent.properties.setdefault("speed", 1)
            agent.properties.setdefault("eta", 0)
            agent.properties.setdefault("status", 0)  # 0=idle, 1=in_transit
            agent.metadata.setdefault("route_index", 0)
            agent.metadata.setdefault("loaded", False)
            agent.metadata.setdefault("destination", "")

        # Store pending scenario events
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
        """Apply any pending scenario events."""
        events: list[Event] = []
        for se in self._pending_scenarios:
            handle_scenario_event(se, state)
        self._pending_scenarios.clear()
        return events

    def notify_scenario_event(self, event: ScenarioEvent) -> None:
        """Called by the engine (via tick loop) to queue scenario events."""
        self._pending_scenarios.append(event)

    def _run_production(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick

        for node in state.nodes.values():
            # Raw materials production
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
                # Produce proportionally to available raw materials
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
            # Price raw materials based on stock
            if "price_raw" in node.properties:
                stock = node.properties.get("raw_materials_stock", 0)
                target = 100  # comfortable stock level
                old_price = node.properties["price_raw"]
                multiplier = _elasticity_multiplier(stock, target, elasticity)
                new_price = max(1.0, base_raw * multiplier)
                # Smooth: 30% toward target
                node.properties["price_raw"] = old_price * 0.7 + new_price * 0.3
                events.append(PriceUpdateEvent(
                    tick=tick, node_id=node.id, resource="raw_materials",
                    old_price=old_price, new_price=node.properties["price_raw"],
                ))

            # Price finished goods
            if "price_finished" in node.properties:
                stock = node.properties.get("finished_goods_stock", 0)
                target = 80
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
        """Route-based agent decisions: load at source, travel, deliver at dest."""
        events: list[Event] = []
        tick = state.tick

        for agent in state.agents.values():
            if agent.properties.get("status", 0) == 1:
                # In transit, skip decisions
                continue

            route = agent.metadata.get("route", [])
            if not route:
                continue

            cargo_type = agent.metadata.get("cargo_type", "raw_materials")
            stock_key = f"{cargo_type}_stock"
            cargo_qty = agent.properties.get("cargo_quantity", 0)
            capacity = agent.properties.get("cargo_capacity", 50)
            route_index = agent.metadata.get("route_index", 0)

            if cargo_qty > 0 and agent.metadata.get("loaded", False):
                # Has cargo — deliver if at a destination that wants it
                node = state.nodes.get(agent.location)
                if node and route_index > 0:
                    # Deliver cargo
                    delivered = cargo_qty
                    node.properties[stock_key] = node.properties.get(stock_key, 0) + delivered
                    agent.properties["cargo_quantity"] = 0
                    agent.metadata["loaded"] = False
                    events.append(CargoDeliverEvent(
                        tick=tick, agent_id=agent.id, node_id=agent.location,
                        resource=cargo_type, quantity=delivered,
                    ))
                    # Advance route or reverse
                    if route_index >= len(route) - 1:
                        agent.metadata["route_index"] = 0
                    else:
                        agent.metadata["route_index"] = route_index + 1

                    # Start heading to next stop
                    next_idx = agent.metadata["route_index"]
                    next_dest = route[next_idx]
                    if next_dest != agent.location:
                        dist = state.graph.shortest_path_distance(agent.location, next_dest)
                        if dist is not None:
                            agent.properties["eta"] = math.ceil(dist / max(agent.properties.get("speed", 1), 0.1))
                            agent.properties["status"] = 1
                            agent.metadata["destination"] = next_dest
                            events.append(AgentMoveEvent(
                                tick=tick, agent_id=agent.id,
                                from_node=agent.location, to_node=next_dest,
                            ))
                else:
                    # Not at delivery point — travel to next route stop
                    next_dest = route[min(route_index + 1, len(route) - 1)]
                    if next_dest != agent.location:
                        dist = state.graph.shortest_path_distance(agent.location, next_dest)
                        if dist is not None:
                            agent.properties["eta"] = math.ceil(dist / max(agent.properties.get("speed", 1), 0.1))
                            agent.properties["status"] = 1
                            agent.metadata["destination"] = next_dest
                            agent.metadata["route_index"] = route.index(next_dest) if next_dest in route else route_index + 1
                            events.append(AgentMoveEvent(
                                tick=tick, agent_id=agent.id,
                                from_node=agent.location, to_node=next_dest,
                            ))

            else:
                # No cargo — try to load at current location
                node = state.nodes.get(agent.location)
                if node:
                    available = node.properties.get(stock_key, 0)
                    load_qty = min(capacity, available)
                    if load_qty > 0:
                        node.properties[stock_key] = available - load_qty
                        agent.properties["cargo_quantity"] = load_qty
                        agent.metadata["loaded"] = True
                        events.append(CargoLoadEvent(
                            tick=tick, agent_id=agent.id, node_id=agent.location,
                            resource=cargo_type, quantity=load_qty,
                        ))

                # After loading (or if nothing to load), head to next route stop
                if route_index < len(route) - 1:
                    next_dest = route[route_index + 1]
                else:
                    next_dest = route[0]

                if next_dest != agent.location:
                    dist = state.graph.shortest_path_distance(agent.location, next_dest)
                    if dist is not None:
                        agent.properties["eta"] = math.ceil(dist / max(agent.properties.get("speed", 1), 0.1))
                        agent.properties["status"] = 1
                        agent.metadata["destination"] = next_dest
                        new_idx = route.index(next_dest) if next_dest in route else route_index + 1
                        agent.metadata["route_index"] = new_idx
                        events.append(AgentMoveEvent(
                            tick=tick, agent_id=agent.id,
                            from_node=agent.location, to_node=next_dest,
                        ))

        return events

    def _run_movement(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        """Progress agents in transit."""
        events: list[Event] = []
        tick = state.tick

        for agent in state.agents.values():
            if agent.properties.get("status", 0) != 1:
                continue

            eta = agent.properties.get("eta", 0)
            if eta > 1:
                agent.properties["eta"] = eta - 1
            else:
                # Arrived
                dest = agent.metadata.get("destination", "")
                if dest:
                    agent.location = dest
                    agent.properties["status"] = 0
                    agent.properties["eta"] = 0
                    agent.metadata["destination"] = ""
                    events.append(AgentArriveEvent(
                        tick=tick, agent_id=agent.id, node_id=dest,
                    ))

        return events

    def _run_consumption(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick

        for node in state.nodes.values():
            # Consume finished goods
            rate = node.properties.get("finished_goods_consumption", 0)
            if rate > 0:
                stock = node.properties.get("finished_goods_stock", 0)
                if stock >= rate:
                    consumed = rate
                else:
                    consumed = stock
                    if rate > 0:
                        events.append(ShortageEvent(
                            tick=tick, node_id=node.id, resource="finished_goods",
                            needed=rate, available=stock,
                        ))
                node.properties["finished_goods_stock"] = max(0, stock - consumed)
                if consumed > 0:
                    events.append(ConsumptionEvent(
                        tick=tick, node_id=node.id,
                        resource="finished_goods", amount=consumed,
                    ))

        return events

    def _run_snapshots(self, state: EnvironmentState) -> list[Event]:
        nodes_snapshot = {
            nid: dict(node.properties)
            for nid, node in state.nodes.items()
        }
        agents_snapshot = {
            aid: {"location": a.location, **a.properties}
            for aid, a in state.agents.items()
        }
        return [SnapshotEvent(
            tick=state.tick, nodes=nodes_snapshot, agents=agents_snapshot,
        )]

    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict[str, Any]:
        agent = state.agents[agent_id]
        # Agent sees its own state and nearby nodes
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
        # Actions are handled internally in _run_decisions for algorithmic agents
        return []


def handle_scenario_event(event: ScenarioEvent, state: EnvironmentState) -> None:
    """Apply a scenario event to the environment state."""
    if event.event_type == "edge_disruption":
        from_node = event.parameters.get("from", "")
        to_node = event.parameters.get("to", "")
        new_distance = event.parameters.get("new_distance", 0)

        # Rebuild edges with modified distance
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

        # Rebuild the graph
        from constellation_core.topology.graph import Graph
        state.graph = Graph(node_ids=state.graph.node_ids, edges=new_edges)
