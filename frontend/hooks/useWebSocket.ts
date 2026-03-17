'use client'

import { useCallback, useEffect, useRef } from 'react'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MessageHandler = (msg: any) => void

export function useWebSocket(url: string, onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handlerRef = useRef(onMessage)
  handlerRef.current = onMessage

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (timerRef.current) clearTimeout(timerRef.current)
      }

      ws.onmessage = (ev) => {
        try {
          handlerRef.current(JSON.parse(ev.data))
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        timerRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    } catch {
      timerRef.current = setTimeout(connect, 3000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])
}
