import { useState, useEffect, useRef, useCallback } from 'react'
import type { TickSnapshot } from '../types'

export function useSSE(url: string) {
  const [snapshots, setSnapshots] = useState<TickSnapshot[]>([])
  const [connected, setConnected] = useState(false)
  const [complete, setComplete] = useState(false)
  const [domain, setDomain] = useState('')
  const eventSourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'init') {
          setDomain(data.domain || '')
        } else if (data.type === 'tick') {
          setSnapshots(prev => [...prev, data as TickSnapshot])
        } else if (data.type === 'complete') {
          setComplete(true)
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
    }
  }, [url])

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close()
    }
  }, [])

  return { snapshots, connected, complete, domain, connect }
}
