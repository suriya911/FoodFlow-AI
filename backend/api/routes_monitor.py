"""
Monitor routes — agent trace, model status, and manual tier switching.
"""

from fastapi import APIRouter, HTTPException
from services.model_router import model_router
from services import simulator

router = APIRouter()


@router.get("/agent-trace")
async def get_agent_trace():
    """Return the last 100 agent execution trace entries."""
    if simulator.game_state is None:
        raise HTTPException(status_code=503, detail="Simulation not initialized")
    return {"agent_trace": simulator.game_state.agent_trace}


@router.get("/model-status")
async def get_model_status():
    """Return current model router status (active tier, stats, switch log)."""
    return model_router.get_status()


@router.post("/force-fallback")
async def force_fallback():
    """Manually advance the active model to the next tier."""
    name = model_router.force_fallback()
    return {"message": f"Switched to {name}", "status": model_router.get_status()}


@router.post("/force-restore")
async def force_restore():
    """Reset active model back to base tier (Nemotron-Super-49B)."""
    name = model_router.force_restore()
    return {"message": f"Restored to {name}", "status": model_router.get_status()}
