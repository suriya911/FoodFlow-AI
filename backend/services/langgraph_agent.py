"""
FlowGrid Multi-Agent Graph (LangGraph)
======================================
Graph layout:

  [rag_node] → [scoring_node] → [dispatch_agent_node] → [conflict_check_node]
                                                                  │
                                              ┌──────────────────┤
                                         conflict?         no conflict?
                                              │                   │
                                     [supervisor_node]    [finalize_node]
                                              │                   │
                                              └────────┬──────────┘
                                                   [END]

Each node appends one entry to agent_trace — judges can see every reasoning step live.
"""

import logging
import operator
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from services.model_router import DISPATCH_SYSTEM_PROMPT, SUPERVISOR_SYSTEM_PROMPT, model_router
from services.rag_store import rag_store
from services.tool_scoring import (
    find_candidate_centers,
    find_candidate_volunteers,
)

logger = logging.getLogger(__name__)


# ── State ──────────────────────────────────────────────────────────────────────

class FlowGridState(TypedDict):
    signal:             Dict[str, Any]
    stream:             str                                   # "food" | "transport"
    centers_data:       List[Dict]
    volunteers_data:    List[Dict]
    rag_context:        str
    proposal:           Optional[Dict]
    final_decision:     Optional[Dict]
    conflict_detected:  bool
    agent_trace:        Annotated[List[Dict], operator.add]  # accumulates across nodes


# ── Helpers ────────────────────────────────────────────────────────────────────

def _trace(agent: str, action: str, model: str, summary: str, latency_ms: float) -> Dict:
    return {
        "id":          uuid.uuid4().hex[:6],
        "ts":          datetime.now(timezone.utc).isoformat(),
        "agent":       agent,
        "action":      action,
        "model":       model,
        "summary":     summary[:200],
        "latency_ms":  round(latency_ms),
    }


def _gs():
    """Late import to avoid circular dependency."""
    from services import simulator
    return simulator.game_state


def _build_dispatch_context(signal: Dict, centers: List, volunteers: List, rag_ctx: str) -> str:
    import json as _json
    ctx = {
        "signal": {
            "stream":            signal.get("stream"),
            "source_name":       signal.get("source_name"),
            "food_type":         signal.get("food_type", "N/A"),
            "urgency_reason":    signal.get("urgency_reason", "N/A"),
            "meals_or_pax":      signal.get("meals", signal.get("passenger_count", 1)),
            "spoilage_minutes":  signal.get("spoilage_minutes"),
            "urgency_score":     signal.get("urgency_score"),
        },
        "candidate_centers":    centers[:3],
        "candidate_volunteers": volunteers[:3],
        "rag_context":          rag_ctx,
    }
    return f"Dispatch context:\n{_json.dumps(ctx, indent=2)}\n\nReturn dispatch JSON:"


# ── Nodes ──────────────────────────────────────────────────────────────────────

async def rag_node(state: FlowGridState) -> Dict:
    t0 = time.time()
    ctx = rag_store.retrieve_similar(state["signal"])
    latency = (time.time() - t0) * 1000
    trace = _trace(
        "RAGAgent", "retrieve_context", "in-memory-store",
        f"Retrieved context ({rag_store.size()} records). Preview: {ctx[:80]}…",
        latency,
    )
    return {"rag_context": ctx, "agent_trace": [trace]}


async def scoring_node(state: FlowGridState) -> Dict:
    t0 = time.time()
    signal = state["signal"]
    gs = _gs()
    stream = state["stream"]

    if stream == "food":
        centers = find_candidate_centers(
            signal["lat"], signal["lng"],
            signal.get("meals", 1),
            gs.centers,
        )
        if centers:
            best_c = gs.get_center(centers[0]["center_id"])
            c_lat, c_lng = best_c["lat"], best_c["lng"]
        else:
            c_lat, c_lng = signal["lat"], signal["lng"]
    else:
        # Transport: destination is pre-determined in the signal
        dest = gs.get_ride_destination(signal.get("destination_id", ""))
        if dest:
            centers = [{
                "center_id": dest["id"], "name": dest["name"],
                "demand_score": 1.0, "distance_km": 0,
                "capacity_remaining": 999, "composite_score": 1.0,
            }]
            c_lat, c_lng = dest["lat"], dest["lng"]
        else:
            centers = []
            c_lat, c_lng = signal["lat"], signal["lng"]

    avail_vols = [v for v in gs.volunteers if v.get("available", True)]
    vols = find_candidate_volunteers(
        signal["lat"], signal["lng"],
        c_lat, c_lng,
        signal.get("meals", signal.get("passenger_count", 1)),
        avail_vols,
    )

    latency = (time.time() - t0) * 1000
    trace = _trace(
        "ScoringAgent", "score_candidates", "tool_scoring",
        f"Ranked {len(centers)} centers, {len(vols)} volunteers available",
        latency,
    )
    return {"centers_data": centers, "volunteers_data": vols, "agent_trace": [trace]}


async def dispatch_agent_node(state: FlowGridState) -> Dict:
    t0 = time.time()
    stream = state["stream"]
    centers = state["centers_data"]
    vols    = state["volunteers_data"]
    agent_name = "FoodAgent" if stream == "food" else "TransportAgent"

    if not centers or not vols:
        trace = _trace(agent_name, "propose_dispatch", "skipped",
                       "No candidates — skipping dispatch", 0)
        return {"proposal": None, "agent_trace": [trace]}

    user_msg = _build_dispatch_context(state["signal"], centers, vols, state["rag_context"])
    result, model_used = await model_router.call(DISPATCH_SYSTEM_PROMPT, user_msg)

    # Greedy fallback if model returned None
    if result is None:
        result = {
            "center_id":      centers[0]["center_id"],
            "volunteer_id":   vols[0]["volunteer_id"],
            "priority_score": round((centers[0]["composite_score"] +
                               max(0.0, 1.0 - vols[0]["eta_minutes"] / 30.0)) / 2, 3),
            "rationale":      (f"Greedy: {centers[0]['name']} (score {centers[0]['composite_score']}) "
                               f"+ {vols[0]['name']} (ETA {vols[0]['eta_minutes']} min)"),
            "fallback":       centers[1]["center_id"] if len(centers) > 1 else None,
        }

    latency = (time.time() - t0) * 1000
    trace = _trace(
        agent_name, "propose_dispatch", model_used,
        f"Proposed center={result.get('center_id')} vol={result.get('volunteer_id')} "
        f"score={result.get('priority_score')} | {result.get('rationale', '')[:80]}",
        latency,
    )
    return {"proposal": result, "agent_trace": [trace]}


def conflict_check_node(state: FlowGridState) -> Dict:
    proposal = state.get("proposal")
    if not proposal or "volunteer_id" not in proposal:
        trace = _trace("ConflictDetector", "check_availability", "rule-engine",
                       "No proposal to check", 0)
        return {"conflict_detected": False, "agent_trace": [trace]}

    gs = _gs()
    vol = gs.get_volunteer(proposal["volunteer_id"])
    conflict = (vol is not None) and (not vol.get("available", True))

    summary = (
        f"⚠️ CONFLICT — {proposal['volunteer_id']} is busy!"
        if conflict else
        f"✅ {proposal['volunteer_id']} is available"
    )
    trace = _trace("ConflictDetector", "check_availability", "rule-engine", summary, 0)
    return {"conflict_detected": conflict, "agent_trace": [trace]}


async def supervisor_node(state: FlowGridState) -> Dict:
    t0 = time.time()
    import json as _json
    gs = _gs()
    original = state["proposal"]
    avail_vols = [v for v in gs.volunteers if v.get("available", True)]

    if not avail_vols:
        trace = _trace("SupervisorAgent", "resolve_conflict", "rule-engine",
                       "No volunteers available — dispatch deferred", 0)
        return {"final_decision": None, "agent_trace": [trace]}

    conflict_ctx = {
        "conflict":              f"Volunteer {original.get('volunteer_id')} is currently busy",
        "original_proposal":     original,
        "available_volunteers":  [{"id": v["id"], "name": v["name"], "capacity": v["capacity"]}
                                  for v in avail_vols],
        "rag_context":           state.get("rag_context", ""),
    }
    user_msg = (f"Conflict resolution needed:\n{_json.dumps(conflict_ctx, indent=2)}\n\n"
                f"Pick the best available volunteer and return updated dispatch JSON:")

    result, model_used = await model_router.call(SUPERVISOR_SYSTEM_PROMPT, user_msg)

    # Fallback: rule-based reassignment
    if result is None or "volunteer_id" not in result:
        result = {
            **original,
            "volunteer_id":  avail_vols[0]["id"],
            "rationale":     f"[Supervisor] Conflict resolved: reassigned to {avail_vols[0]['name']} "
                             f"(original vol busy).",
            "priority_score": original.get("priority_score", 0.8),
            "fallback":       None,
        }
    else:
        result = {
            **original,
            **result,
            "rationale": f"[Supervisor] {result.get('rationale', '')}",
        }

    latency = (time.time() - t0) * 1000
    trace = _trace(
        "SupervisorAgent", "resolve_conflict", model_used,
        f"Resolved → vol={result.get('volunteer_id')} | {result.get('rationale','')[:90]}",
        latency,
    )
    return {"final_decision": result, "agent_trace": [trace]}


def finalize_node(state: FlowGridState) -> Dict:
    decision = state.get("final_decision") or state.get("proposal")
    trace = _trace(
        "CommitAgent", "finalize", "state-machine",
        f"Decision finalized → center={decision.get('center_id') if decision else 'none'} "
        f"vol={decision.get('volunteer_id') if decision else 'none'}",
        0,
    )
    return {"final_decision": decision, "agent_trace": [trace]}


# ── Routing ────────────────────────────────────────────────────────────────────

def route_after_conflict_check(state: FlowGridState) -> str:
    if not state.get("proposal"):
        return "end"
    return "supervisor" if state.get("conflict_detected") else "finalize"


# ── Graph ──────────────────────────────────────────────────────────────────────

def _build() -> Any:
    builder = StateGraph(FlowGridState)
    builder.add_node("rag",             rag_node)
    builder.add_node("scoring",         scoring_node)
    builder.add_node("dispatch_agent",  dispatch_agent_node)
    builder.add_node("conflict_check",  conflict_check_node)
    builder.add_node("supervisor",      supervisor_node)
    builder.add_node("finalize",        finalize_node)

    builder.set_entry_point("rag")
    builder.add_edge("rag",            "scoring")
    builder.add_edge("scoring",        "dispatch_agent")
    builder.add_edge("dispatch_agent", "conflict_check")
    builder.add_conditional_edges(
        "conflict_check",
        route_after_conflict_check,
        {"supervisor": "supervisor", "finalize": "finalize", "end": END},
    )
    builder.add_edge("supervisor", "finalize")
    builder.add_edge("finalize",   END)
    return builder.compile()


flowgrid_graph = _build()


# ── Public entry point ─────────────────────────────────────────────────────────

async def run_agent(signal: Dict, stream: str) -> Dict:
    """Run the full LangGraph pipeline for one signal. Returns the final state."""
    initial: FlowGridState = {
        "signal":           signal,
        "stream":           stream,
        "centers_data":     [],
        "volunteers_data":  [],
        "rag_context":      "",
        "proposal":         None,
        "final_decision":   None,
        "conflict_detected": False,
        "agent_trace":      [],
    }
    result = await flowgrid_graph.ainvoke(initial)
    return result
