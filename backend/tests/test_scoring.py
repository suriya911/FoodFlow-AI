import json
from pathlib import Path

import pytest

from services.tool_scoring import (
    estimate_impact,
    find_candidate_centers,
    find_candidate_volunteers,
    haversine_km,
    score_urgency,
)


@pytest.fixture
def seed():
    with open(Path(__file__).parent.parent / "data" / "seed_world.json") as f:
        return json.load(f)


def test_haversine_sf_to_la():
    dist = haversine_km(37.7749, -122.4194, 34.0522, -118.2437)
    assert 540 < dist < 580, f"Expected ~559 km, got {dist}"


def test_haversine_same_point():
    assert haversine_km(37.7749, -122.4194, 37.7749, -122.4194) == 0.0


def test_urgency_high():
    score = score_urgency(120, 30)
    assert score > 0.7, f"High urgency expected > 0.7, got {score}"


def test_urgency_low():
    score = score_urgency(20, 120)
    assert score < 0.2, f"Low urgency expected < 0.2, got {score}"


def test_urgency_bounded():
    for meals in [0, 50, 150, 200]:
        for mins in [1, 60, 120, 200]:
            s = score_urgency(meals, mins)
            assert 0.0 <= s <= 1.0, f"urgency out of [0,1]: {s}"


def test_candidate_centers_returns_sorted(seed):
    centers = find_candidate_centers(37.7749, -122.4194, 50, seed["centers"])
    assert len(centers) > 0
    assert "center_id" in centers[0]
    assert "composite_score" in centers[0]
    scores = [c["composite_score"] for c in centers]
    assert scores == sorted(scores, reverse=True), "Centers not sorted by composite_score"


def test_candidate_centers_capacity_filter(seed):
    # Request more meals than any center has capacity for
    centers = find_candidate_centers(37.7749, -122.4194, 10000, seed["centers"])
    assert centers == [], "Should exclude centers with insufficient capacity"


def test_candidate_volunteers_sorted(seed):
    vols = find_candidate_volunteers(
        37.7749, -122.4194,
        37.7830, -122.4189,
        50, seed["volunteers"],
    )
    assert len(vols) > 0
    etas = [v["eta_minutes"] for v in vols]
    assert etas == sorted(etas), "Volunteers not sorted by ETA"


def test_candidate_volunteers_capacity_filter(seed):
    # Only volunteers with capacity >= meals qualify
    vols = find_candidate_volunteers(
        37.7749, -122.4194, 37.7830, -122.4189,
        1000, seed["volunteers"],
    )
    assert all(v["capacity"] >= 1000 for v in vols)


def test_estimate_impact():
    impact = estimate_impact(100, 60)
    assert impact["meals_saved"] == 100
    assert impact["co2_avoided_kg"] == 50.0
    assert impact["people_fed"] == 100
