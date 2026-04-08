import { useState, useEffect } from 'react'

interface Props {
  currentTick: number
  totalTicks: number
  isRunning: boolean
  isComplete: boolean
  domain: string
}

// Speed presets: label -> delay in seconds
const SPEED_PRESETS = [
  { label: '0.25x', delay: 1.0 },
  { label: '0.5x', delay: 0.5 },
  { label: '1x', delay: 0.2 },
  { label: '2x', delay: 0.1 },
  { label: '5x', delay: 0.04 },
  { label: '10x', delay: 0.02 },
]

export default function TickBar({ currentTick, totalTicks, isRunning, isComplete, domain }: Props) {
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0
  const [paused, setPaused] = useState(false)
  const [speedIndex, setSpeedIndex] = useState(2) // default 1x

  useEffect(() => {
    // Sync initial playback state from server
    fetch('/api/playback')
      .then(r => r.json())
      .then(data => {
        setPaused(data.paused || false)
        // Find closest speed preset
        const delay = data.tick_delay || 0.2
        const closest = SPEED_PRESETS.reduce((best, preset, i) =>
          Math.abs(preset.delay - delay) < Math.abs(SPEED_PRESETS[best].delay - delay) ? i : best
        , 0)
        setSpeedIndex(closest)
      })
      .catch(() => {})
  }, [])

  const togglePause = async () => {
    const endpoint = paused ? '/api/resume' : '/api/pause'
    await fetch(endpoint, { method: 'POST' })
    setPaused(!paused)
  }

  const changeSpeed = async (index: number) => {
    setSpeedIndex(index)
    const delay = SPEED_PRESETS[index].delay
    await fetch(`/api/speed?delay=${delay}`, { method: 'POST' })
  }

  return (
    <div style={styles.container}>
      <div style={styles.topRow}>
        <span style={styles.domain}>{domain || 'constellation-core'}</span>
        <span style={styles.tick}>
          Tick {currentTick} / {totalTicks}
        </span>
        <span style={{
          ...styles.status,
          color: isComplete ? '#66bb6a' : paused ? '#fdd835' : isRunning ? '#4a9eff' : '#888',
        }}>
          {isComplete ? 'Complete' : paused ? 'Paused' : isRunning ? 'Running' : 'Idle'}
        </span>
      </div>

      <div style={styles.progressBg}>
        <div style={{ ...styles.progressBar, width: `${progress}%` }} />
      </div>

      {/* Playback controls */}
      {isRunning && !isComplete && (
        <div style={styles.controls}>
          <button onClick={togglePause} style={styles.pauseBtn}>
            {paused ? 'Resume' : 'Pause'}
          </button>

          <div style={styles.speedRow}>
            <span style={styles.speedLabel}>Speed:</span>
            {SPEED_PRESETS.map((preset, i) => (
              <button
                key={preset.label}
                onClick={() => changeSpeed(i)}
                style={{
                  ...styles.speedBtn,
                  background: i === speedIndex ? '#4a9eff' : '#1a1a2e',
                  color: i === speedIndex ? '#fff' : '#aaa',
                }}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}
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
  topRow: {
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
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    marginTop: 10,
  },
  pauseBtn: {
    background: '#1a1a2e',
    color: '#e0e0e0',
    border: '1px solid #333',
    borderRadius: 6,
    padding: '4px 16px',
    fontSize: 13,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  speedRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  speedLabel: {
    color: '#888',
    fontSize: 12,
    marginRight: 4,
  },
  speedBtn: {
    border: '1px solid #333',
    borderRadius: 4,
    padding: '3px 8px',
    fontSize: 11,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
}
