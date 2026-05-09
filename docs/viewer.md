# The Simulation Viewer

The Constellation Viewer is a React-based web application that provides real-time visualization of your multi-agent simulations.

---

## Features

- **Live Graph Rendering:** Watch nodes and edges update in real-time.
- **Agent Tracking:** See agent movement and status across the topology.
- **Node Inspection:** Click on any node to view its current properties (stock levels, prices, etc.).
- **Time-Series Charts:** Monitor system-wide metrics over the course of the simulation.
- **Playback Controls:** Start, pause, and step through simulations.

---

## Technical Stack

- **Frontend:** React + Vite + TypeScript
- **Styling:** Tailwind CSS
- **Visualization:** React Flow (for graph rendering), Recharts (for data visualization).
- **Communication:** Server-Sent Events (SSE) from the FastAPI backend.

---

## How to use it

1. **Start the Backend:**
   The viewer needs a running Constellation server to provide data.
   ```bash
   python -m constellation_core serve examples/supply_chain/config.yaml
   ```

2. **Start the Frontend:**
   ```bash
   cd viewer
   npm run dev
   ```

3. **Navigate to `http://localhost:5173`:**
   Click **"Start Simulation"** in the sidebar.

---

## Extending the Viewer

The viewer is designed to be as agnostic as the core engine. It doesn't know about "supply chains" or "stocks." Instead, it listens for a special `SNAPSHOT` event emitted by your plugin.

To make your domain visible in the viewer, ensure your plugin emits a `SnapshotEvent` during its snapshot phase:

```python
@dataclass(frozen=True)
class SnapshotEvent(Event):
    kind: str = "SNAPSHOT"
    nodes: dict = field(default_factory=dict)
    agents: dict = field(default_factory=dict)
```

The viewer will automatically detect the properties in this snapshot and offer them for visualization in the inspector panel.

---

- **[Next: Examples](examples.md)**
- **[Back to Home](index.md)**
