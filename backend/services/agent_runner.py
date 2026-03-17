import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FoodFlow AI's autonomous dispatch agent.

Your mission: route surplus food from a source to the most impactful food center using an available volunteer.

Optimization priorities (in order):
1. Urgency — higher urgency_score means food spoils sooner; act faster
2. Center demand — higher demand_score = more people waiting
3. Volunteer ETA — lower eta_minutes = food arrives before spoilage
4. Meals impact — prefer routes that save more meals

Return ONLY a valid JSON object. No markdown, no code blocks, no extra text:
{
  "source_id": "string",
  "center_id": "string",
  "volunteer_id": "string",
  "priority_score": 0.0,
  "rationale": "1-2 sentence plain-English explanation of your choice",
  "fallback": "center_id or null"
}"""


def _client() -> Optional[AsyncOpenAI]:
    api_key = os.getenv("NEMOTRON_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def plan_dispatch(
    signal: Dict[str, Any],
    urgency_score: float,
    candidate_centers: List[Dict],
    candidate_volunteers: List[Dict],
    impact: Dict,
) -> Dict:
    if not candidate_centers or not candidate_volunteers:
        return _mock(signal, candidate_centers, candidate_volunteers)

    cl = _client()
    if cl is None:
        logger.info("No NEMOTRON_API_KEY — using mock planner")
        return _mock(signal, candidate_centers, candidate_volunteers)

    model = os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
    context = {
        "surplus": {
            "source_id": signal["source_id"],
            "source_name": signal["source_name"],
            "food_type": signal["food_type"],
            "meals": signal["meals"],
            "spoilage_minutes": signal["spoilage_minutes"],
            "urgency_score": urgency_score,
        },
        "candidate_centers": candidate_centers,
        "candidate_volunteers": candidate_volunteers,
        "estimated_impact": impact,
    }

    try:
        resp = await cl.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Dispatch context:\n{json.dumps(context, indent=2)}\n\n"
                        "Return the dispatch JSON now:"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown fences if model wraps output
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        decision = json.loads(raw.strip())
        logger.info("Nemotron decision: %s → %s", decision.get("center_id"), decision.get("volunteer_id"))
        return decision
    except Exception as exc:
        logger.warning("Nemotron error (%s) — falling back to mock", exc)
        return _mock(signal, candidate_centers, candidate_volunteers)


def _mock(signal: Dict, centers: List[Dict], volunteers: List[Dict]) -> Dict:
    """Deterministic greedy fallback when API is unavailable."""
    if not centers or not volunteers:
        return {}
    best_c = centers[0]
    best_v = volunteers[0]
    fallback = centers[1]["center_id"] if len(centers) > 1 else None
    eta_score = max(0.0, 1.0 - best_v["eta_minutes"] / 30.0)
    score = round((best_c["composite_score"] + eta_score) / 2, 3)
    return {
        "source_id": signal["source_id"],
        "center_id": best_c["center_id"],
        "volunteer_id": best_v["volunteer_id"],
        "priority_score": score,
        "rationale": (
            f"Greedy selection: {best_c['name']} has the highest composite demand score "
            f"({best_c['composite_score']}); {best_v['name']} has the fastest ETA "
            f"({best_v['eta_minutes']} min) to reach the source."
        ),
        "fallback": fallback,
    }
