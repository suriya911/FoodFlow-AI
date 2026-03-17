export interface Restaurant {
  id: string
  name: string
  lat: number
  lng: number
  type: 'restaurant'
}

export interface FoodEvent {
  id: string
  name: string
  lat: number
  lng: number
  type: 'event'
}

export interface Volunteer {
  id: string
  name: string
  lat: number
  lng: number
  available: boolean
  capacity: number
  vehicle?: string
  streams?: string[]
  current_assignment?: string | null
}

export interface Center {
  id: string
  name: string
  lat: number
  lng: number
  demand_score: number
  capacity_remaining: number
}

export interface RideOrigin {
  id: string
  name: string
  lat: number
  lng: number
  type: 'ride_origin'
}

export interface RideDestination {
  id: string
  name: string
  lat: number
  lng: number
  type: 'hospital' | 'shelter'
}

export interface SurplusSignal {
  id: string
  stream: 'food' | 'transport'
  source_id: string
  source_name: string
  source_type: 'restaurant' | 'event' | 'ride_origin'
  lat: number
  lng: number
  food_type?: string
  meals: number
  spoilage_minutes: number
  urgency_score: number
  destination_id?: string
  destination_name?: string
  destination_lat?: number
  destination_lng?: number
  passenger_count?: number
  passenger_name?: string
  urgency_reason?: string
  timestamp: string
  status: 'pending' | 'assigned' | 'delivered'
}

export interface DispatchDecision {
  id: string
  stream: 'food' | 'transport'
  signal_id: string
  source_id: string
  source_name: string
  center_id: string
  center_name: string
  volunteer_id: string
  volunteer_name: string
  priority_score: number
  rationale: string
  fallback?: string | null
  timestamp: string
  status: 'active' | 'delivering' | 'completed' | 'cancelled'
  food_type?: string
  meals: number
  spoilage_minutes: number
  passenger_count?: number
  passenger_name?: string
  destination_name?: string
  urgency_reason?: string
}

export interface Metrics {
  meals_saved: number
  co2_avoided_kg: number
  rides_completed: number
  avg_dispatch_time_mins: number
  on_time_rate: number
  total_dispatches: number
  food_dispatches: number
  transport_dispatches: number
}

export interface WorldState {
  restaurants: Restaurant[]
  events: FoodEvent[]
  volunteers: Volunteer[]
  centers: Center[]
  ride_origins: RideOrigin[]
  ride_destinations: RideDestination[]
  active_signals: SurplusSignal[]
  active_dispatches: DispatchDecision[]
  metrics: Metrics
  sim_running: boolean
}

export interface AgentTraceEntry {
  id: string
  ts: string
  agent: string
  action: string
  model: string
  summary: string
  latency_ms: number
}

export interface TierStats {
  tier: string
  name: string
  description: string
  status: 'active' | 'standby' | 'error'
  calls: number
  errors: number
  avg_latency_ms: number
}

export interface ModelSwitchEntry {
  timestamp: string
  from_tier: string
  to_tier: string
  reason: string
}

export interface ModelStatus {
  active_tier: string
  active_model: string
  tiers: TierStats[]
  switch_log: ModelSwitchEntry[]
}

export type WSMessage =
  | { type: 'state'; data: WorldState }
  | { type: 'signal'; data: SurplusSignal }
  | { type: 'dispatch'; data: DispatchDecision }
  | { type: 'volunteer_move'; data: { volunteer_id: string; lat: number; lng: number; available: boolean } }
  | { type: 'delivery_complete'; data: { dispatch_id: string; signal_id: string; stream: string; meals: number; volunteer_id: string } }
  | { type: 'metrics'; data: Metrics }
  | { type: 'agent_trace'; data: AgentTraceEntry[] }
  | { type: 'model_switch'; data: ModelStatus }
  | { type: 'sim_started' }
  | { type: 'sim_stopped' }
