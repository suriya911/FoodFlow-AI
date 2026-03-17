'use client'

import { useState } from 'react'
import { forceModelFallback, forceModelRestore } from '@/lib/api'
import type { ModelStatus } from '@/lib/types'

function statusDot(status: string) {
  if (status === 'active')  return 'bg-green-400 animate-pulse'
  if (status === 'error')   return 'bg-red-400'
  return 'bg-gray-600'
}

function statusLabel(status: string) {
  if (status === 'active')  return 'text-green-400'
  if (status === 'error')   return 'text-red-400'
  return 'text-gray-500'
}

interface Props {
  modelStatus: ModelStatus | null
  onStatusChange: (s: ModelStatus) => void
}

export default function ModelStatusPanel({ modelStatus, onStatusChange }: Props) {
  const [loading, setLoading] = useState<'fallback' | 'restore' | null>(null)

  async function handleFallback() {
    setLoading('fallback')
    try {
      const res = await forceModelFallback()
      if (res.status) onStatusChange(res.status)
    } finally {
      setLoading(null)
    }
  }

  async function handleRestore() {
    setLoading('restore')
    try {
      const res = await forceModelRestore()
      if (res.status) onStatusChange(res.status)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-800 flex-shrink-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Model Router</span>
        {modelStatus && (
          <span className="ml-2 text-[10px] text-green-400 font-mono">
            Active: {modelStatus.active_model}
          </span>
        )}
        <div className="ml-auto flex gap-1.5">
          <button
            onClick={handleFallback}
            disabled={!!loading}
            className="px-2 py-0.5 text-[10px] rounded bg-orange-900/60 hover:bg-orange-800/60 text-orange-300 font-semibold transition disabled:opacity-50"
            title="Advance to next model tier"
          >
            {loading === 'fallback' ? '…' : '↓ Fallback'}
          </button>
          <button
            onClick={handleRestore}
            disabled={!!loading}
            className="px-2 py-0.5 text-[10px] rounded bg-green-900/60 hover:bg-green-800/60 text-green-300 font-semibold transition disabled:opacity-50"
            title="Restore to base Nemotron tier"
          >
            {loading === 'restore' ? '…' : '↑ Restore'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {!modelStatus ? (
          <div className="px-3 py-4 text-gray-600 text-center text-xs">Loading model status…</div>
        ) : (
          <>
            {/* Tier table */}
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-gray-600 border-b border-gray-800">
                  <th className="px-3 py-1 text-left font-normal">Model</th>
                  <th className="px-3 py-1 text-left font-normal">Tier</th>
                  <th className="px-3 py-1 text-right font-normal">Calls</th>
                  <th className="px-3 py-1 text-right font-normal">Errors</th>
                  <th className="px-3 py-1 text-right font-normal">Avg ms</th>
                </tr>
              </thead>
              <tbody>
                {modelStatus.tiers.map((tier) => (
                  <tr
                    key={tier.tier}
                    className={`border-b border-gray-900/60 ${tier.status === 'active' ? 'bg-green-950/30' : ''}`}
                  >
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusDot(tier.status)}`} />
                        <span className={`font-semibold ${statusLabel(tier.status)}`}>{tier.name}</span>
                      </div>
                      <div className="text-gray-600 text-[10px] pl-3">{tier.description}</div>
                    </td>
                    <td className={`px-3 py-1.5 font-mono uppercase text-[10px] ${statusLabel(tier.status)}`}>
                      {tier.status}
                    </td>
                    <td className="px-3 py-1.5 text-right text-gray-400 font-mono">{tier.calls}</td>
                    <td className={`px-3 py-1.5 text-right font-mono ${tier.errors > 0 ? 'text-red-400' : 'text-gray-600'}`}>
                      {tier.errors}
                    </td>
                    <td className="px-3 py-1.5 text-right text-gray-400 font-mono">
                      {tier.avg_latency_ms > 0 ? tier.avg_latency_ms.toFixed(0) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Switch log */}
            {modelStatus.switch_log.length > 0 && (
              <div className="mt-1">
                <div className="px-3 py-1 text-[10px] text-gray-600 uppercase tracking-wider font-semibold border-b border-gray-900">
                  Switch Log
                </div>
                {[...modelStatus.switch_log].reverse().slice(0, 5).map((entry, i) => (
                  <div key={i} className="px-3 py-1 border-b border-gray-900/40 text-[11px]">
                    <span className="text-orange-400">{entry.from_tier}</span>
                    <span className="text-gray-600"> → </span>
                    <span className="text-green-400">{entry.to_tier}</span>
                    <span className="text-gray-600 ml-2">{entry.reason}</span>
                    <div className="text-gray-700 text-[10px] font-mono">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
