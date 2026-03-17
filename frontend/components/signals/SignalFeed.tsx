'use client'

import { useEffect, useState } from 'react'
import type { SurplusSignal } from '@/lib/types'

function urgencyLabel(score: number): { label: string; cls: string } {
  if (score >= 0.7) return { label: 'URGENT', cls: 'bg-red-500/20 text-red-400 border-red-500/40' }
  if (score >= 0.4) return { label: 'MODERATE', cls: 'bg-orange-500/20 text-orange-400 border-orange-500/40' }
  return { label: 'LOW', cls: 'bg-green-500/20 text-green-400 border-green-500/40' }
}

function urgencyBar(score: number): string {
  if (score >= 0.7) return 'bg-red-500'
  if (score >= 0.4) return 'bg-orange-400'
  return 'bg-green-400'
}

function statusDot(status: SurplusSignal['status']): string {
  if (status === 'assigned') return 'bg-blue-400'
  if (status === 'delivered') return 'bg-gray-500'
  return 'bg-orange-400 animate-pulse'
}

function timeAgo(iso: string): string {
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (secs < 60) return `${secs}s ago`
  return `${Math.floor(secs / 60)}m ago`
}

interface Props {
  signals: SurplusSignal[]
}

export default function SignalFeed({ signals }: Props) {
  const [, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 5000)
    return () => clearInterval(id)
  }, [])

  const visible = signals.slice(0, 12)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 flex-shrink-0">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">📡 Signal Feed</span>
        <span className="ml-auto text-xs text-gray-500">{signals.length} total</span>
      </div>

      {visible.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
          <span className="text-2xl">📡</span>
          <span>Awaiting signals…</span>
          <span className="text-xs">Start the simulation to see live events</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto panel-scroll space-y-1 p-2">
          {visible.map((sig) => {
            const urg = urgencyLabel(sig.urgency_score)
            const isTransport = sig.stream === 'transport'
            return (
              <div
                key={sig.id}
                className={`rounded-lg border p-2.5 transition-all animate-slide-in ${
                  sig.status === 'delivered'
                    ? 'bg-gray-900/40 border-gray-800 opacity-50'
                    : sig.status === 'assigned'
                    ? isTransport
                      ? 'bg-cyan-950/30 border-cyan-800/40'
                      : 'bg-blue-950/30 border-blue-800/40'
                    : 'bg-gray-900 border-gray-700'
                }`}
              >
                {/* Header row */}
                <div className="flex items-center gap-1.5 mb-1">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot(sig.status)}`} />
                  <span className="text-[10px] px-1 rounded font-semibold flex-shrink-0 bg-gray-800 text-gray-400">
                    {isTransport ? '🚖 RIDE' : '🍽️ FOOD'}
                  </span>
                  <span className="text-xs font-medium text-white truncate flex-1">
                    {sig.source_name}
                  </span>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${urg.cls}`}>
                    {urg.label}
                  </span>
                </div>

                {/* Details — food */}
                {!isTransport && (
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span>🍱 {sig.food_type}</span>
                    <span>×{sig.meals}</span>
                    <span className={sig.spoilage_minutes <= 45 ? 'text-red-400' : 'text-gray-400'}>
                      ⏱ {sig.spoilage_minutes}m
                    </span>
                    <span className="ml-auto text-gray-600">{timeAgo(sig.timestamp)}</span>
                  </div>
                )}

                {/* Details — transport */}
                {isTransport && (
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span>👤 {sig.passenger_name}</span>
                    <span className="text-gray-600">→ {sig.destination_name}</span>
                    <span className="ml-auto text-gray-600">{timeAgo(sig.timestamp)}</span>
                  </div>
                )}

                {/* Urgency bar */}
                <div className="mt-1.5 h-1 rounded-full bg-gray-800">
                  <div
                    className={`h-1 rounded-full transition-all ${urgencyBar(sig.urgency_score)}`}
                    style={{ width: `${sig.urgency_score * 100}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
