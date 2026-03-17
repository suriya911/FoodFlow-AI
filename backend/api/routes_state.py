from fastapi import APIRouter

from services import simulator

router = APIRouter()


@router.get("/state")
async def get_state():
    if simulator.game_state is None:
        return {"error": "State not initialized"}
    return simulator.game_state.to_world_state()


@router.get("/signals")
async def get_signals():
    if simulator.game_state is None:
        return []
    return simulator.game_state.signals


@router.get("/metrics")
async def get_metrics():
    if simulator.game_state is None:
        return {}
    return simulator.game_state.metrics
