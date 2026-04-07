"""CLI entry point: python -m constellation_core"""

from __future__ import annotations

import argparse
import sys

from constellation_core.config.loader import load_config, resolve_plugin
from constellation_core.engine.simulation import Simulation


def cmd_run(args: argparse.Namespace) -> None:
    """Run a simulation headless."""
    config = load_config(args.config)
    plugin = resolve_plugin(config.domain)

    engine_config = config.to_engine_config()
    sim = Simulation(plugin, engine_config)
    sim.setup()

    ticks = args.ticks or config.ticks
    print(f"Running {config.domain} for {ticks} ticks...")

    events = sim.run(ticks=ticks)
    print(f"Completed. {len(events)} events generated. Final tick: {sim.state.tick}")  # type: ignore[union-attr]


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the server with viewer."""
    try:
        from constellation_core.server.app import run_server
    except ImportError:
        print("Server dependencies not installed. Run: pip install constellation-core[server]")
        sys.exit(1)
    run_server(args.config, ticks=args.ticks, port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="constellation-core",
        description="Domain-agnostic simulation platform",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a simulation headless")
    run_parser.add_argument("config", help="Path to YAML config file")
    run_parser.add_argument("--ticks", type=int, default=None)

    serve_parser = subparsers.add_parser("serve", help="Start server with viewer")
    serve_parser.add_argument("config", help="Path to YAML config file")
    serve_parser.add_argument("--ticks", type=int, default=None)
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
