import { useCallback, useEffect, useRef, useState } from 'react'
import { tokenStore } from '../lib/api'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

interface SSEState<T> {
  data: T | null
  connected: boolean
  error: string | null
}

/**
 * Streams SSE from a JWT-protected endpoint using fetch + ReadableStream,
 * since EventSource doesn't support custom headers.
 */
export function useSSE<T = Record<string, unknown>>(path: string): SSEState<T> {
  const [state, setState] = useState<SSEState<T>>({
    data: null,
    connected: false,
    error: null,
  })
  const controllerRef = useRef<AbortController | null>(null)

  const connect = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    const token = tokenStore.getAccess()
    if (!token) return

    try {
      const response = await fetch(`${BASE_URL}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        setState((s) => ({ ...s, error: `HTTP ${response.status}`, connected: false }))
        return
      }

      setState((s) => ({ ...s, connected: true, error: null }))

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value, { stream: true })
        for (const line of text.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6)) as T
              setState((s) => ({ ...s, data: parsed }))
            } catch {
              // ignore malformed SSE line
            }
          }
        }
      }
      setState((s) => ({ ...s, connected: false }))
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setState((s) => ({ ...s, connected: false, error: 'Stream disconnected' }))
      }
    }
  }, [path])

  useEffect(() => {
    void connect()
    return () => controllerRef.current?.abort()
  }, [connect])

  return state
}
