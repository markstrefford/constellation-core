import { useState, useEffect, useMemo } from 'react'
import { useSSE } from './hooks/useSSE'
import TopologyMap from './components/TopologyMap'
import NodeDetail from './components/NodeDetail'
import AgentList from './components/AgentList'
import TickBar from './components/TickBar'
import TimeSeriesChart from './components/TimeSeriesChart'
import type { Topology, SimStatus } from './types'

export default function App() {
  const [topology, setTopology] = useState<Topology | null>(null)
  const [status, setStatus] = useState<SimStatus | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [chartKeys, setChartKeys] = useState<string[]>([])
  const [started, setStarted] = useState(false)

  const { snapshots, complete, domain, connect } = useSSE('/api/events')

  const currentSnapshot = snapshots.length > 0 ? snapshots[snapshots.length - 1] : null

  // Fetch topology on mount
  useEffect(() => {
    fetch('/api/topology')
      .then(r => r.json())
      .then(setTopology)
      .catch(() => {})

    fetch('/api/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
  }, [])

  // Auto-select chart keys based on first snapshot
  useEffect(() => {
    if (chartKeys.length > 0 || !currentSnapshot || !selectedNode) return
    const props = currentSnapshot.nodes[selectedNode]?.properties
    if (props) {
      // Pick properties that look like prices or stocks (most interesting to chart)
      const interesting = Object.keys(props).filter(k =>
        k.includes('price') || k.includes('stock') || k.includes('sentiment')
      )
      setChartKeys(interesting.length > 0 ? interesting.slice(0, 6) : Object.keys(props).slice(0, 4))
    }
  }, [currentSnapshot, selectedNode, chartKeys.length])

  // Reset chart keys when node changes
  useEffect(() => {
    setChartKeys([])
  }, [selectedNode])

  // Available property keys for the selected node
  const availableKeys = useMemo(() => {
    if (!currentSnapshot || !selectedNode) return []
    const props = currentSnapshot.nodes[selectedNode]?.properties
    return props ? Object.keys(props).sort() : []
  }, [currentSnapshot, selectedNode])

  const handleStart = async () => {
    connect()
    await fetch('/api/start', { method: 'POST' })
    setStarted(true)
    // Refresh status
    const s = await fetch('/api/status').then(r => r.json())
    setStatus(s)
  }

  const toggleChartKey = (key: string) => {
    setChartKeys(prev =>
      prev.includes(key)
        ? prev.filter(k => k !== key)
        : [...prev, key]
    )
  }

  return (
    <div style={styles.root}>
      {/* Header */}
      <TickBar
        currentTick={currentSnapshot?.tick ?? 0}
        totalTicks={status?.total_ticks ?? 0}
        isRunning={started && !complete}
        isComplete={complete}
        domain={domain || status?.domain || ''}
      />

      <div style={styles.layout}>
        {/* Left: Topology Map */}
        <div style={styles.mapPanel}>
          {topology ? (
            <TopologyMap
              topology={topology}
              snapshot={currentSnapshot}
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
            />
          ) : (
            <div style={styles.placeholder}>Loading topology...</div>
          )}

          {!started && (
            <div style={styles.startOverlay}>
              <button onClick={handleStart} style={styles.startButton}>
                Start Simulation
              </button>
              <p style={styles.startHint}>
                {status?.node_count ?? '?'} nodes, {status?.agent_count ?? '?'} agents
              </p>
            </div>
          )}
        </div>

        {/* Right: Details */}
        <div style={styles.detailPanel}>
          {selectedNode ? (
            <>
              <NodeDetail nodeId={selectedNode} snapshot={currentSnapshot} />

              {/* Property selector for chart */}
              <div style={styles.chartSelector}>
                <span style={styles.chartSelectorLabel}>Chart:</span>
                <div style={styles.chipContainer}>
                  {availableKeys.map(key => (
                    <button
                      key={key}
                      onClick={() => toggleChartKey(key)}
                      style={{
                        ...styles.chip,
                        background: chartKeys.includes(key) ? '#4a9eff' : '#1a1a2e',
                        color: chartKeys.includes(key) ? '#fff' : '#aaa',
                      }}
                    >
                      {key.replace(/_/g, ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {chartKeys.length > 0 && snapshots.length > 1 && (
                <TimeSeriesChart
                  snapshots={snapshots}
                  nodeId={selectedNode}
                  propertyKeys={chartKeys}
                />
              )}
            </>
          ) : (
            <div style={styles.noSelection}>
              <p style={{ color: '#888', fontSize: 14 }}>
                Click a node to view details and charts
              </p>
            </div>
          )}

          <AgentList snapshot={currentSnapshot} />
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    background: '#0f0f23',
    color: '#e0e0e0',
    minHeight: '100vh',
    padding: 16,
  },
  layout: {
    display: 'flex',
    gap: 16,
    height: 'calc(100vh - 80px)',
  },
  mapPanel: {
    flex: 3,
    position: 'relative',
    background: '#16213e',
    borderRadius: 8,
    overflow: 'hidden',
  },
  detailPanel: {
    flex: 2,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  placeholder: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#888',
    fontSize: 16,
  },
  startOverlay: {
    position: 'absolute',
    bottom: 20,
    left: '50%',
    transform: 'translateX(-50%)',
    textAlign: 'center',
  },
  startButton: {
    background: '#4a9eff',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '12px 32px',
    fontSize: 16,
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  startHint: {
    color: '#888',
    fontSize: 13,
    marginTop: 8,
  },
  noSelection: {
    background: '#16213e',
    borderRadius: 8,
    padding: 24,
    textAlign: 'center',
  },
  chartSelector: {
    background: '#16213e',
    borderRadius: 8,
    padding: '8px 12px',
  },
  chartSelectorLabel: {
    color: '#888',
    fontSize: 11,
    textTransform: 'uppercase' as const,
    letterSpacing: 1,
  },
  chipContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 6,
  },
  chip: {
    border: '1px solid #333',
    borderRadius: 12,
    padding: '3px 10px',
    fontSize: 11,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
}
