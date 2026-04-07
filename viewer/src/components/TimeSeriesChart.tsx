import { useMemo } from 'react'
import type { TickSnapshot } from '../types'

interface Props {
  snapshots: TickSnapshot[]
  nodeId: string
  propertyKeys: string[]
}

const COLORS = ['#4a9eff', '#ff8c42', '#66bb6a', '#e53935', '#ab47bc', '#fdd835', '#26c6da', '#ff7043']

export default function TimeSeriesChart({ snapshots, nodeId, propertyKeys }: Props) {
  const series = useMemo(() => {
    return propertyKeys.map((key, i) => ({
      key,
      color: COLORS[i % COLORS.length],
      values: snapshots.map(s => s.nodes[nodeId]?.properties[key] ?? 0),
    }))
  }, [snapshots, nodeId, propertyKeys])

  if (snapshots.length < 2 || series.length === 0) {
    return <div style={{ color: '#888', fontSize: 13, padding: 16 }}>Waiting for data...</div>
  }

  // Chart dimensions
  const W = 560
  const H = 200
  const padL = 50
  const padR = 10
  const padT = 10
  const padB = 25
  const plotW = W - padL - padR
  const plotH = H - padT - padB

  // Find global min/max across all series
  let allMin = Infinity
  let allMax = -Infinity
  for (const s of series) {
    for (const v of s.values) {
      if (v < allMin) allMin = v
      if (v > allMax) allMax = v
    }
  }
  if (allMin === allMax) { allMin -= 1; allMax += 1 }
  const range = allMax - allMin

  const xScale = (i: number) => padL + (i / (snapshots.length - 1)) * plotW
  const yScale = (v: number) => padT + plotH - ((v - allMin) / range) * plotH

  // Downsample for performance if many points
  const step = Math.max(1, Math.floor(snapshots.length / 300))

  return (
    <div style={styles.container}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(frac => {
          const y = padT + plotH * (1 - frac)
          const val = allMin + range * frac
          return (
            <g key={frac}>
              <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="#333" strokeWidth={0.5} />
              <text x={padL - 5} y={y + 3} fill="#888" fontSize="9" textAnchor="end">
                {val.toFixed(0)}
              </text>
            </g>
          )
        })}

        {/* Series */}
        {series.map(s => {
          const points = s.values
            .filter((_, i) => i % step === 0 || i === s.values.length - 1)
            .map((v, idx) => {
              const origIdx = idx * step
              return `${xScale(origIdx)},${yScale(v)}`
            })
            .join(' ')

          return (
            <polyline
              key={s.key}
              points={points}
              fill="none"
              stroke={s.color}
              strokeWidth={1.5}
              opacity={0.9}
            />
          )
        })}

        {/* X-axis tick labels */}
        {[0, 0.25, 0.5, 0.75, 1].map(frac => {
          const idx = Math.floor(frac * (snapshots.length - 1))
          const tick = snapshots[idx]?.tick ?? 0
          return (
            <text key={frac} x={xScale(idx)} y={H - 3} fill="#888" fontSize="9" textAnchor="middle">
              {tick}
            </text>
          )
        })}
      </svg>

      {/* Legend */}
      <div style={styles.legend}>
        {series.map(s => (
          <div key={s.key} style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: s.color }} />
            <span style={styles.legendLabel}>{s.key.replace(/_/g, ' ')}</span>
            <span style={styles.legendValue}>{s.values[s.values.length - 1]?.toFixed(1)}</span>
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
    padding: 12,
    marginBottom: 12,
  },
  legend: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 8,
    paddingLeft: 50,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    display: 'inline-block',
  },
  legendLabel: {
    color: '#aaa',
    fontSize: 11,
    textTransform: 'capitalize' as const,
  },
  legendValue: {
    color: '#e0e0e0',
    fontSize: 11,
    fontFamily: 'monospace',
  },
}
