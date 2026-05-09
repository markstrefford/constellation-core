# Frequently Asked Questions (FAQ)

## What makes Constellation different from LangChain?
LangChain is excellent for building individual intelligent agents that can use tools and reason through tasks. Constellation is designed to run **many** such agents inside a shared environment to see how they interact. Think of Constellation as the "World" that LangChain agents live in.

## How many agents can Constellation handle?
For simple heuristic agents, Constellation can handle thousands of agents in real-time. For LLM-driven agents, the bottleneck is usually the API rate limits and cost of the LLM provider.

## Can I use Constellation for reinforcement learning?
Yes. Constellation's environment-agent loop is very similar to the Gymnasium (OpenAI Gym) interface. You can wrap a Constellation simulation as a reinforcement learning environment to train agents.

## Does it support 3D visualization?
Not currently. The built-in viewer uses 2D graph layouts which are more suited for systemic analysis of supply chains, financial markets, and organizational structures.

## How do I handle large graphs?
Constellation uses a domain-agnostic graph structure. For very large graphs (millions of nodes), you may need to implement a custom `StorageBackend` or use a specialized graph database, as the current core is optimized for complexity of interaction rather than sheer node count.

## Can agents communicate with each other?
In the current version, agents communicate *indirectly* by changing the state of the world (e.g., buying a stock, moving a cargo container). Direct agent-to-agent messaging is a planned feature for a future release.

---

- **[Next: Contributing](contributing.md)**
- **[Back to Home](index.md)**
