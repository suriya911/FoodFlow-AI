'use client'

import type { AgentTraceEntry } from '@/lib/types'

const AGENT_COLORS: Record<string, string> = {
  RAGAgent:        'text-purple-400',
  ScoringAgent:    'text-blue-400',
  FoodAgent:       'text-green-400',
  TransportAgent:  'text-cyan-400',
  ConflictDetector:'text-yellow-400',
  SupervisorAgent: 'text-orange-400',
  CommitAgent:     'text-emerald-400',
}

function agentColor(agent: string) {
  return AGENT_COLORS[agent] ?? 'text-gray-300'
}

function modelBadge(model: string) {
  if (model.includes('49B') || model.includes('Super'))  return 'bg-green-900/60 text-green-300'
  if (model.includes('9B')  || model.includes('Nano'))   return 'bg-blue-900/60 text-blue-300'
  return 'bg-gray-800 text-gray-400'
}

interface Props {
  trace: AgentTraceEntry[]
}

export default function AgentTrace({ trace }: Props) {
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="px-3 py-2 border-b border-gray-800 flex-shrink-0 flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Agent Execution Trace</span>
        <span className="ml-auto text-[10px] text-gray-600 font-mono">{trace.length} entries</span>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 font-mono text-[11px]">
        {trace.length === 0 ? (
          <div className="px-3 py-4 text-gray-600 text-center text-xs">
            No trace yet — start the sim to see agent activity
          </div>
        ) : (
          [...trace].reverse().map((entry) => (
            <div
              key={entry.id}
              className="px-3 py-1.5 border-b border-gray-900/60 hover:bg-gray-900/40 transition-colors"
            >
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`font-semibold ${agentColor(entry.agent)}`}>{entry.agent}</span>
                <span className="text-gray-600">›</span>
                <span className="text-gray-400">{entry.action}</span>
                <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-sans ${modelBadge(entry.model)}`}>
                  {entry.model.split(' ')[0]}
                </span>
              </div>
              <div className="text-gray-400 leading-relaxed">{entry.summary}</div>
              <div className="flex gap-3 mt-0.5 text-[10px] text-gray-600">
                <span>{new Date(entry.ts).toLocaleTimeString()}</span>
                <span className={entry.latency_ms > 2000 ? 'text-orange-500' : 'text-gray-600'}>
                  {entry.latency_ms.toFixed(0)} ms
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
