import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes_dispatch import router as dispatch_router
from api.routes_monitor import router as monitor_router
from api.routes_sim import router as sim_router
from api.routes_state import router as state_router
from services import simulator
from services.websocket_manager import ws_manager

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(name)s │ %(message)s")
logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).parent / "data" / "seed_world.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(SEED_PATH) as f:
        seed = json.load(f)
    simulator.init_state(seed)
    n = (
        len(seed["restaurants"])
        + len(seed["events"])
        + len(seed["volunteers"])
        + len(seed["centers"])
        + len(seed.get("ride_origins", []))
        + len(seed.get("ride_destinations", []))
    )
    logger.info("🌱 World seeded — %d entities ready", n)
    yield
    await simulator.stop_sim()


app = FastAPI(title="FoodFlow AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(state_router, prefix="/api")
app.include_router(dispatch_router, prefix="/api/dispatch")
app.include_router(sim_router, prefix="/api/sim")
app.include_router(monitor_router, prefix="/api/monitor")


@app.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Push full state to new client immediately
        if simulator.game_state:
            await ws.send_text(
                json.dumps(
                    {"type": "state", "data": simulator.game_state.to_world_state()},
                    default=str,
                )
            )
        while True:
            await ws.receive_text()  # keep-alive ping
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@app.get("/health")
async def health():
    return {"status": "ok", "sim_running": simulator.game_state.sim_running if simulator.game_state else False}
