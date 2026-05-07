# Configuration

Constellation simulations are configured using YAML files. These files define the topology, the initial state of agents, and the domain-specific parameters.

---

## Root Fields

| Field | Type | Description |
|-------|------|-------------|
| `seed` | `int` | Random seed for reproducibility. Default: `42`. |
| `ticks` | `int` | How many ticks to run the simulation for. |
| `domain` | `str` | The name of the registered plugin to use. |
| `bidirectional_edges` | `bool` | If true, all edges are treated as two-way. Default: `true`. |
| `nodes` | `list` | List of node definitions. |
| `edges` | `list` | List of edge definitions. |
| `agents` | `list` | List of agent definitions. |
| `scenario_events` | `list` | List of scheduled shocks/events. |
| `domain_config` | `dict` | Arbitrary key-value pairs passed to the plugin's `setup` and `run_phase`. |

---

## Node Configuration

Each node in the `nodes` list has:

```yaml
- id: rotterdam        # Unique identifier
  properties:          # Domain-specific floats
    stock: 500.0
    price: 12.5
  metadata:             # Static info for the plugin or viewer
    label: "Rotterdam Port"
    type: port
```

---

## Edge Configuration

Edges connect nodes and define the "cost" of travel.

```yaml
- from: shanghai
  to: rotterdam
  distance: 15.0       # Distance in ticks (for speed=1)
  edge_type: ocean     # Metadata for the plugin
```

---

## Agent Configuration

Agents are placed at a starting node and can carry their own state.

```yaml
- id: freighter_1
  starting_location: shanghai
  properties:
    capacity: 100.0
  metadata:
    role: carrier
```

---

## Scenario Events

Schedule changes to the environment at specific ticks.

```yaml
scenario_events:
  - tick: 200
    type: edge_disruption
    parameters:
      from: shanghai
      to: rotterdam
      new_distance: 35.0
```

---

## Example Config

```yaml
seed: 123
ticks: 1000
domain: supply_chain
bidirectional_edges: false

nodes:
  - id: A
    properties: { stock: 100 }
  - id: B
    properties: { stock: 0 }

edges:
  - from: A
    to: B
    distance: 5

agents:
  - id: truck_1
    starting_location: A

domain_config:
  tax_rate: 0.05
```
