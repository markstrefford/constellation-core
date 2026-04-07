"""Tests for the stock market example domain."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))

from stock_market.plugin import (
    OrderEvent,
    SentimentEvent,
    SnapshotEvent,
    StockMarketPlugin,
    TradeEvent,
)

from constellation_core.config.loader import load_config
from constellation_core.engine.events import ScenarioEvent
from constellation_core.engine.simulation import Simulation


CONFIG_PATH = Path(__file__).parent.parent.parent / "examples" / "stock_market" / "config.yaml"


class TestStockMarketPlugin:
    def _run_sim(self, ticks: int = 100) -> tuple:
        config = load_config(CONFIG_PATH)
        engine_config = config.to_engine_config()
        plugin = StockMarketPlugin()
        sim = Simulation(plugin, engine_config)
        sim.setup()
        events = sim.run(ticks=ticks)
        return sim, events, plugin

    def test_runs_without_crash(self):
        sim, events, _ = self._run_sim(500)
        assert len(events) > 0
        assert sim.state is not None
        assert sim.state.tick == 500

    def test_single_node_20_agents(self):
        sim, _, _ = self._run_sim(1)
        assert sim.state is not None
        assert len(sim.state.nodes) == 1
        assert len(sim.state.agents) == 20

    def test_orders_submitted(self):
        _, events, _ = self._run_sim(10)
        orders = [e for e in events if isinstance(e, OrderEvent)]
        assert len(orders) > 0

    def test_trades_occur(self):
        _, events, _ = self._run_sim(10)
        trades = [e for e in events if isinstance(e, TradeEvent)]
        assert len(trades) > 0

    def test_prices_fluctuate(self):
        sim, _, plugin = self._run_sim(100)
        assert sim.state is not None
        exchange = sim.state.nodes["exchange"]
        # Prices should have changed from initial values
        # At least one stock should have moved
        initial_prices = {
            "stock_a": 100, "stock_b": 50, "stock_c": 200,
            "stock_d": 75, "stock_e": 150,
        }
        changes = 0
        for stock, initial in initial_prices.items():
            current = exchange.properties.get(f"{stock}_price", initial)
            if abs(current - initial) > 0.01:
                changes += 1
        assert changes > 0, "No prices changed after 100 ticks"

    def test_sentiment_changes(self):
        _, events, _ = self._run_sim(50)
        sentiment_events = [e for e in events if isinstance(e, SentimentEvent)]
        assert len(sentiment_events) > 0

    def test_agents_maintain_non_negative_cash(self):
        sim, _, _ = self._run_sim(200)
        assert sim.state is not None
        for agent in sim.state.agents.values():
            assert agent.properties.get("cash", 0) >= 0, (
                f"Agent {agent.id} has negative cash: {agent.properties.get('cash')}"
            )

    def test_earnings_surprise_affects_stock_a(self):
        """At tick 100, stock_a gets a 20% price shock."""
        sim, events, plugin = self._run_sim(150)
        assert sim.state is not None
        # The scenario event should have been fired
        scenarios = [e for e in events if isinstance(e, ScenarioEvent)]
        assert any(e.event_type == "price_shock" for e in scenarios)

    def test_panic_drops_sentiment(self):
        """At tick 300, sentiment drops to 0.1."""
        sim, events, _ = self._run_sim(310)
        assert sim.state is not None
        scenarios = [e for e in events if isinstance(e, ScenarioEvent)]
        assert any(e.event_type == "sentiment_shock" for e in scenarios)
        # Shortly after panic (10 ticks), sentiment should be notably lower
        sentiment = sim.state.nodes["exchange"].properties.get("market_sentiment", 0.5)
        assert sentiment < 0.45, f"Sentiment {sentiment} not below 0.45 shortly after panic"

    def test_snapshots_emitted(self):
        _, events, _ = self._run_sim(10)
        snapshots = [e for e in events if isinstance(e, SnapshotEvent)]
        assert len(snapshots) == 10  # one per tick
