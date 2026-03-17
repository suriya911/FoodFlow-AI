from fastapi import APIRouter

from services import simulator

router = APIRouter()


@router.post("/start")
async def start():
    await simulator.start_sim()
    return {"status": "started"}


@router.post("/stop")
async def stop():
    await simulator.stop_sim()
    return {"status": "stopped"}


@router.post("/tick")
async def tick():
    """Manually emit one food surplus signal."""
    signal = await simulator.emit_signal("food")
    return {"status": "ticked", "signal_id": signal["id"], "stream": "food"}


@router.post("/tick/ride")
async def tick_ride():
    """Manually emit one SafeRide transport signal."""
    signal = await simulator.emit_signal("transport")
    return {"status": "ticked", "signal_id": signal["id"], "stream": "transport"}
