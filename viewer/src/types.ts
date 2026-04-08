export interface NodeData {
  id: string
  properties: Record<string, number>
  metadata: Record<string, string>
}

export interface EdgeData {
  origin: string
  destination: string
  distance: number
  edge_type: string
}

export interface AgentSnapshot {
  location: string
  origin: string
  destination: string
  properties: Record<string, number>
  metadata: Record<string, string | number | boolean>
}

export interface TickSnapshot {
  tick: number
  nodes: Record<string, { properties: Record<string, number>; metadata: Record<string, string> }>
  agents: Record<string, AgentSnapshot>
}

export interface Topology {
  nodes: NodeData[]
  edges: EdgeData[]
}

export interface SimStatus {
  status: string
  current_tick: number
  total_ticks: number
  domain: string
  node_count: number
  agent_count: number
}
