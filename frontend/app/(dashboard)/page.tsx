'use client'

import dynamic from 'next/dynamic'
import { useCallback, useEffect, useState } from 'react'
import { getState, getModelStatus, startSim, stopSim, tickSim, tickRide } from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import type {
  AgentTraceEntry, DispatchDecision, Metrics,
  ModelStatus, SurplusSignal, WorldState, WSMessage,
} from '@/lib/types'
import SignalFeed from '@/components/signals/SignalFeed'
import DispatchBoard from '@/components/dispatch/DispatchBoard'
import ImpactStats from '@/components/metrics/ImpactStats'
import AgentTrace from '@/components/monitor/AgentTrace'
import ModelStatusPanel from '@/components/monitor/ModelStatus'

// Leaflet must be client-only (no SSR)
const MapCanvas = dynamic(() => import('@/components/map/MapCanvas'), { ssr: false })

const WS_URL = (process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000') + '/ws/live'

const EMPTY_METRICS: Metrics = {
  meals_saved: 0,
  co2_avoided_kg: 0,
  rides_completed: 0,
  avg_dispatch_time_mins: 0,
  on_time_rate: 1,
  total_dispatches: 0,
  food_dispatches: 0,
  transport_dispatches: 0,
}

type Tab = 'live' | 'agents' | 'impact'

export default function DashboardPage() {
  const [world, setWorld]             = useState<WorldState | null>(null)
  const [signals, setSignals]         = useState<SurplusSignal[]>([])
  const [dispatches, setDispatches]   = useState<DispatchDecision[]>([])
  const [metrics, setMetrics]         = useState<Metrics>(EMPTY_METRICS)
  const [agentTrace, setAgentTrace]   = useState<AgentTraceEntry[]>([])
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null)
  const [simRunning, setSimRunning]   = useState(false)
  const [connected, setConnected]     = useState(false)
  const [ticking, setTicking]         = useState(false)
  const [tickingRide, setTickingRide] = useState(false)
  const [tab, setTab]                 = useState<Tab>('live')

  // Bootstrap from REST on mount
  useEffect(() => {
    getState()
      .then((state) => {
        setWorld(state)
        setSignals((state.active_signals ?? []).slice(0, 20))
        setDispatches((state.active_dispatches ?? []).slice(0, 20))
        setMetrics(state.metrics ?? EMPTY_METRICS)
        setSimRunning(state.sim_running ?? false)
      })
      .catch(() => {/* backend not ready yet — WS will sync */})

    getModelStatus().then(setModelStatus).catch(() => {})
  }, [])

  const handleMsg = useCallback((msg: WSMessage) => {
    setConnected(true)

    switch (msg.type) {
      case 'state':
        setWorld(msg.data)
        setSignals((msg.data.active_signals ?? []).slice(0, 20))
        setDispatches((msg.data.active_dispatches ?? []).slice(0, 20))
        setMetrics(msg.data.metrics ?? EMPTY_METRICS)
        setSimRunning(msg.data.sim_running)
        break

      case 'signal':
        setSignals((prev) => [msg.data, ...prev].slice(0, 20))
        break

      case 'dispatch':
        setDispatches((prev) => {
          const without = prev.filter((d) => d.id !== msg.data.id)
          return [msg.data, ...without].slice(0, 20)
        })
        break

      case 'volunteer_move':
        setWorld((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            volunteers: prev.volunteers.map((v) =>
              v.id === msg.data.volunteer_id
                ? { ...v, lat: msg.data.lat, lng: msg.data.lng, available: msg.data.available }
                : v,
            ),
          }
        })
        break

      case 'delivery_complete':
        setDispatches((prev) =>
          prev.map((d) =>
            d.id === msg.data.dispatch_id ? { ...d, status: 'completed' as const } : d,
          ),
        )
        setSignals((prev) =>
          prev.map((s) =>
            s.id === msg.data.signal_id ? { ...s, status: 'delivered' as const } : s,
          ),
        )
        break

      case 'metrics':
        setMetrics(msg.data)
        break

      case 'agent_trace':
        setAgentTrace((prev) => [...msg.data, ...prev].slice(0, 100))
        break

      case 'model_switch':
        setModelStatus(msg.data)
        break

      case 'sim_started':
        setSimRunning(true)
        break

      case 'sim_stopped':
        setSimRunning(false)
        break
    }
  }, [])

  useWebSocket(WS_URL, handleMsg)

  async function handleToggleSim() {
    if (simRunning) {
      await stopSim()
      setSimRunning(false)
    } else {
      await startSim()
      setSimRunning(true)
    }
  }

  async function handleTick() {
    setTicking(true)
    try { await tickSim() } finally { setTicking(false) }
  }

  async function handleTickRide() {
    setTickingRide(true)
    try { await tickRide() } finally { setTickingRide(false) }
  }

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 text-xs font-semibold rounded-md transition ${
      tab === t
        ? 'bg-gray-700 text-white'
        : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/60'
    }`

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-3 px-4 py-2 bg-gray-900/90 border-b border-gray-800 flex-shrink-0 backdrop-blur">
        {/* Brand */}
        <div className="flex items-center gap-2 mr-2">
          <span className="text-lg font-bold text-green-400 tracking-tight">🌱 FoodFlow AI</span>
          <div className="flex items-center gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse-slow' : 'bg-gray-600'}`} />
            <span className="text-[10px] text-gray-500 font-mono uppercase">
              {connected ? 'live' : 'connecting'}
            </span>
          </div>
        </div>

        {/* Active model badge */}
        {modelStatus && (
          <span className="hidden sm:inline text-[10px] px-2 py-0.5 rounded bg-green-950 text-green-400 font-mono border border-green-900/60">
            {modelStatus.active_model}
          </span>
        )}

        {/* Sim controls */}
        <div className="flex items-center gap-1.5 ml-2">
          <button
            onClick={handleToggleSim}
            className={`px-3 py-1 text-xs rounded-md font-semibold transition ${
              simRunning
                ? 'bg-red-600/80 hover:bg-red-500 text-white'
                : 'bg-green-700/80 hover:bg-green-600 text-white'
            }`}
          >
            {simRunning ? '⏹ Stop' : '▶ Start'} Sim
          </button>
          <button
            onClick={handleTick}
            disabled={ticking}
            className="px-3 py-1 text-xs rounded-md font-semibold bg-gray-700 hover:bg-gray-600 text-white transition disabled:opacity-50"
            title="Emit one food surplus signal"
          >
            {ticking ? '…' : '⚡ Food'}
          </button>
          <button
            onClick={handleTickRide}
            disabled={tickingRide}
            className="px-3 py-1 text-xs rounded-md font-semibold bg-cyan-800/80 hover:bg-cyan-700 text-white transition disabled:opacity-50"
            title="Emit one SafeRide transport signal"
          >
            {tickingRide ? '…' : '🚖 Ride'}
          </button>
        </div>

        {/* Quick metrics */}
        <div className="hidden sm:flex items-center gap-4 ml-auto text-xs text-gray-400">
          <span>
            <span className="text-green-400 font-semibold">{metrics.meals_saved}</span> meals
          </span>
          <span>
            <span className="text-cyan-400 font-semibold">{metrics.rides_completed}</span> rides
          </span>
          <span>
            <span className="text-emerald-400 font-semibold">{metrics.co2_avoided_kg.toFixed(1)}</span> kg CO₂
          </span>
          <span>
            <span className="text-blue-400 font-semibold">{metrics.total_dispatches}</span> dispatches
          </span>
          <span className={metrics.on_time_rate >= 0.9 ? 'text-green-400' : 'text-orange-400'}>
            <span className="font-semibold">{(metrics.on_time_rate * 100).toFixed(0)}%</span> on-time
          </span>
        </div>

        {/* Legend */}
        <div className="hidden xl:flex items-center gap-3 ml-4 text-[10px] text-gray-500 border-l border-gray-800 pl-4">
          <span>🍽️ Restaurant</span>
          <span>🎪 Event</span>
          <span>📍 Pickup</span>
          <span>🏥 Dest</span>
          <span>🚗 Driver</span>
          <span>🏠 Center</span>
          <span className="text-blue-400">── food</span>
          <span className="text-orange-400">── ride</span>
        </div>
      </header>

      {/* ── Main layout ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map — left ~60% */}
        <div className="flex-1 relative min-w-0">
          <MapCanvas world={world} dispatches={dispatches} signals={signals} />
        </div>

        {/* Right panel — fixed 420px */}
        <div className="w-[420px] flex flex-col border-l border-gray-800 bg-gray-950 overflow-hidden flex-shrink-0">

          {/* Tab bar */}
          <div className="flex gap-1 px-2 py-1.5 border-b border-gray-800 flex-shrink-0 bg-gray-900/50">
            <button className={tabClass('live')}   onClick={() => setTab('live')}>Live Feed</button>
            <button className={tabClass('agents')} onClick={() => setTab('agents')}>Agents</button>
            <button className={tabClass('impact')} onClick={() => setTab('impact')}>Impact</button>
          </div>

          {/* ── Live Feed tab ── */}
          {tab === 'live' && (
            <>
              <div className="flex-[3] overflow-hidden border-b border-gray-800 min-h-0">
                <SignalFeed signals={signals} />
              </div>
              <div className="flex-[4] overflow-hidden min-h-0">
                <DispatchBoard dispatches={dispatches} signals={signals} world={world} />
              </div>
            </>
          )}

          {/* ── Agents tab ── */}
          {tab === 'agents' && (
            <>
              <div className="flex-[4] overflow-hidden border-b border-gray-800 min-h-0">
                <ModelStatusPanel
                  modelStatus={modelStatus}
                  onStatusChange={setModelStatus}
                />
              </div>
              <div className="flex-[6] overflow-hidden min-h-0">
                <AgentTrace trace={agentTrace} />
              </div>
            </>
          )}

          {/* ── Impact tab ── */}
          {tab === 'impact' && (
            <div className="flex-1 overflow-hidden min-h-0">
              <ImpactStats metrics={metrics} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
