const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function get(path: string) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return res.json()
}

async function post(path: string, body?: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`)
  return res.json()
}

export const getState           = () => get('/api/state')
export const startSim           = () => post('/api/sim/start')
export const stopSim            = () => post('/api/sim/stop')
export const tickSim            = () => post('/api/sim/tick')
export const tickRide           = () => post('/api/sim/tick/ride')
export const getModelStatus     = () => get('/api/monitor/model-status')
export const getAgentTrace      = () => get('/api/monitor/agent-trace')
export const forceModelFallback = () => post('/api/monitor/force-fallback')
export const forceModelRestore  = () => post('/api/monitor/force-restore')

export function manualOverride(signal_id: string, center_id: string, volunteer_id: string) {
  return post('/api/dispatch/accept', { signal_id, center_id, volunteer_id })
}
