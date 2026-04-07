import type { TickSnapshot } from '../types'

interface Props {
  nodeId: string
  snapshot: TickSnapshot | null
}

export default function NodeDetail({ nodeId, snapshot }: Props) {
  const nodeData = snapshot?.nodes[nodeId]
  if (!nodeData) {
    return <div style={styles.container}><p style={styles.empty}>No data for {nodeId}</p></div>
  }

  const label = nodeData.metadata?.label || nodeId

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>{label}</h3>
      <div style={styles.props}>
        {Object.entries(nodeData.properties)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([key, value]) => (
            <div key={key} style={styles.row}>
              <span style={styles.key}>{key.replace(/_/g, ' ')}</span>
              <span style={styles.value}>
                {typeof value === 'number' ? value.toFixed(1) : String(value)}
              </span>
            </div>
          ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  title: {
    margin: '0 0 12px 0',
    color: '#e0e0e0',
    fontSize: 16,
  },
  empty: {
    color: '#888',
    fontSize: 13,
  },
  props: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 13,
  },
  key: {
    color: '#aaa',
    textTransform: 'capitalize' as const,
  },
  value: {
    color: '#e0e0e0',
    fontFamily: 'monospace',
  },
}
