"""
Model Router — 3-tier Nemotron model switching with auto-fallback.

Tier 0 (Base)    : Nemotron-Super-49B  via build.nvidia.com
Tier 1 (Backup 1): Nemotron-Nano-9B   via OpenRouter
Tier 2 (Backup 2): Greedy mock        (always available, zero latency)
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

TIERS: List[Dict[str, Any]] = [
    {
        "tier":       "base",
        "name":       "Nemotron-Super-49B",
        "model_id":   "nvidia/llama-3.3-nemotron-super-49b-v1_5",
        "base_url":   "https://integrate.api.nvidia.com/v1",
        "key_env":    "NEMOTRON_API_KEY",
        "description": "Best reasoning — NVIDIA API Catalog",
    },
    {
        "tier":       "backup_1",
        "name":       "Nemotron-70B (OpenRouter)",
        "model_id":   "nvidia/llama-3.1-nemotron-70b-instruct",
        "base_url":   "https://openrouter.ai/api/v1",
        "key_env":    "OPENROUTER_API_KEY",
        "description": "Fast & capable — OpenRouter",
    },
    {
        "tier":       "backup_2",
        "name":       "Mock Greedy",
        "model_id":   "mock",
        "base_url":   None,
        "key_env":    None,
        "description": "Deterministic fallback — always available",
    },
]

DISPATCH_SYSTEM_PROMPT = """\
You are a FlowGrid AI dispatch agent. Assign the best available volunteer to route this signal.
Priorities: (1) urgency/spoilage, (2) center demand, (3) volunteer ETA, (4) meals impact.
Return ONLY valid JSON — no markdown, no extra text:
{
  "center_id": "...",
  "volunteer_id": "...",
  "priority_score": 0.0,
  "rationale": "1-2 sentence explanation",
  "fallback": "center_id or null"
}"""

SUPERVISOR_SYSTEM_PROMPT = """\
You are the FlowGrid Supervisor Agent. A volunteer conflict was detected.
Choose the best alternative available volunteer and return the updated dispatch.
Return ONLY valid JSON:
{
  "center_id": "...",
  "volunteer_id": "...",
  "priority_score": 0.0,
  "rationale": "1-2 sentence resolution explanation",
  "fallback": null
}"""


class TierStats:
    def __init__(self) -> None:
        self.calls: int = 0
        self.errors: int = 0
        self.total_latency_ms: float = 0.0
        self.status: str = "standby"  # standby | active | error

    @property
    def avg_latency_ms(self) -> float:
        return round(self.total_latency_ms / self.calls, 1) if self.calls else 0.0

    def to_dict(self, tier_meta: Dict) -> Dict:
        return {
            "tier":           tier_meta["tier"],
            "name":           tier_meta["name"],
            "description":    tier_meta["description"],
            "status":         self.status,
            "calls":          self.calls,
            "errors":         self.errors,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ModelRouter:
    def __init__(self) -> None:
        self._current: int = 0  # index into TIERS
        self._stats: List[TierStats] = [TierStats() for _ in TIERS]
        self._stats[0].status = "active"
        self._switch_log: List[Dict] = []

    # ── public interface ─────────────────────────────────────────────────────

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> Tuple[Optional[Dict], str]:
        """Call active tier; auto-fallback on failure. Returns (parsed_json, model_name)."""
        for idx in range(self._current, len(TIERS)):
            tier = TIERS[idx]
            stat = self._stats[idx]

            if tier["model_id"] == "mock":
                return None, tier["name"]  # caller uses greedy fallback

            api_key = os.getenv(tier["key_env"], "").strip()
            if not api_key:
                logger.info("No key for %s — skipping to next tier", tier["name"])
                continue

            t0 = time.time()
            try:
                client = AsyncOpenAI(api_key=api_key, base_url=tier["base_url"])
                resp = await client.chat.completions.create(
                    model=tier["model_id"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                result = json.loads(raw.strip())

                latency = (time.time() - t0) * 1000
                stat.calls += 1
                stat.total_latency_ms += latency

                if idx != self._current:
                    self._do_switch(idx, f"Recovered to {tier['name']}")

                logger.info("Model call OK: %s (%.0f ms)", tier["name"], latency)
                return result, tier["name"]

            except Exception as exc:
                latency = (time.time() - t0) * 1000
                stat.errors += 1
                stat.total_latency_ms += latency
                stat.status = "error"
                logger.warning("Tier %s failed: %s — falling back", tier["name"], exc)

        return None, TIERS[-1]["name"]  # all tiers exhausted → mock

    def force_fallback(self) -> str:
        """Manually advance to next tier (for demo / ops)."""
        next_idx = min(self._current + 1, len(TIERS) - 1)
        self._do_switch(next_idx, "Manual force-fallback by operator")
        return TIERS[self._current]["name"]

    def force_restore(self) -> str:
        """Reset back to base tier."""
        self._do_switch(0, "Manual restore to base tier")
        return TIERS[0]["name"]

    def get_status(self) -> Dict:
        return {
            "active_tier":  TIERS[self._current]["tier"],
            "active_model": TIERS[self._current]["name"],
            "tiers":        [s.to_dict(TIERS[i]) for i, s in enumerate(self._stats)],
            "switch_log":   self._switch_log[-10:],
        }

    # ── private ──────────────────────────────────────────────────────────────

    def _do_switch(self, new_idx: int, reason: str) -> None:
        from datetime import datetime, timezone
        self._stats[self._current].status = "standby"
        self._current = new_idx
        self._stats[new_idx].status = "active"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_tier": TIERS[max(0, new_idx - 1)]["name"],
            "to_tier":   TIERS[new_idx]["name"],
            "reason":    reason,
        }
        self._switch_log.append(entry)
        logger.info("Model switch: %s → %s (%s)", entry["from_tier"], entry["to_tier"], reason)

        # Broadcast to all WS clients
        try:
            import asyncio
            from services.websocket_manager import ws_manager
            asyncio.create_task(ws_manager.broadcast({"type": "model_switch", "data": self.get_status()}))
        except Exception:
            pass


# Module singleton
model_router = ModelRouter()
