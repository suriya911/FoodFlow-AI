from pydantic import BaseModel
from typing import Optional, List


class Restaurant(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    type: str = "restaurant"


class Event(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    type: str = "event"


class Volunteer(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    available: bool = True
    capacity: int
    current_assignment: Optional[str] = None


class Center(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    demand_score: float
    capacity_remaining: int


class SurplusSignal(BaseModel):
    id: str
    source_id: str
    source_name: str
    source_type: str
    lat: float
    lng: float
    food_type: str
    meals: int
    spoilage_minutes: int
    urgency_score: float = 0.0
    timestamp: str
    status: str = "pending"


class CandidateCenter(BaseModel):
    center_id: str
    name: str
    demand_score: float
    distance_km: float
    capacity_remaining: int
    composite_score: float


class CandidateVolunteer(BaseModel):
    volunteer_id: str
    name: str
    distance_to_source_km: float
    eta_minutes: float
    capacity: int


class DispatchDecision(BaseModel):
    id: str
    signal_id: str
    source_id: str
    source_name: str
    center_id: str
    volunteer_id: str
    priority_score: float
    rationale: str
    fallback: Optional[str] = None
    timestamp: str
    status: str = "active"
    food_type: str
    meals: int
    spoilage_minutes: int


class Metrics(BaseModel):
    meals_saved: int = 0
    co2_avoided_kg: float = 0.0
    avg_dispatch_time_mins: float = 0.0
    on_time_rate: float = 1.0
    total_dispatches: int = 0


class WorldState(BaseModel):
    restaurants: List[Restaurant]
    events: List[Event]
    volunteers: List[Volunteer]
    centers: List[Center]
    active_signals: List[SurplusSignal]
    active_dispatches: List[DispatchDecision]
    metrics: Metrics
    sim_running: bool


class AcceptDispatchRequest(BaseModel):
    signal_id: str
    center_id: str
    volunteer_id: str
