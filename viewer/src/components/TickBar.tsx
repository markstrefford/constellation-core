interface Props {
  currentTick: number
  totalTicks: number
  isRunning: boolean
  isComplete: boolean
  domain: string
}

export default function TickBar({ currentTick, totalTicks, isRunning, isComplete, domain }: Props) {
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0

  return (
    <div style={styles.container}>
      <div style={styles.info}>
        <span style={styles.domain}>{domain || 'constellation-core'}</span>
        <span style={styles.tick}>
          Tick {currentTick} / {totalTicks}
        </span>
        <span style={{
          ...styles.status,
          color: isComplete ? '#66bb6a' : isRunning ? '#4a9eff' : '#888',
        }}>
          {isComplete ? 'Complete' : isRunning ? 'Running' : 'Idle'}
        </span>
      </div>
      <div style={styles.progressBg}>
        <div style={{ ...styles.progressBar, width: `${progress}%` }} />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#16213e',
    borderRadius: 8,
    padding: '12px 16px',
    marginBottom: 12,
  },
  info: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  domain: {
    color: '#e0e0e0',
    fontSize: 16,
    fontWeight: 'bold',
  },
  tick: {
    color: '#aaa',
    fontSize: 14,
    fontFamily: 'monospace',
  },
  status: {
    fontSize: 13,
    fontWeight: 'bold',
  },
  progressBg: {
    height: 4,
    background: '#1a1a2e',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    background: '#4a9eff',
    borderRadius: 2,
    transition: 'width 0.1s ease',
  },
}
