# Getting Started

Get Constellation up and running on your machine and run your first multi-agent simulation.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (only required for the real-time viewer)

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/markstrefford/constellation-core.git
cd constellation-core
```

### 2. Install the Python package
We recommend using a virtual environment.

```bash
# Install core + server + dev tools
pip install -e ".[dev,server]"
```

### 3. Install viewer dependencies (Optional)
If you want to use the web-based simulation viewer:

```bash
cd viewer
npm install
cd ..
```

---

## Running Your First Simulation

Constellation comes with several built-in examples. Let's run the **Global Supply Chain** simulation, which models cargo moving from Shanghai to European retail hubs.

### Option A: Headless (CLI only)
Run a quick 500-tick simulation and see the event log in your terminal.

```bash
python -m constellation_core run examples/supply_chain/config.yaml --ticks 500
```

### Option B: With the Real-Time Viewer
To see the simulation unfold visually:

**1. Start the API Server:**
```bash
python -m constellation_core serve examples/supply_chain/config.yaml
```

**2. Start the Viewer (in a new terminal):**
```bash
cd viewer
npm run dev
```

**3. Open the Viewer:**
Navigate to `http://localhost:5173`. Click **"Start Simulation"** and watch the freighters and trucks move across the graph.

---

## What just happened?

When you ran the supply chain simulation:
1. **The Engine** initialized a graph representing ports and factories.
2. **The Plugin** defined the "physics": how raw materials are produced and how prices change based on supply and demand.
3. **The Agents** (ships and trucks) began moving cargo between nodes to maximize their objectives.
4. **A Scenario Event** occurred at tick 200: a "Suez Canal blockage" increased the distance between Shanghai and Rotterdam, causing a ripple effect of shortages and price spikes across the network.

## Next Steps

- **[Understand the Concepts](concepts.md)** — Learn how Constellation is structured.
- **[Build your own Domain](build-a-domain.md)** — Start writing your own simulation physics.
