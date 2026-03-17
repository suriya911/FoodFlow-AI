import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import simulator

router = APIRouter()


class AcceptRequest(BaseModel):
    signal_id: str
    center_id: str
    volunteer_id: str


@router.post("/plan/{surplus_id}")
async def plan_dispatch(surplus_id: str):
    if simulator.game_state is None:
        raise HTTPException(400, "State not initialized")
    signal = simulator.game_state.get_signal(surplus_id)
    if not signal:
        raise HTTPException(404, f"Signal {surplus_id} not found")
    asyncio.create_task(simulator.plan_and_dispatch(signal))
    return {"status": "planning", "signal_id": surplus_id}


@router.post("/accept")
async def accept_override(req: AcceptRequest):
    if simulator.game_state is None:
        raise HTTPException(400, "State not initialized")
    try:
        dispatch = await simulator.manual_override(req.signal_id, req.center_id, req.volunteer_id)
        return dispatch
    except ValueError as exc:
        raise HTTPException(400, str(exc))
