"""FastAPI server — SSE streaming, agent API, topology endpoint."""

import asyncio
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

from constellation_core.config.loader import load_config
from constellation_core.engine.events import Event
from constellation_core.engine.simulation import Simulation

# Global state for the running simulation
_sim_state: dict[str, Any] = {
    "simulation": None,
    "plugin": None,
    "config": None,
    "tick_events": [],  # list of per-tick event batches
    "current_tick": 0,
    "status": "idle",
    "snapshots": [],  # latest snapshot per tick for the viewer
}


def _event_to_dict(event: Event) -> dict[str, Any]:
    """Convert an Event dataclass to a JSON-serializable dict."""
    d: dict[str, Any] = {"tick": event.tick, "kind": event.kind}
    for key, value in event.__dict__.items():
        if key not in ("tick", "kind"):
            d[key] = value
    return d


def _run_simulation_thread(sim: Simulation, plugin: Any, ticks: int) -> None:
    """Run simulation in background thread, storing snapshots for SSE."""
    _sim_state["status"] = "running"
    domain_config = sim.config.get("domain_config", {})

    try:
        for tick_events in sim.run_streaming(ticks=ticks):
            event_dicts = [_event_to_dict(e) for e in tick_events]
            _sim_state["tick_events"].append(event_dicts)
            _sim_state["current_tick"] = sim.state.tick if sim.state else 0

            # Build snapshot for viewer
            if sim.state:
                snapshot = {
                    "tick": sim.state.tick - 1,  # tick was already incremented
                    "nodes": {
                        nid: {
                            "properties": dict(node.properties),
                            "metadata": dict(node.metadata),
                        }
                        for nid, node in sim.state.nodes.items()
                    },
                    "agents": {
                        aid: {
                            "location": agent.location,
                            "properties": dict(agent.properties),
                            "metadata": {
                                k: v for k, v in agent.metadata.items()
                                if isinstance(v, (str, int, float, bool))
                            },
                        }
                        for aid, agent in sim.state.agents.items()
                    },
                }
                _sim_state["snapshots"].append(snapshot)

            time.sleep(0.02)  # ~50 ticks/sec max, gives viewer time to render

        _sim_state["status"] = "completed"
    except Exception as e:
        _sim_state["status"] = f"failed: {e}"


def create_app(config_path: str, ticks: int | None = None) -> Any:
    """Create and return the FastAPI app."""
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles

    config = load_config(config_path)
    engine_config = config.to_engine_config()
    total_ticks = ticks or config.ticks

    # Resolve plugin
    domain = config.domain
    plugin: Any = None

    # Try to import from examples
    examples_dir = Path(__file__).parent.parent.parent.parent / "examples"
    if examples_dir.exists():
        sys.path.insert(0, str(examples_dir))

    if domain == "supply_chain":
        from supply_chain.plugin import SupplyChainPlugin
        plugin = SupplyChainPlugin()
    elif domain == "stock_market":
        from stock_market.plugin import StockMarketPlugin
        plugin = StockMarketPlugin()
    else:
        from constellation_core.config.loader import resolve_plugin
        plugin = resolve_plugin(domain)

    sim = Simulation(plugin, engine_config)
    sim.setup()

    _sim_state["simulation"] = sim
    _sim_state["plugin"] = plugin
    _sim_state["config"] = engine_config
    _sim_state["tick_events"] = []
    _sim_state["snapshots"] = []
    _sim_state["current_tick"] = 0
    _sim_state["status"] = "idle"

    app = FastAPI(title="constellation-core", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve viewer static files if they exist
    viewer_dist = Path(__file__).parent.parent.parent.parent / "viewer" / "dist"
    if viewer_dist.exists():
        app.mount("/viewer", StaticFiles(directory=str(viewer_dist), html=True), name="viewer")

    @app.get("/api/topology")
    def get_topology() -> dict[str, Any]:
        if sim.state is None:
            return {"nodes": [], "edges": []}

        graph_dict = sim.state.graph.to_dict()
        # Add node metadata for the viewer
        nodes_with_meta = []
        for nid in sim.state.graph.node_ids:
            node = sim.state.nodes.get(nid)
            nodes_with_meta.append({
                "id": nid,
                "metadata": dict(node.metadata) if node else {},
                "properties": dict(node.properties) if node else {},
            })
        graph_dict["nodes"] = nodes_with_meta
        return graph_dict

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {
            "status": _sim_state["status"],
            "current_tick": _sim_state["current_tick"],
            "total_ticks": total_ticks,
            "domain": domain,
            "node_count": len(sim.state.nodes) if sim.state else 0,
            "agent_count": len(sim.state.agents) if sim.state else 0,
        }

    @app.post("/api/start")
    def start_simulation() -> dict[str, str]:
        if _sim_state["status"] == "running":
            return {"status": "already running"}
        thread = threading.Thread(
            target=_run_simulation_thread,
            args=(sim, plugin, total_ticks),
            daemon=True,
        )
        thread.start()
        return {"status": "started"}

    @app.get("/api/snapshot/{tick}")
    def get_snapshot(tick: int) -> dict[str, Any]:
        if 0 <= tick < len(_sim_state["snapshots"]):
            return _sim_state["snapshots"][tick]
        return {"error": "tick not available"}

    @app.get("/api/events")
    async def stream_events(request: Request) -> StreamingResponse:
        """SSE endpoint — streams snapshots as they're produced."""

        async def event_generator():
            last_sent = 0
            yield f"data: {json.dumps({'type': 'init', 'domain': domain})}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                snapshots = _sim_state["snapshots"]
                if last_sent < len(snapshots):
                    for i in range(last_sent, len(snapshots)):
                        data = json.dumps({"type": "tick", **snapshots[i]})
                        yield f"data: {data}\n\n"
                    last_sent = len(snapshots)

                if _sim_state["status"] in ("completed", "idle") and last_sent >= len(snapshots):
                    if _sim_state["status"] == "completed":
                        yield f"data: {json.dumps({'type': 'complete', 'total_ticks': last_sent})}\n\n"
                        break

                await asyncio.sleep(0.05)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def root() -> str:
        """Redirect to viewer or show status."""
        if viewer_dist.exists():
            return '<meta http-equiv="refresh" content="0;url=/viewer/">'
        return """
        <html><body>
        <h1>constellation-core</h1>
        <p>Server running. Viewer not built yet.</p>
        <p>API: <a href="/api/status">/api/status</a> |
           <a href="/api/topology">/api/topology</a> |
           SSE: <a href="/api/events">/api/events</a></p>
        <p>POST <a href="#" onclick="fetch('/api/start',{method:'POST'}).then(r=>r.json()).then(d=>alert(JSON.stringify(d)));return false;">/api/start</a> to begin simulation</p>
        </body></html>
        """

    return app


def run_server(config_path: str, ticks: int | None = None, port: int = 8000) -> None:
    """Start the server."""
    import uvicorn
    app = create_app(config_path, ticks)
    uvicorn.run(app, host="0.0.0.0", port=port)
