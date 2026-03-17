"""
FlowGrid Simulator — dual-stream (food + transport) with LangGraph agents.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.rag_store import rag_store
from services.tool_scoring import FOOD_TYPES, score_urgency
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

URGENCY_REASONS = ["medical_appointment", "emergency_shelter", "hospital_transfer", "routine_care"]
PASSENGER_NAMES = ["Anonymous Guest", "Senior Resident", "Walk-In Client", "Referred Patient"]


# ── GameState ─────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self, seed: Dict) -> None:
        self.restaurants: List[Dict]       = seed["restaurants"]
        self.events: List[Dict]            = seed["events"]
        self.volunteers: List[Dict]        = [dict(v) for v in seed["volunteers"]]
        self.centers: List[Dict]           = [dict(c) for c in seed["centers"]]
        self.ride_origins: List[Dict]      = seed.get("ride_origins", [])
        self.ride_destinations: List[Dict] = seed.get("ride_destinations", [])

        self.signals: List[Dict]     = []
        self.dispatches: List[Dict]  = []
        self.agent_trace: List[Dict] = []  # last 100 trace entries

        self.metrics: Dict[str, Any] = {
            "meals_saved":            0,
            "co2_avoided_kg":         0.0,
            "rides_completed":        0,
            "avg_dispatch_time_mins": 0.0,
            "on_time_rate":           1.0,
            "total_dispatches":       0,
            "food_dispatches":        0,
            "transport_dispatches":   0,
        }
        self._dispatch_times: List[float]  = []
        self.sim_running: bool             = False
        self._task: Optional[asyncio.Task] = None

    def get_volunteer(self, vid: str) -> Optional[Dict]:
        return next((v for v in self.volunteers if v["id"] == vid), None)

    def get_center(self, cid: str) -> Optional[Dict]:
        return next((c for c in self.centers if c["id"] == cid), None)

    def get_ride_destination(self, did: str) -> Optional[Dict]:
        return next((d for d in self.ride_destinations if d["id"] == did), None)

    def get_signal(self, sid: str) -> Optional[Dict]:
        return next((s for s in self.signals if s["id"] == sid), None)

    def add_trace(self, entries: List[Dict]) -> None:
        self.agent_trace.extend(entries)
        if len(self.agent_trace) > 100:
            self.agent_trace = self.agent_trace[-100:]

    def to_world_state(self) -> Dict:
        return {
            "restaurants":       self.restaurants,
            "events":            self.events,
            "volunteers":        self.volunteers,
            "centers":           self.centers,
            "ride_origins":      self.ride_origins,
            "ride_destinations": self.ride_destinations,
            "active_signals":    [s for s in self.signals    if s["status"] != "delivered"],
            "active_dispatches": [d for d in self.dispatches if d["status"] not in ("completed", "cancelled")],
            "metrics":           self.metrics,
            "sim_running":       self.sim_running,
        }


# ── Module singleton ──────────────────────────────────────────────────────────

game_state: Optional[GameState] = None


def init_state(seed: Dict) -> None:
    global game_state
    game_state = GameState(seed)


# ── Simulation control ────────────────────────────────────────────────────────

async def start_sim() -> None:
    if game_state is None:
        raise RuntimeError("State not initialized")
    if game_state.sim_running:
        return
    game_state.sim_running = True
    game_state._task = asyncio.create_task(_sim_loop())
    await ws_manager.broadcast({"type": "sim_started"})
    logger.info("Simulation started (dual-stream food + transport)")


async def stop_sim() -> None:
    if game_state is None:
        return
    game_state.sim_running = False
    if game_state._task:
        game_state._task.cancel()
        game_state._task = None
    await ws_manager.broadcast({"type": "sim_stopped"})
    logger.info("Simulation stopped")


async def _sim_loop() -> None:
    while game_state and game_state.sim_running:
        await asyncio.sleep(random.uniform(10, 20))
        if game_state and game_state.sim_running:
            stream = "food" if random.random() < 0.6 else "transport"
            await emit_signal(stream)


# ── Signal emission ───────────────────────────────────────────────────────────

async def emit_signal(stream: str = "food") -> Dict:
    if stream == "transport":
        return await _emit_transport_signal()
    return await _emit_food_signal()


async def emit_surplus() -> Dict:
    """Legacy alias used by manual tick — emits food by default."""
    return await emit_signal("food")


async def _emit_food_signal() -> Dict:
    sources = game_state.restaurants + game_state.events
    source  = random.choice(sources)
    meals   = random.randint(20, 150)
    spoilage= random.randint(30, 120)

    signal: Dict = {
        "id":               f"sig_{uuid.uuid4().hex[:8]}",
        "stream":           "food",
        "source_id":        source["id"],
        "source_name":      source["name"],
        "source_type":      source["type"],
        "lat":              source["lat"],
        "lng":              source["lng"],
        "food_type":        random.choice(FOOD_TYPES),
        "meals":            meals,
        "spoilage_minutes": spoilage,
        "urgency_score":    score_urgency(meals, spoilage),
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "status":           "pending",
    }
    game_state.signals.append(signal)
    await ws_manager.broadcast({"type": "signal", "data": signal})
    asyncio.create_task(plan_and_dispatch(signal, "food"))
    return signal


async def _emit_transport_signal() -> Dict:
    if not game_state.ride_origins or not game_state.ride_destinations:
        return await _emit_food_signal()

    origin  = random.choice(game_state.ride_origins)
    dest    = random.choice(game_state.ride_destinations)
    pax     = random.randint(1, 3)
    window  = random.randint(20, 90)
    urgency = round(max(0.2, 1.0 - window / 90.0) * 0.7 + random.uniform(0.1, 0.3), 3)

    signal: Dict = {
        "id":               f"ride_{uuid.uuid4().hex[:8]}",
        "stream":           "transport",
        "source_id":        origin["id"],
        "source_name":      origin["name"],
        "source_type":      "ride_origin",
        "lat":              origin["lat"],
        "lng":              origin["lng"],
        "destination_id":   dest["id"],
        "destination_name": dest["name"],
        "destination_lat":  dest["lat"],
        "destination_lng":  dest["lng"],
        "passenger_count":  pax,
        "passenger_name":   random.choice(PASSENGER_NAMES),
        "urgency_reason":   random.choice(URGENCY_REASONS),
        "meals":            pax,
        "spoilage_minutes": window,
        "urgency_score":    urgency,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "status":           "pending",
    }
    game_state.signals.append(signal)
    await ws_manager.broadcast({"type": "signal", "data": signal})
    asyncio.create_task(plan_and_dispatch(signal, "transport"))
    return signal


# ── Planning & dispatch ───────────────────────────────────────────────────────

async def plan_and_dispatch(signal: Dict, stream: str) -> None:
    from services.langgraph_agent import run_agent
    t_start = datetime.now(timezone.utc)

    try:
        result = await run_agent(signal, stream)
    except Exception as exc:
        logger.error("LangGraph run_agent failed for %s: %s", signal["id"], exc)
        return

    trace_entries = result.get("agent_trace", [])
    if trace_entries:
        game_state.add_trace(trace_entries)
        await ws_manager.broadcast({"type": "agent_trace", "data": trace_entries})

    decision = result.get("final_decision")
    if not decision or "volunteer_id" not in decision:
        logger.warning("No final decision for signal %s", signal["id"])
        return

    vol = game_state.get_volunteer(decision["volunteer_id"])
    if not vol or not vol.get("available", True):
        avail = [v for v in game_state.volunteers if v.get("available", True)]
        if not avail:
            logger.warning("All volunteers busy for %s", signal["id"])
            return
        vol = avail[0]
        decision["volunteer_id"] = vol["id"]
        decision["rationale"] = f"[Auto-reassigned to {vol['name']}] " + decision.get("rationale", "")

    if stream == "food":
        dest_obj  = game_state.get_center(decision["center_id"])
        dest_lat  = dest_obj["lat"]  if dest_obj else signal["lat"]
        dest_lng  = dest_obj["lng"]  if dest_obj else signal["lng"]
        dest_name = dest_obj["name"] if dest_obj else decision["center_id"]
    else:
        dest_obj  = game_state.get_ride_destination(decision["center_id"])
        dest_lat  = dest_obj["lat"]  if dest_obj else signal.get("destination_lat", signal["lat"])
        dest_lng  = dest_obj["lng"]  if dest_obj else signal.get("destination_lng", signal["lng"])
        dest_name = dest_obj["name"] if dest_obj else signal.get("destination_name", "")

    elapsed_mins = (datetime.now(timezone.utc) - t_start).total_seconds() / 60.0
    dispatch: Dict = {
        "id":            f"dsp_{uuid.uuid4().hex[:8]}",
        "stream":        stream,
        "signal_id":     signal["id"],
        "source_id":     signal["source_id"],
        "source_name":   signal["source_name"],
        "center_id":     decision["center_id"],
        "center_name":   dest_name,
        "volunteer_id":  decision["volunteer_id"],
        "volunteer_name":vol["name"],
        "priority_score":decision.get("priority_score", 0.8),
        "rationale":     decision.get("rationale", ""),
        "fallback":      decision.get("fallback"),
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "status":        "active",
        "food_type":     signal.get("food_type", ""),
        "meals":         signal.get("meals", 0),
        "spoilage_minutes": signal.get("spoilage_minutes", 60),
        "passenger_count":  signal.get("passenger_count", 0),
        "passenger_name":   signal.get("passenger_name", ""),
        "destination_name": signal.get("destination_name", ""),
        "urgency_reason":   signal.get("urgency_reason", ""),
    }

    game_state.dispatches.append(dispatch)
    vol["available"]          = False
    vol["current_assignment"] = dispatch["id"]
    signal["status"]          = "assigned"

    gs = game_state
    gs.metrics["total_dispatches"] += 1
    gs._dispatch_times.append(elapsed_mins)
    gs.metrics["avg_dispatch_time_mins"] = round(
        sum(gs._dispatch_times) / len(gs._dispatch_times), 2
    )
    gs.metrics["food_dispatches" if stream == "food" else "transport_dispatches"] += 1

    await ws_manager.broadcast({"type": "dispatch", "data": dispatch})
    await ws_manager.broadcast({"type": "metrics",  "data": gs.metrics})
    rag_store.store_decision(signal, decision)
    logger.info("Dispatched [%s] %s vol=%s → %s", stream, dispatch["id"], vol["id"], dest_name)

    asyncio.create_task(_simulate_delivery(dispatch, signal, dest_lat, dest_lng))


# ── Delivery animation ────────────────────────────────────────────────────────

async def _simulate_delivery(dispatch: Dict, signal: Dict,
                              dest_lat: float, dest_lng: float) -> None:
    vol = game_state.get_volunteer(dispatch["volunteer_id"])
    if not vol:
        return

    await _animate(vol, vol["lat"], vol["lng"], signal["lat"], signal["lng"], 10, 1.0)
    await _animate(vol, signal["lat"], signal["lng"], dest_lat, dest_lng, 15, 1.0)

    dispatch["status"] = "completed"
    signal["status"]   = "delivered"
    vol["available"]   = True
    vol["current_assignment"] = None

    gs = game_state
    stream = dispatch.get("stream", "food")
    if stream == "food":
        gs.metrics["meals_saved"]    += signal.get("meals", 0)
        gs.metrics["co2_avoided_kg"]  = round(
            gs.metrics["co2_avoided_kg"] + signal.get("meals", 0) * 0.5, 1)
        center = gs.get_center(dispatch["center_id"])
        if center:
            center["capacity_remaining"] = max(0, center["capacity_remaining"] - signal.get("meals", 0))
    else:
        gs.metrics["rides_completed"] += 1

    total   = gs.metrics["total_dispatches"]
    on_time = 1.0 if signal.get("spoilage_minutes", 60) > 15 else 0.0
    gs.metrics["on_time_rate"] = round(
        (gs.metrics["on_time_rate"] * (total - 1) + on_time) / total, 3
    )

    await ws_manager.broadcast({
        "type": "delivery_complete",
        "data": {
            "dispatch_id":  dispatch["id"],
            "signal_id":    signal["id"],
            "stream":       stream,
            "meals":        signal.get("meals", 0),
            "volunteer_id": vol["id"],
        },
    })
    await ws_manager.broadcast({"type": "metrics", "data": gs.metrics})
    await ws_manager.broadcast({
        "type": "volunteer_move",
        "data": {"volunteer_id": vol["id"], "lat": vol["lat"],
                 "lng": vol["lng"], "available": True},
    })


async def _animate(vol: Dict, from_lat: float, from_lng: float,
                   to_lat: float, to_lng: float, steps: int, delay: float) -> None:
    for i in range(1, steps + 1):
        t = i / steps
        vol["lat"] = round(from_lat + t * (to_lat - from_lat), 6)
        vol["lng"] = round(from_lng + t * (to_lng - from_lng), 6)
        await ws_manager.broadcast({
            "type": "volunteer_move",
            "data": {"volunteer_id": vol["id"], "lat": vol["lat"],
                     "lng": vol["lng"], "available": False},
        })
        await asyncio.sleep(delay)


# ── Manual override ───────────────────────────────────────────────────────────

async def manual_override(signal_id: str, center_id: str, volunteer_id: str) -> Dict:
    signal = game_state.get_signal(signal_id)
    if not signal:
        raise ValueError(f"Signal {signal_id} not found")
    vol    = game_state.get_volunteer(volunteer_id)
    stream = signal.get("stream", "food")
    dest_obj = (game_state.get_center(center_id) if stream == "food"
                else game_state.get_ride_destination(center_id))
    if not dest_obj or not vol:
        raise ValueError("Invalid center/destination or volunteer id")

    for d in game_state.dispatches:
        if d["signal_id"] == signal_id and d["status"] == "active":
            d["status"] = "cancelled"
            old_vol = game_state.get_volunteer(d["volunteer_id"])
            if old_vol:
                old_vol["available"] = True
                old_vol["current_assignment"] = None

    dispatch: Dict = {
        "id":            f"dsp_{uuid.uuid4().hex[:8]}",
        "stream":        stream,
        "signal_id":     signal_id,
        "source_id":     signal["source_id"],
        "source_name":   signal["source_name"],
        "center_id":     center_id,
        "center_name":   dest_obj["name"],
        "volunteer_id":  volunteer_id,
        "volunteer_name":vol["name"],
        "priority_score":1.0,
        "rationale":     "Manual override by operator.",
        "fallback":      None,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "status":        "active",
        "food_type":     signal.get("food_type", ""),
        "meals":         signal.get("meals", 0),
        "spoilage_minutes": signal.get("spoilage_minutes", 60),
        "passenger_count":  signal.get("passenger_count", 0),
        "passenger_name":   signal.get("passenger_name", ""),
        "destination_name": signal.get("destination_name", ""),
        "urgency_reason":   signal.get("urgency_reason", ""),
    }
    game_state.dispatches.append(dispatch)
    vol["available"] = False
    vol["current_assignment"] = dispatch["id"]
    signal["status"] = "assigned"

    await ws_manager.broadcast({"type": "dispatch", "data": dispatch})
    asyncio.create_task(_simulate_delivery(
        dispatch, signal, dest_obj["lat"], dest_obj["lng"]))
    return dispatch
