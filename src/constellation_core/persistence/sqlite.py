"""SQLite storage backend."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


class SQLiteStorage:
    """Persists simulation data to a local SQLite database."""

    def __init__(self, db_path: str = "constellation.db") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS simulations (
                sim_id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                topology TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                final_tick INTEGER,
                summary TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sim_id TEXT NOT NULL,
                tick INTEGER NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY (sim_id) REFERENCES simulations(sim_id)
            );
            CREATE INDEX IF NOT EXISTS idx_events_sim_tick
                ON events(sim_id, tick);
        """)

    def start_simulation(
        self,
        sim_id: str,
        config: dict[str, Any],
        topology: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO simulations (sim_id, config, topology, status, created_at) "
            "VALUES (?, ?, ?, 'running', ?)",
            (
                sim_id,
                json.dumps(config),
                json.dumps(topology) if topology else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def save_tick(
        self,
        sim_id: str,
        tick: int,
        events: list[dict[str, Any]],
    ) -> None:
        self._conn.execute(
            "INSERT INTO events (sim_id, tick, payload) VALUES (?, ?, ?)",
            (sim_id, tick, json.dumps(events)),
        )
        self._conn.commit()

    def complete_simulation(
        self,
        sim_id: str,
        final_tick: int,
        summary: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE simulations SET status='completed', final_tick=?, summary=? "
            "WHERE sim_id=?",
            (final_tick, json.dumps(summary) if summary else None, sim_id),
        )
        self._conn.commit()

    def get_simulation(self, sim_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM simulations WHERE sim_id=?", (sim_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "sim_id": row["sim_id"],
            "config": json.loads(row["config"]),
            "topology": json.loads(row["topology"]) if row["topology"] else None,
            "status": row["status"],
            "final_tick": row["final_tick"],
            "summary": json.loads(row["summary"]) if row["summary"] else None,
            "created_at": row["created_at"],
        }

    def get_events(self, sim_id: str, tick: int) -> list[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT payload FROM events WHERE sim_id=? AND tick=?",
            (sim_id, tick),
        ).fetchone()
        if row is None:
            return []
        return json.loads(row["payload"])

    def list_simulations(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT sim_id, status, final_tick, created_at FROM simulations "
            "ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._conn.close()
