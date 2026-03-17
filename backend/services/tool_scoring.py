import math
from typing import List, Dict, Any

FOOD_TYPES = [
    "Mixed Plates", "Sandwiches", "Rice & Beans", "Salad", "Pizza",
    "Soup", "Pastries", "Fruit & Veg", "Hot Entrees", "Catered Meals",
]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 3)


def score_urgency(meals: int, spoilage_minutes: int) -> float:
    """0-1 score: higher = more urgent. Weighted by time pressure + volume."""
    time_factor = max(0.0, 1.0 - spoilage_minutes / 120.0)
    meal_factor = min(1.0, meals / 150.0)
    return round(0.6 * time_factor + 0.4 * meal_factor, 3)


def find_candidate_centers(
    source_lat: float,
    source_lng: float,
    meals: int,
    centers: List[Dict],
    top_k: int = 4,
) -> List[Dict]:
    candidates = []
    for c in centers:
        if c["capacity_remaining"] < max(10, meals * 0.3):
            continue
        dist = haversine_km(source_lat, source_lng, c["lat"], c["lng"])
        distance_score = max(0.0, 1.0 - dist / 10.0)
        capacity_score = min(1.0, c["capacity_remaining"] / 200.0)
        composite = round(
            0.5 * c["demand_score"] + 0.3 * distance_score + 0.2 * capacity_score, 3
        )
        candidates.append(
            {
                "center_id": c["id"],
                "name": c["name"],
                "demand_score": c["demand_score"],
                "distance_km": dist,
                "capacity_remaining": c["capacity_remaining"],
                "composite_score": composite,
            }
        )
    return sorted(candidates, key=lambda x: x["composite_score"], reverse=True)[:top_k]


def find_candidate_volunteers(
    source_lat: float,
    source_lng: float,
    center_lat: float,
    center_lng: float,
    meals: int,
    volunteers: List[Dict],
    top_k: int = 3,
) -> List[Dict]:
    SPEED_KMH = 30.0
    candidates = []
    for v in volunteers:
        if not v.get("available", True):
            continue
        if v["capacity"] < meals:
            continue
        dist_to_source = haversine_km(v["lat"], v["lng"], source_lat, source_lng)
        eta_mins = round((dist_to_source / SPEED_KMH) * 60.0, 1)
        candidates.append(
            {
                "volunteer_id": v["id"],
                "name": v["name"],
                "distance_to_source_km": round(dist_to_source, 3),
                "eta_minutes": eta_mins,
                "capacity": v["capacity"],
            }
        )
    return sorted(candidates, key=lambda x: x["eta_minutes"])[:top_k]


def estimate_impact(meals: int, spoilage_minutes: int) -> Dict:
    return {
        "meals_saved": meals,
        "co2_avoided_kg": round(meals * 0.5, 1),
        "people_fed": meals,
    }
