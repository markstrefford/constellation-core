---
id: phase-a-constellation-core-prs
kind: runbook
project: constellation-core
status: active
sources:
  - sdlc/work/active/constellation-core-migration-audit.md
created: 2026-04-29
updated: 2026-04-29
verified-on: 2026-04-29
tags: [constellation-core, phase-a, upstream-prs, preconditions]
---

# Phase A: Upstream PRs to constellation-core

## Purpose

Two small PRs against the open-source `constellation-core` repo (`~/Development/constellation-core`, Apache 2.0). Both are preconditions for the closed-repo migration epic `epic-constellation-core-migration` -- specifically `s1-story-cc-pin-dep` is blocked until they land and a release is tagged.

This runbook is the canonical specification of what changes to make. Execution happens in a separate session in the `constellation-core` repo. When that session opens, the first action is to mirror this content as either a `docs/NEXT-STEPS.md` update or proper issues in that repo, then write the PRs against it.

Both PRs are independent, can land in any order or in parallel, and are fully backwards-compatible with existing callers (current `examples/supply_chain`, `examples/stock_market`, `examples/reorg`).

## PR-1: Widen `Node.properties` typing

### Target file and line

`/Users/mark/Development/constellation-core/src/constellation_core/topology/state.py` -- line 24.

### Current code

```python
@dataclass
class Node:
    """..."""

    id: str
    properties: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Change

Widen the `properties` value type from `float` to `Any`:

```python
properties: dict[str, Any] = field(default_factory=dict)
```

`Any` is already imported on line 6 of the same file -- no import change needed.

### Why

Constellation's domain (a space economy with planets, hubs, sectors) needs to attach non-numeric properties to nodes:

- **Strings**: planet role (`"refiner"`, `"city"`), node kind (`"planet"`, `"hub"`, `"sector"`).
- **Enums / categoricals**: refining priority (`PriorityType.FUEL_FIRST`).
- **Nested dicts**: production rates per asset (`{"fuel_raw": 10.0, "food": 3.0}`), consumption rates, current prices, stocks.

Today these have to spill into `Node.metadata` (which is `dict[str, Any]`), which dilutes the abstraction -- `metadata` is meant for renderer hints / non-essential annotations, not load-bearing domain state.

### Test plan

- Existing `tests/test_topology/` tests pass unchanged. `dict[str, float]` is a subtype of `dict[str, Any]` for a covariant value type, so all existing typed callers compile.
- Add one test in `tests/test_topology/test_state.py` that creates a `Node` with mixed-type properties (a string, a dict, a list) and verifies they round-trip via the dataclass and survive `dataclasses.asdict()` if used.
- Run mypy strict on the package. If existing code (e.g. in `examples/supply_chain`) relies on `properties[key]` being typed as `float`, it gets a warning -- fix locally with explicit casts where needed; this is unlikely because all current examples store floats.

### Backwards compatibility

Fully backwards compatible. Type widening, not narrowing. Existing callers writing floats still work; their property reads still return float values at runtime.

### Expected diff size

1 line of source + ~10 lines of test.

### PR description template

```
Widen Node.properties typing from dict[str, float] to dict[str, Any]

Domain plugins riding on constellation-core need to attach non-numeric
state to nodes (role strings, enum-typed flags, nested dicts of per-asset
production rates). Today this has to spill into Node.metadata, which is
meant for renderer hints rather than load-bearing domain state.

Type widening, not narrowing -- all existing callers continue to work.
Existing supply_chain and stock_market examples store only floats; no
behavioural change.
```

---

## PR-2: Add `allowed_nodes` filter to pathfinding

### Target file and lines

`/Users/mark/Development/constellation-core/src/constellation_core/topology/graph.py` -- two methods:

- `Graph.shortest_path()` (line 83-139)
- `Graph.shortest_path_distance()` (line 141-159)

(Optional, recommended for API consistency: `Graph.neighbors()` line 65-77 -- see "Open questions" below.)

### Current signatures

```python
def shortest_path(
    self,
    origin: str,
    destination: str,
    allowed_types: set[str] | None = None,
) -> list[str] | None: ...

def shortest_path_distance(
    self,
    origin: str,
    destination: str,
    allowed_types: set[str] | None = None,
) -> float | None: ...
```

### Change

Add a new keyword argument `allowed_nodes: set[str] | None = None` to both. When `allowed_nodes` is provided, the pathfinding algorithm must skip any neighbor whose id is not in the set. When `None` (default), behaviour is unchanged.

In `shortest_path()` (the implementation), add the filter to the existing neighbor-expansion loop at line 119:

```python
for neighbor, edge_dist, edge_type in self._adjacency.get(current, []):
    if allowed_types is not None and edge_type not in allowed_types:
        continue
    if allowed_nodes is not None and neighbor not in allowed_nodes:
        continue
    if neighbor in visited:
        continue
    # ... existing dijkstra step
```

In `shortest_path_distance()`, the implementation calls `self.shortest_path(origin, destination, allowed_types)` -- update that call to pass `allowed_nodes` through.

Important: `origin` and `destination` themselves are not subject to `allowed_nodes` -- the caller chose them deliberately. Only intermediate nodes are filtered. (If a caller does want to forbid origin/destination, they can validate before calling.)

### Why

Constellation's hierarchical galaxy gives each agent class a different reachable set:

- **Local couriers** (`agent_class == "local_courier"`) operate within a single sector and may only visit planets in that sector. Whitelist = sector member ids.
- **Galactic freighters** (`agent_class == "galactic_freighter"`) only travel between hubs. Whitelist = hub ids.
- Existing `agent.decisions.profit_seeker.py:65` constructs and uses these whitelists today.

Without `allowed_nodes`, the closed plugin would have to either build a sub-graph per query (allocating + rebuilding adjacency lookups every pathfinding call -- O(E) per call instead of O(log V) on the existing Dijkstra) or post-filter paths by walking and discarding any path that touches a disallowed node (which can produce no result even when a valid filtered path exists).

### Test plan

Add to `tests/test_topology/test_graph.py`:

1. **Filter excludes intermediate nodes**: a 4-node chain `A-B-C-D`. With `allowed_nodes={"A", "C", "D"}` (excluding B), `shortest_path("A", "D")` returns `None` because the only route through B is blocked.
2. **Filter allows disjoint subgraph paths**: a graph with two routes from A to D, one through B and one through C. With `allowed_nodes={"A", "B", "D"}`, the path through B is selected.
3. **Filter does not affect endpoints**: with `allowed_nodes={"A", "B", "C", "D"}` not containing intermediate "X" (where X is a hub between B and C), the path correctly excludes X and uses the longer A-B-C-D route if one exists.
4. **Filter combined with `allowed_types`**: both filters apply (intersection-like; both must pass).
5. **Default `None` preserves behaviour**: identical results to pre-PR for all existing tests.
6. **`shortest_path_distance` honours the filter**: total distance reflects the allowed-only path, not the unrestricted shortest.

Existing `tests/test_topology/test_graph.py` tests pass unchanged.

### Backwards compatibility

Fully backwards compatible. The new parameter is keyword-only with a default of `None` that preserves existing behaviour. No existing caller is affected.

### Expected diff size

~10 lines of source (signature changes + filter check) + ~40 lines of tests.

### PR description template

```
Add allowed_nodes filter to Graph.shortest_path() and shortest_path_distance()

Domain plugins frequently need per-agent whitelists of reachable nodes --
e.g. an agent class that may only travel between certain node kinds. Today
this requires either rebuilding sub-graphs per query (O(E) allocation per
call) or post-filtering paths (which can fail to find valid filtered paths).

Adds an optional `allowed_nodes: set[str] | None` keyword argument to both
methods. When provided, intermediate nodes outside the set are skipped
during Dijkstra expansion. Origin and destination are not filtered --
callers chose them deliberately.

Default None preserves existing behaviour; no callers are affected.
```

---

## Sequencing & release

- The two PRs are independent. Land them in any order or in parallel.
- Once both are merged, tag a release (suggested: `0.2.0`, since this is a non-breaking but visible API addition).
- Update `~/Development/constellation-core/docs/NEXT-STEPS.md` to record the additions, removing the items if they were listed there pre-merge.
- The closed-repo `epic-constellation-core-migration` then pins to the new tag in `s1-story-cc-pin-dep`.

## Acceptance for "Phase A done"

1. PR-1 merged on `main` of `constellation-core`. CI green (mypy strict, pytest, ruff).
2. PR-2 merged on `main` of `constellation-core`. CI green.
3. A new tag exists on `constellation-core` `main` (e.g. `0.2.0`) that includes both merges. Tag pushed to remote.
4. `docs/NEXT-STEPS.md` updated with a brief mention (or removal if previously listed).
5. The closed-repo audit (`sdlc/work/active/constellation-core-migration-audit.md`) § 7 updates the precondition status from "open" to "landed in `constellation-core 0.2.0`."

Once all five hold, `s1-story-cc-pin-dep`'s `blocker:` field can be cleared and the story moves to `active`.

## Open questions

1. **Should `Graph.neighbors()` (line 65) also accept `allowed_nodes`?** It currently takes `allowed_types`. For API symmetry and to avoid filter-leakage if a domain calls `neighbors()` directly, it probably should. Not strictly required by the closed-repo plugin (which uses `shortest_path` for reachability), but worth a one-line addition while the PR is open. Decide during PR-2 review.
2. **Strict mypy fallout from PR-1.** Existing examples store only floats, so the widening should be invisible. Verify by running `mypy --strict` against the whole package post-merge; if anything surfaces, address as a follow-up rather than blocking the PR.
3. **`docs/CONSTELLATION-CORE-SPEC.md:23-29` overclaims JSON-everything for agents.** Separate concern, not part of Phase A. File as an issue against the open repo when convenient.

## When this runbook moves

Per SDLC co-locate rule, this lives in `sdlc/work/active/` while `epic-constellation-core-migration` is in flight. At epic close (S10), it graduates to `sdlc/docs/runbooks/phase-a-constellation-core-prs.md` as a historical record.
