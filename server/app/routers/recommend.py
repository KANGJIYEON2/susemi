"""POST /recommend — Phase 4-3 What-if greedy 추천."""

from fastapi import APIRouter

from app.schemas.recommend_schema import RecommendRequest, RecommendResponse
from app.services.recommend import recommend as recommend_service


router = APIRouter()


@router.post("/recommend", response_model=RecommendResponse)
def recommend_endpoint(body: RecommendRequest):
    return recommend_service(body)
