"""POST /simulate — 다년도 What-if 시뮬레이션."""

from fastapi import APIRouter

from app.schemas.simulate_schema import SimulateRequest, SimulateResponse
from app.services.simulate import simulate as simulate_service


router = APIRouter()


@router.post("/simulate", response_model=SimulateResponse)
def simulate_endpoint(body: SimulateRequest):
    return simulate_service(body)
