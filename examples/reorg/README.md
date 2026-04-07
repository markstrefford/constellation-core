# Company Restructure Example (Coming Soon)

## The Story

A company with 5 departments. Each department is a node with headcount, budget, productivity, and morale. Agents are department heads making decisions: hire, cut, invest in training, request budget. Internal communications flow between departments (edges). A restructuring event (AI automation) hits one department and cascades through the org.

## Topology

```
              [CEO Office]
             /      |      \
    [Engineering] [Sales] [Operations]
                    |
                [Marketing]
```

5 nodes. Edges represent reporting lines and information flow.

## Node Properties

- `headcount`, `budget`, `productivity`, `morale`, `ai_adoption`, `backlog`

## Agents

5 department heads. Each observes their own department's state plus limited visibility of adjacent departments (information asymmetry — the CEO sees everything, department heads see neighbours only).

## Scenario Events

- **Tick 50**: "AI automation" — engineering's ai_adoption jumps, headcount_target drops 30%
- **Tick 100**: "Budget reallocation" — operations budget cut, engineering budget increased
- **Tick 200**: "Morale crisis" — if morale below threshold in any department, attrition spikes

## Why "Coming Soon"

This is the SignalStrata use case. It needs the information asymmetry (visibility) layer working properly, and the agent decisions are more nuanced (policy decisions, not buy/sell). It's the right example to add when Tier 2 lands.
