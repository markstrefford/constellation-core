# Persistence

Constellation is designed to capture every event that occurs during a simulation. This enables post-run analysis, replayability, and debugging.

---

## Storage Architecture

Persistence is handled by a `StorageBackend`. The engine emits event batches at the end of each tick, and the backend stores them.

### `StorageBackend` Protocol
You can implement your own storage (e.g., PostgreSQL, S3, MongoDB) by following the `StorageBackend` protocol:

- `start_simulation()`: Called when a run begins.
- `save_tick()`: Called every tick with a list of events.
- `complete_simulation()`: Called when the run finishes.
- `get_events()`: Used for replaying or analyzing a specific tick.

---

## Built-in SQLite Backend

Constellation includes a production-ready SQLite implementation. It stores simulation runs in a local `.db` file, which is ideal for research and local development.

### Database Schema
The SQLite backend uses two main tables:
1. **`simulations`**: Stores the metadata, initial YAML config, and topology.
2. **`events`**: Stores every individual event, indexed by simulation ID and tick number.

---

## Replaying a Simulation

Because Constellation records every state mutation as an event, you can "replay" a simulation by reading the events from the database and streaming them to the viewer, without actually re-running the logic.

This is particularly useful for:
- **Auditing LLM Decisions:** Seeing exactly what observation an LLM received before it took a specific action.
- **Sensitivity Analysis:** Comparing how the same scenario event impacted different runs.
- **Reporting:** Generating time-series charts from historical simulation data.

---

- **[Next: Simulation Viewer](viewer.md)**
- **[Back to Home](index.md)**
