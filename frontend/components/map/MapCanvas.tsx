'use client'

import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet'
import { useEffect, useState } from 'react'
import type {
  Center, DispatchDecision, FoodEvent, Restaurant,
  RideDestination, RideOrigin, SurplusSignal, Volunteer, WorldState,
} from '@/lib/types'

// Fix Leaflet icon paths broken by webpack bundling
if (typeof window !== 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (L.Icon.Default.prototype as any)._getIconUrl
}

function makeIcon(bg: string, emoji: string, size = 34) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px;height:${size}px;
      background:${bg};
      border:2.5px solid rgba(255,255,255,0.85);
      border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      font-size:${Math.round(size * 0.44)}px;
      box-shadow:0 2px 10px rgba(0,0,0,0.55);
      cursor:pointer;
    ">${emoji}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  })
}

const ICONS = {
  restaurant:          makeIcon('#ef4444', '🍽️'),
  event:               makeIcon('#8b5cf6', '🎪'),
  volunteer_available: makeIcon('#3b82f6', '🚗'),
  volunteer_busy:      makeIcon('#f59e0b', '🚗', 34),
  center:              makeIcon('#22c55e', '🏠'),
  center_high_demand:  makeIcon('#16a34a', '🏠', 38),
  ride_origin:         makeIcon('#f97316', '📍'),
  ride_destination:    makeIcon('#ec4899', '🏥'),
}

function centerIcon(c: Center) {
  return c.demand_score >= 0.9 ? ICONS.center_high_demand : ICONS.center
}

// ── OSRM road routing ────────────────────────────────────────────────────────

type LatLng = [number, number]
type RouteCache = Record<string, LatLng[]>

async function fetchOSRMRoute(from: LatLng, to: LatLng): Promise<LatLng[]> {
  try {
    const url =
      `https://router.project-osrm.org/route/v1/driving/` +
      `${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`
    const res = await fetch(url)
    if (!res.ok) throw new Error('OSRM error')
    const data = await res.json()
    const coords: [number, number][] = data.routes[0].geometry.coordinates
    // OSRM returns [lng, lat]; Leaflet needs [lat, lng]
    return coords.map(([lng, lat]) => [lat, lng])
  } catch {
    // Fallback to straight line if OSRM fails
    return [from, to]
  }
}

function routeKey(from: LatLng, to: LatLng) {
  return `${from[0].toFixed(4)},${from[1].toFixed(4)}-${to[0].toFixed(4)},${to[1].toFixed(4)}`
}

// ── Route component that fetches from OSRM ────────────────────────────────────

interface RouteLineProps {
  id: string
  from: LatLng
  to: LatLng
  color: string
  weight?: number
  dashArray?: string
  opacity?: number
  cache: RouteCache
  onCached: (key: string, coords: LatLng[]) => void
}

function RouteLine({ id, from, to, color, weight = 3, dashArray, opacity = 0.9, cache, onCached }: RouteLineProps) {
  const key = routeKey(from, to)
  const [coords, setCoords] = useState<LatLng[]>(cache[key] ?? [from, to])

  useEffect(() => {
    if (cache[key]) {
      setCoords(cache[key])
      return
    }
    fetchOSRMRoute(from, to).then((route) => {
      onCached(key, route)
      setCoords(route)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return (
    <Polyline
      key={id}
      positions={coords}
      color={color}
      weight={weight}
      dashArray={dashArray}
      opacity={opacity}
    />
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  world: WorldState | null
  dispatches: DispatchDecision[]
  signals: SurplusSignal[]
}

export default function MapCanvas({ world, dispatches, signals }: Props) {
  // Cache OSRM responses so we don't re-fetch the same route on every render
  const [routeCache, setRouteCache] = useState<RouteCache>({})

  function handleCached(key: string, coords: LatLng[]) {
    setRouteCache((prev) => ({ ...prev, [key]: coords }))
  }

  if (!world) {
    return (
      <div className="w-full h-full bg-gray-900 flex items-center justify-center text-gray-500 text-sm">
        Connecting to backend…
      </div>
    )
  }

  const activeDispatches = dispatches.filter(
    (d) => d.status === 'active' || d.status === 'delivering',
  )

  return (
    <MapContainer
      center={[37.775, -122.43]}
      zoom={13}
      style={{ width: '100%', height: '100%' }}
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />

      {/* Restaurants */}
      {world.restaurants.map((r: Restaurant) => (
        <Marker key={r.id} position={[r.lat, r.lng]} icon={ICONS.restaurant}>
          <Popup><strong>{r.name}</strong><br />🍽️ Restaurant</Popup>
        </Marker>
      ))}

      {/* Events */}
      {world.events.map((e: FoodEvent) => (
        <Marker key={e.id} position={[e.lat, e.lng]} icon={ICONS.event}>
          <Popup><strong>{e.name}</strong><br />🎪 Event venue</Popup>
        </Marker>
      ))}

      {/* Food centers */}
      {world.centers.map((c: Center) => (
        <Marker key={c.id} position={[c.lat, c.lng]} icon={centerIcon(c)}>
          <Popup>
            <strong>{c.name}</strong><br />
            Demand: <b>{(c.demand_score * 100).toFixed(0)}%</b><br />
            Capacity: <b>{c.capacity_remaining}</b> meals
          </Popup>
        </Marker>
      ))}

      {/* Ride origins */}
      {(world.ride_origins ?? []).map((o: RideOrigin) => (
        <Marker key={o.id} position={[o.lat, o.lng]} icon={ICONS.ride_origin}>
          <Popup><strong>{o.name}</strong><br />📍 SafeRide pickup</Popup>
        </Marker>
      ))}

      {/* Ride destinations */}
      {(world.ride_destinations ?? []).map((d: RideDestination) => (
        <Marker key={d.id} position={[d.lat, d.lng]} icon={ICONS.ride_destination}>
          <Popup>
            <strong>{d.name}</strong><br />
            {d.type === 'hospital' ? '🏥 Hospital' : '🏠 Shelter'}
          </Popup>
        </Marker>
      ))}

      {/* Volunteers */}
      {world.volunteers.map((v: Volunteer) => (
        <Marker
          key={v.id}
          position={[v.lat, v.lng]}
          icon={v.available ? ICONS.volunteer_available : ICONS.volunteer_busy}
        >
          <Popup>
            <strong>{v.name}</strong><br />
            {v.available ? '✅ Available' : '🚗 In transit'}<br />
            {v.vehicle && <span>Vehicle: {v.vehicle}<br /></span>}
            Capacity: {v.capacity}
          </Popup>
        </Marker>
      ))}

      {/* Active dispatch road routes via OSRM */}
      {activeDispatches.flatMap((d) => {
        const vol = world.volunteers.find((v) => v.id === d.volunteer_id)
        const sig = signals.find((s) => s.id === d.signal_id)
        if (!vol || !sig) return []

        const volPos: LatLng    = [vol.lat, vol.lng]
        const sigPos: LatLng    = [sig.lat, sig.lng]

        if (d.stream === 'transport') {
          const destLat = sig.destination_lat ?? sig.lat
          const destLng = sig.destination_lng ?? sig.lng
          const destPos: LatLng = [destLat, destLng]

          return [
            // Driver → pickup (dashed orange)
            <RouteLine
              key={`${d.id}-to-pickup`}
              id={`${d.id}-to-pickup`}
              from={volPos}
              to={sigPos}
              color="#f97316"
              weight={3}
              dashArray="8 5"
              opacity={0.85}
              cache={routeCache}
              onCached={handleCached}
            />,
            // Pickup → destination (solid pink)
            <RouteLine
              key={`${d.id}-to-dest`}
              id={`${d.id}-to-dest`}
              from={sigPos}
              to={destPos}
              color="#ec4899"
              weight={4}
              opacity={0.9}
              cache={routeCache}
              onCached={handleCached}
            />,
          ]
        }

        // Food: vol → source (dashed blue) → center (solid green)
        const center = world.centers.find((c) => c.id === d.center_id)
        if (!center) return []
        const centerPos: LatLng = [center.lat, center.lng]

        return [
          <RouteLine
            key={`${d.id}-to-source`}
            id={`${d.id}-to-source`}
            from={volPos}
            to={sigPos}
            color="#60a5fa"
            weight={3}
            dashArray="8 5"
            opacity={0.85}
            cache={routeCache}
            onCached={handleCached}
          />,
          <RouteLine
            key={`${d.id}-to-center`}
            id={`${d.id}-to-center`}
            from={sigPos}
            to={centerPos}
            color="#4ade80"
            weight={4}
            opacity={0.9}
            cache={routeCache}
            onCached={handleCached}
          />,
        ]
      })}
    </MapContainer>
  )
}
