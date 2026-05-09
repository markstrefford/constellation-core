# Examples

Constellation includes several built-in examples that demonstrate the platform's capabilities across different domains.

---

## 1. Global Supply Chain
**Location:** `examples/supply_chain/`

Models a multi-stage logistics network moving raw materials from production ports to consumer distribution centers.

- **Topology:** 5 nodes (Shanghai, Rotterdam, Stuttgart, Munich, Berlin).
- **Agents:** 1 Ocean freighter, 3 Trucks.
- **Key Physics:**
  - Production at source nodes.
  - Transformation (Raw materials &rarr; Finished goods) at the Factory node.
  - Price elasticity based on stock levels.
  - Consumption at retail nodes.
- **Scenario:** A "Suez Canal blockage" increases travel distance at tick 200, causing a bullwhip effect of shortages and price spikes.

---

## 2. Stock Market
**Location:** `examples/stock_market/`

A high-frequency trading simulation demonstrating emergent behavior and strategy convergence.

- **Topology:** A single Exchange node.
- **Agents:** 20 Traders with mixed strategies:
  - **Momentum:** Buy when price is rising, sell when falling.
  - **Contrarian:** Buy when price is falling, sell when rising.
  - **Noise:** Random trading to provide liquidity.
- **Key Physics:** Order book matching and price discovery.
- **Scenario:** An "Earnings Surprise" followed by a "Market Panic" to test how strategy diversity impacts system stability.

---

## 3. Company Restructure (Coming Soon)
**Location:** `examples/reorg/`

A simulation of corporate decision-making and information flow.

- **Topology:** A tree graph representing department hierarchy.
- **Agents:** Department heads.
- **Key Physics:** Information decay as reports move up the chain and budget allocation impacts productivity.

---

## How to run an example

You can run any example using the `constellation_core` CLI:

```bash
# Run headless
python -m constellation_core run examples/supply_chain/config.yaml

# Run with server (for viewer)
python -m constellation_core serve examples/stock_market/config.yaml
```

---

- **[Next: FAQ](faq.md)**
- **[Back to Home](index.md)**
