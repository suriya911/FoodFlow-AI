"""
In-memory RAG store for FlowGrid.
Stores every committed dispatch decision and retrieves semantically
similar past decisions to feed as context to the Supervisor agent.

No external vector DB required — uses urgency/stream/food-type matching.
Swap retrieve_similar() for a Pinecone call to upgrade to production RAG.
"""

import logging
from collections import deque
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_STORE = 150  # rolling window of past decisions


class InMemoryRAGStore:
    def __init__(self) -> None:
        self._store: deque = deque(maxlen=MAX_STORE)

    # ── write ────────────────────────────────────────────────────────────────

    def store_decision(self, signal: Dict, decision: Dict) -> None:
        record = {
            "stream":          signal.get("stream", "food"),
            "source_type":     signal.get("source_type", "restaurant"),
            "food_type":       signal.get("food_type", ""),
            "meals":           signal.get("meals", signal.get("passenger_count", 1)),
            "urgency_score":   round(signal.get("urgency_score", 0.5), 2),
            "spoilage_minutes":signal.get("spoilage_minutes", 60),
            "center_id":       decision.get("center_id", ""),
            "volunteer_id":    decision.get("volunteer_id", ""),
            "priority_score":  round(decision.get("priority_score", 0.5), 2),
            "rationale":       (decision.get("rationale") or "")[:120],
        }
        self._store.append(record)
        logger.debug("RAG stored decision for stream=%s urgency=%.2f", record["stream"], record["urgency_score"])

    # ── read ─────────────────────────────────────────────────────────────────

    def retrieve_similar(self, signal: Dict, top_k: int = 3) -> str:
        """Return a plain-text context string of the top-k similar past decisions."""
        if not self._store:
            return "No historical dispatch data available yet."

        stream        = signal.get("stream", "food")
        urgency       = signal.get("urgency_score", 0.5)
        food_type     = signal.get("food_type", "")

        # Score each stored record for similarity
        scored: List[tuple] = []
        for rec in self._store:
            sim = 0.0
            if rec["stream"] == stream:
                sim += 0.4
            sim += max(0.0, 0.3 - abs(rec["urgency_score"] - urgency) * 0.6)
            if food_type and rec.get("food_type") == food_type:
                sim += 0.3
            scored.append((sim, rec))

        top = sorted(scored, key=lambda x: x[0], reverse=True)[:top_k]

        if not top or top[0][0] < 0.1:
            return "No closely matching historical decisions found."

        lines = ["Relevant past dispatch decisions:"]
        for rank, (score, rec) in enumerate(top, 1):
            lines.append(
                f"  [{rank}] stream={rec['stream']} urgency={rec['urgency_score']:.2f} "
                f"meals={rec['meals']} → center={rec['center_id']} volunteer={rec['volunteer_id']} "
                f"score={rec['priority_score']:.2f} | \"{rec['rationale']}\""
            )
        return "\n".join(lines)

    def size(self) -> int:
        return len(self._store)


# Module singleton
rag_store = InMemoryRAGStore()
