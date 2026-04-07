import type { TickSnapshot } from '../types'

interface Props {
  snapshot: TickSnapshot | null
}

export default function AgentList({ snapshot }: Props) {
  if (!snapshot) return null

  const agents = Object.entries(snapshot.agents)

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Agents ({agents.length})</h3>
      <div style={styles.table}>
        <div style={styles.headerRow}>
          <span style={{ ...styles.cell, ...styles.headerCell, flex: 2 }}>ID</span>
          <span style={{ ...styles.cell, ...styles.headerCell, flex: 2 }}>Location</span>
          <span style={{ ...styles.cell, ...styles.headerCell, flex: 3 }}>Key Properties</span>
        </div>
        {agents.map(([aid, agent]) => {
          // Show most interesting properties (skip internal ones)
          const props = Object.entries(agent.properties)
            .filter(([k]) => !['status', 'eta', 'speed'].includes(k))
            .slice(0, 3)
            .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'number' ? v.toFixed(0) : v}`)
            .join(', ')

          return (
            <div key={aid} style={styles.row}>
              <span style={{ ...styles.cell, flex: 2, color: '#e0e0e0' }}>{aid}</span>
              <span style={{ ...styles.cell, flex: 2, color: '#4a9eff' }}>{agent.location}</span>
              <span style={{ ...styles.cell, flex: 3, color: '#aaa', fontSize: 12 }}>{props}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: 8,
    padding: 16,
  },
  title: {
    margin: '0 0 12px 0',
    color: '#e0e0e0',
    fontSize: 16,
  },
  table: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  headerRow: {
    display: 'flex',
    borderBottom: '1px solid #333',
    paddingBottom: 4,
    marginBottom: 4,
  },
  row: {
    display: 'flex',
    padding: '4px 0',
    borderBottom: '1px solid #1a1a2e',
  },
  cell: {
    fontSize: 13,
    fontFamily: 'monospace',
  },
  headerCell: {
    color: '#888',
    fontSize: 11,
    textTransform: 'uppercase' as const,
    fontFamily: 'sans-serif',
    letterSpacing: 1,
  },
}
