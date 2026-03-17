'use client'

import { useState } from 'react'
import { manualOverride } from '@/lib/api'
import type { Center, DispatchDecision, RideDestination, SurplusSignal, Volunteer, WorldState } from '@/lib/types'

function statusBadge(status: DispatchDecision['status']) {
  switch (status) {
    case 'active':
      return <span className="px-1.5 py-0.5 text-[10px] rounded bg-blue-500/20 text-blue-400 border border-blue-500/40 font-semibold">ACTIVE</span>
    case 'delivering':
      return <span className="px-1.5 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-400 border border-yellow-500/40 font-semibold">DELIVERING</span>
    case 'completed':
      return <span className="px-1.5 py-0.5 text-[10px] rounded bg-green-500/20 text-green-400 border border-green-500/40 font-semibold">DONE ✓</span>
    case 'cancelled':
      return <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-700 text-gray-400 border border-gray-600 font-semibold">CANCELLED</span>
  }
}

interface OverrideState {
  dispatchId: string
  signalId: string
  centerId: string
  volunteerId: string
  loading: boolean
}

interface Props {
  dispatches: DispatchDecision[]
  signals: SurplusSignal[]
  world: WorldState | null
}

export default function DispatchBoard({ dispatches, signals, world }: Props) {
  const [override, setOverride] = useState<OverrideState | null>(null)

  async function applyOverride() {
    if (!override) return
    setOverride((o) => o && { ...o, loading: true })
    try {
      await manualOverride(override.signalId, override.centerId, override.volunteerId)
      setOverride(null)
    } catch {
      setOverride((o) => o && { ...o, loading: false })
    }
  }

  const visible = dispatches.slice(0, 10)
  const availableVolunteers: Volunteer[] = world?.volunteers.filter((v) => v.available) ?? []
  const centers: Center[] = world?.centers ?? []
  const rideDestinations: RideDestination[] = world?.ride_destinations ?? []

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 flex-shrink-0">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">🚚 Dispatch Board</span>
        <span className="ml-auto text-xs text-gray-500">{dispatches.length} total</span>
      </div>

      {visible.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
          <span className="text-2xl">🚚</span>
          <span>No active dispatches</span>
          <span className="text-xs">Nemotron is waiting for signals…</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto panel-scroll space-y-1.5 p-2">
          {visible.map((d) => {
            const vol = world?.volunteers.find((v) => v.id === d.volunteer_id)
            const isTransport = d.stream === 'transport'
            const destName = isTransport
              ? (rideDestinations.find((r) => r.id === d.center_id)?.name ?? d.center_name ?? d.center_id)
              : (centers.find((c) => c.id === d.center_id)?.name ?? d.center_name ?? d.center_id)
            const isOverriding = override?.dispatchId === d.id

            return (
              <div
                key={d.id}
                className={`rounded-lg border p-2.5 transition-all animate-fade-in ${
                  d.status === 'completed' || d.status === 'cancelled'
                    ? 'bg-gray-900/30 border-gray-800 opacity-60'
                    : isTransport
                    ? 'bg-cyan-950/20 border-cyan-900/40'
                    : 'bg-gray-900 border-gray-700'
                }`}
              >
                {/* Header */}
                <div className="flex items-center gap-1.5 mb-1.5">
                  {statusBadge(d.status)}
                  <span className="text-[10px] px-1 rounded font-semibold bg-gray-800 text-gray-400 flex-shrink-0">
                    {isTransport ? '🚖' : '🍽️'}
                  </span>
                  <span className="text-xs font-medium text-white truncate flex-1">
                    {d.source_name}
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {(d.priority_score * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Route */}
                <div className="flex items-center gap-1 text-[11px] text-gray-400 mb-1.5 flex-wrap">
                  <span className="text-blue-400">👤 {vol?.name ?? d.volunteer_name}</span>
                  <span className="text-gray-600 mx-0.5">→</span>
                  <span className="text-orange-400">📍 {d.source_name}</span>
                  <span className="text-gray-600 mx-0.5">→</span>
                  <span className={isTransport ? 'text-pink-400' : 'text-green-400'}>
                    {isTransport ? '🏥' : '🏠'} {destName}
                  </span>
                </div>

                {/* Food details */}
                {!isTransport && (
                  <div className="text-[11px] text-gray-500 mb-1.5">
                    🍱 {d.food_type} · {d.meals} meals · ⏱ {d.spoilage_minutes}m
                  </div>
                )}

                {/* Transport details */}
                {isTransport && (
                  <div className="text-[11px] text-gray-500 mb-1.5">
                    👤 {d.passenger_name} · {d.passenger_count} pax · {d.urgency_reason?.replace('_', ' ')}
                  </div>
                )}

                {/* Nemotron rationale */}
                {d.rationale && (
                  <div className="text-[10px] text-gray-500 bg-gray-800/60 rounded px-2 py-1 mb-1.5 italic leading-relaxed">
                    🤖 {d.rationale}
                  </div>
                )}

                {/* Override controls — food only (ride destinations are fixed) */}
                {d.status === 'active' && !isTransport && (
                  <div>
                    {!isOverriding ? (
                      <button
                        onClick={() =>
                          setOverride({
                            dispatchId: d.id,
                            signalId: d.signal_id,
                            centerId: d.center_id,
                            volunteerId: d.volunteer_id,
                            loading: false,
                          })
                        }
                        className="text-[10px] px-2 py-0.5 rounded border border-gray-700 text-gray-400 hover:border-orange-500/50 hover:text-orange-400 transition"
                      >
                        Override
                      </button>
                    ) : (
                      <div className="mt-1 space-y-1">
                        <select
                          value={override.centerId}
                          onChange={(e) => setOverride((o) => o && { ...o, centerId: e.target.value })}
                          className="w-full bg-gray-800 border border-gray-700 text-xs text-white rounded px-1.5 py-0.5"
                        >
                          {centers.map((c) => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                          ))}
                        </select>
                        <select
                          value={override.volunteerId}
                          onChange={(e) => setOverride((o) => o && { ...o, volunteerId: e.target.value })}
                          className="w-full bg-gray-800 border border-gray-700 text-xs text-white rounded px-1.5 py-0.5"
                        >
                          {availableVolunteers.map((v) => (
                            <option key={v.id} value={v.id}>{v.name}</option>
                          ))}
                          {availableVolunteers.length === 0 && (
                            <option value={d.volunteer_id}>{vol?.name ?? d.volunteer_id} (current)</option>
                          )}
                        </select>
                        <div className="flex gap-1">
                          <button
                            onClick={applyOverride}
                            disabled={override.loading}
                            className="flex-1 text-[10px] px-2 py-0.5 rounded bg-orange-600 hover:bg-orange-500 text-white font-semibold disabled:opacity-50 transition"
                          >
                            {override.loading ? 'Applying…' : 'Apply'}
                          </button>
                          <button
                            onClick={() => setOverride(null)}
                            className="text-[10px] px-2 py-0.5 rounded border border-gray-700 text-gray-400 hover:text-white transition"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
