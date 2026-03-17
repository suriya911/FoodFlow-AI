'use client'

import type { Metrics } from '@/lib/types'

interface StatCardProps {
  icon: string
  label: string
  value: string
  sub?: string
  highlight?: boolean
  color?: string
}

function StatCard({ icon, label, value, sub, highlight, color }: StatCardProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-2 rounded-lg border ${
        highlight
          ? 'bg-green-950/40 border-green-700/40'
          : 'bg-gray-900 border-gray-800'
      }`}
    >
      <span className="text-lg leading-none mb-0.5">{icon}</span>
      <span className={`text-lg font-bold leading-tight ${color ?? (highlight ? 'text-green-400' : 'text-white')}`}>
        {value}
      </span>
      <span className="text-[10px] text-gray-500 text-center leading-tight">{label}</span>
      {sub && <span className="text-[10px] text-gray-600">{sub}</span>}
    </div>
  )
}

interface Props {
  metrics: Metrics
}

export default function ImpactStats({ metrics }: Props) {
  const foodPct = metrics.total_dispatches > 0
    ? ((metrics.food_dispatches / metrics.total_dispatches) * 100).toFixed(0)
    : '0'
  const ridePct = metrics.total_dispatches > 0
    ? ((metrics.transport_dispatches / metrics.total_dispatches) * 100).toFixed(0)
    : '0'

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 flex-shrink-0">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Impact & Stats</span>
        <span className="ml-auto text-xs text-gray-500">
          {metrics.total_dispatches} dispatch{metrics.total_dispatches !== 1 ? 'es' : ''}
        </span>
      </div>

      <div className="p-2 grid grid-cols-2 gap-1.5">
        <StatCard
          icon="🍽️"
          label="Meals Saved"
          value={metrics.meals_saved.toLocaleString()}
          highlight={metrics.meals_saved > 0}
        />
        <StatCard
          icon="🚖"
          label="Rides Completed"
          value={metrics.rides_completed.toLocaleString()}
          color="text-cyan-400"
        />
        <StatCard
          icon="🌱"
          label="CO₂ Avoided"
          value={`${metrics.co2_avoided_kg.toFixed(1)}`}
          sub="kg"
        />
        <StatCard
          icon="✅"
          label="On-Time Rate"
          value={`${(metrics.on_time_rate * 100).toFixed(0)}%`}
          highlight={metrics.on_time_rate >= 0.9}
        />
        <StatCard
          icon="⚡"
          label="Avg Dispatch"
          value={`${metrics.avg_dispatch_time_mins.toFixed(1)}`}
          sub="min"
        />
        <StatCard
          icon="📊"
          label="Total Dispatches"
          value={metrics.total_dispatches.toLocaleString()}
        />
      </div>

      {/* Stream breakdown */}
      <div className="px-3 pb-3">
        <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5 font-semibold">
          Stream Breakdown
        </div>
        <div className="flex gap-2 text-[11px]">
          <div className="flex-1 bg-gray-900 rounded-lg p-2 border border-gray-800">
            <div className="text-green-400 font-bold text-base">{metrics.food_dispatches}</div>
            <div className="text-gray-500">🍽️ Food ({foodPct}%)</div>
          </div>
          <div className="flex-1 bg-gray-900 rounded-lg p-2 border border-gray-800">
            <div className="text-cyan-400 font-bold text-base">{metrics.transport_dispatches}</div>
            <div className="text-gray-500">🚖 SafeRide ({ridePct}%)</div>
          </div>
        </div>

        {/* Progress bar */}
        {metrics.total_dispatches > 0 && (
          <div className="mt-2 h-1.5 rounded-full bg-gray-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-cyan-500 transition-all duration-500"
              style={{ width: `${foodPct}%` }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
