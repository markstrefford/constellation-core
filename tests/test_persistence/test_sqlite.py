"""Tests for SQLite persistence."""

from __future__ import annotations

import tempfile
from pathlib import Path

from constellation_core.persistence.sqlite import SQLiteStorage


class TestSQLiteStorage:
    def _storage(self, tmp_path: Path) -> SQLiteStorage:
        return SQLiteStorage(str(tmp_path / "test.db"))

    def test_start_and_get_simulation(self, tmp_path: Path):
        s = self._storage(tmp_path)
        s.start_simulation("sim1", {"ticks": 100}, {"nodes": ["a", "b"]})

        sim = s.get_simulation("sim1")
        assert sim is not None
        assert sim["sim_id"] == "sim1"
        assert sim["config"]["ticks"] == 100
        assert sim["topology"]["nodes"] == ["a", "b"]
        assert sim["status"] == "running"
        s.close()

    def test_save_and_get_events(self, tmp_path: Path):
        s = self._storage(tmp_path)
        s.start_simulation("sim1", {})
        s.save_tick("sim1", 0, [{"kind": "TICK", "payload": "start"}])
        s.save_tick("sim1", 1, [{"kind": "TICK", "payload": "start"}, {"kind": "TEST"}])

        events_0 = s.get_events("sim1", 0)
        assert len(events_0) == 1
        assert events_0[0]["kind"] == "TICK"

        events_1 = s.get_events("sim1", 1)
        assert len(events_1) == 2
        s.close()

    def test_complete_simulation(self, tmp_path: Path):
        s = self._storage(tmp_path)
        s.start_simulation("sim1", {})
        s.complete_simulation("sim1", final_tick=99, summary={"total_events": 500})

        sim = s.get_simulation("sim1")
        assert sim is not None
        assert sim["status"] == "completed"
        assert sim["final_tick"] == 99
        assert sim["summary"]["total_events"] == 500
        s.close()

    def test_list_simulations(self, tmp_path: Path):
        s = self._storage(tmp_path)
        s.start_simulation("sim1", {})
        s.start_simulation("sim2", {})

        sims = s.list_simulations()
        assert len(sims) == 2
        sim_ids = {s["sim_id"] for s in sims}
        assert sim_ids == {"sim1", "sim2"}
        s.close()

    def test_get_nonexistent(self, tmp_path: Path):
        s = self._storage(tmp_path)
        assert s.get_simulation("nope") is None
        assert s.get_events("nope", 0) == []
        s.close()
