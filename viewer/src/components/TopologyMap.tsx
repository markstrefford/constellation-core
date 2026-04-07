import { useMemo } from 'react'
import type { Topology, TickSnapshot } from '../types'

interface Props {
  topology: Topology
  snapshot: TickSnapshot | null
  selectedNode: string | null
  onSelectNode: (id: string | null) => void
}

interface NodePos {
  x: number
  y: number
}

function layoutNodes(topology: Topology): Record<string, NodePos> {
  const positions: Record<string, NodePos> = {}
  const n = topology.nodes.length
  if (n === 0) return positions

  if (n === 1) {
    positions[topology.nodes[0].id] = { x: 400, y: 300 }
    return positions
  }

  // Force-directed-ish layout using adjacency
  // Start with circle layout, then nudge based on edges
  const cx = 400
  const cy = 300
  const radius = Math.min(250, 80 * n)

  topology.nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2
    positions[node.id] = {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })

  // Simple spring iterations to improve layout
  for (let iter = 0; iter < 50; iter++) {
    const forces: Record<string, { fx: number; fy: number }> = {}
    for (const node of topology.nodes) {
      forces[node.id] = { fx: 0, fy: 0 }
    }

    // Repulsion between all pairs
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = topology.nodes[i].id
        const b = topology.nodes[j].id
        const dx = positions[b].x - positions[a].x
        const dy = positions[b].y - positions[a].y
        const dist = Math.sqrt(dx * dx + dy * dy) + 1
        const force = 5000 / (dist * dist)
        forces[a].fx -= (dx / dist) * force
        forces[a].fy -= (dy / dist) * force
        forces[b].fx += (dx / dist) * force
        forces[b].fy += (dy / dist) * force
      }
    }

    // Attraction along edges
    for (const edge of topology.edges) {
      const a = edge.origin
      const b = edge.destination
      if (!positions[a] || !positions[b]) continue
      const dx = positions[b].x - positions[a].x
      const dy = positions[b].y - positions[a].y
      const dist = Math.sqrt(dx * dx + dy * dy) + 1
      const idealDist = 60 + edge.distance * 8
      const force = (dist - idealDist) * 0.01
      if (forces[a] && forces[b]) {
        forces[a].fx += (dx / dist) * force
        forces[a].fy += (dy / dist) * force
        forces[b].fx -= (dx / dist) * force
        forces[b].fy -= (dy / dist) * force
      }
    }

    // Center gravity
    for (const node of topology.nodes) {
      const pos = positions[node.id]
      forces[node.id].fx += (cx - pos.x) * 0.005
      forces[node.id].fy += (cy - pos.y) * 0.005
    }

    // Apply forces
    for (const node of topology.nodes) {
      const f = forces[node.id]
      positions[node.id].x += Math.max(-10, Math.min(10, f.fx))
      positions[node.id].y += Math.max(-10, Math.min(10, f.fy))
      // Clamp to viewport
      positions[node.id].x = Math.max(60, Math.min(740, positions[node.id].x))
      positions[node.id].y = Math.max(60, Math.min(540, positions[node.id].y))
    }
  }

  return positions
}

const EDGE_TYPE_COLORS: Record<string, string> = {
  ocean: '#4a9eff',
  road: '#888',
  default: '#666',
}

const NODE_TYPE_COLORS: Record<string, string> = {
  port: '#4a9eff',
  factory: '#ff8c42',
  retail: '#66bb6a',
  exchange: '#ab47bc',
}

export default function TopologyMap({ topology, snapshot, selectedNode, onSelectNode }: Props) {
  const positions = useMemo(() => layoutNodes(topology), [topology])

  // Count agents per node
  const agentsAtNode: Record<string, string[]> = {}
  if (snapshot) {
    for (const [aid, agent] of Object.entries(snapshot.agents)) {
      const loc = agent.location
      if (!agentsAtNode[loc]) agentsAtNode[loc] = []
      agentsAtNode[loc].push(aid)
    }
  }

  return (
    <svg viewBox="0 0 800 600" style={{ width: '100%', height: '100%', background: '#1a1a2e' }}>
      {/* Edges */}
      {topology.edges.map((edge, i) => {
        const from = positions[edge.origin]
        const to = positions[edge.destination]
        if (!from || !to) return null
        const color = EDGE_TYPE_COLORS[edge.edge_type] || '#666'
        return (
          <g key={`edge-${i}`}>
            <line
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke={color}
              strokeWidth={1.5}
              opacity={0.6}
            />
            {/* Distance label */}
            <text
              x={(from.x + to.x) / 2}
              y={(from.y + to.y) / 2 - 6}
              fill="#888"
              fontSize="10"
              textAnchor="middle"
            >
              {edge.distance}
            </text>
          </g>
        )
      })}

      {/* Nodes */}
      {topology.nodes.map((node) => {
        const pos = positions[node.id]
        if (!pos) return null
        const meta = snapshot?.nodes[node.id]?.metadata || node.metadata
        const nodeType = (meta?.type as string) || 'default'
        const color = NODE_TYPE_COLORS[nodeType] || '#aaa'
        const isSelected = selectedNode === node.id
        const agentCount = agentsAtNode[node.id]?.length || 0
        const label = (meta?.label as string) || node.id

        return (
          <g
            key={node.id}
            style={{ cursor: 'pointer' }}
            onClick={() => onSelectNode(isSelected ? null : node.id)}
          >
            {/* Node circle */}
            <circle
              cx={pos.x} cy={pos.y}
              r={isSelected ? 28 : 22}
              fill={color}
              opacity={isSelected ? 1 : 0.85}
              stroke={isSelected ? '#fff' : 'none'}
              strokeWidth={2}
            />
            {/* Label */}
            <text
              x={pos.x} y={pos.y - 30}
              fill="#e0e0e0"
              fontSize="11"
              textAnchor="middle"
              fontWeight={isSelected ? 'bold' : 'normal'}
            >
              {label}
            </text>
            {/* Agent count badge */}
            {agentCount > 0 && (
              <>
                <circle
                  cx={pos.x + 18} cy={pos.y - 14}
                  r={9}
                  fill="#e53935"
                />
                <text
                  x={pos.x + 18} y={pos.y - 10}
                  fill="#fff"
                  fontSize="10"
                  textAnchor="middle"
                  fontWeight="bold"
                >
                  {agentCount}
                </text>
              </>
            )}
          </g>
        )
      })}
    </svg>
  )
}
