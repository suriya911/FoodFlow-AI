# 🌱 FoodFlow AI

> **Agentic surplus food dispatch network** — NVIDIA Nemotron reasons over time-to-spoilage, center demand, volunteer ETA, and impact to route food where it matters most. Live on a map. In real time.

---

## What it does

FoodFlow AI is a **live logistics system**, not a food listing app.

1. **Surplus signals** are emitted from 5 restaurants and 2 events every 10–20 s
2. **Tool functions** score urgency, rank centers, and rank volunteers
3. **NVIDIA Nemotron** (LLM) receives structured context and returns a JSON dispatch decision with a rationale
4. **Decision is committed** — volunteer begins moving on the map
5. **Impact metrics** update live: meals saved, CO₂ avoided, on-time rate
6. Operator can **manually override** any active dispatch

---

## Resources you need (read before running)

| Resource | Where to get it | Required? |
|---|---|---|
| **NVIDIA Nemotron API key** | [build.nvidia.com](https://build.nvidia.com) → API Catalog → Get API Key | Optional — app falls back to deterministic mock |
| **Node.js ≥ 18** | [nodejs.org](https://nodejs.org) | Required |
| **Python ≥ 3.10** | [python.org](https://python.org) | Required |
| GPU / CUDA | None — all inference is via API | Not needed |
| Supabase / DB | None — in-memory state | Not needed |

**Getting the Nemotron key (2 min):**
1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Sign up / log in
3. Navigate to **API Catalog** → search **Nemotron**
4. Click **Get API Key** → copy key starting with `nvapi-`
5. Paste into `backend/.env` (see step 3 below)

**Alternative — OpenRouter (free tier):**
- Sign up at [openrouter.ai](https://openrouter.ai)
- Generate API key
- Use `NEMOTRON_BASE_URL=https://openrouter.ai/api/v1` and `NEMOTRON_MODEL=nvidia/llama-3.1-nemotron-70b-instruct`

---

## Local setup

### 1 — Enter project

```bash
cd D:/FoodFlow-AI
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

### 3 — Configure environment

```bash
cp .env.example .env
# Edit .env — paste your NEMOTRON_API_KEY
# Leave blank to use the built-in mock planner (still works great for demos)
```

### 4 — Run backend

```bash
# from backend/ directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend is ready when you see:
```
INFO │ __main__ │ 🌱 World seeded — 17 entities ready
```

### 5 — Frontend (new terminal)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 6 — Run tests

```bash
cd backend
pytest tests/ -v
```

---

## Demo walkthrough

1. Open the app — map loads with all 17 entities pinned on San Francisco
2. Click **▶ Start Sim** — surplus signals begin flowing every 10–20 s
3. Watch the **Signal Feed** — urgency bars, food type, meals, spoilage countdown
4. Watch the **Dispatch Board** — Nemotron picks a center and volunteer with a rationale
5. Watch the **map** — volunteer moves (dashed blue line = pickup, solid green = delivery)
6. Watch **Impact** counters climb — meals saved, CO₂ avoided, on-time rate
7. Click **⚡ Tick** to fire one signal immediately (great for live demos)
8. Click **Override** on any active dispatch to reassign center/volunteer manually

---

## Architecture

```
frontend/                   Next.js 15 + TypeScript + Tailwind
├── app/(dashboard)/page    Main dashboard — WebSocket client, state reducer
├── components/map          react-leaflet map with live volunteer movement
├── components/signals      Signal feed with urgency bars
├── components/dispatch     Dispatch board with Nemotron rationale + override
└── components/metrics      Impact stats panel

backend/                    FastAPI + asyncio
├── main.py                 App entry, lifespan, WebSocket endpoint
├── services/simulator.py   Simulation loop, surplus emission, delivery animation
├── services/agent_runner   Nemotron API client + greedy mock fallback
├── services/tool_scoring   Haversine distance, urgency, candidate scoring
├── services/ws_manager     WebSocket broadcast hub
├── api/routes_state        GET /api/state  /signals  /metrics
├── api/routes_dispatch     POST /api/dispatch/plan  /accept (override)
├── api/routes_sim          POST /api/sim/start  /stop  /tick
└── data/seed_world.json    17 entities seeded in San Francisco
```

### WebSocket message types

| Type | Direction | Payload |
|---|---|---|
| `state` | server → client | Full WorldState on connect |
| `signal` | server → client | New SurplusSignal |
| `dispatch` | server → client | DispatchDecision from Nemotron |
| `volunteer_move` | server → client | {volunteer_id, lat, lng, available} |
| `delivery_complete` | server → client | {dispatch_id, signal_id, meals} |
| `metrics` | server → client | Updated Metrics |

### Key API endpoints

```
GET  /api/state                    Full world snapshot
GET  /api/signals                  All signals
GET  /api/metrics                  Metrics
POST /api/sim/start                Start auto-simulation
POST /api/sim/stop                 Stop auto-simulation
POST /api/sim/tick                 Emit one surplus signal immediately
POST /api/dispatch/plan/{id}       Re-plan a specific signal
POST /api/dispatch/accept          Manual override {signal_id, center_id, volunteer_id}
WS   /ws/live                      Live event stream
```

---

## Deployment

### Backend → Render

1. Create a new **Web Service** on [render.com](https://render.com)
2. Root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `NEMOTRON_API_KEY`, `NEMOTRON_BASE_URL`, `NEMOTRON_MODEL`

### Frontend → Vercel

1. Import repo on [vercel.com](https://vercel.com)
2. Root directory: `frontend`
3. Add env vars:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - `NEXT_PUBLIC_WS_URL` = `wss://your-backend.onrender.com`
4. Deploy

---

## Seed world (San Francisco)

| Type | Count | Examples |
|---|---|---|
| Restaurants | 5 | Golden Gate Bistro, Mission Taqueria, SOMA Kitchen |
| Events | 2 | Moscone Center Expo, Oracle Park Gala |
| Volunteers | 3 | Maria Santos, James Chen, Aisha Johnson |
| Food centers | 7 | SF Food Bank, Glide Memorial, Tenderloin Relief Center |

---

*Built for a hackathon. Powered by NVIDIA Nemotron. Map data © OpenStreetMap contributors.*