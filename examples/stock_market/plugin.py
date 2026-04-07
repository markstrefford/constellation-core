"""Stock market domain plugin — emergent herd behaviour simulation."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from constellation_core.engine.events import Event, ScenarioEvent
from constellation_core.topology.state import EnvironmentState


# --- Domain events ---

STOCKS = ["stock_a", "stock_b", "stock_c", "stock_d", "stock_e"]


@dataclass(frozen=True)
class OrderEvent(Event):
    kind: str = "ORDER"
    agent_id: str = ""
    action: str = ""  # "buy" or "sell"
    stock: str = ""
    quantity: int = 0


@dataclass(frozen=True)
class TradeEvent(Event):
    kind: str = "TRADE"
    stock: str = ""
    net_demand: int = 0
    volume: int = 0
    price_before: float = 0
    price_after: float = 0


@dataclass(frozen=True)
class SentimentEvent(Event):
    kind: str = "SENTIMENT"
    old_sentiment: float = 0
    new_sentiment: float = 0


@dataclass(frozen=True)
class SnapshotEvent(Event):
    kind: str = "SNAPSHOT"
    prices: dict = field(default_factory=dict)
    sentiment: float = 0
    agents: dict = field(default_factory=dict)


# --- Agent strategies (algorithmic) ---


def _hash_seed(agent_id: str, tick: int, extra: str = "") -> float:
    """Deterministic pseudo-random float [0, 1) from agent_id + tick."""
    h = hashlib.md5(f"{agent_id}:{tick}:{extra}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class StockMarketPlugin:
    """
    Mini stock market simulation.

    Single node (exchange). 20 agents with different strategies trade
    each tick. The interesting finding: when too many agents follow
    momentum, prices crash.
    """

    def __init__(self) -> None:
        self._orders: list[dict[str, Any]] = []
        self._price_history: dict[str, list[float]] = {}
        self._pending_scenarios: list[ScenarioEvent] = []

    def get_tick_phases(self) -> list[str]:
        return [
            "scenario",
            "market_open",
            "decisions",
            "order_matching",
            "price_update",
            "sentiment",
            "snapshots",
        ]

    def setup(self, state: EnvironmentState, config: dict[str, Any]) -> None:
        stocks = config.get("stocks", STOCKS)
        exchange = state.nodes.get("exchange")
        if exchange:
            for stock in stocks:
                price = exchange.properties.get(f"{stock}_price", 100)
                self._price_history[stock] = [price]

    def run_phase(
        self,
        phase: str,
        state: EnvironmentState,
        config: dict[str, Any],
    ) -> list[Event]:
        if phase == "scenario":
            return self._run_scenario(state, config)
        elif phase == "market_open":
            return self._run_market_open(state, config)
        elif phase == "decisions":
            return self._run_decisions(state, config)
        elif phase == "order_matching":
            return self._run_order_matching(state, config)
        elif phase == "price_update":
            return self._run_price_update(state, config)
        elif phase == "sentiment":
            return self._run_sentiment(state, config)
        elif phase == "snapshots":
            return self._run_snapshots(state)
        return []

    def _run_scenario(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        exchange = state.nodes.get("exchange")
        if not exchange:
            self._pending_scenarios.clear()
            return []

        for se in self._pending_scenarios:
            if se.event_type == "price_shock":
                stock = se.parameters.get("stock", "")
                multiplier = se.parameters.get("multiplier", 1.0)
                price_key = f"{stock}_price"
                if price_key in exchange.properties:
                    exchange.properties[price_key] *= multiplier
            elif se.event_type == "sentiment_shock":
                new_sentiment = se.parameters.get("sentiment", 0.5)
                exchange.properties["market_sentiment"] = new_sentiment

        self._pending_scenarios.clear()
        return []

    def notify_scenario_event(self, event: ScenarioEvent) -> None:
        self._pending_scenarios.append(event)

    def _run_market_open(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        self._orders.clear()
        exchange = state.nodes.get("exchange")
        if exchange:
            exchange.properties["total_buy_orders"] = 0
            exchange.properties["total_sell_orders"] = 0
            stocks = config.get("stocks", STOCKS)
            for stock in stocks:
                exchange.properties[f"{stock}_volume"] = 0
        return []

    def _run_decisions(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick
        exchange = state.nodes.get("exchange")
        if not exchange:
            return events

        stocks = config.get("stocks", STOCKS)
        sentiment = exchange.properties.get("market_sentiment", 0.5)
        max_order_frac = config.get("max_order_fraction", 0.1)

        for agent in state.agents.values():
            strategy = int(agent.properties.get("strategy", 3))
            risk = agent.properties.get("risk_tolerance", 0.5)
            cash = agent.properties.get("cash", 0)

            for stock in stocks:
                price_key = f"{stock}_price"
                price = exchange.properties.get(price_key, 100)
                holdings = agent.properties.get(stock, 0)

                # Compute price change signal
                history = self._price_history.get(stock, [price])
                if len(history) >= 2:
                    pct_change = (history[-1] - history[-2]) / max(history[-2], 0.01)
                else:
                    pct_change = 0

                action = "hold"
                quantity = 0

                if strategy == 1:  # Momentum
                    # Buy rising, sell falling. Sentiment amplifies.
                    signal = pct_change * (1 + sentiment)
                    if signal > 0.01 * (1 - risk):
                        # Buy
                        max_buy = int(cash * max_order_frac / max(price, 0.01))
                        quantity = max(1, int(max_buy * risk))
                        if quantity > 0 and cash >= quantity * price:
                            action = "buy"
                    elif signal < -0.01 * (1 - risk):
                        # Sell
                        quantity = max(1, int(holdings * max_order_frac * risk))
                        if quantity > 0 and holdings >= quantity:
                            action = "sell"

                elif strategy == 2:  # Contrarian
                    # Buy falling, sell rising. Ignores sentiment.
                    if pct_change < -0.01 * (1 - risk):
                        max_buy = int(cash * max_order_frac / max(price, 0.01))
                        quantity = max(1, int(max_buy * risk))
                        if quantity > 0 and cash >= quantity * price:
                            action = "buy"
                    elif pct_change > 0.01 * (1 - risk):
                        quantity = max(1, int(holdings * max_order_frac * risk))
                        if quantity > 0 and holdings >= quantity:
                            action = "sell"

                elif strategy == 3:  # Random
                    rand = _hash_seed(agent.id, tick, stock)
                    if rand < 0.3:
                        max_buy = int(cash * max_order_frac / max(price, 0.01))
                        quantity = max(1, int(max_buy * 0.3))
                        if quantity > 0 and cash >= quantity * price:
                            action = "buy"
                    elif rand > 0.7:
                        quantity = max(1, int(holdings * max_order_frac * 0.3))
                        if quantity > 0 and holdings >= quantity:
                            action = "sell"

                if action != "hold" and quantity > 0:
                    self._orders.append({
                        "agent_id": agent.id,
                        "action": action,
                        "stock": stock,
                        "quantity": quantity,
                        "price": price,
                    })
                    events.append(OrderEvent(
                        tick=tick, agent_id=agent.id,
                        action=action, stock=stock, quantity=quantity,
                    ))

        return events

    def _run_order_matching(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick
        exchange = state.nodes.get("exchange")
        if not exchange:
            return events

        stocks = config.get("stocks", STOCKS)

        # Aggregate orders per stock
        for stock in stocks:
            buy_orders = [o for o in self._orders if o["stock"] == stock and o["action"] == "buy"]
            sell_orders = [o for o in self._orders if o["stock"] == stock and o["action"] == "sell"]

            total_buy = sum(o["quantity"] for o in buy_orders)
            total_sell = sum(o["quantity"] for o in sell_orders)
            matched = min(total_buy, total_sell)
            price = exchange.properties.get(f"{stock}_price", 100)

            # Execute matched trades
            # Proportionally fill orders
            if matched > 0:
                buy_fill_ratio = matched / total_buy if total_buy > 0 else 0
                sell_fill_ratio = matched / total_sell if total_sell > 0 else 0

                for order in buy_orders:
                    filled = int(order["quantity"] * buy_fill_ratio)
                    if filled > 0:
                        agent = state.agents.get(order["agent_id"])
                        if agent:
                            cost = filled * price
                            if agent.properties.get("cash", 0) >= cost:
                                agent.properties["cash"] = agent.properties.get("cash", 0) - cost
                                agent.properties[stock] = agent.properties.get(stock, 0) + filled

                for order in sell_orders:
                    filled = int(order["quantity"] * sell_fill_ratio)
                    if filled > 0:
                        agent = state.agents.get(order["agent_id"])
                        if agent:
                            held = agent.properties.get(stock, 0)
                            actual_sell = min(filled, int(held))
                            if actual_sell > 0:
                                agent.properties[stock] = held - actual_sell
                                agent.properties["cash"] = agent.properties.get("cash", 0) + actual_sell * price

            exchange.properties[f"{stock}_volume"] = total_buy + total_sell
            exchange.properties["total_buy_orders"] = (
                exchange.properties.get("total_buy_orders", 0) + total_buy
            )
            exchange.properties["total_sell_orders"] = (
                exchange.properties.get("total_sell_orders", 0) + total_sell
            )

            events.append(TradeEvent(
                tick=tick, stock=stock,
                net_demand=total_buy - total_sell,
                volume=total_buy + total_sell,
                price_before=price, price_after=price,  # Updated in price_update phase
            ))

        self._orders.clear()
        return events

    def _run_price_update(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick
        exchange = state.nodes.get("exchange")
        if not exchange:
            return events

        stocks = config.get("stocks", STOCKS)
        impact = config.get("price_impact_factor", 0.001)

        for stock in stocks:
            price_key = f"{stock}_price"
            volume_key = f"{stock}_volume"
            old_price = exchange.properties.get(price_key, 100)
            volume = exchange.properties.get(volume_key, 0)

            # Net demand from this tick's trade events
            buy_orders = exchange.properties.get("total_buy_orders", 0)
            sell_orders = exchange.properties.get("total_sell_orders", 0)
            # Use per-stock volume as proxy
            stock_volume = exchange.properties.get(volume_key, 1)

            # Recompute net demand from orders (rough approximation)
            # More buys -> price up, more sells -> price down
            if stock_volume > 0:
                # Get per-stock net from trade events in this phase
                net = 0
                for agent in state.agents.values():
                    # Not ideal but works for the simple model
                    pass

                # Simple: use total buy/sell ratio as price signal
                if buy_orders + sell_orders > 0:
                    buy_ratio = buy_orders / (buy_orders + sell_orders)
                    pressure = (buy_ratio - 0.5) * 2  # [-1, 1]
                else:
                    pressure = 0

                new_price = old_price * (1 + impact * pressure * stock_volume)
            else:
                new_price = old_price

            # Clamp price
            new_price = max(1.0, new_price)

            exchange.properties[price_key] = new_price

            # Update history
            if stock not in self._price_history:
                self._price_history[stock] = []
            self._price_history[stock].append(new_price)
            # Keep last 50 ticks
            if len(self._price_history[stock]) > 50:
                self._price_history[stock] = self._price_history[stock][-50:]

        return events

    def _run_sentiment(self, state: EnvironmentState, config: dict[str, Any]) -> list[Event]:
        events: list[Event] = []
        tick = state.tick
        exchange = state.nodes.get("exchange")
        if not exchange:
            return events

        stocks = config.get("stocks", STOCKS)
        alpha = config.get("sentiment_alpha", 0.1)
        old_sentiment = exchange.properties.get("market_sentiment", 0.5)

        # Average price change across all stocks
        total_change = 0
        count = 0
        for stock in stocks:
            history = self._price_history.get(stock, [])
            if len(history) >= 2:
                pct = (history[-1] - history[-2]) / max(history[-2], 0.01)
                total_change += pct
                count += 1

        if count > 0:
            avg_change = total_change / count
            # Map price change to sentiment shift: rising = greed, falling = fear
            sentiment_signal = 0.5 + avg_change * 10  # Scale factor
            sentiment_signal = max(0, min(1, sentiment_signal))
            new_sentiment = old_sentiment * (1 - alpha) + sentiment_signal * alpha
        else:
            new_sentiment = old_sentiment

        new_sentiment = max(0, min(1, new_sentiment))
        exchange.properties["market_sentiment"] = new_sentiment

        if abs(new_sentiment - old_sentiment) > 0.001:
            events.append(SentimentEvent(
                tick=tick, old_sentiment=old_sentiment, new_sentiment=new_sentiment,
            ))

        return events

    def _run_snapshots(self, state: EnvironmentState) -> list[Event]:
        exchange = state.nodes.get("exchange")
        if not exchange:
            return []

        prices = {
            k: v for k, v in exchange.properties.items()
            if k.endswith("_price")
        }
        agents = {
            aid: {
                "cash": a.properties.get("cash", 0),
                **{s: a.properties.get(s, 0) for s in STOCKS},
            }
            for aid, a in state.agents.items()
        }
        return [SnapshotEvent(
            tick=state.tick,
            prices=prices,
            sentiment=exchange.properties.get("market_sentiment", 0.5),
            agents=agents,
        )]

    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict[str, Any]:
        agent = state.agents[agent_id]
        exchange = state.nodes["exchange"]

        stocks = STOCKS
        prices = {s: exchange.properties.get(f"{s}_price", 100) for s in stocks}
        price_changes = {}
        for s in stocks:
            history = self._price_history.get(s, [])
            if len(history) >= 2:
                price_changes[s] = (history[-1] - history[-2]) / max(history[-2], 0.01)
            else:
                price_changes[s] = 0

        portfolio = {s: agent.properties.get(s, 0) for s in stocks}

        return {
            "agent_id": agent_id,
            "cash": agent.properties.get("cash", 0),
            "portfolio": portfolio,
            "prices": prices,
            "price_changes": price_changes,
            "sentiment": exchange.properties.get("market_sentiment", 0.5),
        }

    def get_available_actions(self, agent_id: str, state: EnvironmentState) -> list[str]:
        return ["buy", "sell", "hold"]

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
