# FoodFlow AI

**Real-time multi-agent logistics for surplus food rescue and safe-ride dispatch.**

FoodFlow AI is a production-grade agentic system that coordinates two critical last-mile operations in parallel: routing surplus food from restaurants and events to food banks before it spoils, and dispatching safe rides for vulnerable populations. A LangGraph multi-agent pipeline powered by NVIDIA Nemotron reasons over urgency, spoilage windows, center demand, and volunteer proximity — and commits dispatch decisions in real time to a live map.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron--70B-76b900?logo=nvidia)](https://openrouter.ai)
[![Docker](https://img.shields.io/badge/Docker-containerized-2496ED?logo=docker)](https://docker.com)
[![Terraform](https://img.shields.io/badge/Terraform-AWS-7B42BC?logo=terraform)](https://terraform.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Most food rescue apps are static listings. FoodFlow AI treats surplus food and transport dispatch as a live **agentic scheduling problem**: signals arrive continuously, resources are constrained, priorities conflict, and decisions need to be explained.

The system processes two concurrent streams:

- **Food stream** — surplus signals from restaurants and events, matched to food banks and shelters by urgency, spoilage time, center demand, and volunteer ETA
- **Transport stream (SafeRide)** — ride requests from vulnerable populations, matched to available volunteers by proximity and capacity

A six-node LangGraph graph handles every signal end-to-end with full observability: each agent node appends a structured trace entry, giving operators a complete audit trail for every decision.

---

## Architecture

```
                         Browser
                            │
                     Vercel (Next.js 15)
                            │  WebSocket + REST
                      ┌─────┴──────┐
                      │  FastAPI   │  AWS EC2 t2.micro
                      │  (port 80) │  nginx reverse proxy
                      └─────┬──────┘
                            │
              ┌─────────────▼──────────────┐
              │     LangGraph Pipeline      │
              │                            │
              │  RAGAgent                  │  In-memory rolling buffer
              │     ↓                      │  (150 past decisions)
              │  ScoringAgent              │  Haversine + urgency scoring
              │     ↓                      │
              │  FoodAgent / TransportAgent│  NVIDIA Nemotron-70B
              │     ↓                      │  via OpenRouter
              │  ConflictDetector          │  Resource contention check
              │     ↓                      │
              │  SupervisorAgent           │  Override + rationale
              │     ↓                      │
              │  CommitAgent               │  Final dispatch commit
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   3-Tier Model Router       │
              │                            │
              │  Tier 0  Nemotron-Super-49B │  NVIDIA API Catalog
              │  Tier 1  Nemotron-70B       │  OpenRouter (active)
              │  Tier 2  Greedy Mock        │  Zero-latency fallback
              └────────────────────────────┘
```

---

## Tech Stack

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| **API framework** | FastAPI 0.111 | Async REST + WebSocket server |
| **Agent orchestration** | LangGraph 0.2 | Stateful multi-agent graph with typed state |
| **LLM inference** | NVIDIA Nemotron-70B via OpenRouter | Dispatch reasoning and rationale generation |
| **In-memory RAG** | Custom rolling buffer (deque, 150 entries) | Retrieval-augmented context from past decisions |
| **Scoring tools** | Python (haversine, urgency, demand) | Deterministic candidate ranking before LLM call |
| **Simulation engine** | asyncio background task | Dual-stream signal emission every 10–20 s |
| **WebSocket hub** | FastAPI WebSocket + asyncio | Real-time state broadcast to all connected clients |
| **Containerisation** | Docker (python:3.11-slim) | Reproducible builds, ECR-ready |
| **Infrastructure** | Terraform + AWS EC2 t2.micro | Immutable infra-as-code, free-tier eligible |

### Frontend

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | Next.js 15 + TypeScript | App Router, server components |
| **Styling** | Tailwind CSS | Utility-first responsive layout |
| **Map** | react-leaflet + Leaflet + OpenStreetMap | Live entity map, route animation |
| **State** | useReducer + useRef | WebSocket message reducer, no external state lib |
| **Hosting** | Vercel (Hobby) | CI/CD from GitHub push, global CDN |

---

## Features

- **Live dual-stream dispatch** — food and ride signals processed in parallel, visualised on one map
- **LangGraph multi-agent pipeline** — six specialised agents with typed shared state and accumulated execution trace
- **NVIDIA Nemotron reasoning** — every dispatch includes a human-readable rationale from the LLM
- **3-tier model router** — automatic fallback from Nemotron-Super-49B → Nemotron-70B (OpenRouter) → Greedy Mock; manual force-switch via UI
- **In-memory RAG** — past decisions used as retrieval context; no external vector database required
- **Conflict detection** — detects when the same volunteer is double-booked and routes to supervisor for resolution
- **Agent trace viewer** — tabbed panel shows per-node latency, model used, and decision summary for every signal
- **Route animation** — volunteers animate along road-accurate paths on the map (OSRM routing)
- **Manual override** — operator can reassign any in-flight dispatch to a different center or volunteer
- **Impact metrics** — meals saved, CO₂ avoided (kg), rides completed, on-time rate, updated live

---

## Local Development

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.11 | [python.org](https://python.org) |
| Node.js | ≥ 18 | [nodejs.org](https://nodejs.org) |
| Git | any | [git-scm.com](https://git-scm.com) |

### 1 — Clone

```bash
git clone https://github.com/YOUR_USERNAME/foodflow-ai.git
cd foodflow-ai
```

### 2 — Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3 — Environment

```bash
cp .env.example .env
```

Open `backend/.env` and add your OpenRouter key:

```env
OPENROUTER_API_KEY=sk-or-v1-...   # openrouter.ai → Keys → Create Key
NEMOTRON_API_KEY=                  # optional — build.nvidia.com Tier 0
APP_URL=http://localhost:3000
```

> **No key?** The system runs in Greedy Mock mode (Tier 2) — fully functional, no LLM calls.

### 4 — Start backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Ready when you see:
```
INFO  🌱 World seeded — 18 entities ready
INFO  Uvicorn running on http://0.0.0.0:8000
```

### 5 — Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 6 — Tests

```bash
cd backend
pytest tests/ -v
```

---

## API Reference

### Simulation

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/sim/start` | Start automatic signal emission (10–20 s interval) |
| `POST` | `/api/sim/stop` | Stop automatic emission |
| `POST` | `/api/sim/tick/food` | Emit one food signal immediately |
| `POST` | `/api/sim/tick/ride` | Emit one ride signal immediately |

### State

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/state` | Full world snapshot (entities, dispatches, metrics) |
| `GET` | `/api/metrics` | Live impact metrics |
| `GET` | `/api/signals` | All signals with status |

### Dispatch

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/dispatch/accept` | Manual override `{signal_id, center_id, volunteer_id}` |

### Monitor

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/monitor/model-status` | Active tier, per-tier stats (calls, errors, latency) |
| `GET` | `/api/monitor/agent-trace` | Last 100 LangGraph trace entries |
| `POST` | `/api/monitor/force-fallback` | Force switch to next tier |
| `POST` | `/api/monitor/force-restore` | Restore to Tier 0 |

### WebSocket

```
WS /ws/live
```

| Message type | Direction | Payload |
|---|---|---|
| `state` | server → client | Initial full world state on connect |
| `signal` | server → client | New surplus / ride signal |
| `dispatch` | server → client | Committed dispatch decision + rationale |
| `agent_trace` | server → client | LangGraph execution trace for last signal |
| `model_switch` | server → client | Tier change event with reason |
| `volunteer_move` | server → client | `{id, lat, lng, available}` |
| `metrics` | server → client | Updated impact counters |

---

## LangGraph Agent Pipeline

Every signal (food or ride) passes through the same six-node graph:

```
RAGAgent
  │  Retrieves 3 similar past decisions from the rolling buffer
  │  Builds retrieval context: stream type, urgency, food type match
  ▼
ScoringAgent
  │  Runs deterministic scoring tools (no LLM)
  │  Scores centers by demand + distance; volunteers by ETA + capacity
  ▼
FoodAgent / TransportAgent
  │  Calls NVIDIA Nemotron with structured context + RAG snippet
  │  Returns JSON: {center_id, volunteer_id, rationale, confidence}
  ▼
ConflictDetector
  │  Checks if proposed volunteer has an active in-flight dispatch
  │  Routes to SupervisorAgent if conflict detected
  ▼
SupervisorAgent (conditional — only on conflict)
  │  Asks Nemotron to resolve: reassign volunteer or delay dispatch
  ▼
CommitAgent
  │  Writes final dispatch to GameState
  │  Calls rag_store.store_decision() to update retrieval buffer
  │  Broadcasts WebSocket messages: dispatch + agent_trace
```

State shape (`FlowGridState`):

```python
class FlowGridState(TypedDict):
    signal:      Dict           # incoming signal
    stream:      str            # "food" | "transport"
    candidates:  List[Dict]     # scored centers + volunteers
    proposal:    Optional[Dict] # LLM dispatch proposal
    conflict:    bool           # conflict flag
    decision:    Optional[Dict] # final committed decision
    agent_trace: Annotated[List[Dict], operator.add]  # accumulated trace
```

---

## Deployment

Infrastructure-as-code targets **AWS EC2 t2.micro** (free tier eligible) behind nginx for WebSocket support, with the Docker image stored in **AWS ECR**. The frontend deploys to **Vercel** via GitHub integration.

See [DEPLOY.md](DEPLOY.md) for the full step-by-step guide.

### Quick cost estimate

| Resource | Tier | Monthly cost |
|---|---|---|
| AWS EC2 t2.micro | Free for 12 months → ~$9/mo after | **$0–9** |
| AWS ECR (Docker registry) | 500 MB free | **$0** |
| Vercel (frontend) | Hobby free | **$0** |
| OpenRouter (Nemotron-70B) | ~$0.00042 / 1K tokens | **< $1** |
| **Total** | | **$0–10 / month** |

---

## Project Structure

```
foodflow-ai/
├── backend/
│   ├── main.py                    FastAPI app, lifespan, WebSocket endpoint
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── api/
│   │   ├── routes_state.py        GET /api/state, /signals, /metrics
│   │   ├── routes_dispatch.py     POST /api/dispatch/accept
│   │   ├── routes_sim.py          POST /api/sim/start, /stop, /tick/*
│   │   └── routes_monitor.py      GET/POST /api/monitor/*
│   ├── services/
│   │   ├── simulator.py           Dual-stream simulation engine
│   │   ├── langgraph_agent.py     6-node LangGraph pipeline
│   │   ├── model_router.py        3-tier model router with auto-fallback
│   │   ├── rag_store.py           In-memory RAG rolling buffer
│   │   ├── tool_scoring.py        Haversine, urgency, candidate scoring
│   │   └── ws_manager.py          WebSocket broadcast hub
│   ├── data/
│   │   └── seed_world.json        18 seeded entities in San Francisco
│   └── tests/
│       ├── test_scoring.py
│       └── test_simulator.py
├── frontend/
│   ├── app/(dashboard)/page.tsx   Main dashboard, WebSocket client
│   ├── components/
│   │   ├── map/MapCanvas.tsx      react-leaflet live map
│   │   ├── monitor/AgentTrace.tsx LangGraph execution log
│   │   └── monitor/ModelStatus.tsx Model health table
│   └── lib/
│       ├── types.ts               Shared TypeScript types
│       └── api.ts                 REST + monitor API helpers
├── infrastructure/
│   ├── main.tf                    EC2, ECR, VPC, security groups
│   ├── variables.tf
│   ├── outputs.tf
│   ├── userdata.sh                EC2 bootstrap: Docker + nginx + container
│   └── terraform.tfvars.example
├── docker-compose.yml             Local full-stack dev
└── DEPLOY.md                      Step-by-step deploy guide
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Map data © [OpenStreetMap](https://openstreetmap.org/copyright) contributors. Routing © [OSRM](http://project-osrm.org/).*
